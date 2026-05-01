"""allow duplicate record item ids within a run

Revision ID: 20260502_0002
Revises: 20260501_0001
Create Date: 2026-05-02 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260502_0002"
down_revision: str | None = "20260501_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE records DROP CONSTRAINT IF EXISTS uq_records_run_item")


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_records_run_item",
        "records",
        ["run_id", "item_id"],
    )
