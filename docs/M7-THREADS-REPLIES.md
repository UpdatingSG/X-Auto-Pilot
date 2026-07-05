# M7: Threads + Reply Engagement

## Overview

Mixed daily content plans: single tweets, educational threads, and reply engagement — with full draft generation and publishing.

## Features

### Mixed content planner
- Uses schedule settings: `tweets_per_day`, `threads_per_week`, `replies_per_day`
- Threads appear on Mon/Wed (spread across week) when `threads_per_week >= 2`
- Reply ideas appear only when active reply targets exist (max 3/day)

### Thread generation
- `thread_writer` agent produces 2 variants with `thread_tweets` JSON
- Draft variants store full thread; preview uses tweet 1

### Reply engagement
- **Reply targets**: manually added tweets to engage with (`/v1/reply-targets`)
- Planner links reply ideas to targets via `content_ideas.reply_target_id`
- Reply drafts store `x_tweet_id` in `generation_metadata` for publish

### Publishing
- **Tweet**: `POST /2/tweets` with text
- **Thread**: sequential replies chaining each tweet to the previous
- **Reply**: `POST /2/tweets` with `reply.in_reply_to_tweet_id`

## API

| Endpoint | Description |
|----------|-------------|
| `GET/POST /v1/reply-targets` | List / add reply targets |
| `DELETE /v1/reply-targets/{id}` | Remove target |
| `POST /v1/drafts/generate` | `{ idea_id }` or `{ reply_target_id }` |
| `POST /v1/publish/{draft_id}` | Publishes tweet, thread, or reply |

## UI

- **Engagement** (`/dashboard/engagement`): manage reply targets, draft replies directly
- **Content Plan**: content-type badges (tweet / thread / reply)
- **Drafts**: thread tweets shown as numbered list

## Usage

1. Add reply targets on the Engagement page (include X tweet ID for publishing)
2. **Regenerate plan** on Content Plan to get mixed ideas
3. Approve ideas → generate drafts → approve → schedule → publish

## Migration

```bash
cd apps/api && alembic upgrade head  # 0010_reply_targets
```

## Tests

- `test_threads.py` — thread draft + publish
- `test_replies.py` — reply targets, plan integration, reply publish
- `test_content_plans.py` — mixed plan types
