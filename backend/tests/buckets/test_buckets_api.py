"""Buckets: exact weights, funds only, tracking, edits and deletes (D-047)."""

import pytest
from fastapi.testclient import TestClient
from navs.conftest import NIFTY, PARAG, FakeNavFetcher


@pytest.fixture
def api(client: TestClient, funds: dict[str, int], fetcher: FakeNavFetcher) -> TestClient:
    client.app.state.nav_fetcher = fetcher
    return client


def core(ids: dict[str, int], **extra) -> dict:
    return {
        "name": "Core",
        "description": "Flexi cap plus the index",
        "rebalance": "yearly",
        "benchmark_id": ids[NIFTY],
        "funds": [
            {"instrument_id": ids[PARAG], "weight": "60"},
            {"instrument_id": ids[NIFTY], "weight": "40"},
        ],
        **extra,
    }


def test_default_benchmark_is_the_nifty_50_index_fund(api: TestClient) -> None:
    benchmark = api.get("/api/v1/buckets/default-benchmark").json()

    assert (benchmark["amfi_code"], benchmark["name"]) == ("120716", "UTI Nifty 50 Index Fund")
    assert (benchmark["plan"], benchmark["option"]) == ("direct", "Growth")


def test_create_and_read_a_bucket(api: TestClient, funds) -> None:
    created = api.post("/api/v1/buckets", json=core(funds))
    assert created.status_code == 201, created.text
    bucket = created.json()

    assert (bucket["name"], bucket["rebalance"]) == ("Core", "yearly")
    assert [(f["fund"]["amfi_code"], f["weight"]) for f in bucket["funds"]] == [
        (PARAG, "60"),
        (NIFTY, "40"),
    ]
    assert bucket["benchmark"]["fund"]["amfi_code"] == NIFTY
    assert bucket["common_start"] is None  # no NAVs synced yet
    assert api.get(f"/api/v1/buckets/{bucket['id']}").json() == bucket
    assert [b["name"] for b in api.get("/api/v1/buckets").json()] == ["Core"]


def test_bucket_funds_are_tracked_and_sync(api: TestClient, funds) -> None:
    bucket = api.post("/api/v1/buckets", json=core(funds)).json()

    api.post("/api/v1/navs/sync")

    status = api.get("/api/v1/navs/status").json()
    reasons = {row["fund"]["amfi_code"]: row["used_by"] for row in status["funds"]}
    assert reasons == {PARAG: ["bucket Core"], NIFTY: ["bucket Core", "benchmark of Core"]}
    refreshed = api.get(f"/api/v1/buckets/{bucket['id']}").json()
    assert refreshed["common_start"] == "2013-05-28"  # Parag Parikh's first NAV is the later one
    assert refreshed["funds"][0]["coverage"]["count"] == 13
    untrack = api.delete(f"/api/v1/instruments/{funds[PARAG]}/tracking")
    assert untrack.status_code == 409
    assert "bucket Core" in untrack.json()["detail"]


@pytest.mark.parametrize(
    ("weights", "message"),
    [
        (["60", "39.99"], "Weights must add up to 100, not 99.99."),
        (["60", "40.01"], "Weights must add up to 100, not 100.01."),
        (["100", "0"], "weight must be more than 0"),
    ],
)
def test_weights_must_add_up_to_exactly_100(api: TestClient, funds, weights, message) -> None:
    payload = core(funds)
    for fund, weight in zip(payload["funds"], weights, strict=True):
        fund["weight"] = weight

    response = api.post("/api/v1/buckets", json=payload)

    assert response.status_code == 422
    assert message in response.json()["detail"]


def test_weights_must_be_strings(api: TestClient, funds) -> None:
    payload = core(funds)
    payload["funds"][0]["weight"] = 60  # a JSON number could lose precision (D-032)

    assert api.post("/api/v1/buckets", json=payload).status_code == 422


def test_only_funds(api: TestClient, funds) -> None:
    payload = core(funds)
    payload["funds"].append({"instrument_id": funds["INFY"], "weight": "0.5"})

    response = api.post("/api/v1/buckets", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"] == "Fund: Infosys Limited is not a mutual fund scheme."


def test_a_fund_listed_twice_is_refused(api: TestClient, funds) -> None:
    payload = core(funds)
    payload["funds"][1]["instrument_id"] = funds[PARAG]

    assert api.post("/api/v1/buckets", json=payload).json()["detail"] == "A fund is listed twice."


def test_names_are_unique(api: TestClient, funds) -> None:
    api.post("/api/v1/buckets", json=core(funds))

    response = api.post("/api/v1/buckets", json=core(funds, name="  Core "))

    assert response.status_code == 409


def test_edit_changes_weights_order_and_members(api: TestClient, funds) -> None:
    bucket = api.post("/api/v1/buckets", json=core(funds)).json()

    edited = api.put(
        f"/api/v1/buckets/{bucket['id']}",
        json=core(
            funds,
            name="Core v2",
            rebalance="none",
            benchmark_id=None,
            funds=[
                {"instrument_id": funds[NIFTY], "weight": "70.5"},
                {"instrument_id": funds["108844"], "weight": "29.5"},
            ],
        ),
    )

    assert edited.status_code == 200, edited.text
    body = edited.json()
    assert (body["name"], body["rebalance"], body["benchmark"]) == ("Core v2", "none", None)
    assert [(f["fund"]["amfi_code"], f["weight"]) for f in body["funds"]] == [
        (NIFTY, "70.5"),
        ("108844", "29.5"),
    ]


def test_delete(api: TestClient, funds) -> None:
    bucket = api.post("/api/v1/buckets", json=core(funds)).json()

    assert api.delete(f"/api/v1/buckets/{bucket['id']}").status_code == 204
    assert api.get(f"/api/v1/buckets/{bucket['id']}").status_code == 404
    assert api.get("/api/v1/navs/status").json()["funds"] == []
