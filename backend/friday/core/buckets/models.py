"""Bucket table: a named pile of money, such as Retirement, that purchases and SIPs belong to.

A bucket follows a model (the split new money moves it towards) or none yet. A paper bucket
holds pretend purchases at real NAVs, kept out of the portfolio's totals. A bucket made by
an FM sync keeps FM's bucket id, so a rename in FM renames it here.
"""

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from friday.core.db import Base
from friday.core.models.models import Model
from friday.core.types import UtcDateTime


class Bucket(Base):
    __tablename__ = "buckets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    paper: Mapped[bool] = mapped_column(default=False)
    model_id: Mapped[int | None] = mapped_column(ForeignKey("models.id", ondelete="SET NULL"))
    fm_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime())
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime())

    model: Mapped[Model | None] = relationship()
