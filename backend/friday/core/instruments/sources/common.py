"""Shared pieces for the list parsers: the normalised record and CSV header helpers."""

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime

from friday.core.instruments.classify import Classification


class SourceFormatError(ValueError):
    """A downloaded file doesn't look like the list it should be (e.g. a bot-check page)."""


@dataclass
class Record:
    """One instrument as a source list describes it, before matching to the database."""

    kind: str
    name: str
    market: str
    currency: str
    classification: Classification
    active: bool = True
    exchange: str | None = None
    symbol: str | None = None
    isin: str | None = None
    series: str | None = None
    listed_on: date | None = None
    cik: str | None = None
    amfi_code: str | None = None
    isin_reinvestment: str | None = None
    fund_house: str | None = None
    scheme_type: str | None = None
    fund_category: str | None = None
    plan: str | None = None
    option: str | None = None
    option_kind: str | None = None
    scheme_key: str | None = None
    extra: dict[str, str] = field(default_factory=dict)


def clean(value: str | None) -> str:
    """Trim and collapse runs of whitespace; curly quotes become straight ones."""
    if value is None:
        return ""
    value = value.replace("\u2019", "'").replace("\u2018", "'")
    return " ".join(value.split())


def header_key(name: str) -> str:
    """Compare column names loosely: ``" ISIN NUMBER"`` and ``"ISINNumber"`` → ``isinnumber``."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def read_rows(
    text: str, *, file: str, required: set[str], delimiter: str = ","
) -> list[dict[str, str]]:
    """Parse a delimited file into dicts keyed by :func:`header_key`, checking the columns."""
    text = text.lstrip("\ufeff")
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        header = [header_key(column) for column in next(reader)]
    except StopIteration:
        raise SourceFormatError(f"{file} is empty") from None
    missing = required - set(header)
    if missing:
        first_line = text.splitlines()[0][:80] if text else ""
        raise SourceFormatError(
            f"{file} doesn't look right: missing columns {sorted(missing)}; "
            f"first line was {first_line!r}"
        )
    return [
        {key: clean(value) for key, value in zip(header, row, strict=False)}
        for row in reader
        if any(cell.strip() for cell in row)
    ]


def parse_date(value: str) -> date | None:
    """Dates as the Indian lists write them: ``06-OCT-2008``, ``08-Jan-02``, ``23-Oct-2026``."""
    value = value.strip()
    for pattern in ("%d-%b-%Y", "%d-%b-%y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, pattern).date()  # noqa: DTZ007 (a plain date)
        except ValueError:
            continue
    return None


def optional(value: str) -> str | None:
    """Empty cells and AMFI's ``-`` placeholder become ``None``."""
    return value if value and value != "-" else None
