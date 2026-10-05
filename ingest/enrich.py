"""Richer company data from yfinance, beyond the five ratios the snapshot started with.

What it adds (all stamped at ingest time; yfinance gives no history for these, so they are SNAPSHOT values and the
research summary says how old they are):
  growth      revenue growth, earnings growth, 3-year revenue CAGR
  quality     cash conversion (operating cash flow / net income), free cash flow, Piotroski F-score, Altman Z-score
  safety      debt to equity, interest cover, current ratio
  income      dividend yield and payout
  ownership   insider/promoter share and institutional share (snapshots accumulate, so a trend appears with time)
  valuation   the company's own past P/E range (fiscal-year-end prices over annual EPS)
Banks and other financial companies are not scored on debt, liquidity or Altman Z: those measures mean something
different (or nothing) for a lender, and a made-up verdict is worse than none.
"""
from __future__ import annotations

import math
import statistics
from datetime import datetime, timezone

from core import universe
from core.signal import Latency, Signal, SourceType
from ingest.base import sid

FIN_SECTORS = {"FINANCIALS"}


def _f(x) -> float | None:
    try:
        v = float(x)
        return None if math.isnan(v) or math.isinf(v) else v
    except (TypeError, ValueError):
        return None


def _row(df, *names):
    """First matching row of a statement as {period: value}, newest first."""
    if df is None or getattr(df, "empty", True):
        return {}
    for n in names:
        if n in df.index:
            s = df.loc[n]
            return {c: _f(v) for c, v in s.items() if _f(v) is not None}
    return {}


def piotroski(fin, bal, cf) -> tuple[int, int] | None:
    """(points, tests that could be run). Needs two years of statements; a missing line skips that test."""
    ni = _row(fin, "Net Income", "Net Income Common Stockholders")
    ta = _row(bal, "Total Assets")
    ocf = _row(cf, "Operating Cash Flow", "Cash Flow From Continuing Operating Activities")
    rev = _row(fin, "Total Revenue")
    gp = _row(fin, "Gross Profit")
    ltd = _row(bal, "Long Term Debt")
    ca, cl = _row(bal, "Current Assets"), _row(bal, "Current Liabilities")
    sh = _row(bal, "Ordinary Shares Number", "Share Issued")
    pts = n = 0

    def test(cond):
        nonlocal pts, n
        if cond is not None:
            n += 1
            pts += 1 if cond else 0

    ks = sorted(set(ni) & set(ta), reverse=True)
    if len(ks) < 2:
        return None
    c, p = ks[0], ks[1]
    roa_c, roa_p = ni[c] / ta[c], ni[p] / ta[p]
    test(roa_c > 0)
    test(ocf.get(c) > 0 if c in ocf else None)
    test(roa_c > roa_p)
    test(ocf[c] > ni[c] if c in ocf else None)
    if c in ltd and p in ltd:
        test(ltd[c] / ta[c] < ltd[p] / ta[p] or ltd[c] == 0)
    if all(k in d for d in (ca, cl) for k in (c, p)) and cl[c] and cl[p]:
        test(ca[c] / cl[c] > ca[p] / cl[p])
    if c in sh and p in sh:
        test(sh[c] <= sh[p] * 1.005)
    if c in gp and p in gp and c in rev and p in rev and rev[c] and rev[p]:
        test(gp[c] / rev[c] > gp[p] / rev[p])
    if c in rev and p in rev and ta.get(p):
        test(rev[c] / ta[c] > rev[p] / ta[p])
    return (pts, n) if n >= 5 else None


def altman_z(fin, bal, mcap: float | None) -> float | None:
    ta, ca, cl = _row(bal, "Total Assets"), _row(bal, "Current Assets"), _row(bal, "Current Liabilities")
    re_, tl = _row(bal, "Retained Earnings"), _row(bal, "Total Liabilities Net Minority Interest", "Total Liabilities")
    ebit, rev = _row(fin, "EBIT", "Operating Income"), _row(fin, "Total Revenue")
    ks = sorted(set(ta) & set(ca) & set(cl) & set(re_) & set(tl) & set(ebit) & set(rev), reverse=True)
    if not ks or not mcap or not tl[ks[0]]:
        return None
    k = ks[0]
    return round(1.2 * (ca[k] - cl[k]) / ta[k] + 1.4 * re_[k] / ta[k] + 3.3 * ebit[k] / ta[k] + 0.6 * mcap / tl[k] + 1.0 * rev[k] / ta[k], 2)


