# Publishing Pipeline

## Overview

Publishes approved drafts to X/Twitter via API v2. Handles tweets, threads, replies, and quote tweets with rate limiting, idempotency, and failure recovery.

## X API Integration

### OAuth 2.0 PKCE Flow

```
User → /auth/x/authorize → X consent screen → callback
→ Exchange code for access + refresh tokens
→ Encrypt and store in x_accounts
```

**Required scopes:**
- `tweet.read`
- `tweet.write`
- `users.read`
- `offline.access` (refresh token)

### Token Management

```python
class XTokenManager:
    async def get_valid_token(self, user_id: str) -> str:
        account = await get_x_account(user_id)
        if account.token_expires_at < now() + timedelta(minutes=5):
            tokens = await refresh_oauth_token(account.refresh_token)
            await update_encrypted_tokens(account.id, tokens)
        return decrypt(account.access_token_enc)
```

## Publish Flow

```
Draft (approved) → Schedule → PublishTick → PublishWorkflow
    → Rate limit check → Content validation → X API call
    → Store x_tweet_id → Update status → Trigger analytics
```

## Content Types

### Single Tweet

```python
POST https://api.twitter.com/2/tweets
{
  "text": "draft content"
}
```

### Thread

Sequential replies to previous tweet:

```python
async def publish_thread(draft: Draft) -> PublishResult:
    tweets = draft.selected_variant.thread_tweets
    root_id = None
    published_ids = []

    for i, tweet in enumerate(sorted(tweets, key=lambda t: t.index)):
        payload = {"text": tweet.text}
        if root_id:
            payload["reply"] = {"in_reply_to_tweet_id": published_ids[-1]}

        response = await x_client.post_tweet(payload)
        published_ids.append(response.id)
        if i == 0:
            root_id = response.id

        # Rate limit: 200 tweets/15min per user
        await asyncio.sleep(random.uniform(2, 5))  # human-like gap

    return PublishResult(x_tweet_id=root_id, thread_ids=published_ids)
```

### Reply

```python
{
  "text": "reply content",
  "reply": { "in_reply_to_tweet_id": target.x_tweet_id }
}
```

### Quote Tweet

```python
{
  "text": "your perspective",
  "quote_tweet_id": target.x_tweet_id
}
```

## Rate Limiting

### X API Limits (User Context)

| Endpoint | Limit | Window |
|----------|-------|--------|
| POST /2/tweets | 200 | 15 min |
| GET tweet metrics | 900 | 15 min |

### Implementation

```python
class XRateLimiter:
    async def acquire(self, user_id: str, endpoint: str) -> bool:
        key = f"ratelimit:x:{user_id}:{endpoint}"
        remaining = await redis.get(key)

        if remaining is not None and int(remaining) <= 0:
            reset_at = await redis.get(f"{key}:reset")
            raise RateLimitError(reset_at=reset_at)

        return True

    async def update_from_headers(self, user_id: str, endpoint: str, headers: dict):
        key = f"ratelimit:x:{user_id}:{endpoint}"
        await redis.set(key, headers["x-rate-limit-remaining"])
        await redis.set(f"{key}:reset", headers["x-rate-limit-reset"])
        ttl = int(headers["x-rate-limit-reset"]) - int(time.time())
        await redis.expire(key, max(ttl, 1))
```

On 429: reschedule publish to `reset_at + random(30-120)s`.

## Idempotency

```python
async def publish_tweet(draft: Draft) -> PublishResult:
    if draft.idempotency_key:
        existing = await check_idempotency(draft.idempotency_key)
        if existing:
            return existing

    key = f"publish:{draft.id}"
    acquired = await redis.set(key, "1", nx=True, ex=3600)
    if not acquired:
        raise PublishInProgressError()

    try:
        result = await x_api_post(draft)
        await save_idempotency(draft.idempotency_key, result)
        return result
    finally:
        await redis.delete(key)
```

`idempotency_key` generated at draft approval: `sha256(draft_id + content_hash)`.

## Pre-Publish Validation

```python
def validate_before_publish(draft: Draft) -> list[str]:
    errors = []
    if draft.status not in ("approved", "scheduled"):
        errors.append("Draft not approved")
    if not draft.selected_variant:
        errors.append("No variant selected")
    text = get_content_text(draft)
    if len(text) > char_limit(draft.user_id):
        errors.append(f"Exceeds char limit: {len(text)}")
    if contains_banned_phrases(text, draft.user_id):
        errors.append("Contains banned phrase")
    if draft.scheduled_at and draft.scheduled_at < now() - timedelta(hours=48):
        errors.append("Draft expired")
    return errors
```

## Failure Handling

| Error | Action |
|-------|--------|
| 401 Unauthorized | Mark account `needs_reauth`, notify user, pause publishing |
| 403 Forbidden (policy) | Mark draft `failed`, log reason, notify user |
| 429 Rate limit | Reschedule per reset header |
| 500 X server error | Retry 3x with exponential backoff |
| Network timeout | Retry 3x |
| Thread partial publish | Store published IDs, mark `partial_publish`, manual recovery UI |

### Thread Partial Recovery

```python
# drafts.generation_metadata stores progress
{
  "partial_publish": {
    "published_indices": [0, 1, 2],
    "published_ids": ["123", "456", "789"],
    "failed_at_index": 3
  }
}
```

UI shows "Resume thread" button → continues from index 3.

## Post-Publish

1. Update `drafts.status = published`, `published_at`, `x_tweet_id`
2. Insert `published_posts` with content snapshot
3. Insert `generation_memory` (topic + embedding)
4. Increment quota counter
5. Notify via WebSocket
6. Start `MetricsCollectionWorkflow`

## Fallback: Manual Copy

If X API unavailable or account not connected:

```python
if not x_account.is_active:
    draft.status = "ready"  # stays as draft
    notify_user("Connect X account or copy manually")
    return ManualPublishResult(copy_text=draft.content)
```

UI provides "Copy to clipboard" + "Mark as published" for manual tracking.

## Audit Trail

Every publish attempt logged:

```json
{
  "action": "publish.attempt",
  "resource_type": "draft",
  "resource_id": "uuid",
  "details": {
    "content_type": "thread",
    "x_tweet_id": "123",
    "latency_ms": 1234,
    "success": true
  }
}
```

## Security

- Tokens encrypted at rest (AES-256-GCM, key from AWS Secrets Manager)
- Tokens never returned via API
- Publish only for authenticated user's own drafts
- Content policy check before API call (block obvious violations)
