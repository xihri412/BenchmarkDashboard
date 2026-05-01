# Backend Details

The backend is a FastAPI service that imports benchmark JSONL files, normalizes each dataset through adapters, stores results in PostgreSQL, and serves query APIs for the dashboard.

## Runtime Responsibilities

- Read configuration from environment variables.
- Connect to PostgreSQL through SQLAlchemy.
- Run Alembic migrations.
- Import raw JSONL files from `DATA_DIR`.
- Normalize raw rows through dataset adapters.
- Store models, datasets, evaluation runs, records, and metric summaries.
- Serve metrics, wrong item search, model comparison, and health APIs.

## File Map

| Path | Purpose |
|---|---|
| `app/main.py` | FastAPI application entrypoint. Adds CORS and mounts API routers under `/api`. |
| `app/config.py` | Runtime settings: app name, `DATABASE_URL`, `DATA_DIR`, auto-ingest behavior, refresh interval, and CORS origins. |
| `app/database.py` | SQLAlchemy engine/session helpers used by API dependencies and ingestion. |
| `app/db/base.py` | Declarative SQLAlchemy base imported by models and migrations. |
| `app/db/session.py` | Secondary database session setup used by the db package. Keep aligned with `app/database.py` if consolidating later. |
| `app/models/benchmark.py` | Database models: `Model`, `Dataset`, `EvaluationRun`, `Record`, and `MetricsSummary`. |
| `app/ingest.py` | Scans `data/`, computes source hashes, imports flat and nested JSONL layouts, creates runs, records, and metric summaries. |
| `app/data_sync.py` | Auto-sync dependency used by API routes to refresh imported data when configured. |
| `app/dataset_categories.py` | Fixed dataset category/order config used by homepage grouped matrices. |
| `app/adapters/base.py` | Adapter protocol and `NormalizedRecord` contract. |
| `app/adapters/common.py` | Small conversion helpers for adapter implementations. |
| `app/adapters/aime26.py` | Adapter for `aime26` rows. |
| `app/adapters/gpqa.py` | Adapter for `gpqa` rows. |
| `app/adapters/ifeval.py` | Adapter for `ifeval` rows. |
| `app/adapters/korbench.py` | Adapter for `korbench` rows. |
| `app/adapters/registry.py` | Dataset registry. Add new dataset configs here after creating an adapter. |
| `app/api/health.py` | `GET /api/health`. |
| `app/api/metrics.py` | Matrix and overall metrics APIs. Handles dataset filtering, grouped columns, overall values, and category averages. |
| `app/api/records.py` | `GET /api/records/search` for wrong item and record search. |
| `app/api/compare.py` | `GET /api/compare` for two-model item alignment and comparison. |
| `alembic/env.py` | Alembic migration environment. Imports app metadata. |
| `alembic/versions/20260501_0001_create_benchmark_tables.py` | Initial database schema migration. |
| `alembic.ini` | Alembic configuration. |
| `requirements.txt` | Python dependencies for local and Docker installs. |
| `pyproject.toml` | Python project metadata/tooling configuration. |
| `.env.example` | Example backend environment variables. |
| `Dockerfile` | Future container image build for Linux deployment. |

Ignore generated folders such as `.venv/`, `__pycache__/`, and local `.env` files. They should not be committed.

## Database Tables

| Table | Purpose |
|---|---|
| `models` | One row per model folder name. |
| `datasets` | One row per supported dataset key/adapter. |
| `evaluation_runs` | One import version for a model + dataset + source hash. |
| `records` | Normalized per-item model outputs, answers, correctness, timing, token length, and original JSON. |
| `metrics_summary` | Per-run aggregate accuracy, average output length, average inference time, total count, and correct count. |

APIs use the latest successful run per model + dataset. This preserves history while making the dashboard show the newest imported data.

## Data Import Logic

`app/ingest.py` supports:

