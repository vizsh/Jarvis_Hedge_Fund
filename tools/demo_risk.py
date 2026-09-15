"""Runnable proof that the firewall works, before any LLM or UI exists.

    python tools/demo_risk.py

This is deliberately the first thing that runs in the project. If the model layer
disappoints on the day, this still demos.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from risk.engine import RiskEngine            # noqa: E402
from risk.policy import Policy                 # noqa: E402
from risk.portfolio import Proposal            # noqa: E402
from risk.seed import PRICES, SECTORS, seed_fund  # noqa: E402

FUND = seed_fund()
RULE = "-" * 78


def show(engine: RiskEngine, proposal: Proposal, label: str) -> None:
    d = engine.evaluate(FUND, proposal, PRICES, SECTORS)
    print(f"\n{RULE}\n  {label}")
    print(f"  PROPOSAL   {proposal.side} {proposal.shares} {proposal.ticker} "
          f"@ {proposal.price:,.2f}  (notional {d.metrics['notional']:,.0f})")
    print(f"  POLICY     {d.policy_version}")
    print(f"  VERDICT    {d.summary}")
    for v in d.violations:
        print(f"             ! {v.code}: {v.message}")
    if d.remedy:
        print(f"  REMEDY     {d.remedy.explanation}")
    print(RULE)


def main() -> None:
    nav = FUND.nav(PRICES)
    it = FUND.sector_value("IT", PRICES, SECTORS)
    print(f"\n  FUND STATE   NAV {nav:,.0f}   cash {FUND.cash / nav * 100:.1f}%   "
          f"IT sector {it / nav * 100:.1f}%   (compliant at rest)")

    engine = RiskEngine(Policy())

    show(engine, Proposal(ticker="ITC.NS", side="BUY", shares=150, price=PRICES["ITC.NS"]),
         "1. A compliant trade passes untouched -- the firewall is not just a blocker.")

    show(engine, Proposal(ticker="PERSISTENT.NS", side="BUY", shares=30, price=PRICES["PERSISTENT.NS"]),
         "2. THE DEMO MOMENT: a reasonable-looking buy breaches the SECTOR cap only,\n"
         "     and the engine solves for the compliant size instead of just refusing.")

    show(engine, Proposal(ticker="TCS.NS", side="BUY", shares=400, price=PRICES["TCS.NS"]),
         "3. A greedy buy trips two limits at once; the tighter one binds.")

    show(engine, Proposal(ticker="TCS.NS", side="SELL", shares=5000, price=PRICES["TCS.NS"]),
         "4. Shorting is disabled, so the sell is capped at the shares actually held.")

    relaxed = RiskEngine(Policy().with_limit(max_sector_pct=0.40))
    show(relaxed, Proposal(ticker="PERSISTENT.NS", side="BUY", shares=30, price=PRICES["PERSISTENT.NS"]),
         "5. POLICY SIMULATOR: same trade, sector cap relaxed 30% -> 40%, verdict flips.")

    print("\n  Every verdict and every sentence above is a deterministic template built\n"
          "  from measured numbers. No LLM was involved in any decision on this page.\n")


if __name__ == "__main__":
    main()
