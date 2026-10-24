"""Instrument search over a local SQLite FTS5 index (D-042).

The index ``instrument_search`` holds one row per instrument (rowid = instrument id) with
three columns: symbols and codes, the name, and extra text (fund house, old names). It is
rebuilt after any refresh that changed something; that takes well under a second.

Ranking: exact symbol, scheme code or ISIN first, then symbol prefix, then text relevance.
Mutual fund variants (plans and options of one scheme) come back as one result, Direct
Growth first, with the others listed as its variants.
"""

import re
from dataclasses import dataclass, field

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from friday.core.instruments.models import Instrument

FTS_TABLE = "instrument_search"

# Created in migration 0002: columns symbols, name, extra; '&' kept inside words ("M&M").

_REBUILD = f"""
INSERT INTO {FTS_TABLE} (rowid, symbols, name, extra)
SELECT
    i.id,
    coalesce(i.symbol, '') || ' ' || coalesce(i.amfi_code, '') || ' ' || coalesce(i.isin, '')
        || ' ' || coalesce((SELECT group_concat(a.value, ' ') FROM instrument_aliases a
                            WHERE a.instrument_id = i.id AND a.kind = 'symbol'), ''),
    i.name,
    coalesce(i.fund_house, '')
        || ' ' || coalesce((SELECT group_concat(a.value, ' ') FROM instrument_aliases a
                            WHERE a.instrument_id = i.id AND a.kind = 'name'), '')
FROM instruments i
"""

# bm25 column weights: a symbol hit counts most, then the name, then fund house / old names.
_SEARCH = f"""
SELECT i.id,
    CASE
        WHEN upper(i.symbol) = :exact OR i.amfi_code = :exact OR i.isin = :exact THEN 0
        WHEN upper(i.symbol) LIKE :prefix ESCAPE '\\' THEN 1
        ELSE 2
    END AS tier,
    bm25({FTS_TABLE}, 10.0, 4.0, 1.0) AS score
FROM {FTS_TABLE} JOIN instruments i ON i.id = {FTS_TABLE}.rowid
WHERE {FTS_TABLE} MATCH :match
    AND (:include_inactive OR i.is_active)
    AND (:market IS NULL OR i.market = :market)
    AND (:kind IS NULL OR i.kind = :kind)
ORDER BY
    tier,
    score,
    CASE i.plan WHEN 'direct' THEN 0 WHEN 'regular' THEN 2 ELSE 1 END,
    CASE i.option_kind WHEN 'growth' THEN 0 WHEN 'idcw' THEN 2 ELSE 1 END,
    i.name
LIMIT :fetch
"""

MAX_LIMIT = 50


def rebuild_search_index(session: Session) -> None:
    session.flush()
    session.execute(text(f"DELETE FROM {FTS_TABLE}"))
    session.execute(text(_REBUILD))


def _tokens(query: str) -> list[str]:
    return re.findall(r"[\w&]+", query.lower())


def _variant_order(instrument: Instrument) -> tuple[int, int, str]:
    plan = {"direct": 0, "regular": 2}.get(instrument.plan or "", 1)
    option = {"growth": 0, "idcw": 2}.get(instrument.option_kind or "", 1)
    return plan, option, instrument.option or ""


@dataclass
class SearchHit:
    instrument: Instrument
    variants: list[Instrument] = field(default_factory=list)  # other plans and options


def _groups(instrument: Instrument) -> bool:
    return instrument.kind == "mutual_fund" and instrument.scheme_key is not None


def scheme_variants(session: Session, instrument: Instrument) -> list[Instrument]:
    """The other plans and options of a mutual fund scheme, best first."""
    if not _groups(instrument):
        return []
    statement = select(Instrument).where(
        Instrument.scheme_key == instrument.scheme_key,
        Instrument.kind == "mutual_fund",
        Instrument.id != instrument.id,
    )
    if instrument.is_active:  # a closed scheme lists every variant; an open one, open ones
        statement = statement.where(Instrument.is_active)
    return sorted(session.scalars(statement), key=_variant_order)


def search_instruments(
    session: Session,
    query: str,
    *,
    limit: int = 20,
    market: str | None = None,
    kind: str | None = None,
    include_inactive: bool = False,
) -> list[SearchHit]:
    tokens = _tokens(query)
    if not tokens:
        return []
    limit = max(1, min(limit, MAX_LIMIT))
    exact = query.strip().upper()
    escaped = exact.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    rows = session.execute(
        text(_SEARCH),
        {
            "match": " ".join(f'"{token}"*' for token in tokens),
            "exact": exact,
            "prefix": f"{escaped}%",
            "include_inactive": include_inactive,
            "market": market,
            "kind": kind,
            "fetch": limit * 5,  # room to fold fund variants together
        },
    ).all()
    ids = [row.id for row in rows]
    exact_ids = {row.id for row in rows if row.tier == 0}
    by_id = {i.id: i for i in session.scalars(select(Instrument).where(Instrument.id.in_(ids)))}

    hits: list[SearchHit] = []
    seen_schemes: set[str] = set()
    for instrument_id in ids:
        instrument = by_id[instrument_id]
        if _groups(instrument):
            if instrument.scheme_key in seen_schemes:
                continue
            seen_schemes.add(instrument.scheme_key or "")
        hits.append(SearchHit(instrument))
        if len(hits) == limit:
            break

    grouped = [hit for hit in hits if _groups(hit.instrument)]
    if grouped:
        keys = {hit.instrument.scheme_key for hit in grouped}
        siblings: dict[str, list[Instrument]] = {}
        statement = select(Instrument).where(
            Instrument.scheme_key.in_(keys), Instrument.kind == "mutual_fund"
        )
        if not include_inactive:
            statement = statement.where(Instrument.is_active)
        for other in session.scalars(statement):
            siblings.setdefault(other.scheme_key or "", []).append(other)
        for hit in grouped:
            members = siblings.get(hit.instrument.scheme_key or "", [])
            if hit.instrument not in members:
                members.append(hit.instrument)
            members.sort(key=_variant_order)
            # The scheme leads with its best variant (Direct Growth), not whichever variant
            # the text score ranked first, unless I typed that variant's exact code.
            if hit.instrument.id not in exact_ids:
                hit.instrument = members[0]
            hit.variants = [m for m in members if m.id != hit.instrument.id]
    return hits
