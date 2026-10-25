"""Fund NAVs: tracking, sync, history and statistics (T1-12)."""

from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from friday.api.deps import SessionDep
from friday.core.instruments.models import Instrument
from friday.core.navs.models import NavSync
from friday.core.navs.service import (
    ME,
    Coverage,
    FundResult,
    NavStats,
    NotAFund,
    NotTracked,
    StillUsed,
    SyncResult,
    coverage,
    last_run,
    nav_series,
    nav_stats,
    require_fund,
    run_results,
    sync_navs,
    track,
    tracking_reasons,
    untrack,
)
from friday.core.navs.sources import NavPoint
from friday.core.schema_types import Nav, Percent, UtcDatetime

router = APIRouter(tags=["navs"])


class NavPointOut(BaseModel):
    date: date
    nav: Nav


class FundRef(BaseModel):
    id: int
    name: str
    amfi_code: str | None
    fund_house: str | None
    fund_category: str | None
    plan: str | None
    option: str | None
    is_active: bool


class CoverageOut(BaseModel):
    first: date | None
    last: date | None
    count: int


class FundResultOut(BaseModel):
    instrument_id: int
    name: str
    status: Literal["ok", "fallback", "failed"]
    added: int
    corrected: int
    last_date: date | None
    message: str | None


class SyncRunOut(BaseModel):
    id: int
    status: Literal["ok", "partial", "failed"]
    started_at: UtcDatetime
    finished_at: UtcDatetime
    funds: int
    added: int
    corrected: int
    failed: int
    results: list[FundResultOut]


class TrackedFundOut(BaseModel):
    fund: FundRef
    tracked_by_me: bool
    used_by: list[str]
    coverage: CoverageOut
    last_result: FundResultOut | None


class NavStatusOut(BaseModel):
    last_run: SyncRunOut | None
    funds: list[TrackedFundOut]


class NavStatsOut(BaseModel):
    first: NavPointOut
    latest: NavPointOut
    change_1d_pct: Percent | None
    change_1y_pct: Percent | None
    change_since_first_pct: Percent
    cagr_pct: Percent | None
    high_52w: NavPointOut
    low_52w: NavPointOut


class NavSummaryOut(BaseModel):
    instrument_id: int
    is_fund: bool
    tracked: bool
    tracked_by_me: bool
    used_by: list[str]
    coverage: CoverageOut
    stats: NavStatsOut | None


class SyncIn(BaseModel):
    instrument_ids: list[int] | None = None
    """Only these funds; all tracked funds when left out."""


def _point(point: NavPoint) -> NavPointOut:
    return NavPointOut(date=point[0], nav=point[1])


def _coverage(value: Coverage) -> CoverageOut:
    return CoverageOut(first=value.first, last=value.last, count=value.count)


def _result(result: FundResult) -> FundResultOut:
    return FundResultOut.model_validate(result, from_attributes=True)


def _stats(stats: NavStats | None) -> NavStatsOut | None:
    if stats is None:
        return None
    return NavStatsOut(
        first=_point(stats.first),
        latest=_point(stats.latest),
        change_1d_pct=stats.change_1d_pct,
        change_1y_pct=stats.change_1y_pct,
        change_since_first_pct=stats.change_since_first_pct,
        cagr_pct=stats.cagr_pct,
        high_52w=_point(stats.high_52w),
        low_52w=_point(stats.low_52w),
    )


def _run(run: NavSync) -> SyncRunOut:
    return SyncRunOut(
        id=run.id,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        funds=run.funds,
        added=run.added,
        corrected=run.corrected,
        failed=run.failed,
        results=[_result(result) for result in run_results(run)],
    )


def _sync_out(sync: SyncResult, session: Session) -> SyncRunOut:
    run = session.get(NavSync, sync.run_id)
    assert run is not None
    return _run(run)


def _instrument(session: Session, instrument_id: int) -> Instrument:
    instrument = session.get(Instrument, instrument_id)
    if instrument is None:
        raise HTTPException(404, f"No instrument with id {instrument_id}.")
    return instrument


