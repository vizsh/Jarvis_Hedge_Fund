"""Tests for the usability layer: universe, portfolios, X-ray, stress, explainer.

The theme running through these: a tool for non-experts fails differently from a tool
for experts. An expert notices a wrong number; a non-expert does not, and acts on it.
So the tests here care disproportionately about answers being *unambiguous* -- no
holding silently dropped, no score quoted without its yardstick, no what-if presented
as a fact.
"""
from __future__ import annotations

import pytest

from analysis import stress, xray
from backend import explain, portfolios
from core import universe
from core.db import init
from core.pit import PointInTimeStore
from risk.policy import Policy
from risk.portfolio import Portfolio

PRICES = {"TCS.NS": 2000.0, "INFY.NS": 1000.0, "HDFCBANK.NS": 700.0,
          "ITC.NS": 250.0, "SUNPHARMA.NS": 1800.0, "MARUTI.NS": 12000.0,
          "^NSEI": 24000.0}


# --------------------------------------------------------------------- universe
@pytest.mark.parametrize("query,expected", [
    ("TCS.NS", "TCS.NS"), ("TCS", "TCS.NS"), ("tcs", "TCS.NS"),
    ("Infosys", "INFY.NS"), ("infosys", "INFY.NS"),
    ("HDFC Bank", "HDFCBANK.NS"), ("hdfc bank", "HDFCBANK.NS"),
    ("Sun Pharma", "SUNPHARMA.NS"), ("Maruti Suzuki", "MARUTI.NS"),
])
def test_symbol_resolution_accepts_how_people_actually_type(query, expected):
    assert universe.resolve(query) == expected


def test_longer_name_wins_over_a_prefix():
    """"HDFC Bank" must not land on HDFC Life just because it matched first."""
    assert universe.resolve("HDFC Bank") == "HDFCBANK.NS"
    assert universe.resolve("HDFC Life") == "HDFCLIFE.NS"


def test_unknown_symbol_resolves_to_nothing():
    assert universe.resolve("ZOMATO") is None
    assert universe.resolve("") is None


def test_every_ticker_has_a_sector_and_a_readable_name():
    for ticker in universe.tickers():
        assert universe.sector(ticker) != "UNKNOWN", ticker
        assert universe.name(ticker) and not universe.name(ticker).endswith(".NS")


# --------------------------------------------------------------------- pasting
def test_pasted_holdings_survive_broker_formatting():
    text = ("Symbol,Qty\n"
            "TCS, 40\n"
            "HDFC Bank, 120\n"
            "Infosys 85\n"
            "RELIANCE,30\n"
            "Sun Pharma\t60\n")
    positions, rejected = portfolios.parse_pasted(text)
    assert positions == {"TCS.NS": 40, "HDFCBANK.NS": 120, "INFY.NS": 85,
                         "RELIANCE.NS": 30, "SUNPHARMA.NS": 60}
    assert not rejected


def test_unreadable_lines_are_returned_not_silently_dropped():
    """A holding that vanished quietly is worse than one that failed loudly -- the
    user would act on a portfolio that is missing a position they think they own."""
    positions, rejected = portfolios.parse_pasted("TCS, 40\nnonsense line here\n")
    assert positions == {"TCS.NS": 40}
    assert len(rejected) == 1


def test_duplicate_lines_accumulate():
    positions, _ = portfolios.parse_pasted("TCS, 40\nTCS, 10\n")
    assert positions == {"TCS.NS": 50}


def test_presets_convert_to_whole_shares_within_budget():
    for preset in portfolios.PRESETS:
        cash, positions = portfolios.preset_to_positions(preset, PRICES, nav=1_000_000)
        assert cash >= 0, f"{preset['key']} overspent its budget"
        assert all(isinstance(v, int) and v > 0 for v in positions.values())


