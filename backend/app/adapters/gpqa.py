from __future__ import annotations

from typing import Any

from app.adapters.base import NormalizedRecord
from app.adapters.common import exact_match, optional_float, optional_int, optional_str
from app.adapters.common_choice import item_index, stable_item_id


class GpqaAdapter:
    key = "gpqa"

    def normalize(self, row: dict[str, Any]) -> NormalizedRecord:
        return NormalizedRecord(
            item_id=stable_item_id(row),
            item_index=item_index(row),
            prompt=optional_str(row.get("prompt") or row.get("question")),
            question=optional_str(row.get("question")),
            target=row.get("targets", row.get("target")),
            output=optional_str(row.get("output")),
            raw_output=optional_str(row.get("raw_output") or row.get("output")),
            is_correct=exact_match(row.get("exact_match")),
            output_length=optional_int(
                row.get("output_token_len")
                if row.get("output_token_len") is not None
                else len(str(row["output"]))
                if row.get("output") is not None
                else None
            ),
            inference_time=optional_float(row.get("output_time")),
            original=row,
        )
