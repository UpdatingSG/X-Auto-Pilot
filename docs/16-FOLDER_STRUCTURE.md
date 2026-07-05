# Folder Structure

Monorepo using Turborepo for frontend + Python backend packages.

```
x-autopilot/
├── README.md
├── docker-compose.yml              # Local dev: PG, Redis, Temporal, all services
├── docker-compose.prod.yml
├── turbo.json
├── .github/
│   └── workflows/
│       ├── ci.yml                  # Lint, test, build
│       ├── deploy-staging.yml
│       └── deploy-prod.yml
│
├── apps/
│   ├── web/                        # Next.js 15 frontend
│   │   ├── package.json
│   │   ├── next.config.ts
│   │   ├── tailwind.config.ts
│   │   ├── tsconfig.json
│   │   ├── public/
│   │   └── src/
│   │       ├── app/                # App Router
│   │       │   ├── layout.tsx
│   │       │   ├── page.tsx        # Dashboard
│   │       │   ├── (auth)/
│   │       │   │   ├── login/
│   │       │   │   └── register/
│   │       │   ├── dashboard/
│   │       │   │   ├── page.tsx
│   │       │   │   ├── drafts/
│   │       │   │   ├── plan/
│   │       │   │   ├── analytics/
│   │       │   │   └── schedule/
│   │       │   ├── settings/
│   │       │   │   ├── profile/    # Voice profile editor
│   │       │   │   ├── sources/
│   │       │   │   ├── x-account/
│   │       │   │   └── schedule/
│   │       │   └── api/            # BFF routes if needed
│   │       ├── components/
│   │       │   ├── ui/             # shadcn/ui primitives
│   │       │   ├── drafts/
│   │       │   ├── analytics/
│   │       │   ├── plan/
│   │       │   └── layout/
│   │       ├── hooks/
│   │       │   ├── use-drafts.ts
│   │       │   ├── use-websocket.ts
│   │       │   └── use-analytics.ts
│   │       ├── lib/
│   │       │   ├── api-client.ts
│   │       │   └── utils.ts
│   │       └── types/
│   │           └── api.ts          # Generated from OpenAPI
│   │
│   └── api/                        # FastAPI backend
│       ├── pyproject.toml
│       ├── alembic.ini
│       ├── alembic/
│       │   └── versions/
│       └── src/
│           └── xautopilot/
│               ├── main.py
│               ├── config.py
│               ├── dependencies.py
│               ├── routers/
│               │   ├── auth.py
│               │   ├── profile.py
│               │   ├── sources.py
│               │   ├── plans.py
│               │   ├── drafts.py
│               │   ├── publish.py
│               │   ├── analytics.py
│               │   ├── research.py
│               │   └── websocket.py
│               ├── models/         # SQLAlchemy models
│               │   ├── user.py
│               │   ├── voice_profile.py
│               │   ├── knowledge.py
│               │   ├── content.py
│               │   └── analytics.py
│               ├── schemas/        # Pydantic request/response
│               ├── services/
│               │   ├── auth_service.py
│               │   ├── draft_service.py
│               │   ├── schedule_service.py
│               │   └── analytics_service.py
│               └── middleware/
│                   ├── rate_limit.py
│                   └── auth.py
│
├── workers/                        # Temporal workers
│   ├── pyproject.toml
│   └── src/
│       └── xautopilot_workers/
│           ├── main.py             # Worker entrypoint (all pools)
│           ├── workflows/
│           │   ├── ingestion.py
│           │   ├── research.py
│           │   ├── planning.py
│           │   ├── generation.py
│           │   ├── publish.py
│           │   └── analytics.py
│           ├── activities/
│           │   ├── fetch_sources.py
│           │   ├── embed.py
│           │   ├── rag.py
│           │   ├── agents.py       # LLM agent calls
│           │   ├── publish_x.py
│           │   └── metrics.py
│           └── schedules.py        # Temporal schedule definitions
│
├── packages/
│   ├── ai/                         # AI/LLM package (shared)
│   │   ├── pyproject.toml
│   │   └── src/
│   │       └── xautopilot_ai/
│   │           ├── agents/
│   │           │   ├── base.py
│   │           │   ├── tweet_writer.py
│   │           │   ├── thread_writer.py
│   │           │   ├── reply_agent.py
│   │           │   ├── fact_checker.py
│   │           │   ├── quality_reviewer.py
│   │           │   ├── humanizer.py
│   │           │   ├── content_planner.py
│   │           │   ├── research_agent.py
│   │           │   └── learning_agent.py
│   │           ├── prompts/
│   │           │   ├── tweet_writer/v1.1.0.yaml
│   │           │   ├── thread_writer/v1.0.0.yaml
│   │           │   └── ...
│   │           ├── rag/
│   │           │   ├── chunker.py
│   │           │   ├── embedder.py
│   │           │   ├── retriever.py
│   │           │   └── reranker.py
│   │           ├── guardrails/
│   │           │   ├── banned_phrases.py
│   │           │   ├── char_limit.py
│   │           │   └── duplicate_check.py
│   │           ├── llm/
│   │           │   ├── client.py
│   │           │   ├── router.py
│   │           │   └── cost_tracker.py
│   │           └── eval/
│   │               ├── golden_set.json
│   │               └── run_eval.py
│   │
│   ├── shared-python/              # Shared Python utilities
│   │   └── src/
│   │       └── xautopilot_shared/
│   │           ├── db.py
│   │           ├── redis.py
│   │           ├── crypto.py
│   │           └── x_client.py
│   │
│   └── shared-types/               # Shared TypeScript types
│       ├── package.json
│       └── src/
│           └── index.ts
│
├── infra/
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── modules/
│   │   │   ├── ecs/
│   │   │   ├── rds/
│   │   │   ├── redis/
│   │   │   └── networking/
│   │   └── environments/
│   │       ├── staging/
│   │       └── prod/
│   └── docker/
│       ├── Dockerfile.api
│       ├── Dockerfile.web
│       ├── Dockerfile.workers
│       └── Dockerfile.temporal
│
├── scripts/
│   ├── seed_dev_data.py
│   ├── generate_openapi_types.sh
│   └── run_migrations.sh
│
├── docs/                           # Design documents (this folder)
│   ├── 01-PRD.md
│   └── ...
│
└── tests/
    ├── api/
    │   ├── test_auth.py
    │   ├── test_drafts.py
    │   └── test_profile.py
    ├── workers/
    │   ├── test_generation_workflow.py
    │   └── test_publish_workflow.py
    ├── ai/
    │   ├── test_agents.py
    │   ├── test_rag.py
    │   └── test_guardrails.py
    └── e2e/
        └── test_full_pipeline.py
```

## Package Boundaries

| Package | Depends On | Consumed By |
|---------|-----------|-------------|
| `apps/web` | shared-types | — |
| `apps/api` | shared-python, ai | — |
| `workers` | shared-python, ai | — |
| `ai` | shared-python | api, workers |
| `shared-python` | — | api, workers, ai |

## Key Conventions

- **Python:** `src` layout, `pyproject.toml` per package, `ruff` + `mypy`
- **TypeScript:** strict mode, `eslint` + `prettier`
- **Imports:** `from xautopilot_ai.agents import TweetWriter`
- **Env:** `.env.local` per app, never committed
- **Migrations:** Alembic in `apps/api`, run via `scripts/run_migrations.sh`
- **API types:** `openapi-typescript` generates `apps/web/src/types/api.ts`

## Docker Compose Services (Local)

```yaml
services:
  postgres:     # PG 16 + pgvector
  redis:        # Redis 7
  temporal:     # Temporal server + UI
  api:          # FastAPI (hot reload)
  workers:      # Temporal workers
  web:          # Next.js dev server
```

Single command: `docker compose up` → full stack running.
