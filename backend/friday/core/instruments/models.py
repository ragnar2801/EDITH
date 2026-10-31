"""Instrument tables.

Every stock, ETF and mutual fund scheme Friday knows about. Rows are never deleted:
anything that drops off its source list is marked inactive, so holdings and history
keep pointing at it.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from friday.core.db import Base
from friday.core.types import DecimalText, UtcDateTime

BUCKETS = ("equity", "debt", "gold", "silver", "other")
"""Allocation buckets. Each instrument's split over these sums to 100."""


class AllocationColumns:
    """Percent of the instrument in each bucket. All empty means unclassified."""

    equity_pct: Mapped[Decimal | None] = mapped_column(DecimalText(2))
    debt_pct: Mapped[Decimal | None] = mapped_column(DecimalText(2))
    gold_pct: Mapped[Decimal | None] = mapped_column(DecimalText(2))
    silver_pct: Mapped[Decimal | None] = mapped_column(DecimalText(2))
    other_pct: Mapped[Decimal | None] = mapped_column(DecimalText(2))
    exposure: Mapped[str] = mapped_column(String(8))  # IN | US | GLOBAL

    def allocation(self) -> dict[str, Decimal]:
        """Non-zero buckets, e.g. ``{"equity": Decimal("75"), "debt": Decimal("25")}``."""
        shares = {bucket: getattr(self, f"{bucket}_pct") for bucket in BUCKETS}
        return {bucket: pct for bucket, pct in shares.items() if pct}

    def set_allocation(self, allocation: dict[str, Decimal]) -> None:
        for bucket in BUCKETS:
            setattr(self, f"{bucket}_pct", allocation.get(bucket))


class Instrument(AllocationColumns, Base):
    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))  # stock | etf | mutual_fund
    name: Mapped[str] = mapped_column(String(300))
    market: Mapped[str] = mapped_column(String(2))  # IN | US: where it trades or is domiciled
    currency: Mapped[str] = mapped_column(String(3))
    # Which list owns this row and decides whether it is active: nse | amfi | nasdaqtrader
    source: Mapped[str] = mapped_column(String(16))
    is_active: Mapped[bool] = mapped_column(default=True)

    # Listed instruments
    exchange: Mapped[str | None] = mapped_column(String(16))
    symbol: Mapped[str | None] = mapped_column(String(40))
    isin: Mapped[str | None] = mapped_column(String(12), index=True)
    series: Mapped[str | None] = mapped_column(String(4))  # NSE series: EQ, BE, BZ
    listed_on: Mapped[date | None] = mapped_column(Date)
    cik: Mapped[str | None] = mapped_column(String(10))  # SEC company id (US)

    # Mutual funds, and NSE ETFs matched to their AMFI scheme
    amfi_code: Mapped[str | None] = mapped_column(String(10), unique=True)
    isin_reinvestment: Mapped[str | None] = mapped_column(String(12))
    fund_house: Mapped[str | None] = mapped_column(String(120))
    scheme_type: Mapped[str | None] = mapped_column(String(20))  # Open Ended, Close Ended...
    fund_category: Mapped[str | None] = mapped_column(String(120))
    plan: Mapped[str | None] = mapped_column(String(8))  # direct | regular
    option: Mapped[str | None] = mapped_column(String(120))  # as AMFI writes it
    option_kind: Mapped[str | None] = mapped_column(String(8))  # growth | idcw | bonus | other
    scheme_key: Mapped[str | None] = mapped_column(String(400), index=True)  # groups variants

    created_at: Mapped[datetime] = mapped_column(UtcDateTime())
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime())

    aliases: Mapped[list[InstrumentAlias]] = relationship(
        back_populates="instrument", cascade="all, delete-orphan", order_by="InstrumentAlias.id"
    )
    override: Mapped[ClassificationOverride | None] = relationship(
        back_populates="instrument", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # A symbol is unique per exchange among *active* instruments only: exchanges reuse
        # the symbols of delisted companies, and the old row must keep its own.
        Index(
            "uq_instruments_active_listing",
            "exchange",
            "symbol",
            unique=True,
            sqlite_where=text("is_active AND symbol IS NOT NULL"),
        ),
    )


class InstrumentAlias(Base):
    """An older symbol or name, so searches for "Zomato" still find Eternal."""

    __tablename__ = "instrument_aliases"

    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(8))  # symbol | name
    value: Mapped[str] = mapped_column(String(300))
    changed_on: Mapped[date | None] = mapped_column(Date)

    instrument: Mapped[Instrument] = relationship(back_populates="aliases")

    __table_args__ = (UniqueConstraint("instrument_id", "kind", "value"),)


class ClassificationOverride(AllocationColumns, Base):
    """My own classification for an instrument. Wins over the rules; refresh never touches it."""

    __tablename__ = "instrument_overrides"

    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), primary_key=True
    )
    note: Mapped[str | None] = mapped_column(String(500))
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime())

    instrument: Mapped[Instrument] = relationship(back_populates="override")


class InstrumentImport(Base):
    """One row per source per refresh run: what happened and when."""

    __tablename__ = "instrument_imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(8))  # ok | failed
    started_at: Mapped[datetime] = mapped_column(UtcDateTime())
    finished_at: Mapped[datetime] = mapped_column(UtcDateTime())
    rows: Mapped[int] = mapped_column(default=0)
    added: Mapped[int] = mapped_column(default=0)
    updated: Mapped[int] = mapped_column(default=0)
    deactivated: Mapped[int] = mapped_column(default=0)
    reactivated: Mapped[int] = mapped_column(default=0)
    message: Mapped[str | None] = mapped_column(String(2000))
