"""AMFI ``NAVAll.txt`` (D-039): every mutual fund scheme code with its latest NAV.

``https://portal.amfiindia.com/spages/NAVAll.txt``. Checked 2026-10-24. The file is
semicolon-separated with header lines between blocks::

    Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;
        Net Asset Value;Date                                (one line in the file)

    Open Ended Schemes(Equity Scheme - Flexi Cap Fund)      <- category
    PPFAS Mutual Fund                                       <- fund house
    122639;INF879O01027;-;Parag Parikh Flexi Cap Fund;Direct Plan;Growth;92.4567;23-Oct-2026

Older copies have no Plan and Option columns; both layouts are read.
"""

import re
from datetime import date, timedelta

from friday.core.instruments.classify import classify_fund
from friday.core.instruments.sources.common import (
    Record,
    SourceFormatError,
    clean,
    header_key,
    optional,
    parse_date,
)

NAV_ALL = "NAVAll.txt"

STALE_AFTER = timedelta(days=30)
"""A scheme whose last NAV is this much older than the file's newest NAV is closed (D-041)."""

_CATEGORY = re.compile(r"^(?P<type>.+?) Schemes?\s*\((?P<category>.*)\)$")
_REQUIRED = {"schemecode", "schemename", "date"}


def _plan(plan: str, name: str) -> str | None:
    text = plan or name
    if re.search(r"\bdirect\b", text, re.IGNORECASE):
        return "direct"
    if re.search(r"\bregular\b", text, re.IGNORECASE):
        return "regular"
    return None


def _option_kind(option: str, name: str) -> str | None:
    text = option or name
    if re.search(r"growth", text, re.IGNORECASE):
        return "growth"
    if re.search(r"idcw|dividend|income distribution", text, re.IGNORECASE):
        return "idcw"
    if re.search(r"bonus", text, re.IGNORECASE):
        return "bonus"
    return "other" if option else None


def scheme_key(fund_house: str, name: str, category: str) -> str:
    """Variants (plans and options) of one scheme share this key (D-042)."""
    return "|".join(clean(part).lower() for part in (fund_house, name, category))


def parse_nav_all(text: str) -> list[Record]:
    lines = text.lstrip("\ufeff").splitlines()
    header = next((line for line in lines if line.strip()), "")
    columns = [header_key(column) for column in header.split(";")]
    if not set(columns) >= _REQUIRED:
        raise SourceFormatError(f"{NAV_ALL} doesn't look right: first line was {header[:80]!r}")
    index = {column: position for position, column in enumerate(columns)}
    isin_growth = columns[1]  # "ISIN Div Payout/ ISIN Growth"
    isin_reinvest = columns[2]  # "ISIN Div Reinvestment"

    scheme_type = category = fund_house = ""
    parsed: list[tuple[Record, date | None]] = []
    for line in lines[lines.index(header) + 1 :]:
        line = line.strip()
        if not line:
            continue
        if ";" not in line:
            if match := _CATEGORY.match(line):
                scheme_type = clean(match["type"])
                category = clean(match["category"])
            else:
                fund_house = clean(line)
            continue

        cells = [clean(cell) for cell in line.split(";")]
        if len(cells) < len(columns):
            continue
        get = {column: cells[position] for column, position in index.items()}
        code, name = get["schemecode"], get["schemename"]
        if not code.isdigit() or not name:
            continue
        plan_text, option_text = get.get("plan", ""), get.get("option", "")
        record = Record(
            kind="etf" if re.search(r"\bETFs?\b", category) else "mutual_fund",
            name=name,
            market="IN",
            currency="INR",
            classification=classify_fund(category, name),
            amfi_code=code,
            isin=optional(get[isin_growth]),
            isin_reinvestment=optional(get[isin_reinvest]),
            fund_house=fund_house or None,
            scheme_type=scheme_type or None,
            fund_category=category or None,
            plan=_plan(plan_text, name),
            option=option_text or None,
            option_kind=_option_kind(option_text, name),
            scheme_key=scheme_key(fund_house, name, category),
        )
        parsed.append((record, parse_date(get["date"])))

    nav_dates = [nav_date for _, nav_date in parsed if nav_date]
    if not nav_dates:
        raise SourceFormatError(f"{NAV_ALL} has no schemes with a NAV date")
    cutoff = max(nav_dates) - STALE_AFTER
    for record, nav_date in parsed:
        record.active = nav_date is not None and nav_date >= cutoff
    return [record for record, _ in parsed]
