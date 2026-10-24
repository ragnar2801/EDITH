from fastapi.testclient import TestClient


def test_health_reports_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["server_time"].endswith("Z")


def test_money_and_timestamp_round_trip_exactly(client: TestClient) -> None:
    payload = {
        "money": {"amount": "1234567.89", "currency": "INR"},
        "at": "2026-10-24T09:30:00.123456+05:30",
    }

    response = client.post("/api/v1/diagnostics/echo", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "money": {"amount": "1234567.89", "currency": "INR"},
        "at": "2026-10-24T04:00:00.123456Z",  # same instant, normalised to UTC
    }


def test_large_and_tiny_amounts_keep_every_digit(client: TestClient) -> None:
    for amount in ["99999999999999.99", "0.01", "-0.10", "0"]:
        response = client.post(
            "/api/v1/diagnostics/echo",
            json={"money": {"amount": amount, "currency": "USD"}, "at": "2026-01-01T00:00:00Z"},
        )
        assert response.status_code == 200
        assert response.json()["money"]["amount"] == amount


def test_json_number_amount_is_rejected_as_problem_details(client: TestClient) -> None:
    response = client.post(
        "/api/v1/diagnostics/echo",
        json={"money": {"amount": 1234567.89, "currency": "INR"}, "at": "2026-01-01T00:00:00Z"},
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["status"] == 422
    assert body["errors"][0]["loc"] == ["body", "money", "amount"]


def test_too_many_decimal_places_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/diagnostics/echo",
        json={"money": {"amount": "1.005", "currency": "INR"}, "at": "2026-01-01T00:00:00Z"},
    )

    assert response.status_code == 422


def test_naive_timestamp_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/diagnostics/echo",
        json={"money": {"amount": "1.00", "currency": "INR"}, "at": "2026-01-01T00:00:00"},
    )

    assert response.status_code == 422


def test_unknown_currency_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/diagnostics/echo",
        json={"money": {"amount": "1.00", "currency": "EUR"}, "at": "2026-01-01T00:00:00Z"},
    )

    assert response.status_code == 422


def test_unknown_api_path_is_a_404_problem(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
