"""Write claims and decisions to the ledger.

Rejected claims are stored alongside accepted ones. That is deliberate: the record of
what the model tried to assert without evidence is part of the audit trail, and it is
the substrate for the calibration panel later (which desks were right, how often, and
on what quality of evidence).
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone

from agents.schema import DeskReport, Verdict


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_run(conn: sqlite3.Connection, reports: list[DeskReport],
             verdict: Verdict, run_id: str | None = None) -> str:
    run_id = run_id or uuid.uuid4().hex[:12]
    clock = verdict.sim_clock          # what the desk could see, not when we ran it
    rows = []
    for r in reports:
        for c in r.accepted:
            rows.append((uuid.uuid4().hex[:16], run_id, r.desk, r.ticker, c.claim,
                         c.stance.value, c.weight, json.dumps(c.source_ids), 1,
                         clock, _now()))
        for c, reason in r.rejected:
            rows.append((uuid.uuid4().hex[:16], run_id, r.desk, r.ticker,
                         c.claim, c.stance.value, c.weight,
                         json.dumps({"ids": c.source_ids, "rejected": reason.value}),
                         0, clock, _now()))
    conn.executemany(
        "INSERT OR REPLACE INTO claims (id,run_id,desk,ticker,claim,stance,weight,"
        "source_ids,accepted,sim_clock,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    return run_id


def save_decision(conn: sqlite3.Connection, run_id: str, verdict: Verdict,
                  ticker: str, side: str | None, shares: int | None,
                  price: float | None, approved: bool, violations: list[str],
                  policy_version: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO decisions (id,run_id,sim_clock,ticker,side,shares,"
        "price,approved,violations,conviction,policy_version,created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (uuid.uuid4().hex[:16], run_id, verdict.sim_clock, ticker, side, shares, price,
         int(approved), json.dumps(violations), verdict.conviction, policy_version,
         _now()))
    conn.commit()
