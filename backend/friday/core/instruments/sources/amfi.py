"""AMFI ``NAVAll.txt``: every mutual fund scheme code with its latest NAV.

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
from dataclasses import dataclass, replace
from datetime import date, timedelta

from friday.core.instruments.classify import classify_fund
from friday.core.instruments.sources.common import (
    Record,
    SourceFormatError,
    clean,
    header_key,
    optional,
    parse_date,
    read_rows,
)

NAV_ALL = "NAVAll.txt"

STALE_AFTER = timedelta(days=30)
"""A scheme whose last NAV is this much older than the file's newest NAV is closed."""

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
    """Variants (plans and options) of one scheme share this key."""
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


# -- Scheme master ---------------------------------------------------------------------

SCHEME_MASTER = "SchemeData.csv"
"""AMFI's scheme master: ``portal.amfiindia.com/DownloadSchemeData_Po.aspx?mf=0``.

Checked 2026-10-25. Comma-separated, one row per scheme code::

    AMC,Code,Scheme Name,Scheme Type,Scheme Category,Scheme NAV Name,...
    Motilal Oswal Asset Management Company Limited,127042,Motilal Oswal Midcap Fund,
        Open Ended,Equity Scheme - Mid Cap Fund,Motilal Oswal Midcap Fund-Direct Plan-Growth
        Option,...                                          (one line in the file)

Only the *Scheme NAV Name* is used: it names the plan and option for the 5,600 rows of
``NAVAll.txt`` whose Plan and Option columns are blank.
"""

_OPTION_LABEL = {"growth": "Growth", "idcw": "IDCW", "bonus": "Bonus"}


@dataclass(frozen=True)
class SchemeLabel:
    """Plan and option of one scheme code, read from its NAV name in the scheme master."""

    amfi_code: str
    plan: str
    option_kind: str | None
    option: str | None


def parse_scheme_master(text: str) -> list[SchemeLabel]:
    rows = read_rows(
        text, file=SCHEME_MASTER, required={"amc", "code", "schemename", "schemenavname"}
    )
    parsed = []
    for row in rows:
        code, scheme, nav_name = row["code"], row["schemename"], row["schemenavname"]
        if not code.isdigit() or not nav_name:
            continue
        # What the NAV name adds to the scheme name, so a fund called "... Growth Fund"
        # isn't read as the growth option.
        suffix = (
            nav_name[len(scheme) :] if nav_name.lower().startswith(scheme.lower()) else nav_name
        )
        # Every scheme has had a direct plan since 2013; a variant not called direct is
        # sold through distributors, which is the regular plan.
        plan = "direct" if re.search(r"\bdirect\b", suffix, re.IGNORECASE) else "regular"
        if re.search(r"\bunclaimed\b", suffix, re.IGNORECASE):
            option_kind, option = "other", "Unclaimed"
        elif re.search(r"\bcumulative\b", suffix, re.IGNORECASE):
            option_kind, option = "growth", "Growth"
        else:
            option_kind = _option_kind("", suffix)
            option = _OPTION_LABEL.get(option_kind or "")
        parsed.append(
            (row["amc"].lower(), scheme.lower(), SchemeLabel(code, plan, option_kind, option))
        )

    # A plan with one variant and no option in its name is a growth-only scheme (index
    # funds often are): AMCs always name IDCW options.
    variants: dict[tuple[str, str, str], int] = {}
    for amc, scheme, label in parsed:
        key = (amc, scheme, label.plan)
        variants[key] = variants.get(key, 0) + 1
    return [
        replace(label, option_kind="growth", option="Growth")
        if label.option_kind is None and variants[(amc, scheme, label.plan)] == 1
        else label
        for amc, scheme, label in parsed
    ]


def fill_plan_and_option(records: list[Record], labels: list[SchemeLabel]) -> int:
    """Fill plan and option where ``NAVAll.txt`` left them blank and return how many
    records changed. ``NAVAll.txt`` wins where both say something: its columns are explicit,
    while NAV names are loose (about 150 read as another option, e.g. "Growth Plan - Bonus")."""
    by_code = {label.amfi_code: label for label in labels}
    filled = 0
    for record in records:
        label = by_code.get(record.amfi_code or "")
        if label is None or record.kind != "mutual_fund":
            continue  # an ETF is one variant: no plan or option to tell apart
        changed = False
        if record.plan is None:
            record.plan, changed = label.plan, True
        if record.option_kind is None and label.option_kind:
            record.option_kind, record.option, changed = label.option_kind, label.option, True
        filled += changed
    return filled
