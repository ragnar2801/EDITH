"""Holdings: lump sums, SIPs, selling from lots, worked by hand (D-051 to D-054)."""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from navs.conftest import NIFTY, PARAG, FakeNavFetcher
from sqlalchemy.orm import Session, sessionmaker

from friday.core.db import session_scope
from friday.core.navs.models import FundNav

# Parag Parikh NAVs for a SIP on the 5th: 5 Feb is a holiday and 5 Apr a Sunday.
NAVS = {
    date(2026, 1, 5): "80",
    date(2026, 1, 6): "81",
    date(2026, 2, 6): "83.3333",
    date(2026, 3, 5): "75.25",
    date(2026, 4, 6): "90.1",
    date(2026, 4, 10): "91",
}


@pytest.fixture
def api(client: TestClient, funds: dict[str, int], fetcher: FakeNavFetcher) -> TestClient:
    client.app.state.nav_fetcher = fetcher
    return client


@pytest.fixture
def navs(factory: sessionmaker[Session], funds: dict[str, int]) -> None:
    with session_scope(factory) as session:
        for day, nav in NAVS.items():
            session.add(
                FundNav(instrument_id=funds[PARAG], nav_date=day, nav=Decimal(nav), source="mfapi")
            )


def sip(funds, **extra) -> dict:
    return {
        "instrument_id": funds[PARAG],
        "amount": "5000",
        "day": 5,
        "start_date": "2026-01-01",
        **extra,
    }


def lump(funds, **extra) -> dict:
    return {"instrument_id": funds[PARAG], "buy_date": "2026-01-06", "amount": "100000", **extra}


def lots(holding: dict) -> list[tuple]:
    return [
        (lot["kind"], lot["buy_date"], lot["nav"], lot["units"], lot["units_remaining"])
        for lot in holding["lots"]
    ]


def test_sip_instalments_and_a_lump_sum(api: TestClient, funds, navs) -> None:
    created = api.post("/api/v1/sips", json=sip(funds))
    assert created.status_code == 201, created.text

    response = api.post("/api/v1/lots", json=lump(funds))

    assert response.status_code == 201, response.text
    holding = response.json()
    assert lots(holding) == [
        ("sip", "2026-01-05", "80", "62.500", "62.500"),  # 5,000 / 80
        ("lump_sum", "2026-01-06", "81", "1234.568", "1234.568"),  # 1,00,000 / 81
        ("sip", "2026-02-06", "83.3333", "60.000", "60.000"),  # 5,000 / 83.3333
        ("sip", "2026-03-05", "75.25", "66.445", "66.445"),
        ("sip", "2026-04-06", "90.1", "55.494", "55.494"),
    ]
    assert (holding["units"], holding["cost"]) == ("1479.007", "120000.00")
    assert (holding["sips"][0]["instalments"], holding["sips"][0]["active"]) == (4, True)


