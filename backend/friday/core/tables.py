"""Every ORM model, imported in one place so Alembic sees the whole schema."""

from friday.core.backtest.models import BacktestRun
from friday.core.buckets.models import Bucket
from friday.core.cash.models import CashAccount, PlanSettings
from friday.core.fm.models import FmImport
from friday.core.holdings.models import Lot, LotSale, Sip
from friday.core.instruments.models import (
    ClassificationOverride,
    Instrument,
    InstrumentAlias,
    InstrumentImport,
)
from friday.core.models.models import Model, ModelFund
from friday.core.navs.models import FundNav, NavSync, TrackedFund

__all__ = [
    "BacktestRun",
    "Bucket",
    "Model",
    "ModelFund",
    "CashAccount",
    "ClassificationOverride",
    "FmImport",
    "FundNav",
    "Instrument",
    "InstrumentAlias",
    "InstrumentImport",
    "Lot",
    "LotSale",
    "NavSync",
    "PlanSettings",
    "Sip",
    "TrackedFund",
]
