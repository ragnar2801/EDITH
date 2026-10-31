"""The cash plan's arithmetic. Pure functions, no I/O.

New cash first tops up the emergency money, then goes to the funds of my target split that
are furthest below it, without selling anything. "Furthest below" is measured as value ÷
weight: the plan raises the lowest funds to a common level, so after it every fund that got
money is equally far from its target, and none is pushed above it.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

ZERO = Decimal(0)
RUPEE = Decimal(1)
CENT = Decimal("0.01")
HUNDRED = Decimal(100)


@dataclass(frozen=True)
class Target:
    key: int
    """The fund's instrument id."""
    weight: Decimal
    """Its target share, in percent."""
    value: Decimal
    """What I hold of it now."""


@dataclass(frozen=True)
class Month:
    start: date
    """First day of the month the transfer is for."""
    amounts: dict[int, Decimal]


@dataclass(frozen=True)
class Plan:
    emergency: Decimal
    """Topping up the emergency money, before anything else."""
    split: dict[int, Decimal]
    """Whole rupees per fund, in the bucket's order; only funds that get money."""
    left: Decimal
    """Not invested: paise, or an amount too small for the minimum per fund."""
    months: list[Month]
    """The staggered transfers, or empty when the split goes in at once."""


def _floor(value: Decimal) -> Decimal:
    return value.quantize(RUPEE, ROUND_FLOOR)


def percent(part: Decimal, whole: Decimal) -> Decimal | None:
    if whole <= 0:
        return None
    return (part / whole * HUNDRED).quantize(CENT, ROUND_HALF_UP)


def fill(targets: Sequence[Target], budget: Decimal) -> dict[int, Decimal]:
    """Exact amounts that raise the lowest funds (by value ÷ weight) to one level, using
    the whole budget. A fund already above that level gets nothing."""
    pool = sorted((t for t in targets if t.weight > 0), key=lambda t: t.value / t.weight)
    weights = values = ZERO
    for i, target in enumerate(pool):
        weights += target.weight
        values += target.value
        level = (budget + values) / weights
        if i + 1 == len(pool) or level <= pool[i + 1].value / pool[i + 1].weight:
            return {t.key: t.weight * level - t.value for t in pool[: i + 1]}
    return {}


def whole_rupees(amounts: dict[int, Decimal], total: Decimal) -> dict[int, Decimal]:
    """Round down to whole rupees, then hand the rupees that frees up (out of ``total``
    rounded down) to the largest remainders, so nothing beyond paise is left over."""
    floors = {key: _floor(amount) for key, amount in amounts.items()}
    spare = int(_floor(total) - sum(floors.values(), ZERO))
    keys = list(amounts)  # ties go to the fund listed first
    by_remainder = sorted(keys, key=lambda key: (-(amounts[key] - floors[key]), keys.index(key)))
    for key in by_remainder[: max(spare, 0)]:
        floors[key] += RUPEE
    return floors


def split(targets: Sequence[Target], budget: Decimal, minimum: Decimal) -> dict[int, Decimal]:
    """Whole rupees per fund. A fund whose share is under ``minimum`` is left out and the
    others are planned again, smallest share first, until every share meets it."""
    pool = [t for t in targets if t.weight > 0]
    while pool and _floor(budget) >= max(minimum, RUPEE):
        amounts = whole_rupees(fill(pool, budget), budget)
        small = [key for key, amount in amounts.items() if amount < minimum]
        if not small:
            order = [t.key for t in targets]
            return {key: amounts[key] for key in order if amounts.get(key, ZERO) > 0}
        smallest = min(small, key=lambda key: amounts[key])
        pool = [t for t in pool if t.key != smallest]
    return {}


def _add_months(day: date, months: int) -> date:
    index = day.year * 12 + day.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


def stagger(amounts: dict[int, Decimal], months: int, first: date) -> list[Month]:
    """Each fund's share in ``months`` equal monthly transfers of whole rupees; the last
    month takes what rounding leaves."""
    monthly = {key: _floor(amount / months) for key, amount in amounts.items()}
    plan = []
    for i in range(months):
        last = i == months - 1
        plan.append(
            Month(
                start=_add_months(first.replace(day=1), i),
                amounts={
                    key: amount - monthly[key] * (months - 1) if last else monthly[key]
                    for key, amount in amounts.items()
                },
            )
        )
    return plan


def make_plan(
    amount: Decimal,
    emergency_shortfall: Decimal,
    targets: Sequence[Target],
    *,
    minimum: Decimal,
    stagger_from: Decimal | None,
    stagger_months: int,
    today: date,
) -> Plan:
    emergency = min(amount, max(emergency_shortfall, ZERO))
    budget = amount - emergency
    amounts = split(targets, budget, minimum)
    invested = sum(amounts.values(), ZERO)
    staggered = stagger_from is not None and invested > 0 and budget >= stagger_from
    return Plan(
        emergency=emergency,
        split=amounts,
        left=budget - invested,
        months=stagger(amounts, stagger_months, today) if staggered else [],
    )
