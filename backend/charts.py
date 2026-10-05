"""Price-history series for the chat charts: fetched live from Yahoo Finance when the machine is online,
otherwise read from the saved snapshot (and labelled as such, with its date).

A chart is a picture of numbers that exist elsewhere, so it never invents any: every point is a close from one of
those two sources, and the answer says which one it was and how old the last point is.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutTimeout
from datetime import date, datetime
from typing import Any

from core import universe

_TTL = 600.0
_CACHE: dict[tuple[str, str], tuple[float, list[tuple[str, float]] | None]] = {}
_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="chart")

_US = {"AAPL": "NASDAQ", "MSFT": "NASDAQ", "NVDA": "NASDAQ", "GOOGL": "NASDAQ", "AMZN": "NASDAQ", "META": "NASDAQ", "TSLA": "NASDAQ"}


def tv_symbol(ticker: str) -> str:
    """The TradingView symbol for the optional embedded live chart."""
    t = ticker.upper()
    if t.endswith(".NS"):
        return "NSE:" + t[:-3].replace("&", "_").replace("-", "_")
    if t.endswith(".BO"):
        return "BSE:" + t[:-3]
    return f"{_US.get(t, 'NASDAQ')}:{t}"


def currency(ticker: str) -> str:
    return "₹" if ticker.upper().endswith((".NS", ".BO")) else "$"


def _live(ticker: str, period: str) -> list[tuple[str, float]] | None:
    try:
        import yfinance as yf
        h = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=False)
        if h is None or h.empty:
            return None
        out = [(i.strftime("%Y-%m-%d"), float(c)) for i, c in zip(h.index, h["Close"]) if c == c]
        return out if len(out) >= 20 else None
    except Exception:  # noqa: BLE001
        return None


def live_series(ticker: str, period: str = "1y", wait: float = 6.0) -> list[tuple[str, float]] | None:
    """Closes from the internet, cached for ten minutes (a failure is cached too, so an offline machine does not
    wait on every question)."""
    key = (ticker, period)
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < _TTL:
        return hit[1]
    fut = _POOL.submit(_live, ticker, period)
    try:
        res = fut.result(timeout=wait)
    except (FutTimeout, Exception):  # noqa: BLE001
        res = None
    _CACHE[key] = (time.time(), res)
    return res


def snapshot_series(pit, ticker: str, limit: int = 250) -> list[tuple[str, float]]:
    return [(r["date"], float(r["close"])) for r in pit.prices(ticker, limit) if r.get("close")]


def _sma(vals: list[float], n: int) -> list[float | None]:
    out: list[float | None] = []
    run = 0.0
    for i, v in enumerate(vals):
        run += v
        if i >= n:
            run -= vals[i - n]
        out.append(round(run / n, 2) if i >= n - 1 else None)
    return out


def _age(last: str) -> int | None:
    try:
        return (date.today() - datetime.fromisoformat(last[:10]).date()).days
    except ValueError:
        return None


def price_chart(pit, ticker: str, live: bool = True) -> dict[str, Any] | None:
    """One company's year of closes with its 50- and 200-day averages, the source, and how old the last close is."""
    ser = live_series(ticker) if live else None
    source = "live"
    if not ser:
        ser, source = snapshot_series(pit, ticker), "snapshot"
    if len(ser) < 20:
        return None
    closes = [c for _, c in ser]
    ma50, ma200 = _sma(closes, 50), _sma(closes, 200)
    hi, lo = max(closes), min(closes)
    return {"kind": "price", "ticker": ticker, "name": universe.name(ticker), "currency": currency(ticker), "source": source,
            "last_date": ser[-1][0], "age_days": _age(ser[-1][0]), "tv": tv_symbol(ticker),
            "points": [[d, round(c, 2)] for d, c in ser], "ma50": ma50, "ma200": ma200,
            "last": round(closes[-1], 2), "first": round(closes[0], 2), "high": round(hi, 2), "low": round(lo, 2),
            "change_pct": round((closes[-1] / closes[0] - 1) * 100, 1)}


def compare_chart(pit, tickers: list[str], live: bool = True) -> dict[str, Any] | None:
    """Several companies over the same dates, each rebased to 100 at the start so growth can be compared."""
    sers = []
    source = "live"
    for tk in tickers:
        s = live_series(tk) if live else None
        if not s:
            s, source = snapshot_series(pit, tk), "snapshot"
        if len(s) >= 20:
            sers.append((tk, s))
    if len(sers) < 2:
        return None
    # one shared start date: the latest first-date among them, so every line starts at 100 together
    start = max(s[0][0] for _, s in sers)
    series = []
    for tk, s in sers:
        s = [(d, c) for d, c in s if d >= start]
        if len(s) < 10:
            return None
        base = s[0][1]
        series.append({"ticker": tk, "name": universe.name(tk), "points": [[d, round(c / base * 100, 2)] for d, c in s],
                       "change_pct": round((s[-1][1] / base - 1) * 100, 1)})
    return {"kind": "compare", "source": source, "start": start, "last_date": max(s["points"][-1][0] for s in series),
            "series": series, "tv": [tv_symbol(tk) for tk, _ in sers]}
