"""Ingestion scaffolding: upserts, source results, and per-source PIT honesty.

The interesting part of this file is `PitSafety`.

Not every free source is equally honest about time, and pretending otherwise would
quietly reintroduce the exact lookahead we built `PointInTimeStore` to prevent. Three
tiers, declared per source and carried all the way to the UI:

  EXACT       the source tells us when the fact was published (EDGAR filing dates,
              RSS pubDate, GDELT seendate, a daily close). Replay is trustworthy.

  APPROXIMATED  the source gives the period but not the release date, so we add a
              documented statutory lag (Indian quarterly results are due within 45
              days of quarter end). Directionally honest, not exact. confidence < 1.

  SNAPSHOT_ONLY  the source only ever returns TODAY's value with no history
              (yfinance trailing P/E is the big one). Stamping it with an old date
              would be a straight lookahead injection, so it is stamped with the
              ingest time and therefore correctly DISAPPEARS when you rewind.

That last tier is the one that catches people out. A rewound dashboard showing a
current P/E is not a time machine, it is a bug with good lighting.
"""
from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Iterable

from core.signal import Signal


class PitSafety(str, Enum):
    EXACT = "exact"
    APPROXIMATED = "approximated"
    SNAPSHOT_ONLY = "snapshot_only"


# Indian listed companies must file quarterly results within 45 days of period end
# (SEBI LODR reg. 33); annual within 60. Used only for APPROXIMATED sources.
QUARTERLY_FILING_LAG = timedelta(days=45)


def sid(*parts: Any) -> str:
    """Stable id, so re-running ingestion updates rows instead of duplicating them."""
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class SourceResult:
    name: str
    kind: str
    pit_safety: PitSafety
    rows: int = 0
    online: bool = False
    latency_ms: int = 0
    error: str | None = None
    notes: str = ""
    warnings: list[str] = field(default_factory=list)

    def warn(self, msg: str) -> None:
        """Per-item failures. Swallowing these silently cost real debugging time once
        already -- a source that returns zero rows while reporting itself online is
        the worst possible failure mode."""
        if len(self.warnings) < 8:
            self.warnings.append(msg[:140])

    @property
    def status_line(self) -> str:
        if not self.online:
            return f"{self.name:<22} FAILED  {self.error or ''}"[:100]
        flag = {"exact": "PIT:exact", "approximated": "PIT:approx",
                "snapshot_only": "PIT:snapshot"}[self.pit_safety.value]
        warn = f"  ({len(self.warnings)} warn)" if self.warnings else ""
        return (f"{self.name:<22} {self.rows:>6} rows  {self.latency_ms:>6}ms  "
                f"{flag}{warn}")


@dataclass
class Writer:
    """All DB writes go through here so ids and upsert semantics stay consistent."""
    conn: sqlite3.Connection
    counts: dict[str, int] = field(default_factory=dict)

    def signals(self, rows: Iterable[Signal]) -> int:
        n = 0
        for s in rows:
            self.conn.execute(
                "INSERT OR REPLACE INTO signals (id,ticker,kind,source_type,value_num,"
                "value_text,as_of,published_at,source_name,source_uri,confidence,"
                "latency_class) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (s.id, s.ticker, s.kind, s.source_type.value, s.value_num, s.value_text,
                 s.as_of.isoformat(), s.published_at.isoformat(), s.source_name,
                 s.source_uri, s.confidence, s.latency_class.value))
            n += 1
        self.conn.commit()
        return n

    def prices(self, rows: Iterable[tuple]) -> int:
        rows = list(rows)
        self.conn.executemany(
            "INSERT OR REPLACE INTO prices (ticker,date,open,high,low,close,volume,"
            "published_at) VALUES (?,?,?,?,?,?,?,?)", rows)
        self.conn.commit()
        return len(rows)

    def documents(self, rows: Iterable[tuple]) -> int:
        rows = list(rows)
        self.conn.executemany(
            "INSERT OR REPLACE INTO documents (id,ticker,title,body,url,source_name,"
            "published_at) VALUES (?,?,?,?,?,?,?)", rows)
        self.conn.commit()
        return len(rows)

    def record_source(self, r: SourceResult) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO sources (name,kind,url,rows,ingested_at) "
            "VALUES (?,?,?,?,?)",
            (r.name, r.kind, r.notes, r.rows, utcnow().isoformat()))
        self.conn.commit()
