# API Design

Base URL: `https://api.xautopilot.app/v1`  
Auth: Bearer JWT (user session) + X OAuth tokens stored server-side  
Content-Type: `application/json`

## Error Format

```json
{
  "error": {
    "code": "DRAFT_NOT_FOUND",
    "message": "Draft with id ... not found",
    "details": {}
  }
}
```

HTTP status codes: 400 validation, 401 unauth, 403 forbidden, 404 not found, 429 rate limited, 500 internal.

---

## Authentication

### POST /auth/register

```json
{ "email": "user@example.com", "password": "..." }
```

### POST /auth/login

Returns `{ "access_token", "refresh_token", "expires_in" }`.

### POST /auth/refresh

### GET /auth/x/authorize

Redirects to X OAuth 2.0 PKCE flow.

### GET /auth/x/callback

Handles OAuth callback, stores encrypted tokens.

---

## Voice Profile

### GET /profile/voice

Returns active voice profile.

### POST /profile/voice

Creates new version (deactivates previous).

```json
{
  "profession": "Backend Engineer",
  "bio": "...",
  "interests": [{"topic": "System Design", "weight": 1.0}],
  "tone": ["technical", "helpful", "honest"],
  "writing_style": {
    "sentence_length": "varied",
    "humor_level": "subtle",
    "formality": "casual-professional"
  },
  "vocabulary": { "use": ["idempotent", "latency"], "avoid": ["leverage", "synergy"] },
  "never_discuss": ["politics", "crypto shilling"],
  "favorite_creators": [{"handle": "kelseyhightower", "priority": 1}]
}
```

### GET /profile/voice/versions

List all versions with `version`, `created_at`, `is_active`.

### POST /profile/voice/{version}/activate

---

## Knowledge Sources

### GET /sources

### POST /sources

```json
{
  "source_type": "rss",
  "name": "High Scalability",
  "config": { "url": "http://highscalability.com/rss.xml" },
  "fetch_interval_minutes": 240
}
```

### PATCH /sources/{id}

### DELETE /sources/{id}

### POST /sources/{id}/fetch

Trigger manual ingestion (starts Temporal workflow).

---

## Schedule

### GET /schedule

### PUT /schedule

```json
{
  "tweets_per_day": 3,
  "threads_per_week": 2,
  "replies_per_day": 15,
  "quote_tweets_per_day": 1,
  "posting_windows": [
    { "start": "09:00", "end": "09:45", "days": [1,2,3,4,5,6,7] },
    { "start": "13:00", "end": "13:45", "days": [1,2,3,4,5,6,7] },
    { "start": "19:00", "end": "19:45", "days": [1,2,3,4,5,6,7] }
  ],
  "jitter_minutes": 15,
  "require_approval": true
}
```

---

## Content Plans

### GET /plans?date=2026-07-04

### GET /plans/today

### POST /plans/generate

Trigger manual plan generation for a date.

### PATCH /plans/{plan_id}/ideas/{idea_id}

```json
{ "status": "approved" }
```

Bulk: `POST /plans/{plan_id}/ideas/bulk-update`

```json
{ "updates": [{ "idea_id": "...", "status": "rejected" }] }
```

---

## Drafts

### GET /drafts?status=ready&date=2026-07-04

Query params: `status`, `content_type`, `date`, `page`, `limit`.

### GET /drafts/{id}

Includes all variants with scores.

### POST /drafts/generate

Generate from approved idea.

```json
{ "idea_id": "uuid" }
```

Returns `{ "draft_id", "workflow_id" }` — poll or WebSocket for completion.

### PATCH /drafts/{id}

```json
{
  "status": "approved",
  "selected_variant_id": "uuid"
}
```

### PUT /drafts/{id}/content

User inline edit (triggers re-score).

```json
{
  "content_text": "edited tweet text",
  "thread_tweets": [{"index": 0, "text": "..."}]
}
```

### POST /drafts/{id}/regenerate

Generate new variants, same idea.

### POST /drafts/bulk-approve

```json
{ "draft_ids": ["uuid1", "uuid2"] }
```

---

## Publishing

### GET /publish/queue

Upcoming scheduled posts.

### POST /drafts/{id}/schedule

```json
{ "scheduled_at": "2026-07-04T09:23:00Z" }
```

Omit `scheduled_at` to auto-assign next window slot.

### POST /drafts/{id}/publish-now

Immediate publish (still requires `approved` status).

### DELETE /drafts/{id}/schedule

Cancel scheduled publish, revert to `approved`.

---

## Analytics

### GET /analytics/overview?period=7d

```json
{
  "follower_delta": 42,
  "total_impressions": 125000,
  "avg_engagement_rate": 0.034,
  "posts_published": 21,
  "top_post": { "id": "...", "engagement_rate": 0.12 }
}
```

### GET /analytics/posts?period=30d&sort=engagement_rate

### GET /analytics/insights

Weekly learning report.

```json
{
  "period": "2026-06-27 to 2026-07-04",
  "what_worked": ["engineering hot takes with personal anecdote"],
  "what_failed": ["generic productivity tips"],
  "best_posting_hour": 13,
  "best_category": "engineering",
  "recommended_adjustments": { "increase_weight": ["hot_take"], "decrease_weight": ["productivity"] }
}
```

### GET /analytics/topics

Topic performance breakdown.

---

## Research

### GET /research/clusters?limit=20

Recent ranked clusters.

### GET /research/runs

Ingestion/research run history.

---

## WebSocket

### WS /ws?token={jwt}

Events:

```json
{ "type": "draft.ready", "draft_id": "...", "content_type": "tweet" }
{ "type": "draft.failed", "draft_id": "...", "error": "..." }
{ "type": "publish.success", "draft_id": "...", "x_tweet_id": "..." }
{ "type": "publish.failed", "draft_id": "...", "error": "..." }
{ "type": "plan.ready", "plan_id": "...", "plan_date": "2026-07-04" }
```

---

## Internal APIs (Worker → API, mTLS)

Not exposed publicly. Used by Temporal activities.

- `POST /internal/drafts/{id}/complete`
- `POST /internal/metrics/sync`
- `POST /internal/research/complete`

---

## Rate Limits (API)

| Tier | Limit |
|------|-------|
| Authenticated | 100 req/min |
| Generation endpoints | 10 req/min |
| Bulk operations | 5 req/min |

Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.

## OpenAPI

Auto-generated from FastAPI at `/docs` (dev) and `/openapi.json`.

Pydantic models shared via `packages/shared-python` and TypeScript types generated for frontend via `openapi-typescript`.
