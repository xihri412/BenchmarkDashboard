from __future__ import annotations

from typing import Any

from app.adapters.base import NormalizedRecord
from app.adapters.common import exact_match, optional_float, optional_int, optional_str


class Aime26Adapter:
    key = "aime26"

    def normalize(self, row: dict[str, Any]) -> NormalizedRecord:
        return NormalizedRecord(
            item_id=str(row["id"]),
            item_index=optional_int(row.get("idx")),
            prompt=optional_str(row.get("prompt")),
            question=optional_str(row.get("question")),
            target=row.get("target"),
            output=optional_str(row.get("output")),
            raw_output=optional_str(row.get("raw_output") or row.get("output")),
            is_correct=exact_match(row.get("exact_match")),
            output_length=optional_int(row.get("output_token_len")),
            inference_time=optional_float(row.get("output_time")),
            original=row,
        )
