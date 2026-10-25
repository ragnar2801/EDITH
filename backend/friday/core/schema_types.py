"""API-facing types for money and time (D-032).

Amounts travel as JSON strings such as ``"1234567.89"``. JSON numbers are rejected,
because the JSON parser turns them into floats before validation and precision is lost.
Timestamps must carry a timezone and are normalised to UTC.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    Field,
    PlainSerializer,
    WithJsonSchema,
)

IST = ZoneInfo("Asia/Kolkata")

Currency = Literal["INR", "USD"]

_DECIMAL_PATTERN = r"^-?\d+(\.\d+)?$"


def _require_string(value: Any) -> Any:
    if isinstance(value, float | int) and not isinstance(value, bool):
        raise ValueError('send exact values as strings, e.g. "1234.50", not JSON numbers')
    return value


def _decimal_string(decimal_places: int) -> Any:
    return Annotated[
        Decimal,
        BeforeValidator(_require_string),
        Field(decimal_places=decimal_places),
        PlainSerializer(lambda value: format(value, "f"), return_type=str, when_used="json"),
        WithJsonSchema({"type": "string", "pattern": _DECIMAL_PATTERN}),
    ]


Amount = _decimal_string(2)
"""Cash amount: 2 decimal places."""

Price = _decimal_string(4)
"""Price or NAV: 4 decimal places."""

Nav = _decimal_string(8)
"""Mutual fund NAV, exactly as published: up to 8 decimal places (D-045)."""

Units = _decimal_string(8)
"""Quantity or units: up to 8 decimal places (fractional US shares)."""

FxRate = _decimal_string(6)
"""Exchange rate: 6 decimal places."""

Percent = _decimal_string(2)
"""Percentage, e.g. an allocation share: 2 decimal places."""

Figure = _decimal_string(2)
"""A plain figure such as a Sharpe ratio or a number of years: 2 decimal places."""

Ratio = _decimal_string(6)
"""A growth index or ratio, e.g. 100 → 123.456789: 6 decimal places."""


def _to_utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


UtcDatetime = Annotated[AwareDatetime, AfterValidator(_to_utc)]
"""Timezone-aware timestamp, normalised to UTC. Serialised as ``...Z``."""


class Money(BaseModel):
    amount: Amount
    currency: Currency


def to_ist(value: datetime) -> datetime:
    """Convert a UTC timestamp for display in IST."""
    return value.astimezone(IST)
