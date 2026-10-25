"""Cash tables (D-056, D-057): INR accounts with an earmark, and the plan's settings.

An account holds only its current balance. The settings are one row: which bucket is my
target split, the emergency goal and fund, and the staggering rule.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from friday.core.buckets.models import Bucket
from friday.core.db import Base
from friday.core.instruments.models import Instrument
from friday.core.types import DecimalText, UtcDateTime

EARMARKS = ("emergency", "deployable", "reserved")


class CashAccount(Base):
    __tablename__ = "cash_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    balance: Mapped[Decimal] = mapped_column(DecimalText(2))
    earmark: Mapped[str] = mapped_column(String(12))
    note: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime())


class PlanSettings(Base):
    """The one row of cash plan settings (id 1)."""

    __tablename__ = "plan_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    target_bucket_id: Mapped[int | None] = mapped_column(
        ForeignKey("buckets.id", ondelete="SET NULL")
    )
    emergency_goal: Mapped[Decimal] = mapped_column(DecimalText(2))
    emergency_fund_id: Mapped[int | None] = mapped_column(ForeignKey("instruments.id"))
    stagger_fund_id: Mapped[int | None] = mapped_column(ForeignKey("instruments.id"))
    stagger_threshold: Mapped[Decimal | None] = mapped_column(DecimalText(2))  # None: never
    stagger_months: Mapped[int]
    min_per_fund: Mapped[Decimal] = mapped_column(DecimalText(2))
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime())

    target_bucket: Mapped[Bucket | None] = relationship()
    emergency_fund: Mapped[Instrument | None] = relationship(foreign_keys=[emergency_fund_id])
    stagger_fund: Mapped[Instrument | None] = relationship(foreign_keys=[stagger_fund_id])
