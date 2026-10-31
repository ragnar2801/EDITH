"""A lots feed shaped like the one FM builds (``friday_lots_export.dart``), with a field FM
might add one day."""

import json

import pytest
from navs.conftest import fetcher, funds  # noqa: F401 (shared fixtures)

SECURITIES = {
    "parag": {"name": "Parag flexi cap", "ticker": "122639", "security_type": "MF"},
    "nifty": {"name": "UTI nifty", "ticker": "120716", "security_type": "MF"},
    "ghost": {"name": "Closed fund", "ticker": "999999", "security_type": "MF"},
    "infy": {"name": "Infosys", "ticker": "INFY", "security_type": "STOCK"},
}
ACCOUNTS = {"grow": "grow mf", "amma": "Amma IndMoney"}


class Feed:
    def __init__(self) -> None:
        self.lots: dict[str, dict] = {}

    def lot(
        self, lot_id, security, date, units, price, *, account="grow", currency="INR", bucket=None
    ):
        """``bucket``: FM's ``(id, name)`` of the bucket the purchase was put in."""
        self.lots[lot_id] = {
            "id": lot_id,
            "security_id": security,
            "acquisition_date": f"{date}T00:00:00.000",
            "total_units": units,
            "remaining_units": units,
            "unit_price": price,
            "total_cost": units * price,
            "future_field": "x",
            "security": {"id": security, "market": "NASDAQ", **SECURITIES[security]},
            "account": {"id": account, "name": ACCOUNTS[account], "account_type": "security"},
            "currency": {"id": currency.lower(), "code": currency},
            "acquisition": {
                "id": f"t-{lot_id}",
                "type": "BUYSECURITY",
                "bucket_id": bucket[0] if bucket else None,
            },
            "bucket": {"id": bucket[0], "name": bucket[1]} if bucket else None,
            "sales": [],
        }
        return self.lots[lot_id]

    def sell(self, sale_id, lot_id, date, units, price):
        lot = self.lots[lot_id]
        lot["sales"].append(
            {
                "id": sale_id,
                "lot_id": lot_id,
                "allocated_units": units,
                "transaction": {
                    "id": f"t-{sale_id}",
                    "type": "SELLSECURITY",
                    "timestamp": f"{date}T11:30:33.264857",
                    "amount": units * price,
                    "security_units": units,
                    "unit_price_at_transaction": price,
                },
            }
        )
        lot["remaining_units"] -= units

    def body(self, **extra) -> bytes:
        return json.dumps(
            {
                "format": "fm-lots",
                "version": 1,
                "fm_schema": 32,
                "sent_at": "2026-10-31T06:00:00.000Z",
                "lots": list(self.lots.values()),
                **extra,
            }
        ).encode()


@pytest.fixture
def feed() -> Feed:
    return Feed()
