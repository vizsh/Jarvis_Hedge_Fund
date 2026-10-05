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
    ("RETURN_RATE", "Promises a fixed return every day, week or month",
     r"(\b\d{1,3}(?:\.\d+)?\s?%\s*(?:return|profit|gain|income|growth)?s?\s*(?:per|a|every|each|/)\s*(?:day|week|month)\b|\b(?:daily|weekly|monthly)\s+(?:returns?|profits?|income)\b|\b(?:fixed|regular|steady)\s+(?:monthly|weekly|daily)\s+(?:returns?|income|payout)\b)", 55,
     "Markets do not pay a steady rate every week. A fixed periodic payout is the signature of a Ponzi-style scheme."),
    ("TRACK_RECORD", "Offers a track record as proof",
     r"\b((?:last|previous|past)\s+\d+\s+(?:calls?|tips?|trades?)|(?:all|every)\s+(?:my\s+)?(?:calls?|tips?|trades?)\s+(?:hit|worked|made|were\s+profit\w*)|\d{2,3}\s?%\s*(?:accuracy|success|hit\s*rate|win\s*rate)|screenshots?\s+of\s+(?:profit|returns?)|see\s+my\s+profits?|proof\s+of\s+profit)\b", 20,
     "A track record posted by the seller cannot be checked and is usually cherry-picked; real advisers publish audited, complete records."),
    ("RISK_DENIAL", "Plays down the risk",
     r"\b(low[- ]risk|safe\s+(?:bet|stock|investment|trade)|can'?t\s+(?:go\s+)?wrong|no\s+(?:risk|downside)|limited\s+downside|only\s+upside|cannot\s+fall|can'?t\s+fall)\b", 20,
     "Every share can fall. A message that removes the downside from the picture is selling comfort, not information."),
    ("PAYMENT", "Asks for money, account details or control of your account",
     r"(\b(?:send|transfer|pay|deposit)\b[^.\n]{0,30}(?:₹|rs\.?|rupees|\d{3,})|\b(?:registration|joining|subscription|service|processing)\s*(?:fee|charges?)\b|\bupi\s*id\b|\baccount\s*(?:number|details)\b|\b(?:give|share|send)\s+(?:me\s+)?(?:your\s+)?(?:demat|login|password|otp|pin)\b|\btrade\s+(?:for|on\s+behalf\s+of)\s+you\b|\bmanage\s+(?:your\s+)?(?:account|portfolio|funds?)\b)", 55,
     "A genuine adviser never takes money into a personal account or access to yours. This is how the money disappears."),
    ("SECRECY", "Asks you to keep it quiet or says it is exclusive",
     r"\b(?:don'?t|do\s+not)\s+(?:share|forward|tell)\b|\bonly\s+for\s+(?:selected|few|my|chosen)\b|\bexclusive\s+(?:tip|call|stock|group|access)\b|\bsecret\s+(?:tip|stock|call)\b|\bselected\s+members\b", 15,
     "Secrecy stops you asking anyone who could tell you it is a scam."),
    ("PENNY", "Pushes a penny or tiny stock",
     r"\bpenny\s+stocks?\b|\bunder\s*(?:₹|rs\.?)\s?\d{1,2}\b|\b(?:tiny|small)\s+(?:company|cap)\b[^.\n]{0,25}\b(?:rocket|explode|jackpot|fly)\b", 15,
     "Thinly traded stocks are easy to push up for a few days and hard to sell, which is why pump groups prefer them."),
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


_DIRECTIVE = re.compile(
    r"\b(buy|accumulate|add|enter|invest(?:\s+in)?|go\s+long|book\s+profit|hold|keep|target|tgt|cmp|entry|stop[- ]?loss|sl|"
    r"will\s+(?:go|rise|touch|cross|hit|double|fly|rally|jump|surge)|expected\s+to|set\s+to|poised\s+to|breakout|bullish|rally|"
    r"strong\s+(?:buy|momentum)|worth\s+(?:buying|adding)|good\s+(?:buy|time\s+to\s+buy)|reasonable\s+to\s+(?:buy|hold|add))\b", re.I)
_REASON = re.compile(
    r"\b(because|due\s+to|since|results?|earnings|quarter(?:ly)?|q[1-4]|filing|annual\s+report|order\s+book|valuation|p/?e|debt|margins?|"
    r"dividend|announced|announcement|acquisition|contract|guidance|balance\s+sheet|cash\s*flow|growth|profit|revenue|sales)\b", re.I)
