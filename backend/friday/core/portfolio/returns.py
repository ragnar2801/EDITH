"""Returns of real money: pure arithmetic over dated cash flows, no database.

A flow is money I put in (``amount > 0``, a buy) or took out (``amount < 0``, a sale's
proceeds). Amounts are exact ``Decimal``s; XIRR is a float rounded to 2 places like the
backtest ratios.
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from friday.core.backtest.engine import figure, xirr

ZERO = Decimal(0)
HUNDRED = Decimal(100)
CENT = Decimal("0.01")

MIN_XIRR_DAYS = 365
"""XIRR is shown once the first money has been in this long; before that an annualised
figure swings wildly (a 2% gain in a month reads as 27% a year), so only the absolute
return is shown."""


@dataclass(frozen=True)
class Flow:
    date: date
    amount: Decimal


@dataclass(frozen=True)
class Returns:
    invested: Decimal
    """Every rupee put in."""
    redeemed: Decimal
    """Every rupee taken out."""
    value: Decimal
    """What is still held is worth, on ``on``."""
    gain: Decimal
    """``value + redeemed - invested``: realised and unrealised P&L together."""
    return_pct: Decimal | None
    """``gain ÷ invested``, in percent; ``None`` when nothing was put in."""
    xirr_pct: Decimal | None
    """Money-weighted annual return, in percent; ``None`` under :data:`MIN_XIRR_DAYS`."""
    since: date | None
    on: date


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, ROUND_HALF_UP)


def pct(part: Decimal, whole: Decimal) -> Decimal | None:
    return money(part / whole * HUNDRED) if whole > 0 else None


def returns(flows: list[Flow], value: Decimal, on: date) -> Returns:
    """Returns of ``flows`` with ``value`` still held on ``on``."""
    flows = sorted(flows, key=lambda flow: flow.date)
    invested = sum((f.amount for f in flows if f.amount > 0), ZERO)
    redeemed = -sum((f.amount for f in flows if f.amount < 0), ZERO)
    invested, redeemed, value = money(invested), money(redeemed), money(value)
    gain = value + redeemed - invested
    since = flows[0].date if flows else None
    rate = None
    if since is not None and (on - since).days >= MIN_XIRR_DAYS:
        dated = [(f.date, -float(f.amount)) for f in flows]
        if value > 0:
            dated.append((on, float(value)))
        found = xirr(dated)
        rate = figure(found * 100) if found is not None else None
    return Returns(invested, redeemed, value, gain, pct(gain, invested), rate, since, on)
