#!/usr/bin/env bash
# Load golden fixture, start lakehouse server, run Playwright console smoke tests.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PORT="${PLAYWRIGHT_PORT:-8787}"
BASE="http://127.0.0.1:${PORT}"
LAKE="${TRUSTOPS_LAKE:-build/lakehouse-e2e}"

echo "==> Load golden fixture into ${LAKE}"
uv run security-lakehouse fixtures load --company golden --out "$LAKE"
uv run security-lakehouse db upgrade --lake "$LAKE"

echo "==> Start server on ${BASE}"
export TRUSTOPS_COOKIE_SIGNING_KEY="${TRUSTOPS_COOKIE_SIGNING_KEY:-e2e-test-cookie-signing-key}"
uv run security-lakehouse serve \
  --lake "$LAKE" \
  --server \
  --allow-insecure-no-auth \
  --port "$PORT" \
  --host 127.0.0.1 &
SERVER_PID=$!
cleanup() {
  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT

deadline=$((SECONDS + 45))
until curl -sf "${BASE}/api/v1/healthz" >/dev/null 2>&1; do
  if (( SECONDS > deadline )); then
    echo "Server failed to start on ${BASE}" >&2
    exit 1
  fi
  sleep 0.5
done

echo "==> Run Playwright console smoke tests"
PLAYWRIGHT_BASE_URL="$BASE" npm --prefix app/web run test:e2e

echo "==> E2E smoke passed"
