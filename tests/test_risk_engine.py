"""Risk engine tests.

The load-bearing one is `test_remedy_is_always_compliant`: it is not enough for the
engine to compute a smaller number, that number has to actually pass the same gate.
A remedy that still breaches is worse than a plain rejection, because it looks
authoritative on screen.
"""
from __future__ import annotations

import pytest

from risk.engine import RiskEngine
from risk.policy import Policy
from risk.portfolio import Portfolio, Proposal

from risk.seed import PRICES, SECTORS, seed_fund


@pytest.fixture
def engine() -> RiskEngine:
    return RiskEngine(Policy())


@pytest.fixture
def pf() -> Portfolio:
    """Deliberately over-concentrated, for exercising breach paths."""
    # NAV = 2,000,000 cash + 4,000,000 IT + 1,600,000 fin = 7,600,000
    return Portfolio(cash=2_000_000.0,
                     positions={"TCS.NS": 700, "INFY.NS": 800, "HDFCBANK.NS": 1000})


@pytest.fixture
def pf_compliant() -> Portfolio:
    """The shared demo fund -- compliant at rest, parked just under the IT sector cap."""
    return seed_fund()


def test_small_buy_approved(engine, pf):
    d = engine.evaluate(pf, Proposal(ticker="ITC.NS", side="BUY", shares=100, price=450.0),
                        PRICES, SECTORS)
    assert d.approved
    assert d.violations == []


def test_position_limit_breach(engine, pf):
    # 700 held + 200 more at 4000 = 3.6m on ~7.6m NAV -> well past the 5% ceiling
    d = engine.evaluate(pf, Proposal(ticker="TCS.NS", side="BUY", shares=200, price=4000.0),
                        PRICES, SECTORS)
    assert not d.approved
    assert "POSITION_LIMIT" in {v.code for v in d.violations}


def test_sector_limit_breach_reports_measured_value(engine, pf):
    d = engine.evaluate(pf, Proposal(ticker="INFY.NS", side="BUY", shares=500, price=1500.0),
                        PRICES, SECTORS)
    sector_v = next(v for v in d.violations if v.code == "SECTOR_LIMIT")
    assert sector_v.measured > 0.30
    assert sector_v.limit == 0.30
    assert "IT" in sector_v.message


def test_cash_reserve_breach(engine):
    pf = Portfolio(cash=500_000.0, positions={"ITC.NS": 10_000})
    d = engine.evaluate(pf, Proposal(ticker="ITC.NS", side="BUY", shares=1000, price=450.0),
                        PRICES, SECTORS)
    assert not d.approved
    assert "CASH_RESERVE" in {v.code for v in d.violations}


@pytest.mark.parametrize("ticker,shares", [
    ("TCS.NS", 200), ("INFY.NS", 500), ("HDFCBANK.NS", 900), ("ITC.NS", 20_000),
])
def test_remedy_is_always_compliant(engine, pf, ticker, shares):
    """Any remedy the engine offers must itself survive the gate."""
    d = engine.evaluate(pf, Proposal(ticker=ticker, side="BUY", shares=shares,
                                     price=PRICES[ticker]), PRICES, SECTORS)
    if d.approved:
        pytest.skip("not a breach case")
    assert d.remedy is not None
    n = d.remedy.max_shares
    if n == 0:
        return  # engine correctly says no size works
    redo = engine.evaluate(pf, Proposal(ticker=ticker, side="BUY", shares=n,
                                        price=PRICES[ticker]), PRICES, SECTORS)
    assert redo.approved, f"remedy of {n} shares still breaches: {redo.summary}"


def test_remedy_is_maximal(engine, pf):
    """One more share than the remedy must breach, or we are leaving capital idle."""
    d = engine.evaluate(pf, Proposal(ticker="INFY.NS", side="BUY", shares=500, price=1500.0),
                        PRICES, SECTORS)
    n = d.remedy.max_shares
    over = engine.evaluate(pf, Proposal(ticker="INFY.NS", side="BUY", shares=n + 1,
                                        price=1500.0), PRICES, SECTORS)
    assert not over.approved


def test_cannot_sell_more_than_held(engine, pf):
    d = engine.evaluate(pf, Proposal(ticker="TCS.NS", side="SELL", shares=5000, price=4000.0),
                        PRICES, SECTORS)
    assert not d.approved
    assert d.remedy.max_shares == 700


def test_sell_within_holding_approved(engine, pf):
    d = engine.evaluate(pf, Proposal(ticker="TCS.NS", side="SELL", shares=100, price=4000.0),
                        PRICES, SECTORS)
    assert d.approved


def test_explanations_are_deterministic(engine, pf):
    """Same inputs, same words. Never a generative explanation."""
    p = Proposal(ticker="INFY.NS", side="BUY", shares=500, price=1500.0)
    a = engine.evaluate(pf, p, PRICES, SECTORS)
    b = engine.evaluate(pf, p, PRICES, SECTORS)
    assert [v.message for v in a.violations] == [v.message for v in b.violations]
    assert a.remedy.explanation == b.remedy.explanation


def test_costs_are_charged(engine, pf):
    """Omitting trading costs is how published backtests inflate returns."""
    before = pf.nav(PRICES)
    after = pf.apply("ITC.NS", "BUY", 100, 450.0, cost_bps=15)
    assert after.nav(PRICES) < before


def test_sector_limit_binds_in_isolation(engine, pf_compliant):
    """A new IT name, small enough for the position ceiling, still breaches the sector cap."""
    p = Proposal(ticker="PERSISTENT.NS", side="BUY", shares=30, price=PRICES["PERSISTENT.NS"])
    d = engine.evaluate(pf_compliant, p, PRICES, SECTORS)
    assert not d.approved
    assert {v.code for v in d.violations} == {"SECTOR_LIMIT"}
    assert d.remedy.binding_constraint == "SECTOR_LIMIT"


def test_policy_simulator_relaxes_the_binding_limit(pf_compliant):
    """The what-if: same trade, looser sector cap, different verdict."""
    p = Proposal(ticker="PERSISTENT.NS", side="BUY", shares=30, price=PRICES["PERSISTENT.NS"])
    strict = RiskEngine(Policy())
    assert not strict.evaluate(pf_compliant, p, PRICES, SECTORS).approved

    relaxed = RiskEngine(Policy().with_limit(max_sector_pct=0.40))
    d = relaxed.evaluate(pf_compliant, p, PRICES, SECTORS)
    assert d.approved
    assert d.policy_version.endswith("+sim")


def test_seed_fund_is_compliant_at_rest(engine, pf_compliant):
    """If the demo opens on a portfolio that already breaches, the story falls apart."""
    lim = engine.policy.limits
    nav = pf_compliant.nav(PRICES)
    for ticker, weight in pf_compliant.weights(PRICES).items():
        assert weight <= lim.max_position_pct + 1e-9, f"{ticker} at {weight:.3%}"
    for sector in set(SECTORS.values()):
        w = pf_compliant.sector_value(sector, PRICES, SECTORS) / nav
        assert w <= lim.max_sector_pct + 1e-9, f"{sector} at {w:.3%}"
    assert pf_compliant.cash / nav >= lim.min_cash_pct


def test_seed_fund_sits_just_under_the_it_cap(pf_compliant):
    """The trap that makes the demo land: headroom, but not much."""
    nav = pf_compliant.nav(PRICES)
    it = pf_compliant.sector_value("IT", PRICES, SECTORS) / nav
    assert 0.27 < it < 0.30
