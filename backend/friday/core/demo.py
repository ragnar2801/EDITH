"""Made-up data for the dev database (``just dev``), so the app can be run, tested and
screenshotted without my real portfolio.

The funds and their NAVs are real and public (downloaded from AMFI and mfapi); every
purchase, SIP, sale, cash balance and model is invented here.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from friday.core.buckets.service import BucketInput, create_bucket
from friday.core.cash.service import AccountInput, SettingsInput, create_account, update_settings
from friday.core.db import session_scope
from friday.core.holdings.service import (
    BuyInput,
    SaleInput,
    SipInput,
    create_lump_sum,
    create_sip,
    sell,
)
from friday.core.instruments.download import Fetcher
from friday.core.instruments.models import Instrument
from friday.core.instruments.refresh import refresh_instruments
from friday.core.navs.download import NavFetcher
from friday.core.navs.models import FundNav
from friday.core.navs.service import sync_navs, track

FLEXI = "122639"  # Parag Parikh Flexi Cap
NIFTY = "120716"  # UTI Nifty 50 Index
MIDCAP = "147622"  # Motilal Oswal Nifty Midcap 150 Index
GOLD = "119132"  # HDFC Gold ETF Fund of Fund
SHORT = "120754"  # ICICI Prudential Short Term
LIQUID = "143269"  # Parag Parikh Liquid
FUNDS = [FLEXI, NIFTY, MIDCAP, GOLD, SHORT, LIQUID]


class DemoError(RuntimeError):
    pass


def _nav_day(session: Session, instrument_id: int, day: date) -> date:
    """The first NAV date on or after ``day``, so buys and sales land on a priced day."""
    found = session.scalar(
        select(FundNav.nav_date)
        .where(FundNav.instrument_id == instrument_id, FundNav.nav_date >= day)
        .order_by(FundNav.nav_date)
        .limit(1)
    )
    if found is None:
        raise DemoError(f"no NAV on or after {day} for instrument {instrument_id}")
    return found


def make_demo(
    factory: sessionmaker[Session],
    fetcher: Fetcher,
    nav_fetcher: NavFetcher,
    today: date,
) -> None:
    """Fill an empty database with the demo funds, their NAVs and an invented portfolio."""
    with session_scope(factory) as session:
        if session.scalar(select(Instrument.id).limit(1)) is not None:
            raise DemoError("the database isn't empty")

    for result in refresh_instruments(factory, fetcher, ["amfi"]):
        if result.status != "ok":
            raise DemoError(f"AMFI list: {result.message}")

    with session_scope(factory) as session:
        found = {
            instrument.amfi_code: instrument
            for instrument in session.scalars(
                select(Instrument).where(Instrument.amfi_code.in_(FUNDS))
            )
        }
        missing = [code for code in FUNDS if code not in found]
        if missing:
            raise DemoError(f"AMFI no longer lists {', '.join(missing)}")
        for instrument in found.values():
            track(session, instrument)
        ids = {code: instrument.id for code, instrument in found.items()}

    result = sync_navs(factory, nav_fetcher, ids.values())
    if result.status == "failed":
        raise DemoError("couldn't download any NAVs")

    with session_scope(factory) as session:

        def buy(code: str, years_ago: float, amount: int) -> int:
            day = _nav_day(session, ids[code], today - timedelta(days=round(years_ago * 365)))
            return create_lump_sum(session, ids[code], BuyInput(day, Decimal(amount))).id

        buy(FLEXI, 4.2, 150_000)
        nifty = buy(NIFTY, 3.6, 200_000)
        buy(NIFTY, 1.1, 75_000)
        buy(MIDCAP, 2.4, 60_000)
        buy(GOLD, 2.0, 40_000)
        buy(SHORT, 1.5, 50_000)
        buy(LIQUID, 2.8, 120_000)

        create_sip(session, ids[FLEXI], SipInput(Decimal(10_000), 5, today - timedelta(days=1100)))
        create_sip(session, ids[MIDCAP], SipInput(Decimal(5_000), 12, today - timedelta(days=700)))

        sale_day = _nav_day(session, ids[NIFTY], today - timedelta(days=200))
        sell(session, SaleInput(sale_day, [(nifty, Decimal(1500))]))

        long_term = create_bucket(
            session,
            BucketInput(
                name="Long term",
                funds=[
                    (ids[FLEXI], Decimal(40)),
                    (ids[NIFTY], Decimal(30)),
                    (ids[MIDCAP], Decimal(15)),
                    (ids[GOLD], Decimal(10)),
                    (ids[SHORT], Decimal(5)),
                ],
                rebalance="yearly",
            ),
        )
        create_bucket(
            session,
            BucketInput(
                name="Steady",
                funds=[(ids[NIFTY], Decimal(50)), (ids[SHORT], Decimal(50))],
            ),
        )

        create_account(session, AccountInput("Savings", Decimal(320_000), "deployable"))
        create_account(session, AccountInput("Emergency FD", Decimal(200_000), "emergency"))
        create_account(session, AccountInput("Bills", Decimal(60_000), "reserved"))
        update_settings(
            session,
            SettingsInput(
                target_bucket_id=long_term.id,
                emergency_goal=Decimal(600_000),
                emergency_fund_id=ids[LIQUID],
                stagger_fund_id=ids[LIQUID],
                stagger_threshold=Decimal(500_000),
                stagger_months=6,
                min_per_fund=Decimal(500),
            ),
        )
