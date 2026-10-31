"""Funds side by side: returns, risk and consistency over the dates they share."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from friday.api.deps import SessionDep
from friday.api.schemas import FundRef
from friday.core.compare.schemas import ComparedFund, Comparison
from friday.core.compare.service import CompareError, compare_funds
from friday.core.instruments.models import Instrument

router = APIRouter(tags=["compare"])


class ComparedFundOut(ComparedFund):
    fund: FundRef


class FundComparisonOut(Comparison):
    funds: list[ComparedFundOut]
    benchmark: ComparedFundOut | None


@router.get("/compare/funds", operation_id="compareFunds")
def compare(
    session: SessionDep,
    ids: Annotated[list[int], Query()],
    benchmark_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    rolling_years: int = 3,
) -> FundComparisonOut:
    """Compare funds over the dates they all have, or from ``start`` for the funds that go
    back that far, against ``benchmark_id`` or the default benchmark."""
    try:
        result = compare_funds(
            session,
            ids,
            benchmark_id=benchmark_id,
            start=start,
            end=end,
            rolling_years=rolling_years,
        )
    except LookupError as error:
        raise HTTPException(404, str(error)) from None
    except CompareError as error:
        raise HTTPException(422, str(error)) from None

    def out(fund: ComparedFund) -> ComparedFundOut:
        instrument = session.get(Instrument, fund.instrument_id)
        return ComparedFundOut(
            **fund.model_dump(), fund=FundRef.model_validate(instrument, from_attributes=True)
        )

    return FundComparisonOut(
        **result.model_dump(exclude={"funds", "benchmark"}),
        funds=[out(fund) for fund in result.funds],
        benchmark=out(result.benchmark) if result.benchmark else None,
    )
