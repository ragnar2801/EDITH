"""Column types that keep money and time exact in SQLite (D-032).

SQLite has no exact decimal type: a ``NUMERIC`` column silently stores floats. Money,
prices, units and FX rates are therefore stored as plain-notation decimal text and come
back as ``Decimal``. Timestamps are stored as UTC text in one sortable format and come
back as timezone-aware ``datetime`` objects.
"""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import String
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

_UTC_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


class DecimalText(TypeDecorator[Decimal]):
    """Exact decimal stored as text. Floats are refused; extra decimal places are an error."""

    impl = String
    cache_ok = True

    def __init__(self, scale: int | None = None) -> None:
        super().__init__()
        self.scale = scale

    def process_bind_param(self, value: Decimal | int | str | None, dialect: Dialect) -> str | None:
        if value is None:
            return None
        if isinstance(value, float):
            raise TypeError("float is not allowed for exact values; use Decimal or str")
        number = value if isinstance(value, Decimal) else Decimal(value)
        if not number.is_finite():
            raise ValueError(f"not a finite number: {number}")
        if self.scale is not None and -number.normalize().as_tuple().exponent > self.scale:
            raise ValueError(f"{number} has more than {self.scale} decimal places")
        return format(number, "f")

    def process_result_value(self, value: str | None, dialect: Dialect) -> Decimal | None:
        return None if value is None else Decimal(value)


class UtcDateTime(TypeDecorator[datetime]):
    """Timezone-aware datetime stored as UTC text. Naive datetimes are refused."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("naive datetime is not allowed; attach a timezone")
        return value.astimezone(UTC).strftime(_UTC_FORMAT)

    def process_result_value(self, value: str | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return datetime.strptime(value, _UTC_FORMAT).replace(tzinfo=UTC)
