"""Factor computation, correlation, and screening — the analyst's screening desk.

This is the part of a fund's work that is genuinely automatable, because it is
arithmetic over price history rather than a forecast. Nothing here predicts anything;
it measures what already happened and ranks on it.

The correlation engine is the one that earns its place in the pitch. "You own eight
stocks" is a count. "Four of them move together at 0.9, so you really own five
positions" is a fact that changes what you do next, and no retail tool tells you.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Any

from core import universe
from core.pit import PointInTimeStore

WINDOW = 250          # ~1 trading year
MIN_OVERLAP = 60      # fewer shared days than this and a correlation is noise


@dataclass
class Factors:
    ticker: str
    name: str
    sector: str
    price: float
    ret_1m: float | None
    ret_3m: float | None
    ret_12m: float | None
    volatility: float | None
    max_drawdown: float | None
    rsi: float | None
    above_200d: bool | None
    score: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        d = self.__dict__.copy()
        d["sector_label"] = universe.sector_label(self.sector)
        return d


def _returns(closes: list[float]) -> list[float]:
    return [b / a - 1 for a, b in zip(closes, closes[1:]) if a and b]


def _rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains = losses = 0.0
    for a, b in zip(closes[-period - 1:-1], closes[-period:]):
        change = b - a
        gains += max(change, 0.0)
        losses += max(-change, 0.0)
    if losses == 0:
        return 100.0
    rs = (gains / period) / (losses / period)
    return 100 - 100 / (1 + rs)


def series(pit: PointInTimeStore, ticker: str, days: int = WINDOW) -> list[float]:
    """Closes only, nulls dropped. Vendors ship incomplete bars and a single None
    propagates into every ratio downstream."""
    return [b["close"] for b in pit.prices(ticker, limit=days)
            if b["close"] is not None and b["close"] > 0]


def compute(pit: PointInTimeStore, ticker: str) -> Factors | None:
    closes = series(pit, ticker)
    if len(closes) < 30:
        return None
    last = closes[-1]

    def back(n: int) -> float | None:
        return last / closes[-n - 1] - 1 if len(closes) > n else None

    rets = _returns(closes)
    vol = statistics.pstdev(rets) * math.sqrt(252) if len(rets) > 20 else None

    peak = -math.inf
    mdd = 0.0
    for c in closes:
        peak = max(peak, c)
        mdd = min(mdd, c / peak - 1)

    sma200 = statistics.fmean(closes[-200:]) if len(closes) >= 200 else None

    return Factors(
        ticker=ticker, name=universe.name(ticker), sector=universe.sector(ticker),
        price=round(last, 2),
        ret_1m=back(21), ret_3m=back(63), ret_12m=back(250),
        volatility=round(vol, 4) if vol else None,
        max_drawdown=round(mdd, 4),
        rsi=round(_rsi(closes), 1) if _rsi(closes) else None,
        above_200d=(last > sma200) if sma200 else None,
    )


def compute_all(pit: PointInTimeStore) -> dict[str, Factors]:
    out: dict[str, Factors] = {}
    for ticker in universe.tickers():
        if (f := compute(pit, ticker)):
            out[ticker] = f
    return out


# --------------------------------------------------------------------- correlation
def correlation_matrix(pit: PointInTimeStore, tickers: list[str],
                       days: int = WINDOW) -> dict[str, dict[str, float]]:
    """Pairwise correlation of daily returns, aligned on shared dates.

    Aligning on dates matters: two series with different listing histories would
    otherwise be correlated against mismatched days and produce confident nonsense.
    """
    by_date: dict[str, dict[str, float]] = {}
    for ticker in tickers:
        bars = pit.prices(ticker, limit=days)
        prev = None
        for bar in bars:
            close = bar["close"]
            if close is None or close <= 0:
                continue
            if prev:
                by_date.setdefault(bar["date"], {})[ticker] = close / prev - 1
            prev = close

    matrix: dict[str, dict[str, float]] = {t: {} for t in tickers}
    for i, a in enumerate(tickers):
        for b in tickers[i:]:
            pairs = [(d[a], d[b]) for d in by_date.values() if a in d and b in d]
            if len(pairs) < MIN_OVERLAP:
                continue
            xs = [p for p, _ in pairs]
            ys = [q for _, q in pairs]
            try:
                r = statistics.correlation(xs, ys)
            except (statistics.StatisticsError, ValueError):
                continue
            matrix[a][b] = round(r, 3)
            matrix[b][a] = round(r, 3)
    return matrix


def correlated_pairs(matrix: dict[str, dict[str, float]], weights: dict[str, float],
                     threshold: float = 0.7) -> list[dict[str, Any]]:
    """Holdings that move together, heaviest combined weight first.

    The point is not the number, it is the consequence: two names at 0.9 correlation
    and 12% each are one 24% bet wearing a disguise.
    """
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, Any]] = []
    for a, row in matrix.items():
        for b, r in row.items():
            if a == b or r < threshold:
                continue
            key = tuple(sorted((a, b)))
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "a": a, "b": b, "a_name": universe.name(a), "b_name": universe.name(b),
                "correlation": r,
                "combined_weight": round(weights.get(a, 0) + weights.get(b, 0), 4),
                "same_sector": universe.sector(a) == universe.sector(b),
            })
    out.sort(key=lambda d: -d["combined_weight"])
    return out


def diversification_ratio(matrix: dict[str, dict[str, float]],
                          weights: dict[str, float]) -> float | None:
    """Weighted average pairwise correlation across the book.

    Lower is better. It is the honest counterpart to "how many stocks do you own":
    twenty names all at 0.9 is one position with extra brokerage.
    """
    pairs = []
    names = [t for t in weights if t in matrix]
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            r = matrix.get(a, {}).get(b)
            if r is None:
                continue
            pairs.append((weights[a] * weights[b], r))
    total = sum(w for w, _ in pairs)
    return round(sum(w * r for w, r in pairs) / total, 3) if total else None


# --------------------------------------------------------------------- screening
SCREENS = {
    "diversifiers": "Lowest correlation to what you already own",
    "momentum": "Strongest 3-month trend, still above its 200-day average",
    "quality_value": "Least drawdown for the volatility taken",
    "oversold": "Beaten down but not broken — low RSI, above the 200-day",
}


def screen(pit: PointInTimeStore, kind: str, held: dict[str, float],
           limit: int = 8) -> list[dict[str, Any]]:
    """Rank the universe. Candidates already held are excluded — a screener that
    keeps recommending what you own is not doing the job."""
    facts = compute_all(pit)
    candidates = [f for t, f in facts.items() if t not in held and not t.startswith("^")]

    if kind == "diversifiers" and held:
        universe_tickers = [f.ticker for f in candidates] + list(held)
        matrix = correlation_matrix(pit, universe_tickers)
        scored = []
        for f in candidates:
            rs = [matrix.get(f.ticker, {}).get(h) for h in held]
            rs = [r for r in rs if r is not None]
            if not rs:
                continue
            avg = sum(r * held[h] for r, h in zip(rs, held) if r is not None)
            f.score = round(-avg, 4)          # lower correlation ranks higher
            scored.append((f, {"avg_correlation_to_book": round(avg, 3)}))
        scored.sort(key=lambda kv: -kv[0].score)
        return [{**f.as_dict(), **extra} for f, extra in scored[:limit]]

    if kind == "momentum":
        pool = [f for f in candidates if f.ret_3m is not None and f.above_200d]
        pool.sort(key=lambda f: -(f.ret_3m or 0))
        for f in pool:
            f.score = round(f.ret_3m or 0, 4)
        return [f.as_dict() for f in pool[:limit]]

    if kind == "quality_value":
        pool = [f for f in candidates if f.volatility and f.max_drawdown]
        for f in pool:
            # Shallower drawdown per unit of volatility: fell less than its own
            # jumpiness would predict.
            f.score = round(-(f.max_drawdown or 0) / (f.volatility or 1), 3)
        pool.sort(key=lambda f: f.score)
        return [f.as_dict() for f in pool[:limit]]

    if kind == "oversold":
        pool = [f for f in candidates if f.rsi is not None and f.rsi < 45 and f.above_200d]
        pool.sort(key=lambda f: f.rsi or 100)
        for f in pool:
            f.score = round(100 - (f.rsi or 100), 1)
        return [f.as_dict() for f in pool[:limit]]

    return []
