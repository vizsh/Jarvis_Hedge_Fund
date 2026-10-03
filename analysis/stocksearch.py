"""Find any listed stock by typing part of its name or symbol.

Two sources, no keys:
  * the NSE equity list (about 2,000 listed companies), downloaded once and cached under data/
  * yfinance's own search, as a fallback for anything not on that list (other exchanges, new listings)

Matching is local and instant: exact symbol, symbol prefix, name prefix, a word of the name, any
substring, then a spelling-tolerant fallback. Each hit says whether the snapshot already holds its
data (`covered`) or it would be fetched on demand (see ingest/ondemand.py).
"""
from __future__ import annotations

import csv
import difflib
import io
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from core import universe

CACHE = Path(__file__).resolve().parent.parent / "data" / "nse_equities.csv"
URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
MAX_AGE_DAYS = 14

_WORDS = re.compile(r"\b(limited|ltd|corporation|corp|company|co|inc|india|industries|the|of)\b\.?", re.I)


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", _WORDS.sub(" ", s.lower().replace("&", " and "))).strip()


def _download() -> str | None:
    try:
        import requests
        r = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        if r.status_code == 200 and "SYMBOL" in r.text[:200]:
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(r.text, encoding="utf-8")
            return r.text
    except Exception:  # noqa: BLE001 - offline is fine: the cache or the local universe still answers
        return None
    return None


@lru_cache(maxsize=1)
def catalogue() -> list[dict[str, Any]]:
    """Every searchable company: the local universe plus the NSE list."""
    text = None
    if CACHE.exists() and (time.time() - CACHE.stat().st_mtime) < MAX_AGE_DAYS * 86400:
        text = CACHE.read_text(encoding="utf-8", errors="ignore")
    text = text or _download() or (CACHE.read_text(encoding="utf-8", errors="ignore") if CACHE.exists() else "")
    out: dict[str, dict[str, Any]] = {}
    for t in universe.tickers():
        out[t] = {"symbol": t, "name": universe.name(t), "exchange": "NSE" if t.endswith(".NS") else "US"}
    for row in csv.DictReader(io.StringIO(text)):
        sym = (row.get("SYMBOL") or "").strip()
        series = (row.get(" SERIES") or row.get("SERIES") or "").strip()
        if not sym or series not in ("EQ", "BE", "SM", "ST"):
            continue
        t = f"{sym}.NS"
        out.setdefault(t, {"symbol": t, "name": (row.get("NAME OF COMPANY") or sym).strip().title(), "exchange": "NSE"})
    for e in universe.extras().values():
        out.setdefault(e["ticker"], {"symbol": e["ticker"], "name": e["name"], "exchange": "NSE"})
    for e in out.values():
        e["key"] = _norm(e["name"])
        e["bare"] = e["symbol"].replace(".NS", "").replace(".BO", "").lower()
    return list(out.values())


def _score(q: str, qn: str, e: dict[str, Any]) -> float:
    bare, key = e["bare"], e["key"]
    if q == bare:
        return 100
    if bare.startswith(q):
        return 90 - min(10, len(bare) - len(q))
    if key.startswith(qn) and qn:
        return 85 - min(10, len(key) - len(qn)) / 2
    if qn and any(w.startswith(qn) for w in key.split()):
        return 75
    if qn and qn in key:
        return 60
    return 0


def search(query: str, limit: int = 8) -> list[dict[str, Any]]:
    q = query.strip().lower()
    if len(q) < 1:
        return []
    qn = _norm(q)
    cat = catalogue()
    scored = [(s, e) for e in cat if (s := _score(q, qn, e)) > 0]
    if len(scored) < limit and len(qn) >= 4:        # spelling tolerance only when little else matched
        keys = {e["key"]: e for e in cat}
        for k in difflib.get_close_matches(qn, list(keys), n=limit, cutoff=0.72):
            scored.append((50, keys[k]))
    scored.sort(key=lambda se: (-se[0], len(se[1]["symbol"])))
    seen, out = set(), []
    covered = _covered()
    for s, e in scored:
        if e["symbol"] in seen:
            continue
        seen.add(e["symbol"])
        out.append({"symbol": e["symbol"], "name": e["name"], "exchange": e["exchange"],
                    "covered": e["symbol"] in covered})
        if len(out) >= limit:
            break
    if len(out) < 3:                                # still thin: ask yfinance (needs network)
        out += _yahoo(query, {o["symbol"] for o in out}, limit - len(out))
    return out


def _covered() -> set[str]:
    return set(universe.tickers()) | set(universe.extras())


def _yahoo(query: str, have: set[str], n: int) -> list[dict[str, Any]]:
    try:
        import yfinance as yf
        hits = yf.Search(query, max_results=n + 3).quotes
    except Exception:  # noqa: BLE001
        return []
    out = []
    for h in hits:
        sym = h.get("symbol")
        if not sym or sym in have or h.get("quoteType") not in (None, "EQUITY"):
            continue
        out.append({"symbol": sym, "name": h.get("shortname") or h.get("longname") or sym,
                    "exchange": h.get("exchDisp") or h.get("exchange") or "", "covered": sym in _covered()})
        if len(out) >= n:
            break
    return out


def best(query: str) -> dict[str, Any] | None:
    """The single most likely company for a name typed or spoken in a sentence."""
    hits = search(query, 3)
    return hits[0] if hits else None
