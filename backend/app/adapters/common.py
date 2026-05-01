from __future__ import annotations

from typing import Any


def optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def exact_match(value: Any) -> bool | None:
    if value is None:
        return None
    return int(value) == 1


def optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)
