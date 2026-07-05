#!/usr/bin/env bash
set -euo pipefail

# Render/managed Postgres often provides postgresql:// — SQLAlchemy async needs +asyncpg
if [[ -n "${DATABASE_URL:-}" && "${DATABASE_URL}" == postgresql://* ]]; then
  export DATABASE_URL="postgresql+asyncpg://${DATABASE_URL#postgresql://}"
fi

echo "Running database migrations..."
alembic upgrade head

echo "Starting API..."
exec "$@"
