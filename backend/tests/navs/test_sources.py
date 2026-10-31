"""NAV parsers, on slices of the real mfapi.in and AMFI responses from 2026-10-25."""

from datetime import date
from decimal import Decimal

import pytest

from friday.core.instruments.sources.common import SourceFormatError
from friday.core.navs.sources import parse_amfi_latest, parse_mfapi, parse_nav

from .conftest import NIFTY, PARAG, fixture_text


def test_mfapi_history_comes_back_oldest_first_and_exact() -> None:
    points = parse_mfapi(fixture_text(f"mfapi_{PARAG}.json"), PARAG)

    assert len(points) == 13
    assert points[0] == (date(2013, 5, 28), Decimal("9.9992"))
    assert points[-1] == (date(2026, 10, 23), Decimal("88.9695"))
    assert [day for day, _ in points] == sorted(day for day, _ in points)
    assert str(points[-1][1]) == "88.9695"  # trailing zeros dropped, value unchanged


def test_mfapi_answer_for_another_scheme_is_rejected() -> None:
    with pytest.raises(SourceFormatError, match="answered for scheme 122639"):
        parse_mfapi(fixture_text(f"mfapi_{PARAG}.json"), NIFTY)


@pytest.mark.parametrize(
    "text",
    ["<html>Bad gateway</html>", '{"meta": {}, "status": "FAIL"}', "[]"],
)
def test_mfapi_errors_are_format_errors(text: str) -> None:
    with pytest.raises(SourceFormatError):
        parse_mfapi(text, PARAG)


def test_mfapi_skips_blank_and_zero_navs_and_duplicate_dates() -> None:
    text = (
        '{"meta":{"scheme_code":122639},"data":['
        '{"date":"23-10-2026","nav":"88.96950"},{"date":"23-10-2026","nav":"1.0"},'
        '{"date":"22-10-2026","nav":"0.00000"},{"date":"21-10-2026","nav":"N.A."},'
        '{"date":"bad","nav":"89.1"},{"date":"20-10-2026","nav":"90.1"}]}'
    )
    assert parse_mfapi(text, PARAG) == [
        (date(2026, 10, 20), Decimal("90.1")),
        (date(2026, 10, 23), Decimal("88.9695")),  # the first (newest) entry for a date wins
    ]


def test_amfi_latest_navs_keep_all_published_places() -> None:
    latest = parse_amfi_latest(fixture_text("NAVAll.txt"))

    assert latest[PARAG] == (date(2026, 10, 23), Decimal("88.9695"))
    assert latest[NIFTY] == (date(2026, 10, 23), Decimal("159.177"))
    assert str(latest["108844"][1]) == "14.86269632"  # Bandhan publishes 8 places
    assert "148304" not in latest  # a 0.0000 NAV (segregated portfolio) is no NAV


def test_amfi_file_that_is_not_navall_is_rejected() -> None:
    with pytest.raises(SourceFormatError):
        parse_amfi_latest("<html>Access denied</html>")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12.3450", Decimal("12.345")),
        ("1,234.5", Decimal("1234.5")),
        ("1000.0000", Decimal("1000")),
        ("12.123456789", Decimal("12.12345679")),
        ("", None),
        ("N.A.", None),
        ("0", None),
        ("-1", None),
    ],
)
def test_parse_nav(text: str, expected: Decimal | None) -> None:
    assert parse_nav(text) == expected
