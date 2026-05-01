from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Text, cast, func, or_, select
from sqlalchemy.orm import Session

from app.data_sync import sync_data_if_needed
from app.database import get_db
from app.models.benchmark import Dataset, EvaluationRun, Model, Record

SUCCESSFUL_RUN_STATUSES = ("completed", "success", "successful")

router = APIRouter(prefix="/records", tags=["records"])


@router.get("/search")
def search_records(
    dataset: str | None = None,
    model: str | None = None,
    correct: str | None = Query(default=None),
    keyword: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    _: None = Depends(sync_data_if_needed),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    correct_filter = _parse_correct_filter(correct)
    latest_runs = _latest_successful_runs_subquery()

    query = (
        select(Record, Model, Dataset, EvaluationRun)
        .join(Model, Model.id == Record.model_id)
        .join(Dataset, Dataset.id == Record.dataset_id)
        .join(EvaluationRun, EvaluationRun.id == Record.run_id)
        .join(latest_runs, latest_runs.c.run_id == Record.run_id)
        .where(latest_runs.c.row_number == 1)
    )

    if dataset:
        query = query.where(Dataset.name == dataset)
    if model:
        query = query.where(Model.name == model)
    if correct_filter == "unknown":
        query = query.where(Record.is_correct.is_(None))
    elif correct_filter is not None:
        query = query.where(Record.is_correct.is_(correct_filter))

    normalized_keyword = keyword.strip() if keyword else ""
    if normalized_keyword:
        pattern = f"%{normalized_keyword}%"
        query = query.where(
            or_(
                Record.item_id.ilike(pattern),
                Record.question.ilike(pattern),
                Record.prompt.ilike(pattern),
                cast(Record.target_json, Text).ilike(pattern),
                Record.output.ilike(pattern),
                Record.raw_output.ilike(pattern),
            )
        )

    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    rows = db.execute(
        query.order_by(Record.item_index.asc().nullslast(), Record.item_id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return {
        "items": [
            _serialize_record(record, record_model, record_dataset, run)
            for record, record_model, record_dataset, run in rows
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
    }


def _latest_successful_runs_subquery():
    return (
        select(
            EvaluationRun.id.label("run_id"),
            EvaluationRun.model_id.label("model_id"),
            EvaluationRun.dataset_id.label("dataset_id"),
            func.row_number()
            .over(
                partition_by=(EvaluationRun.model_id, EvaluationRun.dataset_id),
                order_by=(EvaluationRun.created_at.desc(), EvaluationRun.id.desc()),
            )
            .label("row_number"),
        )
        .where(EvaluationRun.status.in_(SUCCESSFUL_RUN_STATUSES))
        .subquery()
    )


def _parse_correct_filter(value: str | None) -> bool | str | None:
    if value is None:
        return None

    normalized_value = value.strip().lower()
    if normalized_value == "":
        return None

    if normalized_value in {"true", "1", "yes"}:
        return True
    if normalized_value in {"false", "0", "no"}:
        return False
    if normalized_value in {"unknown", "null", "none"}:
        return "unknown"

    raise HTTPException(
        status_code=422,
        detail="correct must be true, false, unknown, or empty",
    )


def _serialize_record(
    record: Record,
    model: Model,
    dataset: Dataset,
    run: EvaluationRun,
) -> dict[str, object]:
    return {
        "id": record.id,
        "run_id": record.run_id,
        "model": model.name,
        "model_display_name": model.display_name,
        "dataset": dataset.name,
        "dataset_display_name": dataset.display_name,
        "item_id": record.item_id,
        "item_index": record.item_index,
        "question": record.question,
        "prompt": record.prompt,
        "target_json": record.target_json,
        "output": record.output,
        "raw_output": record.raw_output,
        "is_correct": record.is_correct,
        "output_length": record.output_length,
        "inference_time": record.inference_time,
        "original_json": record.original_json,
        "run": {
            "id": run.id,
            "source_path": run.source_path,
            "source_hash": run.source_hash,
            "status": run.status,
            "created_at": run.created_at,
        },
    }
