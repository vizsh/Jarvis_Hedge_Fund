"""Research any listed stock: type-ahead search, on-demand fetch, and the 'analyse X' routing."""
from __future__ import annotations

import sqlite3

import pytest

from analysis import stocksearch
from backend import intents
from core import universe

FAKE = [
    {"symbol": "IRCTC.NS", "name": "Indian Railway Catering And Tourism Corporation Limited", "exchange": "NSE"},
    {"symbol": "ITC.NS", "name": "ITC", "exchange": "NSE"},
    {"symbol": "TMCV.NS", "name": "Tata Motors Limited", "exchange": "NSE"},
    {"symbol": "DMART.NS", "name": "Avenue Supermarts Limited", "exchange": "NSE"},
    {"symbol": "RELIANCE.NS", "name": "Reliance Industries", "exchange": "NSE"},
    {"symbol": "RELIGARE.NS", "name": "Religare Enterprises Limited", "exchange": "NSE"},
]


@pytest.fixture()
def fake_catalogue(monkeypatch):
    cat = [dict(e, key=stocksearch._norm(e["name"]), bare=e["symbol"].replace(".NS", "").lower()) for e in FAKE]
    monkeypatch.setattr(stocksearch, "catalogue", lambda: cat)
    monkeypatch.setattr(stocksearch, "_yahoo", lambda *a, **k: [])
    return cat


@pytest.mark.parametrize("query,first", [
    ("irct", "IRCTC.NS"), ("IRCTC", "IRCTC.NS"), ("indian railway", "IRCTC.NS"), ("tata mot", "TMCV.NS"),
    ("dmart", "DMART.NS"), ("avenue", "DMART.NS"), ("reli", "RELIANCE.NS"), ("itc", "ITC.NS"),
])
def test_search_finds_a_company_from_a_fragment_of_its_name_or_symbol(fake_catalogue, query, first):
    assert stocksearch.search(query, 5)[0]["symbol"] == first


def test_search_marks_what_is_already_covered_and_tolerates_a_typo(fake_catalogue):
    hits = {h["symbol"]: h for h in stocksearch.search("reli", 5)}
    assert hits["RELIANCE.NS"]["covered"] is True or "RELIANCE.NS" in universe.tickers()
    assert stocksearch.search("irctc", 1)[0]["covered"] in (True, False)
    assert stocksearch.search("avnue supermarts", 3)[0]["symbol"] == "DMART.NS"      # spelling tolerance
    assert stocksearch.search("", 5) == []


@pytest.mark.parametrize("text,unresolved", [
    ("analyse zomato", "zomato"), ("research Tata Motors please", "Tata Motors"), ("analyze the Dmart stock", "Dmart"),
])
def test_an_unknown_company_is_looked_up_instead_of_silently_becoming_tcs(text, unresolved):
    i = intents.parse_pattern(text)
    assert i.verb == "investigate" and i.ticker is None and i.args.get("unresolved") == unresolved


def test_known_companies_and_symbols_still_resolve_directly():
    assert intents.parse_pattern("analyse TCS").ticker == "TCS.NS"
    assert intents.parse_pattern("analyse HDFC Bank").ticker == "HDFCBANK.NS"
    assert intents.parse_pattern("analyse IRCTC.NS").ticker == "IRCTC.NS"
    assert intents.parse_pattern("analyse M&M.NS").ticker == "M&M.NS"


def test_a_fetched_stock_is_registered_and_then_resolvable_by_name(monkeypatch, tmp_path):
    from ingest import ondemand
    db = tmp_path / "snap.db"
    monkeypatch.setattr(ondemand, "DB_PATH", db)
    import core.db as coredb
    monkeypatch.setattr(coredb, "DB_PATH", db)
    monkeypatch.setattr(universe, "_extra_conn", lambda: _conn(db))
    monkeypatch.setattr(universe, "_EXTRA", {})
    monkeypatch.setattr(ondemand.S, "fetch_prices", lambda t, start: ([("FAKECO.NS", "2026-01-02", 1, 2, 1, 2, 10, "2026-01-02")], None))
    monkeypatch.setattr(ondemand.S, "fetch_yf_fundamentals", lambda t: ([], None))
    monkeypatch.setattr(ondemand.S, "fetch_yf_quarterly", lambda t: ([], None))
    monkeypatch.setattr(ondemand.S, "fetch_google_news", lambda q: ([], None))
    got = ondemand.add_stock("FAKECO.NS", "Fakeco Limited")
    assert got["ok"] and got["prices"] >= 1 and "FAKECO.NS" in universe.extras()
    assert universe.name("FAKECO.NS") == "Fakeco Limited"
    assert intents.resolve_ticker("analyse Fakeco Limited") == "FAKECO.NS"


def test_a_stock_with_no_price_history_is_not_registered(monkeypatch, tmp_path):
    from ingest import ondemand
    db = tmp_path / "snap2.db"
    monkeypatch.setattr(ondemand, "DB_PATH", db)
    import core.db as coredb
    monkeypatch.setattr(coredb, "DB_PATH", db)
    monkeypatch.setattr(universe, "_extra_conn", lambda: _conn(db))
    monkeypatch.setattr(universe, "_EXTRA", {})
    monkeypatch.setattr(ondemand.S, "fetch_prices", lambda t, start: ([], None))
    got = ondemand.add_stock("NOPE.NS", "Nope Limited")
    assert got["ok"] is False and "NOPE.NS" not in universe.extras()


def _conn(path):
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE IF NOT EXISTS extra_universe (ticker TEXT PRIMARY KEY, name TEXT, sector TEXT, added_at TEXT)")
    return c
