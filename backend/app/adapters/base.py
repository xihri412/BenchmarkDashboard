from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class NormalizedRecord:
    item_id: str
    item_index: int | None
    prompt: str | None
    question: str | None
    target: dict[str, Any] | list[Any] | str | int | float | bool | None
    output: str | None
    raw_output: str | None
    is_correct: bool | None
    output_length: int | None
    inference_time: float | None
    original: dict[str, Any]


class DatasetAdapter(Protocol):
    key: str

    def normalize(self, row: dict[str, Any]) -> NormalizedRecord:
        """Convert one raw dataset row into the API/database contract."""
        ...
