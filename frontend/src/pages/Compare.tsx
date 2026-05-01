import { useEffect, useMemo, useState } from "react";

import {
  compareRecords,
  getMetricsMatrix,
  type CompareItem,
  type ComparePattern,
  type MetricsMatrixResponse,
} from "../api/client";
import { Button } from "../components/Button";
import { SearchInput, Select } from "../components/Inputs";
import { formatDatasetOptionLabel } from "../utils/dataset";

type LoadState = "idle" | "loading" | "ok" | "error";

const pageSize = 30;
const refreshIntervalMs = 5000;

const patternOptions: { label: string; value: ComparePattern }[] = [
  { label: "全部模式", value: "all" },
  { label: "A 正确，B 错误", value: "a_correct_b_wrong" },
  { label: "A 错误，B 正确", value: "a_wrong_b_correct" },
  { label: "两者都正确", value: "both_correct" },
  { label: "两者都错误", value: "both_wrong" },
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

function correctnessLabel(value: boolean | null | undefined, missing?: boolean) {
  if (missing) return "缺失";
  if (value === true) return "正确";
  if (value === false) return "错误";
  return "未知";
}

function statusTone(value: boolean | null | undefined, missing?: boolean) {
  if (missing || value === false) return "bad";
  if (value === true) return "good";
  return "neutral";
}

export function Compare() {
  const [metadata, setMetadata] = useState<MetricsMatrixResponse | null>(null);
  const [dataset, setDataset] = useState("");
  const [modelA, setModelA] = useState("");
  const [modelB, setModelB] = useState("");
  const [pattern, setPattern] = useState<ComparePattern>("all");
  const [keyword, setKeyword] = useState("");
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<CompareItem[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [status, setStatus] = useState<LoadState>("idle");
  const [message, setMessage] = useState("");
  const [refreshTick, setRefreshTick] = useState(0);

  useEffect(() => {
    let isMounted = true;

    getMetricsMatrix("accuracy")
      .then((response) => {
        if (!isMounted) return;
        setMetadata(response);
        setDataset((current) => current || response.datasets[0] || "");
        setModelA((current) => current || response.models[0] || "");
        setModelB((current) => current || response.models[1] || response.models[0] || "");
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
  }, [dataset, keyword, modelA, modelB, pattern]);

  useEffect(() => {
    if (!dataset || !modelA || !modelB) {
      return;
    }

    let isMounted = true;
    setStatus("loading");
    setMessage("");

    compareRecords({
      dataset,
      modelA,
      modelB,
      pattern,
      keyword,
      page,
      pageSize,
    })
      .then((response) => {
        if (!isMounted) return;
        setItems(response.items);
        setTotal(response.total);
        setTotalPages(response.total_pages);
        setSelectedId((current) => {
          if (response.items.some((item) => item.item_id === current)) {
            return current;
          }

          return response.items[0]?.item_id ?? "";
        });
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
  }, [dataset, keyword, modelA, modelB, page, pattern, refreshTick]);

  const selectedItem = useMemo(
    () => items.find((item) => item.item_id === selectedId) ?? items[0] ?? null,
    [items, selectedId],
  );

  const datasetOptions = (metadata?.datasets ?? []).map((name) => ({
    label: formatDatasetOptionLabel(name),
    value: name,
  }));
  const modelOptions = (metadata?.models ?? []).map((name) => ({
    label: name,
    value: name,
  }));

  return (
    <section className="page compare-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">评测</p>
          <h1>模型比较</h1>
        </div>
        <span className="section-note">匹配 {total} 条</span>
      </header>

      <div className="toolbar toolbar-five">
        <Select
          aria-label="评测集"
          value={dataset}
          onChange={(event) => setDataset(event.target.value)}
          options={datasetOptions}
        />
        <Select
          aria-label="模型 A"
          value={modelA}
          onChange={(event) => setModelA(event.target.value)}
          options={modelOptions}
        />
        <Select
          aria-label="模型 B"
          value={modelB}
          onChange={(event) => setModelB(event.target.value)}
          options={modelOptions}
        />
        <Select
          aria-label="比较模式"
          value={pattern}
          onChange={(event) => setPattern(event.target.value as ComparePattern)}
          options={patternOptions}
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

      <div className="compare-workspace">
        <aside className="item-list" aria-label="比较条目">
          {items.length === 0 ? (
            <div className="empty-panel">
              {status === "loading" ? "加载中" : "暂无数据"}
            </div>
          ) : (
            items.map((item) => (
              <button
                key={item.item_id}
                className={`item-list-row ${
                  item.item_id === selectedItem?.item_id ? "is-active" : ""
                }`}
                type="button"
                onClick={() => setSelectedId(item.item_id)}
              >
                <span>{item.item_id}</span>
                <span className="item-list-status">
                  <span
                    className={`pill pill-${statusTone(
                      item.model_a.correct,
                      item.model_a.missing,
                    )}`}
                  >
                    A {correctnessLabel(item.model_a.correct, item.model_a.missing)}
                  </span>
                  <span
                    className={`pill pill-${statusTone(
                      item.model_b.correct,
                      item.model_b.missing,
                    )}`}
                  >
                    B {correctnessLabel(item.model_b.correct, item.model_b.missing)}
                  </span>
                </span>
              </button>
            ))
          )}

          <div className="pagination compact-pagination">
            <Button
              variant="secondary"
              disabled={page <= 1 || status === "loading"}
              onClick={() => setPage((current) => Math.max(1, current - 1))}
            >
              上一页
            </Button>
            <span>
              {page}/{Math.max(totalPages, 1)}
            </span>
            <Button
              variant="secondary"
              disabled={page >= totalPages || status === "loading"}
              onClick={() => setPage((current) => current + 1)}
            >
              下一页
            </Button>
          </div>
        </aside>

        <main className="compare-detail">
          {selectedItem ? (
            <>
              <section className="detail-block">
                <div className="split-heading">
                  <h2>{selectedItem.item_id}</h2>
                  <span className="section-note">{selectedItem.dataset}</span>
                </div>
                <h3>题干</h3>
                <pre>{formatValue(selectedItem.prompt)}</pre>
                <h3>目标答案</h3>
                <pre>{formatValue(selectedItem.target_json)}</pre>
              </section>

              <div className="model-compare-grid">
                <ModelPanel
                  label="模型 A"
                  model={selectedItem.model_a.model}
                  correct={selectedItem.model_a.correct}
                  missing={selectedItem.model_a.missing}
                  output={selectedItem.model_a.output}
                  rawOutput={selectedItem.model_a.raw_output}
                />
                <ModelPanel
                  label="模型 B"
                  model={selectedItem.model_b.model}
                  correct={selectedItem.model_b.correct}
                  missing={selectedItem.model_b.missing}
                  output={selectedItem.model_b.output}
                  rawOutput={selectedItem.model_b.raw_output}
                />
              </div>
            </>
          ) : (
            <div className="empty-panel">请选择一条数据比较模型输出</div>
          )}
        </main>
      </div>
    </section>
  );
}

function ModelPanel({
  label,
  model,
  correct,
  missing,
  output,
  rawOutput,
}: {
  label: string;
  model: string;
  correct: boolean | null;
  missing?: boolean;
  output: string | null;
  rawOutput: string | null;
}) {
  return (
    <section className="model-panel">
      <div className="split-heading">
        <div>
          <p className="eyebrow">{label}</p>
          <h2>{model}</h2>
        </div>
        <span className={`pill pill-${statusTone(correct, missing)}`}>
          {correctnessLabel(correct, missing)}
        </span>
      </div>
      <h3>输出</h3>
      <pre>{missing ? "该模型缺少此条目" : formatValue(output)}</pre>
      <h3>原始输出</h3>
      <pre>{missing ? "该模型缺少此条目" : formatValue(rawOutput)}</pre>
    </section>
  );
}
