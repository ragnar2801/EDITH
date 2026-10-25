"""Instrument search, detail and my classification overrides (T1-02)."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from friday.api.deps import SessionDep
from friday.core.instruments.classify import Classification
from friday.core.instruments.models import Instrument, InstrumentImport
from friday.core.instruments.refresh import SOURCES, refresh_instruments
from friday.core.instruments.search import MAX_LIMIT, scheme_variants, search_instruments
from friday.core.instruments.service import (
    InvalidClassification,
    clear_override,
    effective_classification,
    rule_classification,
    set_override,
    source_statuses,
)
from friday.core.schema_types import Percent, UtcDatetime

router = APIRouter(prefix="/instruments", tags=["instruments"])

Kind = Literal["stock", "etf", "mutual_fund"]
Market = Literal["IN", "US"]
Currency = Literal["INR", "USD"]
Bucket = Literal["equity", "debt", "gold", "silver", "other"]
AssetClass = Literal["equity", "debt", "gold", "silver", "other", "hybrid", "unclassified"]
Exposure = Literal["IN", "US", "GLOBAL"]


class Share(BaseModel):
    bucket: Bucket
    percent: Percent


class ClassificationOut(BaseModel):
    asset_class: AssetClass
    allocation: list[Share]
    exposure: Exposure


class Variant(BaseModel):
    """Another plan or option of the same mutual fund scheme."""

    id: int
    amfi_code: str | None
    plan: str | None
    option: str | None
    is_active: bool


class InstrumentSummary(BaseModel):
    id: int
    kind: Kind
    name: str
    market: Market
    currency: Currency
    exchange: str | None
    symbol: str | None
    amfi_code: str | None
    isin: str | None
    fund_house: str | None
    fund_category: str | None
    plan: str | None
    option: str | None
    asset_class: AssetClass
    exposure: Exposure
    is_active: bool
    variants: list[Variant] = Field(default_factory=list)


class Alias(BaseModel):
    kind: Literal["symbol", "name"]
    value: str
    changed_on: date | None


class Override(ClassificationOut):
    note: str | None
    updated_at: UtcDatetime


class InstrumentDetail(InstrumentSummary):
    source: str
    series: str | None
    listed_on: date | None
    cik: str | None
    isin_reinvestment: str | None
    scheme_type: str | None
    aliases: list[Alias]
    rule: ClassificationOut
    override: Override | None
    created_at: UtcDatetime
    updated_at: UtcDatetime


class OverrideIn(BaseModel):
    allocation: list[Share] = Field(min_length=1)
    exposure: Exposure
    note: str | None = Field(default=None, max_length=500)


class ImportRun(BaseModel):
    status: Literal["ok", "failed"]
    finished_at: UtcDatetime
    rows: int
    added: int
    updated: int
    deactivated: int
    message: str | None


Source = Literal["nse", "amfi", "us"]


class SourceOut(BaseModel):
    source: Source
    active_instruments: int
    last_run: ImportRun | None
    last_success: ImportRun | None


class RefreshIn(BaseModel):
    sources: list[Source] | None = Field(default=None, description="Blank: every list")


class RefreshResultOut(BaseModel):
    source: Source
    status: Literal["ok", "failed"]
    rows: int
    added: int
    updated: int
    deactivated: int
    reactivated: int
    message: str | None
    warnings: list[str]


def _classification(classification: Classification) -> ClassificationOut:
    return ClassificationOut(
        asset_class=classification.asset_class,
        allocation=[
            Share(bucket=bucket, percent=pct) for bucket, pct in classification.allocation.items()
        ],
        exposure=classification.exposure,
    )


def _variant(instrument: Instrument) -> Variant:
    return Variant.model_validate(instrument, from_attributes=True)


def _summary_fields(instrument: Instrument, variants: list[Instrument]) -> dict:
    effective = effective_classification(instrument)
    return {
        **{
            field: getattr(instrument, field)
            for field in InstrumentSummary.model_fields
            if field not in {"asset_class", "exposure", "variants"}
        },
        "asset_class": effective.asset_class,
        "exposure": effective.exposure,
        "variants": [_variant(variant) for variant in variants],
    }


def _import_run(run: InstrumentImport | None) -> ImportRun | None:
    return None if run is None else ImportRun.model_validate(run, from_attributes=True)


def _get(session: Session, instrument_id: int) -> Instrument:
    instrument = session.get(Instrument, instrument_id)
    if instrument is None:
        raise HTTPException(404, f"No instrument with id {instrument_id}.")
    return instrument


def _detail(session: Session, instrument: Instrument) -> InstrumentDetail:
    override = instrument.override
    return InstrumentDetail(
        **_summary_fields(instrument, scheme_variants(session, instrument)),
        source=instrument.source,
        series=instrument.series,
        listed_on=instrument.listed_on,
        cik=instrument.cik,
        isin_reinvestment=instrument.isin_reinvestment,
        scheme_type=instrument.scheme_type,
        aliases=[Alias.model_validate(a, from_attributes=True) for a in instrument.aliases],
        rule=_classification(rule_classification(instrument)),
        override=None
        if override is None
        else Override(
            **_classification(effective_classification(instrument)).model_dump(),
            note=override.note,
            updated_at=override.updated_at,
        ),
        created_at=instrument.created_at,
        updated_at=instrument.updated_at,
    )


@router.get("/search", operation_id="searchInstruments")
def search(
    session: SessionDep,
    q: Annotated[str, Query(min_length=1, max_length=100, description="Name, symbol or code")],
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 20,
    market: Market | None = None,
    kind: Kind | None = None,
    include_inactive: bool = False,
) -> list[InstrumentSummary]:
    """Find instruments by part of a name, a symbol, an AMFI scheme code or an ISIN."""
    hits = search_instruments(
        session, q, limit=limit, market=market, kind=kind, include_inactive=include_inactive
    )
    return [InstrumentSummary(**_summary_fields(hit.instrument, hit.variants)) for hit in hits]


@router.post("/refresh", operation_id="refreshInstruments")
def refresh(request: Request, payload: RefreshIn | None = None) -> list[RefreshResultOut]:
    """Download the lists and update instruments, as ``friday instruments refresh`` does
    (D-065). Each list is its own transaction; a failed one is reported, not raised."""
    wanted = set(payload.sources) if payload and payload.sources else set(SOURCES)
    results = refresh_instruments(
        request.app.state.session_factory,
        request.app.state.list_fetcher,
        [source for source in SOURCES if source in wanted],  # NSE before AMFI (refresh order)
    )
    return [
        RefreshResultOut(**{name: getattr(result, name) for name in RefreshResultOut.model_fields})
        for result in results
    ]


@router.get("/sources", operation_id="getInstrumentSources")
def sources(session: SessionDep) -> list[SourceOut]:
    """When each instrument list was last refreshed."""
    return [
        SourceOut(
            source=status.source,
            active_instruments=status.active_instruments,
            last_run=_import_run(status.last_run),
            last_success=_import_run(status.last_success),
        )
        for status in source_statuses(session)
    ]


@router.get("/{instrument_id}", operation_id="getInstrument")
def get_instrument(session: SessionDep, instrument_id: int) -> InstrumentDetail:
    return _detail(session, _get(session, instrument_id))


@router.put("/{instrument_id}/classification", operation_id="setClassification")
def put_classification(
    session: SessionDep, instrument_id: int, payload: OverrideIn
) -> InstrumentDetail:
    """Set my own allocation split and exposure. It wins over the rules and survives refresh."""
    instrument = _get(session, instrument_id)
    allocation: dict[str, Decimal] = {}
    for share in payload.allocation:
        if share.bucket in allocation:
            raise HTTPException(422, f"{share.bucket} is listed twice.")
        allocation[share.bucket] = share.percent
    try:
        set_override(session, instrument, allocation, payload.exposure, payload.note)
    except InvalidClassification as error:
        raise HTTPException(422, str(error)) from None
    return _detail(session, instrument)


@router.delete("/{instrument_id}/classification", operation_id="clearClassification")
def delete_classification(session: SessionDep, instrument_id: int) -> InstrumentDetail:
    """Go back to the rule-based classification."""
    instrument = _get(session, instrument_id)
    clear_override(session, instrument)
    return _detail(session, instrument)
