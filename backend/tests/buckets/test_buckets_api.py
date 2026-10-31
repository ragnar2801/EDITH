"""Buckets through the API: making and changing them, and moving purchases between them."""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from navs.conftest import NIFTY, PARAG
from sqlalchemy.orm import Session, sessionmaker

from friday.core.buckets.service import fm_bucket
from friday.core.db import session_scope
from friday.core.navs.models import FundNav

DAY = date(2026, 1, 5)


@pytest.fixture
def api(client: TestClient, funds: dict[str, int], factory: sessionmaker[Session]) -> TestClient:
    with session_scope(factory) as session:
        for code in (PARAG, NIFTY):
            session.add(
                FundNav(instrument_id=funds[code], nav_date=DAY, nav=Decimal(50), source="amfi")
            )
    return client


def post(api: TestClient, url: str, body: dict) -> dict:
    response = api.post(url, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def bucket(api: TestClient, name: str, **extra) -> dict:
    return post(api, "/api/v1/buckets", {"name": name, **extra})


def lump(api: TestClient, funds, bucket_id: int | None, code: str = PARAG) -> dict:
    body = {
        "instrument_id": funds[code],
        "buy_date": DAY.isoformat(),
        "amount": "1000",
        "bucket_id": bucket_id,
    }
    return post(api, "/api/v1/lots", body)["lots"][-1]


def model(api: TestClient, funds) -> dict:
    return post(
        api,
        "/api/v1/models",
        {"name": "Core", "funds": [{"instrument_id": funds[PARAG], "weight": "100"}]},
    )


def test_make_list_rename_and_delete(api: TestClient, funds) -> None:
    core = model(api, funds)
    retirement = bucket(api, "  Retirement ", model_id=core["id"])
    bucket(api, "Try", paper=True)

    assert retirement["name"] == "Retirement" and retirement["model"]["name"] == "Core"
    listed = api.get("/api/v1/buckets").json()
    assert [(b["name"], b["paper"], b["value"]) for b in listed] == [
        ("Retirement", False, None),
        ("Try", True, None),
    ]
    assert api.post("/api/v1/buckets", json={"name": "retirement"}).status_code == 409

    renamed = api.put(f"/api/v1/buckets/{retirement['id']}", json={"name": "Pension"})
    assert renamed.status_code == 200, renamed.text
    assert (renamed.json()["name"], renamed.json()["model"]) == ("Pension", None)

    lot = lump(api, funds, retirement["id"])
    assert api.delete(f"/api/v1/buckets/{retirement['id']}").status_code == 204
    # The real purchase stays, in no bucket.
    [kept] = api.get(f"/api/v1/holdings/{funds[PARAG]}").json()["lots"]
    assert (kept["id"], kept["bucket"]) == (lot["id"], None)


def test_deleting_a_model_leaves_its_buckets_without_one(api: TestClient, funds) -> None:
    core = model(api, funds)
    made = bucket(api, "Retirement", model_id=core["id"])

    assert api.delete(f"/api/v1/models/{core['id']}").status_code == 204

    [listed] = api.get("/api/v1/buckets").json()
    assert (listed["id"], listed["model"]) == (made["id"], None)


def test_paper_stays_paper_and_real_stays_real(api: TestClient, funds) -> None:
    real = bucket(api, "Retirement")
    paper = bucket(api, "Try", paper=True)
    lot = lump(api, funds, paper["id"])

    moved = api.put(
        f"/api/v1/lots/{lot['id']}",
        json={"buy_date": DAY.isoformat(), "amount": "1000", "bucket_id": real["id"]},
    )
    assert moved.status_code == 422
    assert "between a paper bucket and real money" in moved.json()["detail"]

    switched = api.put(f"/api/v1/buckets/{paper['id']}", json={"name": "Try", "paper": False})
    assert switched.status_code == 422
    # An empty bucket can still switch.
    empty = api.put(f"/api/v1/buckets/{real['id']}", json={"name": "Retirement", "paper": True})
    assert empty.status_code == 200 and empty.json()["paper"] is True


def test_a_purchase_moves_between_real_buckets(api: TestClient, funds) -> None:
    house = bucket(api, "House")
    lot = lump(api, funds, None)

    moved = api.put(
        f"/api/v1/lots/{lot['id']}",
        json={"buy_date": DAY.isoformat(), "amount": "1000", "bucket_id": house["id"]},
    )

    assert moved.status_code == 200, moved.text
    assert moved.json()["lots"][0]["bucket"] == {"id": house["id"], "name": "House", "paper": False}
    assert api.get("/api/v1/buckets").json()[0]["purchases"] == 1


def test_a_sips_instalments_follow_it_to_another_bucket(api: TestClient, funds) -> None:
    house = bucket(api, "House")
    sip = {"instrument_id": funds[PARAG], "amount": "500", "day": 5, "start_date": "2026-01-01"}
    holding = post(api, "/api/v1/sips", sip)
    [instalment] = holding["lots"]
    assert instalment["bucket"] is None

    changed = api.put(
        f"/api/v1/sips/{holding['sips'][0]['id']}", json={**sip, "bucket_id": house["id"]}
    )

    assert changed.status_code == 200, changed.text
    assert changed.json()["sips"][0]["bucket"]["name"] == "House"
    assert [lot["bucket"]["name"] for lot in changed.json()["lots"]] == ["House"]


def test_deleting_a_paper_bucket_deletes_its_purchases(api: TestClient, funds) -> None:
    paper = bucket(api, "Try", paper=True)
    lot = lump(api, funds, paper["id"])
    post(
        api,
        "/api/v1/sales",
        {"sale_date": DAY.isoformat(), "lots": [{"lot_id": lot["id"], "units": "5"}]},
    )
    lump(api, funds, None, NIFTY)

    assert api.delete(f"/api/v1/buckets/{paper['id']}").status_code == 204

    assert api.get(f"/api/v1/holdings/{funds[PARAG]}").json()["lots"] == []
    assert len(api.get(f"/api/v1/holdings/{funds[NIFTY]}").json()["lots"]) == 1


def test_a_bucket_from_fm_is_named_there(api: TestClient, factory: sessionmaker[Session]) -> None:
    with session_scope(factory) as session:
        made = fm_bucket(session, "fm-1", "Retirement").id

    renamed = api.put(f"/api/v1/buckets/{made}", json={"name": "Pension"})
    assert renamed.status_code == 422
    assert "rename it there" in renamed.json()["detail"]
    assert api.get("/api/v1/buckets").json()[0]["from_fm"] is True


def test_holdings_of_one_bucket(api: TestClient, funds) -> None:
    house = bucket(api, "House")
    lump(api, funds, house["id"])
    lump(api, funds, None, NIFTY)

    listed = api.get("/api/v1/holdings", params={"bucket_id": house["id"]}).json()

    assert [row["fund"]["amfi_code"] for row in listed] == [PARAG]
    assert len(api.get("/api/v1/holdings").json()) == 2
    assert api.get("/api/v1/holdings", params={"bucket_id": 99}).status_code == 404
