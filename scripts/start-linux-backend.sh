#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
DATA_DIR="${DATA_DIR:-$ROOT_DIR/data}"
BACKEND_ENV="$BACKEND_DIR/.env"
BACKEND_ENV_EXAMPLE="$BACKEND_DIR/.env.example"

CONDA_ENV_NAME="${CONDA_ENV_NAME:-benchmark-dashboard}"
PYTHON_VERSION="${PYTHON_VERSION:-3.12}"
BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

START_POSTGRES_DOCKER="${START_POSTGRES_DOCKER:-1}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-benchmark-dashboard-postgres}"
POSTGRES_IMAGE="${POSTGRES_IMAGE:-postgres:16-alpine}"
POSTGRES_DB="${POSTGRES_DB:-benchmark_dashboard}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_VOLUME="${POSTGRES_VOLUME:-benchmark-dashboard-postgres-data}"

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1" >&2
    exit 1
  fi
}

wait_for_postgres() {
  local attempt
  for attempt in $(seq 1 60); do
    if docker exec "$POSTGRES_CONTAINER" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done

  echo "PostgreSQL did not become ready in time." >&2
  exit 1
}

prepare_conda() {
  require_command conda

  local conda_base
  conda_base="$(conda info --base)"
  # shellcheck disable=SC1090
  source "$conda_base/etc/profile.d/conda.sh"

  if ! conda env list | awk '{print $1}' | grep -qx "$CONDA_ENV_NAME"; then
    log "Creating conda environment: $CONDA_ENV_NAME"
    conda create -y -n "$CONDA_ENV_NAME" "python=$PYTHON_VERSION"
  fi

  conda activate "$CONDA_ENV_NAME"
}

start_postgres_with_docker() {
  require_command docker

  if docker ps --format '{{.Names}}' | grep -qx "$POSTGRES_CONTAINER"; then
    log "PostgreSQL container is already running: $POSTGRES_CONTAINER"
  elif docker ps -a --format '{{.Names}}' | grep -qx "$POSTGRES_CONTAINER"; then
    log "Starting existing PostgreSQL container: $POSTGRES_CONTAINER"
    docker start "$POSTGRES_CONTAINER" >/dev/null
  else
    log "Creating PostgreSQL container: $POSTGRES_CONTAINER"
    docker run -d \
      --name "$POSTGRES_CONTAINER" \
      -e POSTGRES_DB="$POSTGRES_DB" \
      -e POSTGRES_USER="$POSTGRES_USER" \
      -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
      -p "$POSTGRES_PORT:5432" \
      -v "$POSTGRES_VOLUME:/var/lib/postgresql/data" \
      "$POSTGRES_IMAGE" >/dev/null
  fi

  wait_for_postgres
}

if [[ ! -f "$BACKEND_ENV" && -f "$BACKEND_ENV_EXAMPLE" ]]; then
  log "Creating backend/.env from backend/.env.example"
  cp "$BACKEND_ENV_EXAMPLE" "$BACKEND_ENV"
fi

if [[ "$START_POSTGRES_DOCKER" == "1" ]]; then
  start_postgres_with_docker
else
  log "Skipping Docker PostgreSQL startup because START_POSTGRES_DOCKER=$START_POSTGRES_DOCKER"
fi

export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://$POSTGRES_USER:$POSTGRES_PASSWORD@localhost:$POSTGRES_PORT/$POSTGRES_DB}"
export DATA_DIR="$DATA_DIR"
export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:5173,http://127.0.0.1:5173}"

prepare_conda

log "Installing backend Python dependencies"
cd "$BACKEND_DIR"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

log "Running database migrations"
alembic upgrade head

if [[ -d "$DATA_DIR" ]]; then
  log "Importing benchmark data from $DATA_DIR"
  python -m app.ingest --data-dir "$DATA_DIR"
else
  log "Skipping ingestion because data directory does not exist: $DATA_DIR"
fi

log "Starting backend on http://$BACKEND_HOST:$BACKEND_PORT"
exec uvicorn app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT"
