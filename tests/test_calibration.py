"""Calibration scoring tests.

The panel exists to report a result honestly, including an unflattering one, so the
scoring has to be right in both directions: a desk that called it correctly must score
well, and one that did not must not be quietly rescued by the arithmetic.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest

from backend.calibration import NEUTRAL_BRIER, ensure_sim_clock_column, forward_return, score
from core.db import init


def _prices(conn, ticker: str, series: list[tuple[str, float]]) -> None:
    conn.executemany(
        "INSERT OR REPLACE INTO prices VALUES (?,?,?,?,?,?,?,?)",
        [(ticker, d, 0, 0, 0, c, 0, d) for d, c in series])
    conn.commit()


def _claim(conn, desk: str, ticker: str, stance: str, weight: float, clock: str) -> None:
    conn.execute(
        "INSERT INTO claims (id,run_id,desk,ticker,claim,stance,weight,source_ids,"
        "accepted,sim_clock,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (uuid.uuid4().hex[:16], "r1", desk, ticker, "c", stance, weight,
         json.dumps(["E1"]), 1, clock, datetime.now(timezone.utc).isoformat()))
    conn.commit()


@pytest.fixture
def conn():
    c = init(":memory:")
    ensure_sim_clock_column(c)
    # A clean 20% rise over the scoring window.
    _prices(c, "UP.NS", [("2024-01-01", 100.0), ("2024-01-10", 110.0),
                         ("2024-02-05", 120.0), ("2024-03-01", 125.0)])
    # A clean fall.
    _prices(c, "DOWN.NS", [("2024-01-01", 100.0), ("2024-01-10", 90.0),
                           ("2024-02-05", 80.0), ("2024-03-01", 78.0)])
    return c


def test_forward_return_is_measured_from_the_claim_clock(conn):
    r = forward_return(conn, "UP.NS", "2024-01-01", 7)
    assert r == pytest.approx(0.10, abs=0.01)


def test_forward_return_is_none_past_the_end_of_the_snapshot(conn):
    """An unresolved call must be excluded, never counted as a miss."""
    assert forward_return(conn, "UP.NS", "2024-03-01", 30) is None


def test_a_correct_call_scores_a_hit(conn):
    _claim(conn, "Quant", "UP.NS", "bull", 0.8, "2024-01-01")
    d = score(conn)["desks"][0]
    assert d["hit_rate"] == 1.0
    assert d["brier"] < NEUTRAL_BRIER


def test_a_wrong_confident_call_scores_worse_than_guessing(conn):
    _claim(conn, "Quant", "DOWN.NS", "bull", 0.9, "2024-01-01")
    d = score(conn)["desks"][0]
    assert d["hit_rate"] == 0.0
    assert d["brier"] > NEUTRAL_BRIER
    assert d["beats_coin_flip"] is False


def test_confidence_is_penalised_not_just_direction(conn):
    """Right 100% of the time at 0.55 confidence should not look identical to right
    100% of the time at 0.95 -- only Brier separates them."""
    _claim(conn, "Timid", "UP.NS", "bull", 0.1, "2024-01-01")
    _claim(conn, "Bold", "UP.NS", "bull", 0.9, "2024-01-01")
    desks = {d["desk"]: d for d in score(conn)["desks"]}
    assert desks["Timid"]["hit_rate"] == desks["Bold"]["hit_rate"] == 1.0
    assert desks["Bold"]["brier"] < desks["Timid"]["brier"]


def test_neutral_claims_are_excluded(conn):
    """A neutral claim makes no directional call, so it cannot be right or wrong."""
    _claim(conn, "Quant", "UP.NS", "neutral", 0.9, "2024-01-01")
    assert score(conn)["total_scored"] == 0


def test_one_sided_desk_is_flagged(conn):
    """A desk that nearly always says the same thing carries no information."""
    for _ in range(9):
        _claim(conn, "Doomer", "UP.NS", "bear", 0.7, "2024-01-01")
    _claim(conn, "Doomer", "DOWN.NS", "bull", 0.5, "2024-01-01")
    d = score(conn)["desks"][0]
    assert d["one_sided"] is True
    assert d["bear_share"] >= 0.85


def test_systematic_bias_is_reported_across_desks(conn):
    for i in range(20):
        _claim(conn, f"D{i % 4}", "UP.NS", "bear", 0.6, "2024-01-01")
    r = score(conn)
    assert r["systematic_bias"] is True
    assert r["bear_share"] == 1.0


def test_small_sample_is_flagged(conn):
    _claim(conn, "Quant", "UP.NS", "bull", 0.6, "2024-01-01")
    assert score(conn)["sample_warning"] is True


def test_result_always_carries_the_training_contamination_caveat(conn):
    """PIT control stops the desks SEEING the future; it cannot unread the model's
    training data. The number must never appear without that caveat attached."""
    _claim(conn, "Quant", "UP.NS", "bull", 0.6, "2024-01-01")
    assert "upper bound" in score(conn)["caveat"]


def test_migration_adds_the_column_without_losing_claims(conn):
    conn.execute("ALTER TABLE claims RENAME TO claims_old")
    conn.execute("CREATE TABLE claims (id TEXT PRIMARY KEY, run_id TEXT, desk TEXT,"
                 " ticker TEXT, claim TEXT, stance TEXT, weight REAL, source_ids TEXT,"
                 " accepted INTEGER, created_at TEXT)")
    conn.execute("INSERT INTO claims VALUES ('x','r','Quant','UP.NS','c','bull',0.6,"
                 "'[]',1,'now')")
    conn.commit()
    ensure_sim_clock_column(conn)
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(claims)")}
    assert "sim_clock" in cols
    assert conn.execute("SELECT COUNT(*) c FROM claims").fetchone()["c"] == 1
