"""Point-in-time tests -- the Time Machine.

These guard the one claim no competing repo can make: that the agents physically
cannot see the future. If any of these break, the backtest is lying.
"""
from __future__ import annotations

import pytest

from core.db import init
from core.pit import PointInTimeStore, PointInTimeViolation
from core.signal import Signal, SourceType


@pytest.fixture
def pit() -> PointInTimeStore:
    conn = init(":memory:")
    conn.executemany("INSERT INTO prices VALUES (?,?,?,?,?,?,?,?)", [
        ("TCS.NS", "2020-01-15", 0, 0, 0, 2180.0, 1e6, "2020-01-15"),
        ("TCS.NS", "2020-02-14", 0, 0, 0, 2100.0, 1e6, "2020-02-14"),
        ("TCS.NS", "2020-03-23", 0, 0, 0, 1506.0, 9e6, "2020-03-23"),
        ("TCS.NS", "2020-06-30", 0, 0, 0, 2050.0, 3e6, "2020-06-30"),
    ])
    conn.executemany("INSERT INTO documents VALUES (?,?,?,?,?,?,?)", [
        ("d1", "TCS.NS", "IT spend outlook steady", "b", "u", "GoogleNews", "2020-01-20"),
        ("d2", "TCS.NS", "Covid-19 selloff deepens", "b", "u", "GoogleNews", "2020-03-20"),
        ("d3", "TCS.NS", "Recovery underway", "b", "u", "GoogleNews", "2020-06-15"),
    ])
    conn.commit()
    return PointInTimeStore(conn, "2020-02-20")


def test_future_prices_are_invisible(pit):
    assert pit.last_close("TCS.NS") == 2100.0          # pre-crash
    assert pit.visible_counts()["prices"] == 2


def test_rewinding_hides_what_was_already_seen(pit):
    pit.set_clock("2020-06-30")
    assert pit.last_close("TCS.NS") == 2050.0
    pit.set_clock("2020-02-20")
    assert pit.last_close("TCS.NS") == 2100.0, "rewind must not leak the later price"


def test_crash_news_invisible_before_it_happened(pit):
    titles = [n["title"] for n in pit.news("TCS.NS")]
    assert "Covid-19 selloff deepens" not in titles
    pit.set_clock("2020-03-25")
    assert "Covid-19 selloff deepens" in [n["title"] for n in pit.news("TCS.NS")]


def test_price_series_is_truncated_not_masked(pit):
    """The agent must not even receive future rows -- masking downstream is not enough."""
    assert all(row["date"] <= "2020-02-20" for row in pit.prices("TCS.NS"))


def test_guard_rejects_explicit_future_read(pit):
    with pytest.raises(PointInTimeViolation):
        pit.guard("2021-01-01")


def test_signal_rejects_publication_before_the_period_it_describes():
    """Filtering on as_of instead of published_at is the classic lookahead bug."""
    with pytest.raises(ValueError):
        Signal(id="bad", kind="eps", source_type=SourceType.FUNDAMENTAL, value_num=1.0,
               as_of="2024-03-31", published_at="2024-01-01", source_name="EDGAR")


def test_quarterly_result_hidden_until_filing_date():
    """Q1 ends in March but nobody can read it until the May filing."""
    conn = init(":memory:")
    conn.execute(
        "INSERT INTO signals (id,ticker,kind,source_type,value_num,as_of,published_at,"
        "source_name) VALUES (?,?,?,?,?,?,?,?)",
        ("s1", "TCS.NS", "eps", "fundamental", 28.4, "2024-03-31", "2024-05-14", "EDGAR"))
    conn.commit()

    early = PointInTimeStore(conn, "2024-04-10")
    assert early.latest("TCS.NS", "eps") is None, "Q1 EPS leaked before its filing date"

    later = PointInTimeStore(conn, "2024-05-20")
    assert later.latest("TCS.NS", "eps").value_num == 28.4
