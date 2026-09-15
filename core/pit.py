"""PointInTimeStore — the Time Machine, and the reason our backtest isn't lying.

Published 2026 work is blunt about this: LLMs trained on internet-scale text have
already seen historical outcomes, so an unguarded backtest measures recall, not skill.
Most competing agent repos evaluate on windows the model memorised.

Our answer is structural rather than a promise: agents never touch raw tables. Every
read goes through here, and every query is filtered on `published_at <= sim_clock`.
There is no code path that can see the future, so lookahead is impossible by
construction instead of by discipline.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from core.signal import Signal


class PointInTimeViolation(RuntimeError):
    """Raised when something tries to read past the simulation clock."""


def _utc(when: datetime | str) -> datetime:
    if isinstance(when, str):
        when = datetime.fromisoformat(when.replace("Z", "+00:00"))
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when.astimezone(timezone.utc)


class PointInTimeStore:
    def __init__(self, conn: sqlite3.Connection, sim_clock: datetime | str | None = None):
        self.conn = conn
        self.set_clock(sim_clock or datetime.now(timezone.utc))

    # -- the clock ----------------------------------------------------------------
    def set_clock(self, when: datetime | str) -> None:
        self.sim_clock = _utc(when)

    @property
    def clock_iso(self) -> str:
        return self.sim_clock.isoformat()

    def guard(self, when: datetime | str) -> None:
        """Belt-and-braces for anything that bypasses the query helpers."""
        if _utc(when) > self.sim_clock:
            raise PointInTimeViolation(
                f"read at {_utc(when).isoformat()} is past sim clock {self.clock_iso}"
            )

    # -- reads (all PIT-filtered) --------------------------------------------------
    def signals(self, ticker: str | None = None, kind: str | None = None,
                limit: int = 200) -> list[Signal]:
        sql = "SELECT * FROM signals WHERE published_at <= ?"
        args: list[Any] = [self.clock_iso]
        if ticker:
            sql += " AND ticker = ?"
            args.append(ticker)
        if kind:
            sql += " AND kind = ?"
            args.append(kind)
        sql += " ORDER BY published_at DESC LIMIT ?"
        args.append(limit)
        return [Signal(**dict(r)) for r in self.conn.execute(sql, args)]

    def latest(self, ticker: str, kind: str) -> Signal | None:
        rows = self.signals(ticker=ticker, kind=kind, limit=1)
        return rows[0] if rows else None

    def prices(self, ticker: str, limit: int = 250) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT date, open, high, low, close, volume FROM prices "
            "WHERE ticker = ? AND published_at <= ? ORDER BY date DESC LIMIT ?",
            (ticker, self.clock_iso, limit),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def last_close(self, ticker: str) -> float | None:
        """Most recent usable close at or before the clock.

        `close IS NOT NULL` is load-bearing, not defensive tidiness. Ingestion writes a
        row as soon as a bar opens, so the newest row for a ticker whose market has not
        closed yet carries a null close. Ordering by date and taking the first row then
        returned None for every US name in the universe -- they were simply unpriceable,
        so `reprice()` skipped them, the picker could not quote them, and the rebalancer
        silently dropped any trade it proposed in them. The US half of the product was
        dead and nothing raised, because None is a perfectly ordinary value here.
        """
        row = self.conn.execute(
            "SELECT close FROM prices WHERE ticker = ? AND published_at <= ? "
            "AND close IS NOT NULL ORDER BY date DESC LIMIT 1",
            (ticker, self.clock_iso),
        ).fetchone()
        return row["close"] if row else None

    def news(self, ticker: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        sql = ("SELECT id, ticker, title, body, url, source_name, published_at "
               "FROM documents WHERE published_at <= ?")
        args: list[Any] = [self.clock_iso]
        if ticker:
            sql += " AND ticker = ?"
            args.append(ticker)
        sql += " ORDER BY published_at DESC LIMIT ?"
        args.append(limit)
        return [dict(r) for r in self.conn.execute(sql, args)]

    def chunks(self, limit: int = 500) -> list[dict[str, Any]]:
        """Embedded chunks visible at the clock — the retrieval corpus."""
        rows = self.conn.execute(
            "SELECT id, doc_id, text, embedding FROM doc_chunks "
            "WHERE published_at <= ? LIMIT ?",
            (self.clock_iso, limit),
        )
        return [dict(r) for r in rows]

    def visible_counts(self) -> dict[str, int]:
        """Drives the telemetry rail: how much of the world exists at this clock."""
        def q(table: str) -> int:
            sql = f"SELECT COUNT(*) AS c FROM {table} WHERE published_at <= ?"
            return self.conn.execute(sql, (self.clock_iso,)).fetchone()["c"]
        return {"signals": q("signals"), "prices": q("prices"), "documents": q("documents")}
