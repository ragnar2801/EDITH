"""Backtest endpoints: run, store, save, list, interval, delete, and refusals."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from navs.conftest import NIFTY, PARAG, FakeNavFetcher

from friday.core.backtest import service


@pytest.fixture
def api(client: TestClient, funds: dict[str, int], fetcher: FakeNavFetcher) -> TestClient:
    client.app.state.nav_fetcher = fetcher
    return client


@pytest.fixture
def bucket(api: TestClient, funds) -> dict:
    created = api.post(
        "/api/v1/buckets",
        json={
            "name": "Core",
            "benchmark_id": funds[NIFTY],
            "funds": [
                {"instrument_id": funds[PARAG], "weight": "60"},
                {"instrument_id": funds[NIFTY], "weight": "40"},
            ],
        },
    ).json()
    api.post("/api/v1/navs/sync")
    return created


def run(api: TestClient, bucket: dict, params: dict, **extra):
    return api.post(
        "/api/v1/backtests", json={"bucket_id": bucket["id"], "params": params, **extra}
    )


def test_sip_run_with_the_same_sip_in_the_benchmark(api: TestClient, bucket) -> None:
    response = run(api, bucket, {"strategy": "sip", "amount": "10000", "start": "2026-10-01"})

    assert response.status_code == 200, response.text
    body = response.json()
    result = body["result"]
    assert (body["bucket_name"], body["saved"], body["strategy"]) == ("Core", False, "sip")
    assert result["metrics"]["start_date"] == "2026-10-09"  # first NAV date both funds share
    assert result["metrics"]["total_invested"] == "10000.00"  # one October instalment
    assert result["benchmark"]["metrics"]["total_invested"] == "10000.00"
    assert result["benchmark"]["name"] == "UTI Nifty 50 Index Fund"
    assert [f["weight"] for f in result["funds"]] == ["60", "40"]
    point = result["curve"][0]
    assert set(point) == {"date", "value", "invested", "withdrawn", "index"}
    assert point["index"] == "100.000000"
    assert all(isinstance(v, str) for v in result["metrics"].values() if v is not None)


def test_a_requested_start_before_the_data_is_reported(api: TestClient, bucket) -> None:
    result = run(api, bucket, {"strategy": "regular", "capital": "100000", "start": "2013-01-01"})

    warnings = result.json()["result"]["warnings"]
    assert warnings == [
        "Started on 2013-05-28 instead of 2013-01-01: Parag Parikh Flexi Cap Fund has no NAV "
        "before then."
    ]


def test_save_list_load_and_delete(api: TestClient, bucket) -> None:
    first = run(api, bucket, {"strategy": "regular", "capital": "100000"}).json()
    run(api, bucket, {"strategy": "swp", "corpus": "500000", "amount": "4000"})

    saved = api.patch(f"/api/v1/backtests/{first['id']}", json={"saved": True, "name": " Lump "})
    assert saved.json()["name"] == "Lump"
    listed = api.get(f"/api/v1/buckets/{bucket['id']}/backtests").json()
    assert [(r["id"], r["name"], r["params"]["capital"]) for r in listed] == [
        (first["id"], "Lump", "100000")
    ]
    loaded = api.get(f"/api/v1/backtests/{first['id']}").json()
    assert loaded["result"] == first["result"]

    assert api.delete(f"/api/v1/backtests/{first['id']}").status_code == 204
    assert api.get(f"/api/v1/backtests/{first['id']}").status_code == 404


def test_run_and_save_in_one_go(api: TestClient, bucket) -> None:
    body = run(api, bucket, {"strategy": "regular", "capital": "1000"}, save=True, name="x").json()

    assert (body["saved"], body["name"]) == (True, "x")


def test_only_the_latest_unsaved_runs_are_kept(api: TestClient, bucket, monkeypatch) -> None:
    monkeypatch.setattr(service, "KEEP_UNSAVED", 2)
    kept = run(api, bucket, {"strategy": "regular", "capital": "1"}, save=True).json()
    ids = [run(api, bucket, {"strategy": "regular", "capital": "1"}).json()["id"] for _ in range(3)]

    assert api.get(f"/api/v1/backtests/{ids[0]}").status_code == 404
    assert all(api.get(f"/api/v1/backtests/{i}").status_code == 200 for i in [*ids[1:], kept["id"]])


def test_interval_of_a_stored_run(api: TestClient, bucket) -> None:
    body = run(
        api, bucket, {"strategy": "regular", "capital": "100000", "start": "2026-10-01"}
    ).json()
    curve = body["result"]["curve"]

    window = api.get(
        f"/api/v1/backtests/{body['id']}/interval",
        params={"start": curve[1]["date"], "end": curve[-1]["date"]},
    )

    assert window.status_code == 200, window.text
    data = window.json()
    assert (data["start_value"], data["end_value"]) == (curve[1]["value"], curve[-1]["value"])
    assert (data["invested"], data["withdrawn"]) == ("0.00", "0.00")
    assert data["benchmark_return_pct"] is not None
    too_small = api.get(
        f"/api/v1/backtests/{body['id']}/interval", params={"start": curve[-1]["date"]}
    )
    assert too_small.status_code == 422


def test_custom_positions_and_trades(api: TestClient, bucket, funds) -> None:
    params = {
        "strategy": "custom",
        "positions": [
            {
                "instrument_id": funds[PARAG],
                "entry": "2026-10-09",
                "exit": "2026-10-16",
                "amount": "50000",
            }
        ],
        "trades": [
            {"instrument_id": funds[NIFTY], "date": "2026-10-16", "side": "buy", "amount": "50000"}
        ],
    }

    result = run(api, bucket, params).json()["result"]

    assert [(t["side"], t["name"], t["date"]) for t in result["trades"]] == [
        ("buy", "Parag Parikh Flexi Cap Fund", "2026-10-09"),
        ("sell", "Parag Parikh Flexi Cap Fund", "2026-10-16"),
        ("buy", "UTI Nifty 50 Index Fund", "2026-10-16"),
    ]
    parag = result["funds"][0]
    assert (parag["invested"], parag["units"]) == ("50000.00", "0.00000000")
    assert parag["pnl"] is not None


@pytest.mark.parametrize(
    "params",
    [
        {"strategy": "sip", "amount": 10000},  # amounts are strings
        {"strategy": "sip", "amount": "0"},
        {"strategy": "sip", "amount": "1", "frequency": "daily"},
        {"strategy": "sip", "amount": "1", "start": "2026-01-02", "end": "2026-01-01"},
        {"strategy": "custom"},
        {
            "strategy": "custom",
            "trades": [{"instrument_id": 1, "date": "2026-10-09", "side": "buy"}],  # no amount
        },
        {"strategy": "lump"},
    ],
)
def test_bad_parameters_are_refused(api: TestClient, bucket, params) -> None:
    assert run(api, bucket, params).status_code == 422


def test_a_fund_outside_the_bucket_is_refused(api: TestClient, bucket, funds) -> None:
    params = {
        "strategy": "custom",
        "trades": [
            {"instrument_id": funds["108844"], "date": "2026-10-09", "side": "buy", "amount": "1"}
        ],
    }

    response = run(api, bucket, params)

    assert response.status_code == 422
    assert response.json()["detail"] == "Trade 1: that fund isn't in this bucket."


def test_no_navs_yet_is_explained(api: TestClient, funds) -> None:
    bucket = api.post(
        "/api/v1/buckets",
        json={"name": "Empty", "funds": [{"instrument_id": funds[PARAG], "weight": "100"}]},
    ).json()

    response = run(api, bucket, {"strategy": "regular", "capital": "1000"})

    assert response.status_code == 422
    assert "No NAVs yet for Parag Parikh Flexi Cap Fund" in response.json()["detail"]


def test_deleting_a_bucket_deletes_its_runs(api: TestClient, bucket) -> None:
    body = run(api, bucket, {"strategy": "regular", "capital": "1000"}, save=True).json()

    api.delete(f"/api/v1/buckets/{bucket['id']}")

    assert api.get(f"/api/v1/backtests/{body['id']}").status_code == 404


def split(funds, **weights) -> list[dict]:
    return [{"instrument_id": funds[code], "weight": w} for code, w in weights.items()]


def test_a_split_is_run_and_kept_without_changing_the_bucket(api: TestClient, bucket, funds):
    params = {
        "strategy": "regular",
        "capital": "100000",
        "start": "2026-10-01",
        "split": [{"instrument_id": funds[PARAG], "weight": "100"}],
    }
    body = run(api, bucket, params).json()

    assert [(f["name"], f["weight"]) for f in body["result"]["funds"]] == [
        ("Parag Parikh Flexi Cap Fund", "100")
    ]
    assert body["params"]["split"] == [{"instrument_id": funds[PARAG], "weight": "100"}]
    assert api.get(f"/api/v1/backtests/{body['id']}").json()["params"]["split"] == [
        {"instrument_id": funds[PARAG], "weight": "100"}
    ]
    model = api.get(f"/api/v1/buckets/{bucket['id']}").json()
    assert [f["weight"] for f in model["funds"]] == ["60", "40"]


@pytest.mark.parametrize(
    ("weights", "reason"),
    [
        ({PARAG: "60", NIFTY: "30"}, "Split: weights must add up to 100, not 90."),
        ({PARAG: "0", NIFTY: "100"}, "weight must be more than 0 and at most 100"),
    ],
)
def test_a_split_a_bucket_couldnt_have_is_refused(api, bucket, funds, weights, reason) -> None:
    params = {"strategy": "sip", "amount": "1000", "split": split(funds, **weights)}

    response = run(api, bucket, params)

    assert response.status_code == 422
    assert reason in response.json()["detail"]


def test_comparing_a_tweaked_split_with_the_run_before(api: TestClient, bucket, funds) -> None:
    common = {"strategy": "regular", "capital": "100000", "start": "2026-10-01"}
    before = run(api, bucket, common).json()
    after = run(api, bucket, {**common, "split": split(funds, **{PARAG: "90", NIFTY: "10"})})
    after = after.json()

    response = api.get(f"/api/v1/backtests/{after['id']}/compare", params={"against": before["id"]})

    assert response.status_code == 200, response.text
    got = response.json()
    now, then = after["result"]["metrics"], before["result"]["metrics"]
    assert got["against"] == before["id"]
    assert got["same_settings"] is True
    # by hand: the two runs' own figures, subtracted

    assert Decimal(got["end_value"]) == Decimal(now["end_value"]) - Decimal(then["end_value"])
    assert Decimal(got["volatility_pct"]) == (
        Decimal(now["volatility_pct"]) - Decimal(then["volatility_pct"])
    )
    assert [(w["before"], w["after"]) for w in got["weights"]] == [("60", "90"), ("40", "10")]


def test_comparing_runs_with_other_settings_or_dropped_funds(api, bucket, funds) -> None:
    before = run(api, bucket, {"strategy": "sip", "amount": "1000"}).json()
    after = run(
        api, bucket, {"strategy": "sip", "amount": "2000", "split": split(funds, **{PARAG: "100"})}
    ).json()

    got = api.get(f"/api/v1/backtests/{after['id']}/compare", params={"against": before["id"]})

    body = got.json()
    assert body["same_settings"] is False
    assert [(w["name"], w["before"], w["after"]) for w in body["weights"]] == [
        ("Parag Parikh Flexi Cap Fund", "60", "100"),
        ("UTI Nifty 50 Index Fund", "40", None),
    ]
    missing = api.get(f"/api/v1/backtests/{after['id']}/compare", params={"against": 999})
    assert missing.status_code == 404


def optimise(api: TestClient, bucket: dict, params: dict, **settings):
    return api.post(
        "/api/v1/backtests/optimise",
        json={"bucket_id": bucket["id"], "params": params, **settings},
    )


LUMP = {"strategy": "regular", "capital": "100000", "start": "2026-10-01"}


def test_optimise_tries_every_split_and_reruns_the_best(api: TestClient, bucket) -> None:
    response = optimise(api, bucket, LUMP, step=10)

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["tried"], body["eligible"], len(body["points"])) == (11, 11, 11)
    assert body["start_date"] == "2026-10-09"
    assert [(f["name"], f["weight"]) for f in body["model"]["funds"]] == [
        ("Parag Parikh Flexi Cap Fund", "60"),
        ("UTI Nifty 50 Index Fund", "40"),
    ]
    assert body["benchmark"]["name"] == "UTI Nifty 50 Index Fund"
    top = body["top"]
    assert len(top) == 10
    xirrs = [Decimal(c["metrics"]["xirr_pct"]) for c in top]
    assert xirrs == sorted(xirrs, reverse=True)
    # the exact figures are the backtest's own for that split
    split = [{"instrument_id": f["instrument_id"], "weight": f["weight"]} for f in top[0]["funds"]]
    if len(split) == 1:
        split[0]["weight"] = "100"
    exact = run(api, bucket, {**LUMP, "split": split}).json()["result"]["metrics"]
    assert top[0]["metrics"] == exact


def test_optimise_keeps_to_the_limits(api: TestClient, bucket) -> None:
    every = optimise(api, bucket, LUMP, step=10, goal="drawdown").json()
    least = Decimal(every["top"][0]["metrics"]["max_drawdown_pct"])
    assert all(Decimal(p["max_drawdown_pct"]) >= least for p in every["points"])

    capped = optimise(
        api, bucket, LUMP, step=10, min_weight=20, max_weight=80, max_drawdown_pct=str(least)
    ).json()
    assert capped["tried"] == 7
    assert all(Decimal(c["metrics"]["max_drawdown_pct"]) <= least for c in capped["top"])
    assert capped["eligible"] == sum(p["eligible"] for p in capped["points"])


@pytest.mark.parametrize(
    ("grid", "status", "reason"),
    [
        ({"step": 3}, 422, "step must divide 100"),
        ({"min_weight": 60, "max_weight": 40}, 422, "lowest weight must be at most"),
        ({"min_weight": 55}, 422, "No split with these weights adds up to 100."),
    ],
)
def test_optimise_refuses_a_grid_it_cant_use(api, bucket, grid, status, reason) -> None:
    response = optimise(api, bucket, LUMP, **grid)

    assert response.status_code == status
    assert reason in response.text


def test_optimise_refuses_too_many_funds_or_splits(api, bucket, monkeypatch) -> None:
    from friday.core.backtest import search

    monkeypatch.setattr(search, "MAX_SPLITS", 5)
    assert "That is 21 splits and the most is 5" in optimise(api, bucket, LUMP).text
    monkeypatch.setattr(search, "MAX_FUNDS", 1)
    assert "up to 1 funds" in optimise(api, bucket, LUMP).text
