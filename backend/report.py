"""One page you can print, keep, or hand to someone else.

Everything in this product lives on a screen that is always moving. That is right for
working, and wrong for the two moments that actually matter to a user: showing someone
else what they own, and looking back in six months at what they were told.

So this assembles a single flat document — position, findings, what to do, what it
survived, what it would cost in tax, and the provenance underneath all of it. No
interaction, no live socket, no state. It renders the same on paper as on glass.

The provenance block is not decoration. A report that says "you are 48% technology"
without saying *as of which prices, under which limits, on which clock* is an opinion.
With those three, it is a record.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from analysis import attribution as attrib_mod
from analysis import rebalance as rebalance_mod
from analysis import stress as stress_mod
from analysis import tax as tax_mod
from analysis import xray as xray_mod
from backend import actions as actions_mod
from core import universe
from core.pit import PointInTimeStore
from risk.policy import Policy
from risk.portfolio import Portfolio


def _rupees(a: float) -> str:
    x = abs(a)
    sign = "-" if a < 0 else ""
    if x >= 1_00_00_000:
        return f"{sign}₹{x / 1_00_00_000:.2f} crore"
    if x >= 1_00_000:
        return f"{sign}₹{x / 1_00_000:.2f} lakh"
    return f"{sign}₹{x:,.0f}"


def build(pit: PointInTimeStore, portfolio: Portfolio, prices: dict[str, float],
          policy: Policy, portfolio_name: str,
          lots: dict[str, tax_mod.Lot] | None = None) -> dict[str, Any]:
    if not portfolio.positions:
        return {"empty": True}

    report = xray_mod.analyse(pit, portfolio, prices, policy)
    queue = actions_mod.build(pit, portfolio, prices, policy, lots, limit=5)

    # Each of these is allowed to fail without taking the page with it. A report that
    # renders four of five sections beats a 500.
    try:
        stress = stress_mod.run_all(pit, portfolio, prices)
    except Exception:  # noqa: BLE001
        stress = {"scenarios": [], "worst_case": None}
    try:
        plan = rebalance_mod.plan(pit, portfolio, prices, policy,
                                  deploy_cash=True).as_dict()
        if lots:
            plan = tax_mod.annotate_plan(plan, lots)
    except Exception:  # noqa: BLE001
        plan = {"trades": [], "trade_count": 0}
    try:
        a = attrib_mod.analyse(pit, portfolio, prices, "3m")
        attribution = {**a.as_dict(), "summary": attrib_mod.summary_line(a)}
    except Exception:  # noqa: BLE001
        attribution = None

    nav = report.nav
    positions = sorted(
        ({"ticker": t, "name": universe.name(t), "shares": n,
          "price": prices.get(t, 0.0), "value": n * prices.get(t, 0.0),
          "weight": (n * prices.get(t, 0.0) / nav) if nav else 0.0,
          "sector": universe.sector_label(dict(universe.sectors()).get(t, "UNKNOWN"))}
         for t, n in portfolio.positions.items()),
        key=lambda r: -r["value"])

    sectors: dict[str, float] = {}
    for p in positions:
        sectors[p["sector"]] = sectors.get(p["sector"], 0.0) + p["weight"]

    return {
        "empty": False,
        "title": portfolio_name,
        "generated_at": datetime.now().strftime("%d %B %Y, %H:%M"),
        "as_of": pit.clock_iso[:10],

        "headline": {
            "grade": report.grade,
            "score": report.score,
            "nav": nav,
            "nav_display": _rupees(nav),
            "holdings": report.holdings,
            "sectors": report.sectors,
            # XRay.as_dict() rounds this; reading the attribute directly does not, and
            # "10.768937614291199 positions" on a printed page is not a small blemish.
            "effective_holdings": round(report.effective_holdings, 1),
            "cash_pct": report.cash_pct,
            "beta": report.beta,
            "max_drawdown": report.max_drawdown,
            "verdict": _verdict(report),
        },

        "policy": {
            "profile": report.profile,
            "name": report.profile_name,
            "describes": report.limits_describe,
            "limits": policy.limits.model_dump(),
        },

        "findings": [f.__dict__ for f in report.findings],
        "actions": queue["actions"],

        "positions": positions,
        "sector_split": sorted(sectors.items(), key=lambda kv: -kv[1]),

        "stress": {
            "worst_case": stress.get("worst_case"),
            "scenarios": [
                {"label": s["label"], "kind": s["kind"],
                 "portfolio_return": s["portfolio_return"],
                 "value_change": s["value_change"], "coverage": s["coverage"]}
                for s in stress.get("scenarios", [])
            ],
        },

        "plan": {
            "trade_count": plan.get("trade_count", 0),
            "turnover": plan.get("turnover", 0.0),
            "cost": plan.get("cost", 0.0),
            "compliant_after": plan.get("compliant_after", False),
            "tax": plan.get("tax"),
            "trades": plan.get("trades", [])[:12],
        },

        "attribution": attribution,

        "provenance": {
            "clock": pit.clock_iso,
            "visible": pit.visible_counts(),
            "benchmark": universe.benchmark_label(),
            "rule": "Every figure above is computed from prices dated on or before the "
                    "simulation clock. Nothing in this document was written by a "
                    "language model; the words are templates and the numbers are "
                    "arithmetic.",
            "caveat": "Paper trading only. No orders were placed and no money moved. "
                      "Tax figures are arithmetic on published rates, not tax advice.",
        },
    }


def _verdict(report: xray_mod.XRay) -> str:
    """The one sentence somebody reads if they read nothing else."""
    high = [f for f in report.findings if f.severity == "high"]
    medium = [f for f in report.findings if f.severity == "medium"]
    if not high and not medium:
        return (f"Nothing here sits outside {report.profile_name.lower()} limits. "
                f"The score of {report.score} reflects how evenly the money is spread, "
                f"not how it has performed.")
    if high:
        return (f"{len(high)} thing{'s' if len(high) != 1 else ''} need"
                f"{'' if len(high) != 1 else 's'} attention, "
                f"{'the largest being ' + high[0].headline.lower() if high else ''}. "
                f"Scored {report.score} out of 100 against "
                f"{report.profile_name.lower()} limits.")
    return (f"{len(medium)} thing{'s' if len(medium) != 1 else ''} worth watching, "
            f"none of them severe. Scored {report.score} out of 100 against "
            f"{report.profile_name.lower()} limits.")
