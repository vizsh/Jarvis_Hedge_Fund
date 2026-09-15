"""Portfolio X-ray: one screen that tells you what is actually wrong.

The risk firewall answers "may I make this trade". That is the wrong first question for
someone who has never looked at their concentration. The first question is "what does
what I already own look like", and until now the product had no answer to it.

Every number here is computed from prices in the snapshot. Nothing is generated, and
nothing is an opinion -- the health score is an explicit, published formula so a user
can disagree with the weights rather than being told to trust a number.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Any

from core import universe
from core.pit import PointInTimeStore
from risk.policy import Policy
from risk.portfolio import Portfolio


@dataclass
class Finding:
    """One thing worth telling the user, in their language."""
    severity: str          # high | medium | low | good
    code: str
    headline: str          # plain English, no jargon
    detail: str
    metric: float | None = None


@dataclass
class XRay:
    nav: float
    cash_pct: float
    holdings: int
    sectors: int
    top_holding: tuple[str, float] | None
    top_sector: tuple[str, float] | None
    hhi: float                      # concentration, 0..1
    effective_holdings: float       # 1/HHI: how many positions you REALLY have
    volatility_annual: float | None
    max_drawdown: float | None
    beta: float | None
    score: int
    grade: str
    profile: str = "retail"
    profile_name: str = ""
    limits_describe: str = ""
    findings: list[Finding] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "nav": self.nav, "cash_pct": self.cash_pct, "holdings": self.holdings,
            "sectors": self.sectors,
            "top_holding": self.top_holding, "top_sector": self.top_sector,
            "hhi": round(self.hhi, 4),
            "effective_holdings": round(self.effective_holdings, 1),
            "volatility_annual": self.volatility_annual,
            "max_drawdown": self.max_drawdown, "beta": self.beta,
            "score": self.score, "grade": self.grade,
            "profile": self.profile, "profile_name": self.profile_name,
            "limits_describe": self.limits_describe,
            "findings": [f.__dict__ for f in self.findings],
        }


def _returns(closes: list[float]) -> list[float]:
    return [b / a - 1 for a, b in zip(closes, closes[1:]) if a and b]


def portfolio_series(pit: PointInTimeStore, portfolio: Portfolio,
                     days: int = 250) -> list[tuple[str, float]]:
    """Daily portfolio value, held constant at today's share counts.

    This is a "what would this basket have done" series, not a track record — we do not
    know when anything was bought. Saying so matters: presenting it as realised
    performance would be the kind of quiet dishonesty this project exists to avoid.

    Holdings are carried forward onto a common date axis rather than summed per date.
    That is not a refinement, it is a correctness fix: NSE and US markets keep different
    holiday calendars, so a naive per-date sum drops the entire US half of the book on
    an Indian trading day that is a US holiday, and the entire Indian half on the
    reverse. The result is a sawtooth of ±40% daily "returns" that never happened, which
    poisoned volatility, drawdown and beta together — a mixed India/US portfolio was
    reporting a beta of -366 against the NIFTY. Carrying the last known close forward is
    what every portfolio system does and what the arithmetic assumes.

    The series starts only once every holding has at least one bar. Before that point a
    position would contribute zero and then appear, which is the same cliff in a
    different costume.
    """
    bars: dict[str, dict[str, float]] = {}
    for ticker in portfolio.positions:
        rows = {b["date"]: b["close"] for b in pit.prices(ticker, limit=days)
                if b["close"] is not None}
        if rows:
            bars[ticker] = rows
    if not bars:
        return []

    # Every holding must be priceable from the first date onwards.
    start = max(min(rows) for rows in bars.values())
    dates = sorted({d for rows in bars.values() for d in rows if d >= start})

    series: list[tuple[str, float]] = []
    carried: dict[str, float] = {}
    for date in dates:
        total = 0.0
        for ticker, rows in bars.items():
            if (close := rows.get(date)) is not None:
                carried[ticker] = close
            last = carried.get(ticker)
            if last is None:          # no bar at or before this date yet
                total = 0.0
                break
            total += last * portfolio.positions[ticker]
        if total:
            series.append((date, total))
    return series


def max_drawdown(values: list[float]) -> float:
    peak, worst = -math.inf, 0.0
    for v in values:
        peak = max(peak, v)
        if peak > 0:
            worst = min(worst, v / peak - 1)
    return worst


def analyse(pit: PointInTimeStore, portfolio: Portfolio, prices: dict[str, float],
            policy: Policy) -> XRay:
    nav = portfolio.nav(prices)
    weights = portfolio.weights(prices)
    cash_pct = portfolio.cash / nav if nav else 0.0
    sectors = {}
    for ticker, w in weights.items():
        s = universe.sector(ticker)
        sectors[s] = sectors.get(s, 0.0) + w

    # Herfindahl index over holdings. 1/HHI is the intuitive form: a portfolio with
    # ten equal positions has an effective count of ten; one where a single position
    # is 60% has an effective count near two, whatever the headline holding count says.
    hhi = sum(w * w for w in weights.values()) or 1.0
    effective = 1 / hhi if hhi else 0.0

    top_holding = max(weights.items(), key=lambda kv: kv[1]) if weights else None
    top_sector = max(sectors.items(), key=lambda kv: kv[1]) if sectors else None

    # --- realised risk, from the actual basket ---------------------------------
    series = portfolio_series(pit, portfolio)
    vol = mdd = beta = None
    if len(series) > 30:
        values = [v for _, v in series]
        rets = _returns(values)
        if rets:
            vol = statistics.pstdev(rets) * math.sqrt(252)
            mdd = max_drawdown(values)

        bench = pit.prices(universe.benchmark(), limit=len(series) + 5)
        if len(bench) > 30:
            by_date = dict(series)
            paired = [(by_date[b["date"]], b["close"]) for b in bench
                      if b["date"] in by_date]
            if len(paired) > 30:
                pr = _returns([p for p, _ in paired])
                br = _returns([b for _, b in paired])
                n = min(len(pr), len(br))
                if n > 20 and statistics.pvariance(br[:n]) > 0:
                    beta = (statistics.covariance(pr[:n], br[:n])
                            / statistics.pvariance(br[:n]))

    findings = _findings(policy, weights, sectors, cash_pct, effective, vol, mdd, beta)
    score, grade = _score(policy, weights, sectors, cash_pct, effective)

    return XRay(nav=nav, cash_pct=cash_pct, holdings=len(weights), sectors=len(sectors),
                top_holding=top_holding, top_sector=top_sector, hhi=hhi,
                effective_holdings=effective,
                volatility_annual=round(vol, 4) if vol else None,
                max_drawdown=round(mdd, 4) if mdd else None,
                beta=round(beta, 2) if beta else None,
                score=score, grade=grade, findings=findings,
                profile=policy.profile, profile_name=policy.name,
                limits_describe=policy.describe())


def _findings(policy: Policy, weights: dict[str, float], sectors: dict[str, float],
              cash_pct: float, effective: float, vol: float | None,
              mdd: float | None, beta: float | None) -> list[Finding]:
    lim = policy.limits
    out: list[Finding] = []

    # One finding for oversized positions, not one per position. Nine separate red
    # rows saying the same thing is an alarm, not a diagnosis -- the user cannot act
    # on a list that long, and the real signal (the sector breach) gets buried in it.
    over = [(t, w) for t, w in sorted(weights.items(), key=lambda kv: -kv[1])
            if w > lim.max_position_pct]
    if over:
        names = ", ".join(f"{universe.name(t)} {w:.0%}" for t, w in over[:3])
        more = f" and {len(over) - 3} more" if len(over) > 3 else ""
        biggest = over[0][1]
        out.append(Finding(
            "high" if biggest > lim.max_position_pct * 1.5 else "medium",
            "POSITION_CONCENTRATION",
            (f"{universe.name(over[0][0])} is {biggest:.0%} of your money"
             if len(over) == 1 else
             f"{len(over)} holdings are bigger than the {lim.max_position_pct:.0%} "
             f"single-stock limit"),
            f"{names}{more}. If one of these has a bad year, it moves your whole "
            f"portfolio on its own.",
            biggest))

    for code, w in sorted(sectors.items(), key=lambda kv: -kv[1])[:2]:
        if w > lim.max_sector_pct:
            out.append(Finding(
                "high" if w > lim.max_sector_pct * 1.3 else "medium",
                "SECTOR_CONCENTRATION",
                f"{universe.sector_label(code)} is {w:.0%} of your money",
                f"Above the {lim.max_sector_pct:.0%} sector limit. Companies in the "
                f"same sector tend to fall together, so this is less spread out than "
                f"the number of stocks suggests.",
                w))

    if cash_pct < lim.min_cash_pct:
        out.append(Finding(
            "medium", "LOW_CASH",
            f"Only {cash_pct:.0%} of your money is in cash",
            f"Below the {lim.min_cash_pct:.0%} buffer. Cash is what lets you buy when "
            f"prices fall instead of having to sell something first.",
            cash_pct))

    if effective < 5 and len(weights) >= 5:
        out.append(Finding(
            "medium", "FALSE_DIVERSIFICATION",
            f"You hold {len(weights)} stocks but they behave like {effective:.0f}",
            "Your biggest positions dominate. Counting holdings overstates how spread "
            "out you really are.",
            effective))

    if mdd is not None and mdd < -0.25:
        out.append(Finding(
            "high" if mdd < -0.4 else "medium", "DEEP_DRAWDOWN",
            f"This basket has fallen {abs(mdd):.0%} from a peak before",
            "Measured on the history we hold, with your current share counts. It is "
            "what this mix has already survived, not a forecast.",
            mdd))

    if beta is not None and beta > 1.2:
        out.append(Finding(
            "medium", "HIGH_BETA",
            f"You move about {beta:.1f}x as much as the {universe.benchmark_label()}",
            "When the market falls 10%, a basket like this has tended to fall more.",
            beta))

    if not out:
        out.append(Finding(
            "good", "COMPLIANT",
            "Nothing here breaches your limits",
            "Every position and sector is inside the caps you set, and your cash "
            "buffer is intact.", None))

    # Five is about as many problems as anyone can hold in their head at once.
    rank = {"high": 0, "medium": 1, "low": 2, "good": 3}
    out.sort(key=lambda f: rank[f.severity])
    return out[:5]


def _score(policy: Policy, weights: dict[str, float], sectors: dict[str, float],
           cash_pct: float, effective: float) -> tuple[int, str]:
    """A published formula, not a black box.

    Each category contributes a CAPPED penalty. The first version deducted linearly and
    without limit, so any badly concentrated portfolio hit zero under every profile --
    which destroyed the one thing the score is for, namely telling two bad portfolios
    apart and showing that the profile you pick changes the verdict.

    Caps sum to 100, so the score stays in range and every category keeps its
    discrimination. Anyone is free to disagree with these weights, which is the point
    of publishing them rather than emitting a number and asking for trust.
    """
    lim = policy.limits

    # Total excess over the single-stock cap. 30 percentage points of excess is
    # "as bad as this dimension gets".
    over_position = sum(max(0.0, w - lim.max_position_pct) for w in weights.values())
    p_position = 35 * min(1.0, over_position / 0.30)

    # Sector excess is correlated risk, so it saturates faster: 25pp maxes it out.
    over_sector = sum(max(0.0, w - lim.max_sector_pct) for w in sectors.values())
    p_sector = 30 * min(1.0, over_sector / 0.25)

    # Cash shortfall, relative to the requirement rather than absolute.
    shortfall = max(0.0, lim.min_cash_pct - cash_pct)
    p_cash = 10 * min(1.0, shortfall / max(lim.min_cash_pct, 0.01))

    # Breadth: eight effective positions is the target, one is the floor.
    p_breadth = 25 * min(1.0, max(0.0, 8 - effective) / 7)

    score = int(max(0, min(100, round(100 - p_position - p_sector - p_cash - p_breadth))))
    grade = ("A" if score >= 85 else "B" if score >= 70 else
             "C" if score >= 55 else "D" if score >= 40 else "E")
    return score, grade
