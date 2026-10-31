"""Tracking funds, syncing their NAVs and reading them back.

Sync is one operation: for every tracked fund, download its NAV history and store
whatever is missing or was corrected. Running it twice adds nothing. When mfapi.in fails
for a fund, the latest NAV still comes from AMFI's ``NAVAll.txt``.
"""

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session, sessionmaker

from friday.core.db import session_scope
from friday.core.holdings.service import add_due_instalments, holding_reasons
from friday.core.instruments.download import FetchError
from friday.core.instruments.models import Instrument
from friday.core.instruments.sources.common import SourceFormatError
from friday.core.models.service import model_reasons
from friday.core.navs.download import NavFetcher
from friday.core.navs.models import FundNav, NavSync, TrackedFund
from friday.core.navs.sources import NavPoint, parse_amfi_latest, parse_mfapi

HUNDRED = Decimal(100)
CENT = Decimal("0.01")

ME = "me"
"""Tracking reason for a fund I marked myself."""


class NotAFund(ValueError):
    """Only AMFI schemes have NAVs."""


class NotTracked(ValueError):
    """Sync was asked for a fund nobody tracks."""


class StillUsed(ValueError):
    """The fund can't be untracked while a model uses it."""


def require_fund(instrument: Instrument) -> None:
    if not instrument.amfi_code:
        raise NotAFund(f"{instrument.name} is not a mutual fund scheme, so it has no NAVs.")


def _used_by(session: Session) -> dict[int, list[str]]:
    """Why a fund is tracked other than my marking it: models and holdings."""
    reasons = model_reasons(session)
    for instrument_id, why in holding_reasons(session).items():
        reasons.setdefault(instrument_id, []).extend(why)
    return reasons


def tracking_reasons(session: Session) -> dict[int, list[str]]:
    """Every tracked fund and why: ``"me"``, the models that use it, or ``"holding"``."""
    reasons: dict[int, list[str]] = {
        instrument_id: [ME] for instrument_id in session.scalars(select(TrackedFund.instrument_id))
    }
    for instrument_id, why in _used_by(session).items():
        reasons.setdefault(instrument_id, []).extend(why)
    return reasons


def track(session: Session, instrument: Instrument) -> None:
    require_fund(instrument)
    if session.get(TrackedFund, instrument.id) is None:
        session.add(TrackedFund(instrument_id=instrument.id, added_at=datetime.now(UTC)))
        session.flush()


def untrack(session: Session, instrument: Instrument) -> None:
    others = [why for why in _used_by(session).get(instrument.id, []) if why != ME]
    if others:
        raise StillUsed(f"{instrument.name} is used by {', '.join(others)}; remove it there first.")
    tracked = session.get(TrackedFund, instrument.id)
    if tracked is not None:
        session.delete(tracked)
        session.flush()


@dataclass
class FundResult:
    instrument_id: int
    name: str
    status: str = "ok"  # ok | fallback (latest NAV from AMFI only) | failed
    added: int = 0
    corrected: int = 0
    last_date: date | None = None
    message: str | None = None


@dataclass
class SyncResult:
    run_id: int
    status: str
    started_at: datetime
    finished_at: datetime
    results: list[FundResult] = field(default_factory=list)

    @property
    def added(self) -> int:
        return sum(result.added for result in self.results)


def _store(session: Session, instrument_id: int, points: Iterable[NavPoint], source: str):
    """Insert NAVs for new dates and correct changed ones. Returns (added, corrected)."""
    existing = dict(
        session.execute(
            select(FundNav.nav_date, FundNav.nav).where(FundNav.instrument_id == instrument_id)
        ).all()
    )
    new_rows, corrected = [], 0
    for nav_date, nav in points:
        old = existing.get(nav_date)
        if old is None:
            new_rows.append(
                {"instrument_id": instrument_id, "nav_date": nav_date, "nav": nav, "source": source}
            )
        elif old != nav:
            session.execute(
                update(FundNav)
                .where(FundNav.instrument_id == instrument_id, FundNav.nav_date == nav_date)
                .values(nav=nav, source=source)
            )
            corrected += 1
    if new_rows:
        session.execute(insert(FundNav), new_rows)
    return len(new_rows), corrected


def _last_date(session: Session, instrument_id: int) -> date | None:
    return session.scalar(
        select(func.max(FundNav.nav_date)).where(FundNav.instrument_id == instrument_id)
    )


class _Latest:
    """AMFI's latest-NAV file, downloaded at most once per sync and only if needed."""

    def __init__(self, fetcher: NavFetcher) -> None:
        self.fetcher = fetcher
        self.navs: dict[str, NavPoint] | None = None
        self.error: str | None = None

    def get(self, amfi_code: str) -> NavPoint | None:
        if self.navs is None and self.error is None:
            try:
                self.navs = parse_amfi_latest(self.fetcher.latest())
            except (FetchError, SourceFormatError) as exc:
                self.error = str(exc)
        return (self.navs or {}).get(amfi_code)


