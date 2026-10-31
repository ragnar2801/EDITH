"""Classification rules, with the expected split worked out by hand per case."""

from decimal import Decimal

import pytest

from friday.core.instruments.classify import (
    asset_class,
    classify_fund,
    classify_nse_etf,
    classify_us,
)


def split(**shares: int) -> dict[str, Decimal]:
    return {bucket: Decimal(pct) for bucket, pct in shares.items()}


@pytest.mark.parametrize(
    ("category", "name", "allocation", "exposure"),
    [
        ("Equity Scheme - Flexi Cap Fund", "Parag Parikh Flexi Cap Fund", split(equity=100), "IN"),
        (
            "Equity Schemes - ELSS- Tax Saver Fund",
            "Axis ELSS Tax Saver Fund",
            split(equity=100),
            "IN",
        ),
        ("Debt Scheme - Liquid Fund", "HDFC Liquid Fund", split(debt=100), "IN"),
        ("Income/Debt Oriented Schemes - Gilt Fund", "SBI Magnum Gilt Fund", split(debt=100), "IN"),
        ("Income", "Nippon India Fixed Horizon Fund XXXVI- Series 9", split(debt=100), "IN"),
        ("Growth", "SBI Long Term Advantage Fund Series IV", split(equity=100), "IN"),
        # Hybrid defaults
        (
            "Hybrid Scheme - Aggressive Hybrid Fund",
            "ICICI Prudential Equity & Debt Fund",
            split(equity=75, debt=25),
            "IN",
        ),
        (
            "Hybrid Schemes - Balanced Hybrid Fund",
            "X Balanced Fund",
            split(equity=50, debt=50),
            "IN",
        ),
        (
            "Hybrid Scheme - Conservative Hybrid Fund",
            "X Regular Savings Fund",
            split(equity=20, debt=80),
            "IN",
        ),
        (
            "Hybrid Scheme - Dynamic Asset Allocation or Balanced Advantage",
            "X BAF",
            split(equity=50, debt=50),
            "IN",
        ),
        (
            "Hybrid Schemes - Balanced Advantage Fund/ Dynamic Asset Allocation",
            "X BAF",
            split(equity=50, debt=50),
            "IN",
        ),
        (
            "Hybrid Scheme - Multi Asset Allocation",
            "X Multi Asset Fund",
            split(equity=50, debt=30, gold=20),
            "IN",
        ),
        (
            "Hybrid Scheme - Equity Savings",
            "X Equity Savings Fund",
            split(equity=35, debt=65),
            "IN",
        ),
        ("Hybrid Scheme - Arbitrage Fund", "X Arbitrage Fund", split(debt=100), "IN"),
        (
            "Index Funds - Hybrid Fund",
            "X Nifty 50 and SDL 50:50 Index Fund",
            split(equity=50, debt=50),
            "IN",
        ),
        # Index funds and ETFs: by name where the category doesn't say
        ("Other Scheme - Index Funds", "UTI Nifty 50 Index Fund", split(equity=100), "IN"),
        ("Other Scheme - Index Funds", "Bharat Bond FOF - April 2030", split(debt=100), "IN"),
        ("Other Scheme - Index Funds", "Motilal Oswal S&P 500 Index Fund", split(equity=100), "US"),
        ("Index Funds - Debt Funds", "X CRISIL IBX Gilt Index", split(debt=100), "IN"),
        ("Other Scheme - Gold ETF", "Nippon India ETF Gold BeES", split(gold=100), "IN"),
        (
            "Exchange Traded Funds (ETFs) - Silver ETF",
            "ICICI Prudential Silver ETF",
            split(silver=100),
            "IN",
        ),
        ("Other Scheme - Other ETFs", "Nippon India ETF Nifty 50 BeES", split(equity=100), "IN"),
        (
            "Other Scheme - Other ETFs",
            "Nippon India ETF Nifty 1D Rate Liquid BeES",
            split(debt=100),
            "IN",
        ),
        (
            "Exchange Traded Funds (ETFs) - ETFs investing overseas",
            "Mirae Asset Hang Seng TECH ETF",
            split(equity=100),
            "GLOBAL",
        ),
        # Fund of funds
        (
            "Other Scheme - FoF Overseas",
            "Franklin India Feeder - Franklin U.S. Opportunities Fund",
            split(equity=100),
            "US",
        ),
        (
            "Overseas Fund of Funds - Fund of Funds investing overseas",
            "X Global Innovation FoF",
            split(equity=100),
            "GLOBAL",
        ),
        (
            "Other Scheme - FoF Domestic",
            "Motilal Oswal Nasdaq 100 Fund of Fund",
            split(equity=100),
            "US",
        ),
        ("Other Scheme - FoF Domestic", "SBI Gold Fund", split(gold=100), "IN"),
        ("Other Scheme - FoF Domestic", "X Asset Allocator FoF", {}, "IN"),  # unclear: unclassified
        # Varies by plan: set by hand
        (
            "Solution Oriented Scheme - Retirement Fund",
            "Axis Retirement Fund - Aggressive Plan",
            {},
            "IN",
        ),
        ("Children's Fund - Childrens' Fund", "Axis Children's Fund", {}, "IN"),
        (
            "Life Cycle Funds - Life Cycle Fund with Maturity of 30 Years",
            "X Life Cycle Fund",
            {},
            "IN",
        ),
        ("Something AMFI adds next year", "X Fund", {}, "IN"),
    ],
)
def test_fund_rules(category: str, name: str, allocation: dict, exposure: str) -> None:
    result = classify_fund(category, name)
    assert (result.allocation, result.exposure) == (allocation, exposure)


