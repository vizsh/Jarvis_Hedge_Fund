"""The Risk Firewall.

Pure, deterministic, unit-testable, and completely LLM-free. This is the component the
entire pitch rests on: if the model layer disappoints on the day, a working firewall
still demos.

Two things make it more than a threshold check:

1.  It does not merely reject. It solves in closed form for the largest trade that
    WOULD pass, and names which constraint binds. "Rejected" is a dead end;
    "reduce to 62 shares, sector lands at 29.8%" is a decision.

2.  Every message is a deterministic template built from measured numbers -- never a
    generative explanation, never a bare confidence score. The explanation is
    reproducible from the inputs alone.

Closed-form remedy, buying n shares at price p with cost rate c (= bps/10_000):

    nav_after  = nav - n*p*c                (fees are the only NAV leak at fair value)
    position:  n <= (max_pos*nav - pos_val)      / (p * (1 + max_pos*c))
    sector:    n <= (max_sec*nav - sector_val)   / (p * (1 + max_sec*c))
    cash:      n <= (cash - min_cash*nav)        / (p * (1 + c*(1 - min_cash)))

The binding constraint is the minimum of the three.
"""
from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel, Field

from risk.policy import Policy
from risk.portfolio import Portfolio, Proposal


class Violation(BaseModel):
    code: str
    message: str          # deterministic template, safe to read aloud
    measured: float
    limit: float
    headroom: float


class Remedy(BaseModel):
    max_shares: int
    binding_constraint: str
    explanation: str
    resulting: dict[str, float] = Field(default_factory=dict)


class RiskDecision(BaseModel):
    approved: bool
    policy_version: str
    violations: list[Violation] = Field(default_factory=list)
    remedy: Remedy | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)

    @property
    def summary(self) -> str:
        if self.approved:
            return "APPROVED - within all policy limits."
        codes = ", ".join(v.code for v in self.violations)
        return f"REJECTED - {codes}"


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