def sync_navs(
    factory: sessionmaker[Session],
    fetcher: NavFetcher,
    instrument_ids: Iterable[int] | None = None,
) -> SyncResult:
    """Catch every tracked fund (or the given ones) up to today. Each fund is committed on
    its own, so one failure doesn't undo the others."""
    started = datetime.now(UTC)
    with session_scope(factory) as session:
        tracked = tracking_reasons(session)
        wanted = list(tracked) if instrument_ids is None else list(dict.fromkeys(instrument_ids))
        missing = [instrument_id for instrument_id in wanted if instrument_id not in tracked]
        if missing:
            raise NotTracked(f"not tracked: {', '.join(map(str, missing))}")
        funds = [
            (instrument.id, instrument.name, instrument.amfi_code)
            for instrument in session.scalars(
                select(Instrument).where(Instrument.id.in_(wanted)).order_by(Instrument.name)
            )
        ]

    latest = _Latest(fetcher)
    results: list[FundResult] = []
    for instrument_id, name, amfi_code in funds:
        result = FundResult(instrument_id=instrument_id, name=name)
        results.append(result)
        try:
            points = parse_mfapi(fetcher.history(amfi_code), amfi_code)
            if not points:
                raise SourceFormatError(f"mfapi {amfi_code}: no NAVs in the response")
            source = "mfapi"
        except (FetchError, SourceFormatError) as exc:
            point = latest.get(amfi_code)
            if point is None:
                result.status = "failed"
                result.message = str(exc) + (f"; AMFI: {latest.error}" if latest.error else "")
                continue
            points, source = [point], "amfi"
            result.status = "fallback"
            result.message = f"history unavailable ({exc}); latest NAV from AMFI"
        with session_scope(factory) as session:
            result.added, result.corrected = _store(session, instrument_id, points, source)
            result.last_date = _last_date(session, instrument_id)

    failed = sum(result.status == "failed" for result in results)
    status = "failed" if results and failed == len(results) else "partial" if failed else "ok"
    finished = datetime.now(UTC)
    with session_scope(factory) as session:
        run = NavSync(
            status=status,
            started_at=started,
            finished_at=finished,
            funds=len(results),
            added=sum(result.added for result in results),
            corrected=sum(result.corrected for result in results),
            failed=failed,
            results=json.dumps([asdict(result) for result in results], default=str),
        )
        session.add(run)
        session.flush()
        run_id = run.id
        add_due_instalments(session)  # new NAVs may cover new SIP instalments
    return SyncResult(run_id, status, started, finished, results)


def run_results(run: NavSync) -> list[FundResult]:
    results = []
    for item in json.loads(run.results):
        last = item.get("last_date")
        results.append(
            FundResult(**{**item, "last_date": date.fromisoformat(last) if last else None})
        )
    return results


def last_run(session: Session) -> NavSync | None:
    return session.scalars(select(NavSync).order_by(NavSync.id.desc()).limit(1)).first()


@dataclass(frozen=True)
class Coverage:
    first: date | None = None
    last: date | None = None
    count: int = 0


def coverage(session: Session, instrument_ids: Iterable[int]) -> dict[int, Coverage]:
    ids = list(instrument_ids)
    rows = session.execute(
        select(
            FundNav.instrument_id,
            func.min(FundNav.nav_date),
            func.max(FundNav.nav_date),
            func.count(),
        )
        .where(FundNav.instrument_id.in_(ids))
        .group_by(FundNav.instrument_id)
    ).all()
    found = {row[0]: Coverage(row[1], row[2], row[3]) for row in rows}
    return {instrument_id: found.get(instrument_id, Coverage()) for instrument_id in ids}


def nav_series(
    session: Session, instrument_id: int, start: date | None = None, end: date | None = None
) -> list[NavPoint]:
    """NAVs oldest first, optionally limited to ``start``–``end`` (both inclusive)."""
    statement = select(FundNav.nav_date, FundNav.nav).where(FundNav.instrument_id == instrument_id)
    if start:
        statement = statement.where(FundNav.nav_date >= start)
    if end:
        statement = statement.where(FundNav.nav_date <= end)
    return [(row[0], row[1]) for row in session.execute(statement.order_by(FundNav.nav_date))]


@dataclass(frozen=True)
class NavStats:
    first: NavPoint
    latest: NavPoint
    change_1d_pct: Decimal | None
    change_1y_pct: Decimal | None
    change_since_first_pct: Decimal
    cagr_pct: Decimal | None
    high_52w: NavPoint
    low_52w: NavPoint


def _pct(new: Decimal, old: Decimal) -> Decimal:
    return ((new / old - 1) * HUNDRED).quantize(CENT, ROUND_HALF_UP)


def years_before(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year - years)
    except ValueError:  # 29 February
        return day.replace(year=day.year - years, day=28)


def nav_stats(points: list[NavPoint]) -> NavStats | None:
    """Headline figures for a NAV history (oldest first)."""
    if not points:
        return None
    first, latest = points[0], points[-1]
    year_ago = years_before(latest[0], 1)
    before = [point for point in points if point[0] <= year_ago]
    last_year = [point for point in points if point[0] > year_ago]
    days = (latest[0] - first[0]).days
    cagr = None
    if days >= 365:
        rate = (float(latest[1] / first[1]) ** (365 / days) - 1) * 100
        cagr = Decimal(str(round(rate, 2))).quantize(CENT)
    return NavStats(
        first=first,
        latest=latest,
        change_1d_pct=_pct(latest[1], points[-2][1]) if len(points) > 1 else None,
        change_1y_pct=_pct(latest[1], before[-1][1]) if before else None,
        change_since_first_pct=_pct(latest[1], first[1]),
        cagr_pct=cagr,
        high_52w=max(last_year, key=lambda point: (point[1], point[0])),
        low_52w=min(last_year, key=lambda point: (point[1], point[0])),
    )
