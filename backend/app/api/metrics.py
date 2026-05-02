from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.database import get_db
from app.data_sync import sync_data_if_needed
from app.dataset_categories import DATASET_CATEGORIES, iter_configured_dataset_keys
from app.models.benchmark import Dataset, EvaluationRun, MetricsSummary, Model

MetricName = Literal["accuracy", "avg_output_length", "avg_inference_time"]

SUCCESSFUL_RUN_STATUSES = ("completed", "success", "successful")

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/matrix")
def get_metrics_matrix(
    metric: MetricName = "accuracy",
    datasets: str | None = None,
    _: None = Depends(sync_data_if_needed),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    dataset_models = db.scalars(select(Dataset).order_by(Dataset.name)).all()
    models = db.scalars(select(Model).order_by(Model.name)).all()
    selected_dataset_keys = _parse_selected_dataset_keys(datasets)

    latest_metrics = _latest_metrics_subquery()
    return _get_grouped_matrix(
        db,
        metric,
        models,
        dataset_models,
        latest_metrics,
        selected_dataset_keys,
    )


def _get_grouped_matrix(
    db: Session,
    metric: MetricName,
    models: list[Model],
    datasets: list[Dataset],
    latest_metrics: Any,
    selected_dataset_keys: set[str] | None,
) -> dict[str, object]:
    latest_rows = db.execute(
        select(latest_metrics).where(latest_metrics.c.row_number == 1)
    ).all()
    latest_rows = _filter_existing_source_rows(latest_rows)
    dataset_name_by_id = {dataset.id: dataset.name for dataset in datasets}
    values_by_model_dataset = {
        (row.model_id, dataset_name_by_id[row.dataset_id]): getattr(row, metric)
        for row in latest_rows
        if row.dataset_id in dataset_name_by_id
    }

    rows_by_model_id: dict[int, list[Any]] = {}
    for row in latest_rows:
        if row.dataset_id in dataset_name_by_id:
            rows_by_model_id.setdefault(row.model_id, []).append(row)
    models_with_metrics = [
        model for model in models if model.id in rows_by_model_id
    ]

    groups = _build_metric_groups(datasets, selected_dataset_keys)
    dataset_names = [
        column["key"]
        for group in groups
        for column in group["columns"]
        if column["type"] == "dataset"
    ]
    model_names = [model.name for model in models_with_metrics]
    rows = [
        {
            "model": model.name,
            "values": _build_metric_values(
                metric,
                model.id,
                groups,
                rows_by_model_id.get(model.id, []),
                dataset_name_by_id,
                values_by_model_dataset,
            ),
        }
        for model in models_with_metrics
    ]

    return {
        "metric": metric,
        "datasets": dataset_names,
        "models": model_names,
        "groups": groups,
        "rows": rows,
    }


def _build_metric_groups(
    datasets: list[Dataset], selected_dataset_keys: set[str] | None
) -> list[dict[str, object]]:
    active_dataset_names = {
        dataset.name for dataset in datasets if dataset.is_active
    }
    configured_dataset_names = set(iter_configured_dataset_keys())
    groups: list[dict[str, object]] = [
        {
            "key": "overall",
            "label": "Overall",
            "columns": [
                {
                    "key": "__overall__",
                    "label": "Overall",
                    "type": "overall",
                }
            ],
        }
    ]

    for category in DATASET_CATEGORIES:
        selected_category_datasets = [
            dataset
            for dataset in category.datasets
            if selected_dataset_keys is None or dataset.key in selected_dataset_keys
        ]
        if not selected_category_datasets:
            continue

        columns: list[dict[str, object]] = [
            {
                "key": f"__category_avg__:{category.key}",
                "label": f"{category.label} Avg",
                "type": "category_avg",
                "category": category.key,
            }
        ]
        columns.extend(
            {
                "key": dataset.key,
                "label": dataset.label,
                "type": "dataset",
                "category": category.key,
            }
            for dataset in selected_category_datasets
        )
        groups.append(
            {
                "key": category.key,
                "label": category.label,
                "columns": columns,
            }
        )

    extra_datasets: list[str] = []
    if selected_dataset_keys is not None:
        extra_datasets = sorted(
            dataset_name
            for dataset_name in active_dataset_names - configured_dataset_names
            if dataset_name in selected_dataset_keys
        )
    if extra_datasets:
        groups.append(
            {
                "key": "uncategorized",
                "label": "Uncategorized",
                "columns": [
                    {
                        "key": "__category_avg__:uncategorized",
                        "label": "Uncategorized Avg",
                        "type": "category_avg",
                        "category": "uncategorized",
                    },
                    *(
                        {
                            "key": dataset_name,
                            "label": dataset_name,
                            "type": "dataset",
                            "category": "uncategorized",
                        }
                        for dataset_name in extra_datasets
                    ),
                ],
            }
        )

    return groups


def _parse_selected_dataset_keys(datasets: str | None) -> set[str] | None:
    if datasets is None:
        return None
    return {dataset.strip() for dataset in datasets.split(",") if dataset.strip()}


def _build_metric_values(
    metric: MetricName,
    model_id: int,
    groups: list[dict[str, object]],
    model_rows: list[Any],
    dataset_name_by_id: dict[int, str],
    values_by_model_dataset: dict[tuple[int, str], float | None],
) -> dict[str, float | None]:
    selected_dataset_names = {
        column["key"]
        for group in groups
        for column in group["columns"]
        if column["type"] == "dataset"
    }
    selected_rows = [
        row
        for row in model_rows
        if dataset_name_by_id.get(row.dataset_id) in selected_dataset_names
    ]
    values: dict[str, float | None] = {
        "__overall__": _weighted_metric(selected_rows, metric)
    }

    for group in groups:
        category_dataset_names = [
            column["key"]
            for column in group["columns"]
            if column["type"] == "dataset"
        ]
        category_rows = [
            row
            for row in model_rows
            if dataset_name_by_id.get(row.dataset_id) in category_dataset_names
        ]

        for column in group["columns"]:
            if column["type"] == "category_avg":
                values[column["key"]] = _weighted_metric(category_rows, metric)
            elif column["type"] == "dataset":
                values[column["key"]] = values_by_model_dataset.get(
                    (model_id, column["key"])
                )

    return values


@router.get("/overall")
def get_overall_metrics(
    _: None = Depends(sync_data_if_needed),
    db: Session = Depends(get_db),
) -> dict[str, list[dict[str, object]]]:
    models = db.scalars(select(Model).order_by(Model.name)).all()
    latest_metrics = _latest_metrics_subquery()
    latest_rows = db.execute(
        select(latest_metrics).where(latest_metrics.c.row_number == 1)
    ).all()
    latest_rows = _filter_existing_source_rows(latest_rows)

    rows_by_model_id: dict[int, list[Any]] = {}
    for row in latest_rows:
        rows_by_model_id.setdefault(row.model_id, []).append(row)

    rows: list[dict[str, object]] = []
    for model in models:
        model_rows = rows_by_model_id.get(model.id, [])
        if not model_rows:
            continue
        total_count = sum(row.total_count for row in model_rows)
        correct_count = sum(row.correct_count for row in model_rows)
        rows.append(
            {
                "model": model.name,
                "accuracy": (correct_count / total_count) if total_count else None,
                "avg_output_length": _weighted_average(
                    model_rows, "avg_output_length"
                ),
                "avg_inference_time": _weighted_average(
                    model_rows, "avg_inference_time"
                ),
                "dataset_count": len(model_rows),
                "total_count": total_count,
                "correct_count": correct_count,
            }
        )

    rows.sort(
        key=lambda row: (
            row["accuracy"] is None,
            -(row["accuracy"] or 0),
            row["model"],
        )
    )
    return {"rows": rows}


def _latest_metrics_subquery() -> Any:
    return (
        select(
            MetricsSummary.model_id.label("model_id"),
            MetricsSummary.dataset_id.label("dataset_id"),
            MetricsSummary.accuracy.label("accuracy"),
            MetricsSummary.avg_output_length.label("avg_output_length"),
            MetricsSummary.avg_inference_time.label("avg_inference_time"),
            MetricsSummary.total_count.label("total_count"),
            MetricsSummary.correct_count.label("correct_count"),
            EvaluationRun.source_path.label("source_path"),
            func.row_number()
            .over(
                partition_by=(MetricsSummary.model_id, MetricsSummary.dataset_id),
                order_by=(EvaluationRun.created_at.desc(), EvaluationRun.id.desc()),
            )
            .label("row_number"),
        )
        .join(EvaluationRun, EvaluationRun.id == MetricsSummary.run_id)
        .where(EvaluationRun.status.in_(SUCCESSFUL_RUN_STATUSES))
        .subquery()
    )


def _filter_existing_source_rows(rows: list[Any]) -> list[Any]:
    return [
        row
        for row in rows
        if row.source_path and Path(row.source_path).expanduser().exists()
    ]


def _weighted_average(rows: list[Any], metric: str) -> float | None:
    valid_rows = [
        row
        for row in rows
        if getattr(row, metric) is not None and row.total_count > 0
    ]
    total_count = sum(row.total_count for row in valid_rows)
    if total_count == 0:
        return None
    return (
        sum(getattr(row, metric) * row.total_count for row in valid_rows)
        / total_count
    )


def _weighted_metric(rows: list[Any], metric: MetricName) -> float | None:
    if metric == "accuracy":
        return _weighted_accuracy(rows)
    return _weighted_average(rows, metric)


def _weighted_accuracy(rows: list[Any]) -> float | None:
    total_count = sum(row.total_count for row in rows)
    if total_count == 0:
        return None
    return sum(row.correct_count for row in rows) / total_count
