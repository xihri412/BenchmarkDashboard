from __future__ import annotations

import argparse
import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.base import NormalizedRecord
from app.adapters.registry import DatasetConfig, get_dataset_config, iter_dataset_configs
from app.database import SessionLocal
from app.models.benchmark import Dataset, EvaluationRun, MetricsSummary, Model, Record

IGNORED_JSONL_FILENAMES = {
    "shopping_mmlu_score_raw.jsonl",
    "ifbench_score_old.jsonl",
}

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImportResult:
    model_name: str
    dataset_name: str
    source_path: Path
    source_hash: str
    status: str
    run_id: int | None = None
    total_count: int = 0
    correct_count: int = 0
    error_type: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class ImportSource:
    model_name: str
    dataset_name: str
    source_path: Path
    files: tuple[Path, ...]
    source_type: str = "jsonl"


def ingest_data_dir(data_dir: Path, db: Session) -> list[ImportResult]:
    data_dir = data_dir.expanduser().resolve()
    _ensure_datasets(db)

    results: list[ImportResult] = []
    for source in _iter_import_sources(data_dir):
        dataset_config = get_dataset_config(source.dataset_name)
        if dataset_config is None:
            continue

        result = ingest_source_best_effort(
            db=db,
            source=source,
            dataset_config=dataset_config,
        )
        results.append(result)

    return results


def ingest_file(
    *,
    db: Session,
    source_path: Path,
    model_name: str,
    dataset_config: DatasetConfig,
) -> ImportResult:
    source_path = source_path.expanduser().resolve()
    source = ImportSource(
        model_name=model_name,
        dataset_name=dataset_config.name,
        source_path=source_path,
        files=(source_path,),
    )
    return ingest_source(db=db, source=source, dataset_config=dataset_config)


def ingest_source_best_effort(
    *,
    db: Session,
    source: ImportSource,
    dataset_config: DatasetConfig,
) -> ImportResult:
    source_path = source.source_path.expanduser().resolve()
    source_hash: str | None = None
    try:
        source_hash = _sha256_files(tuple(path.expanduser().resolve() for path in source.files))
        result = ingest_source(
            db=db,
            source=source,
            dataset_config=dataset_config,
            source_hash=source_hash,
        )
        return result
    except Exception as exc:
        db.rollback()
        _log_source_failure(source, exc)
        return _record_failed_import(
            db=db,
            source=source,
            dataset_config=dataset_config,
            source_path=source_path,
            source_hash=source_hash,
            exc=exc,
        )


def ingest_source(
    *,
    db: Session,
    source: ImportSource,
    dataset_config: DatasetConfig,
    source_hash: str | None = None,
) -> ImportResult:
    source_path = source.source_path.expanduser().resolve()
    source_files = tuple(path.expanduser().resolve() for path in source.files)
    source_hash = source_hash or _sha256_files(source_files)

    model = _get_or_create_model(db, source.model_name)
    dataset = _get_or_create_dataset(db, dataset_config)

    existing_run = db.scalar(
        select(EvaluationRun).where(
            EvaluationRun.model_id == model.id,
            EvaluationRun.dataset_id == dataset.id,
            EvaluationRun.source_hash == source_hash,
            EvaluationRun.status == "completed",
        )
    )
    if existing_run is not None:
        return ImportResult(
            model_name=model.name,
            dataset_name=dataset.name,
            source_path=source_path,
            source_hash=source_hash,
            status="skipped",
            run_id=existing_run.id,
            total_count=existing_run.total_count,
            correct_count=existing_run.correct_count,
        )

    if source.source_type == "summary_json":
        return _ingest_summary_source(
            db=db,
            source=source,
            source_path=source_path,
            source_hash=source_hash,
            model=model,
            dataset=dataset,
        )

    normalized_records = _load_normalized_records(source_files, dataset_config)
    total_count = len(normalized_records)
    correct_count = sum(1 for record in normalized_records if record.is_correct is True)

    run = EvaluationRun(
        model_id=model.id,
        dataset_id=dataset.id,
        source_path=str(source_path),
        source_hash=source_hash,
        status="importing",
        total_count=total_count,
        correct_count=correct_count,
    )
    db.add(run)
    db.flush()

    db.add_all(
        _build_record(run.id, model.id, dataset.id, normalized)
        for normalized in normalized_records
    )
    db.add(
        MetricsSummary(
            run_id=run.id,
            model_id=model.id,
            dataset_id=dataset.id,
            accuracy=(correct_count / total_count) if total_count else None,
            avg_output_length=_average(
                record.output_length for record in normalized_records
            ),
            avg_inference_time=_average(
                record.inference_time for record in normalized_records
            ),
            total_count=total_count,
            correct_count=correct_count,
        )
    )
    run.status = "completed"
    db.commit()
    db.refresh(run)

    return ImportResult(
        model_name=model.name,
        dataset_name=dataset.name,
        source_path=source_path,
        source_hash=source_hash,
        status="imported",
        run_id=run.id,
        total_count=total_count,
        correct_count=correct_count,
    )


