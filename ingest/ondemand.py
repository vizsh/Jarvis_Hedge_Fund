"""Fetch one stock's prices, fundamentals and headlines into the live snapshot, on request.

The same adapters the full ingest uses, pointed at a single ticker. A dead source degrades the run;
it never fails it. The stock is only registered (and so only offered to the research desks) once
price history has actually arrived, because desks over an empty pack return confident nonsense.
"""
from __future__ import annotations

from datetime import datetime, timezone

from core import universe
from core.db import DB_PATH, init
from ingest import sources as S
from ingest.base import Writer

START = "2019-06-01"


def add_stock(symbol: str, name: str | None = None) -> dict:
    """Blocking (network). Run in a thread. Returns what arrived."""
    symbol = symbol.strip().upper()
    label = name or universe.name(symbol)
    conn = init(str(DB_PATH))
    w = Writer(conn)
    got: dict = {"symbol": symbol, "name": label, "prices": 0, "signals": 0, "documents": 0, "errors": []}

    def attempt(what: str, fn) -> None:
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            got["errors"].append(f"{what}: {type(e).__name__}")

    def prices():
        rows, _ = S.fetch_prices([symbol], START)
        got["prices"] = w.prices(rows) or len(rows)

    def ratios():
        sigs, _ = S.fetch_yf_fundamentals([symbol])
        got["signals"] += w.signals(sigs) or len(sigs)

    def quarterly():
        sigs, _ = S.fetch_yf_quarterly([symbol])
        got["signals"] += w.signals(sigs) or len(sigs)

    def news():
        rows, _ = S.fetch_google_news({symbol: f"{label} stock"})
        got["documents"] = w.documents(rows) or len(rows)

    attempt("prices", prices)
    if not got["prices"]:
        conn.close()
        got["ok"] = False
        got["message"] = f"No price history found for {symbol}."
        return got
    attempt("ratios", ratios)
    attempt("quarterly", quarterly)
    attempt("news", news)
    conn.commit()
    conn.close()
    universe.register_extra(symbol, label)
    got["ok"] = True
    got["added_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return got
