# Deployment Guide

Get X-Autopilot live on the internet.

| Path | Best for | Cost |
|------|----------|------|
| **[Free — Vercel + Render + Neon](DEPLOYMENT-FREE.md)** | Personal / hobby, no card | **$0/mo** |
| **[A) Render](#path-a-render)** | Easiest paid all-in-one | ~$14/mo |
| **[B) VPS + Docker](#path-b-vps--docker)** | Full control | ~$6–12/mo |

Both paths give you HTTPS, Postgres, auto-migrations, and background workers (auto-publish + metrics).

---

## Before you deploy

### 1. Generate production secrets

```bash
./scripts/generate-secrets.sh
```

Save the output — you'll paste into your hosting provider's env vars.

### 2. X Developer Portal

In [developer.twitter.com](https://developer.twitter.com/):

1. Create / open your app → **User authentication settings**
2. Enable OAuth 2.0, type **Web App**
3. Set callback URL to your **production** frontend:
   ```
   https://YOUR_APP_DOMAIN/settings/x/callback
   ```
4. Scopes: `tweet.read`, `tweet.write`, `users.read`, `offline.access`

### 3. LLM provider

Production requires `LLM_MODE=live` and `OPENAI_API_KEY`.

- **OpenAI:** `OPENAI_BASE_URL=https://api.openai.com/v1`, `OPENAI_MODEL=gpt-4o-mini`
- **Groq:** `OPENAI_BASE_URL=https://api.groq.com/openai/v1`, `OPENAI_MODEL=llama-3.3-70b-versatile`

---

## Path A: Render (paid — ~$14/mo for API + Web)

> **Want free?** Use **[DEPLOYMENT-FREE.md](DEPLOYMENT-FREE.md)** (Vercel + Render free API + Neon = $0).

### Step 1 — Push to GitHub

```bash
git add .
git commit -m "Add production deployment config"
git push origin main
```

### Step 2 — Create Blueprint

1. Go to [render.com](https://render.com) → **New** → **Blueprint**
2. Connect your GitHub repo
3. Render reads `render.yaml` and creates:
   - **xautopilot-db** (Postgres)
   - **xautopilot-api** (FastAPI + worker)
   - **xautopilot-web** (Next.js)

### Step 3 — Set environment variables

After the blueprint is created, open each service and set **sync: false** vars:

**API service (`xautopilot-api`):**

| Variable | Example |
|----------|---------|
| `TOKEN_ENCRYPTION_KEY` | from `generate-secrets.sh` |
| `CORS_ORIGINS` | `["https://xautopilot-web.onrender.com"]` |
| `FRONTEND_URL` | `https://xautopilot-web.onrender.com` |
| `X_REDIRECT_URI` | `https://xautopilot-web.onrender.com/settings/x/callback` |
| `X_CLIENT_ID` | your X app client ID |
| `X_CLIENT_SECRET` | your X app secret |
| `OPENAI_API_KEY` | your OpenAI/Groq key |

**Web service (`xautopilot-web`):**

| Variable | Example |
|----------|---------|
| `API_URL` | Vercel (server only) | `https://xautopilot-api.onrender.com` |
| `NEXT_PUBLIC_API_URL` | **Do not set** | Delete if present — it is baked into the browser bundle |

> **Important:** The web app proxies `/v1/*` to Render via a Next.js route handler using **runtime** `API_URL`. Do **not** set `NEXT_PUBLIC_API_URL` on Vercel (especially not to `localhost`). After changing env vars, redeploy the web app.

### Step 4 — Custom domain (optional)

1. Render → web service → **Settings** → **Custom Domain** → add `app.yourdomain.com`
2. API service → add `api.yourdomain.com`
3. Update env vars (`FRONTEND_URL`, `CORS_ORIGINS`, `X_REDIRECT_URI`, `NEXT_PUBLIC_API_URL`) to use custom domains
4. Update X Developer Portal callback URL
5. Redeploy both services

### Step 5 — Verify

```bash
curl https://YOUR_API_URL/health
curl https://YOUR_API_URL/health/ready
```

Open `https://YOUR_WEB_URL` → register → connect X → generate a plan.

---

## Path B: VPS + Docker

For a DigitalOcean / Hetzner / AWS Lightsail VPS with Docker.

### Step 1 — Server setup

```bash
# On Ubuntu 22.04+ VPS
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
sudo usermod -aG docker $USER
```

### Step 2 — Clone and configure

```bash
git clone https://github.com/YOUR_USER/x-autopilot.git
cd x-autopilot
cp .env.production.example .env.production
```

Edit `.env.production`:

- Set `APP_DOMAIN`, `API_DOMAIN`, `ACME_EMAIL`
- Paste secrets from `generate-secrets.sh`
- Set X OAuth + LLM keys

### Step 3 — DNS

Point A records to your VPS IP:

```
app.yourdomain.com  →  VPS_IP
api.yourdomain.com  →  VPS_IP
```

### Step 4 — Deploy

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

Caddy automatically provisions HTTPS via Let's Encrypt.

### Step 5 — Verify

```bash
docker compose -f docker-compose.prod.yml ps
curl https://api.yourdomain.com/health
```

---

## What runs in production

| Component | Behavior |
|-----------|----------|
| **API** | FastAPI on port 8000, runs `alembic upgrade head` on startup |
| **Worker** | APScheduler in-process (`WORKER_ENABLED=true`) — auto-publishes scheduled drafts every 60s |
| **Web** | Next.js standalone (`next start` equivalent via `node server.js`) |
| **Postgres** | pgvector image, persistent volume |

Temporal and Redis are **not required** for the current MVP — workers use APScheduler, not Temporal.

---

## Production checklist

- [ ] `APP_ENV=production`
- [ ] `SECRET_KEY` — 32+ chars, not dev default
- [ ] `TOKEN_ENCRYPTION_KEY` — Fernet key, different from `SECRET_KEY`
- [ ] `CORS_ORIGINS` — HTTPS only, your app domain
- [ ] `FRONTEND_URL` / `X_REDIRECT_URI` — HTTPS, match X Developer Portal
- [ ] `X_API_MODE=live`
- [ ] `LLM_MODE=live` + `OPENAI_API_KEY`
- [ ] `WORKER_MANUAL_TICK_ENABLED=false`
- [ ] X callback URL updated in Developer Portal
- [ ] `GET /health/ready` returns `ready`

---

## Updating after deploy

```bash
# VPS
git pull
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build

# Render — push to main (auto-deploy if enabled)
git push origin main
```

Migrations run automatically on API container startup.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| API won't start in production | Check logs for config validation errors; run `GET /health/config` |
| X OAuth fails | Callback URL must exactly match `X_REDIRECT_URI` (HTTPS) |
| CORS errors | `CORS_ORIGINS` must include your web URL with `https://` |
| Web can't reach API | `NEXT_PUBLIC_API_URL` must be set at **build** time; redeploy web |
| 503 database | Wait for Postgres healthcheck; check `DATABASE_URL` |
| Scheduled posts not publishing | Confirm `WORKER_ENABLED=true` on API service |

---

## Next steps (Step 7 hardening)

- Sentry error monitoring
- Redis rate limiting
- Separate worker process at scale
- Backups for Postgres

See [PRODUCTION-ROADMAP.md](PRODUCTION-ROADMAP.md) Step 6–7.