def _record_failed_import(
    *,
    db: Session,
    source: ImportSource,
    dataset_config: DatasetConfig,
    source_path: Path,
    source_hash: str | None,
    exc: Exception,
) -> ImportResult:
    error_type = type(exc).__name__
    error_message = str(exc)
    try:
        model = _get_or_create_model(db, source.model_name)
        dataset = _get_or_create_dataset(db, dataset_config)
        failed_hash = source_hash or f"failed:{_source_identity_hash(source)}"
        run = EvaluationRun(
            model_id=model.id,
            dataset_id=dataset.id,
            source_path=str(source_path),
            source_hash=failed_hash,
            status="failed",
            total_count=0,
            correct_count=0,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return ImportResult(
            model_name=model.name,
            dataset_name=dataset.name,
            source_path=source_path,
            source_hash=failed_hash,
            status="failed",
            run_id=run.id,
            error_type=error_type,
            error_message=error_message,
        )
    except Exception as failed_run_exc:
        db.rollback()
        logger.warning(
            "Could not record failed dataset run: model=%s dataset=%s source=%s "
            "error=%s: %s original_error=%s: %s",
            source.model_name,
            dataset_config.name,
            source_path,
            type(failed_run_exc).__name__,
            failed_run_exc,
            error_type,
            error_message,
        )
        return ImportResult(
            model_name=source.model_name,
            dataset_name=dataset_config.name,
            source_path=source_path,
            source_hash=source_hash or "",
            status="failed",
            error_type=error_type,
            error_message=error_message,
        )


def _log_source_failure(source: ImportSource, exc: Exception) -> None:
    logger.warning(
        "Skipped dataset import: model=%s dataset=%s source=%s error=%s: %s",
        source.model_name,
        source.dataset_name,
        source.source_path,
        type(exc).__name__,
        exc,
    )


def _source_identity_hash(source: ImportSource) -> str:
    digest = hashlib.sha256()
    digest.update(source.model_name.encode("utf-8"))
    digest.update(b"\0")
    digest.update(source.dataset_name.encode("utf-8"))
    digest.update(b"\0")
    digest.update(str(source.source_path).encode("utf-8"))
    return digest.hexdigest()


def _ensure_datasets(db: Session) -> None:
    for dataset_config in iter_dataset_configs():
        _get_or_create_dataset(db, dataset_config)
    db.commit()


def _iter_import_sources(data_dir: Path) -> list[ImportSource]:
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory does not exist: {data_dir}")

    sources: list[ImportSource] = []
    for path in sorted(data_dir.glob("*/*.jsonl")):
        if not _is_supported_jsonl(path):
            continue
        dataset_config = get_dataset_config(path.stem)
        if dataset_config is None:
            continue
        sources.append(
            ImportSource(
                model_name=path.parent.name,
                dataset_name=dataset_config.name,
                source_path=path,
                files=(path,),
                source_type="jsonl",
            )
        )

    nested_files_by_source: dict[tuple[Path, str], list[Path]] = {}
    for path in sorted(data_dir.glob("*/*/*.jsonl")):
        if not _is_supported_jsonl(path):
            continue
        dataset_config = get_dataset_config(path.parent.name) or get_dataset_config(path.stem)
        if dataset_config is None:
            continue
        nested_files_by_source.setdefault((path.parent, dataset_config.name), []).append(path)

    for (folder, dataset_name), files in sorted(nested_files_by_source.items()):
        sources.append(
            ImportSource(
                model_name=folder.parent.name,
                dataset_name=dataset_name,
                source_path=folder,
                files=tuple(sorted(files)),
                source_type="jsonl",
            )
        )

    for path in sorted(data_dir.glob("*/*/*.json")):
        if not path.is_file():
            continue
        dataset_config = get_dataset_config(path.parent.name) or get_dataset_config(path.stem)
        if dataset_config is None:
            continue
        sources.append(
            ImportSource(
                model_name=path.parent.parent.name,
                dataset_name=dataset_config.name,
                source_path=path,
                files=(path,),
                source_type="summary_json",
            )
        )

    return sources


def _is_supported_jsonl(path: Path) -> bool:
    return path.is_file() and path.name not in IGNORED_JSONL_FILENAMES


def _get_or_create_model(db: Session, name: str) -> Model:
    model = db.scalar(select(Model).where(Model.name == name))
    if model is not None:
        return model

    model = Model(name=name, display_name=name)
    db.add(model)
    db.flush()
    return model


def _get_or_create_dataset(db: Session, dataset_config: DatasetConfig) -> Dataset:
    dataset = db.scalar(select(Dataset).where(Dataset.name == dataset_config.name))
    if dataset is not None:
        dataset.display_name = dataset_config.display_name
        dataset.adapter_key = dataset_config.adapter_key
        dataset.is_active = True
        db.flush()
        return dataset

    dataset = Dataset(
        name=dataset_config.name,
        display_name=dataset_config.display_name,
        adapter_key=dataset_config.adapter_key,
        is_active=True,
    )
    db.add(dataset)
    db.flush()
    return dataset


def _ingest_summary_source(
    *,
    db: Session,
    source: ImportSource,
    source_path: Path,
    source_hash: str,
    model: Model,
    dataset: Dataset,
) -> ImportResult:
    existing_run = db.scalar(
        select(EvaluationRun).where(
            EvaluationRun.model_id == model.id,
            EvaluationRun.dataset_id == dataset.id,
            EvaluationRun.source_hash == source_hash,
            EvaluationRun.status == "completed",
        )
    )
    if existing_run is not None:
        return ImportResult(
            model_name=model.name,
            dataset_name=dataset.name,
            source_path=source_path,
            source_hash=source_hash,
            status="skipped",
            run_id=existing_run.id,
            total_count=existing_run.total_count,
            correct_count=existing_run.correct_count,
        )

    summary = _load_summary_json(source.files[0])
    total_count = summary["total_count"]
    correct_count = summary["correct_count"]
    accuracy = summary["accuracy"]

    run = EvaluationRun(
        model_id=model.id,
        dataset_id=dataset.id,
        source_path=str(source_path),
        source_hash=source_hash,
        status="importing",
        total_count=total_count,
        correct_count=correct_count,
    )
    db.add(run)
    db.flush()

    db.add(
        MetricsSummary(
            run_id=run.id,
            model_id=model.id,
            dataset_id=dataset.id,
            accuracy=accuracy,
            avg_output_length=None,
            avg_inference_time=None,
            total_count=total_count,
            correct_count=correct_count,
        )
    )
    run.status = "completed"
    db.commit()
    db.refresh(run)

    return ImportResult(
        model_name=model.name,
        dataset_name=dataset.name,
        source_path=source_path,
        source_hash=source_hash,
        status="imported",
        run_id=run.id,
        total_count=total_count,
        correct_count=correct_count,
    )


def _load_summary_json(source_path: Path) -> dict[str, int | float | None]:
    with source_path.open("r", encoding="utf-8") as file:
        raw_summary = json.load(file)
    if not isinstance(raw_summary, dict):
        raise ValueError(f"Expected summary object in {source_path}")

    details = raw_summary.get("Details")
    if not isinstance(details, dict):
        details = {}

    total_count = _optional_summary_int(details.get("total"))
    correct_count = _optional_summary_int(details.get("correct"))
    accuracy = _optional_summary_float(
        raw_summary.get("Accuracy", raw_summary.get("Accuracy (%)"))
    )

    if total_count is None:
        wrong_count = _optional_summary_int(details.get("wrong"))
        if correct_count is not None and wrong_count is not None:
            total_count = correct_count + wrong_count
        else:
            total_count = 0

    if correct_count is None:
        if accuracy is not None and total_count:
            correct_count = round(_normalize_accuracy(accuracy) * total_count)
        else:
            correct_count = 0

    normalized_accuracy = (
        _normalize_accuracy(accuracy)
        if accuracy is not None
        else (correct_count / total_count)
        if total_count
        else None
    )

    return {
        "total_count": total_count,
        "correct_count": correct_count,
        "accuracy": normalized_accuracy,
    }


def _optional_summary_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_summary_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _normalize_accuracy(value: float) -> float:
    if value > 1:
        return value / 100
    return value


def _load_normalized_records(
    source_files: tuple[Path, ...], dataset_config: DatasetConfig
) -> list[NormalizedRecord]:
    records: list[NormalizedRecord] = []
    for source_path in source_files:
        with source_path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue
                try:
                    raw_row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSON in {source_path} at line {line_number}: {exc.msg}"
                    ) from exc
                if not isinstance(raw_row, dict):
                    raise ValueError(
                        f"Expected object in {source_path} at line {line_number}"
                    )
                records.append(dataset_config.adapter.normalize(raw_row))
    return records


