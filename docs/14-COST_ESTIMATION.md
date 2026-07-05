# Cost Estimation

Estimates for **single personal user** at MVP cadence, then SaaS projections.

## MVP Usage Profile (Personal)

| Activity | Volume/Day | Volume/Month |
|----------|-----------|--------------|
| Tweets generated | 3 (+ 4 variants each) | 90 |
| Threads generated | ~0.3 (2/week) | 8 |
| Replies generated | 15 | 450 |
| Daily content plan | 1 | 30 |
| Research runs | 6 (every 4h) | 180 |
| Ingestion items | ~200 new/day | 6,000 |
| Analytics syncs | 4 | 120 |
| Weekly learning | — | 4 |

## OpenAI Costs

Model pricing (estimated July 2026 — adjust when billing page updates):

| Model | Input / 1M tokens | Output / 1M tokens |
|-------|-------------------|---------------------|
| gpt-5.5 | $5.00 | $15.00 |
| gpt-5.5-mini | $0.50 | $1.50 |
| text-embedding-3-small | $0.02 | — |

### Monthly Token Breakdown (Personal)

| Operation | Calls/mo | Avg Input | Avg Output | Model | Cost |
|-----------|----------|-----------|------------|-------|------|
| Tweet generation | 360 | 3,000 | 800 | gpt-5.5 | ~$8.50 |
| Thread generation | 24 | 5,000 | 2,500 | gpt-5.5 | ~$1.50 |
| Reply generation | 450 | 2,500 | 400 | gpt-5.5 | ~$8.00 |
| Content planning | 30 | 8,000 | 2,000 | gpt-5.5 | ~$2.50 |
| Research clustering | 180 | 10,000 | 3,000 | gpt-5.5 | ~$15.00 |
| Quality scoring | 1,000 | 1,500 | 200 | gpt-5.5-mini | ~$1.20 |
| Fact checking | 900 | 2,000 | 300 | gpt-5.5 | ~$12.00 |
| Humanization | 500 | 500 | 300 | gpt-5.5-mini | ~$0.50 |
| Summarization (ingest) | 6,000 | 1,500 | 200 | gpt-5.5-mini | ~$6.00 |
| Weekly learning | 4 | 15,000 | 2,000 | gpt-5.5 | ~$0.50 |
| Embeddings | 6,000 chunks | 500 | — | embed-3-small | ~$0.06 |

**OpenAI Total: ~$56/month (personal)**

With caching (24h generation cache, embedding cache): **~$40/month**

## Infrastructure Costs (AWS MVP)

| Service | Spec | Monthly |
|---------|------|---------|
| ECS Fargate (API) | 0.5 vCPU, 1GB × 1 | $15 |
| ECS Fargate (Workers) | 1 vCPU, 2GB × 2 | $60 |
| ECS Fargate (Web) | 0.25 vCPU, 0.5GB × 1 | $8 |
| RDS PostgreSQL | db.t4g.medium, 50GB | $55 |
| ElastiCache Redis | cache.t4g.micro | $12 |
| Temporal Cloud (or self-hosted) | Dev tier / 1 EC2 | $25–100 |
| ALB | 1 load balancer | $20 |
| S3 | <10GB | $1 |
| Secrets Manager | 5 secrets | $2 |
| CloudWatch | Logs + metrics | $10 |
| Route 53 | 1 hosted zone | $1 |

**Infrastructure Total: ~$210–285/month**

Self-hosted Temporal on same ECS cluster: ~$210/month.
Temporal Cloud Essentials: adds ~$100/month but saves ops.

## X API Costs

| Tier | Price | Limits |
|------|-------|--------|
| Free | $0 | Very limited — not viable |
| Basic | $100/mo | 3K tweets/mo read, limited post |
| Pro | $5,000/mo | Full analytics |

**MVP recommendation:** Basic ($100/mo) for publishing. Organic metrics only.

If impressions data required: Pro tier or accept limited analytics in MVP.

## Total MVP Cost (Personal Use)

| Category | Low | High |
|----------|-----|------|
| OpenAI | $40 | $60 |
| AWS Infrastructure | $210 | $285 |
| X API Basic | $100 | $100 |
| Domain + email | $2 | $5 |
| **Total** | **~$352** | **~$450/month** |

## Cost Optimization Strategies

1. **Batch embeddings** — 100 per API call
2. **Cache generation results** — identical ideas within 24h
3. **gpt-5.5-mini for scoring/summarization** — already planned
4. **Skip research LLM when <5 new items** — rule-based clustering
5. **Reserved RDS instances** — 30% savings after 3 months
6. **Fargate Spot for workers** — 70% savings (interruptible OK for Temporal)
7. **Local dev** — Docker Compose, no cloud cost for development

## SaaS Projections (1,000 Users)

Assumptions: avg 2 tweets/day, 1 thread/week, 10 replies/day per user.

| Category | Monthly Cost |
|----------|-------------|
| OpenAI (1K users, with caching) | $25,000–35,000 |
| AWS (scaled) | $3,000–5,000 |
| X API (per-user OAuth — no platform cost) | $0 |
| Temporal Cloud | $500–1,000 |
| **Total COGS** | **~$30,000–40,000** |

At $49/month average: $49,000 revenue → **~20–40% gross margin**.

Margin improvements at scale:
- Volume discounts on OpenAI (enterprise agreement)
- Dedicated embedding model (self-hosted)
- Qdrant vs RDS for vectors (cheaper at scale)

## Unit Economics Target (SaaS)

| Metric | Target |
|--------|--------|
| COGS per user | < $25/month |
| Price per user | $49–99/month |
| Gross margin | > 50% |
| LLM cost per user | < $20/month |

## Monitoring Cost

```python
# Track per-request
generation_metadata = {
    "input_tokens": 3200,
    "output_tokens": 750,
    "model": "gpt-5.5",
    "estimated_cost_usd": 0.027
}
```

Dashboard alert if daily spend > $5 (personal) or per-user > $2 (SaaS).

## Break-Even (SaaS)

Fixed costs ~$5K/month (infra + 1 engineer part-time):

- At $49/user, 50% margin → need ~200 paying users to cover fixed + variable
