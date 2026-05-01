from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Text, and_, cast, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.data_sync import sync_data_if_needed
from app.database import get_db
from app.models.benchmark import Dataset, EvaluationRun, Model, Record

ComparePattern = Literal[
    "all",
    "a_correct_b_wrong",
    "a_wrong_b_correct",
    "both_correct",
    "both_wrong",
]

SUCCESSFUL_RUN_STATUSES = ("completed", "success", "successful")

router = APIRouter(prefix="/compare", tags=["compare"])


@router.get("")
def compare_records(
    dataset: str,
    model_a: str,
    model_b: str,
    pattern: ComparePattern = "all",
    keyword: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    _: None = Depends(sync_data_if_needed),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    record_a = aliased(Record)
    record_b = aliased(Record)
    run_a = aliased(EvaluationRun)
    run_b = aliased(EvaluationRun)
    model_a_alias = aliased(Model)
    model_b_alias = aliased(Model)
    latest_a = _latest_successful_runs_subquery("latest_a")
    latest_b = _latest_successful_runs_subquery("latest_b")

    query = (
        select(record_a, record_b, Dataset, model_a_alias, model_b_alias, run_a, run_b)
        .join(Dataset, Dataset.id == record_a.dataset_id)
        .join(model_a_alias, model_a_alias.id == record_a.model_id)
        .join(run_a, run_a.id == record_a.run_id)
        .join(latest_a, latest_a.c.run_id == record_a.run_id)
        .join(model_b_alias, model_b_alias.name == model_b)
        .outerjoin(
            latest_b,
            and_(
                latest_b.c.model_id == model_b_alias.id,
                latest_b.c.dataset_id == Dataset.id,
                latest_b.c.row_number == 1,
            ),
        )
        .outerjoin(run_b, run_b.id == latest_b.c.run_id)
        .outerjoin(
            record_b,
            and_(
                record_b.dataset_id == record_a.dataset_id,
                record_b.item_id == record_a.item_id,
                record_b.model_id == model_b_alias.id,
                record_b.run_id == latest_b.c.run_id,
            ),
        )
        .where(
            latest_a.c.row_number == 1,
            Dataset.name == dataset,
            model_a_alias.name == model_a,
        )
    )

    if pattern == "a_correct_b_wrong":
        query = query.where(
            record_a.is_correct.is_(True),
            record_b.is_correct.is_(False),
        )
    elif pattern == "a_wrong_b_correct":
        query = query.where(record_a.is_correct.is_(False), record_b.is_correct.is_(True))
    elif pattern == "both_correct":
        query = query.where(record_a.is_correct.is_(True), record_b.is_correct.is_(True))
    elif pattern == "both_wrong":
        query = query.where(record_a.is_correct.is_(False), record_b.is_correct.is_(False))

    normalized_keyword = keyword.strip() if keyword else ""
    if normalized_keyword:
        keyword_pattern = f"%{normalized_keyword}%"
        query = query.where(
            or_(
                record_a.item_id.ilike(keyword_pattern),
                record_a.question.ilike(keyword_pattern),
                record_a.prompt.ilike(keyword_pattern),
                cast(record_a.target_json, Text).ilike(keyword_pattern),
                record_a.output.ilike(keyword_pattern),
                record_a.raw_output.ilike(keyword_pattern),
                record_b.output.ilike(keyword_pattern),
                record_b.raw_output.ilike(keyword_pattern),
            )
        )

    total = (
        db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
        or 0
    )
    rows = db.execute(
        query.order_by(record_a.item_index.asc().nullslast(), record_a.item_id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return {
        "items": [
            _serialize_comparison(
                row_record_a,
                row_record_b,
                row_dataset,
                row_model_a,
                row_model_b,
            )
            for (
                row_record_a,
                row_record_b,
                row_dataset,
                row_model_a,
                row_model_b,
                *_,
            ) in rows
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
        "dataset": dataset,
        "model_a": model_a,
        "model_b": model_b,
        "pattern": pattern,
    }


def _latest_successful_runs_subquery(name: str):
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
        .subquery(name)
    )


def _serialize_comparison(
    record_a: Record,
    record_b: Record | None,
    dataset: Dataset,
    model_a: Model,
    model_b: Model,
) -> dict[str, object]:
    return {
        "dataset": dataset.name,
        "dataset_display_name": dataset.display_name,
        "item_id": record_a.item_id,
        "item_index": record_a.item_index,
        "question": record_a.question,
        "prompt": record_a.prompt,
        "target": record_a.target_json,
        "target_json": record_a.target_json,
        "model_a": {
            "model": model_a.name,
            "output": record_a.output,
            "raw_output": record_a.raw_output,
            "correct": record_a.is_correct,
            "length": record_a.output_length,
            "time": record_a.inference_time,
        },
        "model_b": {
            "model": model_b.name,
            "output": record_b.output if record_b else None,
            "raw_output": record_b.raw_output if record_b else None,
            "correct": record_b.is_correct if record_b else None,
            "length": record_b.output_length if record_b else None,
            "time": record_b.inference_time if record_b else None,
            "missing": record_b is None,
        },
    }
