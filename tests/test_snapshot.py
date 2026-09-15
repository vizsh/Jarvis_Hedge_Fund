"""Integrity checks against the real frozen snapshot.

Skipped automatically when the snapshot has not been built yet, so a fresh clone still
runs green. Run `python tools/ingest.py` to populate it.

These exist because the snapshot is built once and then trusted all day. Two bugs
already got through by hand-inspection alone: a rolling price window that silently
excluded the Covid rewind, and a ticker that 404'd into a zero-row hole while the run
still reported success.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.db import connect
from core.pit import PointInTimeStore
from risk.seed import PRICES, seed_fund

DB = Path(__file__).resolve().parent.parent / "data" / "snapshot.db"
pytestmark = pytest.mark.skipif(not DB.exists(), reason="snapshot not built")


@pytest.fixture
def conn():
    return connect(DB)


def test_every_seed_ticker_has_prices(conn):
    """A ticker in the fund with no price data is a hole the demo falls into."""
    for ticker in seed_fund().positions:
        n = conn.execute("SELECT COUNT(*) c FROM prices WHERE ticker=?",
                         (ticker,)).fetchone()["c"]
        assert n > 100, f"{ticker} has only {n} price rows"


def test_seed_prices_are_within_sane_range_of_reality(conn):
    """The hardcoded demo prices should not drift absurdly far from the snapshot."""
    for ticker, demo_price in PRICES.items():
        row = conn.execute("SELECT close FROM prices WHERE ticker=? ORDER BY date DESC "
                           "LIMIT 1", (ticker,)).fetchone()
        if row is None:
            pytest.fail(f"{ticker} missing from snapshot")
        ratio = demo_price / row["close"]
        assert 0.4 < ratio < 2.5, f"{ticker} demo {demo_price} vs actual {row['close']:.0f}"


def test_covid_window_is_present(conn):
    """The rewind is the best moment in the demo; it needs data behind it."""
    n = conn.execute("SELECT COUNT(*) c FROM prices WHERE date BETWEEN ? AND ?",
                     ("2020-02-01", "2020-04-30")).fetchone()["c"]
    assert n > 300, f"only {n} price rows in the Covid window"


def test_macro_and_tone_reach_back_to_2020(conn):
    """Rails that only start in 2022 make a 2020 rewind look broken."""
    for kind in ("dgs10", "vixcls", "news_tone"):
        row = conn.execute("SELECT MIN(published_at) m FROM signals WHERE kind=?",
                           (kind,)).fetchone()
        assert row["m"] is not None, f"{kind} absent"
        assert row["m"][:4] <= "2020", f"{kind} only reaches back to {row['m'][:10]}"


def test_no_signal_is_published_before_the_period_it_describes(conn):
    """The core lookahead invariant, asserted over every ingested row."""
    bad = conn.execute("SELECT COUNT(*) c FROM signals WHERE published_at < as_of"
                       ).fetchone()["c"]
    assert bad == 0, f"{bad} signals claim publication before their own period"


def test_snapshot_replays_the_covid_drawdown(conn):
    """End to end: the drawdown is invisible beforehand and visible afterwards."""
    pit = PointInTimeStore(conn, "2020-02-20")
    peak = pit.last_close("TCS.NS")
    pit.set_clock("2020-03-23")
    trough = pit.last_close("TCS.NS")
    assert trough < peak * 0.85, "expected a >15% drawdown across the Covid window"

    pit.set_clock("2020-02-20")
    assert pit.last_close("TCS.NS") == peak, "rewind leaked the later price"


def test_snapshot_only_fundamentals_vanish_on_rewind(conn):
    """yfinance ratios have no history. Showing a 2026 P/E on a 2020 clock would be
    a lookahead bug with good lighting."""
    pit = PointInTimeStore(conn, "2020-06-30")
    assert pit.latest("TCS.NS", "pe_ratio") is None
    pit.set_clock("2030-01-01")
    assert pit.latest("TCS.NS", "pe_ratio") is not None


def test_edgar_filing_dates_lag_their_periods(conn):
    """EDGAR is the one natively point-in-time source; prove it carries real lag."""
    row = conn.execute(
        "SELECT COUNT(*) c FROM signals WHERE source_name='SEC EDGAR' "
        "AND julianday(published_at) - julianday(as_of) > 20").fetchone()
    assert row["c"] > 0, "EDGAR rows show no filing lag -- dates may be wrong"
