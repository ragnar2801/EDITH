"""What a backtest is asked to do, and what it returns (D-048, D-049).

These models are both the API's request and response bodies and what a stored run keeps,
so a saved run reads back exactly as it was shown. Amounts are exact decimal strings.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from friday.core.schema_types import Amount, Figure, Nav, Percent, Ratio, Units

Frequency = Literal["weekly", "monthly", "quarterly"]
Rebalance = Literal["none", "monthly", "quarterly", "yearly"]
PositiveAmount = Annotated[Amount, Field(gt=0)]
PositiveUnits = Annotated[Units, Field(gt=0)]


class CommonParams(BaseModel):
    start: date | None = None
    """Start no earlier than this date. The run starts when every fund has a NAV."""
    end: date | None = None
    risk_free_pct: Annotated[Percent, Field(ge=0, le=50)] = Decimal(0)
    """Yearly risk-free rate for Sharpe and Sortino, e.g. "6.5"."""

    @model_validator(mode="after")
    def _dates_in_order(self):
        if self.start and self.end and self.start > self.end:
            raise ValueError("start must be on or before end")
        return self


class RegularParams(CommonParams):
    """A lump sum, optionally rebalanced to the bucket's weights."""

    strategy: Literal["regular"]
    capital: PositiveAmount
    rebalance: Rebalance | None = None
    """Leave out to use the bucket's own policy."""


class SipParams(CommonParams):
    strategy: Literal["sip"]
    amount: PositiveAmount
    frequency: Frequency = "monthly"


class SwpParams(CommonParams):
    strategy: Literal["swp"]
    corpus: PositiveAmount
    amount: PositiveAmount
    frequency: Frequency = "monthly"


class Position(BaseModel):
    """Hold a fund from ``entry`` to ``exit`` (or to the end), buying for ``amount``."""

    instrument_id: int
    entry: date
    exit: date | None = None
    amount: PositiveAmount

    @model_validator(mode="after")
    def _exit_after_entry(self):
        if self.exit and self.exit < self.entry:
            raise ValueError("exit must be on or after entry")
        return self


class CustomTradeIn(BaseModel):
    """One buy or sell: by amount, by units, or (sells only) everything held."""

    instrument_id: int
    date: date
    side: Literal["buy", "sell"]
    amount: PositiveAmount | None = None
    units: PositiveUnits | None = None
    sell_all: bool = False

    @model_validator(mode="after")
    def _one_quantity(self):
        if self.sell_all:
            if self.side != "sell":
                raise ValueError("only a sell can sell everything")
        elif (self.amount is None) == (self.units is None):
            raise ValueError("give either an amount or units")
        return self


class CustomParams(CommonParams):
    """My own timeline over the bucket's funds; weights don't apply."""

    strategy: Literal["custom"]
    positions: list[Position] = Field(default_factory=list)
    trades: list[CustomTradeIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def _something_to_do(self):
        if not self.positions and not self.trades:
            raise ValueError("add at least one position or trade")
        return self


BacktestParams = Annotated[
    RegularParams | SipParams | SwpParams | CustomParams, Field(discriminator="strategy")
]
Strategy = Literal["regular", "sip", "swp", "custom"]


class CurvePoint(BaseModel):
    date: date
    value: Amount
    invested: Amount
    """Money put in so far. A same-day sell and buy (a switch) nets off."""
    withdrawn: Amount
    """Money taken out so far, after the same netting."""
    index: Ratio
    """Time-weighted growth of 100: the investment's own performance, without money flows."""


class MetricsOut(BaseModel):
    start_date: date
    end_date: date
    years: Figure
    start_value: Amount
    end_value: Amount
    total_invested: Amount
    total_withdrawn: Amount
    absolute_return_pct: Percent | None
    """(End value + money taken out − money put in) ÷ money put in."""
    cagr_pct: Percent | None
    """Time-weighted yearly growth, comparable across strategies."""
    xirr_pct: Percent | None
    """Money-weighted yearly return of the actual cash flows."""
    max_drawdown_pct: Percent
    volatility_pct: Percent
    sharpe: Figure | None
    sortino: Figure | None
    depletion_date: date | None


class FundOutcomeOut(BaseModel):
    instrument_id: int
    name: str
    weight: Percent | None
    units: Units
    end_value: Amount
    invested: Amount | None
    proceeds: Amount | None
    pnl: Amount | None
    pnl_pct: Percent | None


class TradeOut(BaseModel):
    date: date
    instrument_id: int
    name: str
    side: Literal["buy", "sell"]
    units: Units
    nav: Nav
    amount: Amount


class BenchmarkOut(BaseModel):
    instrument_id: int
    name: str
    curve: list[CurvePoint]
    metrics: MetricsOut


class BacktestResult(BaseModel):
    strategy: Strategy
    curve: list[CurvePoint]
    metrics: MetricsOut
    funds: list[FundOutcomeOut]
    trades: list[TradeOut]
    """Custom runs only: what was executed, on which NAV date."""
    benchmark: BenchmarkOut | None
    """The same money in and out, in the benchmark fund instead (D-048)."""
    warnings: list[str]


class IntervalOut(BaseModel):
    start_date: date
    end_date: date
    start_value: Amount
    end_value: Amount
    return_pct: Percent | None
    """Money-weighted (Modified Dietz): money put in or taken out isn't gain."""
    max_drawdown_pct: Percent
    invested: Amount
    withdrawn: Amount
    benchmark_return_pct: Percent | None
