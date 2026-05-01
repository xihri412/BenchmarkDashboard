import { useEffect, useRef, useState } from "react";

import {
  API_BASE_URL,
  getHealth,
  getMetricsMatrix,
  getOverallSummary,
  type MatrixMetric,
  type MetricsMatrixGroupColumn,
  type MetricsMatrixResponse,
  type MetricsMatrixRow,
  type OverallSummaryRow,
} from "../api/client";
import { Button } from "../components/Button";
import { Table, type TableColumn } from "../components/Table";
import { formatDatasetOptionLabel } from "../utils/dataset";

type HealthState = "idle" | "loading" | "ok" | "error";
type OverallState = "idle" | "loading" | "ok" | "error";
type MatrixState = "idle" | "loading" | "ok" | "error";

type MetricDefinition = {
  key: MatrixMetric;
  title: string;
};

type MetricRow = {
  name: string;
  value: string;
};

type MatrixMap = Record<MatrixMetric, MetricsMatrixResponse | null>;
type MatrixStateMap = Record<MatrixMetric, MatrixState>;
type MatrixMessageMap = Record<MatrixMetric, string>;
type OverallMap = Record<string, OverallSummaryRow>;
type DatasetCategory = {
  label: string;
  datasets: string[];
};

const metricDefinitions: MetricDefinition[] = [
  { key: "accuracy", title: "准确率矩阵" },
  { key: "avg_output_length", title: "平均输出长度矩阵" },
  { key: "avg_inference_time", title: "平均推理耗时矩阵" },
];

const datasetCategories: DatasetCategory[] = [
  {
    label: "学科知识",
    datasets: [
      "MMLU-Pro",
      "MMLU-Redux",
      "Supergpqa",
      "gpqa",
      "LPFQA",
      "FrontierSci-Olympiad",
      "Encyclo-k",
    ],
  },
  {
    label: "数学",
    datasets: [
      "AIME24",
      "aime25",
      "aime26",
      "hmmt-feb-25",
      "hmmt-nov-25",
      "hmmt-feb-26",
      "beyondaime",
      "imo-answerbench",
      "u-math",
    ],
  },
  { label: "逻辑推理", datasets: ["Zebralogic", "korbench"] },
  {
    label: "指令遵从/写作",
    datasets: [
      "IFEval",
      "IFBench",
      "multichallenge",
      "creativewriting",
      "writingbench",
      "arena-hardv2",
    ],
  },
  { label: "多语言", datasets: ["MMMLU-lite", "global-piqa", "disco-x"] },
  { label: "长序列", datasets: ["aa-lcr", "mrcr-v2", "ruler", "longbench"] },
  {
    label: "代码",
    datasets: [
      "livecodebench-v6",
      "livecodebench-pro",
      "artifactbench",
      "repoqa",
      "multipl-e",
    ],
  },
  { label: "工具调用", datasets: ["bfcl-v3", "tau2", "pinchbnch", "小艺中控"] },
  {
    label: "代码任务",
    datasets: ["swe-bench-verified", "terminalbench", "multi-swebench"],
  },
  { label: "搜索", datasets: ["browsecomp", "browsecomp-zn", "simpleqa", "c-simpleqa"] },
  { label: "STEM冒烟集", datasets: ["数学", "物理", "化学"] },
  { label: "医疗", datasets: ["supergpqa-med", "medmcqa", "medqa", "cmexam"] },
  { label: "金融", datasets: ["mmlu-econonmics", "fineval6.0"] },
  { label: "购物/美食", datasets: ["shoppingmmlu", "chineseecomqa", "foodbench"] },
  { label: "消费电子", datasets: ["eckgbench"] },
];

const allDatasets = datasetCategories.flatMap((category) => category.datasets);

const columns: TableColumn<MetricRow>[] = [
  { key: "name", header: "指标", render: (row) => row.name },
  { key: "value", header: "值", render: (row) => row.value },
];

const numberFormatter = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 2,
});

const accuracyFormatter = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  style: "percent",
});

function formatNumber(value: number | null | undefined) {
  if (value == null) {
    return "-";
  }

  return numberFormatter.format(value);
}

function formatAccuracy(value: number | null | undefined) {
  if (value == null) {
    return "-";
  }

  return accuracyFormatter.format(value);
}

function formatMetricValue(metric: MatrixMetric, value: number | null | undefined) {
  if (metric === "accuracy") {
    return formatAccuracy(value);
  }

  return formatNumber(value);
}