class RiskEngine:
    def __init__(self, policy: Policy | None = None):
        self.policy = policy or Policy.load()

    # -- the closed-form remedy ----------------------------------------------------
    def max_allowable_shares(self, pf: Portfolio, proposal: Proposal,
                             prices: dict[str, float],
                             sectors: dict[str, str]) -> tuple[int, str]:
        lim, c = self.policy.limits, self.policy.execution.cost
        p = proposal.price
        nav = pf.nav(prices)
        if p <= 0 or nav <= 0:
            return 0, "INVALID_INPUT"

        sector = sectors.get(proposal.ticker, "UNKNOWN")
        pos_val = pf.position_value(proposal.ticker, prices)
        sec_val = pf.sector_value(sector, prices, sectors)

        bounds = {
            "POSITION_LIMIT": (lim.max_position_pct * nav - pos_val)
            / (p * (1 + lim.max_position_pct * c)),
            "SECTOR_LIMIT": (lim.max_sector_pct * nav - sec_val)
            / (p * (1 + lim.max_sector_pct * c)),
            "CASH_RESERVE": (pf.cash - lim.min_cash_pct * nav)
            / (p * (1 + c * (1 - lim.min_cash_pct))),
        }
        binding = min(bounds, key=lambda k: bounds[k])
        n = max(0, math.floor(min(bounds.values())))
        return n, binding

    # -- evaluation ----------------------------------------------------------------
    def evaluate(self, pf: Portfolio, proposal: Proposal, prices: dict[str, float],
                 sectors: dict[str, str]) -> RiskDecision:
        lim = self.policy.limits
        pol_v = self.policy.version
        violations: list[Violation] = []

        if proposal.side == "SELL":
            held = pf.positions.get(proposal.ticker, 0)
            if proposal.shares > held:
                violations.append(Violation(
                    code="INSUFFICIENT_HOLDING",
                    message=(f"Cannot sell {proposal.shares} shares of {proposal.ticker}: "
                             f"position holds {held}."),
                    measured=float(proposal.shares), limit=float(held),
                    headroom=float(held - proposal.shares)))
                remedy = Remedy(
                    max_shares=held, binding_constraint="INSUFFICIENT_HOLDING",
                    explanation=f"Reduce to {held} shares - shorting is disabled.")
                return RiskDecision(approved=False, policy_version=pol_v,
                                    violations=violations, remedy=remedy,
                                    metrics=self._metrics(pf, proposal, prices, sectors))
            return RiskDecision(approved=True, policy_version=pol_v,
                                metrics=self._metrics(pf, proposal, prices, sectors))

        # --- BUY ---
        after = pf.apply(proposal.ticker, "BUY", proposal.shares, proposal.price,
                         self.policy.execution.cost_bps)
        nav_after = after.nav(prices)
        sector = sectors.get(proposal.ticker, "UNKNOWN")

        pos_w = after.position_value(proposal.ticker, prices) / nav_after if nav_after else 0.0
        sec_w = after.sector_value(sector, prices, sectors) / nav_after if nav_after else 0.0
        cash_w = after.cash / nav_after if nav_after else 0.0

        if pos_w > lim.max_position_pct + 1e-12:
            violations.append(Violation(
                code="POSITION_LIMIT",
                message=(f"{proposal.ticker} would reach {_pct(pos_w)} of NAV, above the "
                         f"{_pct(lim.max_position_pct)} single-position ceiling."),
                measured=pos_w, limit=lim.max_position_pct,
                headroom=lim.max_position_pct - pos_w))

        if sec_w > lim.max_sector_pct + 1e-12:
            violations.append(Violation(
                code="SECTOR_LIMIT",
                message=(f"{sector} exposure would rise to {_pct(sec_w)}, above the "
                         f"{_pct(lim.max_sector_pct)} sector cap."),
                measured=sec_w, limit=lim.max_sector_pct,
                headroom=lim.max_sector_pct - sec_w))

        if cash_w < lim.min_cash_pct - 1e-12:
            violations.append(Violation(
                code="CASH_RESERVE",
                message=(f"Cash would fall to {_pct(cash_w)}, below the "
                         f"{_pct(lim.min_cash_pct)} minimum reserve."),
                measured=cash_w, limit=lim.min_cash_pct,
                headroom=cash_w - lim.min_cash_pct))

        remedy = None
        if violations:
            n, binding = self.max_allowable_shares(pf, proposal, prices, sectors)
            if n <= 0:
                explanation = (f"No size of this trade is compliant - {binding} is already "
                               f"at its limit. Reduce exposure elsewhere first.")
                resulting: dict[str, float] = {}
            else:
                sim = pf.apply(proposal.ticker, "BUY", n, proposal.price,
                               self.policy.execution.cost_bps)
                sim_nav = sim.nav(prices)
                resulting = {
                    "position_pct": sim.position_value(proposal.ticker, prices) / sim_nav,
                    "sector_pct": sim.sector_value(sector, prices, sectors) / sim_nav,
                    "cash_pct": sim.cash / sim_nav,
                }
                explanation = (f"Reduce from {proposal.shares} to {n} shares - {binding} "
                               f"binds, leaving {sector} at {_pct(resulting['sector_pct'])} "
                               f"and cash at {_pct(resulting['cash_pct'])}.")
            remedy = Remedy(max_shares=n, binding_constraint=binding,
                            explanation=explanation, resulting=resulting)

        return RiskDecision(
            approved=not violations, policy_version=pol_v, violations=violations,
            remedy=remedy, metrics=self._metrics(pf, proposal, prices, sectors))

    def _metrics(self, pf: Portfolio, proposal: Proposal, prices: dict[str, float],
                 sectors: dict[str, str]) -> dict[str, Any]:
        nav = pf.nav(prices)
        sector = sectors.get(proposal.ticker, "UNKNOWN")
        return {
            "nav_before": nav,
            "cash_pct_before": pf.cash / nav if nav else 0.0,
            "position_pct_before": pf.position_value(proposal.ticker, prices) / nav if nav else 0.0,
            "sector": sector,
            "sector_pct_before": pf.sector_value(sector, prices, sectors) / nav if nav else 0.0,
            "notional": proposal.shares * proposal.price,
            "cost": proposal.shares * proposal.price * self.policy.execution.cost,
        }
