"""Named, persisted portfolios — so the system works on YOUR money, not a demo fund.

This is the change that turns the project from a diorama into a tool. Everything else
was already there; what was missing was any way to put your own holdings in.

Presets exist because an empty form is a dead end. A first-time user has no idea what
a "concentrated" portfolio looks like, so we ship three that make the point instantly:
one that is realistically over-concentrated (which is what most retail portfolios
actually look like), one that is diversified, and the original demo fund.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from core import universe

SCHEMA = """
-- Cost basis. Separate from holdings because it is OPTIONAL: the app works without
-- it, and tax is simply reported as unknown until the user supplies a purchase.
CREATE TABLE IF NOT EXISTS lots (
    portfolio_id TEXT NOT NULL,
    ticker       TEXT NOT NULL,
    shares       INTEGER NOT NULL,
    buy_price    REAL NOT NULL,
    buy_date     TEXT NOT NULL,
    PRIMARY KEY (portfolio_id, ticker)
);

CREATE TABLE IF NOT EXISTS portfolios (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    cash       REAL NOT NULL,
    positions  TEXT NOT NULL,        -- json {ticker: shares}
    is_preset  INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Preset:
    key: str
    name: str
    blurb: str
    cash: float
    positions: dict[str, int]


# Weights, not share counts: share counts depend on price, and prices move. Each preset
# is converted to shares against the live snapshot when it is loaded.
PRESETS: list[dict[str, Any]] = [
    {
        "key": "typical_retail",
        "name": "Typical Indian retail",
        "blurb": "What most portfolios actually look like: heavy in IT and banks, "
                 "because that is what everyone owns. Deliberately over-concentrated.",
        "cash_pct": 0.08,
        "weights": {
            "TCS.NS": 0.14, "INFY.NS": 0.12, "HCLTECH.NS": 0.08, "WIPRO.NS": 0.06,
            "HDFCBANK.NS": 0.13, "ICICIBANK.NS": 0.11, "SBIN.NS": 0.07,
            "RELIANCE.NS": 0.10, "ITC.NS": 0.06, "TATASTEEL.NS": 0.05,
        },
    },
    {
        "key": "diversified",
        "name": "Diversified",
        "blurb": "Spread across nine sectors, nothing above 5%. This is what the "
                 "firewall is trying to get you to.",
        "cash_pct": 0.12,
        "weights": {
            "TCS.NS": 0.05, "INFY.NS": 0.04,
            "HDFCBANK.NS": 0.05, "ICICIBANK.NS": 0.04, "SBIN.NS": 0.04,
            "HINDUNILVR.NS": 0.05, "ITC.NS": 0.04, "NESTLEIND.NS": 0.04,
            "MARUTI.NS": 0.05, "M&M.NS": 0.04,
            "SUNPHARMA.NS": 0.05, "CIPLA.NS": 0.04,
            "ULTRACEMCO.NS": 0.05, "TATASTEEL.NS": 0.04,
            "RELIANCE.NS": 0.05, "NTPC.NS": 0.04,
            "LT.NS": 0.05, "BHARTIARTL.NS": 0.04, "TITAN.NS": 0.04,
        },
    },
    {
        "key": "demo_fund",
        "name": "Demo fund",
        "blurb": "Compliant at rest and parked just under the 30% technology cap — "
                 "the setup the scripted walkthrough uses.",
        "cash_pct": 0.53,
        "weights": {
            "TCS.NS": 0.048, "INFY.NS": 0.048, "WIPRO.NS": 0.048,
            "HCLTECH.NS": 0.048, "TECHM.NS": 0.048, "MPHASIS.NS": 0.048,
            "HDFCBANK.NS": 0.045, "ICICIBANK.NS": 0.045,
            "ITC.NS": 0.045, "HINDUNILVR.NS": 0.045,
        },
    },
]

DEFAULT_NAV = 1_000_000.0      # 10 lakh — a realistic retail starting point


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def preset_to_positions(preset: dict, prices: dict[str, float],
                        nav: float = DEFAULT_NAV) -> tuple[float, dict[str, int]]:
    """Convert target weights to whole share counts at current prices.

    Rounding down means the realised weights land slightly under target and the
    remainder falls into cash, which is the right direction to err: a preset that
    silently breached its own limits on load would be a bad first impression.
    """
    positions: dict[str, int] = {}
    spent = 0.0
    for ticker, weight in preset["weights"].items():
        price = prices.get(ticker)
        if not price:
            continue
        shares = int((nav * weight) / price)
        if shares > 0:
            positions[ticker] = shares
            spent += shares * price
    return round(nav - spent, 2), positions


def save(conn: sqlite3.Connection, name: str, cash: float,
         positions: dict[str, int], portfolio_id: str | None = None,
         is_preset: bool = False) -> str:
    pid = portfolio_id or uuid.uuid4().hex[:12]
    existing = conn.execute("SELECT created_at FROM portfolios WHERE id = ?",
                            (pid,)).fetchone()
    created = existing["created_at"] if existing else _now()
    conn.execute(
        "INSERT OR REPLACE INTO portfolios (id,name,cash,positions,is_preset,"
        "created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
        (pid, name, float(cash), json.dumps(positions), int(is_preset), created, _now()))
    conn.commit()
    return pid


def load(conn: sqlite3.Connection, portfolio_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM portfolios WHERE id = ?", (portfolio_id,)).fetchone()
    if not row:
        return None
    return {"id": row["id"], "name": row["name"], "cash": row["cash"],
            "positions": {k: int(v) for k, v in json.loads(row["positions"]).items()},
            "is_preset": bool(row["is_preset"]), "updated_at": row["updated_at"]}


def list_all(conn: sqlite3.Connection) -> list[dict]:
    return [{"id": r["id"], "name": r["name"], "cash": r["cash"],
             "holdings": len(json.loads(r["positions"])),
             "is_preset": bool(r["is_preset"]), "updated_at": r["updated_at"]}
            for r in conn.execute(
                "SELECT * FROM portfolios ORDER BY is_preset, updated_at DESC")]


def delete(conn: sqlite3.Connection, portfolio_id: str) -> bool:
    cur = conn.execute("DELETE FROM portfolios WHERE id = ? AND is_preset = 0",
                       (portfolio_id,))
    conn.commit()
    return cur.rowcount > 0


def parse_pasted(text: str) -> tuple[dict[str, int], list[str]]:
    """Read holdings out of whatever the user pasted.

    Brokers all export differently and nobody is going to reformat a CSV by hand, so
    this accepts anything shaped like "<name or symbol> <quantity>" per line, with
    commas, tabs, or spaces between. Returns (positions, unrecognised lines) -- the
    rejects are shown back rather than silently dropped, because a holding that
    quietly vanished is worse than one that failed loudly.
    """
    positions: dict[str, int] = {}
    rejected: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.lower().startswith(("symbol", "ticker", "stock", "instrument")):
            continue
        parts = [p.strip() for p in line.replace("\t", ",").split(",") if p.strip()]
        if len(parts) < 2:
            parts = line.rsplit(" ", 1)
        if len(parts) < 2:
            rejected.append(raw)
            continue
        symbol_part, qty_part = parts[0], parts[-1]
        ticker = universe.resolve(symbol_part)
        try:
            qty = int(float(qty_part.replace(",", "")))
        except ValueError:
            rejected.append(raw)
            continue
        if not ticker or qty <= 0:
            rejected.append(raw)
            continue
        positions[ticker] = positions.get(ticker, 0) + qty
    return positions, rejected


def save_lot(conn: sqlite3.Connection, portfolio_id: str, ticker: str,
             shares: int, buy_price: float, buy_date: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO lots (portfolio_id,ticker,shares,buy_price,buy_date) "
        "VALUES (?,?,?,?,?)",
        (portfolio_id, ticker, int(shares), float(buy_price), buy_date))
    conn.commit()


def load_lots(conn: sqlite3.Connection, portfolio_id: str | None) -> dict:
    """Cost basis for a portfolio, keyed by ticker. Empty is a valid answer."""
    from analysis.tax import Lot
    if not portfolio_id:
        return {}
    return {r["ticker"]: Lot(ticker=r["ticker"], shares=r["shares"],
                             buy_price=r["buy_price"], buy_date=r["buy_date"])
            for r in conn.execute("SELECT * FROM lots WHERE portfolio_id = ?",
                                  (portfolio_id,))}


def delete_lots(conn: sqlite3.Connection, portfolio_id: str) -> None:
    conn.execute("DELETE FROM lots WHERE portfolio_id = ?", (portfolio_id,))
    conn.commit()
