from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.adapters.aime26 import Aime26Adapter
from app.adapters.base import DatasetAdapter
from app.adapters.browsecomp import BrowseCompAdapter
from app.adapters.browsecomp_zh import BrowseCompZhAdapter
from app.adapters.common import exact_match, optional_bool
from app.adapters.common_choice import (
    GenericJsonlAdapter,
    answer_target,
    binary_judgment_bool,
    null_target,
    score_is_one,
    score_letter_bool,
    verdict_bool,
)
from app.adapters.gpqa import GpqaAdapter
from app.adapters.ifeval import IfevalAdapter
from app.adapters.korbench import KorbenchAdapter
from app.adapters.mmmlu_lite import MmmluLiteAdapter
from app.adapters.mmlu_pro import MmluProAdapter
from app.adapters.mmlu_redux import MmluReduxAdapter

aime26_adapter = Aime26Adapter()
gpqa_adapter = GpqaAdapter()
ifeval_adapter = IfevalAdapter()
korbench_adapter = KorbenchAdapter()
browsecomp_adapter = BrowseCompAdapter()
browsecomp_zh_adapter = BrowseCompZhAdapter()
mmmlu_lite_adapter = MmmluLiteAdapter()
mmlu_pro_adapter = MmluProAdapter()
mmlu_redux_adapter = MmluReduxAdapter()


@dataclass(frozen=True)
class DatasetConfig:
    name: str
    display_name: str
    adapter_key: str
    adapter: DatasetAdapter
    aliases: tuple[str, ...] = ()


def dataset_config(
    name: str,
    display_name: str,
    adapter: DatasetAdapter,
    aliases: tuple[str, ...] = (),
) -> DatasetConfig:
    return DatasetConfig(
        name=name,
        display_name=display_name,
        adapter_key=adapter.key,
        adapter=adapter,
        aliases=aliases,
    )


exact_match_adapter = lambda key: GenericJsonlAdapter(
    key,
    correctness=lambda row: exact_match(row.get("exact_match")),
)

