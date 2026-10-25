"""Every ORM model, imported in one place so Alembic sees the whole schema."""

from friday.core.backtest.models import BacktestRun
from friday.core.buckets.models import Bucket, BucketFund
from friday.core.holdings.models import Lot, LotSale, Sip
from friday.core.instruments.models import (
    ClassificationOverride,
    Instrument,
    InstrumentAlias,
    InstrumentImport,
)
from friday.core.navs.models import FundNav, NavSync, TrackedFund

__all__ = [
    "BacktestRun",
    "Bucket",
    "BucketFund",
    "ClassificationOverride",
    "FundNav",
    "Instrument",
    "InstrumentAlias",
    "InstrumentImport",
    "Lot",
    "LotSale",
    "NavSync",
    "Sip",
    "TrackedFund",
]
