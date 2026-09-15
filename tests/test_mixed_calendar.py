"""Mixed-market portfolios must not be poisoned by differing holiday calendars.

The bug this pins down was silent and total. `portfolio_series` summed `close x shares`
per date across every holding, which is correct only while every holding trades on the
same calendar. The product ships an India-deep / US-shallow universe, so the moment a
portfolio held both, an NSE trading day that was a US holiday dropped the entire US
half of the book out of the total — and the reverse on the other side.

The series became a sawtooth of ±40% daily moves that never happened. Volatility,
maximum drawdown and beta are all computed from that series, so all three were wrong at
once, and the most visible symptom was a beta of -366 against the NIFTY 50 on a
perfectly ordinary basket.

Nothing raised. The numbers simply stopped meaning anything, which is exactly the
failure this project claims to exist to prevent — so it is worth a test that would have
caught it.
"""
from __future__ import annotations

import pytest

from analysis import xray
from backend.session import Session
from risk.portfolio import Portfolio


@pytest.fixture(scope="module")
def session() -> Session:
    s = Session.create()
    s.reprice()
    return s


def _held(session: Session, tickers: dict[str, int]) -> Portfolio:
    available = {t: n for t, n in tickers.items() if session.prices.get(t)}
    if len(available) != len(tickers):
        pytest.skip("snapshot does not carry every ticker this test needs")
    return Portfolio(cash=100_000.0, positions=available)


INDIA = {"TCS.NS": 60, "INFY.NS": 110, "HDFCBANK.NS": 180}
MIXED = {"TCS.NS": 60, "INFY.NS": 110, "NVDA": 3, "MSFT": 1}


def test_calendars_actually_differ(session):
    """If this ever stops being true the rest of the file is testing nothing."""
    nse = {b["date"] for b in session.pit.prices("TCS.NS", limit=120)}
    us = {b["date"] for b in session.pit.prices("NVDA", limit=120)}
    assert nse - us or us - nse, "expected NSE and US holiday calendars to diverge"


def test_series_has_no_phantom_cliffs(session):
    """No single day may move the basket more than 25%.

    A real market can do that; a holiday cannot. Before the fix the mixed series
    regularly swung by the whole weight of one market in a single step.
    """
    series = xray.portfolio_series(session.pit, _held(session, MIXED))
    assert len(series) > 30

    values = [v for _, v in series]
    worst = max(abs(b / a - 1) for a, b in zip(values, values[1:]) if a)
    assert worst < 0.25, f"a single day moved the basket {worst:.0%} — phantom cliff"


def test_every_date_prices_every_holding(session):
    """The total on any date must include all four positions, not whichever market
    happened to be open."""
    pf = _held(session, MIXED)
    series = xray.portfolio_series(session.pit, pf)
    smallest = min(v for _, v in series)

    # The cheapest possible complete basket: every holding at its lowest close.
    floor = 0.0
    for ticker, shares in pf.positions.items():
        closes = [b["close"] for b in session.pit.prices(ticker, limit=250)
                  if b["close"] is not None]
        floor += min(closes) * shares
    assert smallest >= floor * 0.95, "a date is missing at least one holding"


def test_beta_stays_in_a_sane_range(session):
    """Beta against the benchmark belongs roughly in [-2, 3] for a long equity book."""
    for label, held in (("india", INDIA), ("mixed", MIXED)):
        report = xray.analyse(session.pit, _held(session, held), session.prices,
                              session.policy)
        assert report.beta is not None, f"{label}: beta not computed"
        assert -2.0 < report.beta < 3.0, f"{label}: beta {report.beta} is not plausible"


def test_volatility_and_drawdown_stay_bounded(session):
    """Both are derived from the same series, so both broke together."""
    report = xray.analyse(session.pit, _held(session, MIXED), session.prices,
                          session.policy)
    assert report.volatility_annual is not None
    assert 0.0 < report.volatility_annual < 1.5, "annualised volatility is implausible"
    assert report.max_drawdown is not None
    assert -1.0 <= report.max_drawdown <= 0.0


def test_adding_a_us_holding_does_not_distort_the_india_numbers(session):
    """The whole failure mode: one US position must not change the risk profile of an
    Indian book beyond its own weight."""
    india = xray.analyse(session.pit, _held(session, INDIA), session.prices,
                         session.policy)
    mixed = xray.analyse(session.pit, _held(session, MIXED), session.prices,
                         session.policy)
    assert abs(mixed.beta - india.beta) < 1.0, (
        f"beta jumped from {india.beta} to {mixed.beta} on adding two US names")


def test_series_starts_only_when_everything_is_priceable(session):
    """A holding that appears mid-series is the same cliff wearing a different hat."""
    pf = _held(session, MIXED)
    series = xray.portfolio_series(session.pit, pf)
    first_date = series[0][0]
    for ticker in pf.positions:
        bars = [b["date"] for b in session.pit.prices(ticker, limit=250)
                if b["close"] is not None]
        assert bars[0] <= first_date, f"{ticker} has no price on the first date"
