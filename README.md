# X-Autopilot

AI-powered Twitter/X content creation and automation platform. Acts as a personal content team — researching, planning, writing, scheduling, publishing, and learning from engagement.

## Design Documents

| # | Document | Description |
|---|----------|-------------|
| 1 | [PRD](docs/01-PRD.md) | Product Requirements Document |
| 2 | [Architecture](docs/02-ARCHITECTURE.md) | High-Level System Architecture |
| 3 | [Database Schema](docs/03-DATABASE_SCHEMA.md) | PostgreSQL + pgvector schema |
| 4 | [API Design](docs/04-API_DESIGN.md) | REST API specification |
| 5 | [AI Agents](docs/05-AI_AGENTS.md) | Multi-agent architecture |
| 6 | [Temporal Workflows](docs/06-TEMPORAL_WORKFLOWS.md) | Workflow orchestration |
| 7 | [Prompt Strategy](docs/07-PROMPT_STRATEGY.md) | Prompt engineering |
| 8 | [RAG Pipeline](docs/08-RAG_PIPELINE.md) | Retrieval-augmented generation |
| 9 | [Scheduling](docs/09-SCHEDULING.md) | Human-like scheduling |
| 10 | [Publishing](docs/10-PUBLISHING.md) | Publishing pipeline |
| 11 | [Analytics](docs/11-ANALYTICS.md) | Analytics pipeline |
| 12 | [Feedback Loop](docs/12-FEEDBACK_LOOP.md) | Learning from engagement |
| 13 | [Security](docs/13-SECURITY.md) | Security & rate limiting |
| 14 | [Cost Estimation](docs/14-COST_ESTIMATION.md) | Monthly cost projections |
| 15 | [Scalability](docs/15-SCALABILITY.md) | Scale to SaaS |
| 16 | [Folder Structure](docs/16-FOLDER_STRUCTURE.md) | Monorepo layout |
| 17 | [Tech Stack](docs/17-TECH_STACK.md) | Stack justification |
| 18 | [Roadmap](docs/18-ROADMAP.md) | Implementation milestones |

## MVP Scope

- User profile configuration
- AI tweet & thread generation
- Daily content planning
- Scheduler with draft approval
- Analytics dashboard
- Engagement-based learning

## Milestone 1 Status ✅

- [x] FastAPI + health check
- [x] User registration & login (JWT)
- [x] Protected `/v1/auth/me`
- [x] Next.js auth UI + dashboard shell
- [x] Docker Compose, Alembic, CI
- [x] 7 integration tests

See [M1 TDD Walkthrough](docs/M1-TDD-WALKTHROUGH.md).

## Milestone 2 Status ✅

- [x] Voice profile (versioned) API + UI
- [x] Knowledge sources CRUD API + UI
- [x] RSS ingestion with deduplication
- [x] 16 integration tests (9 new)
- [x] Migration `0002`

See [M2 TDD Walkthrough](docs/M2-TDD-WALKTHROUGH.md).

## Milestone 3 Status ✅

- [x] Content Planner agent + daily plan API
- [x] Tweet Writer agent (3 scored variants)
- [x] Idea approval flow
- [x] Draft generation + approval
- [x] Plan & Drafts UI
- [x] 24 integration tests
- [x] Migration `0003`

See [M3 TDD Walkthrough](docs/M3-TDD-WALKTHROUGH.md).

## Milestone 4 Status ✅

- [x] Schedule config API (posting windows, jitter, quotas)
- [x] Slot allocator (human-like times, collision avoidance)
- [x] Schedule / cancel approved drafts
- [x] Publish queue API
- [x] Schedule settings + Publish queue UI
- [x] 30 integration tests
- [x] Migration `0004`

See [M4 TDD Walkthrough](docs/M4-TDD-WALKTHROUGH.md).

## Milestone 5 Status ✅

- [x] X account connection API (mock mode for dev/TDD)
- [x] Token encryption (Fernet / AES)
- [x] X client boundary (Mock + Live)
- [x] Publish draft to X (`POST /v1/publish/{id}`)
- [x] Published history + idempotency
- [x] X Account, Publish now, History UI
- [x] 36 integration tests
- [x] Migration `0005`

See [M5 TDD Walkthrough](docs/M5-TDD-WALKTHROUGH.md).

## Milestone 6 Status ✅

- [x] Post metrics storage (time-series snapshots)
- [x] X metrics sync API (mock + live client)
- [x] Analytics overview, post leaderboard, insights
- [x] Engagement rate calculation
- [x] Analytics dashboard UI
- [x] 41 integration tests
- [x] Migration `0006`

See [M6 TDD Walkthrough](docs/M6-TDD-WALKTHROUGH.md).

## Deploy to production

See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for the full guide.

**Fastest path (Render):**
1. Push to GitHub
2. [Render](https://render.com) → New → Blueprint → connect repo
3. Set env vars (`TOKEN_ENCRYPTION_KEY`, X OAuth, `OPENAI_API_KEY`, `NEXT_PUBLIC_API_URL`)
4. Update X Developer Portal callback to your live URL

**VPS path:**
```bash
cp .env.production.example .env.production   # fill in secrets + domains
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

## Quick Start (local dev)

```bash
# One-time setup: start DB + run migrations
./scripts/setup.sh

# Terminal 1 — API
cd apps/api && source .venv/bin/activate && uvicorn xautopilot.main:app --reload

# Terminal 2 — Web
cd apps/web && npm run dev
```

Open http://localhost:3000

> **If register/login returns 500:** the `users` table is missing. Run `cd apps/api && alembic upgrade head`

- **Frontend:** Next.js 15, React, Tailwind CSS
- **Backend:** FastAPI, PostgreSQL, Redis, Temporal
- **AI:** OpenAI GPT-5.5, pgvector, RAG
- **Infra:** Docker, AWS (EKS future)
