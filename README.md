# BenchmarkDashboard

BenchmarkDashboard is a deployable benchmark analytics service for model inference results. Raw benchmark files stay in `data/` and are not committed to Git. The backend imports those JSONL files into PostgreSQL, normalizes dataset-specific fields through adapters, and exposes APIs consumed by the React dashboard.

## Architecture

```text
data/<model>/<dataset>.jsonl
data/<model>/<dataset_folder>/*.jsonl
        |
        v
FastAPI ingestion + dataset adapters
        |
        v
PostgreSQL tables and metric summaries
        |
        v
FastAPI query APIs
        |
        v
React dashboard
```

The current implementation is local-machine friendly and does not require Docker to run. Docker files are included for the later Linux deployment target.

## Directory Map

| Path | Purpose |
|---|---|
| `backend/` | FastAPI service, SQLAlchemy models, Alembic migrations, ingestion, adapters, and API routes. See `backend/README.md`. |
| `frontend/` | Vite + React + TypeScript dashboard. See `frontend/README.md`. |
| `docs/adapter_development.md` | How to add or update dataset adapters when new JSONL formats arrive. |
| `docs/architecture.md` | Architecture notes and service design. |
| `docs/running.md` | Local and future Docker runbook. |
| `data/` | Local raw benchmark results. This directory is ignored by Git and should not be uploaded unless explicitly intended. |
| `docker-compose.yml` | Future Linux Docker deployment scaffold for frontend, backend, and PostgreSQL. |
| `scripts/start-linux.sh` | Linux full-stack bootstrap: starts backend, PostgreSQL, and frontend. |
| `scripts/start-linux-backend.sh` | Linux backend-only bootstrap using conda for Python and Docker for PostgreSQL. |
| `.gitignore` | Keeps `data/`, `.env`, virtualenvs, build outputs, and dependency folders out of Git. |

## Data Contract

Raw files can use either layout:

```text
data/<model_folder>/<dataset>.jsonl
data/<model_folder>/<dataset_folder>/<dataset_file>.jsonl
```

For the flat layout, the dataset key is the JSONL filename without `.jsonl`. For the nested layout, the dataset key is the folder name, not the file name. Example: `data/Qwen3.5-4B/math500/results.jsonl` uses model `Qwen3.5-4B` and dataset `math500`.

If a model does not have a dataset file, that cell is treated as missing. Missing datasets are never counted as zero in averages.

## Dataset Usage

Keep benchmark outputs in `data/`. This folder is the raw-data input for the service and is intentionally ignored by Git.

### Supported Layouts

Flat layout:

```text
data/<model_folder>/<dataset>.jsonl
```

Example:

```text
data/Qwen3.5-4B/aime26.jsonl
```

Nested layout:

```text
data/<model_folder>/<dataset_folder>/<dataset_file>.jsonl
```

Example:

```text
data/Qwen3.5-4B/math500/results.jsonl
```

For flat files, the dataset key is the file name without `.jsonl`. For nested folders, the dataset key is the folder name. In the example above, the dataset is `math500`, not `results`.

If a nested dataset folder contains multiple JSONL files, they are treated as shards of the same model + dataset run and imported together.

### Updating Data

When you add or replace files under `data/`, run ingestion again:

```bash
cd backend
python -m app.ingest --data-dir ../data
```

The importer hashes source files. If the same model + dataset + hash was already imported successfully, it skips that data. If file content changes, it creates a new `evaluation_run`, and the APIs automatically use the latest successful run.

### Adding Or Changing Dataset Formats

If a new dataset uses a new JSONL schema, update the backend adapter layer:

1. Add or update an adapter in `backend/app/adapters/`.
2. Register the dataset in `backend/app/adapters/registry.py`.
3. Add the dataset and display order in `backend/app/dataset_categories.py`.
4. Rerun ingestion.

See `docs/adapter_development.md` for the full adapter workflow.

## Main Features

- 首页: grouped metric matrices for accuracy, average output length, and average inference time.
- Dataset selector: dropdown multi-select shared by all three homepage matrices.
- 错题分析: search and inspect model records by dataset, model, correctness, and keyword.
- 模型比较: compare two models on the same dataset and aligned item IDs.
- Adapters: each dataset has its own normalization logic so UI and API do not depend on raw JSON field names.
- Versioned imports: each changed source file or dataset folder creates a new `evaluation_run`; APIs use the latest successful run.

## Where To Change Things