function buildMatrixColumns(
  metric: MatrixMetric,
  datasets: string[],
  overallByModel: OverallMap,
  showOverall: boolean,
): TableColumn<MetricsMatrixRow>[] {
  return [
    {
      key: "model",
      header: "模型",
      render: (row) => row.model,
    },
    ...(showOverall
      ? [
          {
            key: "overall",
            header: "总体",
            align: "right" as const,
            render: (row: MetricsMatrixRow) =>
              formatMetricValue(
                metric,
                row.values.__overall__ ?? overallByModel[row.model]?.[metric],
              ),
          },
        ]
      : []),
    ...datasets.map((dataset) => ({
      key: dataset,
      header: dataset,
      align: "right" as const,
      render: (row: MetricsMatrixRow) =>
        formatMetricValue(metric, row.values[dataset] ?? null),
    })),
  ];
}

const initialMatrixStates: MatrixStateMap = {
  accuracy: "idle",
  avg_output_length: "idle",
  avg_inference_time: "idle",
};

const initialMatrixMessages: MatrixMessageMap = {
  accuracy: "",
  avg_output_length: "",
  avg_inference_time: "",
};

type GroupedMatrixTableProps = {
  metric: MatrixMetric;
  matrix: MetricsMatrixResponse;
  overallByModel: OverallMap;
  emptyText: string;
  isSingleDatasetSelected: boolean;
};

function getGroupedCellClass(column: MetricsMatrixGroupColumn) {
  if (column.type === "overall") {
    return "emphasized-column";
  }

  if (column.type === "category_avg") {
    return "category-avg-column";
  }

  return "";
}

function getGroupedCellValue(
  metric: MatrixMetric,
  row: MetricsMatrixRow,
  column: MetricsMatrixGroupColumn,
  overallByModel: OverallMap,
) {
  if (column.key in row.values) {
    return row.values[column.key];
  }

  if (column.type === "overall" || column.key === "__overall__") {
    return overallByModel[row.model]?.[metric];
  }

  return null;
}

