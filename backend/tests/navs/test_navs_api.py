"""NAV endpoints: track, sync, status, history and headline figures."""

import pytest
from fastapi.testclient import TestClient

from .conftest import NIFTY, PARAG, FakeNavFetcher


@pytest.fixture
def api(client: TestClient, funds: dict[str, int], fetcher: FakeNavFetcher) -> TestClient:
    client.app.state.nav_fetcher = fetcher
    return client


def test_track_then_sync_then_read_back(api: TestClient, funds: dict[str, int]) -> None:
    parag = funds[PARAG]

    tracked = api.put(f"/api/v1/instruments/{parag}/tracking")
    assert tracked.status_code == 200, tracked.text
    assert tracked.json()["tracked_by_me"] is True
    assert tracked.json()["coverage"] == {"first": None, "last": None, "count": 0}

    run = api.post("/api/v1/navs/sync", json={"instrument_ids": [parag]})
    assert run.status_code == 200, run.text
    assert run.json()["status"] == "ok"
    assert run.json()["results"][0] | {"message": None} == {
        "instrument_id": parag,
        "name": "Parag Parikh Flexi Cap Fund",
        "status": "ok",
        "added": 13,
        "corrected": 0,
        "last_date": "2026-10-23",
        "message": None,
    }

    navs = api.get(f"/api/v1/instruments/{parag}/navs", params={"start": "2026-10-21"}).json()
    assert navs == [
        {"date": "2026-10-21", "nav": "89.9443"},
        {"date": "2026-10-22", "nav": "89.4088"},
        {"date": "2026-10-23", "nav": "88.9695"},
    ]

    summary = api.get(f"/api/v1/instruments/{parag}/nav-summary").json()
    assert summary["coverage"] == {"first": "2013-05-28", "last": "2026-10-23", "count": 13}
    assert summary["stats"]["latest"] == {"date": "2026-10-23", "nav": "88.9695"}
    assert summary["stats"]["change_1d_pct"] == "-0.49"  # amounts and percents are strings


def test_status_lists_tracked_funds_with_the_last_run(api: TestClient, funds) -> None:
    api.put(f"/api/v1/instruments/{funds[PARAG]}/tracking")
    api.put(f"/api/v1/instruments/{funds[NIFTY]}/tracking")
    api.post("/api/v1/navs/sync")

    status = api.get("/api/v1/navs/status").json()

    assert status["last_run"]["funds"] == 2
    assert status["last_run"]["added"] == 26
    assert [fund["fund"]["name"] for fund in status["funds"]] == [
        "Parag Parikh Flexi Cap Fund",
        "UTI Nifty 50 Index Fund",
    ]
    assert status["funds"][0]["last_result"]["status"] == "ok"
    assert status["funds"][1]["coverage"]["last"] == "2026-10-23"


def test_status_before_anything_is_tracked(api: TestClient) -> None:
    assert api.get("/api/v1/navs/status").json() == {"last_run": None, "funds": []}


def test_a_stock_has_no_navs(api: TestClient, funds) -> None:
    infosys = funds["INFY"]

    assert api.put(f"/api/v1/instruments/{infosys}/tracking").status_code == 422
    assert api.get(f"/api/v1/instruments/{infosys}/navs").status_code == 422
    summary = api.get(f"/api/v1/instruments/{infosys}/nav-summary").json()
    assert (summary["is_fund"], summary["tracked"], summary["stats"]) == (False, False, None)


def test_syncing_an_untracked_fund_is_a_conflict(api: TestClient, funds) -> None:
    response = api.post("/api/v1/navs/sync", json={"instrument_ids": [funds[PARAG]]})

    assert response.status_code == 409
    assert response.headers["content-type"] == "application/problem+json"
    assert "Track these funds first" in response.json()["detail"]


def test_untrack(api: TestClient, funds) -> None:
    api.put(f"/api/v1/instruments/{funds[PARAG]}/tracking")

    response = api.delete(f"/api/v1/instruments/{funds[PARAG]}/tracking")

    assert response.status_code == 200
    assert response.json()["tracked"] is False


def test_unknown_instrument(api: TestClient) -> None:
    assert api.get("/api/v1/instruments/999/nav-summary").status_code == 404
