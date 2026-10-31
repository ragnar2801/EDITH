"""What a backtest is asked to do, and what it returns.

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


class SplitFund(BaseModel):
    instrument_id: int
    weight: Percent


class WeightedParams(CommonParams):
    split: list[SplitFund] | None = None
    """Run these funds and weights instead of the bucket's; the bucket isn't changed."""


class RegularParams(WeightedParams):
    """A lump sum, optionally rebalanced to the bucket's weights."""

    strategy: Literal["regular"]
    capital: PositiveAmount
    rebalance: Rebalance | None = None
    """Leave out to use the bucket's own policy."""


class SipParams(WeightedParams):
    strategy: Literal["sip"]
    amount: PositiveAmount
    frequency: Frequency = "monthly"


class SwpParams(WeightedParams):
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
    """The same money in and out, in the benchmark fund instead."""
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


class WeightChange(BaseModel):
    instrument_id: int
    name: str
    before: Percent | None
    """None: the fund wasn't in the earlier run."""
    after: Percent | None
    """None: the fund isn't in this run."""


class ComparisonOut(BaseModel):
    """This run less an earlier one: rupees for the final value, points for ratios."""

    against: int
    same_settings: bool
    """Everything but the split was the same, so the split is what changed."""
    end_value: Amount
    xirr_pct: Percent | None
    cagr_pct: Percent | None
    absolute_return_pct: Percent | None
    max_drawdown_pct: Percent
    volatility_pct: Percent
    sharpe: Figure | None
    weights: list[WeightChange]
    """Only the funds whose weight changed, in this run's order then the dropped ones."""


Goal = Literal["xirr", "drawdown", "sharpe"]


class SearchSettings(BaseModel):
    """Which splits to try and what makes one better."""

    goal: Goal = "xirr"
    """Highest XIRR, lowest max drawdown, or best Sharpe."""
    step: Annotated[int, Field(ge=1, le=50)] = 5
    """Weights go up in steps of this many percent; it must divide 100."""
    min_weight: Annotated[int, Field(ge=0, le=100)] = 0
    """Lowest weight for a fund; 0 lets a fund drop out."""
    max_weight: Annotated[int, Field(ge=1, le=100)] = 100
    max_drawdown_pct: Annotated[Percent, Field(gt=0)] | None = None
    """Leave out splits that fell further than this."""
    min_xirr_pct: Percent | None = None
    """Leave out splits with a lower XIRR than this."""

    @model_validator(mode="after")
    def _a_grid(self):
        if 100 % self.step:
            raise ValueError("step must divide 100 (1, 2, 4, 5, 10, 20, 25 or 50)")
        if self.min_weight > self.max_weight:
            raise ValueError("the lowest weight must be at most the highest")
        return self


SearchParams = Annotated[RegularParams | SipParams, Field(discriminator="strategy")]


class CandidateFund(BaseModel):
    instrument_id: int
    name: str
    weight: Percent


class Candidate(BaseModel):
    """A split with its figures from the exact engine."""

    funds: list[CandidateFund]
    """Funds with a weight above 0, in the model's order."""
    metrics: MetricsOut


class SearchPoint(BaseModel):
    """One split, for drawing: rounded figures from the search."""

    xirr_pct: Percent | None
    max_drawdown_pct: Percent
    eligible: bool
    """Within the limits."""


class OptimiseOut(BaseModel):
    start_date: date
    end_date: date
    tried: int
    eligible: int
    points: list[SearchPoint]
    model: Candidate
    """The model's own split, for comparison."""
    benchmark: BenchmarkOut | None
    """The same money in the benchmark fund; its curve is left empty."""
    top: list[Candidate]
    """The best splits within the limits, best first."""
    warnings: list[str]
