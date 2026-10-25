"""Refresh the instrument tables from the source lists (D-038, D-039, D-041).

Idempotent: a field is written only when its value changed, so a second run over the
same files changes nothing. Instruments are never deleted. One that drops off its list
becomes inactive; an old symbol or name becomes an alias.

Matching, per source:

- NSE: ISIN → symbol (only when the ISINs share an issuer code, because a face-value split
  changes the ISIN but exchanges also reuse delisted symbols) → NSE's symbol-change chain.
- AMFI: scheme code → ISIN of an NSE-listed ETF (one instrument for both, D-038).
- US: symbol → SEC CIK, when exactly one old and one new instrument share it (a rename).
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from friday.core.db import session_scope
from friday.core.instruments.download import Fetcher, FetchError
from friday.core.instruments.models import BUCKETS, Instrument, InstrumentAlias, InstrumentImport
from friday.core.instruments.search import rebuild_search_index
from friday.core.instruments.sources import amfi, nasdaq, nse, sec
from friday.core.instruments.sources.common import Record, SourceFormatError

SOURCES = ("nse", "amfi", "us")
"""Refresh order matters: AMFI attaches its scheme data to the NSE ETFs."""

_OWNER = {"nse": "nse", "amfi": "amfi", "us": "nasdaqtrader"}


class SuspiciousListError(ValueError):
    """A list came back much shorter than usual: probably a bad download (D-041)."""


@dataclass
class SourceResult:
    source: str
    status: str = "ok"
    rows: int = 0
    added: int = 0
    updated: int = 0
    deactivated: int = 0
    reactivated: int = 0
    aliases_added: int = 0
    message: str | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return any(
            (self.added, self.updated, self.deactivated, self.reactivated, self.aliases_added)
        )


def refresh_instruments(
    factory: sessionmaker[Session],
    fetcher: Fetcher,
    sources: Iterable[str] = SOURCES,
    *,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> list[SourceResult]:
    """Refresh each source in its own transaction, so one failing source keeps the others."""
    results = []
    for source in sources:
        started = clock()
        result = SourceResult(source)
        try:
            with session_scope(factory) as session:
                _Refresh(session, result, clock()).run(fetcher)
                if result.changed:
                    rebuild_search_index(session)
        except (FetchError, SourceFormatError, SuspiciousListError) as error:
            result = SourceResult(source, status="failed", message=str(error))
        with session_scope(factory) as session:
            message = "; ".join(filter(None, [result.message, *result.warnings])) or None
            session.add(
                InstrumentImport(
                    source=source,
                    status=result.status,
                    started_at=started,
                    finished_at=clock(),
                    rows=result.rows,
                    added=result.added,
                    updated=result.updated,
                    deactivated=result.deactivated,
                    reactivated=result.reactivated,
                    message=message[:2000] if message else None,
                )
            )
        results.append(result)
    return results


def _classification_values(record: Record) -> dict[str, Any]:
    allocation = record.classification.allocation
    values: dict[str, Any] = {f"{bucket}_pct": allocation.get(bucket) for bucket in BUCKETS}
    values["exposure"] = record.classification.exposure
    return values


def _same_issuer(a: str | None, b: str | None) -> bool:
    """ISINs ``INE335Y01012`` and ``INE335Y01020`` belong to the same company (IRCTC
    before and after its split): the country code, type letter and issuer code match."""
    return a is None or b is None or a[:7] == b[:7]


class _Refresh:
    def __init__(self, session: Session, result: SourceResult, now: datetime) -> None:
        self.session = session
        self.result = result
        self.now = now
        self.aliases: set[tuple[int, str, str]] | None = None

    def run(self, fetcher: Fetcher) -> None:
        getattr(self, f"_{self.result.source}")(fetcher)

    # -- shared steps -----------------------------------------------------------------

    def _check_size(self, owner: str, records: list[Record]) -> None:
        active_now = self.session.scalar(
            select(func.count())
            .select_from(Instrument)
            .where(Instrument.source == owner, Instrument.is_active)
        )
        active_new = sum(record.active for record in records)
        if active_now and active_new < active_now / 2:
            raise SuspiciousListError(
                f"{owner} list has {active_new} active instruments, but Friday has {active_now}:"
                " refusing to deactivate half the list. Check the downloaded files."
            )

    def _create(self, values: dict[str, Any]) -> Instrument:
        instrument = Instrument(**values, created_at=self.now, updated_at=self.now)
        self.session.add(instrument)
        self.result.added += 1
        return instrument

    def _update(
        self, instrument: Instrument, values: dict[str, Any], *, alias_names: bool = True
    ) -> None:
        changes = {key: value for key, value in values.items() if getattr(instrument, key) != value}
        if not changes:
            return
        if "is_active" in changes:
            if changes["is_active"]:
                self.result.reactivated += 1
            else:
                self.result.deactivated += 1
        old_symbol, old_name = instrument.symbol, instrument.name
        for key, value in changes.items():
            setattr(instrument, key, value)
        instrument.updated_at = self.now
        if set(changes) - {"is_active"}:
            self.result.updated += 1
        if "symbol" in changes and old_symbol:
            self._add_alias(instrument, "symbol", old_symbol, None)
        if alias_names and "name" in changes and old_name.lower() != instrument.name.lower():
            self._add_alias(instrument, "name", old_name, None)

    def _deactivate(self, instruments: Iterable[Instrument]) -> None:
        for instrument in instruments:
            if instrument.is_active:
                instrument.is_active = False
                instrument.updated_at = self.now
                self.result.deactivated += 1

    def _add_alias(self, instrument: Instrument, kind: str, value: str, on: date | None) -> None:
        if self.aliases is None:
            self.aliases = {
                (alias.instrument_id, alias.kind, alias.value.lower())
                for alias in self.session.scalars(select(InstrumentAlias))
            }
        key = (instrument.id, kind, value.lower())
        if instrument.id is None or key in self.aliases:
            return
        self.aliases.add(key)
        self.session.add(
            InstrumentAlias(instrument_id=instrument.id, kind=kind, value=value, changed_on=on)
        )
        self.result.aliases_added += 1

    def _apply(
        self,
        pairs: list[tuple[Instrument | None, dict[str, Any]]],
        stale: list[Instrument],
    ) -> None:
        """Write matches in two steps, so a symbol moving from one row to another never
        collides with the active-symbol unique index halfway through: first clear the
        symbols that change and deactivate stale rows, then write the new values."""
        moving: dict[int, str | None] = {}
        for instrument, values in pairs:
            if instrument is not None and instrument.symbol != values["symbol"]:
                moving[instrument.id] = instrument.symbol
                instrument.symbol = None
        self._deactivate(stale)
        self.session.flush()
        for instrument, values in pairs:
            if instrument is None:
                self._create(values)
                continue
            if instrument.id in moving:
                instrument.symbol = moving[instrument.id]  # so _update sees and aliases it
            self._update(instrument, values)
        self.session.flush()

    # -- NSE ----------------------------------------------------------------------------

    def _nse(self, fetcher: Fetcher) -> None:
        records = {r.symbol: r for r in nse.parse_equity_list(fetcher.get(nse.EQUITY_LIST))}
        records.update({r.symbol: r for r in nse.parse_etf_list(fetcher.get(nse.ETF_LIST))})
        symbol_changes = self._optional(fetcher, nse.SYMBOL_CHANGES, nse.parse_symbol_changes)
        name_changes = self._optional(fetcher, nse.NAME_CHANGES, nse.parse_name_changes)
        self.result.rows = len(records)
        self._check_size("nse", list(records.values()))

        existing = list(
            self.session.scalars(
                select(Instrument).where(
                    (Instrument.exchange == "NSE")
                    | ((Instrument.source == "amfi") & (Instrument.kind == "etf"))
                )
            )
        )
        matches = self._match_nse(list(records.values()), existing, symbol_changes or [])
        stale = [
            i
            for i in existing
            if i.source == "nse" and i.id not in {m.id for m in matches.values() if m}
        ]

        pairs = []
        for record in records.values():
            instrument = matches.get(record.symbol)
            values = {
                "kind": record.kind,
                "name": record.name,
                "market": "IN",
                "currency": "INR",
                "source": "nse",
                "is_active": True,
                "exchange": "NSE",
                "symbol": record.symbol,
                "isin": record.isin,
                "series": record.series,
                "listed_on": record.listed_on,
                **_classification_values(record),
            }
            if instrument is not None and instrument.amfi_code:
                del values["name"]  # the AMFI scheme name is the readable one (D-038)
            pairs.append((instrument, values))
        self._apply(pairs, stale)
        self._nse_aliases(symbol_changes or [], name_changes or [])

    def _match_nse(
        self,
        records: list[Record],
        existing: list[Instrument],
        changes: list[nse.SymbolChange],
    ) -> dict[str | None, Instrument | None]:
        by_isin: dict[str, list[Instrument]] = {}
        by_symbol: dict[str, Instrument] = {}
        for instrument in sorted(existing, key=lambda i: not i.is_active):  # active first
            if instrument.isin:
                by_isin.setdefault(instrument.isin, []).append(instrument)
            if instrument.symbol and instrument.exchange == "NSE":
                by_symbol.setdefault(instrument.symbol, instrument)

        taken: set[int] = set()
        matches: dict[str | None, Instrument | None] = {}

        def take(record: Record, instrument: Instrument) -> None:
            matches[record.symbol] = instrument
            taken.add(instrument.id)

        for record in records:  # 1. same ISIN
            for instrument in by_isin.get(record.isin or "", []):
                if instrument.id not in taken:
                    take(record, instrument)
                    break
        for record in records:  # 2. same symbol, same issuer
            if record.symbol in matches:
                continue
            instrument = by_symbol.get(record.symbol or "")
            if (
                instrument
                and instrument.id not in taken
                and _same_issuer(instrument.isin, record.isin)
            ):
                take(record, instrument)
        if changes:  # 3. old symbol renamed to this one
            renamed: dict[str, Instrument] = {}
            for instrument in existing:
                if (
                    instrument.id not in taken
                    and instrument.symbol
                    and instrument.exchange == "NSE"
                ):
                    new_symbol = nse.resolve_symbol(instrument.symbol, changes)
                    if new_symbol != instrument.symbol:
                        renamed.setdefault(new_symbol, instrument)
            for record in records:
                instrument = renamed.get(record.symbol or "")
                if record.symbol not in matches and instrument and instrument.id not in taken:
                    take(record, instrument)
        return matches

    def _nse_aliases(
        self, symbol_changes: list[nse.SymbolChange], name_changes: list[nse.NameChange]
    ) -> None:
        """Old symbols and names from NSE's change files, so "Zomato" finds Eternal."""
        active = {
            i.symbol: i
            for i in self.session.scalars(
                select(Instrument).where(Instrument.exchange == "NSE", Instrument.is_active)
            )
        }
        for change in symbol_changes:
            instrument = active.get(nse.resolve_symbol(change.old, symbol_changes))
            if instrument and change.old != instrument.symbol:
                self._add_alias(instrument, "symbol", change.old, change.changed_on)
        for change in name_changes:
            instrument = active.get(nse.resolve_symbol(change.symbol, symbol_changes))
            if instrument and change.old_name.lower() != instrument.name.lower():
                self._add_alias(instrument, "name", change.old_name, change.changed_on)

    def _optional(self, fetcher: Fetcher, file: str, parse: Callable[[str], list]) -> list | None:
        try:
            return parse(fetcher.get(file))
        except (FetchError, SourceFormatError) as error:
            self.result.warnings.append(f"skipped {file}: {error}")
            return None

    # -- AMFI ---------------------------------------------------------------------------

    def _amfi(self, fetcher: Fetcher) -> None:
        records = amfi.parse_nav_all(fetcher.get(amfi.NAV_ALL))
        self.result.rows = len(records)
        self._check_size("amfi", records)
        labels = self._optional(fetcher, amfi.SCHEME_MASTER, amfi.parse_scheme_master)
        blank = {r.amfi_code for r in records if r.plan is None or r.option_kind is None}
        if labels is not None:
            amfi.fill_plan_and_option(records, labels)

        by_code = {
            i.amfi_code: i
            for i in self.session.scalars(
                select(Instrument).where(Instrument.amfi_code.is_not(None))
            )
        }
        listed_etfs = {
            i.isin: i
            for i in self.session.scalars(
                select(Instrument).where(
                    Instrument.exchange == "NSE",
                    Instrument.kind == "etf",
                    Instrument.amfi_code.is_(None),
                )
            )
            if i.isin
        }
        seen: set[str] = set()
        for record in records:
            fund_values = {
                "name": record.name,
                "amfi_code": record.amfi_code,
                "isin_reinvestment": record.isin_reinvestment,
                "fund_house": record.fund_house,
                "scheme_type": record.scheme_type,
                "fund_category": record.fund_category,
            }
            instrument = by_code.get(record.amfi_code) or listed_etfs.pop(record.isin or "", None)
            seen.add(record.amfi_code or "")
            if instrument is not None and instrument.source == "nse":
                # An NSE-listed ETF: NSE decides symbol, status and classification.
                self._update(instrument, fund_values, alias_names=False)
                by_code[record.amfi_code] = instrument
                continue
            values = {
                **fund_values,
                "kind": record.kind,
                "market": "IN",
                "currency": "INR",
                "source": "amfi",
                "is_active": record.active,
                "isin": record.isin,
                "plan": record.plan,
                "option": record.option,
                "option_kind": record.option_kind,
                "scheme_key": record.scheme_key,
                **_classification_values(record),
            }
            if labels is None and record.amfi_code in blank and instrument is not None:
                # Without the scheme master, keep the plan and option it gave last time.
                for key in ("plan", "option", "option_kind"):
                    del values[key]
            if instrument is None:
                by_code[record.amfi_code] = self._create(values)
            else:
                self._update(instrument, values)
        self._deactivate(
            i for code, i in by_code.items() if i.source == "amfi" and code not in seen
        )
        self.session.flush()

    # -- US -----------------------------------------------------------------------------

    def _us(self, fetcher: Fetcher) -> None:
        records: dict[str, Record] = {}
        for record in nasdaq.parse_nasdaq_listed(fetcher.get(nasdaq.NASDAQ_LISTED)):
            records[record.symbol or ""] = record
        for record in nasdaq.parse_other_listed(fetcher.get(nasdaq.OTHER_LISTED)):
            records.setdefault(record.symbol or "", record)
        ciks = self._optional_ciks(fetcher)
        self.result.rows = len(records)
        self._check_size("nasdaqtrader", list(records.values()))

        existing = list(self.session.scalars(select(Instrument).where(Instrument.market == "US")))
        by_symbol: dict[str, Instrument] = {}
        for instrument in sorted(existing, key=lambda i: not i.is_active):
            by_symbol.setdefault(instrument.symbol or "", instrument)

        matches: dict[str, Instrument] = {}
        for symbol in records:
            if symbol in by_symbol:
                matches[symbol] = by_symbol[symbol]
        if ciks:  # a ticker change keeps the company's CIK (FB → META)
            taken = {i.id for i in matches.values()}
            old = _unique_by(
                (i for i in existing if i.id not in taken and i.is_active and i.cik),
                lambda i: i.cik,
            )
            new = _unique_by((s for s in records if s not in matches and s in ciks), ciks.get)
            for cik, symbol in new.items():
                if cik in old:
                    matches[symbol] = old[cik]
        matched_ids = {i.id for i in matches.values()}
        stale = [i for i in existing if i.source == "nasdaqtrader" and i.id not in matched_ids]

        pairs = []
        for symbol, record in records.items():
            values = {
                "kind": record.kind,
                "name": record.name,
                "market": "US",
                "currency": "USD",
                "source": "nasdaqtrader",
                "is_active": True,
                "exchange": record.exchange,
                "symbol": symbol,
                **_classification_values(record),
            }
            if symbol in ciks:
                values["cik"] = ciks[symbol]
            pairs.append((matches.get(symbol), values))
        self._apply(pairs, stale)

    def _optional_ciks(self, fetcher: Fetcher) -> dict[str, str]:
        try:
            return sec.parse_company_tickers(fetcher.get(sec.COMPANY_TICKERS))
        except (FetchError, SourceFormatError) as error:
            self.result.warnings.append(f"skipped CIKs: {error}")
            return {}


def _unique_by(items: Iterable[Any], key: Callable[[Any], Any]) -> dict[Any, Any]:
    """Map key → item, keeping only keys that exactly one item has."""
    found: dict[Any, Any] = {}
    duplicates = set()
    for item in items:
        k = key(item)
        if k in found:
            duplicates.add(k)
        found[k] = item
    return {k: item for k, item in found.items() if k not in duplicates}
