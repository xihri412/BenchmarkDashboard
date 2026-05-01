from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class DatasetColumn:
    key: str
    label: str


@dataclass(frozen=True)
class DatasetCategory:
    key: str
    label: str
    datasets: tuple[DatasetColumn, ...]


def dataset(key: str, label: str | None = None) -> DatasetColumn:
    return DatasetColumn(key=key, label=label or key)


DATASET_CATEGORIES: tuple[DatasetCategory, ...] = (
    DatasetCategory(
        key="subject_knowledge",
        label="学科知识",
        datasets=(
            dataset("MMLU-Pro"),
            dataset("MMLU-Redux"),
            dataset("Supergpqa"),
            dataset("gpqa"),
            dataset("LPFQA"),
            dataset("FrontierSci-Olympiad"),
            dataset("Encyclo-k"),
        ),
    ),
    DatasetCategory(
        key="math",
        label="数学",
        datasets=(
            dataset("AIME24"),
            dataset("aime25"),
            dataset("aime26"),
            dataset("hmmt-feb-25"),
            dataset("hmmt-nov-25"),
            dataset("hmmt-feb-26"),
            dataset("beyondaime"),
            dataset("imo-answerbench"),
            dataset("u-math"),
        ),
    ),
    DatasetCategory(
        key="logical_reasoning",
        label="逻辑推理",
        datasets=(
            dataset("Zebralogic"),
            dataset("korbench"),
        ),
    ),
    DatasetCategory(
        key="instruction_writing",
        label="指令遵从/写作",
        datasets=(
            dataset("ifeval", "IFEval"),
            dataset("IFBench"),
            dataset("multichallenge"),
            dataset("creativewriting"),
            dataset("writingbench"),
            dataset("arena-hardv2"),
        ),
    ),
    DatasetCategory(
        key="multilingual",
        label="多语言",
        datasets=(
            dataset("MMMLU-lite"),
            dataset("global-piqa"),
            dataset("disco-x"),
        ),
    ),
    DatasetCategory(
        key="long_context",
        label="长序列",
        datasets=(
            dataset("aa-lcr"),
            dataset("mrcr-v2"),
            dataset("ruler"),
            dataset("longbench"),
        ),
    ),
    DatasetCategory(
        key="code",
        label="代码",
        datasets=(
            dataset("livecodebench-v6"),
            dataset("livecodebench-pro"),
            dataset("artifactbench"),
            dataset("repoqa"),
            dataset("multipl-e"),
        ),
    ),
    DatasetCategory(
        key="tool_calling",
        label="工具调用",
        datasets=(
            dataset("bfcl-v3"),
            dataset("tau2"),
            dataset("pinchbnch"),
            dataset("小艺中控"),
        ),
    ),
    DatasetCategory(
        key="code_tasks",
        label="代码任务",
        datasets=(
            dataset("swe-bench-verified"),
            dataset("terminalbench"),
            dataset("multi-swebench"),
        ),
    ),
    DatasetCategory(
        key="search",
        label="搜索",
        datasets=(
            dataset("browsecomp"),
            dataset("browsecomp-zn"),
            dataset("simpleqa"),
            dataset("c-simpleqa"),
        ),
    ),
    DatasetCategory(
        key="stem_smoke",
        label="STEM冒烟集",
        datasets=(
            dataset("数学"),
            dataset("物理"),
            dataset("化学"),
        ),
    ),
    DatasetCategory(
        key="medical",
        label="医疗",
        datasets=(
            dataset("supergpqa-med"),
            dataset("medmcqa"),
            dataset("medqa"),
            dataset("cmexam"),
        ),
    ),
    DatasetCategory(
        key="finance",
        label="金融",
        datasets=(
            dataset("mmlu-econonmics"),
            dataset("fineval6.0"),
        ),
    ),
    DatasetCategory(
        key="shopping_food",
        label="购物/美食",
        datasets=(
            dataset("shoppingmmlu"),
            dataset("chineseecomqa"),
            dataset("foodbench"),
        ),
    ),
    DatasetCategory(
        key="consumer_electronics",
        label="消费电子",
        datasets=(dataset("eckgbench"),),
    ),
)


def iter_configured_dataset_keys() -> Iterable[str]:
    for category in DATASET_CATEGORIES:
        for column in category.datasets:
            yield column.key
