"""Tip scanner: check a pasted Telegram / WhatsApp / social-media stock tip.

Deterministic on purpose. No language model is asked whether a tip is true -- that is the
failure this product exists to prevent. Instead:

  1. pull out which companies are named and what is being CLAIMED,
  2. look for the language scams are made of (guaranteed returns, urgency, "insider"),
  3. check the claims that CAN be checked against dated data we actually hold,
  4. report what was verified, what contradicts, and what has no support at all.

"No red flags" is never presented as "safe": a tip with no scam language and no support
is still an unsupported tip, and the output says so.
"""
from __future__ import annotations

import re
from typing import Any

from core import universe
from core.pit import PointInTimeStore

# (code, label, regex, points, why it matters)
FLAGS: list[tuple[str, str, str, int, str]] = [
    ("GUARANTEE", "Promises guaranteed returns",
     r"\b(guarantee[d]?|assured|sure[- ]?shot|risk[- ]?free|100\s?%\s*(profit|return|safe)|no\s+loss|zero\s+risk)\b", 35,
     "No one can guarantee a market return. Registered advisers are barred from promising one."),
    ("MULTIPLIER", "Promises a huge multiple",
     r"\b(\d{1,3}\s?x|multi[- ]?bagger|(double|triple)\s+(your\s+)?money|(\d{3,}|\d+\s?k)\s?%\s*(return|profit|gain))\b", 25,
     "Claims of 5x or 10x in weeks are the standard hook of pump-and-dump groups."),
    ("URGENCY", "Pushes you to act now",
     r"\b(buy\s+now|last\s+chance|hurry|today\s+only|before\s+(monday|tomorrow|market\s+opens?)|limited\s+(seats|slots|time)|don'?t\s+miss|act\s+fast)\b", 20,
     "Manufactured urgency is meant to stop you checking anything."),
    ("INSIDER", "Claims inside or operator knowledge",
     r"\b(insider|operator|big\s+players?|bulk\s+deal\s+soon|upper\s+circuit\s+(soon|guaranteed)|news\s+leak|pre[- ]?announcement|jackpot)\b", 30,
     "Trading on inside information is illegal; real insiders do not post it in groups."),
    ("PAYWALL", "Pushes you to a paid or private group",
     r"(\bjoin\s+(my|our)?\s*(vip|premium|paid|private)?\s*(telegram|whatsapp|channel|group)\b|\bdm\s+(me|for)\b|\bpaid\s+(tips|group|calls)\b|t\.me/|wa\.me/)", 25,
     "Tips sold through private groups are the usual route for unregistered advice."),
    ("NO_STOPLOSS", "Tells you to ignore losses",
     r"\b(no\s+stop[- ]?loss|hold\s+till\s+(\d+|target)|never\s+sell)\b", 15,
     "Advice that ignores downside is advice that ignores your capital."),
    ("REGISTRATION", "Claims SEBI registration (verify it)",
     r"\bsebi[- ]?(registered|approved|certified)\b", 10,
     "Check any adviser at sebi.gov.in under Intermediaries before acting. Scam groups often claim it."),
]

_PCT = r"(\d{1,4}(?:\.\d+)?)\s?%"
_GROWTH = re.compile(
    r"\b(profit|net\s+profit|earnings|revenue|sales|income)\b[^.\n]{0,25}?\b(up|rose|grew|jumped|surged|soared|"
    r"increased|down|fell|dropped|declined|slumped)\b[^.\n%]{0,15}?" + _PCT, re.I)
_TARGET = re.compile(r"\b(?:target|tgt)\s*(?:price\s*)?(?:of\s*)?(?:rs\.?|₹|inr)?\s*(\d[\d,]*(?:\.\d+)?)", re.I)
_UP = {"up", "rose", "grew", "jumped", "surged", "soared", "increased"}

KIND_FOR = {"profit": "net_income", "net profit": "net_income", "earnings": "net_income",
            "income": "net_income", "revenue": "revenue", "sales": "revenue"}


