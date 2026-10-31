"""Value over time, the day's move and the gain over a range, worked by hand."""

from datetime import date, timedelta
from decimal import Decimal

from friday.core.portfolio.history import Move, Point, change, combine, daily, index, thin

D1, D2, D3 = date(2025, 1, 1), date(2025, 2, 1), date(2025, 3, 1)
SERIES = [(D1, Decimal(100)), (D2, Decimal(110)), (D3, Decimal(120))]

# 100 units bought at 100 on D1; 50 of them (cost 5,000) sold at 120 on D3 for 6,000.
MOVES = [
    Move(D1, Decimal(100), Decimal(10000), Decimal(10000), Decimal(100)),
    Move(D3, Decimal(-50), Decimal(-5000), Decimal(-6000), Decimal(120)),
]


def test_value_cost_and_money_on_each_date() -> None:
    points = daily(MOVES, SERIES, [D1, D2, D3])

    assert [(p.value, p.cost, p.flow) for p in points] == [
        (Decimal("10000.00"), Decimal("10000.00"), Decimal(10000)),
        (Decimal("11000.00"), Decimal("10000.00"), Decimal(0)),
        (Decimal("6000.00"), Decimal("5000.00"), Decimal(-6000)),
    ]


def test_before_its_first_stored_nav_a_fund_is_priced_at_its_trade() -> None:
    day0 = date(2024, 12, 30)
    bought = Move(day0, Decimal(10), Decimal(950), Decimal(950), Decimal(95))

    points = daily([bought], SERIES, [day0, D1])

    assert [p.value for p in points] == [Decimal("950.00"), Decimal("1000.00")]


def test_gain_and_time_weighted_return_from_the_first_purchase() -> None:
    result = change(daily(MOVES, SERIES, [D1, D2, D3]))

    # 6,000 held + 6,000 taken out − 10,000 put in. The NAV rose 100 → 120: 20%, whatever
    # the timing of the sale (11,000 → 12,000 before it on D3 is 1.0909…; × 1.1 = 1.2).
    assert (result.start, result.end, result.gain, result.return_pct) == (
        D1,
        D3,
        Decimal("2000.00"),
        Decimal("20.00"),
    )


def test_gain_over_a_range_starts_from_the_value_on_its_first_date() -> None:
    points = daily(MOVES, SERIES, [D1, D2, D3])

    result = change(points, date(2025, 1, 15))  # no NAV that day: from D1's value

    assert (result.start, result.gain) == (D1, Decimal("2000.00"))
    result = change(points, D2)
    # 6,000 − 11,000 + 6,000 taken out; 120 / 110 − 1.
    assert (result.start, result.gain, result.return_pct) == (
        D2,
        Decimal("1000.00"),
        Decimal("9.09"),
    )


def test_no_change_without_two_dates() -> None:
    points = daily(MOVES, SERIES, [D1, D2, D3])

    assert change([]) is None
    assert change(points, D3) is None
    assert change(points[:1], D1) is None


def test_a_day_with_nothing_held_before_it_has_a_gain_but_no_return() -> None:
    points = daily(MOVES[:1], SERIES, [date(2024, 12, 1), D1])

    result = change(points, date(2024, 12, 1))

    assert (result.gain, result.return_pct) == (Decimal("0.00"), None)


def test_funds_add_up_point_by_point() -> None:
    other = [Move(D2, Decimal(10), Decimal(1100), Decimal(1100), Decimal(110))]
    a = daily(MOVES, SERIES, [D1, D2, D3])
    b = daily(other, SERIES, [D1, D2, D3])

    total = combine([a, b])

    assert [p.value for p in total] == [Decimal("10000"), Decimal("12100"), Decimal("7200")]
    assert [p.flow for p in total] == [Decimal(10000), Decimal(1100), Decimal(-6000)]
    assert combine([]) == []


def _weekdays(start: date, count: int) -> list[Point]:
    days, day = [], start
    while len(days) < count:
        if day.weekday() < 5:
            days.append(Point(day, Decimal(len(days)), Decimal(0), Decimal(0)))
        day += timedelta(days=1)
    return days


def test_long_histories_keep_the_last_date_of_each_week_then_month() -> None:
    points = _weekdays(date(2023, 1, 3), 780)  # a Tuesday; about three years

    weekly = thin(points)
    monthly = thin(points, limit=100)

    assert len(points) > 500 and len(weekly) <= 160
    assert weekly[0] == points[0] and weekly[-1] == points[-1]
    assert all(p.date.weekday() == 4 for p in weekly[1:-1])  # Fridays
    assert monthly[0] == points[0] and monthly[-1] == points[-1]
    months = [(p.date.year, p.date.month) for p in monthly[1:]]
    assert len(months) == len(set(months)) and len(monthly) <= 40
    short = points[:50]
    assert thin(short) == short


def test_growth_of_100_leaves_out_the_money_put_in_and_taken_out() -> None:
    bought = Move(D2, Decimal(10), Decimal(1100), Decimal(1100), Decimal(110))

    found = index(daily([*MOVES, bought], SERIES, [D1, D2, D3]))

    # The NAV went 100 → 110 → 120, whatever was bought or sold on the way.
    assert found == [(D1, Decimal(100)), (D2, Decimal(110)), (D3, Decimal(120))]


def test_growth_starts_on_the_first_date_with_money_held() -> None:
    later = [Move(D2, Decimal(10), Decimal(1100), Decimal(1100), Decimal(110))]

    assert [day for day, _ in index(daily(later, SERIES, [D1, D2, D3]))] == [D2, D3]
