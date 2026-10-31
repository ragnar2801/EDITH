"""Cash accounts, plan settings and the plan through the API."""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from navs.conftest import NIFTY, PARAG
from sqlalchemy.orm import Session, sessionmaker

from friday.core.db import session_scope
from friday.core.holdings.service import today
from friday.core.navs.models import FundNav

ARBITRAGE = "108844"  # Bandhan Arbitrage Fund: where my emergency money sits
NIFTY_REGULAR = "100822"
DAY = date(2026, 10, 23)
NAVS = {PARAG: "100", NIFTY: "200", ARBITRAGE: "20", NIFTY_REGULAR: "50"}


@pytest.fixture
def api(client: TestClient, funds: dict[str, int], factory: sessionmaker[Session]) -> TestClient:
    with session_scope(factory) as session:
        for code, nav in NAVS.items():
            session.add(
                FundNav(instrument_id=funds[code], nav_date=DAY, nav=Decimal(nav), source="amfi")
            )
    return client


def buy(api: TestClient, fund_id: int, amount: str, bucket_id: int | None = None) -> None:
    response = api.post(
        "/api/v1/lots",
        json={
            "instrument_id": fund_id,
            "buy_date": DAY.isoformat(),
            "amount": amount,
            "bucket_id": bucket_id,
        },
    )
    assert response.status_code == 201, response.text


def account(api: TestClient, name: str, balance: str, earmark: str) -> dict:
    response = api.post(
        "/api/v1/cash/accounts", json={"name": name, "balance": balance, "earmark": earmark}
    )
    assert response.status_code == 201, response.text
    return response.json()


def settings(**extra) -> dict:
    return {
        "emergency_goal": "150000",
        "stagger_threshold": "500000",
        "stagger_months": 6,
        "min_per_fund": "500",
        **extra,
    }


@pytest.fixture
def setup(api: TestClient, funds) -> dict:
    """A Retirement bucket following a 60 / 40 model, holding ₹60k of Parag Parikh, ₹20k of
    the Nifty fund and ₹10k of a fund outside the model; ₹50k in the arbitrage fund as
    emergency money, in no bucket; and cash."""
    model = api.post(
        "/api/v1/models",
        json={
            "name": "Core",
            "funds": [
                {"instrument_id": funds[PARAG], "weight": "60"},
                {"instrument_id": funds[NIFTY], "weight": "40"},
            ],
        },
    ).json()
    bucket = api.post("/api/v1/buckets", json={"name": "Retirement", "model_id": model["id"]})
    assert bucket.status_code == 201, bucket.text
    bucket_id = bucket.json()["id"]
    buy(api, funds[PARAG], "60000", bucket_id)  # 600 units at 100
    buy(api, funds[NIFTY], "20000", bucket_id)  # 100 units at 200
    buy(api, funds[ARBITRAGE], "50000")  # 2,500 units at 20
    buy(api, funds[NIFTY_REGULAR], "10000", bucket_id)
    account(api, "Savings", "50000", "emergency")
    account(api, "Salary", "100000", "deployable")
    account(api, "Car fund", "200000", "reserved")
    saved = api.put(
        "/api/v1/plan/settings",
        json=settings(emergency_fund_id=funds[ARBITRAGE]),
    )
    assert saved.status_code == 200, saved.text
    return {"model": model["id"], "bucket": bucket_id}


def test_cash_totals_and_emergency_status(api: TestClient, setup) -> None:
    cash = api.get("/api/v1/cash").json()

    assert [a["name"] for a in cash["accounts"]] == ["Car fund", "Salary", "Savings"]
    assert (cash["deployable"], cash["reserved"]) == ("100000.00", "200000.00")
    emergency = cash["emergency"]
    assert (emergency["cash"], emergency["fund"]["value"]) == ("50000.00", "50000.00")
    assert (emergency["total"], emergency["shortfall"]) == ("100000.00", "50000.00")


def test_plan_tops_up_emergency_then_fills_the_split(api: TestClient, setup, funds) -> None:
    response = api.post("/api/v1/plan", json={"bucket_id": setup["bucket"]})  # all deployable

    assert response.status_code == 200, response.text
    plan = response.json()
    # ₹1L: ₹50k tops the emergency money up to its ₹1.5L goal. The other ₹50k: Parag is
    # at 60k ÷ 60 = 1,000 and Nifty at 20k ÷ 40 = 500, so both rise to (50k + 80k) ÷ 100
    # = 1,300: Parag 78k (+18k) and Nifty 52k (+32k), exactly 60 / 40.
    assert (plan["amount"], plan["emergency_topup"], plan["to_funds"]) == (
        "100000.00",
        "50000.00",
        "50000.00",
    )
    assert (plan["bucket"]["name"], plan["model"]["name"]) == ("Retirement", "Core")
    rows = [
        (f["fund"]["amfi_code"], f["value_now"], f["share_now"], f["invest"], f["share_after"])
        for f in plan["funds"]
    ]
    assert rows == [
        (PARAG, "60000.00", "75.00", "18000.00", "60.00"),
        (NIFTY, "20000.00", "25.00", "32000.00", "40.00"),
    ]
    assert (plan["invested"], plan["left"], plan["months"]) == ("50000.00", "0.00", [])
    assert [(f["fund"]["amfi_code"], f["value"]) for f in plan["ignored"]] == [
        (NIFTY_REGULAR, "10000.00")
    ]
    # Emergency money is never in the split, and its fund isn't listed as ignored.
    assert funds[ARBITRAGE] not in [f["fund"]["id"] for f in plan["funds"] + plan["ignored"]]


