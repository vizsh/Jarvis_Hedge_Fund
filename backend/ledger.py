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


def simulate_tamper(conn: sqlite3.Connection, entry_id: int, field: str, value: Any,
                    rehash: bool = False, limit: int = 12) -> dict[str, Any]:
    """What WOULD happen if one stored value were edited -- computed in memory, nothing is
    written. With `rehash` the forger also recomputes that row's own fingerprint to cover
    the edit; the damage then shows up one row later, because the next entry still points at
    the old fingerprint."""
    rows = [dict(r) for r in conn.execute("SELECT * FROM paper_ledger ORDER BY id DESC LIMIT ?",
                                          (limit,))][::-1]
    out, prev, broken = [], None, None
    for r in rows:
        stored = r["hash"]
        if r["id"] == entry_id and field in FIELDS and field not in ("prev_hash", "ts"):
            r[field] = value
            if rehash:
                r["hash"] = _digest(r)
        prev_ok = prev is None or r["prev_hash"] == prev
        self_ok = _digest(r) == r["hash"]
        ok = prev_ok and self_ok and broken is None
        if not (prev_ok and self_ok) and broken is None:
            broken = r["id"]
        out.append({"id": r["id"], "ticker": r["ticker"], "side": r["side"], "shares": r["shares"],
                    "price": r["price"], "kind": r["kind"], "edited": r["id"] == entry_id,
                    "stored_hash": stored[:10], "shown_hash": r["hash"][:10],
                    "recomputed": _digest(r)[:10], "prev_ok": prev_ok, "self_ok": self_ok,
                    "ok": ok})
        prev = stored if not rehash else r["hash"]
    return {"rows": out, "broken_at": broken, "intact": broken is None}


def attempt_real_edit(conn: sqlite3.Connection, entry_id: int) -> dict[str, Any]:
    """Really try to rewrite history. The database refuses; the transaction is always rolled
    back, so this cannot change anything even if the trigger were missing."""
    conn.execute("SAVEPOINT tamper")
    try:
        conn.execute("UPDATE paper_ledger SET price = price * 0.5 WHERE id = ?", (entry_id,))
        res = {"blocked": False, "message": "edit was accepted (rolled back)"}
    except sqlite3.DatabaseError as e:
        res = {"blocked": True, "message": str(e)}
    conn.execute("ROLLBACK TO tamper")
    conn.execute("RELEASE tamper")
    return res


def seed_demo(conn: sqlite3.Connection, sim_clock: str, minimum: int = 5) -> int:
    have = conn.execute("SELECT COUNT(*) c FROM paper_ledger").fetchone()["c"]
    demo = [("TCS.NS", "BUY", 10, 3900.0), ("INFY.NS", "BUY", 25, 1500.0),
            ("HDFCBANK.NS", "SELL", 15, 1650.0), ("RELIANCE.NS", "BUY", 8, 2900.0),
            ("ITC.NS", "BUY", 100, 430.0)]
    for t, s, n, p in demo[: max(0, minimum - have)]:
        record(conn, sim_clock=sim_clock, kind="DEMO", ticker=t, side=s, shares=n, price=p,
               cost=round(n * p * 0.001, 2), nav_after=1_000_000.0, reason="Sample entry for the tamper demo")
    return max(0, minimum - have)