```text
data/<model>/<dataset>.jsonl
data/<model>/<dataset_folder>/*.jsonl
```

Flat files create one import source per JSONL. Nested folders create one import source per model + dataset folder; multiple JSONL files in that folder are treated as one dataset run and hashed together. If a successful run with the same source hash already exists, ingestion skips it.

Run manually:

```bash
cd backend
python -m app.ingest --data-dir ../data
```

## Adding New Data

If new files follow an already supported format:

1. Put files under `data/<model>/<dataset>.jsonl` or `data/<model>/<dataset_folder>/*.jsonl`.
2. Confirm the dataset key exists in `app/adapters/registry.py`.
3. Run `python -m app.ingest --data-dir ../data`.
4. Check `GET /api/metrics/matrix?metric=accuracy`.

If the dataset is new or the raw fields changed:

1. Inspect several JSONL rows.
2. Add or update an adapter in `app/adapters/`.
3. Register it in `app/adapters/registry.py`.
4. Add or update its category/order in `app/dataset_categories.py`.
5. Rerun ingestion.
6. Validate metrics, search, and compare APIs.

Use `docs/adapter_development.md` as the detailed adapter checklist.

## Changing Features

| Change | Primary Files |
|---|---|
| Add new normalized record field | `app/adapters/base.py`, adapters, `app/models/benchmark.py`, Alembic migration, serializers in API routes. |
| Change accuracy/output/time calculation | `app/ingest.py` for stored summary values and `app/api/metrics.py` for weighted overall/category logic. |
| Add a new homepage metric | `app/api/metrics.py`, frontend API types, and `frontend/src/pages/Home.tsx`. |
| Change category names or dataset order | `app/dataset_categories.py`. |
| Change search filters | `app/api/records.py`, then `frontend/src/pages/WrongItems.tsx`. |
| Change compare alignment or patterns | `app/api/compare.py`, then `frontend/src/pages/Compare.tsx`. |
| Add admin ingestion API | Add a new router under `app/api/` and include it in `app/main.py`. |

## API Summary

| API | Purpose |
|---|---|
| `GET /api/health` | Health check. |
| `GET /api/metrics/overall` | Overall per-model summaries. |
| `GET /api/metrics/matrix?metric=accuracy` | Accuracy matrix. Supports optional `datasets=a,b`. |
| `GET /api/metrics/matrix?metric=avg_output_length` | Average output length matrix. Supports optional `datasets=a,b`. |
| `GET /api/metrics/matrix?metric=avg_inference_time` | Average inference time matrix. Supports optional `datasets=a,b`. |
| `GET /api/records/search` | Record/wrong item search with dataset, model, correctness, keyword, and pagination. |
| `GET /api/compare` | Two-model comparison by dataset and item ID. |

## Local Run

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
python -m app.ingest --data-dir ../data
uvicorn app.main:app --reload
```

For deployment details, see `docs/running.md`.

## Linux Backend Run With Conda

For a Linux machine where the backend is the main workload and conda + Docker
are available, run this from the repository root:

```bash
bash scripts/start-linux-backend.sh
```

This script is backend-only. It does not start the React frontend. To start both
backend and frontend on Linux, run:

```bash
bash scripts/start-linux.sh
```

Defaults:

- conda environment: `benchmark-dashboard`
- Python version: `3.12`
- PostgreSQL: Docker container `benchmark-dashboard-postgres`
- database URL: `postgresql+psycopg://postgres:postgres@localhost:5432/benchmark_dashboard`
- backend bind address: `0.0.0.0:8000`

Common overrides:

```bash
CONDA_ENV_NAME=benchdash BACKEND_PORT=8001 bash scripts/start-linux-backend.sh
```

If the Linux host already has PostgreSQL running, skip the Docker container:

```bash
START_POSTGRES_DOCKER=0 \
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/benchmark_dashboard \
bash scripts/start-linux-backend.sh
```
