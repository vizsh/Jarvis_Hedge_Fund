"""Tip analysis by a panel of specialists, not by keywords.

A tip is first UNDERSTOOD: what is it actually suggesting (which stock, which direction, what price, by when, on what
reasoning, and what is the reader being asked to do)? A local model helps read free-form wording into a fixed form, and
every number it returns must appear in the text or it is thrown away; a rules reader does the same job when the model is
not available. Then separate analysts examine the claim from different angles:

  Feasibility     is the promised move even possible? A price model (first-passage probability from the stock's own
                  volatility) and no-free-lunch limits on "guaranteed" or periodic returns.
  Fundamentals    does the company's own business support the thesis, and what would the target require the market to pay?
  Technicals      what is the chart doing, and how far is the target from where the stock has ever traded this year?
  Market          can this stock be pushed around (liquidity, size), or does it even exist on the exchange list?
  Source          what is the reader asked to do, and who gains if they do it?
  Rules           what would SEBI's rules say about an adviser who said this?
  Wording         the old text-pattern checks, kept as ONE low-weight witness among the others.
  Consequence     what could this cost, in rupees, in the realistic and the bad case?

The synthesis weighs them into two separate answers: how likely the message is a scam, and how much real backing the idea
has. It ends with what to DO: ignore and report, ignore, verify first, or research it properly. Numbers come from code
and stored data; the model only reads, it never judges or invents.
"""
from __future__ import annotations

import math
import re
import statistics
from datetime import datetime, timezone
from typing import Any

from analysis import scanner
from core import universe
from core.pit import PointInTimeStore

RISK_FREE = 0.07        # roughly what a bank deposit or government bond pays; stated in the output as "about 7%"
EQUITY_LONG_RUN = 0.12  # rough long-run nominal equity return, used only for scale
ELITE_SUSTAINED = 0.25  # about the best sustained record any professional investor claims

_NUM = r"(\d[\d,]*(?:\.\d+)?)"


# =============================================================================================== 1. understanding
_ASKS = {
    "pay": re.compile(r"\b(?:send|transfer|pay|deposit|invest\s+with\s+us|start\s+with)\b[^.\n]{0,30}(?:₹|rs\.?|rupees|\d{3,})|\b(?:registration|joining|subscription|service|processing)\s*(?:fee|charges?)\b|\bupi\s*id\b|\baccount\s*(?:number|details)\b", re.I),
    "credentials": re.compile(r"\b(?:give|share|send|tell)\s+(?:me\s+)?(?:your\s+)?(?:demat|trading)?\s*(?:login|password|otp|pin|credentials)\b|\btrade\s+(?:for|on\s+behalf\s+of)\s+you\b|\bmanage\s+(?:your\s+)?(?:account|portfolio|funds?)\b|\bpower\s+of\s+attorney\b", re.I),
    "join": re.compile(r"\bjoin\s+(?:my|our|the)?\s*(?:vip|premium|paid|private)?\s*(?:telegram|whatsapp|channel|group)\b|\bt\.me/|\bwa\.me/|\bdm\s+(?:me|for)\b|\bpaid\s+(?:tips|group|calls)\b", re.I),
    "refer": re.compile(r"\brefer\b[^.\n]{0,20}\b(?:friends?|others|members)\b|\bbring\s+(?:your\s+)?(?:friends|members)\b", re.I),
    "forward": re.compile(r"\b(?:forward|share)\s+(?:this|it)\s+(?:to|with)\b", re.I),
    "buy": re.compile(r"\b(?:buy|accumulate|add|enter|go\s+long|invest\s+in|take\s+(?:a\s+)?position)\b", re.I),
    "sell": re.compile(r"\b(?:sell|exit|book\s+profits?|short)\b", re.I),
}
_THESIS = {
    "results": re.compile(r"\b(results?|earnings|net\s+profit|profit|revenue|sales|quarter(?:ly)?|q[1-4]|margins?)\b", re.I),
    "valuation": re.compile(r"\b(undervalued|cheap|valuation|discount|p/?e|price\s+to\s+earnings|bargain)\b", re.I),
    "news": re.compile(r"\b(order\s*(?:book|win)|contract|merger|acquisition|approval|launch|deal|partnership|announcement|buyback|dividend|bonus|split)\b", re.I),
    "technical": re.compile(r"\b(breakout|support|resistance|chart|pattern|rsi|moving\s+average|momentum|volume\s+spike|trend)\b", re.I),
    "insider": re.compile(r"\b(insider|operator|big\s+players?|bulk\s+deal|news\s+leak|pre[- ]?announcement|my\s+sources|source\s+in|(?:friend|relative|contact|person|cousin|colleague)\s+(?:at|in|from|inside)\s+\w+|told\s+me|heard\s+from|not\s+yet\s+public)\b", re.I),
    "hype": re.compile(r"\b(rocket|moon|explode|jackpot|next\s+multibagger|will\s+fly|ready\s+to\s+fly|game\s*changer|once\s+in\s+a\s+lifetime)\b", re.I),
}
_EVIDENCE = re.compile(r"\b(annual\s+report|exchange\s+filing|bse|nse\s+(?:announcement|filing)|screener|sebi\s+filing|investor\s+presentation|concall|earnings\s+call|prospectus)\b", re.I)
_CERTAIN = re.compile(r"\b(surely|definitely|for\s+sure|certainly|without\s+(?:a\s+)?doubt|no\s+doubt|bound\s+to)\b", re.I)
_ANCHOR = {"pay": re.compile(r"\b(money|rs\.?|₹|rupees|fee|pay|send|transfer|deposit|subscription|invest\s+with)\b", re.I),
           "credentials": re.compile(r"\b(login|password|otp|pin|account|demat|access|control|behalf|credentials)\b", re.I)}
