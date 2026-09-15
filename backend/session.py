"""Session state: the clock, the fund, the policy, and the counters on the rail.

One session per running backend -- this is a single-operator demo tool, not a
multi-tenant service, and pretending otherwise would cost hours we do not have.

The counters are deliberately public and cumulative. `claims_rejected` and
`violations_blocked` are the two most honest numbers in the product, so they belong on
screen rather than buried in a log.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from agents.llm import ANALYST_MODEL
from core.db import connect
from core.pit import PointInTimeStore
from risk.engine import RiskEngine
from risk.policy import Policy
from risk.portfolio import Portfolio
from core import universe
from risk.seed import seed_fund

DB = Path(__file__).resolve().parent.parent / "data" / "snapshot.db"
FALLBACK_CLOCK = "2026-09-01"


def latest_clock(conn: sqlite3.Connection) -> str:
    """Default the clock to the snapshot's most recent bar, never a hardcoded date.

    risk/seed.py sizes the fund against the LAST close in the snapshot. Pinning the
    clock to any earlier date reprices those holdings and the fund opens already in
    breach -- with a hardcoded 2026-09-01 it opened at 30.5% IT against a 30% cap.
    Deriving the date keeps seed and clock consistent across re-ingestion.
    """
    row = conn.execute("SELECT MAX(date) AS d FROM prices").fetchone()
    return (row["d"] if row and row["d"] else FALLBACK_CLOCK)


@dataclass
class Counters:
    tick: int = 0
    claims_accepted: int = 0
    claims_rejected: int = 0
    violations_blocked: int = 0
    investigations: int = 0
    trades_executed: int = 0


@dataclass
class Session:
    conn: sqlite3.Connection
    pit: PointInTimeStore
    portfolio: Portfolio
    policy: Policy
    engine: RiskEngine
    # Prices come from the snapshot at the current clock, and sectors from the
    # universe config. Both used to be hardcoded in risk/seed.py, which is why only
    # one portfolio was ever possible.
    prices: dict[str, float] = field(default_factory=dict)
    sectors: dict[str, str] = field(default_factory=lambda: dict(universe.sectors()))
    portfolio_id: str | None = None
    portfolio_name: str = "Demo fund"
    counters: Counters = field(default_factory=Counters)
    model: str = ANALYST_MODEL
    orb: str = "idle"
    last_run_id: str | None = None
    # pending  = a trade cleared and staged for human approval (may be a remedied size)
    # requested = what the operator actually asked for, breach or not
    # They must stay separate: the policy simulator asks "would the ORIGINAL trade pass
    # under a different policy", and re-testing the remedy instead trivially answers yes.
    pending: dict | None = None
    requested: dict | None = None
    # A remedy is an OFFER, never an approval. Rolling it into `pending` meant a bare
    # "execute" filled a size the operator never agreed to -- the system substituting
    # its own number for the instruction and then acting on it.
    remedy: dict | None = None

    @classmethod
    def create(cls, clock: str | None = None) -> "Session":
        conn = connect(DB)
        policy = Policy.from_profile()
        return cls(conn=conn, pit=PointInTimeStore(conn, clock or latest_clock(conn)),
                   portfolio=seed_fund(), policy=policy, engine=RiskEngine(policy))

    # -- clock ---------------------------------------------------------------------
    def set_clock(self, when: str) -> None:
        self.pit.set_clock(when)
        self.reprice()

    def reprice(self) -> None:
        """Mark the book at the current sim clock.

        Without this, rewinding changes what the agents can read but leaves the
        portfolio valued at today's prices -- a subtle lookahead leak straight into the
        risk engine, which is the one place it must never reach.

        Prices every ticker in the universe, not just the ones held, so the picker and
        the presets can quote a price for anything the user might add.
        """
        for ticker in universe.tickers():
            close = self.pit.last_close(ticker)
            if close:
                self.prices[ticker] = round(float(close), 2)

    def set_portfolio(self, name: str, cash: float, positions: dict[str, int],
                      portfolio_id: str | None = None) -> None:
        self.portfolio = Portfolio(cash=float(cash),
                                   positions={k: int(v) for k, v in positions.items()})
        self.portfolio_name = name
        self.portfolio_id = portfolio_id
        self.pending = None
        self.remedy = None
        self.requested = None

    # -- derived state -------------------------------------------------------------
    def nav(self) -> float:
        return self.portfolio.nav(self.prices)

    def exposures(self) -> dict[str, float]:
        nav = self.nav()
        out: dict[str, float] = {}
        for sector in set(self.sectors.values()):
            out[sector] = self.portfolio.sector_value(sector, self.prices,
                                                      self.sectors) / nav if nav else 0.0
        return out

    def snapshot(self) -> dict:
        nav = self.nav()
        return {
            "sim_clock": self.pit.clock_iso,
            "portfolio_id": self.portfolio_id,
            "portfolio_name": self.portfolio_name,
            "nav": nav,
            "cash": self.portfolio.cash,
            "cash_pct": self.portfolio.cash / nav if nav else 0.0,
            "positions": [
                {"ticker": t, "shares": sh, "price": self.prices.get(t, 0.0),
                 "value": sh * self.prices.get(t, 0.0),
                 "weight": sh * self.prices.get(t, 0.0) / nav if nav else 0.0,
                 "sector": self.sectors.get(t, "UNKNOWN"),
                 "name": universe.name(t),
                 "sector_label": universe.sector_label(self.sectors.get(t, "UNKNOWN"))}
                for t, sh in sorted(self.portfolio.positions.items())
            ],
            "exposures": self.exposures(),
            "policy": {"version": self.policy.version, "profile": self.policy.profile,
                       "name": self.policy.name,
                       "describes": self.policy.describe(),
                       "limits": self.policy.limits.model_dump()},
            "counters": self.counters.__dict__,
            "model": self.model,
            "visible": self.pit.visible_counts(),
            "broker_execution": self.policy.governance.broker_execution,
        }
