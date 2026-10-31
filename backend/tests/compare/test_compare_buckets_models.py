"""GET /compare/buckets and /compare/models: each one as if it were a fund."""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from navs.conftest import NIFTY, PARAG
from sqlalchemy.orm import Session, sessionmaker

from friday.core.db import session_scope
from friday.core.navs.models import FundNav

NAVS = {
    PARAG: {"2024-01-01": "100", "2025-01-01": "125", "2025-07-01": "150", "2026-01-01": "160"},
    NIFTY: {"2024-01-01": "200", "2025-01-01": "250", "2025-07-01": "300", "2026-01-01": "300"},
}


def post(api: TestClient, url: str, body: dict) -> dict:
    response = api.post(url, json=body)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def api(client: TestClient, funds: dict[str, int], factory: sessionmaker[Session]) -> TestClient:
    """A 60 / 40 model of Parag Parikh and the Nifty 50 index fund, and a Retirement bucket
    following it: ₹10,000 of Parag Parikh at 100, ₹5,000 more at 125, 50 units sold at 150."""
    with session_scope(factory) as session:
        for code, navs in NAVS.items():
            for day, nav in navs.items():
                session.add(
                    FundNav(
                        instrument_id=funds[code],
                        nav_date=date.fromisoformat(day),
                        nav=Decimal(nav),
                        source="amfi",
                    )
                )
    split = [
        {"instrument_id": funds[PARAG], "weight": "60"},
        {"instrument_id": funds[NIFTY], "weight": "40"},
    ]
    model = post(client, "/api/v1/models", {"name": "Core", "funds": split})
    post(client, "/api/v1/models", {"name": "Index", "funds": [{**split[1], "weight": "100"}]})
    bucket = post(client, "/api/v1/buckets", {"name": "Retirement", "model_id": model["id"]})
    post(client, "/api/v1/buckets", {"name": "Empty"})
    buy = {"instrument_id": funds[PARAG], "bucket_id": bucket["id"]}
    post(client, "/api/v1/lots", {**buy, "buy_date": "2024-01-01", "amount": "10000"})
    held = post(client, "/api/v1/lots", {**buy, "buy_date": "2025-01-01", "amount": "5000"})
    post(
        client,
        "/api/v1/sales",
        {"sale_date": "2025-07-01", "lots": [{"lot_id": held["lots"][0]["id"], "units": "50"}]},
    )
    return client


def ids(api: TestClient, kind: str) -> dict[str, int]:
    return {row["name"]: row["id"] for row in api.get(f"/api/v1/{kind}").json()}


def test_a_bucket_grows_like_its_funds_whenever_the_money_went_in(api: TestClient) -> None:
    buckets = ids(api, "buckets")

    response = api.get(
        "/api/v1/compare/buckets", params={"ids": [buckets["Retirement"], buckets["Empty"]]}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    retirement, empty = body["items"]
    assert (retirement["bucket"]["name"], retirement["model"]["name"]) == ("Retirement", "Core")
    # Parag Parikh went 100 → 160, so ₹10,000 at the start is ₹16,000 at the end.
    assert retirement["window"]["growth"][-1] == {"date": "2026-01-01", "value": "16000.00"}
    assert retirement["window"]["return_pct"] == "60.00"
    # 90 units at 160 + 7,500 taken out − 15,000 put in, as Portfolio shows it.
    assert retirement["money"] == {
        "invested": "15000.00",
        "value": "14400.00",
        "gain": "6900.00",
        "return_pct": "46.00",
        "xirr_pct": retirement["money"]["xirr_pct"],
    }
    assert (empty["first"], empty["window"], empty["money"]) == (None, None, None)
    assert any("Empty has no purchases" in warning for warning in body["warnings"])
    assert body["benchmark"]["fund"]["amfi_code"] == NIFTY


def test_a_model_is_a_lump_sum_split_by_its_weights(api: TestClient) -> None:
    models = ids(api, "models")

    response = api.get("/api/v1/compare/models", params={"ids": [models["Core"], models["Index"]]})

    assert response.status_code == 200, response.text
    body = response.json()
    core, index = body["items"]
    assert (core["model"]["name"], core["rebalance"]) == ("Core", "none")
    # 60 units of Parag at 100 and 20 of the Nifty fund at 200: 60 × 160 + 20 × 300.
    assert core["window"]["growth"][-1] == {"date": "2026-01-01", "value": "15600.00"}
    assert index["window"]["growth"][-1] == {"date": "2026-01-01", "value": "15000.00"}
    pairs = {(pair["a"], pair["b"]) for pair in body["correlation"]}
    assert (models["Core"], 0) in pairs  # 0 is the benchmark


def test_unknown_buckets_and_models(api: TestClient) -> None:
    assert api.get("/api/v1/compare/buckets", params={"ids": [999]}).status_code == 404
    assert api.get("/api/v1/compare/models", params={"ids": [999]}).status_code == 404
