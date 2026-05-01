# Frontend Details

The frontend is a Vite + React + TypeScript dashboard. It does not read `data/` directly. It calls FastAPI endpoints and renders homepage matrices, wrong item analysis, and model comparison.

## File Map

| Path | Purpose |
|---|---|
| `src/main.tsx` | React entrypoint. Mounts the app into `index.html`. |
| `src/App.tsx` | Top-level app state for route resolution and layout composition. |
| `src/layout/AppLayout.tsx` | Shared shell: sidebar brand, navigation, and main content area. |
| `src/router/routes.ts` | Route definitions and Chinese navigation labels: 首页, 错题分析, 模型比较. |
| `src/router/useRoute.ts` | Browser location helper used by `App.tsx`. |
| `src/api/client.ts` | Central API client, base URL, request wrapper, API functions, and response types. |
| `src/pages/Home.tsx` | 首页. Dataset multi-select dropdown, grouped metric matrices, formatting, and debug panel. |
| `src/pages/WrongItems.tsx` | 错题分析 page. Dataset/model/status/keyword filters, paginated results, and detail drawer. |
| `src/pages/Compare.tsx` | 模型比较 page. Dataset/model A/model B/pattern filters and side-by-side output comparison. |
| `src/components/Button.tsx` | Shared button component. |
| `src/components/Inputs.tsx` | Shared select and search input components. |
| `src/components/Table.tsx` | Shared basic table component. Homepage grouped matrices use custom markup in `Home.tsx`. |
| `src/utils/dataset.ts` | Dataset display helper for selector labels, such as uppercasing only the first character when needed. |
| `src/styles.css` | Main application styles: layout, tables, dropdowns, drawers, compare grid, status pills, and debug panel. |
| `src/vite-env.d.ts` | Vite TypeScript environment declarations. |
| `index.html` | HTML entrypoint for Vite. |
| `vite.config.ts` | Vite configuration source. |
| `package.json` | npm scripts and frontend dependencies. |
| `.env` | Local frontend environment. Should not contain secrets; prefer `.env.local` for machine-specific overrides. |
| `Dockerfile` | Future production frontend image. |
| `nginx.conf` | Nginx config used by the frontend container. |

There are duplicate/generated files currently visible, such as `Compare 2.tsx`, `WrongItems 2.tsx`, `styles 2.css`, `vite.config.js`, `vite.config.d.ts`, and `*.tsbuildinfo`. Treat these as cleanup candidates unless a maintainer confirms they are intentional. The active imports use `Compare.tsx`, `WrongItems.tsx`, `styles.css`, and `vite.config.ts`.

## API Configuration

The API base URL is read in `src/api/client.ts`:

```ts
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
```

For local development, set:

```text
VITE_API_BASE_URL=http://localhost:8000
```

Do not hardcode backend URLs in page components. Add new API functions and types in `src/api/client.ts`.

## Page Responsibilities

### 首页: `src/pages/Home.tsx`

The homepage renders three metric matrices:

- 准确率矩阵
- 平均输出长度矩阵
- 平均推理耗时矩阵

It also owns the dataset dropdown multi-select. The same selected dataset set is applied to all three metrics. If all datasets are selected, matrix API requests omit the `datasets` parameter. If a subset is selected, requests include `datasets=a,b,c`. If no dataset is selected, API requests are skipped and an empty state is shown.

Important sections in `Home.tsx`:

| Section | Purpose |
|---|---|
| `metricDefinitions` | Controls the three metric tables and their titles. |
| `datasetCategories` | Frontend copy of category labels and dataset order for the dropdown. Keep aligned with backend `app/dataset_categories.py`. |
| `DatasetSelector` | Dropdown multi-select UI with category checkbox, dataset checkbox, search, select all, clear, and done actions. |
| `GroupedMatrixTable` | Two-level grouped table header and matrix cell rendering. |
| `formatMetricValue` | Accuracy percentage and numeric formatting. |
| Debug panel | Collapsed API/health information shown only when expanded. |

To change homepage layout, edit `Home.tsx` and styles in `src/styles.css`.

### 错题分析: `src/pages/WrongItems.tsx`

This page calls `getMetricsMatrix("accuracy")` to populate dataset/model selectors, then calls `searchRecords()` for paginated records.

To change filters or result columns:

- Frontend: `src/pages/WrongItems.tsx`
- Backend: `backend/app/api/records.py`
- API types: `src/api/client.ts`

Dataset option labels use `formatDatasetOptionLabel()` for display only. API requests still use the real dataset key.

### 模型比较: `src/pages/Compare.tsx`

This page calls `getMetricsMatrix("accuracy")` for selector metadata, then calls `compareRecords()` to align two models on the same dataset.

To add a comparison pattern:

1. Add backend logic in `backend/app/api/compare.py`.
2. Update `ComparePattern` in `src/api/client.ts`.
3. Add a label in `patternOptions` in `src/pages/Compare.tsx`.

Dataset option labels use display formatting only; API requests still use the original dataset key.

## Adding Or Changing UI Features

| Change | Primary Files |
|---|---|
| Rename navigation item | `src/router/routes.ts`; if layout changes, also `src/layout/AppLayout.tsx`. |
| Change homepage matrix columns/formatting | `src/pages/Home.tsx`. Backend column data comes from `GET /api/metrics/matrix`. |
| Change dataset selector behavior | `DatasetSelector` in `src/pages/Home.tsx` and related CSS. |
| Change table styling | `src/styles.css`; shared simple table is `src/components/Table.tsx`. |
| Change wrong item detail drawer | `src/pages/WrongItems.tsx`. |
| Change model comparison detail layout | `src/pages/Compare.tsx`. |
| Add API call | `src/api/client.ts`, then consume it in the target page. |
| Change dataset display labels | `src/utils/dataset.ts` for selector-specific formatting, or backend `display_name` if labels should come from API. |

## New Data Or Changed Data Format

The frontend should not be edited for raw data format changes. Update the backend adapter layer instead:

1. Add or update an adapter under `backend/app/adapters/`.
2. Register the dataset in `backend/app/adapters/registry.py`.
3. Add the dataset to `backend/app/dataset_categories.py` if it should appear on the homepage.
4. Rerun ingestion.
5. The frontend should automatically see it through metrics/search/compare APIs.

Only edit frontend dataset category data if the dropdown category UI must be changed. Keep `Home.tsx` category order aligned with `backend/app/dataset_categories.py`.

## Local Run

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Build

```bash
cd frontend
npm run build
```

Do not commit `node_modules/`, `dist/`, `.env.local`, or TypeScript build info files.
