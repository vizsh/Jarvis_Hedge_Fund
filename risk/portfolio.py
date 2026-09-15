"""Portfolio state. Pure data + arithmetic — no LLM, no I/O, no surprises."""
from __future__ import annotations

from pydantic import BaseModel, Field


class Portfolio(BaseModel):
    cash: float
    positions: dict[str, int] = Field(default_factory=dict)   # ticker -> shares

    def market_value(self, prices: dict[str, float]) -> float:
        return sum(sh * prices[t] for t, sh in self.positions.items() if t in prices)

    def nav(self, prices: dict[str, float]) -> float:
        return self.cash + self.market_value(prices)

    def position_value(self, ticker: str, prices: dict[str, float]) -> float:
        return self.positions.get(ticker, 0) * prices.get(ticker, 0.0)

    def sector_value(self, sector: str, prices: dict[str, float],
                     sectors: dict[str, str]) -> float:
        return sum(sh * prices.get(t, 0.0)
                   for t, sh in self.positions.items() if sectors.get(t) == sector)

    def weights(self, prices: dict[str, float]) -> dict[str, float]:
        nav = self.nav(prices)
        if nav <= 0:
            return {}
        return {t: sh * prices.get(t, 0.0) / nav for t, sh in self.positions.items()}

    def apply(self, ticker: str, side: str, shares: int, price: float,
              cost_bps: float = 0.0) -> "Portfolio":
        """Return a NEW portfolio. Immutability keeps the simulator honest."""
        fee = shares * price * (cost_bps / 10_000.0)
        pos = dict(self.positions)
        if side == "BUY":
            cash = self.cash - shares * price - fee
            pos[ticker] = pos.get(ticker, 0) + shares
        else:
            cash = self.cash + shares * price - fee
            pos[ticker] = pos.get(ticker, 0) - shares
        if pos.get(ticker) == 0:
            pos.pop(ticker, None)
        return Portfolio(cash=cash, positions=pos)


class Proposal(BaseModel):
    ticker: str
    side: str            # BUY | SELL
    shares: int
    price: float
    rationale: str = ""
    conviction: float = 0.0
