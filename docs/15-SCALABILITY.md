# Scalability Plan

## Scale Stages

| Stage | Users | Posts/Day | Architecture |
|-------|-------|-----------|--------------|
| MVP | 1 | ~20 | Single ECS cluster, RDS medium |
| Alpha | 10–50 | 200 | Separate worker pools, read replica |
| Beta | 50–500 | 2K | Multi-AZ, ElastiCache cluster, Qdrant |
| SaaS GA | 500–5K | 20K | EKS, sharded workers, CDN |
| Scale | 5K–50K | 200K | Multi-region, dedicated vector DB |

## Bottleneck Analysis

| Component | First Bottleneck | Scale Strategy |
|-----------|-----------------|----------------|
| OpenAI API | Rate limits + cost | Queue, cache, model routing, enterprise agreement |
| PostgreSQL | Write throughput, vector search | Read replicas, connection pooling, Qdrant migration |
| Temporal | Workflow history size | Archival, separate namespaces per tier |
| X API | Per-user rate limits | Per-user queues (already isolated) |
| Redis | Memory | Cluster mode, separate instances per concern |
| Workers | CPU for embedding | Horizontal scaling, GPU for local models |

## Database Scaling

### Phase 1: Single RDS (MVP — 50 users)

- `db.t4g.medium` (2 vCPU, 4GB)
- pgvector HNSW indexes
- PgBouncer connection pooling (max 100 connections)

### Phase 2: Read Replica (50–500 users)

```
Primary (writes) → Replica (analytics queries, dashboard)
```

- Materialized views on replica
- Analytics API reads from replica only

### Phase 3: Vector Migration (500+ users)

Move embeddings to Qdrant:

```
PostgreSQL: relational data, metadata
Qdrant: knowledge_chunks, generation_memory embeddings
```

Dual-write during migration, feature flag for read path.

### Phase 4: Sharding (5K+ users)

Shard by `user_id` hash. Each shard: dedicated PG + Qdrant collection.

```
Router → shard_0, shard_1, ..., shard_N
```

## Worker Scaling

### Task Queue Isolation

Separate worker pools prevent generation from blocking publishing:

```yaml
# ECS services
workers-ingestion:
  desired_count: 2
  task_queue: ingestion-tq

workers-generation:
  desired_count: 5   # scale on queue depth
  task_queue: generation-tq

workers-publish:
  desired_count: 2
  task_queue: publish-tq
```

### Auto-Scaling Policy

```yaml
# CloudWatch alarm → ECS scale
metric: TemporalTaskQueueBacklog
threshold: > 100 tasks
action: +2 generation workers
cooldown: 300s
```

### Worker Resource Sizing

| Pool | vCPU | Memory | Notes |
|------|------|--------|-------|
| ingestion | 0.5 | 1GB | I/O bound |
| generation | 1 | 2GB | LLM API calls, CPU for JSON parsing |
| publish | 0.5 | 1GB | I/O bound |
| analytics | 0.5 | 1GB | Batch queries |

## Caching Strategy at Scale

| Layer | Technology | What |
|-------|-----------|------|
| CDN | CloudFront | Static assets, Next.js pages |
| API | Redis | Session, rate limits, quotas |
| Generation | Redis | 24h result cache by content hash |
| Embeddings | Redis | 7d embedding cache |
| DB | Materialized views | Analytics aggregates |
| LLM | Prompt caching (OpenAI) | System prompts with voice profile |

## Multi-Tenancy (SaaS)

### Data Isolation

```python
# Middleware sets tenant context
@app.middleware("http")
async def tenant_middleware(request, call_next):
    user = await authenticate(request)
    set_tenant_context(user.id)
    return await call_next(request)
```

PostgreSQL RLS on all tenant tables.

### Resource Fairness

```python
# Per-tenant concurrency limits
MAX_CONCURRENT_GENERATIONS = {
    "free": 1,
    "pro": 3,
    "enterprise": 10,
}
```

Temporal task queue per tier (priority queues):

```
generation-tq-enterprise  # processed first
generation-tq-pro
generation-tq-free
```

## Geographic Scaling

### Phase 1: Single Region (us-east-1)

All services in one region. Users globally — latency acceptable for async workflows.

### Phase 2: Multi-Region Read (1K+ users)

- CloudFront for frontend globally
- API in primary region
- Read replica in eu-west-1 for EU users' dashboard

### Phase 3: Multi-Region Write (10K+ users)

- Regional API endpoints
- User data pinned to region (GDPR)
- Cross-region Temporal namespaces
- Global Redis with region-local caches

## LLM Scaling

### Model Routing

```python
def select_model(task: str, user_tier: str) -> str:
    if task == "scoring" or task == "summarization":
        return "gpt-5.5-mini"
    if user_tier == "free":
        return "gpt-5.5-mini"  # cheaper tier
    return "gpt-5.5"
```

### Self-Hosted Models (10K+ users)

| Task | Model | Deployment |
|------|-------|------------|
| Embeddings | bge-small-en | GPU instance (g4dn.xlarge) |
| Scoring/rerank | cross-encoder/ms-marco | Same GPU |
| Generation | Keep OpenAI | Quality critical |

Saves ~60% on embedding costs.

### Request Queuing

```python
# Priority queue for generation requests
class GenerationQueue:
    async def enqueue(self, request, priority: int):
        await redis.zadd("gen:queue", {request.id: priority})

    async def dequeue(self):
        # Highest priority first
        return await redis.zpopmax("gen:queue")
```

## Observability at Scale

| Tool | Purpose |
|------|---------|
| Datadog / CloudWatch | Metrics, alerts |
| Temporal UI | Workflow debugging |
| Sentry | Error tracking |
| Structured logging (JSON) | Correlation IDs across services |
| OpenTelemetry | Distributed tracing |

Key dashboards:
- Generation latency p50/p95/p99
- Publish success rate
- LLM cost per hour
- Queue depth per task queue
- API error rate

## Disaster Recovery

| Scenario | RTO | RPO | Strategy |
|----------|-----|-----|----------|
| RDS failure | 30 min | 5 min | Multi-AZ, automated failover |
| Region outage | 4 hours | 1 hour | Cross-region snapshot restore |
| Temporal failure | 15 min | 0 | Workflows durable, replay on recovery |
| OpenAI outage | N/A | N/A | Queue requests, fallback to mini model |

## Load Testing Targets

Before each scale stage:

```bash
# k6 load test
k6 run --vus 100 --duration 10m tests/load/api.js
```

| Stage | Target |
|-------|--------|
| Alpha | 50 concurrent API requests, p95 < 1s |
| Beta | 500 concurrent, 50 concurrent generations |
| GA | 5000 concurrent API, 500 generations |

## Cost at Scale

See [Cost Estimation](14-COST_ESTIMATION.md). Key lever: LLM cost dominates at >100 users. Self-hosted embeddings + aggressive caching essential for margins.
