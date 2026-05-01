from __future__ import annotations

from typing import Any

from app.adapters.base import NormalizedRecord
from app.adapters.common import optional_bool, optional_float, optional_int, optional_str


class IfevalAdapter:
    key = "ifeval"

    def normalize(self, row: dict[str, Any]) -> NormalizedRecord:
        return NormalizedRecord(
            item_id=str(row.get("id", row.get("pid", row.get("uid")))),
            item_index=optional_int(row.get("idx")),
            prompt=optional_str(row.get("prompt") or row.get("question")),
            question=optional_str(row.get("question")),
            target=row.get("targets", row.get("target")),
            output=optional_str(row.get("output")),
            raw_output=optional_str(row.get("raw_output") or row.get("output")),
            is_correct=optional_bool(row.get("follow_all_instructions")),
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
