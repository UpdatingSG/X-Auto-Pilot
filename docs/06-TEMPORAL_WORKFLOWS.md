# Temporal Workflow Design

## Why Temporal

- **Durable execution:** AI pipelines run 30s–5min; survive worker restarts
- **Retries with backoff:** OpenAI/X API transient failures
- **Visibility:** Debug failed generations in Temporal UI
- **Schedules:** Built-in cron for ingestion, planning, analytics
- **Sagas:** Compensating actions on partial publish failure (thread halfway posted)

## Namespace & Task Queues

```
Namespace: x-autopilot-prod

Task Queues:
  - ingestion-tq
  - research-tq
  - planning-tq
  - generation-tq
  - publish-tq
  - analytics-tq
```

## Workflow Catalog

### Scheduled Workflows (Temporal Schedules)

| Schedule ID | Cron | Workflow | Queue |
|-------------|------|----------|-------|
| `ingest-all-users` | `0 */4 * * *` | IngestionOrchestratorWorkflow | ingestion-tq |
| `daily-plan-all-users` | `0 6 * * *` | PlanningOrchestratorWorkflow | planning-tq |
| `analytics-sync` | `0 */6 * * *` | AnalyticsSyncOrchestratorWorkflow | analytics-tq |
| `weekly-learning` | `0 8 * * 1` | LearningOrchestratorWorkflow | analytics-tq |
| `publish-tick` | `* * * * *` | PublishTickWorkflow | publish-tq |

### Core Workflows

## 1. IngestionWorkflow

Per user, per source.

```python
@workflow.defn
class IngestionWorkflow:
    @workflow.run
    async def run(self, user_id: str, source_id: str) -> IngestionResult:
        raw_items = await workflow.execute_activity(
            fetch_source, source_id,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        normalized = await workflow.execute_activity(
            normalize_items, raw_items,
            start_to_close_timeout=timedelta(minutes=2),
        )
        deduped = await workflow.execute_activity(
            deduplicate_items, user_id, normalized,
            start_to_close_timeout=timedelta(minutes=2),
        )
        embedded = await workflow.execute_activity(
            embed_and_store, user_id, deduped,
            start_to_close_timeout=timedelta(minutes=10),
            heartbeat_timeout=timedelta(seconds=30),
        )
        return embedded
```

**Child workflows:** One `IngestionWorkflow` per enabled source.

`IngestionOrchestratorWorkflow` fans out per user → per source, then triggers `ResearchWorkflow`.

## 2. ResearchWorkflow

```python
@workflow.defn
class ResearchWorkflow:
    @workflow.run
    async def run(self, user_id: str) -> ResearchResult:
        items = await workflow.execute_activity(
            fetch_recent_items, user_id, hours=48,
            start_to_close_timeout=timedelta(minutes=2),
        )
        if len(items) < 3:
            return ResearchResult(skipped=True)

        clusters = await workflow.execute_activity(
            research_agent_cluster, user_id, items,
            start_to_close_timeout=timedelta(minutes=15),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )
        stored = await workflow.execute_activity(
            store_clusters, user_id, clusters,
            start_to_close_timeout=timedelta(minutes=2),
        )
        return stored
```

## 3. DailyPlanningWorkflow

```python
@workflow.defn
class DailyPlanningWorkflow:
    @workflow.run
    async def run(self, user_id: str, plan_date: str) -> PlanResult:
        # Idempotency: skip if plan exists
        exists = await workflow.execute_activity(check_plan_exists, user_id, plan_date)
        if exists:
            return PlanResult(skipped=True)

        clusters = await workflow.execute_activity(fetch_top_clusters, user_id, limit=20)
        memory = await workflow.execute_activity(fetch_generation_memory, user_id)
        schedule = await workflow.execute_activity(fetch_schedule, user_id)
        voice = await workflow.execute_activity(fetch_voice_profile, user_id)

        ideas = await workflow.execute_activity(
            content_planner_agent, user_id, clusters, memory, schedule, voice,
            start_to_close_timeout=timedelta(minutes=10),
        )

        plan = await workflow.execute_activity(save_content_plan, user_id, plan_date, ideas)
        await workflow.execute_activity(notify_plan_ready, user_id, plan.id)

        # Auto-generate drafts for approved ideas (if auto-approve ideas enabled)
        approved = [i for i in ideas if i.auto_approved]
        for idea in approved:
            await workflow.start_child_workflow(
                GenerationWorkflow.run,
                user_id, idea.id,
                id=f"gen-{idea.id}",
                task_queue="generation-tq",
            )

        return plan
```