_LEVERAGE = re.compile(r"\b(futures?|options?|f&o|fno|calls?\s+and\s+puts?|leverage[d]?|margin|2x|3x|5x\s+leverage|intraday)\b", re.I)
_PERIODIC = re.compile(r"(\d{1,3}(?:\.\d+)?)\s?%\s*(?:return|profit|gain|income|growth)?s?\s*(?:per|a|every|each|/)\s*(day|week|month)\b", re.I)
_MOVE = re.compile(r"(\d{1,4}(?:\.\d+)?)\s?%\s*(?:upside|return|gain|rally|rise|jump|profit|move|surge)", re.I)
_REACH = re.compile(r"\b(?:to|reach|touch|cross|hit|till|upto|up\s+to|towards)\s*(?:rs\.?|₹|inr)?\s*" + _NUM, re.I)


def _f(x: str) -> float:
    return float(x.replace(",", ""))


def comprehend_rules(text: str, tickers: list[str], last_close: float | None) -> dict[str, Any]:
    """The tip read into a fixed form by patterns. Always available; the model refines it when it can."""
    spec: dict[str, Any] = {"instruments": [universe.name(t) for t in tickers], "action": "none", "target_price": None, "expected_return_pct": None,
                            "horizon_days": scanner._horizon_days(text), "periodic_return_pct": None, "periodic_unit": None, "guarantee": False,
                            "uses_leverage": bool(_LEVERAGE.search(text)), "thesis": [k for k, rx in _THESIS.items() if rx.search(text)],
                            "evidence_offered": [m.group(0) for m in _EVIDENCE.finditer(text)][:3],
                            "asks": [k for k in ("pay", "credentials", "join", "refer", "forward") if _ASKS[k].search(text)], "summary": ""}
    if scanner.re.search(scanner.FLAGS[0][2], text, re.I):
        spec["guarantee"] = True
    if _ASKS["buy"].search(text):
        spec["action"] = "buy"
    elif _ASKS["sell"].search(text):
        spec["action"] = "sell"
    m = _PERIODIC.search(text)
    if m:
        spec["periodic_return_pct"], spec["periodic_unit"] = float(m.group(1)), m.group(2).lower()
    t = scanner._TARGET.search(text)
    if t:
        spec["target_price"] = _f(t.group(1))
    elif last_close:
        for r in _REACH.finditer(text):
            v = _f(r.group(1))
            if 0.5 * last_close <= v <= 12 * last_close:
                spec["target_price"] = v
                break
    mv = _MOVE.search(text)
    if mv and not m:
        spec["expected_return_pct"] = float(mv.group(1))
    return spec


_SCHEMA = {"type": "object", "properties": {
    "instruments": {"type": "array", "items": {"type": "string"}},
    "action": {"type": "string", "enum": ["buy", "sell", "hold", "avoid", "none"]},
    "target_price": {"type": ["number", "null"]}, "expected_return_pct": {"type": ["number", "null"]}, "horizon_days": {"type": ["number", "null"]},
    "periodic_return_pct": {"type": ["number", "null"]}, "periodic_unit": {"type": "string", "enum": ["day", "week", "month", "year", "none"]},
    "guarantee": {"type": "boolean"}, "uses_leverage": {"type": "boolean"},
    "thesis": {"type": "array", "items": {"type": "string", "enum": ["results", "valuation", "news", "technical", "insider", "hype", "none"]}},
    "evidence_offered": {"type": "array", "items": {"type": "string"}},
    "asks": {"type": "array", "items": {"type": "string", "enum": ["pay", "credentials", "join", "refer", "forward", "buy", "sell", "none"]}},
    "summary": {"type": "string"}},
    "required": ["action", "thesis", "asks", "summary"]}


def _in_text(v: Any, text: str) -> bool:
    """A number the model returns must be one the tip actually states (so it cannot invent a target)."""
    if v is None:
        return True
    plain = text.replace(",", "")
    cands = {str(int(v)) if float(v).is_integer() else str(v), f"{v:g}"}
    return any(re.search(rf"(?<![\d.]){re.escape(c)}(?![\d])", plain) for c in cands)


