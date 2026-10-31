"""The FM status endpoint, read-only FM purchases, and the receiver the phone talks to."""

import http.client

import pytest
from fastapi.testclient import TestClient
from navs.conftest import PARAG
from sqlalchemy import select

from friday.core.db import session_scope
from friday.core.fm.receiver import FmReceiver, ensure_token
from friday.core.fm.service import handle_push, import_feed
from friday.core.holdings.models import Lot


def test_status_before_anything_is_sent(client: TestClient) -> None:
    assert client.get("/api/v1/fm").json() == {"receiver": None, "last_import": None}


def test_status_shows_the_last_import(client, feed, factory, funds) -> None:
    feed.lot("a", "parag", "2025-04-01", 100, 20)
    import_feed(factory, feed.body())
    last = client.get("/api/v1/fm").json()["last_import"]
    assert (last["status"], last["lots"], last["sent_at"]) == ("ok", 1, "2026-10-31T06:00:00Z")


@pytest.fixture
def fm_holding(client, feed, factory, funds) -> dict:
    feed.lot("a", "parag", "2025-04-01", 100, 20)
    feed.sell("s1", "a", "2026-02-14", 40, 30)
    import_feed(factory, feed.body())
    return client.get(f"/api/v1/holdings/{funds[PARAG]}").json()


def test_fm_purchases_are_read_only(client, fm_holding) -> None:
    lot = fm_holding["lots"][0]
    assert (lot["source"], lot["note"], lot["units_remaining"]) == ("fm", "grow mf", "60.00000000")

    edit = {"buy_date": "2025-04-01", "amount": "1000", "nav": "10"}
    sale = {"sale_date": "2026-03-01", "nav": "30", "lots": [{"lot_id": lot["id"], "units": "1"}]}
    for response in (
        client.put(f"/api/v1/lots/{lot['id']}", json=edit),
        client.delete(f"/api/v1/lots/{lot['id']}"),
        client.post("/api/v1/sales", json=sale),
        client.delete(f"/api/v1/sales/{lot['sales'][0]['id']}"),
    ):
        assert response.status_code == 409
        assert response.json()["detail"] == "This purchase comes from FM; change it there."


@pytest.fixture
def receiver(settings, factory):
    server = FmReceiver(
        token=ensure_token(settings.fm_dir),
        host="127.0.0.1",
        port=0,
        on_push=lambda body: handle_push(factory, body),
    )
    server.start()
    yield server
    server.stop()


def call(server: FmReceiver, method: str, path: str, body: bytes = b"", token: str | None = None):
    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=10)
    headers = {"x-sync-token": token} if token is not None else {}
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    answer = (response.status, response.read().decode())
    connection.close()
    return answer


def test_the_phone_can_send_its_lots(receiver, feed, factory, funds, settings) -> None:
    feed.lot("a", "parag", "2025-04-01", 100, 20)
    body = feed.body()

    assert call(receiver, "GET", "/health") == (200, "ok")
    assert call(receiver, "POST", "/lots", body, token="wrong")[0] == 401
    assert call(receiver, "POST", "/db", body, token=receiver.token)[0] == 404
    assert call(receiver, "GET", "/api/v1/fm")[0] == 404  # nothing but the lots is served

    assert call(receiver, "POST", "/lots", body, token=receiver.token) == (
        200,
        "Friday imported 1 purchases and 0 sales of 1 funds.",
    )
    with session_scope(factory) as session:
        assert session.scalars(select(Lot.source_id)).all() == ["a"]
    assert [path.name for path in settings.fm_dir.iterdir()] == ["token.txt"]  # feed not kept

    assert call(receiver, "POST", "/lots", b"not json", token=receiver.token) == (
        422,
        "Friday couldn't read the lots: it isn't JSON",
    )


def test_the_token_is_kept(settings) -> None:
    assert ensure_token(settings.fm_dir) == ensure_token(settings.fm_dir)