## 4. GenerationWorkflow

Central content generation pipeline.

```python
@workflow.defn
class GenerationWorkflow:
    @workflow.run
    async def run(self, user_id: str, idea_id: str) -> DraftResult:
        idea = await workflow.execute_activity(fetch_idea, idea_id)
        draft = await workflow.execute_activity(create_draft_record, user_id, idea_id)

        rag_context = await workflow.execute_activity(
            retrieve_rag_context, user_id, idea,
            start_to_close_timeout=timedelta(minutes=2),
        )

        # Route by content type
        if idea.content_type == "tweet":
            variations = await workflow.execute_activity(
                generate_tweet_variations, user_id, idea, rag_context,
                start_to_close_timeout=timedelta(minutes=3),
            )
        elif idea.content_type == "thread":
            variations = await workflow.execute_activity(
                generate_thread_variations, user_id, idea, rag_context,
                start_to_close_timeout=timedelta(minutes=5),
            )
        elif idea.content_type == "reply":
            variations = await workflow.execute_activity(
                generate_reply_variations, user_id, idea,
                start_to_close_timeout=timedelta(minutes=2),
            )
        else:
            variations = await workflow.execute_activity(
                generate_quote_variations, user_id, idea, rag_context,
                start_to_close_timeout=timedelta(minutes=2),
            )

        # Quality pipeline
        fact_checked = await workflow.execute_activity(
            fact_check_variations, variations, rag_context,
            start_to_close_timeout=timedelta(minutes=2),
        )

        # Retry once if fact check fails
        if fact_checked.needs_regeneration:
            variations = await workflow.execute_activity(
                regenerate_with_fixes, user_id, idea, fact_checked.issues,
                start_to_close_timeout=timedelta(minutes=3),
            )
            fact_checked = await workflow.execute_activity(
                fact_check_variations, variations, rag_context,
            )

        scored = await workflow.execute_activity(
            score_variations, user_id, fact_checked.variations,
            start_to_close_timeout=timedelta(minutes=2),
        )

        humanized = await workflow.execute_activity(
            humanize_top_variant, scored[0],
            start_to_close_timeout=timedelta(minutes=1),
        )

        result = await workflow.execute_activity(
            save_draft_variants, draft.id, humanized, scored,
        )
        await workflow.execute_activity(notify_draft_ready, user_id, draft.id)
        return result
```

## 5. ApprovalScheduleWorkflow

Triggered when user approves draft.

```python
@workflow.defn
class ApprovalScheduleWorkflow:
    @workflow.run
    async def run(self, draft_id: str) -> ScheduleResult:
        draft = await workflow.execute_activity(fetch_draft, draft_id)
        slot = await workflow.execute_activity(
            compute_next_posting_slot, draft.user_id, draft.content_type,
        )
        await workflow.execute_activity(
            update_draft_scheduled, draft_id, slot.scheduled_at,
        )
        await workflow.execute_activity(
            add_to_publish_queue, draft_id, slot.scheduled_at,
        )
        return slot
```

## 6. PublishWorkflow

