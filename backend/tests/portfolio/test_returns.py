"""Returns of real money, worked by hand."""

from datetime import date
from decimal import Decimal

from friday.core.portfolio.history import replay
from friday.core.portfolio.returns import Flow, returns


def d(text: str) -> Decimal:
    return Decimal(text)


def npv(rate_pct: Decimal, flows: list[tuple[date, float]]) -> float:
    rate, start = float(rate_pct) / 100, flows[0][0]
    return sum(a / (1 + rate) ** ((day - start).days / 365) for day, a in flows)


def test_one_lump_sum_over_two_years() -> None:
    # ₹10,000 grows to ₹12,100 in 730 days: 21% in all, 1.21 ** (365 / 730) - 1 = 10% a year.
    result = returns([Flow(date(2024, 1, 1), d("10000"))], d("12100"), date(2025, 12, 31))

    assert (result.invested, result.redeemed, result.gain) == (d("10000"), 0, d("2100"))
    assert result.return_pct == d("21.00")
    assert result.xirr_pct == d("10.00")
    assert result.since == date(2024, 1, 1)


def test_no_xirr_under_a_year() -> None:
    result = returns([Flow(date(2026, 1, 1), d("10000"))], d("10200"), date(2026, 2, 1))

    assert result.return_pct == d("2.00")
    assert result.xirr_pct is None  # 2% in a month would read as about 27% a year


def test_sips_with_a_partial_sell() -> None:
    flows = [
        Flow(date(2024, 1, 1), d("1000")),
        Flow(date(2024, 7, 1), d("1000")),
        Flow(date(2025, 1, 1), d("-600")),
    ]

    result = returns(flows, d("1700"), date(2026, 1, 1))

    # 1,700 held + 600 taken out − 2,000 put in.
    assert (result.invested, result.redeemed, result.gain) == (d("2000"), d("600"), d("300"))
    assert result.return_pct == d("15.00")
    dated = [(f.date, -float(f.amount)) for f in flows] + [(date(2026, 1, 1), 1700.0)]
    assert abs(npv(result.xirr_pct, dated)) < 1  # within a rupee: the 2-place rounding
    assert result.xirr_pct == d("9.86")  # -1000 - 954.2 + 546.0 + 1408.3 ≈ 0 at 9.86%


def test_everything_sold_has_no_value_left() -> None:
    flows = [Flow(date(2024, 1, 1), d("1000")), Flow(date(2025, 1, 1), d("-1100"))]

    result = returns(flows, d("0"), date(2025, 6, 1))

    assert (result.value, result.gain, result.return_pct) == (0, d("100"), d("10.00"))
    assert result.xirr_pct == d("9.97")  # 10% over 366 days (2024 is a leap year)


def test_replay_in_the_index_fund() -> None:
    series = [(date(2024, 1, 1), d("10")), (date(2025, 1, 1), d("20"))]
    flows = [Flow(date(2024, 1, 1), d("1000")), Flow(date(2025, 1, 2), d("-500"))]

    result = replay(series, flows, date(2025, 6, 1))

    # 100 units at 10; ₹500 out at 20 is 25 units; 75 left at 20.
    assert result is not None
    assert (result.invested, result.redeemed, result.value) == (d("1000"), d("500"), d("1500"))


def test_replay_caps_a_sale_at_what_the_index_fund_holds() -> None:
    series = [(date(2024, 1, 1), d("10")), (date(2025, 1, 1), d("20"))]
    flows = [Flow(date(2024, 1, 1), d("1000")), Flow(date(2025, 1, 1), d("-5000"))]

    result = replay(series, flows, date(2025, 6, 1))

    assert result is not None
    assert (result.redeemed, result.value) == (d("2000"), 0)


def test_replay_needs_a_nav_before_the_first_flow() -> None:
    series = [(date(2024, 6, 1), d("10"))]

    assert replay(series, [Flow(date(2024, 1, 1), d("1000"))], date(2025, 1, 1)) is None
