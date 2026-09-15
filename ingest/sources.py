"""The six free data sources.

Every adapter returns plain rows plus a SourceResult, and every one declares its
PIT safety tier honestly (see ingest/base.py). None of them raise -- the runner
treats a dead source as a degraded run, not a failed one, because NSE endpoints in
particular go down without warning and the demo cannot depend on them.

    1. yfinance prices        India + US OHLC              PIT exact
    2. yfinance fundamentals  trailing ratios              PIT snapshot-only
    3. yfinance quarterly     reported financials          PIT approximated (+45d)
    4. SEC EDGAR companyfacts US fundamentals              PIT exact (real filing dates)
    5. Google News RSS        per-ticker headlines         PIT exact (pubDate)
    6. GDELT DOC 2.0          global news tone             PIT exact (seendate)
    7. FRED (CSV, no key)     macro rails                  PIT exact/approximated
"""
from __future__ import annotations

import csv
import io
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from core.signal import Latency, Signal, SourceType
from ingest.base import QUARTERLY_FILING_LAG, PitSafety, SourceResult, sid, utcnow

TIMEOUT = 20
# SEC requires a descriptive User-Agent with contact info or it returns 403.
UA = {"User-Agent": "JARVIS-AlphaOS research prototype (student project)"}


def _dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(str(value)).replace(tzinfo=timezone.utc)


# GDELT enforces one request per 5 seconds and answers violations with a 429 whose body
# is plain text, so `resp.json()` raises and the row count silently lands on zero.
# Throttle deliberately rather than discovering this again at 3am.
_GDELT_MIN_GAP = 8.0
_last_gdelt_call = 0.0


def _gdelt_json(url: str, r: SourceResult, attempts: int = 3) -> dict | None:
    global _last_gdelt_call
    for attempt in range(attempts):
        gap = time.monotonic() - _last_gdelt_call
        if gap < _GDELT_MIN_GAP:
            time.sleep(_GDELT_MIN_GAP - gap)
        try:
            resp = requests.get(url, timeout=40)
            _last_gdelt_call = time.monotonic()
            if resp.status_code == 429:
                time.sleep(_GDELT_MIN_GAP * (attempt + 1))
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            _last_gdelt_call = time.monotonic()
            if attempt == attempts - 1:
                r.warn(f"{url[-40:]}: {type(exc).__name__}")
    r.warn(f"{url[-40:]}: exhausted {attempts} attempts (rate limited)")
    return None


# ---------------------------------------------------------------------------------
# 1. yfinance prices -- PIT EXACT (a daily close is knowable at that day's close)
# ---------------------------------------------------------------------------------
def fetch_prices(tickers: list[str], start: str) -> tuple[list[tuple], SourceResult]:
    """`start` is an absolute date, deliberately. A rolling period window silently
    slid past Feb-Mar 2020 and left the Covid rewind with no data behind it."""
    r = SourceResult("yfinance:prices", "price", PitSafety.EXACT,
                     notes=f"daily OHLCV from {start}, NSE + US")
    t0 = utcnow()
    rows: list[tuple] = []
    try:
        import yfinance as yf
        for ticker in tickers:
            try:
                hist = yf.Ticker(ticker).history(start=start, auto_adjust=False)
            except Exception as exc:  # noqa: BLE001
                r.warn(f"{ticker}: {type(exc).__name__}")
                continue
            for idx, row in hist.iterrows():
                close = row["Close"]
                # An in-progress bar for today comes back with a null close. Storing it
                # poisons every downstream return calculation with a None.
                if close is None or str(close) == "nan" or float(close) <= 0:
                    continue
                date = idx.strftime("%Y-%m-%d")
                rows.append((ticker, date, float(row["Open"]), float(row["High"]),
                             float(row["Low"]), float(close),
                             float(row.get("Volume", 0) or 0), date))
        r.online, r.rows = True, len(rows)
    except Exception as exc:  # noqa: BLE001
        r.error = f"{type(exc).__name__}: {exc}"[:120]
    r.latency_ms = int((utcnow() - t0).total_seconds() * 1000)
    return rows, r


# ---------------------------------------------------------------------------------
# 2. yfinance trailing fundamentals -- PIT SNAPSHOT ONLY
#    yfinance returns only TODAY's ratios with no history. Backdating them would be a
#    straight lookahead injection, so they are stamped with the ingest time and
#    correctly vanish the moment you rewind the clock.
# ---------------------------------------------------------------------------------
SNAPSHOT_FIELDS = {
    "trailingPE": "pe_ratio", "priceToBook": "pb_ratio",
    "returnOnEquity": "roe", "profitMargins": "profit_margin",
    "debtToEquity": "debt_to_equity", "marketCap": "market_cap",
}


