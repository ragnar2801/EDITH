"""Rename buckets to models: a target split of funds is now called a model.

SQLite rewrites the foreign keys that point at a renamed table, so only the tables, the
columns and the one index are renamed here.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-31
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.rename_table("buckets", "models")
    op.rename_table("bucket_funds", "model_funds")
    op.alter_column("model_funds", "bucket_id", new_column_name="model_id")
    op.drop_index("ix_backtest_runs_bucket_id", table_name="backtest_runs")
    op.alter_column("backtest_runs", "bucket_id", new_column_name="model_id")
    op.create_index("ix_backtest_runs_model_id", "backtest_runs", ["model_id"])
    op.alter_column("plan_settings", "target_bucket_id", new_column_name="target_model_id")


def downgrade() -> None:
    op.alter_column("plan_settings", "target_model_id", new_column_name="target_bucket_id")
    op.drop_index("ix_backtest_runs_model_id", table_name="backtest_runs")
    op.alter_column("backtest_runs", "model_id", new_column_name="bucket_id")
    op.create_index("ix_backtest_runs_bucket_id", "backtest_runs", ["bucket_id"])
    op.alter_column("model_funds", "model_id", new_column_name="bucket_id")
    op.rename_table("model_funds", "bucket_funds")
    op.rename_table("models", "buckets")
