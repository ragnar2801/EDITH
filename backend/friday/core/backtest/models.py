"""Stored backtest runs."""

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from friday.core.db import Base
from friday.core.types import UtcDateTime


class BacktestRun(Base):
    """One run: its parameters and its result, as JSON. Unsaved runs are pruned."""

    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    bucket_id: Mapped[int] = mapped_column(ForeignKey("buckets.id", ondelete="CASCADE"), index=True)
    strategy: Mapped[str] = mapped_column(String(10))
    params: Mapped[str] = mapped_column(Text)
    result: Mapped[str] = mapped_column(Text)
    saved: Mapped[bool] = mapped_column(default=False)
    name: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())
