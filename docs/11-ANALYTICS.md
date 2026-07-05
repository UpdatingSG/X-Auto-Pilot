# Analytics Pipeline

## Objectives

1. Track engagement per published post over time
2. Aggregate performance by topic, category, time, hook type
3. Feed data to Learning Agent for continuous improvement
4. Power dashboard visualizations

## Data Collection

### X API Metrics Endpoints

```python
GET /2/tweets/{id}?tweet.fields=public_metrics,non_public_metrics,organic_metrics
```

**Available metrics (depends on API tier):**

| Metric | Basic | Pro |
|--------|-------|-----|
| impressions | organic only | full |
| likes | ✅ | ✅ |
| replies | ✅ | ✅ |
| reposts | ✅ | ✅ |
| bookmarks | ✅ | ✅ |
| quotes | ✅ | ✅ |

### Collection Schedule

`MetricsCollectionWorkflow` snapshots at:

| Checkpoint | Purpose |
|------------|---------|
| +1 hour | Early engagement signal |
| +6 hours | Peak engagement window |
| +24 hours | Primary performance metric |
| +7 days | Long-tail / bookmark signal |

```python
async def fetch_and_store_metrics(draft_id: str):
    post = await get_published_post(draft_id)
    metrics = await x_client.get_tweet_metrics(post.x_tweet_id)
    follower_count = await x_client.get_follower_count(post.user_id)

    engagement_rate = calculate_engagement_rate(metrics)

    await insert_post_metrics(
        post_id=post.id,
        impressions=metrics.impression_count,
        likes=metrics.like_count,
        replies=metrics.reply_count,
        reposts=metrics.retweet_count,
        bookmarks=metrics.bookmark_count,
        quotes=metrics.quote_count,
        engagement_rate=engagement_rate,
        follower_count=follower_count,
    )
```

### Engagement Rate Formula

```python
def calculate_engagement_rate(metrics) -> float:
    impressions = metrics.impression_count or 0
    if impressions == 0:
        return 0.0
    engagements = (
        metrics.like_count +
        metrics.reply_count +
        metrics.retweet_count +
        metrics.bookmark_count +
        metrics.quote_count
    )
    return engagements / impressions
```

## Aggregation Layer

Materialized views refreshed every 6 hours:

### daily_user_stats

```sql
CREATE MATERIALIZED VIEW daily_user_stats AS
SELECT
    pp.user_id,
    DATE(pp.published_at) AS stat_date,
    COUNT(*) AS posts_count,
    COUNT(*) FILTER (WHERE pp.content_type = 'tweet') AS tweets,
    COUNT(*) FILTER (WHERE pp.content_type = 'thread') AS threads,
    COUNT(*) FILTER (WHERE pp.content_type = 'reply') AS replies,
    AVG(latest.engagement_rate) AS avg_engagement_rate,
    SUM(latest.impressions) AS total_impressions,
    MAX(follower_count) - MIN(follower_count) AS follower_delta
FROM published_posts pp
JOIN LATERAL (
    SELECT * FROM post_metrics pm
    WHERE pm.post_id = pp.id
    ORDER BY pm.captured_at DESC LIMIT 1
) latest ON true
GROUP BY pp.user_id, DATE(pp.published_at);
```

### topic_performance

Join `published_posts.content_snapshot` metadata (category, hook_type) with metrics.

## Dashboard API Responses

### Overview (`GET /analytics/overview`)

```python
async def get_overview(user_id: str, period: str) -> Overview:
    return Overview(
        follower_delta=await follower_delta(user_id, period),
        total_impressions=await sum_impressions(user_id, period),
        avg_engagement_rate=await avg_engagement(user_id, period),
        posts_published=await count_posts(user_id, period),
        best_post=await top_post(user_id, period),
        engagement_trend=await daily_engagement_series(user_id, period),
        follower_trend=await follower_series(user_id, period),
    )
```

### Post Leaderboard

Sort by engagement_rate (min 100 impressions to qualify).

### Heatmap: Best Posting Times

```python
# 7x24 grid: day_of_week x hour → avg engagement_rate
heatmap = await db.fetch("""
    SELECT
        EXTRACT(DOW FROM pp.published_at AT TIME ZONE u.timezone) AS dow,
        EXTRACT(HOUR FROM pp.published_at AT TIME ZONE u.timezone) AS hour,
        AVG(pm.engagement_rate) AS avg_er
    FROM published_posts pp
    JOIN users u ON u.id = pp.user_id
    JOIN post_metrics pm ON pm.post_id = pp.id
    WHERE pp.user_id = $1 AND pm.captured_at > pp.published_at + INTERVAL '24 hours'
    GROUP BY dow, hour
""", user_id)
```

### Category Breakdown

Pie/bar chart: engagement by `content_category`.

## Analytics Agent

Weekly report generation:

**Input:**
- All posts from last 7 days with 24h metrics
- Previous week's learnings
- Voice profile current weights

**Output:** Structured insights stored and served via `GET /analytics/insights`.

## Follower Tracking

Daily snapshot via `GET /2/users/{id}?user.fields=public_metrics`:

```sql
INSERT INTO follower_snapshots (user_id, count, captured_at)
VALUES ($1, $2, now());
```

Enables follower growth chart independent of post metrics.

## Frontend Visualizations

| Chart | Library | Data Source |
|-------|---------|-------------|
| Engagement trend line | Recharts | daily_user_stats |
| Follower growth | Recharts | follower_snapshots |
| Posting time heatmap | Custom grid | heatmap query |
| Category breakdown | Recharts pie | topic_performance |
| Top posts table | DataTable | post leaderboard |
| Weekly insights card | Markdown render | analytics insights |

## Alerts (Post-MVP)

- Engagement drop >50% week-over-week
- Post with 0 impressions after 24h (possible shadowban signal)
- Follower loss >1% in a day

## Data Pipeline Architecture

```
X API → MetricsCollectionWorkflow → post_metrics (PG)
                                         ↓
                              Materialized View Refresh (6h)
                                         ↓
                              Analytics API → Dashboard
                                         ↓
                              WeeklyLearningWorkflow
```

## Privacy

- Only fetch metrics for user's own published posts
- No scraping of other users' private metrics
- Analytics data deleted on account deletion (GDPR)
