import { useMemo, useState } from "react";

import { Button } from "../components/Button";
import { Input, SearchInput, Select } from "../components/Inputs";
import { Table, type TableColumn } from "../components/Table";

type WrongItem = {
  id: string;
  model: string;
  dataset: string;
  question: string;
  expected: string;
};

const sampleItems: WrongItem[] = [
  {
    id: "AIME26-001",
    model: "Qwen3.5-4B",
    dataset: "aime26",
    question: "Geometry answer normalization",
    expected: "42",
  },
  {
    id: "AIME26-014",
    model: "Ling-2.6-flsh",
    dataset: "aime26",
    question: "Algebra final extraction",
    expected: "128",
  },
];

const columns: TableColumn<WrongItem>[] = [
  { key: "id", header: "题目 ID", render: (row) => row.id },
  { key: "model", header: "模型", render: (row) => row.model },
  { key: "dataset", header: "评测集", render: (row) => row.dataset },
  { key: "question", header: "题目", render: (row) => row.question },
  { key: "expected", header: "预期答案", render: (row) => row.expected },
];

export function WrongItems() {
  const [query, setQuery] = useState("");
  const [model, setModel] = useState("all");

  const filteredItems = useMemo(() => {
    return sampleItems.filter((item) => {
      const matchesModel = model === "all" || item.model === model;
      const matchesQuery = Object.values(item)
        .join(" ")
        .toLowerCase()
        .includes(query.toLowerCase());

      return matchesModel && matchesQuery;
    });
  }, [model, query]);

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">分析</p>
          <h1>错题分析</h1>
        </div>
        <Button variant="secondary">导出</Button>
      </header>

      <div className="toolbar">
        <SearchInput
          aria-label="搜索错题"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <Select
          aria-label="Filter model"
          value={model}
          onChange={(event) => setModel(event.target.value)}
          options={[
            { label: "全部模型", value: "all" },
            { label: "Qwen3.5-4B", value: "Qwen3.5-4B" },
            { label: "Ling-2.6-flsh", value: "Ling-2.6-flsh" },
          ]}
        />
        <Input aria-label="评测集" defaultValue="aime26" />
      </div>

      <Table columns={columns} data={filteredItems} emptyText="暂无数据" />
    </section>
  );
}