def _fund(session: Session, instrument_id: int) -> Instrument:
    instrument = _instrument(session, instrument_id)
    try:
        require_fund(instrument)
    except NotAFund as error:
        raise HTTPException(422, str(error)) from None
    return instrument


def _summary(session: Session, instrument: Instrument) -> NavSummaryOut:
    reasons = tracking_reasons(session).get(instrument.id, [])
    is_fund = bool(instrument.amfi_code)
    return NavSummaryOut(
        instrument_id=instrument.id,
        is_fund=is_fund,
        tracked=bool(reasons),
        tracked_by_me=ME in reasons,
        used_by=[why for why in reasons if why != ME],
        coverage=_coverage(coverage(session, [instrument.id])[instrument.id]),
        stats=_stats(nav_stats(nav_series(session, instrument.id))) if is_fund else None,
    )


@router.get("/navs/status", operation_id="getNavStatus")
def status(session: SessionDep) -> NavStatusOut:
    """Every tracked fund with the NAV dates Friday has, and the last sync."""
    reasons = tracking_reasons(session)
    covered = coverage(session, reasons)
    run = last_run(session)
    last_results = {result.instrument_id: result for result in run_results(run)} if run else {}
    instruments = sorted(
        (session.get(Instrument, instrument_id) for instrument_id in reasons),
        key=lambda instrument: instrument.name if instrument else "",
    )
    return NavStatusOut(
        last_run=_run(run) if run else None,
        funds=[
            TrackedFundOut(
                fund=FundRef.model_validate(instrument, from_attributes=True),
                tracked_by_me=ME in reasons[instrument.id],
                used_by=[why for why in reasons[instrument.id] if why != ME],
                coverage=_coverage(covered[instrument.id]),
                last_result=_result(last_results[instrument.id])
                if instrument.id in last_results
                else None,
            )
            for instrument in instruments
            if instrument is not None
        ],
    )


@router.post("/navs/sync", operation_id="syncNavs")
def sync(request: Request, session: SessionDep, payload: SyncIn | None = None) -> SyncRunOut:
    """Download missing NAVs for every tracked fund, or only the given ones (D-046)."""
    ids = payload.instrument_ids if payload else None
    try:
        result = sync_navs(request.app.state.session_factory, request.app.state.nav_fetcher, ids)
    except NotTracked as error:
        raise HTTPException(409, f"Track these funds first ({error}).") from None
    return _sync_out(result, session)


@router.get("/instruments/{instrument_id}/navs", operation_id="getNavs")
def navs(
    session: SessionDep, instrument_id: int, start: date | None = None, end: date | None = None
) -> list[NavPointOut]:
    """A fund's NAVs, oldest first."""
    _fund(session, instrument_id)
    return [_point(point) for point in nav_series(session, instrument_id, start, end)]


@router.get("/instruments/{instrument_id}/nav-summary", operation_id="getNavSummary")
def nav_summary(session: SessionDep, instrument_id: int) -> NavSummaryOut:
    """Whether a fund is tracked, which NAV dates Friday has, and its headline figures."""
    return _summary(session, _instrument(session, instrument_id))


@router.put("/instruments/{instrument_id}/tracking", operation_id="trackFund")
def put_tracking(session: SessionDep, instrument_id: int) -> NavSummaryOut:
    """Keep this fund's NAVs. Sync it afterwards to download its history."""
    instrument = _fund(session, instrument_id)
    track(session, instrument)
    return _summary(session, instrument)


@router.delete("/instruments/{instrument_id}/tracking", operation_id="untrackFund")
def delete_tracking(session: SessionDep, instrument_id: int) -> NavSummaryOut:
    """Stop keeping this fund's NAVs up to date. NAVs already stored stay."""
    instrument = _instrument(session, instrument_id)
    try:
        untrack(session, instrument)
    except StillUsed as error:
        raise HTTPException(409, str(error)) from None
    return _summary(session, instrument)
