# Implementation Roadmap

## Overview

16-week roadmap from zero to production MVP, structured in 6 milestones. Each milestone delivers usable functionality.

```
M1: Foundation     ████░░░░░░░░░░░░  Weeks 1-2
M2: Profile+Ingest ████████░░░░░░░░  Weeks 3-4
M3: AI Generation  ████████████░░░░  Weeks 5-8
M4: Scheduler      ██████████████░░  Weeks 9-10
M5: Publish        ████████████████  Weeks 11-13
M6: Analytics      ████████████████  Weeks 14-16
```

---

## Milestone 1: Foundation (Weeks 1–2)

**Goal:** Runnable local dev environment, auth, basic API skeleton.

### Week 1

- [ ] Initialize monorepo (Turborepo, apps/web, apps/api, packages/)
- [ ] Docker Compose: PostgreSQL + pgvector, Redis, Temporal
- [ ] FastAPI skeleton with health check, CORS, OpenAPI
- [ ] Next.js skeleton with Tailwind + shadcn/ui
- [ ] SQLAlchemy models: users, voice_profiles
- [ ] Alembic migration: initial schema
- [ ] Auth: register, login, JWT issue/refresh
- [ ] CI: lint (ruff, eslint), test, build

### Week 2

- [ ] Temporal worker skeleton (connect, register workflows)
- [ ] Shared packages: db, redis, crypto utilities
- [ ] API client in frontend (typed fetch wrapper)
- [ ] Basic layout: sidebar nav, auth pages
- [ ] Settings page shell
- [ ] Deploy staging: ECS + RDS (Terraform skeleton)

**Deliverable:** User can register, login, see empty dashboard.

---

## Milestone 2: Profile & Ingestion (Weeks 3–4)

**Goal:** Voice profile configuration and knowledge ingestion pipeline.

### Week 3

- [ ] Voice profile CRUD API + UI form
  - Interests, tone, style, vocabulary, never_discuss
  - Version history, activate version
- [ ] Knowledge sources CRUD API + UI
  - RSS, Hacker News, Reddit, Dev.to, manual notes
- [ ] Ingestion activities: fetch RSS, fetch HN, normalize
- [ ] Deduplication logic (external_id + semantic)
- [ ] `IngestionWorkflow` + `IngestionOrchestratorWorkflow`
- [ ] Temporal schedule: ingest every 4 hours

### Week 4

- [ ] Chunking pipeline (512 tokens, overlap 64)
- [ ] Embedding pipeline (text-embedding-3-small, batch)
- [ ] `knowledge_items` + `knowledge_chunks` storage
- [ ] `ResearchWorkflow`: cluster + extract insights
- [ ] Research clusters API + UI (view recent clusters)
- [ ] Source fetch manual trigger button
- [ ] Ingestion status dashboard (last run, items count)

**Deliverable:** User configures profile, adds sources, sees ingested knowledge and research clusters.

---

## Milestone 3: AI Content Generation (Weeks 5–8)

**Goal:** Full content planning and generation pipeline with draft approval.

### Week 5

- [ ] `packages/ai` setup: LLM client, prompt loader, cost tracker
- [ ] Prompt templates v1: tweet_writer, content_planner
- [ ] RAG retriever: hybrid search + rerank
- [ ] Content Planner agent + activity
- [ ] `DailyPlanningWorkflow` + schedule (6 AM)
- [ ] Content plans API + UI (view daily plan)

### Week 6

- [ ] Tweet Writer agent (4 variations)
- [ ] Quality Reviewer agent (scoring rubric)
- [ ] Fact Checker agent
- [ ] Humanizer agent
- [ ] Guardrails: banned phrases, char limit, duplicate check
- [ ] `GenerationWorkflow` (full pipeline)
- [ ] Drafts API: list, get, approve, reject

### Week 7

- [ ] Thread Writer agent (6–15 tweets)
- [ ] Reply Agent + reply_targets discovery (from favorite creators via X API)
- [ ] Quote Tweet Agent
- [ ] Draft variants UI: side-by-side comparison, scores
- [ ] Inline edit + re-score
- [ ] Regenerate button
- [ ] WebSocket: draft.ready notifications

### Week 8

- [ ] Bulk approve/reject
- [ ] Idea approval flow (approve ideas → trigger generation)
- [ ] Generation memory (anti-repetition)
- [ ] Prompt eval suite (golden_set.json, 20 scenarios)
- [ ] Error handling: generation_failed state, retry UI
- [ ] Cost tracking dashboard (tokens used today)

**Deliverable:** User sees daily plan, approves ideas, reviews draft tweets/threads with scores, approves/rejects.

---

## Milestone 4: Scheduler (Weeks 9–10)

**Goal:** Human-like scheduling with posting windows and jitter.

### Week 9

- [ ] Schedule config API + UI (quotas, windows, jitter)
- [ ] Slot allocator algorithm
- [ ] Redis publish queue (sorted sets)
- [ ] `ApprovalScheduleWorkflow`
- [ ] Calendar view UI (upcoming posts)
- [ ] Manual schedule override (pick exact time)

### Week 10

- [ ] `PublishTickWorkflow` (every minute)
- [ ] Quota tracking (daily/weekly Redis counters)
- [ ] Reply distribution algorithm (spread through day)
- [ ] Missed slot handling + draft expiry (48h)
- [ ] De-rounding time logic
- [ ] Timezone handling (UI + backend)

