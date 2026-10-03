import sqlite3

from backend import ledger


def _db():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    ledger.ensure(c)
    ledger.seed_demo(c, "2024-01-01")
    return c


def test_naive_edit_is_detected_at_the_edited_row():
    r = ledger.simulate_tamper(_db(), 2, "price", 1.0)
    assert not r["intact"] and r["broken_at"] == 2


def test_rehashed_edit_is_caught_one_row_later():
    r = ledger.simulate_tamper(_db(), 2, "price", 1.0, rehash=True)
    assert r["broken_at"] == 3


def test_real_edit_is_refused_and_chain_survives():
    c = _db()
    assert ledger.attempt_real_edit(c, 2)["blocked"]
    assert ledger.verify(c)["ok"]




def test_goal_fan_orders_percentiles_and_worse_returns_lower_odds():
    from analysis import goal
    from backend import portfolios
    from backend.session import Session
    s = Session.create()
    s.reprice()
    d = portfolios.load(s.conn, "preset_typical_retail")
    s.set_portfolio(d["name"], d["cash"], d["positions"], "preset_typical_retail")
    a = goal.fan(s.pit, s.portfolio, s.prices, 10000, 10, 3_000_000)
    b = goal.fan(s.pit, s.portfolio, s.prices, 10000, 10, 3_000_000, haircut=0.3)
    last = a["points"][-1]
    assert last["p10"] <= last["p50"] <= last["p90"]
    assert b["prob_target"] <= a["prob_target"]
