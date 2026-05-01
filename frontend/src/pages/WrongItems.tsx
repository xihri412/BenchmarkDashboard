import { useEffect, useMemo, useState } from "react";

import {
  getMetricsMatrix,
  searchRecords,
  type BenchmarkRecord,
  type MetricsMatrixResponse,
} from "../api/client";
import { Button } from "../components/Button";
import { SearchInput, Select } from "../components/Inputs";
import { Table, type TableColumn } from "../components/Table";
import { formatDatasetOptionLabel } from "../utils/dataset";

type LoadState = "idle" | "loading" | "ok" | "error";

const pageSize = 20;
const refreshIntervalMs = 5000;

const correctnessOptions = [
  { label: "仅错误", value: "false" },
  { label: "全部状态", value: "" },
  { label: "正确", value: "true" },
  { label: "未知", value: "unknown" },
];

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }

  if (typeof value === "string") {
    return value;
  }

  return JSON.stringify(value, null, 2);
}

function correctnessLabel(value: boolean | null) {
  if (value === true) return "正确";
  if (value === false) return "错误";
  return "未知";
}

function buildColumns(onOpen: (item: BenchmarkRecord) => void): TableColumn<BenchmarkRecord>[] {
  return [
    {
      key: "item_id",
      header: "题目",
      render: (row) => (
        <button className="link-button" type="button" onClick={() => onOpen(row)}>
          {row.item_id}
        </button>
      ),
    },
    { key: "model", header: "模型", render: (row) => row.model },
    { key: "dataset", header: "评测集", render: (row) => row.dataset },
    {
      key: "correctness",
      header: "状态",
      render: (row) => (
        <span className={`pill pill-${row.is_correct === false ? "bad" : "neutral"}`}>
          {correctnessLabel(row.is_correct)}
        </span>
      ),
    },
    {
      key: "target",
      header: "目标答案",
      render: (row) => <span className="table-snippet">{formatValue(row.target_json)}</span>,
    },
    {
      key: "output",
      header: "输出",
      render: (row) => <span className="table-snippet">{formatValue(row.output)}</span>,
    },
  ];
}

export function WrongItems() {
  const [metadata, setMetadata] = useState<MetricsMatrixResponse | null>(null);
  const [dataset, setDataset] = useState("");
  const [model, setModel] = useState("");
  const [correctness, setCorrectness] = useState("false");
  const [keyword, setKeyword] = useState("");
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<BenchmarkRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [status, setStatus] = useState<LoadState>("idle");
  const [message, setMessage] = useState("");
  const [selectedItem, setSelectedItem] = useState<BenchmarkRecord | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);

  useEffect(() => {
    let isMounted = true;

    getMetricsMatrix("accuracy")
      .then((response) => {
        if (!isMounted) return;
        setMetadata(response);
        setDataset((current) => current || response.datasets[0] || "");
        setModel((current) => current || response.models[0] || "");
      })
      .catch((error) => {
        if (!isMounted) return;
        setStatus("error");
        setMessage(error instanceof Error ? error.message : "加载失败");
      });

    return () => {
      isMounted = false;
    };
  }, [refreshTick]);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      setRefreshTick((current) => current + 1);
    }, refreshIntervalMs);

    return () => window.clearInterval(intervalId);
  }, []);

  useEffect(() => {
    setPage(1);
  }, [dataset, model, correctness, keyword]);

  useEffect(() => {
    if (!dataset || !model) {
      return;
    }

    let isMounted = true;
    setStatus("loading");
    setMessage("");

    searchRecords({
      dataset,
      model,
      correct: correctness,
      keyword,
      page,
      pageSize,
    })
      .then((response) => {
        if (!isMounted) return;
        setItems(response.items);
        setTotal(response.total);
        setTotalPages(response.total_pages);
        setStatus("ok");
      })
      .catch((error) => {
        if (!isMounted) return;
        setStatus("error");
        setMessage(error instanceof Error ? error.message : "加载失败");
      });

    return () => {
      isMounted = false;
    };
  }, [correctness, dataset, keyword, model, page, refreshTick]);

  const columns = useMemo(() => buildColumns(setSelectedItem), []);

  const datasetOptions = (metadata?.datasets ?? []).map((name) => ({
    label: formatDatasetOptionLabel(name),
    value: name,
  }));
  const modelOptions = (metadata?.models ?? []).map((name) => ({
    label: name,
    value: name,
  }));

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">分析</p>
          <h1>错题分析</h1>
        </div>
        <span className="section-note">共 {total} 条</span>
      </header>

      <div className="toolbar toolbar-four">
        <Select
          aria-label="评测集"
          value={dataset}
          onChange={(event) => setDataset(event.target.value)}
          options={datasetOptions}
        />
        <Select
          aria-label="模型"
          value={model}
          onChange={(event) => setModel(event.target.value)}
          options={modelOptions}
        />
        <Select
          aria-label="状态"
          value={correctness}
          onChange={(event) => setCorrectness(event.target.value)}
          options={correctnessOptions}
        />
        <SearchInput
          aria-label="关键词"
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          placeholder="搜索题干、输出、题目"
        />
      </div>

      {status === "error" ? (
        <div className="status-banner status-error">
          <span className="status-dot" />
          <span>{message}</span>
        </div>
      ) : null}

      <Table
        columns={columns}
        data={items}
        emptyText={status === "loading" ? "加载中" : "暂无数据"}
      />

      <div className="pagination">
        <Button
          variant="secondary"
          disabled={page <= 1 || status === "loading"}
          onClick={() => setPage((current) => Math.max(1, current - 1))}
        >
          上一页
        </Button>
        <span>
          第 {page} / {Math.max(totalPages, 1)} 页
        </span>
        <Button
          variant="secondary"
          disabled={page >= totalPages || status === "loading"}
          onClick={() => setPage((current) => current + 1)}
        >
          下一页
        </Button>
      </div>

      {selectedItem ? (
        <div className="drawer-backdrop" role="presentation" onClick={() => setSelectedItem(null)}>
          <aside
            aria-label="错题详情"
            className="drawer"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="drawer-header">
              <div>
                <p className="eyebrow">{selectedItem.dataset}</p>
                <h2>{selectedItem.item_id}</h2>
              </div>
              <Button variant="ghost" onClick={() => setSelectedItem(null)}>
                关闭
              </Button>
            </div>

            <DetailBlock title="题干" value={selectedItem.prompt} />
            <DetailBlock title="目标答案" value={selectedItem.target_json} />
            <DetailBlock title="输出" value={selectedItem.output} />
            <DetailBlock title="原始输出" value={selectedItem.raw_output} />
            <DetailBlock title="原始 JSON" value={selectedItem.original_json} />
          </aside>
        </div>
      ) : null}
    </section>
  );
}

function DetailBlock({ title, value }: { title: string; value: unknown }) {
  return (
    <section className="detail-block">
      <h3>{title}</h3>
      <pre>{formatValue(value)}</pre>
    </section>
  );
}