**Deliverable:** Approved drafts auto-scheduled in human-like windows, visible on calendar.

---

## Milestone 5: Publishing (Weeks 11–13)

**Goal:** Publish to X/Twitter with OAuth, rate limiting, and failure recovery.

### Week 11

- [ ] X OAuth 2.0 PKCE flow (authorize, callback, token storage)
- [ ] Token encryption (AES-256-GCM) + refresh logic
- [ ] X API client wrapper (post tweet, post reply, post quote)
- [ ] Rate limiter (Redis, respect X headers)
- [ ] `PublishWorkflow` (single tweet)

### Week 12

- [ ] Thread publishing (reply chain with delays)
- [ ] Reply publishing
- [ ] Quote tweet publishing
- [ ] Idempotency (prevent double-publish)
- [ ] Pre-publish validation pipeline
- [ ] Partial thread recovery
- [ ] Publish-now button (skip schedule)

### Week 13

- [ ] Publish success/failure notifications (WebSocket)
- [ ] Audit logging for all publish actions
- [ ] Manual copy fallback (no X account connected)
- [ ] X account reconnect flow (token expired)
- [ ] End-to-end test: plan → generate → approve → schedule → publish
- [ ] Load test: 50 publishes/hour

**Deliverable:** Full loop works — content publishes to X automatically after approval.

---

## Milestone 6: Analytics & Learning (Weeks 14–16)

**Goal:** Track engagement, display analytics, learn from performance.

### Week 14

- [ ] `MetricsCollectionWorkflow` (1h, 6h, 24h, 7d checkpoints)
- [ ] X API metrics fetch (public_metrics)
- [ ] `post_metrics` storage
- [ ] Follower snapshot (daily)
- [ ] Materialized views: daily_user_stats

### Week 15

- [ ] Analytics API: overview, posts, topics, heatmap
- [ ] Analytics dashboard UI:
  - Engagement trend chart
  - Follower growth chart
  - Top posts table
  - Posting time heatmap
  - Category breakdown
- [ ] `WeeklyLearningWorkflow` + schedule (Monday 8 AM)
- [ ] Learning Agent: analyze patterns, update weights

### Week 16

- [ ] Weekly insights report UI
- [ ] Memory storage from learnings
- [ ] Learned weights applied to planner + writer
- [ ] User rejection → negative memory signal
- [ ] Prompt version tracking in generation_metadata
- [ ] Production hardening:
  - Error monitoring (Sentry)
  - CloudWatch alarms
  - Backup verification
  - Security audit checklist
- [ ] Documentation: deployment guide, runbook

**Deliverable:** Full MVP — autonomous content team with analytics feedback loop.

---

## Post-MVP Backlog (Prioritized)

### Phase 2: Growth Features (Weeks 17–24)

| Priority | Feature |
|----------|---------|
| P0 | Twitter/X source ingestion (trends, followed accounts) |
| P0 | Auto-publish mode (opt-in, confidence threshold) |
| P1 | Email notifications (drafts ready, weekly report) |
| P1 | GitHub Trending + Arxiv sources |
| P1 | Thread resume UI for partial publishes |
| P2 | Creator style analysis (public data) |
| P2 | A/B testing for prompts |

### Phase 3: SaaS (Weeks 25–40)

| Priority | Feature |
|----------|---------|
| P0 | Multi-tenancy (RLS, tenant isolation) |
| P0 | Stripe billing (free/pro tiers) |
| P0 | Onboarding wizard |
| P1 | Team seats (agency model) |
| P1 | Auth0/Clerk integration |
| P1 | Qdrant migration for vectors |
| P2 | White-label option |
| P2 | API for third-party integrations |

---

## Risk Mitigation per Milestone

| Milestone | Risk | Mitigation |
|-----------|------|------------|
| M1 | Temporal setup complexity | Use temporalio/docker-compose dev image |
| M2 | RSS fetch SSRF | URL validation, private IP blocklist |
| M3 | AI quality insufficient | Iterate prompts weekly, eval suite gate |
| M3 | LLM costs | Cache aggressively, mini model for scoring |
| M5 | X API access denied | Apply early; manual copy fallback |
| M5 | X API rate limits | Per-user queues, respect headers |
| M6 | Limited analytics on Basic tier | Design dashboard for available metrics |

---

## Definition of Done (MVP)

- [ ] All M1–M6 deliverables complete
- [ ] E2E test passes: register → profile → sources → plan → generate → approve → publish → analytics
- [ ] 7 days of dogfooding (your own account)
- [ ] Draft first-pass approval rate ≥ 50%
- [ ] No P0 security issues
- [ ] Docker Compose reproduces full stack
- [ ] Staging deployment automated via CI
- [ ] Runbook for common operations

---

## Team Recommendation

| Role | MVP | SaaS |
|------|-----|------|
| Full-stack engineer (you) | ✅ | ✅ |
| AI/prompt engineer | Part-time weeks 5–8 | Full-time |
| DevOps | Part-time weeks 1–2, 16 | Part-time |
| Designer | Part-time weeks 6–8 (dashboard) | Part-time |

Solo developer timeline: 16 weeks at ~20 hours/week.
With AI assistance (Cursor): potentially 10–12 weeks.
