"""Stress tests: what your actual holdings did in crises that actually happened.

Two kinds, and the difference matters:

  HISTORICAL   Replays a real window from the snapshot. Your current share counts are
               valued at the prices that really occurred, so the answer is arithmetic
               over recorded history, not a model. If a stock had not listed yet, it is
               excluded and the coverage figure says so.

  HYPOTHETICAL A parametric shock ("technology falls 30%"). Honest about being a
               what-if: it applies a uniform move and makes no claim about correlation.

Historical scenarios are the ones worth showing. "Your portfolio would have fallen 38%
in the Covid crash" is a fact about your holdings; a Monte Carlo fan chart is a fact
about someone's assumptions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core import universe
from core.pit import PointInTimeStore
from risk.portfolio import Portfolio

# Windows chosen because they are regimes a person remembers, not because they flatter
# the result. Each is (start, trough/end) with the peak first.
HISTORICAL = [
    {"key": "covid", "label": "Covid crash",
     "blurb": "The fastest bear market in history.",
     "start": "2020-02-19", "end": "2020-03-23"},
    {"key": "covid_recovery", "label": "Covid recovery",
     "blurb": "The nine months after the bottom.",
     "start": "2020-03-23", "end": "2020-12-31"},
    {"key": "rate_shock_2022", "label": "2022 rate shock",
     "blurb": "Inflation, rate rises, and a long grind down.",
     "start": "2022-01-17", "end": "2022-06-17"},
    {"key": "adani_2023", "label": "Jan 2023 selloff",
     "blurb": "A sharp, concentrated shock to Indian large caps.",
     "start": "2023-01-24", "end": "2023-03-20"},
]

# Uniform shocks. Deliberately simple and labelled as such.
HYPOTHETICAL = [
    {"key": "market_10", "label": "Market falls 10%", "scope": "ALL", "shock": -0.10},
    {"key": "market_20", "label": "Market falls 20%", "scope": "ALL", "shock": -0.20},
    {"key": "it_30", "label": "Technology falls 30%", "scope": "IT", "shock": -0.30},
    {"key": "banks_25", "label": "Banks fall 25%", "scope": "FINANCIALS", "shock": -0.25},
]


@dataclass
class Result:
    key: str
    label: str
    blurb: str
    kind: str                 # historical | hypothetical
    portfolio_return: float
    benchmark_return: float | None
    value_change: float
    nav_before: float
    nav_after: float
    coverage: float           # share of NAV we could actually price in the window
    worst: list[tuple[str, float]]
    best: list[tuple[str, float]]

    def as_dict(self) -> dict[str, Any]:
        return {**self.__dict__,
                "worst": [(universe.name(t), r) for t, r in self.worst],
                "best": [(universe.name(t), r) for t, r in self.best]}


def _close_near(pit: PointInTimeStore, ticker: str, date: str) -> float | None:
    row = pit.conn.execute(
        "SELECT close FROM prices WHERE ticker = ? AND date <= ? ORDER BY date DESC "
        "LIMIT 1", (ticker, date)).fetchone()
    return row["close"] if row else None


def run_historical(pit: PointInTimeStore, portfolio: Portfolio, scenario: dict,
                   prices: dict[str, float]) -> Result:
    nav_before = portfolio.nav(prices)
    start, end = scenario["start"], scenario["end"]

    priced = 0.0
    before = after = portfolio.cash          # cash does not move
    moves: list[tuple[str, float]] = []

    for ticker, shares in portfolio.positions.items():
        p0 = _close_near(pit, ticker, start)
        p1 = _close_near(pit, ticker, end)
        held_now = shares * prices.get(ticker, 0.0)
        if not p0 or not p1:
            # Not listed yet, or no data in the window. Carry it unchanged and let the
            # coverage number admit the gap rather than pretending it survived flat.
            before += held_now
            after += held_now
            continue
        before += shares * p0
        after += shares * p1
        priced += held_now
        moves.append((ticker, p1 / p0 - 1))

    bench_return = None
    b0 = _close_near(pit, universe.benchmark(), start)
    b1 = _close_near(pit, universe.benchmark(), end)
    if b0 and b1:
        bench_return = b1 / b0 - 1

    ret = (after / before - 1) if before else 0.0
    moves.sort(key=lambda kv: kv[1])
    return Result(
        key=scenario["key"], label=scenario["label"], blurb=scenario["blurb"],
        kind="historical", portfolio_return=round(ret, 4),
        benchmark_return=round(bench_return, 4) if bench_return is not None else None,
        value_change=round(nav_before * ret, 2),
        nav_before=round(nav_before, 2), nav_after=round(nav_before * (1 + ret), 2),
        coverage=round(priced / nav_before, 3) if nav_before else 0.0,
        worst=moves[:3], best=moves[-3:][::-1])


def run_hypothetical(portfolio: Portfolio, scenario: dict,
                     prices: dict[str, float]) -> Result:
    nav_before = portfolio.nav(prices)
    shock, scope = scenario["shock"], scenario["scope"]

    after = portfolio.cash
    moves: list[tuple[str, float]] = []
    hit = 0.0
    for ticker, shares in portfolio.positions.items():
        value = shares * prices.get(ticker, 0.0)
        applies = scope == "ALL" or universe.sector(ticker) == scope
        after += value * (1 + shock) if applies else value
        if applies:
            moves.append((ticker, shock))
            hit += value

    ret = (after / nav_before - 1) if nav_before else 0.0
    return Result(
        key=scenario["key"], label=scenario["label"],
        blurb=f"A uniform {abs(shock):.0%} fall applied to "
              f"{'everything you hold' if scope == 'ALL' else universe.sector_label(scope)}. "
              f"A what-if, not a forecast.",
        kind="hypothetical", portfolio_return=round(ret, 4), benchmark_return=None,
        value_change=round(nav_before * ret, 2),
        nav_before=round(nav_before, 2), nav_after=round(nav_before * (1 + ret), 2),
        coverage=round(hit / nav_before, 3) if nav_before else 0.0,
        worst=moves[:3], best=[])


def run_all(pit: PointInTimeStore, portfolio: Portfolio,
            prices: dict[str, float]) -> dict[str, Any]:
    if not portfolio.positions:
        return {"scenarios": [], "worst_case": None}

    results = [run_historical(pit, portfolio, s, prices) for s in HISTORICAL]
    results += [run_hypothetical(portfolio, s, prices) for s in HYPOTHETICAL]
    losses = [r for r in results if r.portfolio_return < 0]
    worst = min(losses, key=lambda r: r.portfolio_return) if losses else None
    return {"scenarios": [r.as_dict() for r in results],
            "worst_case": worst.as_dict() if worst else None,
            "benchmark_label": universe.benchmark_label()}


def find(key: str) -> dict | None:
    for s in (*HISTORICAL, *HYPOTHETICAL):
        if s["key"] == key:
            return s
    return None
