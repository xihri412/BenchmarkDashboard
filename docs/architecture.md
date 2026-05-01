# Architecture

## Directory Layout

```text
BenchmarkDashboard/
  backend/   FastAPI service, database models, migrations
  frontend/  Vite React TypeScript client
  docs/      project documentation
  data/      existing benchmark data, kept in place
```

## Development Model

Local development runs without Docker:

- backend: Python virtual environment plus `uvicorn`
- frontend: Node package install plus Vite dev server

Docker Compose is present only as deployment scaffolding for a later Linux environment.
