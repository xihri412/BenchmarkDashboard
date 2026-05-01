#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"

BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-0.0.0.0}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
PUBLIC_HOST="${PUBLIC_HOST:-localhost}"
VITE_API_BASE_URL="${VITE_API_BASE_URL:-http://$PUBLIC_HOST:$BACKEND_PORT}"
CORS_ORIGINS="${CORS_ORIGINS:-[\"http://$PUBLIC_HOST:$FRONTEND_PORT\",\"http://localhost:$FRONTEND_PORT\",\"http://127.0.0.1:$FRONTEND_PORT\"]}"

backend_pid=""
frontend_pid=""

cleanup() {
  if [[ -n "$backend_pid" ]] && kill -0 "$backend_pid" 2>/dev/null; then
    kill "$backend_pid" 2>/dev/null || true
  fi
  if [[ -n "$frontend_pid" ]] && kill -0 "$frontend_pid" 2>/dev/null; then
    kill "$frontend_pid" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required to start the frontend but was not found." >&2
  exit 1
fi

log "Starting backend with scripts/start-linux-backend.sh"
(
  export BACKEND_HOST
  export BACKEND_PORT
  export CORS_ORIGINS
  cd "$ROOT_DIR"
  bash scripts/start-linux-backend.sh
) &
backend_pid="$!"

log "Installing frontend dependencies"
cd "$FRONTEND_DIR"
npm install

log "Starting frontend on http://$FRONTEND_HOST:$FRONTEND_PORT"
export VITE_API_BASE_URL
npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" &
frontend_pid="$!"

cat <<EOF

BenchmarkDashboard full stack is starting:
  Backend listen:  http://$BACKEND_HOST:$BACKEND_PORT
  Frontend listen: http://$FRONTEND_HOST:$FRONTEND_PORT
  Browser URL:     http://$PUBLIC_HOST:$FRONTEND_PORT
  API base URL:    $VITE_API_BASE_URL
  CORS origins:    $CORS_ORIGINS

For LAN/server access, run for example:
  PUBLIC_HOST=<linux-host-ip> bash scripts/start-linux.sh

Press Ctrl+C to stop both services.
EOF

wait "$backend_pid" "$frontend_pid"
