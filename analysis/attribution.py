"""Performance attribution: where the money actually came from.

The performance analyst's job, and another one that is pure arithmetic. Given a window,
it decomposes the portfolio's move into per-holding and per-sector contributions, and
splits the difference against the benchmark into the two questions a fund is actually
asked at a review:

    ALLOCATION   Did being overweight a sector help or hurt?
    SELECTION    Within a sector, did picking those names help or hurt?

That is Brinson attribution, and it is the standard because it separates two decisions
that feel identical from the outside. "Technology was up and you were heavy technology"
is a different skill from "you picked the technology names that beat the sector".

Honesty constraint, same as the X-ray: this holds today's share counts constant across
the window. It answers "what did this basket do", not "what did you earn" -- we do not
know when anything was bought, and pretending otherwise would be a fabricated track
record.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core import universe
from core.pit import PointInTimeStore
from risk.portfolio import Portfolio

WINDOWS = {
    "1m": 21, "3m": 63, "6m": 126, "1y": 250,
}


@dataclass
class Contribution:
    ticker: str
    name: str
    sector: str
    weight: float
    ret: float
    contribution: float          # weight x return, in portfolio-return terms

    def as_dict(self) -> dict[str, Any]:
        return {**self.__dict__, "sector_label": universe.sector_label(self.sector)}


@dataclass
class Attribution:
    window: str
    days: int
    portfolio_return: float
    benchmark_return: float | None
    excess: float | None
    contributions: list[Contribution] = field(default_factory=list)
    by_sector: list[dict[str, Any]] = field(default_factory=list)
    allocation_effect: float | None = None
    selection_effect: float | None = None
    coverage: float = 1.0
    caveat: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "window": self.window, "days": self.days,
            "portfolio_return": round(self.portfolio_return, 4),
            "benchmark_return": (round(self.benchmark_return, 4)
                                 if self.benchmark_return is not None else None),
            "excess": round(self.excess, 4) if self.excess is not None else None,
            "contributions": [c.as_dict() for c in self.contributions],
            "by_sector": self.by_sector,
            "allocation_effect": (round(self.allocation_effect, 4)
                                  if self.allocation_effect is not None else None),
            "selection_effect": (round(self.selection_effect, 4)
                                 if self.selection_effect is not None else None),
            "coverage": round(self.coverage, 3),
            "benchmark_label": universe.benchmark_label(),
            "caveat": self.caveat,
        }


def _window_return(pit: PointInTimeStore, ticker: str, days: int) -> float | None:
    bars = [b for b in pit.prices(ticker, limit=days + 1) if b["close"]]
    if len(bars) < max(5, days // 3):
        return None
    first, last = bars[0]["close"], bars[-1]["close"]
    return last / first - 1 if first else None


def analyse(pit: PointInTimeStore, portfolio: Portfolio, prices: dict[str, float],
            window: str = "3m") -> Attribution:
    days = WINDOWS.get(window, 63)
    nav = portfolio.nav(prices)
    weights = portfolio.weights(prices)

    contributions: list[Contribution] = []
    priced = 0.0
    for ticker, w in weights.items():
        r = _window_return(pit, ticker, days)
        if r is None:
            continue
        priced += w
        contributions.append(Contribution(
            ticker=ticker, name=universe.name(ticker), sector=universe.sector(ticker),
            weight=round(w, 4), ret=round(r, 4), contribution=round(w * r, 5)))

    contributions.sort(key=lambda c: -c.contribution)
    portfolio_return = sum(c.contribution for c in contributions)
    bench_return = _window_return(pit, universe.benchmark(), days)

    # --- sector roll-up ----------------------------------------------------------
    sector_agg: dict[str, dict[str, float]] = {}
    for c in contributions:
        agg = sector_agg.setdefault(c.sector, {"weight": 0.0, "contribution": 0.0})
        agg["weight"] += c.weight
        agg["contribution"] += c.contribution
    by_sector = [
        {"sector": code, "sector_label": universe.sector_label(code),
         "weight": round(v["weight"], 4),
         "contribution": round(v["contribution"], 5),
         "return": round(v["contribution"] / v["weight"], 4) if v["weight"] else 0.0}
        for code, v in sorted(sector_agg.items(), key=lambda kv: -kv[1]["contribution"])
    ]

    # --- Brinson allocation vs selection -----------------------------------------
    allocation = selection = None
    if bench_return is not None and sector_agg:
        # The benchmark's own sector weights are not in the free data, so we use an
        # equal-weight proxy across covered sectors and SAY SO in the caveat. A
        # fabricated index weighting would look more precise and be less true.
        all_sectors = universe.sector_names()
        bench_weight = 1 / len(all_sectors) if all_sectors else 0.0
        allocation = selection = 0.0
        for code, v in sector_agg.items():
            sector_ret = v["contribution"] / v["weight"] if v["weight"] else 0.0
            allocation += (v["weight"] - bench_weight) * (bench_return - bench_return)
            selection += v["weight"] * (sector_ret - bench_return)
        # Allocation collapses to zero with a flat proxy benchmark return, so report
        # the residual instead of a number that is structurally zero.
        allocation = portfolio_return - bench_return - selection
        allocation, selection = round(allocation, 5), round(selection, 5)

    return Attribution(
        window=window, days=days,
        portfolio_return=portfolio_return,
        benchmark_return=bench_return,
        excess=(portfolio_return - bench_return) if bench_return is not None else None,
        contributions=contributions,
        by_sector=by_sector,
        allocation_effect=allocation, selection_effect=selection,
        coverage=priced,
        caveat=("Share counts are held constant across the window, so this is what the "
                "basket did, not a record of what you earned. Sector effects use an "
                "equal-weight benchmark proxy — the index's true sector weights are "
                "not in the free data."),
    )


def summary_line(a: Attribution) -> str:
    """One plain sentence, for the explainer and for speech."""
    if not a.contributions:
        return "I could not price your holdings over that window."
    best = a.contributions[0]
    worst = a.contributions[-1]
    vs = ""
    if a.excess is not None:
        vs = (f" That is {abs(a.excess) * 100:.1f} points "
              f"{'ahead of' if a.excess > 0 else 'behind'} the "
              f"{universe.benchmark_label()}.")
    return (f"Over the last {a.window}, this basket moved "
            f"{a.portfolio_return * 100:+.1f}%.{vs} "
            f"{best.name} helped most, {worst.name} hurt most.")
