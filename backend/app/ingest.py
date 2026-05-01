from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.base import NormalizedRecord
from app.adapters.registry import DatasetConfig, get_dataset_config, iter_dataset_configs
from app.database import SessionLocal
from app.models.benchmark import Dataset, EvaluationRun, MetricsSummary, Model, Record


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


@dataclass(frozen=True)
class ImportSource:
    model_name: str
    dataset_name: str
    source_path: Path
    files: tuple[Path, ...]


def ingest_data_dir(data_dir: Path, db: Session) -> list[ImportResult]:
    data_dir = data_dir.expanduser().resolve()
    _ensure_datasets(db)

    results: list[ImportResult] = []
    for source in _iter_import_sources(data_dir):
        dataset_config = get_dataset_config(source.dataset_name)
        if dataset_config is None:
            continue

        result = ingest_source(
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


def ingest_source(
    *,
    db: Session,
    source: ImportSource,
    dataset_config: DatasetConfig,
) -> ImportResult:
    source_path = source.source_path.expanduser().resolve()
    source_files = tuple(path.expanduser().resolve() for path in source.files)
    source_hash = _sha256_files(source_files)

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


def _ensure_datasets(db: Session) -> None:
    for dataset_config in iter_dataset_configs():
        _get_or_create_dataset(db, dataset_config)
    db.commit()


def _iter_import_sources(data_dir: Path) -> list[ImportSource]:
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory does not exist: {data_dir}")

    sources: list[ImportSource] = []
    for path in sorted(data_dir.glob("*/*.jsonl")):
        if not path.is_file():
            continue
        dataset_name = path.stem
        if get_dataset_config(dataset_name) is None:
            continue
        sources.append(
            ImportSource(
                model_name=path.parent.name,
                dataset_name=dataset_name,
                source_path=path,
                files=(path,),
            )
        )

    nested_files_by_folder: dict[Path, list[Path]] = {}
    for path in sorted(data_dir.glob("*/*/*.jsonl")):
        if not path.is_file():
            continue
        dataset_name = path.parent.name
        if get_dataset_config(dataset_name) is None:
            continue
        nested_files_by_folder.setdefault(path.parent, []).append(path)

    for folder, files in sorted(nested_files_by_folder.items()):
        sources.append(
            ImportSource(
                model_name=folder.parent.name,
                dataset_name=folder.name,
                source_path=folder,
                files=tuple(sorted(files)),
            )
        )

    return sources


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
    parser = argparse.ArgumentParser(description="Import benchmark JSONL data.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("../data"),
        help="Directory containing data/<model>/<dataset>.jsonl files.",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        results = ingest_data_dir(args.data_dir, db)

    for result in results:
        print(
            f"{result.status}: {result.model_name}/{result.dataset_name} "
            f"run_id={result.run_id} total={result.total_count} "
            f"correct={result.correct_count} hash={result.source_hash[:12]}"
        )


if __name__ == "__main__":
    main()