def test_sell_from_picked_lots_then_skip_step_up_and_undo(api: TestClient, funds, navs) -> None:
    api.post("/api/v1/sips", json=sip(funds))
    holding = api.post("/api/v1/lots", json=lump(funds)).json()
    jan, _, feb, mar, _ = [lot["id"] for lot in holding["lots"]]

    sold = api.post(
        "/api/v1/sales",
        json={
            "sale_date": "2026-04-10",
            "lots": [{"lot_id": jan, "units": "62.5"}, {"lot_id": feb, "units": "30"}],
        },
    )

    assert sold.status_code == 201, sold.text
    holding = sold.json()
    by_id = {lot["id"]: lot for lot in holding["lots"]}
    assert (by_id[jan]["units_remaining"], by_id[jan]["cost_remaining"]) == ("0.000", "0.00")
    assert (by_id[feb]["units_remaining"], by_id[feb]["cost_remaining"]) == ("30.000", "2500.00")
    assert [(s["sale_date"], s["nav"], s["units"], s["amount"]) for s in by_id[feb]["sales"]] == [
        ("2026-04-10", "91", "30", "2730.00")  # NAV of the sale date, from history
    ]
    assert by_id[jan]["sales"][0]["amount"] == "5687.50"
    # 30 + 66.445 + 55.494 + 1234.568 units; 2,500 + 5,000 + 5,000 + 1,00,000 cost
    assert (holding["units"], holding["cost"]) == ("1386.507", "112500.00")

    skipped = api.put(
        f"/api/v1/lots/{mar}", json={"buy_date": "2026-03-05", "amount": "5000", "skipped": True}
    ).json()
    assert (skipped["units"], skipped["cost"]) == ("1320.062", "107500.00")

    # A step-up: April is rebuilt at 6,000; sold and skipped instalments stay as they were.
    sip_id = holding["sips"][0]["id"]
    stepped = api.put(f"/api/v1/sips/{sip_id}", json=sip(funds, amount="6000")).json()
    assert [(lot["buy_date"], lot["amount"], lot["units"]) for lot in stepped["lots"]] == [
        ("2026-01-05", "5000", "62.500"),
        ("2026-01-06", "100000", "1234.568"),
        ("2026-02-06", "5000", "60.000"),
        ("2026-03-05", "5000", "0"),
        ("2026-04-06", "6000", "66.593"),  # 6,000 / 90.1
    ]
    assert (stepped["units"], stepped["cost"]) == ("1331.161", "108500.00")
    assert stepped["sips"][0]["instalments"] == 3

    assert api.delete(f"/api/v1/sips/{sip_id}").status_code == 409
    feb_sale = next(lot for lot in stepped["lots"] if lot["id"] == feb)["sales"][0]["id"]
    assert api.delete(f"/api/v1/sales/{feb_sale}").status_code == 204
    back = api.get(f"/api/v1/holdings/{funds[PARAG]}").json()
    assert next(lot for lot in back["lots"] if lot["id"] == feb)["units_remaining"] == "60.000"


def test_typed_statement_figures_win(api: TestClient, funds, navs) -> None:
    # What the statement says, after stamp duty.
    holding = api.post("/api/v1/lots", json=lump(funds, nav="81", units="1234.506")).json()

    assert (holding["units"], holding["lots"][0]["units"]) == ("1234.506", "1234.506")


def test_an_edited_instalment_survives_a_rebuild(api: TestClient, funds, navs) -> None:
    holding = api.post("/api/v1/sips", json=sip(funds)).json()
    feb = holding["lots"][1]

    edited = api.put(
        f"/api/v1/lots/{feb['id']}",
        json={"buy_date": "2026-02-06", "amount": "5000", "units": "59.997"},
    ).json()
    assert edited["lots"][1]["edited"] is True

    rebuilt = api.put(f"/api/v1/sips/{holding['sips'][0]['id']}", json=sip(funds, day=6)).json()
    assert [(lot["buy_date"], lot["units"]) for lot in rebuilt["lots"]] == [
        ("2026-01-06", "61.728"),  # 5,000 / 81
        ("2026-02-06", "59.997"),  # kept as edited
        # 6 Mar: the next NAV (6 Apr) is more than 10 days later, so no March instalment
        ("2026-04-06", "55.494"),
    ]


@pytest.mark.parametrize(
    ("units", "status", "message"),
    [("62.501", 409, "only 62.5 units left"), ("0", 422, "more than 0")],
)
def test_cannot_oversell(api: TestClient, funds, navs, units, status, message) -> None:
    jan = api.post("/api/v1/sips", json=sip(funds)).json()["lots"][0]["id"]

    response = api.post(
        "/api/v1/sales", json={"sale_date": "2026-04-10", "lots": [{"lot_id": jan, "units": units}]}
    )

    assert response.status_code == status
    assert message in response.json()["detail"]


def test_sale_needs_a_nav(api: TestClient, funds, navs) -> None:
    jan = api.post("/api/v1/sips", json=sip(funds)).json()["lots"][0]["id"]
    sale = {"sale_date": "2026-04-09", "lots": [{"lot_id": jan, "units": "10"}]}

    missing = api.post("/api/v1/sales", json=sale)
    typed = api.post("/api/v1/sales", json={**sale, "nav": "90.5"})

    assert missing.status_code == 422
    assert "no NAV for Parag Parikh" in missing.json()["detail"]
    assert typed.status_code == 201
    assert typed.json()["lots"][0]["sales"][0]["amount"] == "905.00"