async def comprehend(text: str, tickers: list[str], last_close: float | None) -> tuple[dict[str, Any], str]:
    """(form, how it was read): 'model+rules' when the local model contributed, otherwise 'rules'."""
    spec = comprehend_rules(text, tickers, last_close)
    try:
        from agents.llm import ANALYST_MODEL, chat_json
        prompt = ("Read this stock tip and fill the form. Copy numbers only if the tip states them; use null otherwise. "
                  "'asks' lists what the reader is being asked to do (pay money, hand over login or control, join a group, refer others, forward it, buy, sell). "
                  "'thesis' lists the kinds of reasons it offers (results, valuation, news, technical, insider, hype) or none if it gives no reason. "
                  "'summary' is ONE plain sentence saying what the tip suggests, without judging it.\n\nTIP:\n" + text[:1500])
        out = await chat_json(prompt, _SCHEMA, model=ANALYST_MODEL, temperature=0.0, max_tokens=380, attempts=1, timeout=25.0)
    except Exception:  # noqa: BLE001
        return spec, "rules"
    for k in ("target_price", "expected_return_pct", "horizon_days", "periodic_return_pct"):
        v = out.get(k)
        if spec.get(k) is None and isinstance(v, (int, float)) and _in_text(v, text) and v > 0:
            spec[k] = float(v)
    if not spec["periodic_unit"] and out.get("periodic_unit") in ("day", "week", "month", "year") and spec["periodic_return_pct"]:
        spec["periodic_unit"] = out["periodic_unit"]
    spec["guarantee"] = spec["guarantee"] or (bool(out.get("guarantee")) and bool(re.search(r"guarant|assured|risk[- ]?free|no\s+loss", text, re.I)))
    spec["uses_leverage"] = spec["uses_leverage"] or bool(out.get("uses_leverage"))
    if out.get("action") in ("buy", "sell", "hold", "avoid") and spec["action"] == "none":
        spec["action"] = out["action"]
    # The model may add a benign kind of reasoning freely; an accusation (a request for money or access) needs words in the text that
    # support it, so the model cannot talk itself into a scam the tip does not contain.
    spec["thesis"] = sorted(set(spec["thesis"]) | {x for x in out.get("thesis", []) if x in ("results", "valuation", "news", "technical")})
    spec["asks"] = sorted(set(spec["asks"]) | {x for x in out.get("asks", []) if x in _ANCHOR and _ANCHOR[x].search(text)})
    if isinstance(out.get("summary"), str) and 10 < len(out["summary"]) < 300:
        spec["summary"] = out["summary"].strip()
    return spec, "model+rules"