function GroupedMatrixTable({
  metric,
  matrix,
  overallByModel,
  emptyText,
  isSingleDatasetSelected,
}: GroupedMatrixTableProps) {
  const groups = matrix.groups ?? [];
  const hasOverallColumn = groups.some((group) =>
    group.columns.some(
      (column) => column.type === "overall" || column.key === "__overall__",
    ),
  );
  const displayedGroups = isSingleDatasetSelected
    ? groups
        .map((group) => ({
          ...group,
          columns: group.columns.filter((column) => column.type === "dataset"),
        }))
        .filter((group) => group.columns.length > 0)
    : hasOverallColumn
      ? groups
      : [
        {
          key: "overall",
          label: "总体",
          columns: [{ key: "__overall__", label: "总体", type: "overall" }],
        },
        ...groups,
      ];
  const columnCount = displayedGroups.reduce(
    (total, group) => total + group.columns.length,
    0,
  );

  return (
    <div className="table-wrap matrix-table-wrap">
      <table className="data-table matrix-table grouped-matrix-table">
        <thead>
          <tr>
            <th className="sticky-model matrix-model-header" rowSpan={2}>
              模型
            </th>
            {displayedGroups.map((group) => (
              <th
                className="align-center matrix-group-header"
                colSpan={group.columns.length}
                key={group.key}
              >
                {group.label}
              </th>
            ))}
          </tr>
          <tr>
            {displayedGroups.flatMap((group) =>
              group.columns.map((column) => (
                <th
                  className={`align-right ${getGroupedCellClass(column)}`}
                  key={`${group.key}-${column.key}`}
                >
                  {column.label}
                </th>
              )),
            )}
          </tr>
        </thead>
        <tbody>
          {matrix.rows.length === 0 ? (
            <tr>
              <td
                className="empty-cell"
                colSpan={1 + columnCount}
              >
                {emptyText}
              </td>
            </tr>
          ) : (
            matrix.rows.map((row) => (
              <tr key={row.model}>
                <td className="sticky-model matrix-model-cell">{row.model}</td>
                {displayedGroups.flatMap((group) =>
                  group.columns.map((column: MetricsMatrixGroupColumn) => (
                    <td
                      className={`align-right ${getGroupedCellClass(column)}`}
                      key={`${row.model}-${group.key}-${column.key}`}
                    >
                      {formatMetricValue(
                        metric,
                        getGroupedCellValue(metric, row, column, overallByModel),
                      )}
                    </td>
                  )),
                )}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

type DatasetSelectorProps = {
  selectedDatasets: Set<string>;
  onCategoryChange: (category: DatasetCategory, checked: boolean) => void;
  onDatasetChange: (dataset: string, checked: boolean) => void;
  onSelectAll: () => void;
  onClearAll: () => void;
};

type CategoryCheckboxProps = {
  category: DatasetCategory;
  hideLabel?: boolean;
  selectedDatasets: Set<string>;
  onChange: (category: DatasetCategory, checked: boolean) => void;
};

function CategoryCheckbox({
  category,
  hideLabel = false,
  selectedDatasets,
  onChange,
}: CategoryCheckboxProps) {
  const checkboxRef = useRef<HTMLInputElement>(null);
  const selectedCount = category.datasets.filter((dataset) =>
    selectedDatasets.has(dataset),
  ).length;
  const isChecked = selectedCount === category.datasets.length;
  const isIndeterminate =
    selectedCount > 0 && selectedCount < category.datasets.length;

  useEffect(() => {
    if (checkboxRef.current) {
      checkboxRef.current.indeterminate = isIndeterminate;
    }
  }, [isIndeterminate]);

  return (
    <label className="checkbox-label dataset-category-label">
      <input
        aria-label={hideLabel ? `${category.label}评测集` : undefined}
        checked={isChecked}
        onChange={(event) => onChange(category, event.target.checked)}
        ref={checkboxRef}
        type="checkbox"
      />
      {hideLabel ? null : <span>{category.label}</span>}
    </label>
  );
}

function DatasetSelector({
  selectedDatasets,
  onCategoryChange,
  onDatasetChange,
  onSelectAll,
  onClearAll,
}: DatasetSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    () => new Set(datasetCategories.map((category) => category.label)),
  );
  const selectorRef = useRef<HTMLDivElement>(null);
  const normalizedQuery = searchQuery.trim().toLowerCase();
  const selectedSummary =
    selectedDatasets.size === allDatasets.length
      ? "全部评测集"
      : selectedDatasets.size === 0
        ? "未选择评测集"
        : selectedDatasets.size === 1
          ? formatDatasetOptionLabel(Array.from(selectedDatasets)[0])
          : `已选择 ${selectedDatasets.size} 个评测集`;
  const filteredCategories = datasetCategories
    .map((category) => ({
      ...category,
      datasets: normalizedQuery
        ? category.datasets.filter((dataset) =>
            `${dataset} ${formatDatasetOptionLabel(dataset)}`
              .toLowerCase()
              .includes(normalizedQuery),
          )
        : category.datasets,
    }))
    .filter((category) => category.datasets.length > 0);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const handlePointerDown = (event: MouseEvent) => {
      if (!selectorRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  const toggleCategoryExpansion = (categoryLabel: string) => {
    setExpandedCategories((current) => {
      const next = new Set(current);

      if (next.has(categoryLabel)) {
        next.delete(categoryLabel);
      } else {
        next.add(categoryLabel);
      }

      return next;
    });
  };

  return (
    <section className="dataset-filter">
      <label className="filter-label" htmlFor="dataset-filter-button">
        评测集
      </label>
      <div className="dataset-dropdown" ref={selectorRef}>
        <button
          aria-expanded={isOpen}
          className="dataset-dropdown-trigger"
          id="dataset-filter-button"
          onClick={() => setIsOpen((current) => !current)}
          type="button"
        >
          <span>{selectedSummary}</span>
          <span aria-hidden="true" className="dropdown-caret">
            ▾
          </span>
        </button>

        {isOpen ? (
          <div className="dataset-dropdown-panel">
            <div className="dropdown-toolbar">
              <div className="selector-actions">
                <Button variant="secondary" onClick={onSelectAll}>
                  全选
                </Button>
                <Button variant="ghost" onClick={onClearAll}>
                  清空
                </Button>
              </div>
              <input
                aria-label="搜索评测集"
                className="control dataset-search"
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="搜索评测集"
                type="search"
                value={searchQuery}
              />
            </div>

            <div className="dataset-dropdown-list">
              {filteredCategories.length === 0 ? (
                <div className="dropdown-empty">暂无数据</div>
              ) : (
                filteredCategories.map((category) => {
                  const isExpanded = expandedCategories.has(category.label);

                  return (
                    <div className="dropdown-category" key={category.label}>
                      <div className="dropdown-category-header">
                        <CategoryCheckbox
                          category={
                            datasetCategories.find(
                              (item) => item.label === category.label,
                            ) ?? category
                          }
                          hideLabel
                          onChange={onCategoryChange}
                          selectedDatasets={selectedDatasets}
                        />
                        <button
                          className="category-toggle"
                          onClick={() => toggleCategoryExpansion(category.label)}
                          type="button"
                        >
                          <span>{category.label}</span>
                          <span aria-hidden="true">
                            {isExpanded ? "−" : "+"}
                          </span>
                        </button>
                      </div>
                      {isExpanded ? (
                        <div className="dataset-option-list">
                          {category.datasets.map((dataset) => (
                            <label
                              className="checkbox-label dataset-option"
                              key={dataset}
                            >
                              <input
                                checked={selectedDatasets.has(dataset)}
                                onChange={(event) =>
                                  onDatasetChange(dataset, event.target.checked)
                                }
                                type="checkbox"
                              />
                              <span>{formatDatasetOptionLabel(dataset)}</span>
                            </label>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  );
                })
              )}
            </div>

            <div className="dropdown-footer">
              <span>
                已选择 {selectedDatasets.size} / {allDatasets.length}
              </span>
              <Button variant="primary" onClick={() => setIsOpen(false)}>
                完成
              </Button>
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}

export function Home() {
  const [status, setStatus] = useState<HealthState>("idle");
  const [message, setMessage] = useState("尚未检查");
  const [overallStatus, setOverallStatus] = useState<OverallState>("idle");
  const [overallMessage, setOverallMessage] = useState("");
  const [overallRows, setOverallRows] = useState<OverallSummaryRow[]>([]);
  const [matrixStatuses, setMatrixStatuses] =
    useState<MatrixStateMap>(initialMatrixStates);
  const [matrixMessages, setMatrixMessages] =
    useState<MatrixMessageMap>(initialMatrixMessages);
  const [isDebugExpanded, setIsDebugExpanded] = useState(false);
  const [selectedDatasets, setSelectedDatasets] = useState<Set<string>>(
    () => new Set(allDatasets),
  );
  const [matrices, setMatrices] = useState<MatrixMap>({
    accuracy: null,
    avg_output_length: null,
    avg_inference_time: null,
  });

  const checkHealth = async () => {
    setStatus("loading");

    try {
      const response = await getHealth();
      setStatus("ok");
      setMessage(response.status);
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "加载失败");
    }
  };

  const loadOverall = async () => {
    setOverallStatus("loading");
    setOverallMessage("");

    try {
      const response = await getOverallSummary();
      setOverallRows(response.rows);
      setOverallStatus("ok");
    } catch (error) {
      setOverallStatus("error");
      setOverallMessage(error instanceof Error ? error.message : "加载失败");
    }
  };

  const loadMatrices = async (nextSelectedDatasets: Set<string>) => {
    if (nextSelectedDatasets.size === 0) {
      setMatrices({
        accuracy: null,
        avg_output_length: null,
        avg_inference_time: null,
      });
      setMatrixStatuses({
        accuracy: "ok",
        avg_output_length: "ok",
        avg_inference_time: "ok",
      });
      setMatrixMessages(initialMatrixMessages);
      return;
    }

    const datasetFilter =
      nextSelectedDatasets.size === allDatasets.length
        ? undefined
        : allDatasets.filter((dataset) => nextSelectedDatasets.has(dataset));

    setMatrixStatuses({
      accuracy: "loading",
      avg_output_length: "loading",
      avg_inference_time: "loading",
    });
    setMatrixMessages(initialMatrixMessages);

    const results = await Promise.all(
      metricDefinitions.map(async (metric) => {
        try {
          return {
            metric: metric.key,
            response: await getMetricsMatrix(metric.key, datasetFilter),
            status: "ok" as MatrixState,
            message: "",
          };
        } catch (error) {
          return {
            metric: metric.key,
            response: null,
            status: "error" as MatrixState,
            message: error instanceof Error ? error.message : "加载失败",
          };
        }
      }),
    );

    setMatrices((current) =>
      results.reduce<MatrixMap>(
        (next, result) => ({
          ...next,
          [result.metric]: result.response,
        }),
        current,
      ),
    );
    setMatrixStatuses((current) =>
      results.reduce<MatrixStateMap>(
        (next, result) => ({
          ...next,
          [result.metric]: result.status,
        }),
        current,
      ),
    );
    setMatrixMessages((current) =>
      results.reduce<MatrixMessageMap>(
        (next, result) => ({
          ...next,
          [result.metric]: result.message,
        }),
        current,
      ),
    );
  };

  useEffect(() => {
    void loadOverall();
    void loadMatrices(selectedDatasets);
  }, []);

  const updateSelectedDatasets = (nextSelectedDatasets: Set<string>) => {
    setSelectedDatasets(nextSelectedDatasets);
    void loadMatrices(nextSelectedDatasets);
  };

  const handleCategoryChange = (
    category: DatasetCategory,
    checked: boolean,
  ) => {
    const nextSelectedDatasets = new Set(selectedDatasets);

    category.datasets.forEach((dataset) => {
      if (checked) {
        nextSelectedDatasets.add(dataset);
      } else {
        nextSelectedDatasets.delete(dataset);
      }
    });

    updateSelectedDatasets(nextSelectedDatasets);
  };

  const handleDatasetChange = (dataset: string, checked: boolean) => {
    const nextSelectedDatasets = new Set(selectedDatasets);

    if (checked) {
      nextSelectedDatasets.add(dataset);
    } else {
      nextSelectedDatasets.delete(dataset);
    }

    updateSelectedDatasets(nextSelectedDatasets);
  };

  const handleSelectAll = () => {
    updateSelectedDatasets(new Set(allDatasets));
  };

  const handleClearAll = () => {
    updateSelectedDatasets(new Set());
  };

  const toggleDebug = () => {
    const nextExpanded = !isDebugExpanded;
    setIsDebugExpanded(nextExpanded);

    if (nextExpanded && status === "idle") {
      void checkHealth();
    }
  };

  const overallByModel = overallRows.reduce<OverallMap>((accumulator, row) => {
    accumulator[row.model] = row;
    return accumulator;
  }, {});
  const isSingleDatasetSelected = selectedDatasets.size === 1;
  const noDatasetsSelected = selectedDatasets.size === 0;

  const rows = [
    { name: "API 基础地址", value: API_BASE_URL },
    { name: "健康检查接口", value: "/api/health" },
    { name: "后端状态", value: message },
    {
      name: "总体指标接口",
      value:
        overallStatus === "error"
          ? overallMessage
          : `/api/metrics/overall (${overallStatus})`,
    },
  ];

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">总览</p>
          <h1>首页</h1>
        </div>
      </header>

      <DatasetSelector
        onCategoryChange={handleCategoryChange}
        onClearAll={handleClearAll}
        onDatasetChange={handleDatasetChange}
        onSelectAll={handleSelectAll}
        selectedDatasets={selectedDatasets}
      />

      <section className="dashboard-stack dashboard-primary">
        {metricDefinitions.map((metric) => {
          const matrix = matrices[metric.key];
          const matrixStatus = matrixStatuses[metric.key];
          const matrixMessage = matrixMessages[metric.key];
          const tableColumns = buildMatrixColumns(
            metric.key,
            matrix?.datasets ?? [],
            overallByModel,
            !isSingleDatasetSelected,
          );

          return (
            <section className="dashboard-section" key={metric.key}>
              <div className="section-header">
                <h2>{metric.title}</h2>
                {matrixStatus === "loading" ||
                (!matrix?.groups?.length && overallStatus === "loading") ? (
                  <span className="section-note">加载中</span>
                ) : null}
              </div>
              {noDatasetsSelected ? (
                <div className="empty-state">请至少选择一个评测集</div>
              ) : matrixStatus === "error" ? (
                <div className="status-banner status-error">
                  <span className="status-dot" />
                  <span>{matrixMessage}</span>
                </div>
              ) : matrix?.groups?.length ? (
                <GroupedMatrixTable
                  metric={metric.key}
                  matrix={matrix}
                  overallByModel={overallByModel}
                  emptyText="暂无数据"
                  isSingleDatasetSelected={isSingleDatasetSelected}
                />
              ) : (
                <Table
                  columns={tableColumns}
                  data={matrix?.rows ?? []}
                  emptyText={
                    matrixStatus === "loading" ? "加载中" : "暂无数据"
                  }
                />
              )}
            </section>
          );
        })}
      </section>

      <section className="dashboard-section debug-panel">
        <div className="section-header">
          <h2>调试信息</h2>
          <Button variant="secondary" onClick={toggleDebug}>
            {isDebugExpanded ? "收起调试信息" : "展开调试信息"}
          </Button>
        </div>

        {isDebugExpanded ? (
          <div className="overview-grid">
            <div className={`status-banner status-${status}`}>
              <span className="status-dot" />
              <span>
                后端健康状态：<strong>{message}</strong>
              </span>
            </div>
            <Table columns={columns} data={rows} />
          </div>
        ) : null}
      </section>
    </section>
  );
}
