from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from app.adapters.base import NormalizedRecord
from app.adapters.common import exact_match, optional_bool, optional_float, optional_int, optional_str


CorrectnessMapper = Callable[[dict[str, Any]], bool | None]
TargetMapper = Callable[[dict[str, Any]], Any]


class GenericJsonlAdapter:
    key: str

    def __init__(
        self,
        key: str,
        *,
        correctness: CorrectnessMapper,
        output_fields: tuple[str, ...] = ("output",),
        raw_output_fields: tuple[str, ...] = ("raw_output", "output"),
        target: TargetMapper | None = None,
        question_fields: tuple[str, ...] = ("question",),
    ) -> None:
        self.key = key
        self._correctness = correctness
        self._output_fields = output_fields
        self._raw_output_fields = raw_output_fields
        self._target = target or default_target
        self._question_fields = question_fields

    def normalize(self, row: dict[str, Any]) -> NormalizedRecord:
        return NormalizedRecord(
            item_id=stable_item_id(row),
            item_index=item_index(row),
            prompt=optional_str(first_present(row, ("prompt", "question"))),
            question=optional_str(first_present(row, self._question_fields)),
            target=self._target(row),
            output=optional_str(first_present(row, self._output_fields)),
            raw_output=optional_str(raw_output_value(row, self._raw_output_fields)),
            is_correct=self._correctness(row),
            output_length=optional_int(row.get("output_token_len")),
            inference_time=optional_float(row.get("output_time")),
            original=row,
        )


ChoiceLikeAdapter = GenericJsonlAdapter


class BrowseCompAdapter(GenericJsonlAdapter):
    def __init__(self) -> None:
        super().__init__(
            "browsecomp",
            correctness=lambda row: optional_bool(row.get("is_correct")),
            output_fields=("model_extracted_answer", "output"),
            raw_output_fields=("raw_response", "reasoning", "output"),
        )


class BrowseCompZhAdapter(GenericJsonlAdapter):
    def __init__(self) -> None:
        super().__init__(
            "browsecomp-zn",
            correctness=score_is_one,
            raw_output_fields=("raw_output", "response_raw", "response", "output"),
        )


class ExactMatchChoiceAdapter(GenericJsonlAdapter):
    def __init__(self, key: str) -> None:
        super().__init__(key, correctness=lambda row: exact_match(row.get("exact_match")))


def default_target(row: dict[str, Any]) -> Any:
    if "targets" in row:
        return row.get("targets")
    if "target" in row:
        return row.get("target")
    if "answer" in row:
        return row.get("answer")
    return None


def null_target(_: dict[str, Any]) -> None:
    return None


def answer_target(row: dict[str, Any]) -> Any:
    if "targets" in row:
        return row.get("targets")
    return row.get("answer")


def stable_item_id(row: dict[str, Any]) -> str:
    uid = first_present(row, ("uid",))
    if uid is not None:
        return str(uid)

    targets = row.get("targets")
    if isinstance(targets, dict):
        for key in ("uuid", "id"):
            value = targets.get(key)
            if value is not None and value != "":
                return str(value)
    if isinstance(targets, list):
        for target in targets:
            if not isinstance(target, dict):
                continue
            for key in ("uuid", "id"):
                value = target.get(key)
                if value is not None and value != "":
                    return str(value)

    pid = first_present(row, ("pid",))
    row_id = first_present(row, ("id",))
    if pid is not None and row_id is not None:
        return f"{pid}:{row_id}"
    if row_id is not None:
        return str(row_id)

    raise ValueError("Cannot build stable item_id: missing uid, pid, and id")


def item_index(row: dict[str, Any]) -> int | None:
    return optional_int(first_present(row, ("idx", "id")))


def first_present(row: dict[str, Any], fields: tuple[str, ...]) -> Any:
    for field in fields:
        value = row.get(field)
        if value is not None and value != "":
            return value
    return None


def raw_output_value(row: dict[str, Any], fields: tuple[str, ...]) -> Any:
    for field in fields:
        value = row.get(field)
        if value is None or value == "":
            continue
        if field == "games":
            return json.dumps(value, ensure_ascii=False)
        return value
    return None


def score_is_one(row: dict[str, Any]) -> bool | None:
    score = row.get("score")
    if score is None:
        return None
    return int(score) == 1


def score_letter_bool(row: dict[str, Any]) -> bool | None:
    score = row.get("score")
    if score is None:
        return None
    normalized = str(score).strip().upper()
    if not normalized:
        return None
    return normalized == "A"


def verdict_bool(row: dict[str, Any]) -> bool | None:
    verdict = row.get("verdict")
    if verdict is None:
        return None
    normalized = str(verdict).strip().upper()
    if normalized == "YES":
        return True
    if normalized == "NO":
        return False
    return None


def binary_judgment_bool(row: dict[str, Any]) -> bool | None:
    value = row.get("extracted_judgment_binary")
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        if value == 1:
            return True
        if value == 0:
            return False
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "correct", "yes"}:
        return True
    if normalized in {"0", "false", "incorrect", "no"}:
        return False
    return None
