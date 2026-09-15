"""SQLite schema for the frozen snapshot.

Why a frozen snapshot and not live calls: NSE's unofficial APIs are flaky and will fail
on stage, venue wifi is not a dependency worth taking, and rate limits bite during
rehearsal. It also makes point-in-time replay nearly free — it becomes one WHERE clause
over a table we already own.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "snapshot.db"

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS sources (
    name        TEXT PRIMARY KEY,
    kind        TEXT NOT NULL,
    url         TEXT,
    rows        INTEGER DEFAULT 0,
    ingested_at TEXT
);

-- every observation from every source lands here
CREATE TABLE IF NOT EXISTS signals (
    id           TEXT PRIMARY KEY,
    ticker       TEXT,
    kind         TEXT NOT NULL,
    source_type  TEXT NOT NULL,
    value_num    REAL,
    value_text   TEXT,
    as_of        TEXT NOT NULL,
    published_at TEXT NOT NULL,
    source_name  TEXT NOT NULL,
    source_uri   TEXT,
    confidence   REAL DEFAULT 1.0,
    latency_class TEXT DEFAULT 'daily'
);
CREATE INDEX IF NOT EXISTS ix_sig_pit    ON signals(published_at);
CREATE INDEX IF NOT EXISTS ix_sig_lookup ON signals(ticker, kind, published_at);

-- OHLC kept separate: it's dense, numeric, and charted directly
CREATE TABLE IF NOT EXISTS prices (
    ticker       TEXT NOT NULL,
    date         TEXT NOT NULL,
    open REAL, high REAL, low REAL, close REAL, volume REAL,
    published_at TEXT NOT NULL,
    PRIMARY KEY (ticker, date)
);
CREATE INDEX IF NOT EXISTS ix_px_pit ON prices(ticker, published_at);

-- filings / announcements / articles, chunked + embedded for retrieval
CREATE TABLE IF NOT EXISTS documents (
    id           TEXT PRIMARY KEY,
    ticker       TEXT,
    title        TEXT,
    body         TEXT,
    url          TEXT,
    source_name  TEXT,
    published_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_doc_pit ON documents(ticker, published_at);

CREATE TABLE IF NOT EXISTS doc_chunks (
    id        TEXT PRIMARY KEY,
    doc_id    TEXT NOT NULL REFERENCES documents(id),
    chunk_idx INTEGER NOT NULL,
    text      TEXT NOT NULL,
    embedding BLOB,
    published_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_chunk_pit ON doc_chunks(published_at);

-- provenance: what each desk claimed and what it cited
CREATE TABLE IF NOT EXISTS claims (
    id         TEXT PRIMARY KEY,
    run_id     TEXT NOT NULL,
    desk       TEXT NOT NULL,
    ticker     TEXT,
    claim      TEXT NOT NULL,
    stance     TEXT,
    weight     REAL,
    source_ids TEXT,
    accepted   INTEGER NOT NULL,
    sim_clock  TEXT,          -- the clock the claim was made at; calibration needs it
    created_at TEXT NOT NULL
);

-- decision ledger, also the substrate for calibration backfill
CREATE TABLE IF NOT EXISTS decisions (
    id          TEXT PRIMARY KEY,
    run_id      TEXT NOT NULL,
    sim_clock   TEXT NOT NULL,
    ticker      TEXT,
    side        TEXT,
    shares      INTEGER,
    price       REAL,
    approved    INTEGER NOT NULL,
    violations  TEXT,
    conviction  REAL,
    policy_version TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ledger (
    id         TEXT PRIMARY KEY,
    ticker     TEXT NOT NULL,
    side       TEXT NOT NULL,
    shares     INTEGER NOT NULL,
    price      REAL NOT NULL,
    cost       REAL NOT NULL,
    sim_clock  TEXT NOT NULL,
    nav_after  REAL
);
"""


def connect(path: Path | str = DB_PATH) -> sqlite3.Connection:
    path = Path(path)
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init(path: Path | str = DB_PATH) -> sqlite3.Connection:
    conn = connect(path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn
