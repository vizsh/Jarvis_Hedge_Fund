"""Stage it, look at it, then decide: a portfolio you can try on.

The reason people do not click things in a risk tool is that they cannot tell what will
happen, and the cost of being wrong looks unbounded. Every button in this product
therefore reads as dangerous even when it is not, and the rational response is to click
nothing — which is exactly what a wall of panels produces.

A sandbox removes the guess. Trades go into a staging layer, the *entire* analysis is
recomputed against the hypothetical book, and both versions are returned side by side.
Nothing has moved. You commit or you throw it away.

Two properties worth keeping honest:

  - The staged book is a real `Portfolio`, scored by the real `xray.analyse` against
    the real policy. It is not an estimate of what would happen; it is the same
    calculation on different inputs, which is the only way the comparison means
    anything.
  - Committing does not bypass the risk firewall. It replays each staged trade through
    the same deterministic engine a spoken order goes through, and a trade that would
    have been blocked live is blocked here too. A sandbox that can launder a breach
    into the book is a hole in the governance story, not a feature.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from analysis import stress as stress_mod
from analysis import xray as xray_mod
from core import universe
from core.pit import PointInTimeStore
from risk.policy import Policy
from risk.portfolio import Portfolio


@dataclass
class Staged:
    """A set of hypothetical trades and where they came from."""
    trades: list[dict[str, Any]] = field(default_factory=list)
    origin: str = "manual"            # manual | rebalance | deploy_cash | flow
    note: str = ""

    def clear(self) -> None:
        self.trades = []
        self.origin = "manual"
        self.note = ""

    def as_dict(self) -> dict[str, Any]:
        return {"trades": self.trades, "origin": self.origin, "note": self.note,
                "count": len(self.trades)}


def apply_to(portfolio: Portfolio, trades: list[dict[str, Any]],
             prices: dict[str, float], policy: Policy) -> tuple[Portfolio, list[str]]:
    """Build the hypothetical book. Returns the new portfolio and anything skipped.

    Deep-copied rather than mutated: the caller's live book must be untouched even if
    this raises halfway through a list of trades.
    """
    book = Portfolio(cash=portfolio.cash,
                     positions=copy.deepcopy(portfolio.positions))
    skipped: list[str] = []
    for t in trades:
        ticker = t.get("ticker")
        side = str(t.get("side", "BUY")).upper()
        shares = int(t.get("shares") or 0)
        price = prices.get(ticker or "", 0.0)
        if not ticker or shares <= 0 or not price:
            skipped.append(f"{ticker or 'unknown'}: no price or zero size")
            continue
        if side == "SELL" and book.positions.get(ticker, 0) < shares:
            skipped.append(f"{universe.name(ticker)}: you do not hold {shares} shares")
            continue
        # `apply` returns a NEW portfolio rather than mutating -- the immutability that
        # keeps the simulator honest also means the result has to be rebound.
        book = book.apply(ticker, side, shares, price, policy.execution.cost_bps)
    return book, skipped


def _summary(pit: PointInTimeStore, book: Portfolio, prices: dict[str, float],
             policy: Policy, with_stress: bool) -> dict[str, Any]:
    report = xray_mod.analyse(pit, book, prices, policy)
    out = {
        "nav": report.nav,
        "cash_pct": report.cash_pct,
        "score": report.score,
        "grade": report.grade,
        "holdings": report.holdings,
        "sectors": report.sectors,
        "effective_holdings": round(report.effective_holdings, 2),
        "top_sector": report.top_sector,
        "top_holding": report.top_holding,
        "beta": report.beta,
        "max_drawdown": report.max_drawdown,
        "findings": [f.__dict__ for f in report.findings],
        "breaches": [f.code for f in report.findings if f.severity in ("high", "medium")],
    }
    if with_stress:
        try:
            worst = stress_mod.run_all(pit, book, prices).get("worst_case")
            out["worst_case"] = worst
        except Exception:  # noqa: BLE001 - the comparison must survive a stress failure
            out["worst_case"] = None
    return out


def _deltas(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    """What actually changed, in the order a person cares about.

    Only differences are returned. A comparison table that lists sixteen identical rows
    to highlight the two that moved is a worse table than one with two rows in it.
    """
    rows: list[dict[str, Any]] = []

    def add(label: str, key: str, fmt: str, better: str, why: str = "") -> None:
        a, b = before.get(key), after.get(key)
        if a is None or b is None or abs(float(a) - float(b)) < 1e-9:
            return
        direction = "better" if ((b > a) == (better == "up")) else "worse"
        # Round at the boundary. Float noise like 0.08514185000000002 reaching a UI is
        # how a precise system ends up looking careless.
        places = 0 if fmt in ("money", "points") else 4
        rows.append({"label": label, "key": key,
                     "before": round(float(a), places), "after": round(float(b), places),
                     "delta": round(float(b) - float(a), places), "format": fmt,
                     "direction": direction, "why": why})

    add("Score", "score", "points", "up",
        "Measured against the same limits, so this is a like-for-like move.")
    add("Cash", "cash_pct", "pct", "up",
        "What you could deploy without selling something first.")
    add("Behaves like", "effective_holdings", "count", "up",
        "How many positions the risk really behaves like.")
    add("Holdings", "holdings", "count", "up")
    add("Industries", "sectors", "count", "up")
    add("Total value", "nav", "money", "up",
        "Falls slightly on any plan, because trading costs money.")
    add("Market sensitivity", "beta", "x", "down",
        "How much you move when the market moves.")

    gone = set(before.get("breaches") or []) - set(after.get("breaches") or [])
    new = set(after.get("breaches") or []) - set(before.get("breaches") or [])
    if gone:
        rows.append({"label": "Breaches resolved", "key": "breaches_gone",
                     "before": len(before.get("breaches") or []),
                     "after": len(after.get("breaches") or []),
                     "delta": -len(gone), "format": "count", "direction": "better",
                     "why": "These findings leave your action list: "
                            + ", ".join(sorted(gone))})
    if new:
        rows.append({"label": "New breaches", "key": "breaches_new",
                     "before": len(before.get("breaches") or []),
                     "after": len(after.get("breaches") or []),
                     "delta": len(new), "format": "count", "direction": "worse",
                     "why": "This plan creates a problem that was not there: "
                            + ", ".join(sorted(new))})
    return rows


def preview(pit: PointInTimeStore, portfolio: Portfolio, prices: dict[str, float],
            policy: Policy, staged: Staged, with_stress: bool = True) -> dict[str, Any]:
    """Before and after, plus a plain reading of whether it is an improvement."""
    if not staged.trades:
        return {"staged": False, "trades": [], "deltas": []}

    book, skipped = apply_to(portfolio, staged.trades, prices, policy)
    before = _summary(pit, portfolio, prices, policy, with_stress)
    after = _summary(pit, book, prices, policy, with_stress)
    deltas = _deltas(before, after)

    turnover = sum(abs(int(t.get("shares") or 0) * prices.get(t.get("ticker") or "", 0.0))
                   for t in staged.trades)
    cost = turnover * policy.execution.cost

    worse = [d for d in deltas if d["direction"] == "worse" and d["key"] != "nav"]
    better = [d for d in deltas if d["direction"] == "better"]
    if after["score"] > before["score"] and not after["breaches"]:
        verdict = ("This puts you inside every limit you set, and the score goes up "
                   f"{after['score'] - before['score']} points.")
    elif after["score"] > before["score"]:
        verdict = (f"Better on balance — {after['score'] - before['score']} points — "
                   "but not everything is resolved.")
    elif worse:
        verdict = ("This is not an improvement on the numbers that matter. Worth "
                   "knowing before you commit it.")
    else:
        verdict = "Roughly neutral. The main cost here is the trading itself."

    return {
        "staged": True,
        "origin": staged.origin,
        "note": staged.note,
        "trades": [{**t, "name": universe.name(t.get("ticker", "")),
                    "price": prices.get(t.get("ticker", ""), 0.0),
                    "value": int(t.get("shares") or 0)
                             * prices.get(t.get("ticker", ""), 0.0)}
                   for t in staged.trades],
        "skipped": skipped,
        "before": before,
        "after": after,
        "deltas": deltas,
        "turnover": round(turnover, 2),
        "cost": round(cost, 2),
        "verdict": verdict,
        "improves": len(better) > len(worse),
    }


def spoken(result: dict[str, Any]) -> str:
    """One sentence for the voice channel. The verdict, not the table."""
    if not result.get("staged"):
        return "Nothing is staged."
    n = len(result.get("trades") or [])
    return (f"{n} trade{'s' if n != 1 else ''} staged, nothing committed. "
            + result.get("verdict", ""))
