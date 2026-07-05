#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Starting Postgres + Redis..."
docker compose up postgres redis -d

echo "==> Waiting for Postgres..."
until docker compose exec -T postgres pg_isready -U xautopilot -q; do
  sleep 1
done

echo "==> Running database migrations..."
cd apps/api
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -e ".[dev]" -q
fi
.venv/bin/alembic upgrade head

echo ""
echo "✅ Database ready! Start the API:"
echo "   cd apps/api && source .venv/bin/activate && uvicorn xautopilot.main:app --reload"
echo ""
echo "   Then start the web app:"
echo "   cd apps/web && npm run dev"
