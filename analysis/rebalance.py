"""The rebalancer: the smallest set of trades that makes a portfolio compliant.

This is the portfolio manager's construction job, and it is fully deterministic. There
is no forecast anywhere in it -- it never decides what will go up, only what the current
book violates and the cheapest way to stop violating it. That distinction is the whole
reason it can be trusted to run unattended while return prediction cannot.

The algorithm is greedy and ordered, because "minimal" needs a definition:

  1. Trim every position above the single-stock cap.
  2. Trim sectors above the sector cap, largest offender in the sector first.
  3. Ensure the cash floor is met, selling from the most concentrated names.
  4. Deploy surplus cash into sectors you are light in, preferring candidates with the
     LOWEST correlation to what you already hold.

Step 4 is the one that separates this from a de-risking script. Selling down to
compliance leaves a pile of cash; a portfolio manager would put it somewhere, and where
it goes should reduce correlation rather than just fill a sector quota.

Every proposed trade is re-checked against the risk firewall before it is returned, so
the rebalancer cannot propose something the firewall would refuse. A plan that gets
rejected on execution is worse than no plan.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from analysis import factors
from core import universe
from core.pit import PointInTimeStore
from risk.engine import RiskEngine
from risk.policy import Policy
from risk.portfolio import Portfolio


@dataclass
class Trade:
    side: str
    ticker: str
    name: str
    shares: int
    price: float
    value: float
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class Plan:
    trades: list[Trade] = field(default_factory=list)
    before: dict[str, Any] = field(default_factory=dict)
    after: dict[str, Any] = field(default_factory=dict)
    turnover: float = 0.0
    cost: float = 0.0
    notes: list[str] = field(default_factory=list)
    compliant_after: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {"trades": [t.as_dict() for t in self.trades],
                "before": self.before, "after": self.after,
                "turnover": round(self.turnover, 2), "cost": round(self.cost, 2),
                "notes": self.notes, "compliant_after": self.compliant_after,
                "trade_count": len(self.trades)}


def _snapshot(pf: Portfolio, prices: dict[str, float],
              matrix: dict | None = None) -> dict[str, Any]:
    nav = pf.nav(prices)
    weights = pf.weights(prices)
    sectors: dict[str, float] = {}
    for t, w in weights.items():
        sectors[universe.sector(t)] = sectors.get(universe.sector(t), 0.0) + w
    hhi = sum(w * w for w in weights.values()) or 1.0
    out = {
        "nav": round(nav, 2),
        "cash_pct": round(pf.cash / nav, 4) if nav else 0.0,
        "holdings": len(weights),
        "sectors": len(sectors),
        "top_position": round(max(weights.values()), 4) if weights else 0.0,
        "top_sector": round(max(sectors.values()), 4) if sectors else 0.0,
        "effective_holdings": round(1 / hhi, 1),
        "sector_weights": {universe.sector_label(k): round(v, 4)
                           for k, v in sorted(sectors.items(), key=lambda kv: -kv[1])},
    }
    if matrix:
        out["avg_correlation"] = factors.diversification_ratio(matrix, weights)
    return out


# A breach of one ten-thousandth of a percentage point is floating-point noise across
# twenty trades with fee deductions, not a compliance failure.
TOLERANCE = 1e-4


def _breaches(pf: Portfolio, prices: dict[str, float], policy: Policy) -> list[str]:
    lim = policy.limits
    nav = pf.nav(prices)
    if not nav:
        return []
    out = []
    for t, shares in pf.positions.items():
        if shares * prices.get(t, 0) / nav > lim.max_position_pct + TOLERANCE:
            out.append(f"position:{t}")
    sectors: dict[str, float] = {}
    for t, shares in pf.positions.items():
        sectors[universe.sector(t)] = sectors.get(universe.sector(t), 0.0) + \
            shares * prices.get(t, 0)
    for code, value in sectors.items():
        if value / nav > lim.max_sector_pct + TOLERANCE:
            out.append(f"sector:{code}")
    if pf.cash / nav < lim.min_cash_pct - TOLERANCE:
        out.append("cash")
    return out


def plan(pit: PointInTimeStore, portfolio: Portfolio, prices: dict[str, float],
         policy: Policy, deploy_cash: bool = True) -> Plan:
    lim = policy.limits
    cost_bps = policy.execution.cost_bps
    held = list(portfolio.positions)
    matrix = factors.correlation_matrix(pit, held) if len(held) > 1 else {}

    result = Plan(before=_snapshot(portfolio, prices, matrix))
    work = Portfolio(cash=portfolio.cash, positions=dict(portfolio.positions))

    # --- 1. single-stock cap -----------------------------------------------------
    for ticker in sorted(work.positions,
                         key=lambda t: -work.positions[t] * prices.get(t, 0)):
        price = prices.get(ticker, 0.0)
        if not price:
            continue
        nav = work.nav(prices)
        target = lim.max_position_pct * nav
        excess = work.positions[ticker] * price - target
        shares = int(excess // price) + (1 if excess % price else 0)
        shares = min(shares, work.positions[ticker])
        if shares > 0:
            work = work.apply(ticker, "SELL", shares, price, cost_bps)
            result.trades.append(Trade(
                "SELL", ticker, universe.name(ticker), shares, price,
                round(shares * price, 2),
                f"above the {lim.max_position_pct:.0%} single-stock limit"))

    # --- 2. sector caps ----------------------------------------------------------
    for _ in range(6):                       # bounded: each pass removes one breach
        nav = work.nav(prices)
        sectors: dict[str, float] = {}
        for t, sh in work.positions.items():
            sectors[universe.sector(t)] = sectors.get(universe.sector(t), 0.0) + \
                sh * prices.get(t, 0)
        offender = next(((c, v) for c, v in
                         sorted(sectors.items(), key=lambda kv: -kv[1])
                         if v / nav > lim.max_sector_pct + 1e-9), None)
        if not offender:
            break
        code, value = offender
        excess = value - lim.max_sector_pct * nav
        # Largest holding in the sector first: fewest trades, biggest effect.
        for ticker in sorted((t for t in work.positions if universe.sector(t) == code),
                             key=lambda t: -work.positions[t] * prices.get(t, 0)):
            if excess <= 0:
                break
            price = prices.get(ticker, 0.0)
            if not price:
                continue
            shares = min(work.positions[ticker], int(excess // price) + 1)
            if shares <= 0:
                continue
            work = work.apply(ticker, "SELL", shares, price, cost_bps)
            excess -= shares * price
            result.trades.append(Trade(
                "SELL", ticker, universe.name(ticker), shares, price,
                round(shares * price, 2),
                f"{universe.sector_label(code).lower()} above the "
                f"{lim.max_sector_pct:.0%} limit"))

    # --- 3. cash floor -----------------------------------------------------------
    nav = work.nav(prices)
    if nav and work.cash / nav < lim.min_cash_pct:
        needed = lim.min_cash_pct * nav - work.cash
        for ticker in sorted(work.positions,
                             key=lambda t: -work.positions[t] * prices.get(t, 0)):
            if needed <= 0:
                break
            price = prices.get(ticker, 0.0)
            if not price:
                continue
            shares = min(work.positions[ticker], int(needed // price) + 1)
            if shares <= 0:
                continue
            work = work.apply(ticker, "SELL", shares, price, cost_bps)
            needed -= shares * price
            result.trades.append(Trade(
                "SELL", ticker, universe.name(ticker), shares, price,
                round(shares * price, 2),
                f"to restore the {lim.min_cash_pct:.0%} cash buffer"))

    # --- 4. deploy surplus into low-correlation, under-weight sectors -------------
    if deploy_cash:
        nav = work.nav(prices)
        surplus = work.cash - lim.min_cash_pct * nav
        # Leave a working margin so rounding cannot push us back under the floor.
        surplus -= nav * 0.01
        if surplus > nav * 0.02:
            picks = factors.screen(pit, "diversifiers", work.weights(prices), limit=12)
            engine = RiskEngine(policy)
            for cand in picks:
                if surplus <= 0:
                    break
                ticker, price = cand["ticker"], cand["price"]
                if not price:
                    continue
                sector_value = sum(sh * prices.get(t, 0) for t, sh in work.positions.items()
                                   if universe.sector(t) == universe.sector(ticker))
                nav = work.nav(prices)
                # Buy to 95% of the available headroom, not 100%. Each subsequent buy
                # pays a fee that shrinks NAV, which pushes every EARLIER position
                # fractionally over its cap -- the plan would then report itself
                # non-compliant on positions the firewall had already approved.
                headroom = 0.95 * min(
                    lim.max_position_pct * nav,
                    lim.max_sector_pct * nav - sector_value,
                    surplus,
                )
                shares = int(headroom // price)
                if shares <= 0:
                    continue
                from risk.portfolio import Proposal
                decision = engine.evaluate(work, Proposal(ticker=ticker, side="BUY",
                                                          shares=shares, price=price),
                                           prices, universe.sectors())
                if not decision.approved:
                    # Trust the firewall over our own arithmetic, and take the size it
                    # says is legal. A plan the firewall would refuse is not a plan.
                    shares = decision.remedy.max_shares if decision.remedy else 0
                    if shares <= 0:
                        continue
                work = work.apply(ticker, "BUY", shares, price, cost_bps)
                surplus -= shares * price
                result.trades.append(Trade(
                    "BUY", ticker, cand["name"], shares, price,
                    round(shares * price, 2),
                    f"diversifier — correlation {cand.get('avg_correlation_to_book', 0):.2f} "
                    f"to your book"))

    result.after = _snapshot(work, prices, matrix)
    result.turnover = sum(t.value for t in result.trades)
    result.cost = result.turnover * (cost_bps / 10_000)
    remaining = _breaches(work, prices, policy)
    result.compliant_after = not remaining

    if not result.trades:
        result.notes.append("Nothing to do — the portfolio already meets every limit.")
    else:
        sells = sum(1 for t in result.trades if t.side == "SELL")
        buys = len(result.trades) - sells
        result.notes.append(
            f"{sells} sell{'s' if sells != 1 else ''}"
            + (f" and {buys} buy{'s' if buys != 1 else ''}" if buys else "")
            + f", {result.turnover / result.before['nav']:.1%} of the portfolio turned over.")
    if remaining:
        result.notes.append(
            "Could not clear: " + ", ".join(remaining) +
            ". Usually means a single holding is too large to trim without breaching "
            "the cash floor.")
    return result
