"""SIP instalment dates, worked by hand (D-053)."""

from datetime import date

from friday.core.holdings.service import allotted_units, due_dates, instalment_dates

D = date


def test_first_nav_on_or_after_the_sip_day() -> None:
    navs = [D(2026, 1, 5), D(2026, 1, 6), D(2026, 2, 6), D(2026, 3, 5), D(2026, 4, 6)]

    assert instalment_dates(navs, D(2026, 1, 1), 5, None) == [
        (D(2026, 1, 5), D(2026, 1, 5)),
        (D(2026, 2, 5), D(2026, 2, 6)),  # 5 Feb had no NAV (a holiday)
        (D(2026, 3, 5), D(2026, 3, 5)),
        (D(2026, 4, 5), D(2026, 4, 6)),  # a Sunday
    ]


def test_end_date_stops_the_sip() -> None:
    navs = [D(2026, 1, 5), D(2026, 2, 5), D(2026, 3, 5)]

    assert instalment_dates(navs, D(2026, 1, 1), 5, D(2026, 2, 28)) == [
        (D(2026, 1, 5), D(2026, 1, 5)),
        (D(2026, 2, 5), D(2026, 2, 5)),
    ]


def test_start_after_the_day_begins_next_month_and_crosses_the_year() -> None:
    navs = [D(2025, 12, 5), D(2026, 1, 5), D(2026, 2, 5)]

    assert instalment_dates(navs, D(2025, 11, 20), 5, None) == [
        (D(2025, 12, 5), D(2025, 12, 5)),
        (D(2026, 1, 5), D(2026, 1, 5)),
        (D(2026, 2, 5), D(2026, 2, 5)),
    ]


def test_a_month_without_nav_has_no_instalment() -> None:
    # Missing NAV data for February: its next NAV is already March's.
    navs = [D(2026, 1, 5), D(2026, 3, 10)]

    assert instalment_dates(navs, D(2026, 1, 1), 5, None) == [
        (D(2026, 1, 5), D(2026, 1, 5)),
        (D(2026, 3, 5), D(2026, 3, 10)),
    ]


def test_months_before_the_first_nav_are_left_out() -> None:
    navs = [D(2026, 3, 2), D(2026, 3, 5)]

    assert instalment_dates(navs, D(2026, 1, 1), 5, None) == [(D(2026, 3, 5), D(2026, 3, 5))]


def test_a_due_date_after_the_last_nav_waits() -> None:
    navs = [D(2026, 1, 5), D(2026, 2, 3)]

    assert instalment_dates(navs, D(2026, 1, 1), 5, None) == [(D(2026, 1, 5), D(2026, 1, 5))]
    assert instalment_dates([], D(2026, 1, 1), 5, None) == []


def test_due_dates() -> None:
    assert list(due_dates(D(2026, 1, 28), 28, None, D(2026, 3, 27))) == [
        D(2026, 1, 28),
        D(2026, 2, 28),
    ]


def test_units_are_allotted_to_three_places() -> None:
    from decimal import Decimal

    assert allotted_units(Decimal("5000"), Decimal("83.3333")) == Decimal("60.000")
    assert allotted_units(Decimal("5000"), Decimal("75.25")) == Decimal("66.445")
    assert allotted_units(Decimal("100000"), Decimal("81")) == Decimal("1234.568")
