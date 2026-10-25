"""Returns of real money (D-070): pure arithmetic over dated cash flows, no database.

A flow is money I put in (``amount > 0``, a buy) or took out (``amount < 0``, a sale's
proceeds). Amounts are exact ``Decimal``s; XIRR is a float rounded to 2 places like the
backtest ratios (D-048).
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


def replay(series: list[tuple[date, Decimal]], flows: list[Flow], on: date) -> Returns | None:
    """The same money on the same dates in one other fund (the Nifty 50 index fund, D-070),
    each flow at that fund's NAV on or before its date. A sale takes out the same rupees,
    capped at what the other fund holds by then. ``None`` when the fund has no NAV on or
    before the first flow."""
    points = sorted(series)
    units, taken, j, nav = ZERO, [], 0, None

    def nav_on(day: date) -> Decimal | None:
        nonlocal j, nav
        while j < len(points) and points[j][0] <= day:
            nav = points[j][1]
            j += 1
        return nav

    for flow in sorted(flows, key=lambda f: f.date):
        price = nav_on(flow.date)
        if price is None:
            return None
        if flow.amount > 0:
            units += flow.amount / price
            taken.append(flow)
        elif flow.amount < 0:
            if -flow.amount >= units * price:
                out, units = money(units * price), ZERO  # everything it holds
            else:
                out = -flow.amount
                units -= out / price
            if out:
                taken.append(Flow(flow.date, -out))
    price = nav_on(on)
    value = money(units * price) if price is not None else ZERO
    return returns(taken, value, on)
