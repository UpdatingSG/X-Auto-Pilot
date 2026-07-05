# Production Readiness Roadmap

Step-by-step path from MVP (mock mode) to production.

| Step | Area | Status | Doc |
|------|------|--------|-----|
| 1 | Real X OAuth 2.0 PKCE | ✅ Done | [Step 1](#step-1-real-x-oauth-20-pkce) |
| 2 | Live X API + token refresh | ✅ Done | [Step 2](#step-2-live-x-api--token-refresh) |
| 3 | Production secrets & config | ✅ Done | [Step 3](#step-3-production-secrets--config) |
| 4 | Real LLM (OpenAI) | ✅ Done | [Step 4](#step-4-real-llm-integration) |
| 5 | Background workers | ✅ Done | [Step 5](#step-5-background-workers) |
| 6 | Hosting & infrastructure | ✅ Ready | [DEPLOYMENT.md](DEPLOYMENT.md) |
| 7 | Hardening (rate limits, monitoring) | ⏳ Pending | [Step 7](#step-7-hardening) |

---

## Step 1: Real X OAuth 2.0 PKCE

**Goal:** Replace mock connect with real Twitter/X authorization.

**You need:**
1. [X Developer Portal](https://developer.twitter.com/) app (Free or Basic tier)
2. OAuth 2.0 enabled, type: **Web App** or **Native App** with PKCE
3. Callback URL: `http://localhost:8000/v1/x/oauth/callback` (dev)
4. Scopes: `tweet.read`, `tweet.write`, `users.read`, `offline.access`

**Env vars** (`apps/api/.env`):
```bash
X_API_MODE=live
X_CLIENT_ID=your_client_id
X_CLIENT_SECRET=your_client_secret   # required for confidential web apps
X_REDIRECT_URI=http://localhost:8000/v1/x/oauth/callback
FRONTEND_URL=http://localhost:3000
```

**Flow:**
```
User → Connect with X → /v1/x/oauth/start → Twitter consent
     → /v1/x/oauth/callback → encrypt tokens → x_accounts
     → redirect to /settings/x?connected=1
```

**Tests:** OAuth start URL shape, callback token exchange (mocked HTTP), mock connect still works when `X_API_MODE=mock`.

---

## Step 2: Live X API + Token Refresh

**Goal:** Keep access tokens fresh and handle X API auth/rate-limit failures gracefully.

**Implemented:**
- `get_valid_access_token()` refreshes ~5 min before `token_expires_at`
- Publish + metrics sync use refreshed tokens automatically
- X API `401` → `needs_reauth=true`; user sees reconnect prompt in Settings
- X API `429` → `Retry-After` header on error response
- `POST /v1/x/account/refresh` for proactive refresh (also used in tests)

**Key files:** `x_token_service.py`, `x_client.py` (`XApiUnauthorizedError`, `XApiRateLimitError`)

**Tests:** `tests/test_x_token.py`

---

## Step 3: Production Secrets & Config

**Goal:** Separate JWT signing from token encryption; fail fast on unsafe production config.

**Implemented:**
- `SECRET_KEY` — JWT signing (32+ chars required in staging/production)
- `TOKEN_ENCRYPTION_KEY` — separate Fernet key for X OAuth tokens (required in staging/production)
- `APP_ENV` — `development` | `staging` | `production`
- Startup validation — API refuses to start in staging/production with dev defaults
- `GET /health/config` — safe config audit (no secret values exposed)
- `scripts/generate-secrets.sh` — one-command secret generation
- Templates: `apps/api/.env.production.example`, `apps/web/.env.production.example`

**Key rotation:** Changing `TOKEN_ENCRYPTION_KEY` invalidates stored X tokens — users must reconnect in Settings.

**Vault (production):** Inject env from AWS Secrets Manager, Doppler, or Vault — never commit `.env`.

**Generate secrets:**
```bash
chmod +x scripts/generate-secrets.sh
./scripts/generate-secrets.sh
```

**Production checklist:**
- [ ] `APP_ENV=production`
- [ ] `SECRET_KEY` — `openssl rand -hex 32`
- [ ] `TOKEN_ENCRYPTION_KEY` — from `generate-secrets.sh` (≠ `SECRET_KEY`)
- [ ] `CORS_ORIGINS` — HTTPS production domain only
- [ ] `FRONTEND_URL` / `X_REDIRECT_URI` — HTTPS
- [ ] `X_API_MODE=live`

**Tests:** `tests/test_production_config.py`, `tests/test_health_config.py`

---

## Step 4: Real LLM Integration

**Goal:** Replace template agents with OpenAI; track cost per user/day.

**Implemented:**
- `LLM_MODE=mock|live` — mock uses templates (tests/dev), live calls OpenAI
- `content_planner.py` + `tweet_writer.py` — JSON-mode chat completions via `llm_service.py`
- Versioned prompts in `services/agents/prompts.py` (`PROMPT_VERSION=1.0.0`)
- `generation_metadata` on drafts — model, tokens, cost, prompt version
- `llm_usage_daily` table — per-user daily cost aggregation
- `LLM_DAILY_BUDGET_USD` — default $5/day; returns 429 when exceeded

**Env vars** (`apps/api/.env`):
```bash
LLM_MODE=live
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
LLM_DAILY_BUDGET_USD=5.0
```

**Tests:** `tests/test_openai_llm.py` (mocked OpenAI HTTP)

---

## Step 5: Background Workers

**Goal:** Auto-publish scheduled drafts and sync metrics without manual clicks.

**Implemented:**
- **Publish tick** — every 60s, publishes drafts where `scheduled_at <= now`
- **Metrics sync** — jobs at +1h, +6h, +24h after each publish (manual or auto)
- APScheduler runs in-process when `WORKER_ENABLED=true`
- `POST /v1/worker/tick` — manual tick for dev/testing
- `GET /v1/worker/status` — worker config
- `scripts/run-worker.sh` — optional standalone poller

**Env vars:**
```bash
WORKER_ENABLED=true
WORKER_TICK_INTERVAL_SECONDS=60
WORKER_MANUAL_TICK_ENABLED=true   # false in production
```

**Tests:** `tests/test_worker.py`

---

## Step 6: Hosting & Infrastructure

**Goal:** Deploy API + Web + Postgres to production with HTTPS.

**Implemented:**
- Production Dockerfiles: `infra/docker/Dockerfile.api.prod`, `Dockerfile.web.prod`
- Auto-migrations on API startup (`infra/docker/api-entrypoint.sh`)
- `docker-compose.prod.yml` — VPS deploy with Caddy TLS
- `render.yaml` — one-click Render Blueprint
- `.env.production.example` — production env template
- **[Deployment Guide](DEPLOYMENT.md)** — step-by-step Render + VPS instructions

**Deploy:**
```bash
# Render: connect GitHub repo → New Blueprint → set env vars → deploy
# VPS:
cp .env.production.example .env.production  # fill in secrets
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

**Checklist:**
- [ ] Postgres provisioned (Render addon or compose volume)
- [ ] Secrets from `scripts/generate-secrets.sh` in hosting env
- [ ] X OAuth callback URL updated to production HTTPS domain
- [ ] `GET /health/ready` returns ready
- [ ] Register → connect X → generate plan on live URL

---

## Step 7: Hardening

- API rate limiting (Redis sliding window)
- Sentry error monitoring
- Audit log for publish actions
- CSP headers on frontend
- Security checklist from `docs/13-SECURITY.md`

---

## Definition of Done (Production)

- [ ] Real X OAuth connect works on staging
- [ ] Scheduled posts publish automatically
- [ ] Metrics sync on schedule
- [ ] Real LLM generation with approval gate
- [ ] Secrets in vault, not .env on disk
- [ ] 7 days dogfooding on personal account
- [ ] No P0 security issues
