"""The demo fund: a single source of truth for tests, the demo scripts, and the UI seed.

Prices are REAL last closes taken from the frozen snapshot, not invented round numbers.
An earlier version used made-up prices and drifted almost 3x from reality on WIPRO --
`test_seed_prices_are_within_sane_range_of_reality` exists to catch exactly that, since
a fund quoting impossible prices undermines every number downstream of it.

Sized so the fund is COMPLIANT at rest under config/policy.yaml -- every position under
the 5% ceiling, every sector under 30%, cash far above the 10% floor -- while parked
deliberately close to the IT sector cap at 28.8% of 30%.

That last detail is the whole point: a small, individually reasonable buy in a NEW IT
name breaches the SECTOR cap without tripping the position ceiling. That is the demo
moment, and it is a real portfolio-construction trap rather than a contrived one.
PERSISTENT.NS is held at zero for exactly that purpose.
"""
from __future__ import annotations

from risk.portfolio import Portfolio

# Last closes from data/snapshot.db.
PRICES: dict[str, float] = {
    # IT
    "TCS.NS": 2200.8, "INFY.NS": 1037.7, "WIPRO.NS": 167.4, "HCLTECH.NS": 1206.1,
    "TECHM.NS": 1541.0, "MPHASIS.NS": 2295.0, "PERSISTENT.NS": 5516.0,
    # Financials
    "HDFCBANK.NS": 708.2, "ICICIBANK.NS": 1379.3,
    # FMCG
    "ITC.NS": 259.9, "HINDUNILVR.NS": 1927.0,
}

SECTORS: dict[str, str] = {
    "TCS.NS": "IT", "INFY.NS": "IT", "WIPRO.NS": "IT", "HCLTECH.NS": "IT",
    "TECHM.NS": "IT", "MPHASIS.NS": "IT", "PERSISTENT.NS": "IT",
    "HDFCBANK.NS": "FINANCIALS", "ICICIBANK.NS": "FINANCIALS",
    "ITC.NS": "FMCG", "HINDUNILVR.NS": "FMCG",
}

# The trade the demo proposes: individually modest (1.7% position) but enough to push
# IT from 28.8% through the 30% sector cap.
DEMO_TRADE = {"ticker": "PERSISTENT.NS", "side": "BUY", "shares": 30}


def seed_fund() -> Portfolio:
    """NAV = 10,000,000. Six IT names at 4.80% each (28.8% sector), four non-IT at 4.50%."""
    return Portfolio(cash=5_320_000.0, positions={
        "TCS.NS": 218, "INFY.NS": 463, "WIPRO.NS": 2867,
        "HCLTECH.NS": 398, "TECHM.NS": 311, "MPHASIS.NS": 209,
        "HDFCBANK.NS": 635, "ICICIBANK.NS": 326,
        "ITC.NS": 1731, "HINDUNILVR.NS": 234,
    })
