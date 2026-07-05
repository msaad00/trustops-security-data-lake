#!/usr/bin/env bash
# Load golden fixture, build console, start server, capture README PNGs, stop server.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PORT="${TRUSTOPS_SCREENSHOT_PORT:-8787}"
BASE="http://127.0.0.1:${PORT}"
LAKE="${TRUSTOPS_LAKE:-build/lakehouse}"

echo "==> Load golden fixture into ${LAKE}"
uv run security-lakehouse fixtures load --company golden --out "$LAKE"
uv run security-lakehouse db upgrade --lake "$LAKE"

echo "==> Build console static export"
npm --prefix app/web run build

echo "==> Start server on ${BASE}"
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

deadline=$((SECONDS + 30))
until curl -sf "${BASE}/api/v1/healthz" >/dev/null 2>&1; do
  if (( SECONDS > deadline )); then
    echo "Server failed to start on ${BASE}" >&2
    exit 1
  fi
  sleep 0.5
done

echo "==> Capture screenshots to docs/images/"
TRUSTOPS_SCREENSHOT_URL="$BASE" npm --prefix app/web run demo-screenshots

echo "==> Done. PNGs in docs/images/trustops-demo-*.png"
