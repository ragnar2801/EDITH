"""Search, detail and override endpoints, including searches by name, code and ISIN."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def loaded(client: TestClient, refresh) -> TestClient:
    refresh()
    return client


def search(client: TestClient, q: str, **params) -> list[dict]:
    response = client.get("/api/v1/instruments/search", params={"q": q, **params})
    assert response.status_code == 200, response.text
    return response.json()


def test_infos_finds_infosys_on_nse_first(loaded: TestClient) -> None:
    results = search(loaded, "infos")

    first = results[0]
    assert (first["symbol"], first["exchange"], first["kind"]) == ("INFY", "NSE", "stock")
    assert (first["currency"], first["asset_class"], first["exposure"]) == ("INR", "equity", "IN")
    assert first["name"] == "Infosys Limited"
    adr = next(r for r in results if r["exchange"] == "NYSE")  # the US ADR comes too
    assert (adr["symbol"], adr["currency"]) == ("INFY", "USD")


def test_parag_parikh_flexi_finds_the_direct_growth_plan(loaded: TestClient) -> None:
    [fund] = search(loaded, "parag parikh flexi")

    assert fund["amfi_code"] == "122639"
    assert (fund["plan"], fund["option"]) == ("direct", "Growth")
    assert (fund["kind"], fund["exchange"], fund["currency"]) == ("mutual_fund", None, "INR")
    assert (fund["asset_class"], fund["fund_house"]) == ("equity", "PPFAS Mutual Fund")
    assert [v["amfi_code"] for v in fund["variants"]] == ["153964", "122640", "153965"]


def test_motilal_oswal_midcap_shows_direct_growth_first(loaded: TestClient) -> None:
    # NAVAll.txt leaves Plan and Option blank for this fund; the scheme master names them.
    [fund] = search(loaded, "motilal oswal midcap")

    assert fund["amfi_code"] == "127042"
    assert (fund["plan"], fund["option"]) == ("direct", "Growth")
    [idcw] = fund["variants"]
    assert (idcw["amfi_code"], idcw["plan"], idcw["option"]) == ("127044", "direct", "IDCW")


def test_qqq_finds_the_nasdaq_etf(loaded: TestClient) -> None:
    first = search(loaded, "QQQ")[0]

    assert (first["symbol"], first["exchange"], first["kind"]) == ("QQQ", "NASDAQ", "etf")
    assert (first["currency"], first["market"], first["asset_class"]) == ("USD", "US", "equity")


@pytest.mark.parametrize(
    ("q", "expected"),
    [
        ("zomato", "ETERNAL"),  # old name
        ("MCDOWELL-N", "UNITDSPR"),  # old symbol
        ("m&m", "M&M"),
        ("brk.b", "BRK.B"),
        ("INE009A01021", "INFY"),  # ISIN
        ("nifty 50 bees", "NIFTYBEES"),
        ("ppfas", None),  # fund house
    ],
)
def test_other_ways_to_find_things(loaded: TestClient, q: str, expected: str | None) -> None:
    first = search(loaded, q)[0]
    if expected:
        assert first["symbol"] == expected
    else:
        assert first["amfi_code"] == "122639"


def test_scheme_code_is_an_exact_match(loaded: TestClient) -> None:
    assert search(loaded, "153965")[0]["amfi_code"] == "153965"


def test_closed_schemes_are_hidden_unless_asked_for(loaded: TestClient) -> None:
    assert search(loaded, "fixed horizon") == []

    closed = search(loaded, "fixed horizon", include_inactive="true")
    assert closed and not closed[0]["is_active"]


def test_filters(loaded: TestClient) -> None:
    assert {r["market"] for r in search(loaded, "infosys", market="US")} == {"US"}
    assert {r["kind"] for r in search(loaded, "nifty", kind="etf")} == {"etf"}


def test_nothing_to_search_for(loaded: TestClient) -> None:
    assert search(loaded, "!!!") == []
    assert loaded.get("/api/v1/instruments/search", params={"q": ""}).status_code == 422


def test_instrument_detail(loaded: TestClient) -> None:
    eternal = search(loaded, "eternal")[0]

    response = loaded.get(f"/api/v1/instruments/{eternal['id']}")

    assert response.status_code == 200
    detail = response.json()
    assert detail["isin"] == "INE758T01015"
    assert detail["listed_on"] == "2021-07-23"
    assert {"kind": "symbol", "value": "ZOMATO", "changed_on": "2025-04-09"} in detail["aliases"]
    assert detail["rule"] == {
        "asset_class": "equity",
        "allocation": [{"bucket": "equity", "percent": "100"}],
        "exposure": "IN",
    }
    assert detail["override"] is None


def test_unknown_instrument_is_a_404_problem(loaded: TestClient) -> None:
    response = loaded.get("/api/v1/instruments/99999")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")


def test_set_and_clear_my_classification(loaded: TestClient) -> None:
    fund = search(loaded, "axis retirement")[0]
    assert fund["asset_class"] == "unclassified"
    url = f"/api/v1/instruments/{fund['id']}/classification"

    response = loaded.put(
        url,
        json={
            "allocation": [
                {"bucket": "equity", "percent": "70.50"},
                {"bucket": "debt", "percent": "29.50"},
            ],
            "exposure": "IN",
            "note": "aggressive plan, from the factsheet",
        },
    )

    assert response.status_code == 200
    detail = response.json()
    assert detail["asset_class"] == "hybrid"
    assert detail["override"]["allocation"] == [
        {"bucket": "equity", "percent": "70.50"},
        {"bucket": "debt", "percent": "29.50"},
    ]
    assert detail["override"]["note"] == "aggressive plan, from the factsheet"
    assert detail["rule"]["asset_class"] == "unclassified"  # the rule is still shown
    assert search(loaded, "axis retirement")[0]["asset_class"] == "hybrid"

    cleared = loaded.delete(url).json()
    assert cleared["override"] is None
    assert cleared["asset_class"] == "unclassified"


@pytest.mark.parametrize(
    ("allocation", "message"),
    [
        ([{"bucket": "equity", "percent": "60"}], "add up to 100"),
        (
            [{"bucket": "equity", "percent": "50"}, {"bucket": "equity", "percent": "50"}],
            "listed twice",
        ),
        ([{"bucket": "equity", "percent": "120"}, {"bucket": "debt", "percent": "-20"}], "between"),
    ],
)
def test_invalid_classification_is_rejected(
    loaded: TestClient, allocation: list[dict], message: str
) -> None:
    fund = search(loaded, "parag parikh flexi")[0]

    response = loaded.put(
        f"/api/v1/instruments/{fund['id']}/classification",
        json={"allocation": allocation, "exposure": "IN"},
    )

    assert response.status_code == 422
    assert message in response.json()["detail"]


def test_percent_must_be_a_string(loaded: TestClient) -> None:
    fund = search(loaded, "parag parikh flexi")[0]

    response = loaded.put(
        f"/api/v1/instruments/{fund['id']}/classification",
        json={"allocation": [{"bucket": "equity", "percent": 100}], "exposure": "IN"},
    )

    assert response.status_code == 422


def test_sources_report_the_last_refresh(loaded: TestClient) -> None:
    sources = {s["source"]: s for s in loaded.get("/api/v1/instruments/sources").json()}

    assert set(sources) == {"nse", "amfi", "us"}
    assert sources["nse"]["active_instruments"] == 12
    assert sources["us"]["last_success"]["status"] == "ok"
    assert sources["us"]["last_success"]["finished_at"].endswith("Z")


def test_sources_before_any_refresh(client: TestClient) -> None:
    sources = client.get("/api/v1/instruments/sources").json()

    assert all(s["last_run"] is None and s["active_instruments"] == 0 for s in sources)


def test_refresh_from_the_api_downloads_the_lists(client: TestClient, lists) -> None:
    from friday.core.instruments.download import FolderFetcher

    client.app.state.list_fetcher = FolderFetcher(lists)

    response = client.post("/api/v1/instruments/refresh", json={"sources": ["amfi"]})

    assert response.status_code == 200, response.text
    [amfi] = response.json()
    assert (amfi["source"], amfi["status"], amfi["message"]) == ("amfi", "ok", None)
    assert amfi["added"] > 0
    assert search(client, "parag parikh flexi")[0]["amfi_code"] == "122639"
    sources = {s["source"]: s for s in client.get("/api/v1/instruments/sources").json()}
    assert sources["amfi"]["last_success"]["added"] == amfi["added"]
    assert sources["nse"]["last_run"] is None

    again = client.post("/api/v1/instruments/refresh", json={"sources": ["amfi"]}).json()
    assert (again[0]["added"], again[0]["updated"]) == (0, 0)


def test_refresh_every_list_in_order_and_report_a_failed_one(client: TestClient, lists) -> None:
    from friday.core.instruments.download import FolderFetcher

    (lists / "nasdaqlisted.txt").unlink()  # the US list didn't download
    client.app.state.list_fetcher = FolderFetcher(lists)

    response = client.post("/api/v1/instruments/refresh")

    assert response.status_code == 200, response.text
    results = response.json()
    assert [r["source"] for r in results] == ["nse", "amfi", "us"]
    assert [r["status"] for r in results] == ["ok", "ok", "failed"]
    assert "not found" in results[2]["message"]