```python
@workflow.defn
class PublishWorkflow:
    @workflow.run
    async def run(self, draft_id: str) -> PublishResult:
        draft = await workflow.execute_activity(fetch_draft, draft_id)

        # Idempotency check
        if draft.status == "published":
            return PublishResult(already_published=True)

        await workflow.execute_activity(
            check_x_rate_limit, draft.user_id,
        )

        if draft.content_type == "thread":
            result = await workflow.execute_activity(
                publish_thread, draft,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    non_retryable_error_types=["AuthError", "ContentPolicyError"],
                ),
            )
        else:
            result = await workflow.execute_activity(
                publish_tweet, draft,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )

        await workflow.execute_activity(
            mark_draft_published, draft_id, result.x_tweet_id,
        )
        await workflow.execute_activity(
            save_generation_memory, draft,
        )
        await workflow.execute_activity(notify_publish_success, draft.user_id, draft_id)

        # Schedule metric collection
        await workflow.start_child_workflow(
            MetricsCollectionWorkflow.run,
            draft_id,
            id=f"metrics-{draft_id}",
            task_queue="analytics-tq",
        )

        return result
```

## 7. PublishTickWorkflow

Runs every minute. Checks Redis sorted set for due publishes.

```python
@workflow.defn
class PublishTickWorkflow:
    @workflow.run
    async def run(self) -> None:
        due_drafts = await workflow.execute_activity(
            get_due_drafts, datetime.utcnow(),
            start_to_close_timeout=timedelta(seconds=30),
        )
        for draft_id in due_drafts:
            await workflow.start_child_workflow(
                PublishWorkflow.run,
                draft_id,
                id=f"publish-{draft_id}-{int(time.time())}",
                task_queue="publish-tq",
                parent_close_policy=ParentClosePolicy.ABANDON,
            )
```

## 8. MetricsCollectionWorkflow

```python
@workflow.defn
class MetricsCollectionWorkflow:
    @workflow.run
    async def run(self, draft_id: str) -> None:
        # Collect at 1h, 6h, 24h, 7d after publish
        for delay_hours in [1, 6, 24, 168]:
            await workflow.sleep(timedelta(hours=delay_hours))
            await workflow.execute_activity(
                fetch_and_store_metrics, draft_id,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(maximum_attempts=5),
            )
```

## 9. WeeklyLearningWorkflow

```python
@workflow.defn
class WeeklyLearningWorkflow:
    @workflow.run
    async def run(self, user_id: str) -> LearningResult:
        analytics = await workflow.execute_activity(
            aggregate_weekly_analytics, user_id,
        )
        learnings = await workflow.execute_activity(
            learning_agent, user_id, analytics,
            start_to_close_timeout=timedelta(minutes=10),
        )
        await workflow.execute_activity(
            apply_learned_weights, user_id, learnings,
        )
        await workflow.execute_activity(
            store_memory_entries, user_id, learnings.memory_entries,
        )
        return learnings
```

## Retry & Timeout Policy

| Activity Type | Timeout | Max Retries | Backoff |
|---------------|---------|-------------|---------|
| HTTP fetch (sources) | 5 min | 3 | exponential 2^n |
| OpenAI generation | 3 min | 2 | 5s, 15s |
| OpenAI scoring | 1 min | 3 | 2s, 5s |
| X API publish | 2 min | 3 | respect rate limit reset |
| DB operations | 30s | 5 | 1s |

## Idempotency

- Workflow IDs: `{workflow-type}-{resource-id}` for user-triggered
- Publish: `idempotency_key` on draft, checked before X API call
- Plans: unique constraint on `(user_id, plan_date)`

## Signals & Queries

### GenerationWorkflow

- **Signal `cancel`:** Abort generation, mark draft failed
- **Query `status`:** Return current pipeline stage

### PublishWorkflow

- **Signal `cancel_schedule`:** Remove from queue (user unschedules)

## Local Development

```yaml
# docker-compose.yml temporal section
temporal:
  image: temporalio/auto-setup:latest
  ports:
    - "7233:7233"
    - "8233:8233"  # Web UI
```

Workers run as single process in dev, separate pools in prod.