| Task | Change Here |
|---|---|
| Add a new dataset format | Add an adapter in `backend/app/adapters/`, register it in `backend/app/adapters/registry.py`, and update categories in `backend/app/dataset_categories.py`. See `docs/adapter_development.md`. |
| Old dataset fields changed | Update the relevant adapter, then rerun ingestion. If the normalized schema itself changes, update `backend/app/models/benchmark.py` and create an Alembic migration. |
| Add/remove dataset categories or homepage columns | Update `backend/app/dataset_categories.py`. The frontend renders grouped columns from the metrics API response. |
| Change metric calculations | Update `backend/app/api/metrics.py` and, if needed, ingestion summary creation in `backend/app/ingest.py`. |
| Change homepage layout | Update `frontend/src/pages/Home.tsx` and related styles in `frontend/src/styles.css`. |
| Change wrong item search | Backend: `backend/app/api/records.py`; frontend: `frontend/src/pages/WrongItems.tsx`. |
| Change model comparison | Backend: `backend/app/api/compare.py`; frontend: `frontend/src/pages/Compare.tsx`. |
| Change API base URL | Set `VITE_API_BASE_URL` in frontend environment config. Do not hardcode service URLs in page components. |
| Change backend database/data settings | Edit `.env` values consumed by `backend/app/config.py`. |

## Local Development

### One-command start

For local development on a machine without Docker, use the bundled Bash script:

```bash
bash scripts/start-local.sh
```

The script will:

- create `backend/.env` from `backend/.env.example` if needed
- create `backend/.venv` if needed
- install backend Python dependencies
- run Alembic migrations
- import JSONL data from `data/`
- install frontend npm dependencies
- start FastAPI on `http://localhost:8000`
- start Vite on `http://localhost:5173`

PostgreSQL must already be installed and running locally. The script will try to create the `benchmark_dashboard` database if the `createdb` command is available. Use `Ctrl+C` to stop both backend and frontend.

Optional environment overrides:

```bash
BACKEND_PORT=8001 FRONTEND_PORT=5174 bash scripts/start-local.sh
```

To let another person on the same network open your local dev server, start with host binding enabled by the script, then share your machine IP and frontend port:

```text
http://<your-machine-ip>:5173
```

The frontend still needs to call a reachable backend URL. For shared access, set `VITE_API_BASE_URL` to your machine IP before starting the frontend, for example:

```bash
BACKEND_HOST=0.0.0.0 VITE_API_BASE_URL=http://192.168.1.20:8000 bash scripts/start-local.sh
```

Also set backend CORS to allow that frontend origin in `backend/.env`:

```text
CORS_ORIGINS=http://192.168.1.20:5173
```

For production, prefer a stable domain and HTTPS instead of a raw IP.

### Linux full-stack start with conda and Docker

On a Linux machine that has conda, Docker, Node.js, and npm, use:

```bash
bash scripts/start-linux.sh
```

This starts PostgreSQL through Docker, starts the FastAPI backend through conda,
then starts the React frontend with Vite. By default:

- backend listens on `0.0.0.0:8000`
- frontend listens on `0.0.0.0:5173`
- browser URL is `http://localhost:5173`
- frontend calls `http://localhost:8000`

For access from another machine, pass the Linux host IP or domain:

```bash
PUBLIC_HOST=192.168.1.50 bash scripts/start-linux.sh
```

Then open:

```text
http://192.168.1.50:5173
```

Useful overrides:

```bash
PUBLIC_HOST=192.168.1.50 BACKEND_PORT=8001 FRONTEND_PORT=5174 bash scripts/start-linux.sh
```

### Linux backend only with conda and Docker

If you only want the API service and database, use the backend-focused script:

```bash
bash scripts/start-linux-backend.sh
```

The script will:

- create `backend/.env` from `backend/.env.example` if needed
- start a PostgreSQL 16 Docker container unless one is already running
- create or reuse a conda environment named `benchmark-dashboard`
- install backend Python dependencies
- run Alembic migrations
- import JSONL data from `data/`
- start FastAPI on `http://0.0.0.0:8000`

It does not start the frontend. Use `scripts/start-linux.sh` when you want both
backend and frontend.

Useful overrides:

```bash
CONDA_ENV_NAME=benchdash BACKEND_PORT=8001 bash scripts/start-linux-backend.sh
```

If PostgreSQL is already available outside Docker, skip the container startup and
provide your database URL:

```bash
START_POSTGRES_DOCKER=0 \
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/benchmark_dashboard \
bash scripts/start-linux-backend.sh
```

### 1. PostgreSQL

Install PostgreSQL locally, then create the app database. One macOS example:

```bash
brew install postgresql@16
brew services start postgresql@16
createdb benchmark_dashboard
```

Use `backend/.env.example` as the starting point for backend settings.

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
alembic upgrade head
python -m app.ingest --data-dir ../data
uvicorn app.main:app --reload
```

The API defaults to `http://localhost:8000`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

The app defaults to `http://localhost:5173`.

## GitHub Upload Notes

Do not commit raw evaluation results. The repository should contain source code, docs, migrations, and deployment scaffolding. The `data/` directory is intentionally ignored. If sample data is ever needed, create a tiny sanitized fixture outside `data/`, for example `backend/tests/fixtures/`.
