"""Classification rules: allocation split and exposure region for each instrument.

Rules are deliberately simple and readable. Anything they get wrong is fixed with a
manual override, which always wins and survives refresh.
"""

import re
from dataclasses import dataclass, field
from decimal import Decimal

EXPOSURES = ("IN", "US", "GLOBAL")


@dataclass(frozen=True)
class Classification:
    allocation: dict[str, Decimal] = field(default_factory=dict)  # empty = unclassified
    exposure: str = "IN"

    @property
    def asset_class(self) -> str:
        return asset_class(self.allocation)


def asset_class(allocation: dict[str, Decimal]) -> str:
    """One label for an allocation: its asset, ``hybrid`` if split, or ``unclassified``."""
    shares = [asset for asset, pct in allocation.items() if pct]
    if not shares:
        return "unclassified"
    return shares[0] if len(shares) == 1 else "hybrid"


def _split(**shares: int) -> dict[str, Decimal]:
    return {asset: Decimal(pct) for asset, pct in shares.items()}


EQUITY = _split(equity=100)
DEBT = _split(debt=100)
GOLD = _split(gold=100)
SILVER = _split(silver=100)
OTHER = _split(other=100)
UNCLASSIFIED: dict[str, Decimal] = {}

# Hybrid fund defaults, near the middle of SEBI's ranges for each category.
HYBRID_DEFAULTS: list[tuple[str, dict[str, Decimal]]] = [
    ("arbitrage", DEBT),  # hedged equity: behaves like debt, whatever its tax treatment
    ("aggressive hybrid", _split(equity=75, debt=25)),
    ("balanced hybrid", _split(equity=50, debt=50)),
    ("conservative hybrid", _split(equity=20, debt=80)),
    ("balanced advantage", _split(equity=50, debt=50)),
    ("dynamic asset allocation", _split(equity=50, debt=50)),
    ("multi asset", _split(equity=50, debt=30, gold=20)),
    ("equity savings", _split(equity=35, debt=65)),
    ("hybrid", _split(equity=50, debt=50)),  # any other hybrid: index funds, ETFs
]


def _words(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


GOLD_WORDS = _words(r"\bgold")
SILVER_WORDS = _words(r"\bsilver")
DEBT_WORDS = _words(
    r"\b(gilt|g-?secs?|sdl|bonds?|debt|liquid|money market|overnight|t-?bills?|treasury"
    r"|1d rate|crisil[- ]?ibx|target maturity|constant maturity|fixed income"
    r"|aggregate|municipal|muni|tips|mortgage|floating rate|high yield|clo|cash)\b"
)
EQUITY_WORDS = _words(
    r"\b(equity|nifty|sensex|bse|cap|bluechip|flexi|elss|index|nasdaq|s&p|shares?)\b"
)
OTHER_WORDS = _words(r"\b(reits?|real estate|bitcoin|ether(eum)?|crypto|commodity)\b")
US_WORDS = _words(r"nasdaq|s&p ?500|\bnyse|fang|\bu\.?s\.?\b|\busa\b|\bamerica|\bdow jones|russell")
GLOBAL_WORDS = _words(
    r"global|international|\bworld|overseas|emerging|hang ?seng|japan|china|taiwan"
    r"|europe|\basia|developed|ex-?us\b|eafe|\bacwi\b|brazil|korea|germany"
)
INDIA_WORDS = _words(r"\bindia")


def indian_exposure(*texts: str, default: str = "IN") -> str:
    """Where an India-listed fund invests, from its name: US, GLOBAL or the default."""
    joined = " ".join(texts)
    if US_WORDS.search(joined):
        return "US"
    if GLOBAL_WORDS.search(joined):
        return "GLOBAL"
    return default


def us_exposure(name: str) -> str:
    """Where a US-listed ETF invests, from its name."""
    if INDIA_WORDS.search(name):
        return "IN"
    if GLOBAL_WORDS.search(name):
        return "GLOBAL"
    return "US"


def _by_name(name: str, default: dict[str, Decimal]) -> dict[str, Decimal]:
    """Asset class from keywords in a fund or ETF name. Order matters: gold before debt, etc."""
    if GOLD_WORDS.search(name):
        return GOLD
    if SILVER_WORDS.search(name):
        return SILVER
    if OTHER_WORDS.search(name):
        return OTHER
    if DEBT_WORDS.search(name):
        return DEBT
    return default


def classify_nse_stock() -> Classification:
    return Classification(EQUITY, "IN")


def classify_nse_etf(underlying_type: str, underlying: str, name: str) -> Classification:
    """NSE's ETF list says what each ETF holds in its *ETF Underlying* column."""
    kind = underlying_type.strip().lower()
    text_ = f"{underlying} {name}"
    if kind == "equity":
        return Classification(EQUITY, indian_exposure(text_))
    if kind == "debt":
        return Classification(DEBT, "IN")
    if kind == "commodity":
        return Classification(_by_name(text_, OTHER), "IN")
    if kind == "global indices":
        return Classification(EQUITY, indian_exposure(text_, default="GLOBAL"))
    if kind == "hybrid":
        return Classification(_split(equity=50, debt=50), "IN")
    return Classification(_by_name(text_, EQUITY), indian_exposure(text_))


def classify_fund(category: str, name: str) -> Classification:
    """Indian mutual fund, from its AMFI category header (e.g. "Equity Scheme - Flexi Cap
    Fund") and, where the category doesn't say, its name."""
    cat = " ".join(category.lower().split())
    overseas = "overseas" in cat
    exposure = indian_exposure(name, default="GLOBAL" if overseas else "IN")

    if any(word in cat for word in ("solution oriented", "retirement", "children", "life cycle")):
        return Classification(UNCLASSIFIED, exposure)  # varies by plan: set by hand
    if "gold etf" in cat:
        return Classification(GOLD, exposure)
    if "silver etf" in cat:
        return Classification(SILVER, exposure)
    if "index funds - equity" in cat or "equity etf" in cat:
        return Classification(EQUITY, exposure)
    if "index funds - debt" in cat or "debt etf" in cat:
        return Classification(DEBT, exposure)
    for words, split in HYBRID_DEFAULTS:
        if words in cat:
            return Classification(split, exposure)
    if "fof" in cat or "fund of funds" in cat:
        if overseas:
            return Classification(_by_name(name, EQUITY), exposure)
        # Domestic fund-of-funds hold anything: only classify what the name makes clear.
        by_name = _by_name(name, UNCLASSIFIED)
        if not by_name and EQUITY_WORDS.search(name):
            by_name = EQUITY
        return Classification(by_name, exposure)
    if "etf" in cat or "index fund" in cat:
        return Classification(_by_name(name, EQUITY), exposure)
    if any(word in cat for word in ("debt", "income", "gilt", "liquid", "money market")):
        return Classification(DEBT, exposure)
    if any(word in cat for word in ("equity", "elss", "growth")):
        return Classification(EQUITY, exposure)
    return Classification(UNCLASSIFIED, exposure)


def classify_us(kind: str, name: str) -> Classification:
    if kind == "etf":
        return Classification(_by_name(name, EQUITY), us_exposure(name))
    if "american depositary" in name.lower():
        return Classification(EQUITY, "GLOBAL")  # a foreign company listed in the US
    return Classification(EQUITY, "US")
