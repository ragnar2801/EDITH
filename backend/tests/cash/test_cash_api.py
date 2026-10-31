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


def buy(api: TestClient, fund_id: int, amount: str) -> None:
    response = api.post(
        "/api/v1/lots",
        json={"instrument_id": fund_id, "buy_date": DAY.isoformat(), "amount": amount},
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
def setup(api: TestClient, funds) -> int:
    """₹60k of Parag Parikh and ₹20k of the Nifty fund in a 60 / 40 model, ₹50k in the
    arbitrage fund as emergency money, ₹10k in a fund outside the model, and cash."""
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
    buy(api, funds[PARAG], "60000")  # 600 units at 100
    buy(api, funds[NIFTY], "20000")  # 100 units at 200
    buy(api, funds[ARBITRAGE], "50000")  # 2,500 units at 20
    buy(api, funds[NIFTY_REGULAR], "10000")
    account(api, "Savings", "50000", "emergency")
    account(api, "Salary", "100000", "deployable")
    account(api, "Car fund", "200000", "reserved")
    saved = api.put(
        "/api/v1/plan/settings",
        json=settings(target_model_id=model["id"], emergency_fund_id=funds[ARBITRAGE]),
    )
    assert saved.status_code == 200, saved.text
    return model["id"]


def test_cash_totals_and_emergency_status(api: TestClient, setup) -> None:
    cash = api.get("/api/v1/cash").json()

    assert [a["name"] for a in cash["accounts"]] == ["Car fund", "Salary", "Savings"]
    assert (cash["deployable"], cash["reserved"]) == ("100000.00", "200000.00")
    emergency = cash["emergency"]
    assert (emergency["cash"], emergency["fund"]["value"]) == ("50000.00", "50000.00")
    assert (emergency["total"], emergency["shortfall"]) == ("100000.00", "50000.00")


def test_plan_tops_up_emergency_then_fills_the_split(api: TestClient, setup, funds) -> None:
    response = api.post("/api/v1/plan", json={})  # blank: all deployable cash

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
            target_model_id=setup,
            emergency_fund_id=funds[ARBITRAGE],
            stagger_fund_id=funds[ARBITRAGE],
        ),
    )

    plan = api.post("/api/v1/plan", json={"amount": "650000"}).json()

    assert plan["to_funds"] == "600000.00"  # after the ₹50k emergency top-up
    assert plan["stagger_fund"]["amfi_code"] == ARBITRAGE
    assert len(plan["months"]) == 6
    assert plan["months"][0]["month"] == today().replace(day=1).isoformat()
    assert sum(Decimal(m["total"]) for m in plan["months"]) == Decimal(plan["invested"])


def test_settings_rules(api: TestClient, setup, funds) -> None:
    clash = api.put(
        "/api/v1/plan/settings",
        json=settings(target_model_id=setup, emergency_fund_id=funds[PARAG]),
    )
    assert clash.status_code == 422
    assert "emergency money can't be part of the split" in clash.json()["detail"]

    stock = api.put("/api/v1/plan/settings", json=settings(stagger_fund_id=funds["INFY"]))
    assert stock.status_code == 422

    # Deleting the target model clears it; the plan then asks for one.
    assert api.delete(f"/api/v1/models/{setup}").status_code == 204
    assert api.get("/api/v1/plan/settings").json()["target_model"] is None
    missing = api.post("/api/v1/plan", json={})
    assert missing.status_code == 422
    assert "target split" in missing.json()["detail"]


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
