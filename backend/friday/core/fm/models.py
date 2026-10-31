"""One row per import of FM's lots feed."""

from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from friday.core.db import Base
from friday.core.types import UtcDateTime


class FmImport(Base):
    __tablename__ = "fm_imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(8))  # ok | failed
    imported_at: Mapped[datetime] = mapped_column(UtcDateTime())
    sent_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    """When FM built the feed it sent."""
    fm_schema: Mapped[int | None]  # FM's database version
    funds: Mapped[int] = mapped_column(default=0)
    lots: Mapped[int] = mapped_column(default=0)
    sales: Mapped[int] = mapped_column(default=0)
    added: Mapped[int] = mapped_column(default=0)
    removed: Mapped[int] = mapped_column(default=0)
    warnings: Mapped[str] = mapped_column(Text, default="[]")
    message: Mapped[str | None] = mapped_column(Text)
