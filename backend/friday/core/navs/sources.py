"""NAV parsers.

mfapi.in, ``https://api.mfapi.in/mf/<scheme code>``, checked 2026-10-25::

    {"meta": {"scheme_code": 122639, "scheme_name": "...", ...},
     "data": [{"date": "23-10-2026", "nav": "88.96950"}, ...]}     <- newest first

AMFI ``NAVAll.txt`` (see :mod:`friday.core.instruments.sources.amfi`) has each scheme's
latest NAV and its date in the last two columns.
"""

import json
from datetime import date
from decimal import Decimal, InvalidOperation

from friday.core.instruments.sources.common import SourceFormatError, header_key, parse_date

MAX_PLACES = 8
"""NAVs are kept as published, up to this many decimal places."""

NavPoint = tuple[date, Decimal]


def parse_nav(text: str) -> Decimal | None:
    """A published NAV as an exact decimal; ``None`` for blanks, ``N.A.``, zero or less."""
    try:
        nav = Decimal(text.strip().replace(",", ""))
    except InvalidOperation:
        return None
    if not nav.is_finite() or nav <= 0:
        return None
    nav = nav.normalize()
    if -nav.as_tuple().exponent > MAX_PLACES:
        nav = round(nav, MAX_PLACES).normalize()
    return nav


def parse_mfapi(text: str, amfi_code: str) -> list[NavPoint]:
    """One fund's NAV history from mfapi.in, oldest first, one NAV per date."""
    try:
        body = json.loads(text)
    except json.JSONDecodeError:
        raise SourceFormatError(f"mfapi {amfi_code}: not JSON: {text[:80]!r}") from None
    if not isinstance(body, dict) or not isinstance(body.get("data"), list):
        raise SourceFormatError(f"mfapi {amfi_code}: no NAV list in the response")
    code = str((body.get("meta") or {}).get("scheme_code", ""))
    if code and code != amfi_code:
        raise SourceFormatError(f"mfapi {amfi_code}: answered for scheme {code} instead")

    navs: dict[date, Decimal] = {}
    for row in body["data"]:
        if not isinstance(row, dict):
            continue
        nav_date = parse_date(str(row.get("date", "")))
        nav = parse_nav(str(row.get("nav", "")))
        if nav_date and nav:
            navs.setdefault(nav_date, nav)  # newest first: keep the first value per date
    return sorted(navs.items())


def parse_amfi_latest(text: str) -> dict[str, NavPoint]:
    """Scheme code → (date, NAV) for every scheme in AMFI's ``NAVAll.txt`` with a NAV."""
    lines = text.lstrip("﻿").splitlines()
    header = next((line for line in lines if line.strip()), "")
    columns = [header_key(column) for column in header.split(";")]
    if not {"schemecode", "netassetvalue", "date"} <= set(columns):
        raise SourceFormatError(f"NAVAll.txt doesn't look right: first line was {header[:80]!r}")
    code_at, nav_at, date_at = (
        columns.index("schemecode"),
        columns.index("netassetvalue"),
        columns.index("date"),
    )
    latest: dict[str, NavPoint] = {}
    for line in lines[1:]:
        cells = line.strip().split(";")
        if len(cells) < len(columns) or not cells[code_at].strip().isdigit():
            continue
        nav_date = parse_date(cells[date_at])
        nav = parse_nav(cells[nav_at])
        if nav_date and nav:
            latest[cells[code_at].strip()] = (nav_date, nav)
    return latest
