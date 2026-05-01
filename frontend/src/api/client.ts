export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "错误";
    this.status = status;
  }
}

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);

  if (options.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    body:
      options.body === undefined ? undefined : JSON.stringify(options.body),
  });

  if (!response.ok) {
    const fallback = `请求失败，状态码 ${response.status}`;
    let message = fallback;

    try {
      const payload = (await response.json()) as { detail?: string };
      message = payload.detail ?? fallback;
    } catch {
      message = fallback;
    }

    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const apiClient = {
  get: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "POST", body }),
};

export type HealthResponse = {
  status: string;
};

export function getHealth() {
  return apiClient.get<HealthResponse>("/api/health");
}

export type OverallSummaryRow = {
  model: string;
  accuracy: number | null;
  avg_output_length: number | null;
  avg_inference_time: number | null;
  dataset_count: number | null;
  total_count: number | null;
  correct_count: number | null;
};

export type OverallSummaryResponse = {
  rows: OverallSummaryRow[];
};

export function getOverallSummary() {
  return apiClient.get<OverallSummaryResponse>("/api/metrics/overall");
}

export type MatrixMetric =
  | "accuracy"
  | "avg_output_length"
  | "avg_inference_time";

export type MetricsMatrixRow = {
  model: string;
  values: Record<string, number | null>;
};

export type MetricsMatrixGroupColumn = {
  key: string;
  label: string;
  type: "category_avg" | "dataset" | string;
};

export type MetricsMatrixGroup = {
  key: string;
  label: string;
  columns: MetricsMatrixGroupColumn[];
};

export type MetricsMatrixResponse = {
  datasets: string[];
  groups?: MetricsMatrixGroup[];
  models: string[];
  rows: MetricsMatrixRow[];
};

export function getMetricsMatrix(metric: MatrixMetric, datasets?: string[]) {
  const params = new URLSearchParams({ metric });

  if (datasets?.length) {
    params.set("datasets", datasets.join(","));
  }

  return apiClient.get<MetricsMatrixResponse>(`/api/metrics/matrix?${params}`);
}

export type BenchmarkRecord = {
  id: number;
  run_id: number;
  model: string;
  model_display_name: string;
  dataset: string;
  dataset_display_name: string;
  item_id: string;
  item_index: number | null;
  question: string | null;
  prompt: string | null;
  target_json: unknown;
  output: string | null;
  raw_output: string | null;
  is_correct: boolean | null;
  output_length: number | null;
  inference_time: number | null;
  original_json: unknown;
};

export type PaginatedResponse<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export type SearchRecordsParams = {
  dataset?: string;
  model?: string;
  correct?: string;
  keyword?: string;
  page?: number;
  pageSize?: number;
};

export function searchRecords(params: SearchRecordsParams) {
  const query = new URLSearchParams();

  if (params.dataset) query.set("dataset", params.dataset);
  if (params.model) query.set("model", params.model);
  if (params.correct) query.set("correct", params.correct);
  if (params.keyword) query.set("keyword", params.keyword);
  if (params.page) query.set("page", String(params.page));
  if (params.pageSize) query.set("page_size", String(params.pageSize));

  return apiClient.get<PaginatedResponse<BenchmarkRecord>>(
    `/api/records/search?${query}`,
  );
}

export type ComparePattern =
  | "all"
  | "a_correct_b_wrong"
  | "a_wrong_b_correct"
  | "both_correct"
  | "both_wrong";

export type CompareModelResult = {
  model: string;
  output: string | null;
  raw_output: string | null;
  correct: boolean | null;
  length: number | null;
  time: number | null;
  missing?: boolean;
};

export type CompareItem = {
  dataset: string;
  dataset_display_name: string;
  item_id: string;
  item_index: number | null;
  question: string | null;
  prompt: string | null;
  target: unknown;
  target_json: unknown;
  model_a: CompareModelResult;
  model_b: CompareModelResult;
};

export type CompareRecordsParams = {
  dataset: string;
  modelA: string;
  modelB: string;
  pattern?: ComparePattern;
  keyword?: string;
  page?: number;
  pageSize?: number;
};

export function compareRecords(params: CompareRecordsParams) {
  const query = new URLSearchParams({
    dataset: params.dataset,
    model_a: params.modelA,
    model_b: params.modelB,
    pattern: params.pattern ?? "all",
  });

  if (params.keyword) query.set("keyword", params.keyword);
  if (params.page) query.set("page", String(params.page));
  if (params.pageSize) query.set("page_size", String(params.pageSize));

  return apiClient.get<
    PaginatedResponse<CompareItem> & {
      dataset: string;
      model_a: string;
      model_b: string;
      pattern: ComparePattern;
    }
  >(`/api/compare?${query}`);
}
