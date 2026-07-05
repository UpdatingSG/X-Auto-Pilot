# Feedback Loop Architecture

## Purpose

Close the loop between publishing and generation. The system learns what works for YOUR audience and adjusts future content automatically.

```
Publish → Metrics → Aggregate → Learn → Update Weights → Better Content
    ↑                                                          │
    └──────────────────── Memory RAG ──────────────────────────┘
```

## Loop Cadence

| Loop | Frequency | Scope |
|------|-----------|-------|
| Micro | Per publish | Store topic in memory, increment quota |
| Daily | 6 AM | Adjust today's plan based on yesterday's performance |
| Weekly | Monday 8 AM | Full learning cycle, weight updates, insight report |
| Monthly | 1st of month | Prompt eval, prune stale memory |

## Weekly Learning Workflow

### Step 1: Data Collection

```python
async def aggregate_weekly_analytics(user_id: str) -> WeeklyAnalytics:
    posts = await get_posts_with_24h_metrics(user_id, days=7)

    sorted_by_er = sorted(posts, key=lambda p: p.engagement_rate, reverse=True)
    top_20_pct = sorted_by_er[:max(1, len(sorted_by_er) // 5)]
    bottom_20_pct = sorted_by_er[-max(1, len(sorted_by_er) // 5):]

    return WeeklyAnalytics(
        total_posts=len(posts),
        avg_engagement_rate=mean(p.engagement_rate for p in posts),
        top_performers=top_20_pct,
        bottom_performers=bottom_20_pct,
        category_breakdown=group_by_category(posts),
        hook_type_breakdown=group_by_hook(posts),
        hourly_breakdown=group_by_hour(posts),
        follower_delta=await follower_delta(user_id, days=7),
    )
```

### Step 2: Learning Agent Analysis

LLM analyzes patterns with structured output:

```json
{
  "patterns": {
    "winning": [
      "Personal war stories about production incidents get 2.3x avg engagement",
      "Contrarian hooks outperform question hooks 1.5x",
      "Posts between 180-240 chars perform best"
    ],
    "losing": [
      "Generic productivity tips below average",
      "Posts with >2 hashtags underperform"
    ]
  },
  "weight_adjustments": {
    "category_weights": {
      "engineering": 1.3,
      "hot_take": 1.2,
      "productivity": 0.7
    },
    "hook_weights": {
      "contrarian": 1.2,
      "story": 1.1,
      "question": 0.9
    }
  },
  "scheduling_insights": {
    "best_hours": [9, 13],
    "worst_hours": [22, 23]
  },
  "memory_entries": [
    {
      "type": "success",
      "summary": "Thread on Redis hot keys with personal migration story",
      "embedding_text": "redis hot key migration dragonfly cache warming"
    },
    {
      "type": "failure",
      "summary": "Generic 5 tips for productivity tweet",
      "embedding_text": "productivity tips morning routine"
    }
  ]
}
```

### Step 3: Apply Learnings

```python
async def apply_learned_weights(user_id: str, learnings: LearningResult):
    profile = await get_active_voice_profile(user_id)

    # Merge weights (don't replace — exponential moving average)
    alpha = 0.3  # learning rate
    current = profile.learned_weights
    updated = {}

    for key, new_weights in learnings.weight_adjustments.items():
        updated[key] = {}
        for k, v in new_weights.items():
            old = current.get(key, {}).get(k, 1.0)
            updated[key][k] = old * (1 - alpha) + v * alpha

    await create_voice_profile_version(user_id, learned_weights=updated)
```

### Step 4: Store Memory

```python
async def store_memory_entries(user_id: str, entries: list[MemoryEntry]):
    for entry in entries:
        embedding = await embed(entry.embedding_text)
        await insert_generation_memory(
            user_id=user_id,
            memory_type=entry.type,
            summary=entry.summary,
            embedding=embedding,
            expires_at=now() + timedelta(days=90),
        )
```

## How Learnings Affect Generation

### Content Planner

```python
# Weighted category selection
categories = weighted_random(
    all_categories,
    weights=voice_profile.learned_weights.get("category_weights", {}),
)

# Exclude failed patterns from memory
recent_failures = await fetch_memory(user_id, type="failure", days=30)
# Inject into prompt as "AVOID THESE PATTERNS"
```

### Tweet Writer

```python
# Hook type selection weighted by performance
hook_type = weighted_random(
    ["question", "contrarian", "story", "statistic"],
    weights=voice_profile.learned_weights.get("hook_weights", {}),
)

# Length targeting
optimal_range = voice_profile.learned_weights.get("optimal_length_range", [180, 260])
# Include in prompt: "Target {optimal_range[0]}-{optimal_range[1]} characters"
```

### Scheduler

```python
# Bias slot allocation toward best_hours
best_hours = voice_profile.learned_weights.get("scheduling_insights", {}).get("best_hours", [])
if best_hours:
    windows = prioritize_windows(windows, best_hours)
```

### Few-Shot Selection

Top performers automatically become few-shot examples in writer prompts.

## User Feedback Integration

Explicit user signals (MVP):

| Action | Signal | Effect |
|--------|--------|--------|
| Approve draft | Positive | Boost similar category/hook weights +0.1 |
| Reject draft | Negative | Decrease weights -0.15 |
| Edit before approve | Partial positive | Store edited version as preference |
| Regenerate | Negative | Decrease hook pattern weight |

```python
async def on_draft_rejected(draft_id: str):
    draft = await get_draft(draft_id)
    await store_memory(
        user_id=draft.user_id,
        memory_type="rejection",
        summary=f"Rejected {draft.category} tweet: {draft.preview}",
        embedding=await embed(draft.content_text),
    )
```

## Anti-Overfitting

Safeguards:

1. **Minimum sample size:** Don't adjust weights until ≥20 published posts
2. **EMA smoothing:** `alpha=0.3` prevents wild swings from one viral post
3. **Weight bounds:** Clamp all weights to [0.5, 2.0]
4. **Exploration:** 20% of ideas use random (non-weighted) category selection
5. **Decay:** Memory entries expire after 90 days

## Weekly Report (User-Facing)

Delivered via dashboard + optional email:

```markdown
## Your Week on X (Jun 27 – Jul 4)

**Followers:** +42 (1.2% growth)
**Posts:** 21 (avg engagement: 3.4%)
**Best post:** "We migrated from Redis to..." (8.2% ER, 12K impressions)

### What worked
- Engineering stories with personal anecdotes
- Contrarian takes on popular tools
- Posting at 1 PM your timezone

### What didn't
- Generic productivity content
- Tweets over 260 characters

### Adjustments made
- Increased engineering content weight (+30%)
- Reduced productivity content weight (-30%)
- Prioritizing 1 PM posting window
```

## Metrics for Loop Health

| Metric | Target |
|--------|--------|
| Week-over-week engagement trend | Non-decreasing |
| Draft approval rate trend | Increasing |
| Weight stability (max change/week) | < 0.5 per dimension |
| Memory retrieval hit rate in planning | > 80% |

## Future: Multi-Armed Bandit

Post-MVP, replace static weights with Thompson Sampling per category:

```python
# Each category has Beta(α, β) distribution
# α += engagements, β += (impressions - engagements)
category = thompson_sample(categories)
```

## Future: Style Cloning from Creators

Analyze favorite creators' engagement patterns (public data only) to inform hook structures — not copy voice.
