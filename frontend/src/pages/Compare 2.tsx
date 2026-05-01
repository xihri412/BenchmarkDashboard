import { useState } from "react";

import { Button } from "../components/Button";
import { Select } from "../components/Inputs";
import { Table, type TableColumn } from "../components/Table";

type CompareRow = {
  metric: string;
  baseline: string;
  candidate: string;
  delta: string;
};

const columns: TableColumn<CompareRow>[] = [
  { key: "metric", header: "指标", render: (row) => row.metric },
  { key: "baseline", header: "基线", render: (row) => row.baseline },
  { key: "candidate", header: "候选", render: (row) => row.candidate },
  { key: "delta", header: "差异", render: (row) => row.delta, align: "right" },
];

export function Compare() {
  const [baseline, setBaseline] = useState("Qwen3.5-4B");
  const [candidate, setCandidate] = useState("qwen3.5-122b-a10b");

  const rows = [
    {
      metric: "准确率",
      baseline: "待加载",
      candidate: "待加载",
      delta: "-",
    },
    {
      metric: "错题数",
      baseline,
      candidate,
      delta: "-",
    },
  ];

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">评测</p>
          <h1>模型比较</h1>
        </div>
        <Button>开始比较</Button>
      </header>

      <div className="toolbar">
        <Select
          aria-label="基线模型"
          value={baseline}
          onChange={(event) => setBaseline(event.target.value)}
          options={[
            { label: "Qwen3.5-4B", value: "Qwen3.5-4B" },
            { label: "Qwen3-4B-2507-Instruct", value: "Qwen3-4B-2507-Instruct" },
          ]}
        />
        <Select
          aria-label="候选模型"
          value={candidate}
          onChange={(event) => setCandidate(event.target.value)}
          options={[
            { label: "qwen3.5-122b-a10b", value: "qwen3.5-122b-a10b" },
            { label: "Ling-2.6-flsh", value: "Ling-2.6-flsh" },
          ]}
        />
      </div>

      <Table columns={columns} data={rows} />
    </section>
  );
}
