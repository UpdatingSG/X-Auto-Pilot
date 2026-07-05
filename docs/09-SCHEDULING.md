# Scheduling Architecture

## Goals

1. Respect user-configured quotas and posting windows
2. Appear human — randomized times, no patterns
3. Never double-book or miss approved drafts
4. Handle timezone correctly
5. Recover from missed slots gracefully

## Components

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Schedule       │────▶│  Slot Allocator  │────▶│  Redis ZSET     │
│  Config (PG)    │     │  (Python)        │     │  publish:queue  │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                        ┌──────────────────┐              │
                        │  PublishTick     │◀─────────────┘
                        │  (every minute)  │
                        └────────┬─────────┘
                                 ▼
                        ┌──────────────────┐
                        │  PublishWorkflow │
                        └──────────────────┘
```

## Slot Allocation Algorithm

### Input

- User schedule config (quotas, windows, jitter)
- Approved drafts awaiting schedule
- Already scheduled slots for the day
- Content type of draft

### Process

```python
async def allocate_slot(
    user_id: str,
    content_type: ContentType,
    draft_id: str,
    preferred_date: date | None = None,
) -> datetime:
    schedule = await get_schedule(user_id)
    tz = await get_user_timezone(user_id)
    target_date = preferred_date or date.today()

    # 1. Get available windows for target_date
    windows = get_windows_for_date(schedule.posting_windows, target_date, tz)

    # 2. Get already-occupied slots (scheduled + published today)
    occupied = await get_occupied_slots(user_id, target_date, tz)

    # 3. Check daily quota not exceeded
    if await count_scheduled_today(user_id, content_type) >= get_quota(schedule, content_type):
        target_date += timedelta(days=1)
        return await allocate_slot(user_id, content_type, draft_id, target_date)

    # 4. Pick window with fewest scheduled posts (load balance)
    window = min(windows, key=lambda w: count_in_window(occupied, w))

    # 5. Random time within window
    base_time = random_time_in_window(window, tz)

    # 6. Apply jitter
    jitter = random.randint(0, schedule.jitter_minutes * 60)
    if random.random() > 0.5:
        jitter = -jitter
    slot = base_time + timedelta(seconds=jitter)

    # 7. Avoid collisions (min 20 min gap)
    slot = avoid_collisions(slot, occupied, min_gap_minutes=20)

    # 8. Humanize: avoid :00 and :30 exactly
    slot = de_round_time(slot)

  return slot
```

### De-rounding

```python
def de_round_time(dt: datetime) -> datetime:
    minute = dt.minute
    if minute in (0, 30):
        offset = random.choice([-7, -3, 3, 7, 12, -12])
        dt = dt + timedelta(minutes=offset)
    second = random.randint(3, 47)  # not 0 or 59
    return dt.replace(second=second, microsecond=0)
```

## Redis Queue Structure

```
Key: publish:queue:{user_id}
Type: Sorted Set
Score: Unix timestamp of scheduled_at
Member: draft_id
```

Global queue for tick workflow:

```
Key: publish:queue:global
Score: Unix timestamp
Member: {user_id}:{draft_id}
```

### Operations

```python
# On approve
ZADD publish:queue:global {scheduled_at.timestamp()} {user_id}:{draft_id}

# PublishTick (every minute)
due = ZRANGEBYSCORE publish:queue:global 0 {now.timestamp()} LIMIT 0 50
for member in due:
    user_id, draft_id = member.split(":")
    start PublishWorkflow(draft_id)
    ZREM publish:queue:global member
```

## Quota Management

### Daily Quotas (reset at midnight user TZ)

| Type | Default | Tracking Key |
|------|---------|--------------|
| Tweets | 3 | `quota:{user_id}:{date}:tweet` |
| Replies | 15 | `quota:{user_id}:{date}:reply` |
| Quote tweets | 1 | `quota:{user_id}:{date}:quote_tweet` |

### Weekly Quotas

| Type | Default | Tracking |
|------|---------|----------|
| Threads | 2 | `quota:{user_id}:{iso_week}:thread` |

```python
async def check_quota(user_id, content_type) -> bool:
    key = quota_key(user_id, content_type)
    current = await redis.get(key) or 0
    limit = await get_quota_limit(user_id, content_type)
    return int(current) < limit

async def increment_quota(user_id, content_type):
    key = quota_key(user_id, content_type)
    await redis.incr(key)
    await redis.expire(key, ttl_until_reset(content_type))
```

## Thread Scheduling

Threads always scheduled in lowest-traffic window (typically morning). Never back-to-back with another thread within 3 days.

## Reply Scheduling

Replies spread throughout day — not clustered:

```python
def distribute_replies(replies: list[Draft], windows: list) -> list[datetime]:
    # Divide day into N equal slots, randomize within each
    slots = []
    interval = total_active_minutes(windows) // len(replies)
    for i, reply in enumerate(replies):
        slot_start = windows[0].start + timedelta(minutes=i * interval)
        slot_end = slot_start + timedelta(minutes=interval)
        slots.append(random_time_between(slot_start, slot_end))
    return sorted(slots)
```

## Missed Slot Handling

If `PublishTick` finds draft scheduled >15 min ago and unpublished:

1. Check draft still `approved` or `scheduled`
2. If X API was down → reschedule +15 min
3. If quota day passed → reallocate next available day
4. If draft expired (>48h) → mark `expired`, notify user

## Manual Override

User can set exact `scheduled_at` via API — bypasses allocator but still runs collision check.

## Timezone

- Stored per user in `users.timezone` (IANA, e.g. `Asia/Kolkata`)
- All `scheduled_at` stored as UTC in DB
- UI displays in user timezone
- Windows interpreted in user timezone

## Calendar View (Frontend)

```
GET /publish/queue?from=2026-07-04&to=2026-07-10

Returns:
[
  { draft_id, content_type, scheduled_at, preview_text, status }
]
```

## Observability

Metrics:
- `scheduler.slots_allocated` (by content_type)
- `scheduler.quota_exceeded` (count)
- `scheduler.missed_slots` (count)
- `scheduler.publish_latency` (scheduled_at vs actual publish)
