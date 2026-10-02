"""Scam scanner, tax shield, append-only ledger, and short spoken answers."""
from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from analysis import scanner
from analysis import shield as shield_mod
from analysis.tax import Lot
from backend import explain, ledger
from backend.session import Session
from risk.portfolio import Portfolio


@pytest.fixture(scope="module")
def session() -> Session:
    s = Session.create()
    s.reprice()
    return s


# ---------------------------------------------------------------- scanner
SCAM = ("SURE SHOT 10x multibagger! TCS profit up 300%, target Rs 9000. Buy now before Monday, "
        "insider news. Join my VIP telegram t.me/xyz. 100% guaranteed returns.")


def test_a_typical_scam_tip_is_flagged_red(session):
    r = scanner.scan(session.pit, SCAM)
    assert r["tone"] == "red" and r["score"] >= 55
    codes = {f["code"] for f in r["flags"]}
    assert {"GUARANTEE", "MULTIPLIER", "URGENCY", "INSIDER", "PAYWALL"} <= codes


def test_a_false_growth_claim_is_contradicted_by_data(session):
    r = scanner.scan(session.pit, "TCS profit up 300% last quarter")
    claim = next(c for c in r["claims"] if "300" in c["text"])
    assert claim["status"] == "CONTRADICTED"
    assert claim["source"], "a verdict must say which filing it rests on"


def test_an_absurd_price_target_is_called_out(session):
    r = scanner.scan(session.pit, "TCS target Rs 9000")
    assert any(c["status"] == "CONTRADICTED" and "pump" in c["evidence"] for c in r["claims"])


def test_an_ordinary_note_is_never_certified_safe(session):
    r = scanner.scan(session.pit, "HDFC Bank reported steady results. Reasonable to hold long term.")
    assert r["tone"] == "green"
    assert "NOT ADVICE" in r["verdict"]          # no red flags is not the same as safe


def test_unknown_companies_are_reported_not_invented(session):
    r = scanner.scan(session.pit, "ZOMATO will double, buy ZOMATO")
    assert "ZOMATO" in r["unknown"]


def test_empty_input_is_handled(session):
    assert scanner.scan(session.pit, "   ")["empty"] is True


# ---------------------------------------------------------------- tax shield
def test_shield_says_wait_when_close_to_the_one_year_mark():
    pf = Portfolio(cash=0.0, positions={"TCS.NS": 100})
    lots = {"TCS.NS": Lot("TCS.NS", 0, 1000.0, "2025-10-20")}
    out = shield_mod.shield(pf, {"TCS.NS": 1200.0}, lots, date(2026, 9, 30))
    row = out["rows"][0]
    assert row["status"] == "WAIT" and row["days_to_long_term"] == 20
    assert row["saving"] == pytest.approx(20_000 * (0.20 - 0.125))
    assert out["total_saving"] == pytest.approx(row["saving"])


def test_shield_never_guesses_a_missing_cost_basis():
    pf = Portfolio(cash=0.0, positions={"TCS.NS": 10})
    out = shield_mod.shield(pf, {"TCS.NS": 1200.0}, {}, date(2026, 9, 30))
    assert out["rows"][0]["status"] == "NO_BASIS"
    assert "tax_now" not in out["rows"][0]


def test_shield_reports_losses_and_long_term():
    pf = Portfolio(cash=0.0, positions={"A.NS": 10, "B.NS": 10})
    lots = {"A.NS": Lot("A.NS", 0, 200.0, "2026-01-01"), "B.NS": Lot("B.NS", 0, 100.0, "2024-01-01")}
    out = shield_mod.shield(pf, {"A.NS": 100.0, "B.NS": 150.0}, lots, date(2026, 9, 30))
    by = {r["ticker"]: r for r in out["rows"]}
    assert by["A.NS"]["status"] == "LOSS" and by["B.NS"]["status"] == "LONG_TERM"


# ---------------------------------------------------------------- ledger
@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    ledger.ensure(c)
    return c


def _rec(c, n):
    return ledger.record(c, sim_clock="2026-09-14", kind="TRADE", ticker=f"T{n}.NS", side="BUY",
                         shares=n, price=100.0, nav_after=1e6, reason="test")


def test_ledger_chain_verifies(conn):
    for i in range(1, 4):
        _rec(conn, i)
    v = ledger.verify(conn)
    assert v["ok"] and v["entries"] == 3


def test_ledger_refuses_edits_and_deletes(conn):
    _rec(conn, 1)
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE paper_ledger SET shares = 999")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM paper_ledger")


def test_ledger_detects_tampering_even_without_the_triggers(conn):
    for i in range(1, 4):
        _rec(conn, i)
    conn.execute("DROP TRIGGER paper_ledger_no_update")          # an attacker with raw DB access
    conn.execute("UPDATE paper_ledger SET shares = 999 WHERE id = 2")
    v = ledger.verify(conn)
    assert not v["ok"] and v["broken_at"] == 2


# ---------------------------------------------------------------- short speech
def test_spoken_answers_are_short_but_full_is_available():
    long_headline = ("Your portfolio looks well spread out. I score it 94 out of 100 against retail "
                     "investor limits — no more than 15% in one stock, 35% in one industry, and at "
                     "least 5% kept in cash.")
    a = explain.Answer(headline=long_headline, bullets=["b1 is here.", "b2 is here."], action="Do x.")
    assert len(a.spoken().split()) <= 30
    assert "—" not in a.spoken()
    assert len(a.spoken_full().split()) > len(a.spoken().split())
