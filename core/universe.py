"""The coverage universe: tickers, sectors, display names, benchmark.

Loaded once from config/universe.yaml. Everything that needs to know "what can this
system see" comes through here, so adding a ticker is a config change rather than a
code change.

Display names exist for a usability reason, not a cosmetic one. "HINDUNILVR.NS" is
how the data vendor spells it; "Hindustan Unilever" is how a person spells it, and a
tool that only accepts the vendor's spelling is a tool for people who already know
the vendor's spelling.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

CONFIG = Path(__file__).resolve().parent.parent / "config" / "universe.yaml"

# Human names, so the UI and the explainer can say "Hindustan Unilever" instead of
# "HINDUNILVR.NS". Anything missing falls back to the symbol with the suffix stripped.
NAMES: dict[str, str] = {
    "TCS.NS": "TCS", "INFY.NS": "Infosys", "WIPRO.NS": "Wipro",
    "HCLTECH.NS": "HCL Technologies", "TECHM.NS": "Tech Mahindra",
    "LTTS.NS": "L&T Technology", "TATAELXSI.NS": "Tata Elxsi",
    "MPHASIS.NS": "Mphasis", "PERSISTENT.NS": "Persistent Systems",
    "COFORGE.NS": "Coforge",
    "HDFCBANK.NS": "HDFC Bank", "ICICIBANK.NS": "ICICI Bank",
    "KOTAKBANK.NS": "Kotak Mahindra Bank", "AXISBANK.NS": "Axis Bank",
    "SBIN.NS": "State Bank of India", "BAJFINANCE.NS": "Bajaj Finance",
    "BAJAJFINSV.NS": "Bajaj Finserv", "INDUSINDBK.NS": "IndusInd Bank",
    "SBILIFE.NS": "SBI Life", "HDFCLIFE.NS": "HDFC Life",
    "ITC.NS": "ITC", "HINDUNILVR.NS": "Hindustan Unilever",
    "NESTLEIND.NS": "Nestle India", "BRITANNIA.NS": "Britannia",
    "TATACONSUM.NS": "Tata Consumer",
    "MARUTI.NS": "Maruti Suzuki", "TMPV.NS": "Tata Motors PV",
    "M&M.NS": "Mahindra & Mahindra", "BAJAJ-AUTO.NS": "Bajaj Auto",
    "EICHERMOT.NS": "Eicher Motors", "HEROMOTOCO.NS": "Hero MotoCorp",
    "SUNPHARMA.NS": "Sun Pharma", "DRREDDY.NS": "Dr Reddy's",
    "CIPLA.NS": "Cipla", "DIVISLAB.NS": "Divi's Labs",
    "APOLLOHOSP.NS": "Apollo Hospitals",
    "TATASTEEL.NS": "Tata Steel", "JSWSTEEL.NS": "JSW Steel",
    "HINDALCO.NS": "Hindalco", "ULTRACEMCO.NS": "UltraTech Cement",
    "GRASIM.NS": "Grasim", "ASIANPAINT.NS": "Asian Paints",
    "RELIANCE.NS": "Reliance Industries", "ONGC.NS": "ONGC",
    "BPCL.NS": "Bharat Petroleum", "COALINDIA.NS": "Coal India",
    "NTPC.NS": "NTPC", "POWERGRID.NS": "Power Grid",
    "LT.NS": "Larsen & Toubro", "ADANIENT.NS": "Adani Enterprises",
    "ADANIPORTS.NS": "Adani Ports",
    "BHARTIARTL.NS": "Bharti Airtel", "TITAN.NS": "Titan",
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "Nvidia",
    "^NSEI": "NIFTY 50",
}

# Plain-English sector labels. The codes are what the risk engine uses; these are what
# a person reads.
SECTOR_LABELS: dict[str, str] = {
    "IT": "Technology", "FINANCIALS": "Banks & finance", "FMCG": "Consumer goods",
    "AUTO": "Automobiles", "PHARMA": "Pharma & healthcare", "MATERIALS": "Metals & materials",
    "ENERGY": "Oil & energy", "UTILITIES": "Power & utilities", "INFRA": "Infrastructure",
    "TELECOM": "Telecom", "CONSUMER": "Consumer discretionary", "UNKNOWN": "Unclassified",
}


@lru_cache(maxsize=1)
def _config() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def sectors() -> dict[str, str]:
    cfg = _config()
    out = dict(cfg["india"]["sector_map"])
    out.update(cfg["us"]["sector_map"])
    return out


def tickers() -> list[str]:
    return sorted(sectors())


def benchmark() -> str:
    return (_config().get("benchmark") or {}).get("ticker", "^NSEI")


def benchmark_label() -> str:
    return (_config().get("benchmark") or {}).get("label", "NIFTY 50")


def name(ticker: str) -> str:
    if ticker in NAMES:
        return NAMES[ticker]
    ex = extras().get(ticker) if "_EXTRA" in globals() else None
    return (ex or {}).get("name") or ticker.replace(".NS", "").replace("^", "")


def sector(ticker: str) -> str:
    return sectors().get(ticker, "UNKNOWN")


def sector_label(code: str) -> str:
    return SECTOR_LABELS.get(code, code.title())


def sector_names() -> list[str]:
    return sorted(set(sectors().values()))


def resolve(query: str) -> str | None:
    """Best-effort symbol lookup from whatever a person typed.

    Accepts the exact symbol, the symbol without its suffix, or a company name --
    "hdfc bank", "HDFCBANK", "HDFCBANK.NS" all land on the same place.
    """
    q = query.strip().lower()
    if not q:
        return None
    by_symbol = {t.lower(): t for t in sectors()}
    if q in by_symbol:
        return by_symbol[q]
    bare = {t.replace(".NS", "").lower(): t for t in sectors()}
    if q in bare:
        return bare[q]
    for ticker, label in NAMES.items():
        if label.lower() == q and ticker in sectors():
            return ticker
    # Substring, longest label first so "hdfc bank" beats "hdfc life".
    for ticker, label in sorted(NAMES.items(), key=lambda kv: -len(kv[1])):
        if ticker in sectors() and q in label.lower():
            return ticker
    return None


def catalogue() -> list[dict]:
    """Everything the frontend needs to render a searchable ticker picker."""
    return [{"ticker": t, "name": name(t), "sector": sector(t),
             "sector_label": sector_label(sector(t))}
            for t in tickers()]


# ------------------------------------------------------------------ stocks added on demand
# The base universe (config/universe.yaml) is what the portfolio, risk and screening code is built
# around. A stock the user searches for is stored separately: it can be researched and priced, but it
# does not silently change the sector maps or the screens.
_EXTRA: dict[str, dict] | None = None


def _extra_conn():
    import sqlite3
    from core.db import DB_PATH
    c = sqlite3.connect(DB_PATH)
    c.execute("CREATE TABLE IF NOT EXISTS extra_universe (ticker TEXT PRIMARY KEY, name TEXT, sector TEXT, added_at TEXT)")
    return c


def extras() -> dict[str, dict]:
    global _EXTRA
    if _EXTRA is None:
        try:
            c = _extra_conn()
            _EXTRA = {r[0]: {"ticker": r[0], "name": r[1], "sector": r[2], "added_at": r[3]}
                      for r in c.execute("SELECT ticker, name, sector, added_at FROM extra_universe")}
            c.close()
        except Exception:  # noqa: BLE001 - no database yet (fresh checkout): nothing extra
            _EXTRA = {}
    return _EXTRA


def register_extra(ticker: str, display_name: str, sector_text: str = "UNKNOWN") -> None:
    from datetime import datetime, timezone
    c = _extra_conn()
    c.execute("INSERT OR REPLACE INTO extra_universe VALUES (?,?,?,?)",
              (ticker, display_name, sector_text, datetime.now(timezone.utc).isoformat(timespec="seconds")))
    c.commit()
    c.close()
    extras()[ticker] = {"ticker": ticker, "name": display_name, "sector": sector_text, "added_at": ""}
