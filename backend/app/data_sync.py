from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from fastapi import Depends
from sqlalchemy.orm import Session

from app.adapters.registry import get_dataset_config
from app.config import settings
from app.database import get_db
from app.ingest import IGNORED_JSONL_FILENAMES, ingest_data_dir

DataSnapshot = tuple[tuple[str, int, int], ...]

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_last_check = 0.0
_last_snapshot: DataSnapshot | None = None


def sync_data_if_needed(db: Session = Depends(get_db)) -> None:
    if not settings.auto_ingest_data:
        return

    global _last_check, _last_snapshot

    now = time.monotonic()
    if now - _last_check < settings.data_refresh_interval_seconds:
        return

    with _lock:
        now = time.monotonic()
        if now - _last_check < settings.data_refresh_interval_seconds:
            return

        try:
            snapshot = _data_snapshot(settings.data_dir)
            if snapshot != _last_snapshot:
                ingest_data_dir(settings.data_dir, db)
                _last_snapshot = snapshot
        except Exception as exc:
            db.rollback()
            logger.warning(
                "Auto data sync failed; serving existing database contents. error=%s: %s",
                type(exc).__name__,
                exc,
            )
        finally:
            _last_check = now


def _data_snapshot(data_dir: Path) -> DataSnapshot:
    data_dir = data_dir.expanduser().resolve()
    if not data_dir.exists():
        return ()

    rows: list[tuple[str, int, int]] = []
    for path in sorted(data_dir.glob("*/*.jsonl")):
        if (
            not path.is_file()
            or path.name in IGNORED_JSONL_FILENAMES
            or get_dataset_config(path.stem) is None
        ):
            continue
        stat = path.stat()
        rows.append((str(path.relative_to(data_dir)), stat.st_mtime_ns, stat.st_size))
    for path in sorted(data_dir.glob("*/*/*.jsonl")):
        if (
            not path.is_file()
            or path.name in IGNORED_JSONL_FILENAMES
            or (
                get_dataset_config(path.parent.name) is None
                and get_dataset_config(path.stem) is None
            )
        ):
            continue
        stat = path.stat()
        rows.append((str(path.relative_to(data_dir)), stat.st_mtime_ns, stat.st_size))
    for path in sorted(data_dir.glob("*/*/*.json")):
        if (
            not path.is_file()
            or (
                get_dataset_config(path.parent.name) is None
                and get_dataset_config(path.stem) is None
            )
        ):
            continue
        stat = path.stat()
        rows.append((str(path.relative_to(data_dir)), stat.st_mtime_ns, stat.st_size))
    return tuple(rows)
