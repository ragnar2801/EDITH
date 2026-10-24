"""SEC ``company_tickers_exchange.json`` (D-039): ticker → CIK, for SEC filings later.

``https://www.sec.gov/files/company_tickers_exchange.json``. SEC asks every client to send
a User-Agent with a name and contact email, so this is only fetched when
``FRIDAY_SEC_USER_AGENT`` is set. Checked 2026-10-24.
"""

import json

from friday.core.instruments.sources.common import SourceFormatError

COMPANY_TICKERS = "company_tickers_exchange.json"


def parse_company_tickers(text: str) -> dict[str, str]:
    """``{"fields": ["cik", "name", "ticker", "exchange"], "data": [[320193, ...], ...]}``

    Returns ticker → 10-digit CIK. SEC writes share classes with a dash (``BRK-B``);
    Nasdaq Trader with a dot (``BRK.B``), which is what Friday stores.
    """
    try:
        payload = json.loads(text)
        fields = payload["fields"]
        cik_at, ticker_at = fields.index("cik"), fields.index("ticker")
        rows = payload["data"]
    except (ValueError, KeyError, TypeError) as error:
        raise SourceFormatError(f"{COMPANY_TICKERS} doesn't look right: {error}") from None
    tickers: dict[str, str] = {}
    for row in rows:
        ticker, cik = row[ticker_at], row[cik_at]
        if ticker and cik is not None:
            tickers.setdefault(str(ticker).upper().replace("-", "."), f"{int(cik):010d}")
    return tickers
