"""The evidence pack: the only thing a desk is ever allowed to see.

Two jobs, and the second is the important one.

1.  Assemble what is knowable about a ticker AT THE SIM CLOCK -- prices, deterministic
    indicators, fundamentals, macro rails, press tone, headlines. Everything comes
    through `PointInTimeStore`, so the pack physically cannot contain the future.

2.  Give every item a stable id (E1, E2, ...) that the model must cite. This is what
    makes the citation gate enforceable: a claim citing E9 when the pack stops at E7
    is a fabricated citation, and fabricated citations are the failure mode that
    matters most in finance. Without ids there is nothing to check against.

Indicators are computed here in plain Python rather than asked of the model, because
arithmetic is not something an 8B model should be trusted with and because a computed
number carries a real citation to the price rows it came from.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any

from core.pit import PointInTimeStore


@dataclass
class EvidenceItem:
    id: str
    text: str
    source_name: str
    published_at: str
    confidence: float = 1.0
    source_uri: str | None = None
    kind: str = "fact"

    def as_line(self) -> str:
        return f"{self.id}: {self.text}  [{self.source_name}, {self.published_at[:10]}]"


@dataclass
class EvidencePack:
    ticker: str
    sim_clock: str
    items: list[EvidenceItem] = field(default_factory=list)

    def add(self, text: str, source: str, published_at: str, confidence: float = 1.0,
            uri: str | None = None, kind: str = "fact") -> EvidenceItem:
        item = EvidenceItem(f"E{len(self.items) + 1}", text, source, published_at,
                            confidence, uri, kind)
        self.items.append(item)
        return item

    @property
    def ids(self) -> set[str]:
        return {i.id for i in self.items}

    def by_id(self, eid: str) -> EvidenceItem | None:
        return next((i for i in self.items if i.id == eid), None)

    def render(self, kinds: set[str] | None = None) -> str:
        rows = [i for i in self.items if kinds is None or i.kind in kinds]
        return "\n".join(i.as_line() for i in rows) or "(no evidence available)"

    def mean_confidence(self, ids: list[str]) -> float:
        vals = [i.confidence for i in (self.by_id(e) for e in ids) if i]
        return sum(vals) / len(vals) if vals else 0.0


def _rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for a, b in zip(closes[-period - 1:-1], closes[-period:]):
        change = b - a
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain, avg_loss = sum(gains) / period, sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _pct(new: float, old: float) -> float:
    return (new / old - 1) * 100 if old else 0.0


def build_pack(pit: PointInTimeStore, ticker: str, max_headlines: int = 3) -> EvidencePack:
    pack = EvidencePack(ticker=ticker, sim_clock=pit.clock_iso)
    clock = pit.clock_iso

    # --- price + deterministic indicators (kind: quant) --------------------------
    bars = pit.prices(ticker, limit=260)
    closes = [b["close"] for b in bars]
    if closes:
        last = closes[-1]
        uri = f"https://finance.yahoo.com/quote/{ticker}"
        pack.add(f"{ticker} last close {last:,.2f} on {bars[-1]['date']}",
                 "yfinance", bars[-1]["date"], 1.0, uri, "quant")
        for window, label in ((5, "1w"), (21, "1m"), (63, "3m")):
            if len(closes) > window:
                pack.add(f"{label} return {_pct(last, closes[-window - 1]):+.1f}%",
                         "yfinance (computed)", bars[-1]["date"], 1.0, uri, "quant")
        if len(closes) >= 50:
            sma50 = statistics.fmean(closes[-50:])
            pack.add(f"50-day SMA {sma50:,.2f}; price is "
                     f"{'above' if last > sma50 else 'below'} it by "
                     f"{abs(_pct(last, sma50)):.1f}%",
                     "yfinance (computed)", bars[-1]["date"], 1.0, uri, "quant")
        if (rsi := _rsi(closes)) is not None:
            pack.add(f"RSI(14) {rsi:.0f}", "yfinance (computed)", bars[-1]["date"],
                     1.0, uri, "quant")
        if len(closes) >= 21:
            rets = [_pct(b, a) for a, b in zip(closes[-22:-1], closes[-21:])]
            pack.add(f"21-day realised volatility {statistics.pstdev(rets):.2f}% daily",
                     "yfinance (computed)", bars[-1]["date"], 1.0, uri, "quant")

    # --- fundamentals (kind: fundamental) ----------------------------------------
    seen: set[str] = set()
    for sig in pit.signals(ticker=ticker, limit=400):
        if sig.source_type.value != "fundamental" or sig.kind in seen:
            continue
        seen.add(sig.kind)
        value = (f"{sig.value_num:,.2f}" if abs(sig.value_num or 0) < 1e6
                 else f"{sig.value_num:,.0f}")
        pack.add(f"{sig.kind.replace('_', ' ')} = {value} (period ending "
                 f"{sig.as_of.date()})", sig.source_name, sig.published_at.isoformat(),
                 sig.confidence, sig.source_uri, "fundamental")

    # --- press tone (kind: narrative) --------------------------------------------
    tones = pit.signals(ticker=ticker, kind="news_tone", limit=30)
    if tones:
        latest = tones[0]
        pack.add(f"GDELT global press tone {latest.value_num:+.2f} "
                 f"(negative = adverse coverage)", "GDELT",
                 latest.published_at.isoformat(), latest.confidence,
                 latest.source_uri, "narrative")
        if len(tones) > 5:
            avg = statistics.fmean(t.value_num for t in tones if t.value_num is not None)
            pack.add(f"30-day mean press tone {avg:+.2f}", "GDELT (computed)",
                     latest.published_at.isoformat(), 0.8, latest.source_uri, "narrative")

    for doc in pit.news(ticker, limit=max_headlines):
        pack.add(f"Headline: {doc['title']}", doc["source_name"], doc["published_at"],
                 0.7, doc["url"], "narrative")

    # --- macro rails (kind: macro), shared across tickers -------------------------
    for kind, label in (("dgs10", "US 10Y yield"), ("vixcls", "VIX"),
                        ("cpiaucsl", "US CPI index")):
        rows = pit.signals(kind=kind, limit=1)
        if rows:
            pack.add(f"{label} {rows[0].value_num:,.2f}", "FRED",
                     rows[0].published_at.isoformat(), rows[0].confidence,
                     rows[0].source_uri, "macro")

    if not pack.items:
        pack.add(f"No evidence is visible for {ticker} at {clock[:10]}.",
                 "PointInTimeStore", clock, 1.0, None, "fact")
    return pack