_HORIZON = re.compile(r"\b(?:in|within|by|over|next)\s+(?:the\s+next\s+)?(\d{1,3})\s*(day|days|week|weeks|month|months|year|years)\b|\b(intraday|this\s+week|next\s+week|this\s+month|swing)\b", re.I)
_FUND_CLAIMS = [
    ("DEBT", re.compile(r"\b(debt[- ]?free|zero\s+debt|no\s+debt|low\s+debt|very\s+little\s+debt)\b", re.I)),
    ("VALUE", re.compile(r"\b(undervalued|cheap(?:ly)?\s+valued|trading\s+at\s+a\s+discount|bargain|low\s+valuation)\b", re.I)),
    ("GROWTH", re.compile(r"\b((?:fast|high|strong|rapid|record|explosive)\s+growth|growing\s+fast|growth\s+story)\b", re.I)),
    ("QUALITY", re.compile(r"\b((?:strong|robust|solid|healthy|great|excellent)\s+(?:fundamentals|balance\s+sheet|financials))\b", re.I)),
    ("BREAKOUT", re.compile(r"\b(breakout|new\s+high|52[- ]?week\s+high|all[- ]?time\s+high|at\s+its\s+high)\b", re.I)),
]


def _horizon_days(text: str) -> int | None:
    m = _HORIZON.search(text)
    if not m:
        return None
    if m.group(3):
        w = m.group(3).lower()
        return 1 if w in ("intraday",) else 7 if "week" in w else 30 if "month" in w else 5
    n, unit = int(m.group(1)), m.group(2).lower()
    return n * (1 if unit.startswith("day") else 7 if unit.startswith("week") else 30 if unit.startswith("month") else 365)


def _today(pit: PointInTimeStore) -> PointInTimeStore:
    """Company statistics are stamped when they were fetched, which can be after the simulation clock; the checker reads at the real clock."""
    from datetime import datetime, timezone
    return PointInTimeStore(pit.conn, datetime.now(timezone.utc))


def _val(pit: PointInTimeStore, tk: str, kind: str) -> float | None:
    sg = pit.latest(tk, kind)
    return sg.value_num if sg is not None and sg.value_num is not None else None