def find_companies(text: str) -> list[str]:
    from backend.intents import ALIASES
    low = text.lower()
    found: list[tuple[int, str]] = []
    seen: set[str] = set()

    def add(label: str, ticker: str) -> None:
        if len(label) < 3 or ticker in seen:
            return
        m = re.search(rf"(?<![a-z0-9]){re.escape(label.lower())}(?![a-z0-9])", low)
        if m:
            seen.add(ticker)
            found.append((m.start(), ticker))

    for alias, ticker in sorted(ALIASES.items(), key=lambda kv: -len(kv[0])):
        add(alias, ticker)
    for t in universe.tickers():
        add(universe.name(t), t)
        add(t.replace(".NS", ""), t)
    return [t for _, t in sorted(found)]


def _unknown_symbols(text: str, known: list[str]) -> list[str]:
    skip = {"BUY", "SELL", "NSE", "BSE", "SEBI", "RBI", "IPO", "ETF", "CMP", "TGT", "FNO",
            "THE", "AND", "FOR", "YOU", "ALL", "NOW", "NEW", "TODAY", "VIP", "USD", "INR",
            "STOP", "LOSS", "JOIN", "GUARANTEED", "TARGET", "PROFIT", "TELEGRAM", "WHATSAPP",
            "SURE", "SHOT", "ALSO", "BIG", "HOT", "STOCK", "STOCKS", "TIP", "TIPS", "CALL", "PUMP",
            "ALERT", "URGENT", "FREE", "CHANNEL", "GROUP", "MONDAY", "TOMORROW", "INSIDER", "NEWS",
            "MARKET", "MULTIBAGGER", "LAST", "CHANCE", "HURRY", "PREMIUM", "PRIVATE", "BEFORE",
            "RETURNS", "RETURN", "MONEY", "DOUBLE", "TRIPLE", "SAFE", "RISK", "ZERO", "ONLY", "WITH"}
    names = {t.replace(".NS", "") for t in known}
    every = {t.replace(".NS", "") for t in universe.tickers()}
    out: list[str] = []
    for tok in re.findall(r"\b[A-Z]{3,12}\b", text):
        if tok in skip or tok in names or tok in every or tok in out:
            continue
        out.append(tok)
    return out[:5]


def _latest_two(pit: PointInTimeStore, ticker: str, kind: str):
    sigs = [s for s in pit.signals(ticker=ticker, kind=kind, limit=12) if s.value_num is not None]
    sigs.sort(key=lambda s: str(s.as_of), reverse=True)
    return sigs[:2]


def _market_facts(pit: PointInTimeStore, ticker: str) -> dict[str, Any]:
    bars = [b for b in pit.prices(ticker, limit=70) if b["close"] is not None]
    out: dict[str, Any] = {"ticker": ticker, "name": universe.name(ticker), "evidence": []}
    if not bars:
        out["evidence"].append("No price history held for this name.")
        return out
    last = bars[-1]["close"]
    out["last_close"] = round(last, 2)
    out["as_of"] = bars[-1]["date"]
    for n, label in ((21, "1 month"), (63, "3 months")):
        if len(bars) > n:
            ret = last / bars[-n - 1]["close"] - 1
            out[f"ret_{n}"] = round(ret, 4)
            out["evidence"].append(
                f"Price is {ret * 100:+.1f}% over the last {label} (close {last:,.2f} on {bars[-1]['date']}).")
    return out