def fetch_yf_fundamentals(tickers: list[str]) -> tuple[list[Signal], SourceResult]:
    r = SourceResult("yfinance:ratios", "fundamental", PitSafety.SNAPSHOT_ONLY,
                     notes="trailing ratios; no history available, stamped at ingest")
    t0 = utcnow()
    out: list[Signal] = []
    now = utcnow()
    try:
        import yfinance as yf
        for ticker in tickers:
            try:
                info = yf.Ticker(ticker).info or {}
            except Exception as exc:  # noqa: BLE001
                r.warn(f"{ticker}: {type(exc).__name__}")
                continue
            for field, kind in SNAPSHOT_FIELDS.items():
                val = info.get(field)
                if val is None or isinstance(val, str):
                    continue
                out.append(Signal(
                    id=sid("yfratio", ticker, kind, now.date()), ticker=ticker, kind=kind,
                    source_type=SourceType.FUNDAMENTAL, value_num=float(val),
                    as_of=now, published_at=now, source_name="yfinance",
                    source_uri=f"https://finance.yahoo.com/quote/{ticker}",
                    confidence=0.6, latency_class=Latency.REALTIME))
        r.online, r.rows = True, len(out)
    except Exception as exc:  # noqa: BLE001
        r.error = f"{type(exc).__name__}: {exc}"[:120]
    r.latency_ms = int((utcnow() - t0).total_seconds() * 1000)
    return out, r


# ---------------------------------------------------------------------------------
# 3. yfinance quarterly financials -- PIT APPROXIMATED
#    We get the period end but not the filing date, so we add the SEBI LODR statutory
#    lag (45 days). Directionally honest; flagged with reduced confidence.
# ---------------------------------------------------------------------------------
QUARTERLY_ROWS = {
    "Total Revenue": "revenue", "Net Income": "net_income",
    "Operating Income": "operating_income", "Gross Profit": "gross_profit",
}


def fetch_yf_quarterly(tickers: list[str]) -> tuple[list[Signal], SourceResult]:
    r = SourceResult("yfinance:quarterly", "fundamental", PitSafety.APPROXIMATED,
                     notes="period end + 45d SEBI LODR filing lag")
    t0 = utcnow()
    out: list[Signal] = []
    try:
        import yfinance as yf
        for ticker in tickers:
            try:
                fin = yf.Ticker(ticker).quarterly_financials
            except Exception as exc:  # noqa: BLE001
                r.warn(f"{ticker}: {type(exc).__name__}")
                continue
            if fin is None or fin.empty:
                continue
            for label, kind in QUARTERLY_ROWS.items():
                if label not in fin.index:
                    continue
                for period_end, val in fin.loc[label].items():
                    if val is None or str(val) == "nan":
                        continue
                    as_of = _dt(period_end.to_pydatetime())
                    out.append(Signal(
                        id=sid("yfq", ticker, kind, as_of.date()), ticker=ticker,
                        kind=kind, source_type=SourceType.FUNDAMENTAL,
                        value_num=float(val), as_of=as_of,
                        published_at=as_of + QUARTERLY_FILING_LAG,
                        source_name="yfinance", confidence=0.7,
                        source_uri=f"https://finance.yahoo.com/quote/{ticker}/financials",
                        latency_class=Latency.QUARTERLY))
        r.online, r.rows = True, len(out)
    except Exception as exc:  # noqa: BLE001
        r.error = f"{type(exc).__name__}: {exc}"[:120]
    r.latency_ms = int((utcnow() - t0).total_seconds() * 1000)
    return out, r


# ---------------------------------------------------------------------------------
# 4. SEC EDGAR companyfacts -- PIT EXACT, and the only source here that is natively so.
#    Every fact carries `end` (the period) AND `filed` (when it became public). This is
#    the benchmark the approximated Indian fundamentals are measured against.
# ---------------------------------------------------------------------------------
EDGAR_TAGS = {
    "EarningsPerShareDiluted": "eps_diluted",
    "Revenues": "revenue",
    "NetIncomeLoss": "net_income",
    "Assets": "assets",
    "StockholdersEquity": "equity",
}


