"""The portfolio view through the API, on a portfolio worked by hand."""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from navs.conftest import NIFTY, PARAG
from sqlalchemy.orm import Session, sessionmaker

from friday.core.db import session_scope
from friday.core.navs.models import FundNav

ARBITRAGE = "108844"
NIFTY_REGULAR = "100822"

# NAVs on four dates. Parag Parikh is what I hold; the Nifty 50 index fund is the benchmark.
NAVS = {
    PARAG: {"2024-01-01": "100", "2025-01-01": "125", "2025-07-01": "150", "2026-01-01": "160"},
    NIFTY: {"2024-01-01": "200", "2025-01-01": "250", "2025-07-01": "300", "2026-01-01": "300"},
    ARBITRAGE: {"2026-01-01": "20"},
}


@pytest.fixture
def api(client: TestClient, funds: dict[str, int], factory: sessionmaker[Session]) -> TestClient:
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
    return client


def post(api: TestClient, url: str, body: dict) -> dict:
    response = api.post(url, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def lump_sum(api: TestClient, fund_id: int, day: str, amount: str, **extra) -> dict:
    body = {"instrument_id": fund_id, "buy_date": day, "amount": amount, **extra}
    return post(api, "/api/v1/lots", body)


@pytest.fixture
def held(api: TestClient, funds: dict[str, int]) -> TestClient:
    """Parag Parikh: ₹10,000 at 100 (100 units) and ₹5,000 at 125 (40 units); 50 units of
    the first lot sold at 150 (₹7,500). ₹6,000 of the arbitrage fund as emergency money,
    in a 60 / 40 target bucket of Parag Parikh and the Nifty 50 index fund."""
    lump_sum(api, funds[PARAG], "2024-01-01", "10000")
    holding = lump_sum(api, funds[PARAG], "2025-01-01", "5000")
    first = holding["lots"][0]
    post(
        api,
        "/api/v1/sales",
        {"sale_date": "2025-07-01", "lots": [{"lot_id": first["id"], "units": "50"}]},
    )
    lump_sum(api, funds[ARBITRAGE], "2026-01-01", "6000")
    bucket = post(
        api,
        "/api/v1/buckets",
        {
            "name": "Core",
            "funds": [
                {"instrument_id": funds[PARAG], "weight": "60"},
                {"instrument_id": funds[NIFTY], "weight": "40"},
            ],
        },
    )
    response = api.put(
        "/api/v1/plan/settings",
        json={
            "target_bucket_id": bucket["id"],
            "emergency_fund_id": funds[ARBITRAGE],
            "emergency_goal": "100000",
            "stagger_threshold": "500000",
            "stagger_months": 6,
            "min_per_fund": "500",
        },
    )
    assert response.status_code == 200, response.text
    post(
        api,
        "/api/v1/cash/accounts",
        {"name": "Savings", "balance": "20000", "earmark": "emergency"},
    )
    post(
        api, "/api/v1/cash/accounts", {"name": "Salary", "balance": "4000", "earmark": "deployable"}
    )
    return api


def view(api: TestClient) -> dict:
    response = api.get("/api/v1/portfolio")
    assert response.status_code == 200, response.text
    return response.json()


def test_nothing_held(api: TestClient) -> None:
    data = view(api)

    assert data["returns"] is None and data["funds"] == [] and data["drift"] == []
    assert data["net_worth"] == "0.00"


def test_value_and_pnl_of_a_partly_sold_fund(held: TestClient, funds) -> None:
    data = view(held)

    [parag] = [f for f in data["funds"] if f["fund"]["amfi_code"] == PARAG]
    # 50 + 40 units at 160 = ₹14,400. They cost 5,000 + 5,000.
    assert Decimal(parag["units"]) == 90 and Decimal(parag["nav"]) == 160
    assert parag["nav_date"] == "2026-01-01"
    assert (parag["cost"], parag["returns"]["value"]) == ("10000.00", "14400.00")
    # Sold 50 units for 7,500 that cost 5,000; the rest is unrealised.
    assert (parag["realised"], parag["unrealised"]) == ("2500.00", "4400.00")
    returns = parag["returns"]
    assert (returns["invested"], returns["redeemed"], returns["gain"]) == (
        "15000.00",
        "7500.00",
        "6900.00",
    )
    assert returns["return_pct"] == "46.00"
    assert returns["xirr_pct"] is not None and returns["since"] == "2024-01-01"
    assert parag["role"] == "target"

    # The same money in the index fund: 50 units at 200, 20 at 250, 25 out at 300; 45 × 300.
    benchmark = parag["benchmark"]
    assert (benchmark["value"], benchmark["gain"]) == ("13500.00", "6000.00")


def test_totals_cash_and_benchmark(held: TestClient, funds) -> None:
    data = view(held)

    total = data["returns"]
    assert (total["value"], total["invested"], total["redeemed"]) == (
        "20400.00",
        "21000.00",
        "7500.00",
    )
    assert total["gain"] == "6900.00"  # the arbitrage fund is flat
    assert (data["realised"], data["unrealised"], data["cost"]) == (
        "2500.00",
        "4400.00",
        "16000.00",
    )
    assert data["benchmark_fund"]["amfi_code"] == NIFTY
    assert data["benchmark"]["value"] == "19500.00"  # 13,500 + 6,000 bought at 300, still 300
    assert data["cash"] == {
        "deployable": "4000.00",
        "emergency": "20000.00",
        "reserved": "0.00",
        "total": "24000.00",
    }
    assert data["net_worth"] == "44400.00"
    assert (data["nav_oldest"], data["nav_newest"]) == ("2026-01-01", "2026-01-01")
    shares = {f["fund"]["amfi_code"]: f["share"] for f in data["funds"]}
    assert shares == {PARAG: "70.59", ARBITRAGE: "29.41"}
    [arbitrage] = [f for f in data["funds"] if f["fund"]["amfi_code"] == ARBITRAGE]
    assert arbitrage["role"] == "emergency"
    assert arbitrage["returns"]["xirr_pct"] is None  # bought today: under a year


def test_allocation_by_asset_class(held: TestClient) -> None:
    data = view(held)

    assert data["allocation"] == [
        {"asset": "equity", "value": "14400.00", "share": "70.59"},
        {"asset": "debt", "value": "6000.00", "share": "29.41"},
    ]


def test_drift_from_the_target_split(held: TestClient) -> None:
    data = view(held)

    assert data["target"]["name"] == "Core"
    drift = {row["fund"]["amfi_code"]: row for row in data["drift"]}
    assert (drift[PARAG]["share"], drift[PARAG]["weight"], drift[PARAG]["drift"]) == (
        "100.00",
        "60.00",
        "40.00",
    )
    assert (drift[NIFTY]["value"], drift[NIFTY]["share"], drift[NIFTY]["drift"]) == (
        "0.00",
        "0.00",
        "-40.00",
    )


def test_a_fund_without_nav_history_is_listed_not_counted(held: TestClient, funds) -> None:
    lump_sum(held, funds[NIFTY_REGULAR], "2026-01-01", "1000", nav="50")  # NAV typed in

    data = view(held)

    assert [f["amfi_code"] for f in data["missing_nav"]] == [NIFTY_REGULAR]
    [regular] = [f for f in data["funds"] if f["fund"]["amfi_code"] == NIFTY_REGULAR]
    assert (regular["returns"], regular["share"], regular["role"]) == (None, None, "outside")
    assert data["returns"]["value"] == "20400.00"  # unchanged


def test_each_sale_shows_what_it_realised(held: TestClient, funds) -> None:
    holding = held.get(f"/api/v1/holdings/{funds[PARAG]}").json()

    [sale] = holding["lots"][0]["sales"]
    assert (sale["amount"], sale["realised"]) == ("7500.00", "2500.00")


def test_the_day_is_each_funds_move_between_its_last_two_navs(held: TestClient) -> None:
    data = view(held)

    # Parag Parikh's last two NAVs: 150 on 1 Jul 2025, 160 on 1 Jan 2026, on 90 units. The
    # arbitrage fund has one NAV, so no move yet.
    funds = {f["fund"]["amfi_code"]: f for f in data["funds"]}
    assert funds[PARAG]["day"] == {
        "start": "2025-07-01",
        "end": "2026-01-01",
        "gain": "900.00",
        "return_pct": "6.67",
    }
    assert funds[ARBITRAGE]["day"] is None
    # 900 ÷ 13,500.
    assert (data["day"]["gain"], data["day"]["return_pct"]) == ("900.00", "6.67")


def test_funds_with_navs_on_different_days_each_use_their_own(
    held: TestClient, funds, factory: sessionmaker[Session]
) -> None:
    with session_scope(factory) as session:
        for day, nav in (("2026-01-02", "161"), ("2026-01-03", "20.01")):
            session.add(
                FundNav(
                    instrument_id=funds[PARAG if nav == "161" else ARBITRAGE],
                    nav_date=date.fromisoformat(day),
                    nav=Decimal(nav),
                    source="amfi",
                )
            )

    data = view(held)

    # Parag Parikh 160 → 161 on Friday; the arbitrage fund 20 → 20.01 on Saturday.
    day = {f["fund"]["amfi_code"]: f["day"] for f in data["funds"]}
    assert (day[PARAG]["start"], day[PARAG]["end"], day[PARAG]["gain"]) == (
        "2026-01-01",
        "2026-01-02",
        "90.00",
    )
    assert (day[ARBITRAGE]["start"], day[ARBITRAGE]["end"], day[ARBITRAGE]["gain"]) == (
        "2026-01-01",
        "2026-01-03",
        "3.00",
    )
    # 93 ÷ (14,400 + 6,000).
    assert data["day"] == {
        "start": "2026-01-01",
        "end": "2026-01-03",
        "gain": "93.00",
        "return_pct": "0.46",
    }


def test_rupees_ahead_of_the_benchmark_and_biggest_first(held: TestClient) -> None:
    data = view(held)

    # Gain 6,900 against 6,000 for the same flows in the index fund.
    assert [f["fund"]["amfi_code"] for f in data["funds"]] == [PARAG, ARBITRAGE]
    assert data["funds"][0]["ahead"] == "900.00"
    assert data["funds"][1]["ahead"] == "0.00"  # 6,000 in at 300, still 300
    assert data["ahead"] == "900.00"


def test_sips_per_month_and_the_next_one(held: TestClient, funds, monkeypatch) -> None:
    for module in ("friday.core.holdings.service", "friday.core.portfolio.service"):
        monkeypatch.setattr(f"{module}.today", lambda: date(2026, 1, 10))
    sips = [
        (PARAG, "1000", 5, "2025-01-01", None),
        (NIFTY, "2000", 15, "2025-01-01", None),
        (ARBITRAGE, "500", 1, "2025-06-01", "2025-12-31"),  # ended
    ]
    for code, amount, day, start, end in sips:
        body = {"instrument_id": funds[code], "amount": amount, "day": day, "start_date": start}
        post(held, "/api/v1/sips", {**body, "end_date": end})

    data = view(held)

    assert {k: v for k, v in data["sips"].items() if k != "next_fund"} == {
        "monthly": "3000.00",
        "count": 2,
        "next_date": "2026-01-15",
    }
    assert data["sips"]["next_fund"]["amfi_code"] == NIFTY


def history(api: TestClient, start: str | None = None) -> dict:
    response = api.get("/api/v1/portfolio/history", params={"start": start} if start else {})
    assert response.status_code == 200, response.text
    return response.json()


def test_value_invested_and_benchmark_over_time(held: TestClient) -> None:
    data = history(held)

    assert data["benchmark_fund"]["amfi_code"] == NIFTY
    rows = [(p["date"], p["value"], p["invested"], p["benchmark"]) for p in data["points"]]
    assert rows == [
        ("2024-01-01", "10000.00", "10000.00", "10000.00"),
        ("2025-01-01", "17500.00", "15000.00", "17500.00"),
        ("2025-07-01", "13500.00", "10000.00", "13500.00"),  # after selling 50 units
        ("2026-01-01", "20400.00", "16000.00", "19500.00"),
    ]
    # The last point is the value and cost Portfolio shows.
    assert (rows[-1][1], rows[-1][2]) == (view(held)["returns"]["value"], view(held)["cost"])
    # Parag Parikh went 100 → 160 and the arbitrage fund stayed flat: 60%; Nifty 200 → 300.
    assert data["change"] == {
        "start": "2024-01-01",
        "end": "2026-01-01",
        "gain": "6900.00",
        "return_pct": "60.00",
    }
    assert (data["benchmark_change"]["gain"], data["benchmark_change"]["return_pct"]) == (
        "6000.00",
        "50.00",
    )


def test_history_from_a_start_date(held: TestClient) -> None:
    data = history(held, "2025-03-01")  # no NAV that day: from 1 Jan 2025's value

    assert [p["date"] for p in data["points"]] == ["2025-01-01", "2025-07-01", "2026-01-01"]
    # 20,400 − 17,500 − (6,000 in − 7,500 out); 1.2 × 1.0667.
    assert (data["change"]["gain"], data["change"]["return_pct"]) == ("4400.00", "28.00")
    assert (data["benchmark_change"]["gain"], data["benchmark_change"]["return_pct"]) == (
        "3500.00",
        "20.00",
    )


def test_history_with_nothing_held(api: TestClient) -> None:
    data = history(api)

    assert (data["points"], data["change"], data["benchmark_change"]) == ([], None, None)
