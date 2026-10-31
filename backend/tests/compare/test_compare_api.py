"""GET /compare/funds: funds side by side over the dates they share."""

import pytest
from fastapi.testclient import TestClient
from navs.conftest import NIFTY, PARAG, FakeNavFetcher


@pytest.fixture
def api(client: TestClient, funds: dict[str, int], fetcher: FakeNavFetcher) -> TestClient:
    client.app.state.nav_fetcher = fetcher
    for code in (PARAG, NIFTY):
        client.put(f"/api/v1/instruments/{funds[code]}/tracking")
    client.post("/api/v1/navs/sync")
    return client


def compare(api: TestClient, *ids: int, **params):
    return api.get("/api/v1/compare/funds", params={"ids": list(ids), **params})


def test_two_funds_over_the_dates_they_share(api: TestClient, funds) -> None:
    response = compare(api, funds[PARAG], funds[NIFTY])

    assert response.status_code == 200, response.text
    body = response.json()
    window = body["window"]
    assert window["start"] == "2013-05-28"  # Parag's first NAV: it is younger
    assert window["end"] == "2026-10-23"
    assert window["limited_by"] == funds[PARAG]
    assert window["earliest_start"] == "2013-01-02"
    assert [f["fund"]["name"] for f in body["items"]][0].startswith("Parag Parikh")
    parag = body["items"][0]
    assert parag["window"]["growth"][0] == {"date": "2013-05-28", "value": "10000.00"}
    assert parag["window"]["sip"]["invested"].endswith(".00")
    assert parag["trailing"]["y1"] is not None
    assert body["benchmark"]["fund"]["amfi_code"] == NIFTY
    assert body["calendar_years"][-1] == 2026
    assert [(c["a"], c["b"]) for c in body["correlation"]] == [
        (funds[PARAG], funds[NIFTY]),
        (funds[PARAG], 0),  # 0 is the benchmark
        (funds[NIFTY], 0),
    ]


def test_starting_earlier_leaves_the_younger_fund_out(api: TestClient, funds) -> None:
    body = compare(api, funds[PARAG], funds[NIFTY], start="2013-01-02").json()

    assert body["window"]["start"] == "2013-01-02"
    assert body["items"][0]["window"] is None
    assert body["items"][0]["trailing"]["y1"] is not None  # same dates for everyone anyway
    assert body["items"][1]["window"] is not None


def test_a_fund_without_navs_is_shown_empty(api: TestClient, funds) -> None:
    other = next(i for code, i in funds.items() if code not in (PARAG, NIFTY, "INFY"))

    body = compare(api, funds[PARAG], other).json()

    assert body["items"][1]["first"] is None
    assert body["items"][1]["window"] is None
    assert any("has no NAVs yet" in warning for warning in body["warnings"])


def test_refusals(api: TestClient, funds) -> None:
    assert compare(api, 999_999).status_code == 404
    assert compare(api, funds["INFY"]).status_code == 422
    assert compare(api, funds[PARAG], rolling_years=2).status_code == 422
    assert api.get("/api/v1/compare/funds").status_code == 422
