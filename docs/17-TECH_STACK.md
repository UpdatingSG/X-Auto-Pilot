# Tech Stack Justification

## Decision Summary

| Layer | Choice | Alternatives Considered |
|-------|--------|------------------------|
| Frontend | Next.js 15 + React + Tailwind | Remix, SvelteKit |
| Backend | FastAPI | NestJS, Django |
| Database | PostgreSQL 16 + pgvector | MongoDB, separate Qdrant |
| Cache/Queue | Redis 7 | Memcached, RabbitMQ |
| Orchestration | Temporal | Celery, Airflow, Inngest |
| LLM | OpenAI GPT-5.5 | Anthropic Claude, local Llama |
| Embeddings | text-embedding-3-small | Cohere, self-hosted bge |
| Infra | Docker + AWS ECS | Kubernetes, Railway, Fly.io |
| Monorepo | Turborepo | Nx, separate repos |

---

## Frontend: Next.js 15 + React + Tailwind

### Why Next.js

- **App Router** — server components for dashboard data fetching, client components for interactive draft approval
- **API routes** — optional BFF layer for WebSocket proxy
- **SSR/SSG** — fast dashboard loads, SEO irrelevant but performance matters
- **Ecosystem** — largest React framework ecosystem, shadcn/ui compatibility
- **Deployment** — Vercel or ECS with standalone output

### Why Tailwind + shadcn/ui

- Rapid UI development for dashboard, settings forms, analytics charts
- Consistent design system without custom CSS overhead
- shadcn/ui: accessible, customizable components (not a dependency — copy-paste)

### Why Not Remix/SvelteKit

- Remix: smaller ecosystem for chart/dashboard components
- SvelteKit: team familiarity with React, larger hiring pool for SaaS

---

## Backend: FastAPI

### Why FastAPI

- **Python AI ecosystem** — OpenAI SDK, LangChain, sentence-transformers, numpy all Python-native
- **Single language** — API + workers + AI agents in one language, shared packages
- **Performance** — async/await, comparable to Node for I/O-bound API
- **Auto OpenAPI** — generates spec for frontend type generation
- **Pydantic** — shared validation between API schemas and agent outputs
- **Type hints** — mypy for static analysis

### Why Not NestJS

- Would require separate Python service for AI anyway (or inferior Node LLM libraries)
- Two languages = two deploy artifacts, harder shared types
- NestJS excels at enterprise CRUD but AI pipeline is the core product

### Why Not Django

- Heavier ORM opinions, less natural async support
- FastAPI's lightweight approach better for API-first + worker architecture

---

## Database: PostgreSQL + pgvector

### Why PostgreSQL

- **Relational integrity** — complex relationships (plans → ideas → drafts → variants → posts → metrics)
- **JSONB** — flexible voice profile, schedule config without schema migrations
- **Mature** — RDS managed, read replicas, point-in-time recovery
- **Full-text search** — backup for keyword retrieval alongside vectors

### Why pgvector (over Qdrant) for MVP

- **Single database** — one connection pool, one backup, one migration tool
- **Sufficient scale** — handles <10M vectors with HNSW indexes
- **ACID** — embed and store metadata in same transaction
- **Cost** — no additional service to manage

### Migration Path to Qdrant

At 500+ users or >5M vectors: dual-write to Qdrant, feature-flag read path. Schema designed for portability (chunk IDs consistent).

---

## Cache: Redis

### Why Redis

- **Sorted sets** — publish queue with timestamp scores
- **Rate limiting** — sliding window counters
- **Pub/sub** — real-time draft notifications to WebSocket
- **TTL caches** — generation results, embeddings, sessions
- **Quota tracking** — daily tweet/reply counters

### Why Not RabbitMQ

- Don't need complex routing — Temporal handles job orchestration
- Redis covers caching + lightweight queuing needs

---

## Orchestration: Temporal

### Why Temporal

