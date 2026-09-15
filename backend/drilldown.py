"""Every number is a door: what it is made of, how it was worked out, where it came from.

The glass-box claim in this project is currently spent on a separate "Machinery" mode
that a normal user never opens. That is the wrong place for it. Transparency is only
worth anything at the moment somebody doubts a specific number, and the way to serve
that moment is to let them click the number itself.

So each metric here returns four things, in this order:

  value       what is on screen
  components  the rows that add up to it, biggest first
  formula     how those rows became this number, written out
  provenance  which prices, as of which clock, and what the point-in-time rule was

The fourth is the one that matters for the pitch. A number with a `published_at` behind
it is auditable; a number without one is a vibe.
"""
from __future__ import annotations

from typing import Any

from analysis import xray as xray_mod
from core import universe
from core.pit import PointInTimeStore
from risk.policy import Policy
from risk.portfolio import Portfolio


def _rupees(a: float) -> str:
    x = abs(a)
    if x >= 1_00_00_000:
        return f"₹{x / 1_00_00_000:.2f} crore"
    if x >= 1_00_000:
        return f"₹{x / 1_00_000:.2f} lakh"
    return f"₹{x:,.0f}"


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _provenance(pit: PointInTimeStore, tickers: list[str]) -> dict[str, Any]:
    """Where the prices came from and what the clock was when they were read."""
    rows = []
    for t in tickers[:12]:
        bars = pit.prices(t, limit=1)
        rows.append({
            "ticker": t, "name": universe.name(t),
            "close": bars[-1]["close"] if bars else None,
            "as_of": bars[-1]["date"] if bars else None,
        })
    return {
        "clock": pit.clock_iso,
        "rule": "Only bars dated on or before the simulation clock are visible. "
                "Rewinding the clock hides later data at the query, not in the "
                "application, so no calculation here can see the future.",
        "tier": "EXACT",
        "rows": rows,
    }