def _build_record(
    run_id: int, model_id: int, dataset_id: int, normalized: NormalizedRecord
) -> Record:
    return Record(
        run_id=run_id,
        model_id=model_id,
        dataset_id=dataset_id,
        item_id=normalized.item_id,
        item_index=normalized.item_index,
        prompt=normalized.prompt,
        question=normalized.question,
        target_json=normalized.target,
        output=normalized.output,
        raw_output=normalized.raw_output,
        is_correct=normalized.is_correct,
        output_length=normalized.output_length,
        inference_time=normalized.inference_time,
        original_json=normalized.original,
    )


def _average(values: Any) -> float | None:
    valid_values = [value for value in values if value is not None]
    if not valid_values:
        return None
    return sum(valid_values) / len(valid_values)


def _sha256_file(path: Path) -> str:
    return _sha256_files((path,))


def _sha256_files(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(str(path.name).encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Import benchmark JSONL data.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("../data"),
        help="Directory containing data/<model>/<dataset>.jsonl files.",
    )
    args = parser.parse_args()

    try:
        with SessionLocal() as db:
            results = ingest_data_dir(args.data_dir, db)
    except FileNotFoundError as exc:
        print(f"error: {exc}")
        raise SystemExit(1) from exc

    for result in results:
        print(
            f"{result.status}: {result.model_name}/{result.dataset_name} "
            f"run_id={result.run_id} total={result.total_count} "
            f"correct={result.correct_count} hash={result.source_hash[:12]}"
        )
    counts = {status: 0 for status in ("imported", "skipped", "failed")}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
    print(
        "summary: "
        f"imported={counts.get('imported', 0)} "
        f"skipped={counts.get('skipped', 0)} "
        f"failed={counts.get('failed', 0)}"
    )
    failed_results = [result for result in results if result.status == "failed"]
    if failed_results:
        print("failed sources:")
        for result in failed_results:
            print(
                f"- model={result.model_name} dataset={result.dataset_name} "
                f"source={result.source_path} error={result.error_type}: "
                f"{result.error_message}"
            )


if __name__ == "__main__":
    main()
