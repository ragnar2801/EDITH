"""Holding tables: lots, SIPs and the units taken out of lots.

A lot is one buy: a lump sum, or one SIP instalment. Selling isn't a transaction of its
own: it takes units out of lots I pick, and each take is kept as a ``LotSale``. Lots and
SIPs may belong to a bucket.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from friday.core.buckets.models import Bucket
from friday.core.db import Base
from friday.core.instruments.models import Instrument
from friday.core.types import DecimalText, UtcDateTime


class Sip(Base):
    __tablename__ = "sips"

    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"))
    bucket_id: Mapped[int | None] = mapped_column(ForeignKey("buckets.id", ondelete="SET NULL"))
    amount: Mapped[Decimal] = mapped_column(DecimalText(2))
    day: Mapped[int]  # day of the month, 1–28
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime())

    instrument: Mapped[Instrument] = relationship()
    bucket: Mapped[Bucket | None] = relationship()
    instalments: Mapped[list[Lot]] = relationship(
        back_populates="sip", cascade="all, delete-orphan", order_by="Lot.due_month"
    )


class Lot(Base):
    __tablename__ = "lots"
    __table_args__ = (UniqueConstraint("sip_id", "due_month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"))
    sip_id: Mapped[int | None] = mapped_column(ForeignKey("sips.id", ondelete="CASCADE"))
    # Its SIP's bucket for an instalment. No bucket: real money not set aside for a goal.
    bucket_id: Mapped[int | None] = mapped_column(ForeignKey("buckets.id", ondelete="SET NULL"))
    due_month: Mapped[date | None] = mapped_column(Date)  # SIP instalments: 1st of the month
    buy_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(DecimalText(2))
    nav: Mapped[Decimal] = mapped_column(DecimalText(8))
    units: Mapped[Decimal] = mapped_column(DecimalText(8))
    units_remaining: Mapped[Decimal] = mapped_column(DecimalText(8))
    edited: Mapped[bool] = mapped_column(default=False)  # instalment changed by hand
    skipped: Mapped[bool] = mapped_column(default=False)  # instalment that didn't happen
    note: Mapped[str | None] = mapped_column(String(200))
    # Bought in another app and copied in (``"fm"``): read-only here, changed there.
    source: Mapped[str | None] = mapped_column(String(8))
    source_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime())

    instrument: Mapped[Instrument] = relationship()
    bucket: Mapped[Bucket | None] = relationship()
    sip: Mapped[Sip | None] = relationship(back_populates="instalments")
    sales: Mapped[list[LotSale]] = relationship(
        back_populates="lot", order_by="(LotSale.sale_date, LotSale.id)"
    )


class LotSale(Base):
    """Units taken out of one lot on one date."""

    __tablename__ = "lot_sales"

    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id"))
    sale_date: Mapped[date] = mapped_column(Date)
    units: Mapped[Decimal] = mapped_column(DecimalText(8))
    nav: Mapped[Decimal] = mapped_column(DecimalText(8))
    source_id: Mapped[str | None] = mapped_column(String(64))  # set when the lot has a source
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())

    lot: Mapped[Lot] = relationship(back_populates="sales")