- **Durable execution** — AI pipelines run 30s–5min, survive crashes
- **Built-in retries** — OpenAI/X API transient failures with configurable backoff
- **Visibility** — debug failed generations in Temporal Web UI
- **Schedules** — cron for ingestion (every 4h), planning (daily), analytics (weekly)
- **Saga pattern** — thread publish partial failure recovery
- **Child workflows** — fan-out ingestion per source, per user

### Why Not Celery

- No built-in workflow state — chaining tasks requires custom orchestration
- Harder to debug multi-step failures
- Temporal's workflow history enables replay and audit

### Why Not Airflow

- Designed for batch data pipelines, not real-time API-triggered workflows
- Heavier operational overhead

### Why Not Inngest

- Less mature for complex saga patterns
- Temporal has stronger self-hosted option for cost control

---

## AI: OpenAI GPT-5.5

### Why OpenAI

- **Quality** — best-in-class for nuanced, human-like text generation
- **Structured outputs** — JSON mode with schema validation
- **Embeddings** — text-embedding-3-small is cost-effective
- **Prompt caching** — system prompts with voice profile cached
- **Reliability** — highest uptime among LLM providers

### Model Routing

- **gpt-5.5** — generation (tweets, threads, replies) where quality is critical
- **gpt-5.5-mini** — scoring, summarization, humanization where speed/cost matters

### Why Not Anthropic Claude

- Equally capable but OpenAI embeddings + generation in one provider simplifies billing
- Re-evaluate if Claude shows significant quality advantage for Twitter voice

### Why Not Local Models (MVP)

- Quality gap too large for "doesn't feel AI-generated" requirement
- Self-hosted embeddings planned at scale (see Scalability)

---

## Infrastructure: Docker + AWS ECS

### Why Docker

- Reproducible dev environment via docker-compose
- Same images dev → staging → prod

### Why AWS ECS (over Kubernetes)

- **MVP simplicity** — Fargate removes node management
- **AWS ecosystem** — RDS, ElastiCache, Secrets Manager, ALB integrate natively
- **Cost** — no control plane fee (unlike EKS $75/mo)
- **Scale path** — migrate to EKS at 5K+ users if needed

### Why Not Railway/Fly.io

- Fine for MVP prototyping but limited control for Temporal, RDS, compliance
- AWS better for SaaS compliance (GDPR, SOC2 path)

---

## Monorepo: Turborepo

### Why Monorepo

- Shared types between frontend and backend (OpenAPI generation)
- Shared AI package between API and workers
- Atomic commits across full stack
- Single CI pipeline

### Why Turborepo

- Simpler than Nx for Python + Node mixed repos
- Remote caching for CI speed
- Task orchestration (build web → deploy)

---

## Supporting Libraries

| Purpose | Library | Why |
|---------|---------|-----|
| ORM | SQLAlchemy 2.0 + asyncpg | Async, mature, Alembic migrations |
| Migrations | Alembic | Standard for SQLAlchemy |
| X API | tweepy or httpx | v2 API support |
| RSS | feedparser | Battle-tested |
| HTML strip | bleach | XSS prevention on ingest |
| Charts | Recharts | React-native, composable |
| Auth UI | NextAuth.js or custom JWT | Flexibility |
| Temporal SDK | temporalio (Python) | Official SDK |
| Testing | pytest + vitest | Standard per language |
| Linting | ruff + eslint | Fast Python linter |

---

## What We'd Revisit at SaaS Scale

| Component | Current | At Scale |
|-----------|---------|----------|
| Vector DB | pgvector | Qdrant |
| Orchestration | Self-hosted Temporal | Temporal Cloud |
| Compute | ECS Fargate | EKS with Karpenter |
| Embeddings | OpenAI API | Self-hosted bge-small |
| CDN | None | CloudFront |
| Auth | Custom JWT | Auth0 / Clerk |
| Payments | None | Stripe |
| Email | None | Resend / SES |