def test_a_large_amount_comes_with_a_stagger_plan(api: TestClient, setup, funds) -> None:
    api.put(
        "/api/v1/plan/settings",
        json=settings(
            emergency_fund_id=funds[ARBITRAGE],
            stagger_fund_id=funds[ARBITRAGE],
        ),
    )

    plan = api.post("/api/v1/plan", json={"bucket_id": setup["bucket"], "amount": "650000"}).json()

    assert plan["to_funds"] == "600000.00"  # after the ₹50k emergency top-up
    assert plan["stagger_fund"]["amfi_code"] == ARBITRAGE
    assert len(plan["months"]) == 6
    assert plan["months"][0]["month"] == today().replace(day=1).isoformat()
    assert sum(Decimal(m["total"]) for m in plan["months"]) == Decimal(plan["invested"])


def test_plan_rules(api: TestClient, setup, funds) -> None:
    api.put("/api/v1/plan/settings", json=settings(emergency_fund_id=funds[PARAG]))
    clash = api.post("/api/v1/plan", json={"bucket_id": setup["bucket"]})
    assert clash.status_code == 422
    assert "emergency money can't be part of the split" in clash.json()["detail"]

    stock = api.put("/api/v1/plan/settings", json=settings(stagger_fund_id=funds["INFY"]))
    assert stock.status_code == 422

    # Deleting the model leaves the bucket without one; the plan then asks for one.
    assert api.delete(f"/api/v1/models/{setup['model']}").status_code == 204
    missing = api.post("/api/v1/plan", json={"bucket_id": setup["bucket"]})
    assert missing.status_code == 422
    assert "Choose a model for Retirement" in missing.json()["detail"]
    assert api.post("/api/v1/plan", json={"bucket_id": 999}).status_code == 422


def test_the_plan_counts_only_what_the_bucket_holds(api: TestClient, setup, funds) -> None:
    buy(api, funds[NIFTY], "500000")  # real money in no bucket

    plan = api.post("/api/v1/plan", json={"bucket_id": setup["bucket"]}).json()

    assert [f["value_now"] for f in plan["funds"]] == ["60000.00", "20000.00"]


def test_a_paper_bucket_plans_and_buys_at_the_latest_nav(api: TestClient, setup, funds) -> None:
    made = api.post(
        "/api/v1/buckets", json={"name": "Try", "model_id": setup["model"], "paper": True}
    )
    paper = made.json()["id"]
    assert api.post("/api/v1/plan", json={"bucket_id": paper}).status_code == 422  # no amount

    plan = api.post("/api/v1/plan", json={"bucket_id": paper, "amount": "1000000"}).json()
    # No emergency top-up and no stagger on paper: the whole amount, 60 / 40, at once.
    assert (plan["emergency_topup"], plan["months"]) == ("0.00", [])
    assert [f["invest"] for f in plan["funds"]] == ["600000.00", "400000.00"]

    bought = api.post("/api/v1/plan/paper", json={"bucket_id": paper, "amount": "1000000"})
    assert bought.status_code == 201, bought.text
    assert (bought.json()["purchases"], bought.json()["invested"]) == (2, "1000000.00")
    lots = api.get(f"/api/v1/holdings/{funds[PARAG]}").json()["lots"]
    on_paper = [lot for lot in lots if lot["bucket"] and lot["bucket"]["paper"]]
    assert [(lot["buy_date"], lot["nav"], lot["units"]) for lot in on_paper] == [
        (DAY.isoformat(), "100", "6000.000")
    ]

    # Paper money isn't real: the real bucket's plan and the totals don't see it.
    real = api.post("/api/v1/plan", json={"bucket_id": setup["bucket"]}).json()
    assert [f["value_now"] for f in real["funds"]] == ["60000.00", "20000.00"]
    assert api.get("/api/v1/portfolio").json()["cost"] == "140000.00"

    refused = api.post("/api/v1/plan/paper", json={"bucket_id": setup["bucket"], "amount": "1"})
    assert refused.status_code == 422
    assert "holds real money" in refused.json()["detail"]


def test_accounts_edit_and_delete(api: TestClient) -> None:
    created = account(api, "Savings", "1000.50", "deployable")

    changed = api.put(
        f"/api/v1/cash/accounts/{created['id']}",
        json={"name": "Savings", "balance": "2000", "earmark": "emergency", "note": "HDFC"},
    ).json()
    assert (changed["balance"], changed["earmark"], changed["note"]) == (
        "2000.00",
        "emergency",
        "HDFC",
    )

    duplicate = api.post(
        "/api/v1/cash/accounts", json={"name": "Savings", "balance": "1", "earmark": "reserved"}
    )
    assert duplicate.status_code == 409
    negative = api.post(
        "/api/v1/cash/accounts", json={"name": "Other", "balance": "-1", "earmark": "reserved"}
    )
    assert negative.status_code == 422

    assert api.delete(f"/api/v1/cash/accounts/{created['id']}").status_code == 204
    assert api.get("/api/v1/cash").json()["accounts"] == []
