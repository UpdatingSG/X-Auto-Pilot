# Free Deployment ($0/month)

Render charges ~$7 per service (API + Web = **$14/mo**). This guide deploys everything on **free tiers**.

| Component | Provider | Free tier |
|-----------|----------|-----------|
| **Web** (Next.js) | [Vercel](https://vercel.com) | Hobby — free |
| **API** (FastAPI + worker) | [Fly.io](https://fly.io) | ~3 shared VMs, 256MB each |
| **Postgres** | [Neon](https://neon.tech) | 0.5 GB, free |

**Trade-offs vs paid Render:**
- Fly API **sleeps** when idle (~30s cold start on first request)
- Neon DB sleeps after 5 min inactivity on free tier
- Fine for personal use / dogfooding; upgrade later if you need 24/7

---

## Step 1 — Postgres on Neon (free)

1. Sign up at [neon.tech](https://neon.tech)
2. **New Project** → name `xautopilot` → region closest to you
3. Copy the connection string (looks like `postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require`)
4. Convert for our API — change the prefix:
   ```
   postgresql+asyncpg://user:pass@ep-xxx.neon.tech/neondb?sslmode=require
   ```

---

## Step 2 — API on Fly.io (free)

### Install Fly CLI

```bash
# macOS
brew install flyctl
fly auth login
```

### Generate secrets

```bash
./scripts/generate-secrets.sh
```

Create `.env.fly` (use `.env.free.example` as template):

```bash
DATABASE_URL=postgresql+asyncpg://...@ep-xxx.neon.tech/neondb?sslmode=require
SECRET_KEY=<from generate-secrets.sh>
TOKEN_ENCRYPTION_KEY=<from generate-secrets.sh>
CORS_ORIGINS=["https://YOUR_APP.vercel.app"]
FRONTEND_URL=https://YOUR_APP.vercel.app
X_REDIRECT_URI=https://YOUR_APP.vercel.app/settings/x/callback
X_CLIENT_ID=<your X app>
X_CLIENT_SECRET=<your X app secret>
OPENAI_API_KEY=<Groq or OpenAI key>
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=llama-3.3-70b-versatile
```

> Use a placeholder Vercel URL first; update after Step 3, then `fly secrets import < .env.fly` again.

### Deploy API

```bash
cd /path/to/x-autopilot

# First time only — creates the app (say no to Postgres addon; we use Neon)
fly launch --no-deploy --copy-config --name xautopilot-api

# Set secrets
fly secrets import < .env.fly

# Deploy
fly deploy

# Your API URL:
fly status
# → https://xautopilot-api.fly.dev
```

Verify:

```bash
curl https://xautopilot-api.fly.dev/health
curl https://xautopilot-api.fly.dev/health/ready
```

---

## Step 3 — Web on Vercel (free)

1. Push repo to **GitHub**
2. [vercel.com](https://vercel.com) → **Add New Project** → import repo
3. **Root Directory:** `apps/web`
4. **Environment variable** (required at build time):

   | Key | Value |
   |-----|-------|
   | `NEXT_PUBLIC_API_URL` | `https://xautopilot-api.fly.dev` |

5. **Deploy**

Your app URL will be something like `https://x-autopilot-xxx.vercel.app`.

### Update API CORS + X OAuth

Edit `.env.fly` with the real Vercel URL:

```bash
CORS_ORIGINS=["https://x-autopilot-xxx.vercel.app"]
FRONTEND_URL=https://x-autopilot-xxx.vercel.app
X_REDIRECT_URI=https://x-autopilot-xxx.vercel.app/settings/x/callback
```

```bash
fly secrets import < .env.fly
```

**X Developer Portal** → set callback URL to:
```
https://x-autopilot-xxx.vercel.app/settings/x/callback
```

---

## Step 4 — Verify end-to-end

1. Open your Vercel URL
2. Register → log in
3. Settings → Voice Profile → save
4. Settings → X Account → Connect with X
5. Content Plan → Generate plan

---

## Free tier limits

| Service | Limit | What happens |
|---------|-------|--------------|
| Fly.io | 3 shared VMs, 160GB outbound/mo | API sleeps when idle |
| Neon | 0.5 GB storage, compute sleeps | ~1s wake on first DB query |
| Vercel | 100GB bandwidth, hobby use | Plenty for personal app |

---

## Alternative: 100% free single server (Oracle Cloud)

If you prefer one server instead of three services:

1. Create an **Oracle Cloud Always Free** ARM VM (4 OCPU, 24GB RAM — $0 forever)
2. Install Docker
3. Use Neon for DB anyway (easier than self-hosting Postgres), or run full `docker-compose.prod.yml`
4. Point a domain or use the VM's IP with Caddy

See [DEPLOYMENT.md](DEPLOYMENT.md) Path B for docker-compose details.

---

## Upgrading later

When you outgrow free tiers:

- Fly → `fly scale memory 512` or Render starter ($7)
- Neon → paid plan ($19) for always-on DB
- Vercel Pro only if you need team features

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| API 502 / slow first request | Fly machine was asleep — wait ~30s, retry |
| CORS error | `CORS_ORIGINS` must exactly match Vercel URL with `https://` |
| X OAuth fails | Callback URL must match `X_REDIRECT_URI` exactly |
| DB connection error | Use `postgresql+asyncpg://` prefix; include `?sslmode=require` |
| Web shows wrong API | Redeploy Vercel after changing `NEXT_PUBLIC_API_URL` |