def fetch_edgar(cik_map: dict[str, str], since: datetime) -> tuple[list[Signal], SourceResult]:
    r = SourceResult("SEC EDGAR", "fundamental", PitSafety.EXACT,
                     notes="companyfacts XBRL; real filing dates")
    t0 = utcnow()
    out: list[Signal] = []
    try:
        for ticker, cik in cik_map.items():
            url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
            try:
                resp = requests.get(url, headers=UA, timeout=TIMEOUT)
                resp.raise_for_status()
                facts = resp.json().get("facts", {}).get("us-gaap", {})
            except Exception as exc:  # noqa: BLE001
                r.warn(f"{ticker}: {type(exc).__name__}")
                continue
            for tag, kind in EDGAR_TAGS.items():
                for unit_rows in facts.get(tag, {}).get("units", {}).values():
                    for f in unit_rows:
                        if "filed" not in f or "end" not in f:
                            continue
                        filed = _dt(f["filed"])
                        if filed < since:
                            continue
                        out.append(Signal(
                            id=sid("edgar", ticker, kind, f["end"], f["filed"]),
                            ticker=ticker, kind=kind,
                            source_type=SourceType.FUNDAMENTAL,
                            value_num=float(f["val"]), as_of=_dt(f["end"]),
                            published_at=filed, source_name="SEC EDGAR",
                            source_uri=f"https://www.sec.gov/cgi-bin/browse-edgar?CIK={cik}",
                            confidence=1.0, latency_class=Latency.QUARTERLY))
        r.online, r.rows = True, len(out)
    except Exception as exc:  # noqa: BLE001
        r.error = f"{type(exc).__name__}: {exc}"[:120]
    r.latency_ms = int((utcnow() - t0).total_seconds() * 1000)
    return out, r


# ---------------------------------------------------------------------------------
# 5. Google News RSS -- PIT EXACT (pubDate), no API key
# ---------------------------------------------------------------------------------
def fetch_google_news(queries: dict[str, str]) -> tuple[list[tuple], SourceResult]:
    r = SourceResult("Google News RSS", "news", PitSafety.EXACT, notes="pubDate")
    t0 = utcnow()
    rows: list[tuple] = []
    try:
        import feedparser
        for ticker, query in queries.items():
            url = ("https://news.google.com/rss/search?q="
                   f"{requests.utils.quote(query)}&hl=en-IN&gl=IN&ceid=IN:en")
            try:
                feed = feedparser.parse(requests.get(url, timeout=TIMEOUT).content)
            except Exception as exc:  # noqa: BLE001
                r.warn(f"{ticker}: {type(exc).__name__}")
                continue
            for e in feed.entries[:40]:
                if not getattr(e, "published_parsed", None):
                    continue
                pub = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
                rows.append((sid("gnews", e.link), ticker, e.title,
                             getattr(e, "summary", "")[:2000], e.link,
                             "GoogleNews", pub.isoformat()))
        r.online, r.rows = True, len(rows)
    except Exception as exc:  # noqa: BLE001
        r.error = f"{type(exc).__name__}: {exc}"[:120]
    r.latency_ms = int((utcnow() - t0).total_seconds() * 1000)
    return rows, r


# ---------------------------------------------------------------------------------
# 6. GDELT DOC 2.0 -- PIT EXACT (seendate). Free, global, machine-coded tone.
#    This is the source that makes "multi-source" more than a claim: it is reading
#    world press tone, not one RSS feed.
# ---------------------------------------------------------------------------------
def fetch_gdelt_tone(queries: dict[str, str], start: datetime | None = None
                     ) -> tuple[list[Signal], SourceResult]:
    """`timespan=12m` only reaches back a year, which left the 2020 rewind with no
    news tone at all. GDELT keeps full archives, so ask for an explicit date range --
    this is the only free source here that can narrate the Covid window."""
    r = SourceResult("GDELT", "tone", PitSafety.EXACT,
                     notes="timelinetone, global press, explicit date range")
    t0 = utcnow()
    out: list[Signal] = []
    start = start or (utcnow() - timedelta(days=2000))
    span = (f"&startdatetime={start.strftime('%Y%m%d')}000000"
            f"&enddatetime={utcnow().strftime('%Y%m%d')}000000")
    try:
        for ticker, query in queries.items():
            url = ("https://api.gdeltproject.org/api/v2/doc/doc?query="
                   f"{requests.utils.quote(query)}&mode=timelinetone"
                   f"{span}&format=json")
            data = _gdelt_json(url, r)
            if data is None:
                continue
            for series in data.get("timeline", []):
                for point in series.get("data", []):
                    when = point.get("date")
                    if not when:
                        continue
                    try:
                        stamp = datetime.strptime(when[:8], "%Y%m%d").replace(
                            tzinfo=timezone.utc)
                    except ValueError:
                        continue
                    out.append(Signal(
                        id=sid("gdelt", ticker, when), ticker=ticker, kind="news_tone",
                        source_type=SourceType.TONE, value_num=float(point["value"]),
                        as_of=stamp, published_at=stamp, source_name="GDELT",
                        source_uri="https://api.gdeltproject.org/api/v2/doc/doc",
                        confidence=0.8, latency_class=Latency.DAILY))
        r.online, r.rows = True, len(out)
    except Exception as exc:  # noqa: BLE001
        r.error = f"{type(exc).__name__}: {exc}"[:120]
    r.latency_ms = int((utcnow() - t0).total_seconds() * 1000)
    return out, r


