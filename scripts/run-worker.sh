#!/usr/bin/env bash
# Standalone worker loop (alternative to in-process APScheduler)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_URL="${API_URL:-http://localhost:8000}"
INTERVAL="${WORKER_TICK_INTERVAL_SECONDS:-60}"

echo "Worker polling $API_URL/v1/worker/tick every ${INTERVAL}s (Ctrl+C to stop)"

while true; do
  curl -s -X POST "$API_URL/v1/worker/tick" | python3 -m json.tool 2>/dev/null || true
  sleep "$INTERVAL"
done
