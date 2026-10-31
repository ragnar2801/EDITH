"""Buckets: money set aside for a goal, real or paper, that purchases and SIPs belong to.

The target model leaves the plan settings: each bucket has its own model. If a target was
set, a real bucket named after it takes every existing purchase and SIP, so the Invest plan
works as before.

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-31
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "buckets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("paper", sa.Boolean(), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=True),
        sa.Column("fm_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["model_id"], ["models.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fm_id"),
        sa.UniqueConstraint("name"),
    )
    with op.batch_alter_table("lots", schema=None) as batch_op:
        batch_op.add_column(sa.Column("bucket_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_lots_bucket_id", "buckets", ["bucket_id"], ["id"], ondelete="SET NULL"
        )
    with op.batch_alter_table("sips", schema=None) as batch_op:
        batch_op.add_column(sa.Column("bucket_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_sips_bucket_id", "buckets", ["bucket_id"], ["id"], ondelete="SET NULL"
        )

    conn = op.get_bind()
    target = conn.execute(
        sa.text(
            "SELECT models.id, models.name FROM plan_settings"
            " JOIN models ON models.id = plan_settings.target_model_id"
        )
    ).first()
    held = conn.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM lots) OR EXISTS (SELECT 1 FROM sips)")
    ).scalar()
    if target is not None and held:
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        conn.execute(
            sa.text(
                "INSERT INTO buckets (name, paper, model_id, created_at, updated_at)"
                " VALUES (:name, 0, :model, :now, :now)"
            ),
            {"name": target.name, "model": target.id, "now": now},
        )
        bucket = conn.execute(sa.text("SELECT id FROM buckets")).scalar()
        conn.execute(sa.text("UPDATE lots SET bucket_id = :id"), {"id": bucket})
        conn.execute(sa.text("UPDATE sips SET bucket_id = :id"), {"id": bucket})

    with op.batch_alter_table("plan_settings", schema=None) as batch_op:
        batch_op.drop_column("target_model_id")


def downgrade() -> None:
    with op.batch_alter_table("plan_settings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("target_model_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_plan_settings_target_model_id",
            "models",
            ["target_model_id"],
            ["id"],
            ondelete="SET NULL",
        )
    with op.batch_alter_table("sips", schema=None) as batch_op:
        batch_op.drop_constraint("fk_sips_bucket_id", type_="foreignkey")
        batch_op.drop_column("bucket_id")
    with op.batch_alter_table("lots", schema=None) as batch_op:
        batch_op.drop_constraint("fk_lots_bucket_id", type_="foreignkey")
        batch_op.drop_column("bucket_id")
    op.drop_table("buckets")
