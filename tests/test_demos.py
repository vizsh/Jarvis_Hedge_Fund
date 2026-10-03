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