# =============================================================================================== 2. the specialists
def _phi(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def p_touch(s: float, target: float, sigma: float, days: float) -> float:
    """Chance a stock with this volatility trades at the target at ANY point inside the window (zero drift, lognormal): 2 * (1 - Phi(b / (sigma * sqrt(t))))."""
    if target <= s:
        return 1.0
    return 2 * (1 - _phi(math.log(target / s) / (sigma * math.sqrt(max(days, 1) / 365))))


def _ann_vol(closes: list[float]) -> float | None:
    r = [math.log(b / a) for a, b in zip(closes, closes[1:]) if a > 0 and b > 0]
    return statistics.pstdev(r) * math.sqrt(252) if len(r) >= 40 else None


def _val(pit: PointInTimeStore, tk: str, kind: str) -> float | None:
    sg = pit.latest(tk, kind)
    return sg.value_num if sg is not None and sg.value_num is not None else None


def F(agent: str, stance: str, headline: str, why: str, weight: float = 1.0, signals: list[tuple[str, float]] | None = None, facts: dict | None = None) -> dict[str, Any]:
    return {"agent": agent, "stance": stance, "headline": headline, "reasoning": why, "weight": weight, "signals": signals or [], "facts": facts or {}}


def _rs(x: float) -> str:
    return f"₹{x:,.0f}" if x >= 100 else f"₹{x:,.2f}"


def agent_feasibility(spec, tk, now, last, closes) -> dict:
    name = "Feasibility"
    sig: list[tuple[str, float]] = []
    parts: list[str] = []
    stance = "unknown"
    # a return promised every period, or "guaranteed"
    if spec["periodic_return_pct"] and spec["periodic_unit"]:
        r, u = spec["periodic_return_pct"] / 100, spec["periodic_unit"]
        n = {"day": 252, "week": 52, "month": 12, "year": 1}[u]
        ann = (1 + r) ** n - 1
        parts.append(f"A steady {r * 100:g}% a {u} compounds to about {ann * 100:,.0f}% a year. Bank deposits pay about {RISK_FREE * 100:g}%, long-run equity about {EQUITY_LONG_RUN * 100:g}%, and the best sustained records anywhere are around {ELITE_SUSTAINED * 100:g}%. "
                     "No market pays a fixed rate every period; a payout like this can only be funded by new depositors.")
        sig.append(("A fixed periodic return far above any real market", 0.92 if ann > 0.4 else 0.7))
        stance = "against"
    if spec["guarantee"]:
        parts.append(f"A guaranteed return above the risk-free rate (about {RISK_FREE * 100:g}%) cannot exist in a share: a guarantee means someone else bears the loss, and an individual cannot credibly offer that.")
        sig.append(("A guaranteed return on a share", 0.75))
        stance = "against"
    # a price target
    target = spec["target_price"]
    if not target and spec["expected_return_pct"] and last:
        target = last * (1 + spec["expected_return_pct"] / 100)
    if target and last and closes:
        sigma = _ann_vol(closes)
        up = target / last - 1
        days = spec["horizon_days"]
        if sigma:
            wins = [(days, "the stated window")] if days else [(30, "a month"), (90, "three months"), (365, "a year")]
            txt = []
            for d, lab in wins:
                p = p_touch(last, target, sigma, d)
                txt.append(f"about {p * 100:.0f}% within {lab}" if p >= 0.01 else f"under 1% within {lab}")
            p_main = p_touch(last, target, sigma, days or 90)
            req = ((target / last) ** (365 / days) - 1) if days else None
            parts.append(f"The target {_rs(target)} is {up * 100:+.0f}% from {_rs(last)}. From this stock's own volatility ({sigma * 100:.0f}% a year), the chance it even touches that level is {', '.join(txt)}"
                         + (f"; that pace equals about {req * 100:,.0f}% a year." if req and req > 0.5 else "."))
            if not days:
                parts.append("The tip gives no time frame, which also makes it impossible to check later.")
            if p_main < 0.03:
                sig.append(("A target the stock's volatility makes close to impossible", 0.35)); stance = "against"
            elif p_main < 0.12:
                sig.append(("A target that is a long shot", 0.15)); stance = stance if stance == "against" else "against"
            else:
                stance = stance if stance == "against" else "neutral"
        else:
            parts.append(f"The target is {up * 100:+.0f}% from the last close, but there is not enough price history to model it.")
    if _CERTAIN.search(spec.get("_text", "")):
        parts.append("It speaks of the outcome as certain. No one can be certain of a share price, and sounding certain is a way of discouraging you from checking.")
        sig.append(("Claims certainty about a share price", 0.4))
        stance = "against" if stance == "unknown" else stance
    if spec["uses_leverage"]:
        parts.append("It uses leverage (futures, options or margin): a small adverse move can wipe out the whole stake, so the realistic loss is larger than the stock's own movement.")
        sig.append(("Leverage multiplies the loss", 0.15))
    if not parts:
        return F(name, "unknown", "Nothing measurable is promised", "The tip states no price, return or time frame, so there is nothing to test for feasibility. A suggestion that cannot be tested cannot be held to account either.", 0.6, [("Nothing testable is claimed", 0.15)])
    head = {"against": "The promised outcome is not realistic", "neutral": "The promised move is possible but unproven", "unknown": "Could not be tested"}[stance]
    return F(name, stance, head, " ".join(parts), 1.4, sig)


def agent_fundamentals(spec, tk, now, last) -> dict:
    name = "Fundamentals"
    if not tk:
        return F(name, "unknown", "No company we hold data on", "No company the tip names is in the data we hold, so the business cannot be examined. A tip about a company you cannot look up is the first thing to be careful with.", 1.0, [("The company cannot be examined", 0.3)])
    from analysis import proscons
    r = proscons.pros_cons(now, tk, "en")
    nm = universe.name(tk)
    strong = [x for x in r["pros"] if x["confidence"] != "weak"]
    weak = [x for x in r["cons"] if x["confidence"] != "weak"]
    pe, eps_note = _val(now, tk, "pe_ratio"), ""
    sig: list[tuple[str, float]] = []
    parts = [f"For {nm} the numbers we hold show {len(strong)} well-supported good points and {len(weak)} well-supported watch-outs"
             + (f" (leading: {strong[0]['title'].lower()}; {weak[0]['title'].lower()})." if strong and weak else ".")]
    tgt = spec["target_price"] or (last * (1 + spec["expected_return_pct"] / 100) if spec["expected_return_pct"] and last else None)
    if tgt and last and pe:
        ipe = pe * tgt / last
        peers = sorted(x for x in (_val(now, o, "pe_ratio") for o in universe.tickers() if o != tk and universe.sector(o) == universe.sector(tk)) if x)
        med = peers[len(peers) // 2] if len(peers) >= 3 else None
        hi = _val(now, tk, "pe_hist_high")
        txt = f"At the target the stock would cost about {ipe:.0f} times a year's profit (today {pe:.0f}), so profits would have to grow or the market would have to pay much more for each rupee of them"
        if med:
            txt += f"; similar companies trade around {med:.0f}"
        if hi:
            txt += f" and this company's own year-end high was about {hi:.0f}"
        parts.append(txt + ".")
        if (med and ipe > 1.6 * med) or (hi and ipe > 1.5 * hi):
            sig.append(("The target needs a valuation never seen for this company or its peers", 0.35))
    g, eg = _val(now, tk, "rev_growth"), _val(now, tk, "earn_growth")
    if "results" in spec["thesis"] and g is not None:
        parts.append(f"The tip leans on results; the latest quarter shows sales {g * 100:+.0f}%" + (f" and profit {eg * 100:+.0f}%" if eg is not None else "") + " against a year earlier.")
    stance = "for" if len(strong) >= len(weak) + 2 else "against" if len(weak) >= len(strong) + 2 else "neutral"
    head = {"for": "The business gives the idea some backing", "against": "The business does not support a bullish case", "neutral": "The business is neither a strong reason for nor against"}[stance]
    if not (r["pros"] or r["cons"]):
        return F(name, "unknown", "Too little data on this company", parts[0], 0.8)
    return F(name, stance, head, " ".join(parts), 1.3, sig, {"good": len(strong), "watch": len(weak)})


def agent_technicals(spec, tk, now, last, rows) -> dict:
    name = "Technicals"
    closes = [r["close"] for r in rows if r.get("close")]
    if len(closes) < 60:
        return F(name, "unknown", "Not enough price history", "There is not enough price history to read a trend.", 0.5)
    ma50 = sum(closes[-50:]) / 50
    ma200 = sum(closes[-200:]) / min(200, len(closes))
    hi, lo = max(closes), min(closes)
    ret21 = closes[-1] / closes[-22] - 1 if len(closes) > 22 else 0
    gains = [max(0.0, b - a) for a, b in zip(closes[-15:], closes[-14:])]
    losses = [max(0.0, a - b) for a, b in zip(closes[-15:], closes[-14:])]
    rsi = 100.0 if sum(losses) == 0 else 100 - 100 / (1 + sum(gains) / sum(losses))
    trend = "an uptrend" if last > ma200 and ma50 > ma200 else "a downtrend" if last < ma200 and ma50 < ma200 else "no clear trend"
    parts = [f"The chart shows {trend} ({_rs(last)} against a 50-day average of {_rs(ma50)} and 200-day of {_rs(ma200)}), a year range of {_rs(lo)} to {_rs(hi)}, and a recent-momentum reading (RSI) of {rsi:.0f}."]
    sig: list[tuple[str, float]] = []
    stance = "neutral"
    tgt = spec["target_price"] or (last * (1 + spec["expected_return_pct"] / 100) if spec["expected_return_pct"] else None)
    if tgt:
        above = tgt / hi - 1
        if above > 0:
            parts.append(f"The target is {above * 100:.0f}% above the highest price this stock has reached in the past year.")
            if above > 0.35:
                sig.append(("The target is far above anything the stock has traded at", 0.25)); stance = "against"
    if "technical" in spec["thesis"] and trend == "a downtrend":
        parts.append("The tip leans on momentum or a breakout, but the stock is in a downtrend, so the chart does not back the claim.")
        stance = "against"
    if ret21 > 0.2:
        parts.append(f"The stock already rose {ret21 * 100:.0f}% in the last month. Tips often arrive after the move, when early buyers want someone to sell to.")
        sig.append(("Arrives after a big run-up", 0.12))
    head = {"against": "The chart does not support it", "neutral": "The chart is neutral on the idea", "for": "The chart is consistent with it"}[stance]
    return F(name, stance, head, " ".join(parts), 0.9, sig)


def agent_market(spec, tk, now, rows, unknown_syms) -> dict:
    name = "Market structure"
    sig: list[tuple[str, float]] = []
    if not tk:
        if unknown_syms:
            try:
                from analysis import stocksearch
                listed = any(h["symbol"].replace(".NS", "").upper() == unknown_syms[0].upper() for h in stocksearch.search(unknown_syms[0], limit=5))
            except Exception:  # noqa: BLE001
                listed = None
            if listed is False:
                sig.append(("The name is not on the exchange list we hold", 0.3))
                return F(name, "against", "The name does not match any listed company", f"{', '.join(unknown_syms)} does not match a company on the NSE list we hold. It may be a recent rename (check the exchange site), or a stock that does not exist or a token that is not exchange-traded, which could not be bought safely.", 1.2, sig)
            return F(name, "unknown", "Listed but not held here", f"{', '.join(unknown_syms)} may be listed, but we hold no prices for it, so its liquidity and history cannot be checked. Add it on the Research page to fetch it.", 0.8, [("Cannot be checked", 0.2)])
        return F(name, "unknown", "No stock identified", "No specific stock is named, so there is nothing to examine on the exchange.", 0.4)
    vals = [(r["close"] or 0) * (r.get("volume") or 0) for r in rows[-20:] if r.get("close")]
    traded = statistics.mean(vals) if vals else 0
    mcap = _val(now, tk, "market_cap")
    nm = universe.name(tk)
    txt = f"{nm} trades about {_rs(traded / 1e7)} crore of shares a day" + (f" and is worth about {_rs((mcap or 0) / 1e7)} crore in total." if mcap else ".")
    if traded < 5e6 or (mcap and mcap < 5e9):
        sig.append(("A thinly traded stock that is easy to push", 0.3))
        return F(name, "against", "Small and thin: easy to manipulate", txt + " A stock this small can be pushed up by a few buyers for a few days, which is how pump groups work, and it can be hard to sell.", 1.0, sig)
    return F(name, "neutral", "Large and liquid: hard to push around", txt + " A stock this size is very hard for a group to move, which makes a 'pump' story less likely, but also means a dramatic overnight move is unlikely too.", 0.8)


def agent_source(spec, text) -> dict:
    name = "Source and incentive"
    sig: list[tuple[str, float]] = []
    parts: list[str] = []
    if "pay" in spec["asks"]:
        parts.append("It asks the reader to send money or pay a fee. A tip that costs money to receive, or that asks you to deposit with the sender, makes the sender's income depend on you paying, not on the stock being right.")
        sig.append(("Asks for money", 0.8))
    if "credentials" in spec["asks"]:
        parts.append("It asks for your login, OTP or control of your account. No genuine adviser needs this; it is how accounts are emptied.")
        sig.append(("Asks for account access", 0.9))
    if "join" in spec["asks"]:
        parts.append("It pulls you into a private or paid group, where the real selling happens out of sight.")
        sig.append(("Moves you to a private group", 0.4))
    if "refer" in spec["asks"]:
        parts.append("It asks you to bring in others, the structure of a chain scheme.")
        sig.append(("Asks you to recruit", 0.6))
    if re.search(scanner.FLAGS[next(i for i, f in enumerate(scanner.FLAGS) if f[0] == "TRACK_RECORD")][2], text, re.I):
        parts.append("It offers the sender's own track record as proof. Nobody outside can audit it, and such records are chosen to look good.")
        sig.append(("A self-reported track record as proof", 0.55))
    if "insider" in spec["thesis"]:
        parts.append("It claims inside or operator knowledge. Real insiders do not post it, and trading on it is illegal, so the claim is either false or an invitation to commit an offence.")
        sig.append(("Claims inside knowledge", 0.6))
    if "hype" in spec["thesis"]:
        parts.append("Its reasoning is hype ('rocket', 'will fly') rather than a reason you can test.")
        sig.append(("Hype instead of a reason", 0.3))
    if not spec["evidence_offered"] and spec["action"] in ("buy", "sell"):
        parts.append("It names no source you could check: no filing, announcement or report.")
        sig.append(("No source given", 0.2))
    if spec["evidence_offered"]:
        parts.append("It points to " + ", ".join(spec["evidence_offered"]) + ", which is checkable, so the claim can be verified there.")
    if not parts:
        return F(name, "neutral", "The sender asks nothing of you", "The message does not ask for money, access or recruits, so there is no visible way for the sender to profit from your reading it. That reduces, but does not remove, the chance it is a scam.", 0.9)
    stance = "against" if sig else "neutral"
    return F(name, stance, "Who gains if you act on it", " ".join(parts), 1.5, sig)


def agent_rules(spec, text) -> dict:
    name = "Rules (SEBI)"
    issues: list[str] = []
    sig: list[tuple[str, float]] = []
    if spec["guarantee"] or spec["periodic_return_pct"]:
        issues.append("a registered adviser may not guarantee or promise a return")
        sig.append(("A promise registered advisers are barred from making", 0.35))
    if "insider" in spec["thesis"]:
        issues.append("trading on unpublished price-sensitive information is an offence")
    if "credentials" in spec["asks"] or "pay" in spec["asks"]:
        issues.append("taking money or managing someone's account without registration (as an adviser, portfolio manager or broker) is not allowed")
        sig.append(("Handling money without registration", 0.35))
    if "join" in spec["asks"] or "pay" in spec["asks"]:
        issues.append("selling stock tips for a fee needs SEBI registration as an investment adviser or research analyst")
    if not issues:
        return F(name, "neutral", "Nothing in it breaks an obvious rule", "Nothing in the message, taken at face value, would breach SEBI's rules on advisers. That does not tell you the sender is registered: check the name at sebi.gov.in under intermediaries before relying on anyone for advice.", 0.7)
    return F(name, "against", "What an authorised adviser could not say or do", "Under SEBI's rules for advisers and research analysts (as understood at the time of writing; confirm on sebi.gov.in): " + "; ".join(issues) + ". A person who does this is either unregistered or ignoring the rules, and either way you have no protection if it goes wrong.", 1.0, sig)


def agent_wording(scan: dict) -> dict:
    """The older text-pattern checks, kept as one witness among seven."""
    pmap = {"GUARANTEE": .7, "MULTIPLIER": .5, "URGENCY": .2, "INSIDER": .0, "PAYWALL": .0, "NO_STOPLOSS": .2, "RETURN_RATE": .0, "TRACK_RECORD": .0, "RISK_DENIAL": .3,
            "PAYMENT": .0, "SECRECY": .25, "PENNY": .0, "REGISTRATION": .1}
    sig = [(f["label"], pmap[f["code"]]) for f in scan["flags"] if pmap.get(f["code"], 0) > 0]
    if not sig:
        return F("Wording", "neutral", "No pressure language", "The message has no urgency, hype, guarantees or secrecy in how it is written. This agent is the weakest witness: a tone that sounds calm tells you very little, because careful scams are written calmly.", 0.4)
    return F("Wording", "against", "Pressure and hype in the language", "Wording patterns found: " + "; ".join(f"{f['label'].lower()} ({f['quote']})" for f in scan["flags"][:4]) + ". On its own this proves little, so it carries the least weight.", 0.5, sig)


def agent_consequence(spec, tk, last, closes, amount) -> dict:
    name = "Consequence"
    sigma = _ann_vol(closes) if closes else None
    days = spec["horizon_days"] or 90
    parts = [f"If you put in {_rs(amount)} and it turns out to be a scam, the realistic loss is all of it, with little chance of recovery."]
    if sigma:
        move = sigma * math.sqrt(days / 365)
        parts.append(f"If the stock is real, an ordinary move over {days} days is about ±{move * 100:.0f}%, so even a legitimate holding could be down about {_rs(amount * move)} with no stop or reason to hold.")
    if spec["uses_leverage"]:
        parts.append("With leverage the loss can exceed what you put in.")
    return F(name, "neutral", "What it could cost you", " ".join(parts), 0.3, facts={"amount": amount})


# =============================================================================================== 3. synthesis
def _amount(text: str) -> float:
    m = re.search(r"(?:₹|rs\.?|rupees)\s*" + _NUM + r"\s*(lakh|lac|crore|k)?|" + _NUM + r"\s*(lakh|lac|crore|k)\b", text, re.I)
    if not m:
        return 50000.0
    n = _f(m.group(1) or m.group(3)); u = (m.group(2) or m.group(4) or "").lower()
    return n * {"lakh": 1e5, "lac": 1e5, "crore": 1e7, "k": 1e3}.get(u, 1)


def synthesise(findings: list[dict], spec: dict, scan: dict, tk: str | None) -> dict[str, Any]:
    # scam likelihood: independent signals combine (noisy-or), every one named
    sigs = [(label, p, f["agent"]) for f in findings for label, p in f["signals"] if p > 0]
    q = 1.0
    for _, p, _a in sigs:
        q *= (1 - p)
    scam = round(1 - q, 3)
    if not any(p >= 0.5 for _, p, _a in sigs):
        scam = min(scam, 0.45)          # weak hints add up, but only strong evidence of fraud mechanics can take it past "unreliable"
    contradicted = sum(1 for c in scan["claims"] if c["status"] == "CONTRADICTED" and not c["text"].lower().startswith(("target", "tgt")))
    if contradicted:
        scam = round(1 - (1 - scam) * (0.75 ** contradicted), 3)
        sigs.append((f"{contradicted} factual claim(s) contradicted by the data", 0.25, "Fundamentals"))
    by = {f["agent"]: f for f in findings}
    # reliability: does the idea have real backing, whatever the sender's motives
    rel = 40
    reasons: list[str] = []
    fund = by.get("Fundamentals", {}).get("stance")
    feas = by.get("Feasibility", {})
    if fund == "for":
        rel += 20; reasons.append("+ the company's numbers support a bullish view")
    elif fund == "against":
        rel -= 20; reasons.append("- the company's numbers do not support a bullish view")
    if feas.get("stance") == "against":
        rel -= 25; reasons.append("- the promised outcome is not realistic")
    elif feas.get("stance") == "neutral":
        rel += 10; reasons.append("+ the promised move is within what the stock could do")
    supported = sum(1 for c in scan["claims"] if c["status"] == "SUPPORTED")
    if supported:
        rel += min(20, 10 * supported); reasons.append(f"+ {supported} claim(s) checked out against the data")
    if contradicted:
        rel -= 15 * contradicted; reasons.append(f"- {contradicted} claim(s) contradicted")
    if not spec["thesis"] and not spec["evidence_offered"] and spec["action"] in ("buy", "sell"):
        rel -= 20; reasons.append("- it gives no reason or source for the call")
    if spec["evidence_offered"]:
        rel += 10; reasons.append("+ it cites something you can check")
    if by.get("Technicals", {}).get("stance") == "against":
        rel -= 10; reasons.append("- the chart does not support it")
    if scam >= 0.5:
        rel -= 20; reasons.append("- the sender's own behaviour points to a scam")
    rel = max(0, min(100, rel))

    asked_danger = "pay" in spec["asks"] or "credentials" in spec["asks"]
    informational = spec["action"] == "none" and not spec["asks"] and not spec["target_price"] and not spec["expected_return_pct"] and not spec["periodic_return_pct"] and not spec["guarantee"]
    if informational and scam < 0.3:
        action, verdict, tone = "INFO", "NOT A TIP: INFORMATION ONLY", "green"
    elif asked_danger or scam >= 0.75:
        action, verdict, tone = "IGNORE_REPORT", "LIKELY A SCAM: DO NOT ACT, REPORT IT", "red"
    elif scam >= 0.45 or rel < 30:
        action, verdict, tone = "IGNORE", "UNRELIABLE: DO NOT ACT ON IT", "red" if scam >= 0.6 else "amber"
    elif rel >= 60 and scam < 0.3:
        action, verdict, tone = "RESEARCH", "HAS SOME BACKING: WORTH RESEARCHING, NOT A RECOMMENDATION", "green"
    else:
        action, verdict, tone = "VERIFY", "UNPROVEN: VERIFY BEFORE ANYTHING ELSE", "amber"
    return {"scam": scam, "reliability": rel, "reliability_reasons": reasons, "action": action, "verdict": verdict, "tone": tone,
            "signals": sorted(sigs, key=lambda s: -s[1])}


def next_steps(action: str, spec: dict, tk: str | None) -> list[str]:
    nm = universe.name(tk) if tk else "the company"
    if action == "INFO":
        return ["This reads as information, not a recommendation: nothing asks you to do anything.",
                "If the event matters to you, confirm it on the company's exchange announcements and decide for yourself.",
                "A statement can be true and still not be a reason to buy or sell."]
    if action == "IGNORE_REPORT":
        return ["Do not pay, do not share any login, OTP or account access, and do not join or forward the group.",
                "If you already paid or shared something, use the recovery coach now: freeze cards and UPI in your bank app and call 1930 within the hour.",
                "Report the sender: cybercrime.gov.in, and SEBI's complaint portal (SCORES) for a fake adviser. Keep screenshots.",
                "Block the sender. A scam that fails once is sent to the same person again from a new number."]
    if action == "IGNORE":
        return ["Leave it. Nothing here gives you a reason to put money in.",
                "If you are still curious about the company, look at it on the Research page on your own terms, without the tip's target or deadline.",
                "Check the sender at sebi.gov.in under intermediaries. If they are not registered, they should not be giving stock advice at all.",
                "Do not forward it: if it is a pump, forwarding is how it finds buyers."]
    if action == "RESEARCH":
        return [f"Treat it only as a reason to look at {nm}, not to buy it. Open the Research page and read the good points, the watch-outs and how current the data is.",
                "Read the filing or announcement the tip points to yourself, and check the date.",
                "Decide your own amount and your own exit before anything else. If you cannot say why you would sell, you are not ready to buy.",
                "If you act at all, keep it small enough that losing all of it would not matter."]
    return ["Ask the sender for the filing, announcement or report behind it, and for their SEBI registration number.",
            "Check the company's exchange announcements for the date of the tip: a real catalyst will be there.",
            f"Open the Research page for {nm} and compare what the tip claims with the numbers.",
            "If they cannot or will not show a source, treat the tip as unreliable. Do not act while you wait."]


# =============================================================================================== entry points
def _prepare(pit: PointInTimeStore, text: str):
    scan = scanner.scan(pit, text)
    now = scanner._today(pit)
    tickers = scanner.find_companies(text)
    tk = tickers[0] if tickers else None
    rows = [r for r in now.prices(tk, 250) if r.get("close")] if tk else []
    last = rows[-1]["close"] if rows else None
    return scan, now, tickers, tk, rows, last


def _finish(pit, text, scan, now, tickers, tk, rows, last, spec, how) -> dict[str, Any]:
    closes = [r["close"] for r in rows]
    findings = [agent_feasibility(spec, tk, now, last, closes), agent_fundamentals(spec, tk, now, last), agent_technicals(spec, tk, now, last, rows) if tk else
                F("Technicals", "unknown", "No chart to read", "No stock we hold prices for is named, so there is no chart to read.", 0.3),
                agent_market(spec, tk, now, rows, scan.get("unknown", [])), agent_source(spec, text), agent_rules(spec, text), agent_wording(scan),
                agent_consequence(spec, tk, last, closes, _amount(text))]
    syn = synthesise(findings, spec, scan, tk)
    steps = next_steps(syn["action"], spec, tk)
    out = dict(scan)                                       # keep every older field so existing screens still work
    out.update({"verdict": syn["verdict"], "tone": syn["tone"], "score": round(syn["scam"] * 100), "agents": findings, "reading": {**{k: v for k, v in spec.items() if k != "_text"}, "how": how},
                "scam_likelihood": round(syn["scam"] * 100), "reliability": syn["reliability"], "reliability_reasons": syn["reliability_reasons"],
                "signals": [{"label": a, "p": p, "agent": g} for a, p, g in syn["signals"]], "action": syn["action"], "steps": steps,
                "ticker": tk})
    why = [f"{f['agent']}: {f['headline'].lower()}" for f in findings if f["stance"] == "against"][:3]
    out["summary"] = (f"{syn['verdict'].capitalize()}. Scam likelihood {round(syn['scam'] * 100)}%, backing for the idea {syn['reliability']}/100. "
                      + ("Main reasons: " + "; ".join(why) + "." if why else "No specialist found a serious problem, but that is not a reason to buy."))
    out["disclaimer"] = ("A reasoned check, not advice. Each specialist works from data we hold and standard financial reasoning; it cannot know what is not on file, "
                         "and a tip that passes is still only a reason to research.")
    return out


def analyse_sync(pit: PointInTimeStore, text: str) -> dict[str, Any]:
    """The full analysis with the rules reader (no model): deterministic, used by tests and any offline path."""
    text = (text or "").strip()
    if not text:
        return {"empty": True}
    scan, now, tickers, tk, rows, last = _prepare(pit, text)
    spec = comprehend_rules(text, tickers, last)
    spec["_text"] = text
    return _finish(pit, text, scan, now, tickers, tk, rows, last, spec, "rules")


async def analyse(pit: PointInTimeStore, text: str) -> dict[str, Any]:
    """The full analysis; the local model, when available, reads the wording into the fixed form first."""
    text = (text or "").strip()
    if not text:
        return {"empty": True}
    scan, now, tickers, tk, rows, last = _prepare(pit, text)
    spec, how = await comprehend(text, tickers, last)
    spec["_text"] = text
    return _finish(pit, text, scan, now, tickers, tk, rows, last, spec, how)