def _fund_claim(code: str, tk: str, pit: PointInTimeStore, text: str) -> tuple[str, str | None, str]:
    """(status, evidence, source) for one qualitative claim about a company, tested against the numbers we hold."""
    nm = universe.name(tk)
    if code == "DEBT":
        de = _val(pit, tk, "debt_to_equity")
        if de is None:
            return "UNVERIFIED", f"We hold no debt figure for {nm}.", ""
        ok = de < 30
        return ("SUPPORTED" if ok else "CONTRADICTED"), f"{nm}'s borrowings are about {de:.0f}% of shareholders' capital ({'low' if ok else 'not low, and the tip calls it debt-free or low-debt'}).", "yfinance company statistics"
    if code == "VALUE":
        pe = _val(pit, tk, "pe_ratio")
        peers = [x for x in (_val(pit, o, "pe_ratio") for o in universe.tickers() if o != tk and universe.sector(o) == universe.sector(tk)) if x]
        if not pe or len(peers) < 3:
            return "UNVERIFIED", f"We cannot compare {nm}'s price against profit with its peers.", ""
        med = sorted(peers)[len(peers) // 2]
        ok = pe < med * 0.9
        bad = pe > med * 1.1
        return ("SUPPORTED" if ok else "CONTRADICTED" if bad else "UNVERIFIED"), f"{nm} costs about {pe:.0f} times a year's profit; similar companies cost about {med:.0f}.", "yfinance company statistics, sector peers"
    if code == "GROWTH":
        g = _val(pit, tk, "rev_growth")
        if g is None:
            return "UNVERIFIED", f"We hold no recent sales-growth figure for {nm}.", ""
        return ("SUPPORTED" if g >= 0.12 else "CONTRADICTED" if g <= 0.03 else "UNVERIFIED"), f"{nm}'s sales in the latest quarter moved {g * 100:+.0f}% against a year earlier.", "yfinance company statistics"
    if code == "QUALITY":
        from analysis import proscons
        r = proscons.pros_cons(pit, tk, "en")
        strong = sum(1 for x in r["pros"] if x["confidence"] != "weak")
        weak = sum(1 for x in r["cons"] if x["confidence"] != "weak")
        if not (r["pros"] or r["cons"]):
            return "UNVERIFIED", f"We hold too little on {nm} to judge its fundamentals.", ""
        return ("SUPPORTED" if strong >= weak + 3 else "CONTRADICTED" if weak >= strong else "UNVERIFIED"), f"{nm} shows {strong} good points and {weak} watch-outs in the numbers we hold.", "plain-words research summary"
    if code == "BREAKOUT":
        bars = [b["close"] for b in pit.prices(tk, 250) if b["close"]]
        if len(bars) < 60:
            return "UNVERIFIED", f"Not enough price history on {nm}.", ""
        off = bars[-1] / max(bars) - 1
        return ("SUPPORTED" if off >= -0.03 else "CONTRADICTED"), f"{nm} closed {abs(off) * 100:.0f}% {'below' if off < -0.001 else 'at'} its highest close of the past year.", "price history"
    return "UNVERIFIED", None, ""


def scan(pit: PointInTimeStore, text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {"empty": True}

    flags: list[dict[str, str]] = []
    points = 0
    for code, label, rx, pts, why in FLAGS:
        m = re.search(rx, text, re.I)
        if m:
            flags.append({"code": code, "label": label, "quote": m.group(0).strip(), "why": why, "points": pts})
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

    # ---- what the tip says about a company, tested against the numbers we hold
    now = _today(pit)
    if tickers:
        tk0 = tickers[0]
        for code, rx in _FUND_CLAIMS:
            m = rx.search(text)
            if m:
                status, ev, src = _fund_claim(code, tk0, now, text)
                claims.append({"text": m.group(0).strip(), "status": status, "evidence": ev, "source": src or None})
        facts0 = companies[0]
        if (facts0.get("ret_21") or 0) > 0.20:
            flags.append({"code": "CHASING", "label": "The price has already run up", "quote": f"{facts0['name']} is {facts0['ret_21'] * 100:+.0f}% in a month",
                          "why": "Tips usually arrive after a big move, when the people who bought early want buyers to sell to."})
            points += 10

    # ---- the structure of the message, whatever its tone
    directive = bool(_DIRECTIVE.search(text)) and bool(tickers or unknown)
    horizon = _horizon_days(text)
    checked = [c for c in claims if c["status"] in ("SUPPORTED", "CONTRADICTED") and not c["text"].lower().startswith(("target", "tgt"))]   # a target is an opinion, not a reason
    if directive and not checked:
        flags.append({"code": "NO_BASIS", "label": "A call with nothing checkable behind it",
                      "quote": "(names a stock and a direction, gives no verifiable reason)" if not _REASON.search(text) else "(gives reasons we could not check against any filing)",
                      "why": "A real research note says why: a result, a filing, a valuation. A bare call asks you to trust the sender, and calm wording is not evidence."})
        points += 25 if not _REASON.search(text) else 15
    for c in claims:                                    # a target said to arrive soon is judged on how fast it must move
        if c["text"].lower().startswith(("target", "tgt")) and horizon and companies and companies[0].get("last_close"):
            m = _TARGET.search(text)
            up = (float(m.group(1).replace(",", "")) / companies[0]["last_close"] - 1) * 100 if m else 0
            if (up >= 15 and horizon <= 30) or (up >= 30 and horizon <= 120):
                flags.append({"code": "FAST_TARGET", "label": "Expects a very fast move", "quote": f"{up:+.0f}% in about {horizon} days",
                              "why": "A well-run large company rarely moves this far this fast without news; tips that promise it are usually trying to start the move themselves."})
                points += 20
            break

    contradicted = sum(1 for c in claims if c["status"] == "CONTRADICTED")
    supported = sum(1 for c in claims if c["status"] == "SUPPORTED")
    points += 25 * contradicted + (10 if unknown else 0)
    # a claim that checks out earns a little credit, but never wipes out manipulation tactics
    manip = sum(f["points"] if "points" in f else 0 for f in flags)
    points -= min(15, 8 * supported) if not any(f["code"] in ("GUARANTEE", "PAYMENT", "INSIDER", "RETURN_RATE", "MULTIPLIER") for f in flags) else 0
    points = max(0, min(100, points))

    if points >= 55 or (contradicted and points >= 35):
        verdict, tone = "UNVERIFIED — LIKELY A PUMP OR SCAM", "red"
    elif points >= 25 or contradicted or (directive and not supported):
        verdict, tone = "CAUTION — DO NOT ACT ON THIS ALONE", "amber"
        points = max(points, 25)
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
    if directive and not supported and not any(p.startswith("It uses") for p in parts):
        parts.append("It reads calmly, but it recommends a stock without a reason we can verify, so it is treated as unsupported, not as safe.")
    if not parts:
        parts.append("Nothing in it is alarming, but nothing in it is supported either.")
    parts.append("Check any adviser at sebi.gov.in before paying or acting.")

    return {"verdict": verdict, "tone": tone, "score": points, "flags": flags,
            "claims": claims, "companies": companies, "unknown": unknown,
            "checked": {"claims": len(claims), "tested": len(checked), "directive": directive},
            "summary": " ".join(parts),
            "disclaimer": "A checker, not advice. It tests claims against dated data on file; "
                          "it cannot know what is not on file."}
