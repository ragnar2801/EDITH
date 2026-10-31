"""Nasdaq Trader symbol directory: every US-listed stock and ETF.

``https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt`` (Nasdaq) and
``otherlisted.txt`` (NYSE, NYSE Arca, NYSE American, Cboe, IEX, TXSE...). Pipe-separated,
updated daily, last line ``File Creation Time: ...``. Checked 2026-10-24.
"""

import re

from friday.core.instruments.classify import classify_us
from friday.core.instruments.sources.common import Record, read_rows

NASDAQ_LISTED = "nasdaqlisted.txt"
OTHER_LISTED = "otherlisted.txt"

# Exchange codes used in otherlisted.txt.
EXCHANGES = {
    "N": "NYSE",
    "P": "NYSE_ARCA",
    "A": "NYSE_AMERICAN",
    "Z": "CBOE",
    "V": "IEX",
    "F": "TXSE",
    "M": "NYSE_TEXAS",
}

# Securities Friday doesn't hold: warrants, rights, SPAC units, preferreds and notes.
_NOT_A_HOLDING = re.compile(
    r"\b(warrants?|rights?)\b|[-–]\s*units?\b|\bunits?,? each\b|\bunit\s*$"
    r"|\bpreferred\b|\bnotes? due\b|\bdebentures?\b|\bsenior notes\b",
    re.IGNORECASE,
)
_SUFFIX = re.compile(
    r"\s*(-\s*)?(new )?(common stock|ordinary shares|common shares|capital stock)\s*$",
    re.IGNORECASE,
)


def clean_name(name: str) -> str:
    """``Alphabet Inc. - Class A Common Stock`` → ``Alphabet Inc. - Class A``."""
    return _SUFFIX.sub("", name).rstrip(" -") or name


def _record(symbol: str, name: str, exchange: str, is_etf: bool) -> Record | None:
    if not symbol or "$" in symbol or symbol.startswith("FILE CREATION TIME"):
        return None
    if not is_etf and _NOT_A_HOLDING.search(name):
        return None
    kind = "etf" if is_etf else "stock"
    name = clean_name(name)
    return Record(
        kind=kind,
        name=name,
        market="US",
        currency="USD",
        classification=classify_us(kind, name),
        exchange=exchange,
        symbol=symbol,
    )


def parse_nasdaq_listed(text: str) -> list[Record]:
    """``Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF``"""
    rows = read_rows(
        text,
        file=NASDAQ_LISTED,
        required={"symbol", "securityname", "testissue", "etf"},
        delimiter="|",
    )
    records = (
        _record(row["symbol"].upper(), row["securityname"], "NASDAQ", row["etf"] == "Y")
        for row in rows
        if row.get("testissue") != "Y"
    )
    return [record for record in records if record]


def parse_other_listed(text: str) -> list[Record]:
    """``ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|...``"""
    rows = read_rows(
        text,
        file=OTHER_LISTED,
        required={"actsymbol", "securityname", "exchange", "etf", "testissue"},
        delimiter="|",
    )
    records = (
        _record(
            row["actsymbol"].upper(),
            row["securityname"],
            EXCHANGES.get(row["exchange"], "US_OTHER"),
            row["etf"] == "Y",
        )
        for row in rows
        if row.get("testissue") != "Y"
    )
    return [record for record in records if record]
