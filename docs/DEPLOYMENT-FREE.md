# Free Deployment ($0/month)

No Fly.io. No credit card. No $14 Render Blueprint.

| Component | Provider | Cost |
|-----------|----------|------|
| **Web** (Next.js) | [Vercel](https://vercel.com) | Free |
| **API** (FastAPI + worker) | [Render](https://render.com) free tier | Free |
| **Postgres** | [Neon](https://neon.tech) | Free |

**Why not Fly.io?** New accounts in some regions get a "$4 high risk" card verification. Skip it — use Render's **single free web service** for the API instead.

**Why not the full Render Blueprint (`render.yaml`)?** That creates 2 paid services (API + Web = $14/mo). We only use Render for the API; Vercel hosts the web app for free.

**Trade-offs:**
- Render free API **spins down** after ~15 min idle (cold start ~30–60s)
- Neon free DB sleeps after inactivity
- Perfect for personal / hobby use

---

## Step 1 — Postgres on Neon (free)

1. [neon.tech](https://neon.tech) → sign up → **New Project**
2. Copy connection string
3. Add `+asyncpg` after `postgresql`:
   ```
   postgresql+asyncpg://user:pass@ep-xxx.neon.tech/neondb?sslmode=require
   ```

---

## Step 2 — API on Render (free)

### Option A: Blueprint (API only)

1. Push repo to GitHub
2. Render → **New** → **Blueprint**
3. When asked which file, use **`render-api-free.yaml`** (not `render.yaml`)
4. Confirm it shows **1 service**, plan **Free**
5. Set these env vars when prompted (`sync: false` ones):

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Neon URL with `postgresql+asyncpg://` |
| `TOKEN_ENCRYPTION_KEY` | from `./scripts/generate-secrets.sh` |
| `CORS_ORIGINS` | `["https://PLACEHOLDER.vercel.app"]` (update after Step 3) |
| `FRONTEND_URL` | `https://PLACEHOLDER.vercel.app` |
| `X_REDIRECT_URI` | `https://PLACEHOLDER.vercel.app/settings/x/callback` |
| `X_CLIENT_ID` | your X app |
| `X_CLIENT_SECRET` | your X app secret |
| `OPENAI_API_KEY` | Groq or OpenAI key |

6. **Deploy Blueprint**

Your API URL: `https://xautopilot-api.onrender.com`

### Option B: Manual (if Blueprint fails)

1. Render → **New** → **Web Service**
2. Connect GitHub repo
3. **Runtime:** Docker
4. **Dockerfile path:** `infra/docker/Dockerfile.api.prod`
5. **Instance type:** **Free**
6. Add env vars from table above
7. **Create Web Service**

Verify:
```bash
curl https://xautopilot-api.onrender.com/health
```

> First request after idle may take 30–60s while the service wakes up.

---

## Step 3 — Web on Vercel (free)

1. [vercel.com](https://vercel.com) → **Add New Project** → import repo
2. **Root Directory:** `apps/web`
3. **Environment variable:**

   | Key | Value |
   |-----|-------|
   | `NEXT_PUBLIC_API_URL` | `https://xautopilot-api.onrender.com` |

4. **Deploy**

Note your URL: `https://x-autopilot-xxx.vercel.app`

---

## Step 4 — Connect everything

### Update Render API env vars

Replace placeholders with your real Vercel URL:

```
CORS_ORIGINS=["https://x-autopilot-xxx.vercel.app"]
FRONTEND_URL=https://x-autopilot-xxx.vercel.app
X_REDIRECT_URI=https://x-autopilot-xxx.vercel.app/settings/x/callback
```

Render → your API service → **Environment** → save → **Manual Deploy**

### Update X Developer Portal

Callback URL:
```
https://x-autopilot-xxx.vercel.app/settings/x/callback
```

---

## Step 5 — Test

1. Open Vercel URL → register
2. Settings → X Account → Connect
3. Content Plan → Generate

If API is slow on first load, wait ~60s (Render waking up) and refresh.

---

## If Render free is unavailable

Some accounts/regions can't get Render free tier. Alternatives:

| Option | Cost | Notes |
|--------|------|-------|
| **Oracle Cloud Always Free VM** | $0 | 4 ARM cores, run `docker-compose.prod.yml` + Neon |
| **Google Cloud Run** | $0* | Free tier limits; needs GCP account |
| **Pay Fly.io $4 hold** | Refunded | One-time verification, then free tier works |

Oracle path: see [DEPLOYMENT.md](DEPLOYMENT.md) Path B — use Neon for DB, skip self-hosted Postgres.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Render shows $7 not Free | Pick **Free** instance type manually; don't use `render.yaml` |
| API timeout on first request | Free tier waking up — wait 60s, retry |
| CORS errors | `CORS_ORIGINS` must match Vercel URL exactly |
| X OAuth fails | Callback must match `X_REDIRECT_URI` |
| DB errors | URL must be `postgresql+asyncpg://...?sslmode=require` |
