"""Bucket tables: a target split of funds with weights, a rebalance policy and a
benchmark."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from friday.core.db import Base
from friday.core.instruments.models import Instrument
from friday.core.types import DecimalText, UtcDateTime

REBALANCE = ("none", "monthly", "quarterly", "yearly")


class Bucket(Base):
    __tablename__ = "buckets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str | None] = mapped_column(String(500))
    rebalance: Mapped[str] = mapped_column(String(10), default="none")
    benchmark_id: Mapped[int | None] = mapped_column(ForeignKey("instruments.id"))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime())

    benchmark: Mapped[Instrument | None] = relationship()
    funds: Mapped[list[BucketFund]] = relationship(
        back_populates="bucket",
        cascade="all, delete-orphan",
        order_by="(BucketFund.position, BucketFund.instrument_id)",
    )


class BucketFund(Base):
    __tablename__ = "bucket_funds"

    bucket_id: Mapped[int] = mapped_column(
        ForeignKey("buckets.id", ondelete="CASCADE"), primary_key=True
    )
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), primary_key=True)
    weight_pct: Mapped[Decimal] = mapped_column(DecimalText(2))
    position: Mapped[int] = mapped_column(default=0)  # the order I listed them in

    bucket: Mapped[Bucket] = relationship(back_populates="funds")
    instrument: Mapped[Instrument] = relationship()
