"""One row per import of an FM database copy."""

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
    copied_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    """When the copy reached Friday: the file's modified time."""
    fm_schema: Mapped[int | None]
    funds: Mapped[int] = mapped_column(default=0)
    lots: Mapped[int] = mapped_column(default=0)
    sales: Mapped[int] = mapped_column(default=0)
    added: Mapped[int] = mapped_column(default=0)
    removed: Mapped[int] = mapped_column(default=0)
    warnings: Mapped[str] = mapped_column(Text, default="[]")
    message: Mapped[str | None] = mapped_column(Text)
