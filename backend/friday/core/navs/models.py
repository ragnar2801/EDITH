"""NAV tables.

One row per fund per NAV date, stored exactly as published. Rows are only added, or
corrected when the source corrects a value; a re-sync never duplicates them.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from friday.core.db import Base
from friday.core.types import DecimalText, UtcDateTime


class FundNav(Base):
    __tablename__ = "fund_navs"

    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), primary_key=True
    )
    nav_date: Mapped[date] = mapped_column(Date, primary_key=True)
    nav: Mapped[Decimal] = mapped_column(DecimalText(8))
    source: Mapped[str] = mapped_column(String(8))  # mfapi | amfi


class TrackedFund(Base):
    """A fund I asked Friday to keep NAVs for. Funds in a bucket are tracked anyway."""

    __tablename__ = "tracked_funds"

    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), primary_key=True
    )
    added_at: Mapped[datetime] = mapped_column(UtcDateTime())


class NavSync(Base):
    """One row per sync run: what happened to each fund, as JSON in ``results``."""

    __tablename__ = "nav_syncs"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(8))  # ok | partial | failed
    started_at: Mapped[datetime] = mapped_column(UtcDateTime())
    finished_at: Mapped[datetime] = mapped_column(UtcDateTime())
    funds: Mapped[int] = mapped_column(default=0)
    added: Mapped[int] = mapped_column(default=0)
    corrected: Mapped[int] = mapped_column(default=0)
    failed: Mapped[int] = mapped_column(default=0)
    results: Mapped[str] = mapped_column(Text, default="[]")