_DATASETS: dict[str, DatasetConfig] = {
    "AIME24": dataset_config(
        name="AIME24",
        display_name="AIME 2024",
        adapter=exact_match_adapter("AIME24"),
        aliases=("aime24", "aime24.jsonl"),
    ),
    "aime25": dataset_config(
        name="aime25",
        display_name="AIME 2025",
        adapter=exact_match_adapter("aime25"),
        aliases=("aime25", "aime25.jsonl"),
    ),
    "aime26": dataset_config(
        name="aime26",
        display_name="AIME 2026",
        adapter=aime26_adapter,
        aliases=("aime26", "aime26.jsonl"),
    ),
    "beyondaime": dataset_config(
        name="beyondaime",
        display_name="BeyondAIME",
        adapter=exact_match_adapter("beyondaime"),
        aliases=("beyondaime", "beyondaime.jsonl"),
    ),
    "imo-answerbench": dataset_config(
        name="imo-answerbench",
        display_name="IMO AnswerBench",
        adapter=exact_match_adapter("imo-answerbench"),
        aliases=("imo-answerbench_score", "imo-answerbench_score.jsonl"),
    ),
    "Encyclo-k": dataset_config(
        name="Encyclo-k",
        display_name="Encyclo-k",
        adapter=exact_match_adapter("Encyclo-k"),
        aliases=("encyclo_k_score", "encyclo_k_score.jsonl"),
    ),
    "LPFQA": dataset_config(
        name="LPFQA",
        display_name="LPFQA",
        adapter=exact_match_adapter("LPFQA"),
        aliases=("lpfqa_score", "lpfqa_score.jsonl"),
    ),
    "disco-x": dataset_config(
        name="disco-x",
        display_name="Disco-X",
        adapter=exact_match_adapter("disco-x"),
        aliases=("disco_x_score", "disco_x_score.jsonl"),
    ),
    "global-piqa": dataset_config(
        name="global-piqa",
        display_name="Global-PIQA",
        adapter=exact_match_adapter("global-piqa"),
        aliases=("global-piqa_score", "global-piqa_score.jsonl"),
    ),
    "gpqa": dataset_config(
        name="gpqa",
        display_name="GPQA",
        adapter=gpqa_adapter,
        aliases=("gpqa", "gpqa.jsonl"),
    ),
    "ifeval": dataset_config(
        name="ifeval",
        display_name="IFEval",
        adapter=ifeval_adapter,
    ),
    "korbench": dataset_config(
        name="korbench",
        display_name="KorBench",
        adapter=korbench_adapter,
        aliases=("korbench_score", "korbench_score.jsonl"),
    ),
    "browsecomp": dataset_config(
        name="browsecomp",
        display_name="BrowseComp",
        adapter=browsecomp_adapter,
        aliases=("browsecomp_score", "browsecomp_score.jsonl"),
    ),
    "browsecomp-zn": dataset_config(
        name="browsecomp-zn",
        display_name="BrowseComp-ZH",
        adapter=browsecomp_zh_adapter,
        aliases=(
            "browsecomp_zh_score",
            "browsecomp_zh_score.jsonl",
            "browsecomp_zh",
            "browsecomp-zh",
        ),
    ),
    "c-simpleqa": dataset_config(
        name="c-simpleqa",
        display_name="C-SimpleQA",
        adapter=GenericJsonlAdapter(
            "c-simpleqa",
            correctness=score_letter_bool,
            raw_output_fields=("raw_output", "response_raw", "response", "judge", "output"),
        ),
        aliases=("chinese_simpleqa_score", "chinese_simpleqa_score.jsonl"),
    ),
    "eckgbench": dataset_config(
        name="eckgbench",
        display_name="ECKGBench",
        adapter=GenericJsonlAdapter(
            "eckgbench",
            correctness=score_is_one,
            raw_output_fields=("response", "output"),
        ),
        aliases=("eckgbench_score", "eckgbench_score.jsonl"),
    ),
    "arena-hardv2": dataset_config(
        name="arena-hardv2",
        display_name="Arena-Hard v2",
        adapter=GenericJsonlAdapter(
            "arena-hardv2",
            correctness=lambda row: None,
            raw_output_fields=("games", "output"),
            target=null_target,
        ),
        aliases=("arena_hard_score", "arena_hard_score.jsonl"),
    ),
    "fineval6.0": dataset_config(
        name="fineval6.0",
        display_name="FinEval 6.0",
        adapter=GenericJsonlAdapter(
            "fineval6.0",
            correctness=score_is_one,
            raw_output_fields=("response_raw", "response", "output"),
        ),
        aliases=("fineval", "fineval.jsonl"),
    ),
    "foodbench": dataset_config(
        name="foodbench",
        display_name="FoodBench",
        adapter=exact_match_adapter("foodbench"),
        aliases=("food_bench", "food_bench.jsonl"),
    ),
    "chineseecomqa": dataset_config(
        name="chineseecomqa",
        display_name="ChineseEcomQA",
        adapter=GenericJsonlAdapter(
            "chineseecomqa",
            correctness=score_is_one,
            raw_output_fields=("response_raw", "response", "judge", "output"),
        ),
        aliases=("chinese_ecom_qa_score", "chinese_ecom_qa_score.jsonl"),
    ),
    "IFBench": dataset_config(
        name="IFBench",
        display_name="IFBench",
        adapter=GenericJsonlAdapter(
            "IFBench",
            correctness=lambda row: optional_bool(row.get("follow_all_instructions")),
            raw_output_fields=("raw_output", "response_raw", "response", "output"),
        ),
        aliases=("ifbench_score", "ifbench_score.jsonl"),
    ),
    "creativewriting": dataset_config(
        name="creativewriting",
        display_name="CreativeWriting",
        adapter=GenericJsonlAdapter(
            "creativewriting",
            correctness=lambda row: None,
        ),
        aliases=(
            "creative_writing",
            "creative_writing_score",
            "creative_writing_score.json",
        ),
    ),
    "writingbench": dataset_config(
        name="writingbench",
        display_name="WritingBench",
        adapter=GenericJsonlAdapter(
            "writingbench",
            correctness=lambda row: None,
        ),
        aliases=(
            "writing_bench",
            "writing_bench_score",
            "writing_bench_score.json",
        ),
    ),
    "MMMLU-lite": dataset_config(
        name="MMMLU-lite",
        display_name="MMMLU-lite",
        adapter=mmmlu_lite_adapter,
        aliases=("mmmlu_lite", "mmmlu_lite.jsonl"),
    ),
    "MMLU-Pro": dataset_config(
        name="MMLU-Pro",
        display_name="MMLU-Pro",
        adapter=mmlu_pro_adapter,
        aliases=("mmlu_pro", "mmlu_pro.jsonl"),
    ),
    "MMLU-Redux": dataset_config(
        name="MMLU-Redux",
        display_name="MMLU-Redux",
        adapter=mmlu_redux_adapter,
        aliases=("mmlu", "mmlu.jsonl"),
    ),
    "mmlu-econonmics": dataset_config(
        name="mmlu-econonmics",
        display_name="MMLU Econometrics",
        adapter=exact_match_adapter("mmlu-econonmics"),
        aliases=("mmlu_econometrics", "mmlu_econometrics.jsonl"),
    ),
    "FrontierSci-Olympiad": dataset_config(
        name="FrontierSci-Olympiad",
        display_name="FrontierSci-Olympiad",
        adapter=GenericJsonlAdapter(
            "FrontierSci-Olympiad",
            correctness=verdict_bool,
            raw_output_fields=("reasoning", "output"),
        ),
        aliases=("frontierscience_score", "frontierscience_score.jsonl"),
    ),
    "hmmt-feb-26": dataset_config(
        name="hmmt-feb-26",
        display_name="HMMT Feb 2026",
        adapter=GenericJsonlAdapter(
            "hmmt-feb-26",
            correctness=lambda row: exact_match(row.get("exact_match")),
            target=answer_target,
        ),
        aliases=("hmmt26feb", "hmmt26feb.jsonl"),
    ),
    "medmcqa": dataset_config(
        name="medmcqa",
        display_name="MedMCQA",
        adapter=exact_match_adapter("medmcqa"),
        aliases=("medmcqa", "medmcqa.jsonl"),
    ),
    "multichallenge": dataset_config(
        name="multichallenge",
        display_name="MultiChallenge",
        adapter=GenericJsonlAdapter(
            "multichallenge",
            correctness=score_is_one,
            raw_output_fields=("reasoning", "verdict", "output"),
        ),
        aliases=("multichallenge_score", "multichallenge_score.jsonl"),
    ),
    "simpleqa": dataset_config(
        name="simpleqa",
        display_name="SimpleQA",
        adapter=GenericJsonlAdapter(
            "simpleqa",
            correctness=score_letter_bool,
            raw_output_fields=("raw_output", "response_raw", "response", "judge", "output"),
        ),
        aliases=("simpleqa_verified_score", "simpleqa_verified_score.jsonl"),
    ),
    "mpc_smoke": dataset_config(
        name="mpc_smoke",
        display_name="MPC Smoke",
        adapter=GenericJsonlAdapter(
            "mpc_smoke",
            correctness=score_is_one,
            raw_output_fields=("response_raw", "response", "output"),
        ),
        aliases=("mpc_smoke_score", "mpc_smoke_score.jsonl"),
    ),
    "medqa": dataset_config(
        name="medqa",
        display_name="MedQA",
        adapter=exact_match_adapter("medqa"),
        aliases=("medqa", "medqa.jsonl"),
    ),
    "u-math": dataset_config(
        name="u-math",
        display_name="U-Math",
        adapter=GenericJsonlAdapter(
            "u-math",
            correctness=binary_judgment_bool,
            raw_output_fields=("judge_cot", "extracted_judgment", "output"),
        ),
        aliases=("u_math_score", "u_math_score.jsonl"),
    ),
    "supergpqa-med": dataset_config(
        name="supergpqa-med",
        display_name="SuperGPQA Medicine",
        adapter=exact_match_adapter("supergpqa-med"),
        aliases=("supergpqa_Medicine", "supergpqa_Medicine.jsonl"),
    ),
    "Supergpqa": dataset_config(
        name="Supergpqa",
        display_name="SuperGPQA",
        adapter=exact_match_adapter("Supergpqa"),
        aliases=("supergpqa", "supergpqa.jsonl"),
    ),
    "polymath": dataset_config(
        name="polymath",
        display_name="PolyMath",
        adapter=GenericJsonlAdapter(
            "polymath",
            correctness=score_is_one,
            output_fields=("extracted_pred", "output"),
        ),
        aliases=("polymath_score", "polymath_score.jsonl"),
    ),
    "hmmt-nov-25": dataset_config(
        name="hmmt-nov-25",
        display_name="HMMT Nov 2025",
        adapter=GenericJsonlAdapter(
            "hmmt-nov-25",
            correctness=lambda row: exact_match(row.get("exact_match")),
            target=answer_target,
        ),
        aliases=("hmmt25nov", "hmmt25nov.jsonl"),
    ),
}

_DATASET_ALIASES: dict[str, str] = {}
for dataset_name, dataset in _DATASETS.items():
    _DATASET_ALIASES[dataset_name] = dataset_name
    _DATASET_ALIASES[f"{dataset_name}.jsonl"] = dataset_name
    for alias in dataset.aliases:
        _DATASET_ALIASES[alias] = dataset_name


def get_dataset_config(name: str) -> DatasetConfig | None:
    return _DATASETS.get(_DATASET_ALIASES.get(name, name))


def iter_dataset_configs() -> Iterable[DatasetConfig]:
    return _DATASETS.values()
