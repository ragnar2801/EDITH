"""NSE archive files: equity list, ETF list, symbol changes and name changes.

Files live at ``https://nsearchives.nseindia.com/content/equities/``. Checked 2026-10-24.
"""

from dataclasses import dataclass
from datetime import date

from friday.core.instruments.classify import classify_nse_etf, classify_nse_stock
from friday.core.instruments.sources.common import (
    Record,
    optional,
    parse_date,
    read_rows,
)

EQUITY_LIST = "EQUITY_L.csv"
ETF_LIST = "eq_etfseclist.csv"
SYMBOL_CHANGES = "symbolchange.csv"
NAME_CHANGES = "namechange.csv"


@dataclass(frozen=True)
class SymbolChange:
    old: str
    new: str
    changed_on: date | None


@dataclass(frozen=True)
class NameChange:
    symbol: str
    old_name: str
    new_name: str
    changed_on: date | None


def parse_equity_list(text: str) -> list[Record]:
    """``SYMBOL,NAME OF COMPANY, SERIES, DATE OF LISTING, ..., ISIN NUMBER, FACE VALUE``"""
    rows = read_rows(
        text, file=EQUITY_LIST, required={"symbol", "nameofcompany", "series", "isinnumber"}
    )
    return [
        Record(
            kind="stock",
            name=row["nameofcompany"],
            market="IN",
            currency="INR",
            classification=classify_nse_stock(),
            exchange="NSE",
            symbol=row["symbol"].upper(),
            isin=optional(row["isinnumber"]),
            series=optional(row["series"]),
            listed_on=parse_date(row.get("dateoflisting", "")),
        )
        for row in rows
        if row["symbol"]
    ]


def parse_etf_list(text: str) -> list[Record]:
    """``Symbol,Underlying Asset,SecurityName,DateofListing,...,ISINNumber,...,ETF Underlying``

    NSE's security names are abbreviations (``NIPINDETFNIFTYBEES``), so the name here is a
    readable stand-in; the AMFI import replaces it with the scheme's real name.
    """
    rows = read_rows(
        text, file=ETF_LIST, required={"symbol", "underlyingasset", "isinnumber", "etfunderlying"}
    )
    records = []
    for row in rows:
        symbol = row["symbol"].upper()
        if not symbol:
            continue
        underlying = row["underlyingasset"]
        records.append(
            Record(
                kind="etf",
                name=f"{underlying} ETF ({symbol})" if underlying else symbol,
                market="IN",
                currency="INR",
                classification=classify_nse_etf(
                    row["etfunderlying"], f"{underlying} {row.get('underlyingkey', '')}", symbol
                ),
                exchange="NSE",
                symbol=symbol,
                isin=optional(row["isinnumber"]),
                listed_on=parse_date(row.get("dateoflisting", "")),
            )
        )
    return records


def parse_symbol_changes(text: str) -> list[SymbolChange]:
    """``NAME OF THE COMPANY,OLD SYMBOL,NEW SYMBOL,EFFECTIVE DATE``"""
    rows = read_rows(text, file=SYMBOL_CHANGES, required={"oldsymbol", "newsymbol"})
    return [
        SymbolChange(
            old=row["oldsymbol"].upper(),
            new=row["newsymbol"].upper(),
            changed_on=parse_date(row.get("effectivedate", "")),
        )
        for row in rows
        if row["oldsymbol"] and row["newsymbol"] and row["oldsymbol"] != row["newsymbol"]
    ]


def parse_name_changes(text: str) -> list[NameChange]:
    """``SYMBOL,OLD NAME OF THE COMPANY,NEW NAME OF THE COMPANY,EFFECTIVE DATE``"""
    rows = read_rows(
        text,
        file=NAME_CHANGES,
        required={"symbol", "oldnameofthecompany", "newnameofthecompany"},
    )
    return [
        NameChange(
            symbol=row["symbol"].upper(),
            old_name=row["oldnameofthecompany"],
            new_name=row["newnameofthecompany"],
            changed_on=parse_date(row.get("effectivedate", "")),
        )
        for row in rows
        if row["symbol"] and row["oldnameofthecompany"]
    ]


def resolve_symbol(symbol: str, changes: list[SymbolChange]) -> str:
    """Follow renames forward to today's symbol: ``ZOMATO`` → ``ETERNAL``."""
    forward: dict[str, SymbolChange] = {}
    for change in sorted(changes, key=lambda c: c.changed_on or date.min):
        forward[change.old] = change  # the latest rename away from a symbol wins
    seen = {symbol}
    while symbol in forward:
        symbol = forward[symbol].new
        if symbol in seen:  # a symbol renamed back and forth: stop at the loop
            break
        seen.add(symbol)
    return symbol