def scan(pit: PointInTimeStore, text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {"empty": True}

    flags: list[dict[str, str]] = []
    points = 0
    for code, label, rx, pts, why in FLAGS:
        m = re.search(rx, text, re.I)
        if m:
            flags.append({"code": code, "label": label, "quote": m.group(0).strip(), "why": why})
            points += pts

    tickers = find_companies(text)
    companies = [_market_facts(pit, t) for t in tickers]
    unknown = _unknown_symbols(text, tickers)

    claims: list[dict[str, Any]] = []
    for m in _GROWTH.finditer(text):
        what, verb, pct = m.group(1).lower(), m.group(2).lower(), float(m.group(3))
        said_up = verb in _UP
        kind = KIND_FOR.get(re.sub(r"\s+", " ", what), "net_income")
        claim: dict[str, Any] = {"text": m.group(0).strip(), "status": "UNVERIFIED",
                                 "evidence": None, "source": None}
        if not tickers:
            claim["evidence"] = "No company was named, so there is nothing to check this against."
        else:
            two = _latest_two(pit, tickers[0], kind)
            if len(two) == 2 and two[1].value_num:
                actual = two[0].value_num / two[1].value_num - 1
                sig = two[0]
                claim["source"] = (f"{sig.source_name}, period ending {str(sig.as_of)[:10]}, "
                                   f"published {str(sig.published_at)[:10]}")
                claim["evidence"] = (f"Our data shows {kind.replace('_', ' ')} moved {actual * 100:+.1f}% "
                                     f"from the previous period; the tip says {'+' if said_up else '-'}{pct:.0f}%.")
                if (actual > 0) != said_up:
                    claim["status"] = "CONTRADICTED"
                elif abs(abs(actual) * 100 - pct) <= max(5.0, pct * 0.35):
                    claim["status"] = "SUPPORTED"
                else:
                    claim["status"] = "CONTRADICTED"
            else:
                claim["evidence"] = "No two comparable filings on record, so this number cannot be checked."
        claims.append(claim)

    for m in _TARGET.finditer(text):
        target = float(m.group(1).replace(",", ""))
        c = companies[0] if companies else None
        if c and c.get("last_close"):
            up = (target / c["last_close"] - 1) * 100
            extreme = up > 60
            claims.append({
                "text": m.group(0).strip(), "status": "CONTRADICTED" if extreme else "UNVERIFIED",
                "evidence": (f"That target is {up:+.0f}% from the last close of {c['last_close']:,.2f}. "
                             + ("Calls above +60% in a short window are a classic pump marker." if extreme else
                                "A target is an opinion; no filing can confirm it.")),
                "source": f"Price on {c.get('as_of')}"})
            if extreme:
                points += 20

    contradicted = sum(1 for c in claims if c["status"] == "CONTRADICTED")
    supported = sum(1 for c in claims if c["status"] == "SUPPORTED")
    points += 25 * contradicted + (10 if unknown else 0)
    points = min(100, points)

    if points >= 55 or (contradicted and points >= 35):
        verdict, tone = "UNVERIFIED — LIKELY A PUMP OR SCAM", "red"
    elif points >= 25 or contradicted:
        verdict, tone = "CAUTION — DO NOT ACT ON THIS ALONE", "amber"
    else:
        verdict, tone = "NO RED FLAGS FOUND — STILL NOT ADVICE", "green"

    parts: list[str] = []
    if flags:
        parts.append(f"It uses {len(flags)} scam-style tactic{'s' if len(flags) != 1 else ''}: "
                     + ", ".join(f["label"].lower() for f in flags[:3]) + ".")
    if contradicted:
        parts.append(f"{contradicted} claim{'s' if contradicted != 1 else ''} contradicted by the data we hold.")
    if supported:
        parts.append(f"{supported} claim{'s' if supported != 1 else ''} roughly supported.")
    if unknown:
        parts.append("It names " + ", ".join(unknown) + ", which we have no data on, so nothing about it can be checked.")
    if not parts:
        parts.append("Nothing in it is alarming, but nothing in it is supported either.")
    parts.append("Check any adviser at sebi.gov.in before paying or acting.")

    return {"verdict": verdict, "tone": tone, "score": points, "flags": flags,
            "claims": claims, "companies": companies, "unknown": unknown,
            "summary": " ".join(parts),
            "disclaimer": "A checker, not advice. It tests claims against dated data on file; "
                          "it cannot know what is not on file."}