# --------------------------------------------------------------------------- metrics
def explain_metric(metric: str, pit: PointInTimeStore, portfolio: Portfolio,
                   prices: dict[str, float], policy: Policy,
                   key: str | None = None) -> dict[str, Any]:
    """One metric, opened up. `key` narrows sector/position metrics to one row."""
    report = xray_mod.analyse(pit, portfolio, prices, policy)
    nav = report.nav
    weights = portfolio.weights(prices)
    sectors = dict(universe.sectors())

    if metric == "nav":
        rows = sorted(
            ({"label": universe.name(t), "ticker": t, "value": n * prices.get(t, 0.0),
              "sub": f"{n} shares at ₹{prices.get(t, 0.0):,.2f}"}
             for t, n in portfolio.positions.items()),
            key=lambda r: -r["value"])
        rows.append({"label": "Cash", "ticker": None, "value": portfolio.cash,
                     "sub": "not invested"})
        return {
            "metric": "nav", "title": "Total value",
            "value": nav, "display": _rupees(nav),
            "components": rows,
            "formula": "Every holding priced at its last close on or before the "
                       "simulation clock, multiplied by the shares you hold, plus cash.",
            "why": "This is the number every weight and limit in the product is a "
                   "percentage of, so it is worth knowing exactly what is in it.",
            "provenance": _provenance(pit, list(portfolio.positions)),
        }

    if metric == "sector":
        code = key or (report.top_sector[0] if report.top_sector else None)
        if not code:
            return {"error": "no sector"}
        members = [t for t in portfolio.positions if sectors.get(t) == code]
        rows = sorted(
            ({"label": universe.name(t), "ticker": t,
              "value": portfolio.positions[t] * prices.get(t, 0.0),
              "sub": _pct(weights.get(t, 0.0)) + " of everything you own"}
             for t in members), key=lambda r: -r["value"])
        total = sum(r["value"] for r in rows)
        share = total / nav if nav else 0.0
        limit = policy.limits.max_sector_pct
        return {
            "metric": "sector", "key": code,
            "title": f"{universe.sector_label(code)} exposure",
            "value": share, "display": _pct(share),
            "components": rows,
            "limit": limit, "limit_display": _pct(limit),
            "over_by": max(0.0, share - limit),
            "formula": f"{_rupees(total)} across {len(rows)} holding"
                       f"{'s' if len(rows) != 1 else ''}, divided by a total value of "
                       f"{_rupees(nav)}, gives {_pct(share)}. Your limit is "
                       f"{_pct(limit)}.",
            "why": "Companies in one industry fall together. This is the number that "
                   "says how much of your money one bad industry can reach.",
            "provenance": _provenance(pit, members),
        }

    if metric == "position":
        ticker = key or (report.top_holding[0] if report.top_holding else None)
        if not ticker:
            return {"error": "no position"}
        shares = portfolio.positions.get(ticker, 0)
        price = prices.get(ticker, 0.0)
        value = shares * price
        share = value / nav if nav else 0.0
        return {
            "metric": "position", "key": ticker,
            "title": f"{universe.name(ticker)} weight",
            "value": share, "display": _pct(share),
            "components": [
                {"label": "Shares held", "value": shares, "sub": "as entered by you"},
                {"label": "Last close", "value": price,
                 "sub": f"on or before {pit.clock_iso[:10]}"},
                {"label": "Position value", "value": value, "sub": _rupees(value)},
            ],
            "limit": policy.limits.max_position_pct,
            "limit_display": _pct(policy.limits.max_position_pct),
            "over_by": max(0.0, share - policy.limits.max_position_pct),
            "formula": f"{shares} shares x ₹{price:,.2f} = {_rupees(value)}, which is "
                       f"{_pct(share)} of {_rupees(nav)}.",
            "why": "One company can fail on its own. This caps what that costs you.",
            "provenance": _provenance(pit, [ticker]),
        }

    if metric in ("effective_holdings", "hhi"):
        rows = sorted(
            ({"label": universe.name(t), "ticker": t, "value": w,
              "sub": f"contributes {w * w:.4f} to the concentration index"}
             for t, w in weights.items()), key=lambda r: -r["value"])
        return {
            "metric": "effective_holdings", "title": "Effective holdings",
            "value": report.effective_holdings,
            "display": f"{report.effective_holdings:.1f} positions",
            "components": rows,
            "formula": "Square every weight and add them up — that is the "
                       f"Herfindahl index, {report.hhi:.4f} here. One divided by it "
                       f"gives {report.effective_holdings:.1f}.",
            "why": f"You hold {report.holdings} stocks, but the big ones dominate, so "
                   f"the risk behaves like about {report.effective_holdings:.0f} equal "
                   f"positions. Counting names overstates how spread out you are.",
            "provenance": _provenance(pit, list(portfolio.positions)),
        }

    if metric == "score":
        lim = policy.limits
        sector_w = {c: sum(weights.get(t, 0.0) for t in portfolio.positions
                           if sectors.get(t) == c)
                    for c in {sectors.get(t) for t in portfolio.positions}}
        over_position = sum(max(0.0, w - lim.max_position_pct) for w in weights.values())
        over_sector = sum(max(0.0, w - lim.max_sector_pct) for w in sector_w.values())
        shortfall = max(0.0, lim.min_cash_pct - report.cash_pct)
        p_position = 35 * min(1.0, over_position / 0.30)
        p_sector = 30 * min(1.0, over_sector / 0.25)
        p_cash = 10 * min(1.0, shortfall / max(lim.min_cash_pct, 0.01))
        p_breadth = 25 * min(1.0, max(0.0, 8 - report.effective_holdings) / 7)
        return {
            "metric": "score", "title": f"Score {report.score} / 100",
            "value": report.score, "display": f"{report.score} ({report.grade})",
            "components": [
                {"label": "Single-stock excess", "value": -round(p_position, 1),
                 "sub": f"{_pct(over_position)} over the {_pct(lim.max_position_pct)} "
                        f"cap, across all names · caps at -35"},
                {"label": "Industry excess", "value": -round(p_sector, 1),
                 "sub": f"{_pct(over_sector)} over the {_pct(lim.max_sector_pct)} cap "
                        f"· caps at -30"},
                {"label": "Cash shortfall", "value": -round(p_cash, 1),
                 "sub": f"{_pct(report.cash_pct)} held against a {_pct(lim.min_cash_pct)} "
                        f"requirement · caps at -10"},
                {"label": "Breadth", "value": -round(p_breadth, 1),
                 "sub": f"{report.effective_holdings:.1f} effective positions against a "
                        f"target of 8 · caps at -25"},
            ],
            "formula": "100 minus four capped penalties. The caps sum to 100, so no "
                       "single dimension can drive the score to zero on its own.",
            "why": "The formula is published rather than hidden so you can disagree "
                   "with the weights. Changing your profile changes the limits and "
                   "therefore this score — the portfolio has not moved.",
            "provenance": {"clock": pit.clock_iso,
                           "rule": f"Measured against {report.profile_name}: "
                                   f"{report.limits_describe}",
                           "tier": "EXACT", "rows": []},
        }

    if metric == "beta":
        return {
            "metric": "beta", "title": "Market sensitivity",
            "value": report.beta, "display": f"{report.beta}x" if report.beta else "—",
            "components": [],
            "formula": f"Covariance of your daily returns with {universe.benchmark_label()}, "
                       f"divided by the variance of the benchmark, over the history in "
                       f"the snapshot up to {pit.clock_iso[:10]}.",
            "why": "A beta of 1.2 means that when the market drops 10%, a basket like "
                   "this has tended to drop about 12%. It cuts both ways.",
            "provenance": _provenance(pit, list(portfolio.positions)),
        }

    if metric in ("max_drawdown", "drawdown"):
        return {
            "metric": "max_drawdown", "title": "Worst fall so far",
            "value": report.max_drawdown,
            "display": _pct(abs(report.max_drawdown)) if report.max_drawdown else "—",
            "components": [],
            "formula": "Your current share counts are priced back through every day in "
                       "the snapshot; this is the largest peak-to-trough fall in that "
                       "series.",
            "why": "This is not a forecast. It is what this exact basket has already "
                   "lived through — and it is the number that decides whether somebody "
                   "sells at the bottom.",
            "provenance": _provenance(pit, list(portfolio.positions)),
        }

    if metric == "cash":
        return {
            "metric": "cash", "title": "Cash buffer",
            "value": report.cash_pct, "display": _pct(report.cash_pct),
            "components": [{"label": "Cash", "value": portfolio.cash,
                            "sub": _rupees(portfolio.cash)},
                           {"label": "Total value", "value": nav, "sub": _rupees(nav)}],
            "limit": policy.limits.min_cash_pct,
            "limit_display": _pct(policy.limits.min_cash_pct),
            "formula": f"{_rupees(portfolio.cash)} divided by {_rupees(nav)}.",
            "why": "Cash is what lets you buy when prices fall, instead of having to "
                   "sell something first at the worst possible moment.",
            "provenance": {"clock": pit.clock_iso, "rule": "Cash is held as entered.",
                           "tier": "EXACT", "rows": []},
        }

    return {"error": f"no drill-down for {metric!r}",
            "available": ["nav", "sector", "position", "effective_holdings", "score",
                          "beta", "max_drawdown", "cash"]}