def pe_history(t, fin) -> list[float]:
    """P/E at each fiscal-year end: that month's close over that year's diluted EPS. A short, honest list (about 4)."""
    eps = _row(fin, "Diluted EPS", "Basic EPS")
    if not eps:
        return []
    try:
        h = t.history(period="6y", interval="1mo")["Close"]
    except Exception:  # noqa: BLE001
        return []
    out = []
    for end, e in eps.items():
        if e and e > 0:
            try:
                px = h[h.index <= end.tz_localize(h.index.tz) if getattr(end, "tzinfo", None) is None and h.index.tz is not None else h.index <= end]
                if len(px):
                    out.append(float(px.iloc[-1]) / e)
            except Exception:  # noqa: BLE001
                continue
    return [x for x in out if 0 < x < 500]


def fetch_enriched(ticker: str) -> list[Signal]:
    import yfinance as yf
    now = datetime.now(timezone.utc)
    t = yf.Ticker(ticker)
    info = t.info or {}
    out: list[Signal] = []
    sector = universe.sector(ticker)
    is_fin = sector in FIN_SECTORS

    def put(kind: str, val, text: str | None = None, conf: float = 0.6):
        v = _f(val)
        if v is None:
            return
        out.append(Signal(id=sid("enrich", ticker, kind, now.date()), ticker=ticker, kind=kind, source_type=SourceType.FUNDAMENTAL,
                          value_num=v, value_text=text, as_of=now, published_at=now, source_name="yfinance",
                          source_uri=f"https://finance.yahoo.com/quote/{ticker}", confidence=conf, latency_class=Latency.REALTIME))

    for field, kind in {"revenueGrowth": "rev_growth", "earningsGrowth": "earn_growth", "currentRatio": "current_ratio", "debtToEquity": "debt_to_equity",
                        "operatingMargins": "op_margin", "grossMargins": "gross_margin", "returnOnAssets": "roa", "payoutRatio": "payout",
                        "heldPercentInsiders": "holding_insiders", "heldPercentInstitutions": "holding_institutions", "beta": "beta",
                        "freeCashflow": "fcf", "operatingCashflow": "ocf", "totalDebt": "total_debt", "totalCash": "total_cash"}.items():
        put(kind, info.get(field))
    px = _f(info.get("currentPrice") or info.get("regularMarketPrice"))
    dr = _f(info.get("dividendRate"))
    if px and dr is not None:
        put("div_yield", dr / px)

    fin, bal, cf = t.financials, t.balance_sheet, t.cashflow
    rev = _row(fin, "Total Revenue")
    ks = sorted(rev, reverse=True)
    if len(ks) >= 4 and rev[ks[3]] > 0 and rev[ks[0]] > 0:
        put("rev_cagr_3y", (rev[ks[0]] / rev[ks[3]]) ** (1 / 3) - 1, "3 fiscal years")
    ni, ocf = _row(fin, "Net Income", "Net Income Common Stockholders"), _row(cf, "Operating Cash Flow", "Cash Flow From Continuing Operating Activities")
    k = sorted(set(ni) & set(ocf), reverse=True)
    if k and ni[k[0]] > 0 and not is_fin:
        put("ocf_to_ni", ocf[k[0]] / ni[k[0]], f"fiscal year ending {k[0].date()}")
    if not is_fin:
        ebit, intr = _row(fin, "EBIT", "Operating Income"), _row(fin, "Interest Expense", "Interest Expense Non Operating")
        k = sorted(set(ebit) & set(intr), reverse=True)
        if k and intr[k[0]]:
            put("interest_cover", ebit[k[0]] / abs(intr[k[0]]), f"fiscal year ending {k[0].date()}")
        z = altman_z(fin, bal, _f(info.get("marketCap")))
        if z is not None:
            put("altman_z", z, "non-financial company")
        pf = piotroski(fin, bal, cf)
        if pf:
            put("piotroski_f", pf[0], f"{pf[0]} of {pf[1]} tests passed")
    pe = pe_history(t, fin)
    if len(pe) >= 3:
        put("pe_hist_median", statistics.median(pe), f"{len(pe)} fiscal year-ends")
        put("pe_hist_low", min(pe), f"{len(pe)} fiscal year-ends")
        put("pe_hist_high", max(pe), f"{len(pe)} fiscal year-ends")
    return out
