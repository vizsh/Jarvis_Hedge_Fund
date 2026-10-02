"""Append-only paper ledger. Each entry carries the hash of the one before it, so any edit
to history breaks the chain and `verify()` says exactly where. SQLite triggers also refuse
UPDATE and DELETE, so the guarantee does not rest on the application behaving."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS paper_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL, sim_clock TEXT NOT NULL, kind TEXT NOT NULL,
  ticker TEXT, side TEXT, shares INTEGER, price REAL, cost REAL, nav_after REAL,
  reason TEXT, policy TEXT, prev_hash TEXT NOT NULL, hash TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS paper_ledger_no_update BEFORE UPDATE ON paper_ledger
BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END;
CREATE TRIGGER IF NOT EXISTS paper_ledger_no_delete BEFORE DELETE ON paper_ledger
BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END;
"""
FIELDS = ("ts", "sim_clock", "kind", "ticker", "side", "shares", "price", "cost",
          "nav_after", "reason", "policy", "prev_hash")


def ensure(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def _digest(row: dict[str, Any]) -> str:
    payload = json.dumps([row.get(f) for f in FIELDS], default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def record(conn: sqlite3.Connection, *, sim_clock: str, kind: str, ticker: str | None = None,
           side: str | None = None, shares: int | None = None, price: float | None = None,
           cost: float | None = None, nav_after: float | None = None,
           reason: str = "", policy: str = "") -> dict[str, Any]:
    last = conn.execute("SELECT hash FROM paper_ledger ORDER BY id DESC LIMIT 1").fetchone()
    row = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "sim_clock": sim_clock,
           "kind": kind, "ticker": ticker, "side": side, "shares": shares, "price": price,
           "cost": cost, "nav_after": nav_after, "reason": reason, "policy": policy,
           "prev_hash": last["hash"] if last else "GENESIS"}
    row["hash"] = _digest(row)
    marks = ",".join("?" * (len(FIELDS) + 1))
    conn.execute(f"INSERT INTO paper_ledger ({','.join(FIELDS)},hash) VALUES ({marks})",
                 [row[f] for f in FIELDS] + [row["hash"]])
    conn.commit()
    return row


def entries(conn: sqlite3.Connection, limit: int = 200) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute(
        "SELECT * FROM paper_ledger ORDER BY id DESC LIMIT ?", (limit,))]


def verify(conn: sqlite3.Connection) -> dict[str, Any]:
    prev, n = "GENESIS", 0
    for r in conn.execute("SELECT * FROM paper_ledger ORDER BY id"):
        d = dict(r)
        n += 1
        if d["prev_hash"] != prev or _digest(d) != d["hash"]:
            return {"ok": False, "entries": n, "broken_at": d["id"]}
        prev = d["hash"]
    return {"ok": True, "entries": n, "head": prev[:16] if n else None}