# ---------------------------------------------------------------------------------
# 7. FRED via the CSV endpoint -- no API key, which keeps us inside the free-only rule.
#    Release lag differs per series: market rates print same-day, CPI lags ~2 weeks.
# ---------------------------------------------------------------------------------
FRED_LAG_DAYS = {"DGS10": 0, "DGS2": 0, "VIXCLS": 0, "CPIAUCSL": 14}


def fetch_fred(series: dict[str, str], since: datetime | None = None
               ) -> tuple[list[Signal], SourceResult]:
    exact = all(FRED_LAG_DAYS.get(s, 0) == 0 for s in series)
    r = SourceResult("FRED", "macro",
                     PitSafety.EXACT if exact else PitSafety.APPROXIMATED,
                     notes="CSV endpoint, no key; per-series release lag applied")
    t0 = utcnow()
    out: list[Signal] = []
    # Unbounded, these series go back to 1962 -- ~16k rows each of history we will
    # never replay. Bound it server-side with cosd.
    cosd = (since or (utcnow() - timedelta(days=1400))).strftime("%Y-%m-%d")
    try:
        for code, label in series.items():
            url = (f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={code}"
                   f"&cosd={cosd}")
            try:
                resp = requests.get(url, timeout=TIMEOUT)
                resp.raise_for_status()
            except Exception as exc:  # noqa: BLE001
                r.warn(f"{code}: {type(exc).__name__}")
                continue
            lag = timedelta(days=FRED_LAG_DAYS.get(code, 0))
            for row in csv.DictReader(io.StringIO(resp.text)):
                # FRED labels this column "observation_date"; older exports used "DATE".
                date_key = next((k for k in row if "date" in k.lower()), None)
                raw = row.get(code) or row.get(code.lower())
                if not date_key or raw in (None, "", "."):
                    continue
                try:
                    as_of = _dt(row[date_key])
                    value = float(raw)
                except ValueError:
                    continue
                out.append(Signal(
                    id=sid("fred", code, row[date_key]), ticker=None, kind=code.lower(),
                    source_type=SourceType.MACRO, value_num=value, as_of=as_of,
                    published_at=as_of + lag, source_name="FRED",
                    source_uri=f"https://fred.stlouisfed.org/series/{code}",
                    confidence=1.0, latency_class=Latency.DAILY))
        r.online, r.rows = True, len(out)
    except Exception as exc:  # noqa: BLE001
        r.error = f"{type(exc).__name__}: {exc}"[:120]
    r.latency_ms = int((utcnow() - t0).total_seconds() * 1000)
    return out, r


# ---------------------------------------------------------------------------------
# 8. NSE corporate announcements -- PIT EXACT when it works, but the endpoint is
#    unofficial and rate-limits aggressively. Optional by design: a dead NSE must
#    never take the demo down with it.
# ---------------------------------------------------------------------------------
def fetch_nse_announcements() -> tuple[list[tuple], SourceResult]:
    r = SourceResult("NSE announcements", "announcement", PitSafety.EXACT,
                     notes="unofficial endpoint; optional")
    t0 = utcnow()
    rows: list[tuple] = []
    try:
        from nsepython import nse_events  # type: ignore
        for item in nse_events() or []:
            when = item.get("date") or item.get("bDate")
            symbol = item.get("symbol")
            if not (when and symbol):
                continue
            try:
                pub = datetime.strptime(when[:10], "%d-%b-%Y").replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            rows.append((sid("nse", symbol, when), f"{symbol}.NS",
                         item.get("purpose", "Corporate event"), str(item)[:1000],
                         "https://www.nseindia.com/companies-listing/corporate-filings",
                         "NSE", pub.isoformat()))
        r.online, r.rows = True, len(rows)
    except Exception as exc:  # noqa: BLE001
        r.error = f"{type(exc).__name__}: {exc}"[:120]
    r.latency_ms = int((utcnow() - t0).total_seconds() * 1000)
    return rows, r
