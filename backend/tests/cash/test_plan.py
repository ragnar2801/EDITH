"""The cash plan's arithmetic, against cases worked by hand (D-058, D-059)."""

from datetime import date
from decimal import Decimal

from friday.core.cash.plan import Target, make_plan, split

D = Decimal
FLEXI, MID, DEBT = 1, 2, 3


def bucket(flexi: str, mid: str, debt: str) -> list[Target]:
    """A 50 / 30 / 20 split with these values held now."""
    return [
        Target(FLEXI, D(50), D(flexi)),
        Target(MID, D(30), D(mid)),
        Target(DEBT, D(20), D(debt)),
    ]


def plan(amount: str, targets: list[Target], shortfall: str = "0", minimum: str = "500"):
    return make_plan(
        D(amount),
        D(shortfall),
        targets,
        minimum=D(minimum),
        stagger_from=D(500_000),
        stagger_months=6,
        today=date(2026, 10, 25),
    )


def test_on_target_new_cash_follows_the_weights() -> None:
    # ₹9L held exactly 50 / 30 / 20; ₹1L more keeps it there.
    result = plan("100000", bucket("450000", "270000", "180000"))

    assert result.split == {FLEXI: D(50_000), MID: D(30_000), DEBT: D(20_000)}
    assert (result.emergency, result.left, result.months) == (0, 0, [])


def test_one_fund_far_below_gets_everything() -> None:
    # ₹10L held 60 / 20 / 20. Value ÷ weight: flexi 12,000, mid 6,667, debt 10,000.
    # Raising mid alone to debt's level takes 0.3 × 10L − 2L = ₹1L: exactly the cash.
    result = plan("100000", bucket("600000", "200000", "200000"))

    assert result.split == {MID: D(100_000)}


def test_cash_beyond_the_lowest_fund_is_shared_at_one_level() -> None:
    # ₹1.5L into 60 / 20 / 20: mid's ₹1L reaches debt's level (10,000), then mid and debt
    # share ₹50,000 by weight (30 : 20) up to 11,000. Flexi stays above it.
    result = plan("150000", bucket("600000", "200000", "200000"))

    assert result.split == {MID: D(130_000), DEBT: D(20_000)}  # 3.3L ÷ 30 = 2.2L ÷ 20


def test_whole_rupees_with_the_largest_remainder_getting_the_spare_rupee() -> None:
    targets = [
        Target(1, D("33.33"), D(0)),
        Target(2, D("33.33"), D(0)),
        Target(3, D("33.34"), D(0)),
    ]

    result = plan("1000.75", targets, minimum="0")

    assert result.split == {1: D(333), 2: D(333), 3: D(334)}  # 333.30 / 333.30 / 333.40
    assert result.left == D("0.75")  # paise stay as cash


def test_a_share_under_the_minimum_goes_to_the_others() -> None:
    targets = [Target(1, D(90), D(0)), Target(2, D(10), D(0))]

    assert split(targets, D(2000), D(500)) == {1: D(2000)}  # 1,800 / 200: 200 is too small
    assert split(targets, D(400), D(500)) == {}  # under the minimum for any fund
    assert plan("400", targets).left == D(400)


def test_emergency_is_topped_up_first() -> None:
    held = bucket("450000", "270000", "180000")

    partly = plan("100000", held, shortfall="50000")
    assert partly.emergency == D(50_000)
    assert partly.split == {FLEXI: D(25_000), MID: D(15_000), DEBT: D(10_000)}

    all_of_it = plan("30000", held, shortfall="50000")
    assert (all_of_it.emergency, all_of_it.split, all_of_it.left) == (D(30_000), {}, 0)


def test_a_large_amount_is_staggered_over_six_months() -> None:
    result = plan("650000", bucket("450000", "270000", "180000"))

    assert result.split == {FLEXI: D(325_000), MID: D(195_000), DEBT: D(130_000)}
    assert [m.start for m in result.months] == [
        date(2026, 10, 1),
        date(2026, 11, 1),
        date(2026, 12, 1),
        date(2027, 1, 1),
        date(2027, 2, 1),
        date(2027, 3, 1),
    ]
    # 3,25,000 ÷ 6 = 54,166.67: five months of 54,166 and the last takes 54,170.
    assert [m.amounts[FLEXI] for m in result.months] == [D(54_166)] * 5 + [D(54_170)]
    assert [m.amounts[MID] for m in result.months] == [D(32_500)] * 6
    assert [m.amounts[DEBT] for m in result.months] == [D(21_666)] * 5 + [D(21_670)]


def test_below_the_threshold_goes_in_at_once() -> None:
    assert plan("499999", bucket("450000", "270000", "180000")).months == []
