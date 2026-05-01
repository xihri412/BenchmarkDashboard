from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.adapters.aime26 import Aime26Adapter
from app.adapters.base import DatasetAdapter
from app.adapters.gpqa import GpqaAdapter
from app.adapters.ifeval import IfevalAdapter
from app.adapters.korbench import KorbenchAdapter


@dataclass(frozen=True)
class DatasetConfig:
    name: str
    display_name: str
    adapter_key: str
    adapter: DatasetAdapter


_DATASETS: dict[str, DatasetConfig] = {
    "aime26": DatasetConfig(
        name="aime26",
        display_name="AIME 2026",
        adapter_key=Aime26Adapter.key,
        adapter=Aime26Adapter(),
    ),
    "gpqa": DatasetConfig(
        name="gpqa",
        display_name="GPQA",
        adapter_key=GpqaAdapter.key,
        adapter=GpqaAdapter(),
    ),
    "ifeval": DatasetConfig(
        name="ifeval",
        display_name="IFEval",
        adapter_key=IfevalAdapter.key,
        adapter=IfevalAdapter(),
    ),
    "korbench": DatasetConfig(
        name="korbench",
        display_name="KorBench",
        adapter_key=KorbenchAdapter.key,
        adapter=KorbenchAdapter(),
    ),
}


def get_dataset_config(name: str) -> DatasetConfig | None:
    return _DATASETS.get(name)


def iter_dataset_configs() -> Iterable[DatasetConfig]:
    return _DATASETS.values()