@pytest.mark.parametrize(
    ("underlying_type", "underlying", "allocation", "exposure"),
    [
        ("EQUITY", "Nifty 50", split(equity=100), "IN"),
        ("DEBT", "Government Securities", split(debt=100), "IN"),
        ("COMMODITY", "Gold GOLD", split(gold=100), "IN"),
        ("COMMODITY", "Silver SILVER", split(silver=100), "IN"),
        ("GLOBAL INDICES", "Nasdaq100", split(equity=100), "US"),
        ("GLOBAL INDICES", "Hang Seng Index", split(equity=100), "GLOBAL"),
        ("Hybrid", "Nifty 50 and G-Sec", split(equity=50, debt=50), "IN"),
    ],
)
def test_nse_etf_rules(
    underlying_type: str, underlying: str, allocation: dict, exposure: str
) -> None:
    result = classify_nse_etf(underlying_type, underlying, "X")
    assert (result.allocation, result.exposure) == (allocation, exposure)


@pytest.mark.parametrize(
    ("kind", "name", "bucket", "exposure"),
    [
        ("stock", "Apple Inc.", "equity", "US"),
        ("stock", "Infosys Limited American Depositary Shares", "equity", "GLOBAL"),
        ("etf", "Vanguard S&P 500 ETF", "equity", "US"),
        ("etf", "Vanguard Total Bond Market ETF", "debt", "US"),
        ("etf", "iShares 20+ Year Treasury Bond ETF", "debt", "US"),
        ("etf", "SPDR Gold Shares", "gold", "US"),
        ("etf", "iShares Silver Trust", "silver", "US"),
        ("etf", "Vanguard Real Estate ETF", "other", "US"),
        ("etf", "iShares Bitcoin Trust ETF", "other", "US"),
        ("etf", "iShares MSCI India ETF", "equity", "IN"),
        ("etf", "Vanguard FTSE Emerging Markets ETF", "equity", "GLOBAL"),
        ("etf", "Vanguard Total International Stock ETF", "equity", "GLOBAL"),
        ("etf", "JPMorgan Equity Premium Income ETF", "equity", "US"),  # "income" isn't debt
    ],
)
def test_us_rules(kind: str, name: str, bucket: str, exposure: str) -> None:
    result = classify_us(kind, name)
    assert (result.asset_class, result.exposure) == (bucket, exposure)


def test_asset_class_labels() -> None:
    assert asset_class(split(equity=100)) == "equity"
    assert asset_class(split(equity=75, debt=25)) == "hybrid"
    assert asset_class({}) == "unclassified"
