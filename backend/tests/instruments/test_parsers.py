"""Parsing the source lists. Fixtures are slices of the real files downloaded 2026-10-24."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from friday.core.instruments.sources import amfi, nasdaq, nse, sec
from friday.core.instruments.sources.common import SourceFormatError, parse_date

FIXTURES = Path(__file__).parents[1] / "fixtures" / "instruments"


def read(file: str) -> str:
    return (FIXTURES / file).read_text(encoding="utf-8")


def by_symbol(records):
    return {record.symbol: record for record in records}


def test_nse_equity_list() -> None:
    records = by_symbol(nse.parse_equity_list(read(nse.EQUITY_LIST)))

    infy = records["INFY"]
    assert (infy.name, infy.kind, infy.exchange, infy.currency) == (
        "Infosys Limited",
        "stock",
        "NSE",
        "INR",
    )
    assert infy.isin == "INE009A01021"
    assert infy.series == "EQ"
    assert infy.listed_on == date(1995, 2, 8)
    assert infy.classification.allocation == {"equity": Decimal(100)}
    assert infy.classification.exposure == "IN"
    assert "M&M" in records


def test_nse_etf_list_classifies_from_the_underlying_column() -> None:
    records = by_symbol(nse.parse_etf_list(read(nse.ETF_LIST)))

    assert records["NIFTYBEES"].kind == "etf"
    assert records["NIFTYBEES"].name == "Nifty 50 ETF (NIFTYBEES)"  # until AMFI names it
    assert records["NIFTYBEES"].listed_on == date(2002, 1, 8)
    assert records["GOLDBEES"].classification.asset_class == "gold"
    assert records["LIQUIDBEES"].classification.asset_class == "debt"
    assert records["MON100"].classification.exposure == "US"
    assert records["HNGSNGBEES"].classification.exposure == "GLOBAL"


def test_nse_symbol_and_name_changes() -> None:
    changes = nse.parse_symbol_changes(read(nse.SYMBOL_CHANGES))
    names = nse.parse_name_changes(read(nse.NAME_CHANGES))

    assert nse.SymbolChange("ZOMATO", "ETERNAL", date(2025, 4, 9)) in changes
    assert nse.resolve_symbol("MCDOWELL-N", changes) == "UNITDSPR"
    assert nse.resolve_symbol("INFY", changes) == "INFY"
    assert nse.NameChange("ETERNAL", "Zomato Limited", "ETERNAL LIMITED", date(2025, 4, 9)) in names


def test_symbol_change_chains_follow_to_the_latest_symbol() -> None:
    changes = [
        nse.SymbolChange("A", "B", date(2010, 1, 1)),
        nse.SymbolChange("B", "C", date(2015, 1, 1)),
        nse.SymbolChange("X", "Y", date(2010, 1, 1)),
        nse.SymbolChange("Y", "X", date(2012, 1, 1)),  # renamed back: must not loop forever
    ]
    assert nse.resolve_symbol("A", changes) == "C"
    assert nse.resolve_symbol("X", changes) in {"X", "Y"}


def test_amfi_nav_file() -> None:
    records = {record.amfi_code: record for record in amfi.parse_nav_all(read(amfi.NAV_ALL))}

    direct = records["122639"]
    assert direct.name == "Parag Parikh Flexi Cap Fund"
    assert direct.kind == "mutual_fund"
    assert direct.fund_house == "PPFAS Mutual Fund"
    assert direct.scheme_type == "Open Ended"
    assert direct.fund_category == "Equity Scheme - Flexi Cap Fund"
    assert (direct.plan, direct.option, direct.option_kind) == ("direct", "Growth", "growth")
    assert direct.isin == "INF879O01027"
    assert direct.classification.asset_class == "equity"

    idcw = records["153964"]
    assert idcw.isin is None  # "-" in the file
    assert idcw.isin_reinvestment == "INF879O01308"
    assert idcw.option_kind == "idcw"
    assert idcw.scheme_key == direct.scheme_key  # variants of one scheme

    assert records["140084"].kind == "etf"
    assert records["119091"].classification.asset_class == "debt"  # liquid fund
    nasdaq_fof = records["145552"].classification
    assert (nasdaq_fof.asset_class, nasdaq_fof.exposure) == ("equity", "US")
    assert records["147825"].classification.asset_class == "unclassified"  # retirement fund


def test_amfi_schemes_without_a_recent_nav_are_inactive() -> None:
    records = {record.amfi_code: record for record in amfi.parse_nav_all(read(amfi.NAV_ALL))}

    assert records["122639"].active
    assert not records["142916"].active  # matured FMP: last NAV in May 2021


def test_amfi_older_layout_without_plan_and_option_columns() -> None:
    text = (
        "Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;"
        "Net Asset Value;Date\n\nOpen Ended Schemes(Equity Scheme - Large Cap Fund)\n\n"
        "Axis Mutual Fund\n\n"
        "120465;INF846K01DP8;-;Axis Large Cap Fund - Direct Plan - Growth;60.12;23-Oct-2026\n"
    )
    [record] = amfi.parse_nav_all(text)

    assert (record.plan, record.option_kind) == ("direct", "growth")


def test_amfi_scheme_master_names_plan_and_option() -> None:
    labels = {
        label.amfi_code: label for label in amfi.parse_scheme_master(read(amfi.SCHEME_MASTER))
    }

    def label(code: str) -> tuple:
        return labels[code].plan, labels[code].option_kind, labels[code].option

    assert label("127042") == ("direct", "growth", "Growth")  # "-Direct Plan-Growth Option"
    assert label("127044") == ("direct", "idcw", "IDCW")  # "-Direct - IDCW Payout/Reinvestment"
    assert label("145551") == ("regular", "growth", "Growth")
    assert label("100868") == ("regular", "growth", "Growth")  # "- Growth Plan": not direct
    assert label("149313") == ("regular", "other", "Unclaimed")
    # One variant per plan and no option in the name: a growth-only index fund.
    assert label("154348") == ("direct", "growth", "Growth")
    assert label("154349") == ("regular", "growth", "Growth")


def test_amfi_scheme_master_reads_only_what_follows_the_scheme_name() -> None:
    text = (
        "AMC,Code,Scheme Name,Scheme Type,Scheme Category,Scheme NAV Name\n"
        "X AMC,1,X Growth Fund,Open Ended,Equity,X Growth Fund - Direct Plan - IDCW\n"
        "X AMC,2,X Growth Fund,Open Ended,Equity,X Growth Fund - Direct Plan - Growth\n"
        "Y AMC,3,Y ELSS,Close Ended,ELSS,Y ELSS - Cumulative Option\n"
        "Y AMC,4,Y ELSS,Close Ended,ELSS,Y ELSS - Direct Plan Cumulative Option\n"
    )
    labels = {label.amfi_code: label for label in amfi.parse_scheme_master(text)}

    assert labels["1"].option_kind == "idcw"  # "Growth Fund" is the name, not the option
    assert labels["2"].option_kind == "growth"
    assert (labels["3"].plan, labels["3"].option_kind) == ("regular", "growth")
    assert (labels["4"].plan, labels["4"].option_kind) == ("direct", "growth")


def test_amfi_scheme_master_fills_only_what_navall_left_blank() -> None:
    records = {record.amfi_code: record for record in amfi.parse_nav_all(read(amfi.NAV_ALL))}
    assert (records["127042"].plan, records["127042"].option_kind) == (None, None)
    labels = amfi.parse_scheme_master(read(amfi.SCHEME_MASTER))
    conflicting = amfi.SchemeLabel("122639", "regular", "idcw", "IDCW")

    filled = amfi.fill_plan_and_option(list(records.values()), [*labels, conflicting])

    assert (records["127042"].plan, records["127042"].option) == ("direct", "Growth")
    assert (records["154348"].plan, records["154348"].option) == ("direct", "Growth")
    assert (records["145552"].plan, records["145552"].option) == ("direct", "Growth")
    assert (records["122639"].plan, records["122639"].option) == ("direct", "Growth")  # NAVAll wins
    assert records["140084"].plan == "direct" and records["140084"].option is None  # an ETF
    assert filled == 8  # Midcap x2, Capital Markets x2, Nasdaq FoF x2, Fixed Horizon x2


def test_nasdaq_lists_keep_stocks_and_etfs_only() -> None:
    nasdaq_listed = by_symbol(nasdaq.parse_nasdaq_listed(read(nasdaq.NASDAQ_LISTED)))
    other_listed = by_symbol(nasdaq.parse_other_listed(read(nasdaq.OTHER_LISTED)))

    assert set(nasdaq_listed) == {"AAPL", "GOOGL", "QQQ"}  # no warrant, no test issue
    assert nasdaq_listed["GOOGL"].name == "Alphabet Inc. - Class A"
    assert nasdaq_listed["QQQ"].kind == "etf"
    assert nasdaq_listed["QQQ"].exchange == "NASDAQ"
    assert nasdaq_listed["AAPL"].currency == "USD"

    assert "ABR$D" not in other_listed  # preferred share
    assert "ZZZTX" not in other_listed  # test issue
    assert other_listed["ET"].name == "Energy Transfer LP Common Units"  # LP units are kept
    assert other_listed["BRK.B"].name == "Berkshire Hathaway Inc."
    assert other_listed["SPY"].exchange == "NYSE_ARCA"
    assert other_listed["ET"].exchange == "TXSE"
    assert other_listed["GLD"].classification.asset_class == "gold"
    assert other_listed["INDA"].classification.exposure == "IN"
    assert other_listed["INFY"].classification.exposure == "GLOBAL"  # ADR


def test_sec_tickers_map_to_padded_ciks() -> None:
    tickers = sec.parse_company_tickers(read(sec.COMPANY_TICKERS))

    assert tickers["AAPL"] == "0000320193"
    assert tickers["BRK.B"] == "0001067983"  # SEC writes BRK-B


@pytest.mark.parametrize(
    ("parse", "file"),
    [
        (nse.parse_equity_list, nse.EQUITY_LIST),
        (nasdaq.parse_nasdaq_listed, nasdaq.NASDAQ_LISTED),
        (amfi.parse_nav_all, amfi.NAV_ALL),
        (amfi.parse_scheme_master, amfi.SCHEME_MASTER),
    ],
)
def test_a_bot_check_page_is_a_format_error(parse, file) -> None:
    page = '<html>\n<head>\n<META NAME="robots" CONTENT="noindex,nofollow">\n'
    with pytest.raises(SourceFormatError, match="doesn't look right"):
        parse(page)


def test_sec_garbage_is_a_format_error() -> None:
    with pytest.raises(SourceFormatError):
        sec.parse_company_tickers("<html>")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("06-OCT-2008", date(2008, 10, 6)),
        ("08-Jan-02", date(2002, 1, 8)),
        ("23-Oct-2026", date(2026, 10, 23)),
        ("", None),
        ("N.A.", None),
    ],
)
def test_dates(text: str, expected: date | None) -> None:
    assert parse_date(text) == expected
