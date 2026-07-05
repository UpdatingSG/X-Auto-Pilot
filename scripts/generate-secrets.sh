#!/usr/bin/env bash
# Generate production secrets for apps/api/.env
# NEVER commit the output — paste into your secrets manager or local .env
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PYTHON="$ROOT/apps/api/.venv/bin/python3"

if [ -x "$VENV_PYTHON" ]; then
  PYTHON="$VENV_PYTHON"
else
  PYTHON="python3"
fi

SECRET_KEY="$(openssl rand -hex 32)"
TOKEN_KEY="$("$PYTHON" -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")"

cat <<EOF
# --- Paste into apps/api/.env or your secrets manager ---
# Generate fresh values before each new environment.

APP_ENV=production

# JWT signing (openssl rand -hex 32)
SECRET_KEY=${SECRET_KEY}

# X OAuth token encryption — separate from JWT secret
TOKEN_ENCRYPTION_KEY=${TOKEN_KEY}

# Production domains (HTTPS only)
CORS_ORIGINS=["https://your-app.example.com"]
FRONTEND_URL=https://your-app.example.com
X_REDIRECT_URI=https://your-app.example.com/settings/x/callback

# Database (use managed Postgres in prod)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/xautopilot

# X API (live only in production)
X_API_MODE=live
X_CLIENT_ID=
X_CLIENT_SECRET=

# OpenAI (Step 4) — or Groq-compatible endpoint
# OPENAI_API_KEY=
# OPENAI_BASE_URL=https://api.groq.com/openai/v1
# OPENAI_MODEL=llama-3.3-70b-versatile

# Workers (auto-publish scheduled drafts)
# WORKER_ENABLED=true
# WORKER_MANUAL_TICK_ENABLED=false
EOF