# --------------------------------------------------------------------- x-ray
@pytest.fixture
def pit():
    conn = init(":memory:")
    rows = []
    for ticker, price in PRICES.items():
        for i in range(120):
            date = f"2026-0{1 + i // 31}-{1 + i % 28:02d}"
            drift = 1 + (i % 7 - 3) * 0.01
            rows.append((ticker, date, 0, 0, 0, price * drift, 0, date))
    conn.executemany("INSERT OR REPLACE INTO prices VALUES (?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    return PointInTimeStore(conn, "2026-12-31")


def test_concentrated_portfolio_scores_worse_than_a_spread_one(pit):
    policy = Policy.from_profile("retail")
    concentrated = Portfolio(cash=10_000, positions={"TCS.NS": 450})
    spread = Portfolio(cash=10_000, positions={
        "TCS.NS": 45, "INFY.NS": 90, "HDFCBANK.NS": 128,
        "ITC.NS": 360, "SUNPHARMA.NS": 50, "MARUTI.NS": 7})
    a = xray.analyse(pit, concentrated, PRICES, policy)
    b = xray.analyse(pit, spread, PRICES, policy)
    assert a.score < b.score
    assert a.effective_holdings < b.effective_holdings


def test_effective_holdings_exposes_false_diversification(pit):
    """Ten names where one is 80% is not a ten-stock portfolio."""
    lopsided = Portfolio(cash=0, positions={"TCS.NS": 400, "INFY.NS": 10,
                                            "ITC.NS": 10, "HDFCBANK.NS": 10})
    report = xray.analyse(pit, lopsided, PRICES, Policy.from_profile("retail"))
    assert report.holdings == 4
    assert report.effective_holdings < 2


def test_findings_are_capped_so_the_user_can_act_on_them(pit):
    """Thirteen red rows is an alarm, not a diagnosis."""
    messy = Portfolio(cash=100, positions={t: 100 for t in PRICES if t != "^NSEI"})
    report = xray.analyse(pit, messy, PRICES, Policy.from_profile("fund"))
    assert len(report.findings) <= 5


def test_oversized_positions_collapse_into_one_finding(pit):
    messy = Portfolio(cash=100, positions={t: 100 for t in PRICES if t != "^NSEI"})
    report = xray.analyse(pit, messy, PRICES, Policy.from_profile("fund"))
    codes = [f.code for f in report.findings]
    assert codes.count("POSITION_CONCENTRATION") == 1


def test_the_same_portfolio_scores_differently_per_profile(pit):
    """The whole reason profiles exist: institutional limits applied to a retail
    portfolio produce unreachable advice."""
    pf = Portfolio(cash=50_000, positions={"TCS.NS": 100, "INFY.NS": 150,
                                           "HDFCBANK.NS": 200})
    retail = xray.analyse(pit, pf, PRICES, Policy.from_profile("retail"))
    fund = xray.analyse(pit, pf, PRICES, Policy.from_profile("fund"))
    assert retail.score > fund.score


def test_score_always_carries_the_profile_it_was_measured_against(pit):
    """A score without its yardstick is misleading, not merely incomplete."""
    pf = Portfolio(cash=1000, positions={"TCS.NS": 10})
    report = xray.analyse(pit, pf, PRICES, Policy.from_profile("balanced"))
    assert report.profile == "balanced"
    assert report.profile_name
    assert "10%" in report.limits_describe


# --------------------------------------------------------------------- stress
def test_hypothetical_shock_only_hits_the_named_sector(pit):
    pf = Portfolio(cash=0, positions={"TCS.NS": 100, "ITC.NS": 800})
    it_only = stress.run_hypothetical(pf, {"key": "k", "label": "IT falls 50%",
                                           "scope": "IT", "shock": -0.5}, PRICES)
    # TCS is 200k of 400k, so a 50% IT shock costs 25% of the portfolio.
    assert it_only.portfolio_return == pytest.approx(-0.25, abs=0.01)


def test_cash_is_not_shocked(pit):
    pf = Portfolio(cash=500_000, positions={"TCS.NS": 250})
    r = stress.run_hypothetical(pf, {"key": "k", "label": "all -20%",
                                     "scope": "ALL", "shock": -0.2}, PRICES)
    assert r.portfolio_return == pytest.approx(-0.10, abs=0.01)


def test_scenarios_declare_whether_they_are_real_or_hypothetical(pit):
    pf = Portfolio(cash=1000, positions={"TCS.NS": 100})
    out = stress.run_all(pit, pf, PRICES)
    kinds = {s["kind"] for s in out["scenarios"]}
    assert kinds == {"historical", "hypothetical"}


# --------------------------------------------------------------------- explainer
def test_money_reads_in_indian_conventions():
    assert explain.rupees(150_000) == "₹1.50 lakh"
    assert explain.rupees(25_000_000) == "₹2.50 crore"
    assert "," in explain.rupees(45_000)


def test_every_answer_is_short_enough_to_be_spoken(pit):
    """A spoken paragraph of six bullets is unlistenable."""
    pf = Portfolio(cash=50_000, positions={"TCS.NS": 100, "INFY.NS": 150})
    policy = Policy.from_profile("retail")
    for q in ["how am I doing", "why is my risk high", "what should I sell",
              "what if the market drops 20%", "am I diversified"]:
        a = explain.answer(q, pit, pf, PRICES, policy)
        assert a.headline
        assert len(a.spoken()) < 600, q


def test_glossary_answers_do_not_need_a_portfolio(pit):
    a = explain.answer("what does beta mean", pit, Portfolio(cash=0), PRICES,
                       Policy.from_profile("retail"))
    assert "market moves" in a.headline


def test_empty_portfolio_gets_a_useful_answer_not_an_error(pit):
    a = explain.answer("how am I doing", pit, Portfolio(cash=0), PRICES,
                       Policy.from_profile("retail"))
    assert a.kind == "empty"
    assert "holdings" in a.headline


def test_sell_advice_names_real_share_counts(pit):
    """"Reduce your technology exposure" is not advice. "Sell 22 TCS" is."""
    pf = Portfolio(cash=0, positions={"TCS.NS": 300, "ITC.NS": 100})
    a = explain.answer("what should I sell", pit, pf, PRICES,
                       Policy.from_profile("fund"))
    assert a.kind == "fix"
    assert a.data.get("trims")
    assert all(t["shares"] > 0 for t in a.data["trims"])


def test_hypothetical_answers_say_they_are_hypothetical(pit):
    pf = Portfolio(cash=0, positions={"TCS.NS": 100})
    a = explain.answer("what if the market drops 30%", pit, pf, PRICES,
                       Policy.from_profile("retail"))
    assert "forecast" in (a.action or "").lower()


def test_historical_answers_say_they_are_real(pit):
    pf = Portfolio(cash=0, positions={"TCS.NS": 100})
    a = explain.answer("what happened in covid", pit, pf, PRICES,
                       Policy.from_profile("retail"))
    assert "real prices" in (a.action or "").lower()