def test_one_sale_is_one_fund(api: TestClient, funds, navs) -> None:
    jan = api.post("/api/v1/sips", json=sip(funds)).json()["lots"][0]["id"]
    other = api.post(
        "/api/v1/lots",
        json={
            "instrument_id": funds[NIFTY],
            "buy_date": "2026-01-05",
            "amount": "1000",
            "nav": "150",
        },
    ).json()["lots"][0]["id"]

    response = api.post(
        "/api/v1/sales",
        json={
            "sale_date": "2026-04-10",
            "nav": "91",
            "lots": [{"lot_id": jan, "units": "1"}, {"lot_id": other, "units": "1"}],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "All lots in one sale must be of the same fund."


def test_lots_with_sales_are_protected(api: TestClient, funds, navs) -> None:
    lot = api.post("/api/v1/lots", json=lump(funds)).json()["lots"][0]["id"]
    api.post(
        "/api/v1/sales",
        json={"sale_date": "2026-04-10", "lots": [{"lot_id": lot, "units": "1000"}]},
    )

    fewer = api.put(
        f"/api/v1/lots/{lot}", json={"buy_date": "2026-01-06", "amount": "50000", "units": "999"}
    )

    assert fewer.status_code == 409
    assert "1000 units of this lot were already sold" in fewer.json()["detail"]
    assert api.delete(f"/api/v1/lots/{lot}").status_code == 409


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"buy_date": "2026-01-07"}, "no NAV for Parag Parikh"),
        ({"buy_date": "2999-01-01", "nav": "80"}, "can't be in the future"),
        ({"amount": "0"}, "amount must be more than 0"),
    ],
)
def test_bad_lump_sums(api: TestClient, funds, navs, change, message) -> None:
    response = api.post("/api/v1/lots", json=lump(funds, **change))

    assert response.status_code == 422
    assert message in response.json()["detail"]


def test_amounts_must_be_strings(api: TestClient, funds, navs) -> None:
    assert api.post("/api/v1/lots", json=lump(funds, amount=1000)).status_code == 422


def test_only_funds(api: TestClient, funds) -> None:
    response = api.post("/api/v1/sips", json=sip(funds, instrument_id=funds["INFY"]))

    assert response.status_code == 422
    assert response.json()["detail"] == "Infosys Limited is not a mutual fund scheme."


def test_a_sip_instalment_is_skipped_not_deleted(api: TestClient, funds, navs) -> None:
    jan = api.post("/api/v1/sips", json=sip(funds)).json()["lots"][0]["id"]

    response = api.delete(f"/api/v1/lots/{jan}")

    assert response.status_code == 422
    assert "skip it instead" in response.json()["detail"]


def test_held_funds_are_tracked_and_sync_adds_instalments(api: TestClient, funds) -> None:
    # No NAVs stored yet: the SIP waits for them.
    created = api.post("/api/v1/sips", json=sip(funds, start_date="2026-10-01", day=9)).json()
    assert created["lots"] == []

    api.post("/api/v1/navs/sync")

    status = api.get("/api/v1/navs/status").json()
    assert {row["fund"]["amfi_code"]: row["used_by"] for row in status["funds"]} == {
        PARAG: ["holding"]
    }
    holding = api.get(f"/api/v1/holdings/{funds[PARAG]}").json()
    assert lots(holding) == [("sip", "2026-10-09", "88.9258", "56.227", "56.227")]
    assert api.delete(f"/api/v1/instruments/{funds[PARAG]}/tracking").status_code == 409

    summary = api.get("/api/v1/holdings").json()
    assert [(row["fund"]["amfi_code"], row["units"], row["cost"]) for row in summary] == [
        (PARAG, "56.227", "5000.00")
    ]
    assert (summary[0]["lots"], summary[0]["active_sips"], summary[0]["nav_last"]) == (
        1,
        1,
        "2026-10-23",
    )
    assert api.delete(f"/api/v1/sips/{created['sips'][0]['id']}").status_code == 204
    assert api.get("/api/v1/holdings").json() == []
