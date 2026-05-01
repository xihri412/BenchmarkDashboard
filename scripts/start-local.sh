#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
DATA_DIR="$ROOT_DIR/data"
BACKEND_ENV="$BACKEND_DIR/.env"
BACKEND_ENV_EXAMPLE="$BACKEND_DIR/.env.example"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
FRONTEND_HOST="${FRONTEND_HOST:-0.0.0.0}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

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

if [[ ! -f "$BACKEND_ENV" && -f "$BACKEND_ENV_EXAMPLE" ]]; then
  log "Creating backend/.env from backend/.env.example"
  cp "$BACKEND_ENV_EXAMPLE" "$BACKEND_ENV"
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python command not found: $PYTHON_BIN" >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required but was not found." >&2
  exit 1
fi

if command -v pg_isready >/dev/null 2>&1; then
  if ! pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
    echo "PostgreSQL does not appear to be running on localhost:5432." >&2
    echo "Start PostgreSQL first, then rerun this script." >&2
    exit 1
  fi
fi

if command -v createdb >/dev/null 2>&1; then
  createdb benchmark_dashboard >/dev/null 2>&1 || true
fi

log "Preparing backend virtual environment"
cd "$BACKEND_DIR"
if [[ ! -d ".venv" ]]; then
  "$PYTHON_BIN" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

log "Running database migrations"
alembic upgrade head

if [[ -d "$DATA_DIR" ]]; then
  log "Importing benchmark data from $DATA_DIR"
  python -m app.ingest --data-dir "$DATA_DIR"
else
  log "Skipping ingestion because data directory does not exist"
fi

log "Installing frontend dependencies"
cd "$FRONTEND_DIR"
npm install

log "Starting backend on http://$BACKEND_HOST:$BACKEND_PORT"
cd "$BACKEND_DIR"
uvicorn app.main:app --reload --host "$BACKEND_HOST" --port "$BACKEND_PORT" &
backend_pid="$!"

log "Starting frontend on http://$FRONTEND_HOST:$FRONTEND_PORT"
cd "$FRONTEND_DIR"
npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" &
frontend_pid="$!"

cat <<EOF

BenchmarkDashboard is starting:
  Backend:  http://localhost:$BACKEND_PORT
  Frontend: http://localhost:$FRONTEND_PORT

Press Ctrl+C to stop both services.
EOF

wait "$backend_pid" "$frontend_pid"
