# Running BenchmarkDashboard

This project is local-first. Use the macOS flow below for local development
without Docker. For a Linux machine with conda and Docker, use the backend-first
Linux flow.

## Local macOS Setup Without Docker

### 1. Install PostgreSQL

Install PostgreSQL with Homebrew:

```bash
brew install postgresql@16
brew services start postgresql@16
```

If your shell cannot find PostgreSQL commands after installation, add the
Homebrew path shown by `brew info postgresql@16` to your shell profile. On Apple
Silicon Macs this is commonly:

```bash
echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### 2. Create The Database

The backend default database URL is:

```text
postgresql+psycopg://postgres:postgres@localhost:5432/benchmark_dashboard
```

Create the matching local role and database:

```bash
createuser -s postgres
createdb -O postgres benchmark_dashboard
psql -d benchmark_dashboard -c "ALTER USER postgres WITH PASSWORD 'postgres';"
```

If `createuser` says the `postgres` role already exists, continue with
`createdb` and the password command.

### 3. Install Backend Dependencies

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If you use a different local PostgreSQL user or password, create
`backend/.env` and override `DATABASE_URL`:

```bash
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/benchmark_dashboard
```

### 4. Run Database Migrations

Run Alembic from the `backend/` directory with the virtual environment active:

```bash
alembic upgrade head
```

### 5. Import Benchmark Data

The importer reads JSONL files from two supported layouts:

```text
data/<model>/<dataset>.jsonl
data/<model>/<dataset_folder>/*.jsonl
```

For the flat layout, the dataset key is the JSONL filename without `.jsonl`.
For the nested layout, the dataset key is the folder name, not the JSONL file
name. For example, `data/Qwen3.5-4B/math500/results.jsonl` imports model
`Qwen3.5-4B` and dataset `math500`.

From the `backend/` directory:

```bash
python -m app.ingest --data-dir ../data
```

The importer is idempotent for completed runs with the same source file hash, so
running it again skips data that is already imported.

If you add a new dataset with a new field schema, add an adapter under
`backend/app/adapters/`, register it in `backend/app/adapters/registry.py`, add
it to `backend/app/dataset_categories.py`, and rerun ingestion. See
`docs/adapter_development.md`.

### 6. Start The Backend

From the `backend/` directory:

```bash
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`. A quick health check is:

```bash
curl http://localhost:8000/api/health
```

### 7. Start The Frontend

Open a second terminal and run:

```bash
cd frontend
npm install
npm run dev
```

The Vite app runs at `http://localhost:5173` and calls the API at
`http://localhost:8000` by default.

## Linux Backend Setup With Conda And Docker

This is the recommended path for a Linux host where the backend is the main
service and conda + Docker are already available.

From the repository root:

```bash
bash scripts/start-linux-backend.sh
```

The script does the backend-heavy work:

1. creates `backend/.env` from `backend/.env.example` if needed,
2. starts a PostgreSQL 16 Docker container on `localhost:5432`,
3. creates or reuses a conda environment named `benchmark-dashboard`,
4. installs `backend/requirements.txt`,
5. runs `alembic upgrade head`,
6. imports data from `data/`,
7. starts FastAPI on `0.0.0.0:8000`.

### Linux Script Settings

| Variable | Default | Purpose |
|---|---|---|
| `CONDA_ENV_NAME` | `benchmark-dashboard` | Conda environment to create or reuse. |
| `PYTHON_VERSION` | `3.12` | Python version for a newly created conda environment. |
| `START_POSTGRES_DOCKER` | `1` | Start/manage PostgreSQL through Docker. Set `0` to use an existing database. |
| `POSTGRES_CONTAINER` | `benchmark-dashboard-postgres` | Docker container name. |
| `POSTGRES_PORT` | `5432` | Host port mapped to PostgreSQL. |
| `POSTGRES_DB` | `benchmark_dashboard` | Database name. |
| `POSTGRES_USER` | `postgres` | Database user. |
| `POSTGRES_PASSWORD` | `postgres` | Database password. Change this on shared machines. |
| `DATA_DIR` | `<repo>/data` | Raw benchmark JSONL input directory. |
| `BACKEND_HOST` | `0.0.0.0` | FastAPI listen address. |
| `BACKEND_PORT` | `8000` | FastAPI listen port. |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Frontend origins allowed by FastAPI. |

Examples:

```bash
CONDA_ENV_NAME=benchdash BACKEND_PORT=8001 bash scripts/start-linux-backend.sh
```

Use an existing PostgreSQL instance instead of Docker:

```bash
START_POSTGRES_DOCKER=0 \
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/benchmark_dashboard \
bash scripts/start-linux-backend.sh
```

Expose the backend to another machine on the same network:

```bash
CORS_ORIGINS=http://<linux-host-ip>:5173 \
BACKEND_HOST=0.0.0.0 \
bash scripts/start-linux-backend.sh
```

Then point the frontend at:

```text
VITE_API_BASE_URL=http://<linux-host-ip>:8000
```

## Local Network Access

To let another person open the dashboard from the same network, both the
frontend and backend must be reachable from that person's browser.

Use the repository root script:

```bash
BACKEND_HOST=0.0.0.0 VITE_API_BASE_URL=http://<your-machine-ip>:8000 bash scripts/start-local.sh
```

Then share:

```text
http://<your-machine-ip>:5173
```

Set `backend/.env` so CORS allows the frontend origin:

```text
CORS_ORIGINS=http://<your-machine-ip>:5173
```

Notes:

- `localhost` only works on the same machine. Other users need your LAN IP or a
  domain name.
- The backend must listen on `0.0.0.0` for other machines to reach it. Use
  `BACKEND_HOST=0.0.0.0` with the script, or run uvicorn manually with
  `--host 0.0.0.0`.
- Your firewall must allow inbound traffic on the chosen frontend and backend
  ports.

## Full Docker Compose On Linux

Docker is not required for local development. For a Linux host with Docker and
Docker Compose installed, the repository includes:

- `backend/Dockerfile`: builds the FastAPI service image.
- `frontend/Dockerfile`: builds the Vite static bundle and serves it with nginx.
- `docker-compose.yml`: starts PostgreSQL, backend, and frontend together.

The compose flow is:

```bash
docker compose up --build
```

The backend container is configured to:

1. wait for the PostgreSQL health check,
2. run `alembic upgrade head`,
3. import data from the mounted `./data` directory,
4. start `uvicorn` on port `8000`.

The frontend container serves the built app on host port `5173`. The API is
available on host port `8000`.

For a real Linux deployment, configure these values before building:

```yaml
backend:
  environment:
    DATABASE_URL: postgresql+psycopg://postgres:<strong-password>@db:5432/benchmark_dashboard
    DATA_DIR: /app/data
    CORS_ORIGINS: http://<server-ip>:5173

frontend:
  build:
    args:
      VITE_API_BASE_URL: http://<server-ip>:8000
  ports:
    - "5173:80"
```

If you use a domain:

```text
CORS_ORIGINS=https://dashboard.example.com
VITE_API_BASE_URL=https://api.example.com
```

Recommended production shape:

- Put the frontend behind HTTPS on port `443`.
- Put the backend behind HTTPS on a stable API domain or reverse-proxy path.
- Do not expose PostgreSQL publicly; keep `5432` private to the Docker network
  or trusted hosts only.
- Change default database passwords.
- Mount `./data:/app/data:ro` so raw benchmark files are readable by the
  backend but not modified by the container.

### Port And IP Rules

| Setting | Local default | Shared/server value |
|---|---|---|
| Frontend listen port | `5173` | Any public port, commonly `80` or `443` behind a reverse proxy |
| Backend listen port | `8000` | Any public/internal API port, commonly proxied behind `443` |
| Backend listen host | `127.0.0.1` for private local use | `0.0.0.0` inside Docker or when serving LAN users |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Browser-reachable API URL, for example `http://<server-ip>:8000` |
| `CORS_ORIGINS` | `http://localhost:5173` | Browser frontend origin, for example `http://<server-ip>:5173` |

Remember: `VITE_API_BASE_URL` is baked into the frontend build. If you change the
server IP/domain for a Docker deployment, rebuild the frontend image.
