"""Intent routing: deterministic patterns first, small model only as a fallback.

Regex before LLM is not laziness, it is demo insurance. The handful of commands the
script actually uses must resolve identically every single time, with no model in the
path to have an opinion about them. `phi3:mini` catches the phrasings we did not
anticipate, and if Ollama is down the regex path still works.

Voice transcription mangles tickers badly ("TCS" comes back as "T C S", "Infosys" for
INFY), so ticker resolution goes through an alias table rather than exact matching.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

from agents.llm import ROUTER_MODEL, chat_json
from risk.seed import SECTORS

VERBS = ("investigate", "rewind", "propose", "simulate", "execute", "accept",
         "explain", "reset", "status")

# Spoken forms and common transcription errors -> canonical ticker.
ALIASES: dict[str, str] = {
    "tcs": "TCS.NS", "t c s": "TCS.NS", "tata consultancy": "TCS.NS",
    "infy": "INFY.NS", "infosys": "INFY.NS",
    "wipro": "WIPRO.NS",
    "hcl": "HCLTECH.NS", "hcl tech": "HCLTECH.NS", "hcltech": "HCLTECH.NS",
    "tech mahindra": "TECHM.NS", "techm": "TECHM.NS",
    "mphasis": "MPHASIS.NS", "m phasis": "MPHASIS.NS",
    "persistent": "PERSISTENT.NS", "persistent systems": "PERSISTENT.NS",
    "hdfc": "HDFCBANK.NS", "hdfc bank": "HDFCBANK.NS",
    "icici": "ICICIBANK.NS", "icici bank": "ICICIBANK.NS",
    "itc": "ITC.NS",
    "hul": "HINDUNILVR.NS", "hindustan unilever": "HINDUNILVR.NS",
    "apple": "AAPL", "microsoft": "MSFT", "nvidia": "NVDA",
}

MONTHS = ("january february march april may june july august september october "
          "november december").split()


@dataclass
class Intent:
    verb: str
    ticker: str | None = None
    args: dict = field(default_factory=dict)
    raw: str = ""
    via: str = "pattern"     # pattern | model | fallback

    def as_payload(self) -> dict:
        return {"verb": self.verb, "ticker": self.ticker, "args": self.args,
                "via": self.via}


# A symbol-shaped token: three or more consecutive capitals.
# Words that look like tickers but are not -- so ordinary speech does not trip
# the unknown-symbol check.
_NOT_TICKERS = {"JARVIS", "NAV", "NSE", "BSE", "SEBI", "RBI", "AI", "LLM",
                "USD", "INR", "ETF", "CEO", "CFO", "GDP", "CPI"}

_CANDIDATE = re.compile(r"\b[A-Z]{3,12}\b")


def unresolved_symbol(text: str) -> str | None:
    """A ticker-shaped token that resolves to nothing.

    Without this, "analyse ZOMATO" resolved to None, fell through to the default
    ticker, and confidently investigated TCS under the wrong name -- a wrong answer
    presented as a right one, which is far worse than an error.
    """
    if resolve_ticker(text):
        return None
    for token in _CANDIDATE.findall(text):
        if token.upper() in _NOT_TICKERS:
            continue
        if not resolve_ticker(token):
            return token
    return None


def resolve_ticker(text: str) -> str | None:
    """Find a company mentioned anywhere in a sentence.

    ALIASES is a hand-written table of spoken forms and transcription errors, and it
    only ever covered about twenty names. The universe has fifty-six, so a question
    about any of the other thirty-six -- "should I buy Nestle India" -- resolved to
    nothing and fell through to a generic answer. The alias table still wins first
    (it carries the mishearings), then we scan the full catalogue.
    """
    from core import universe  # local import: universe imports nothing from here

    low = text.lower()
    if m := re.search(r"\b([A-Z]{2,12}\.NS|AAPL|MSFT|NVDA)\b", text):
        return m.group(1)

    # longest alias first so "hdfc bank" beats "hdfc"
    for alias in sorted(ALIASES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", low):
            return ALIASES[alias]

    # Then the whole universe, longest name first for the same reason.
    candidates: list[tuple[str, str]] = []
    for ticker in universe.tickers():
        candidates.append((universe.name(ticker), ticker))
        candidates.append((ticker.replace(".NS", ""), ticker))
    for label, ticker in sorted(candidates, key=lambda kv: -len(kv[0])):
        if len(label) < 3:
            continue
        if re.search(rf"\b{re.escape(label.lower())}\b", low):
            return ticker
    return None


def parse_date(text: str) -> str | None:
    if m := re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text):
        return m.group(0)
    # "20 February 2020" / "february 20 2020" / "feb 2020"
    low = text.lower()
    year = re.search(r"\b(19|20)\d{2}\b", low)
    if not year:
        return None
    month = next((i + 1 for i, name in enumerate(MONTHS)
                  if re.search(rf"\b{name[:3]}", low)), None)
    if not month:
        return f"{year.group(0)}-01-01"
    day = 1
    if d := re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\b(?!\d)", low):
        candidate = int(d.group(1))
        if 1 <= candidate <= 31:
            day = candidate
    try:
        return datetime(int(year.group(0)), month, day).strftime("%Y-%m-%d")
    except ValueError:
        return f"{year.group(0)}-{month:02d}-01"


PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(rewind|go back|take us back|travel back|set the clock)\b", re.I), "rewind"),
    (re.compile(r"\b(investigate|analyse|analyze|look at|research|what about)\b", re.I), "investigate"),
    (re.compile(r"\b(buy|sell|propose|add|trim)\b", re.I), "propose"),
    (re.compile(r"\b(simulate|what if|relax|tighten|loosen)\b", re.I), "simulate"),
    # "accept" is tested BEFORE "execute" on purpose. Taking the firewall's smaller
    # counter-offer is a different decision from approving what you actually asked for,
    # and collapsing the two lets the system book a size you never agreed to.
    (re.compile(r"\bremed(?:y|ies)\b", re.I), "accept"),
    (re.compile(r"\b(accept|take)\b.{0,24}\b(reduction|smaller|counter[- ]?offer)\b", re.I),
     "accept"),
    (re.compile(r"\b(execute|approve|confirm|do it|book it)\b", re.I), "execute"),
    (re.compile(r"\b(why|explain|justify|reason)\b", re.I), "explain"),
    (re.compile(r"\b(reset|start over|restore)\b", re.I), "reset"),
    (re.compile(r"\b(status|state|position|portfolio|exposure)\b", re.I), "status"),
]

INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "verb": {"type": "string", "enum": list(VERBS)},
        "ticker": {"type": "string"},
    },
    "required": ["verb"],
}


def parse_pattern(text: str) -> Intent | None:
    for rx, verb in PATTERNS:
        if rx.search(text):
            intent = Intent(verb=verb, ticker=resolve_ticker(text), raw=text)
            if verb in ("investigate", "propose") and not intent.ticker:
                if (unknown := unresolved_symbol(text)):
                    intent.args["unresolved"] = unknown
            if verb == "rewind":
                intent.args["date"] = parse_date(text)
            elif verb == "propose":
                side = "SELL" if re.search(r"\b(sell|trim)\b", text, re.I) else "BUY"
                shares = re.search(r"\b(\d{1,6})\s*(shares?|units?)?\b", text)
                intent.args = {"side": side,
                               "shares": int(shares.group(1)) if shares else None}
            elif verb == "simulate":
                if pct := re.search(r"(\d{1,3})\s*(?:%|percent)", text, re.I):
                    intent.args["max_sector_pct"] = int(pct.group(1)) / 100
            return intent
    return None


async def parse(text: str) -> Intent:
    """Patterns first. Only unrecognised phrasings reach the model."""
    if (intent := parse_pattern(text)) is not None:
        return intent
    try:
        data = await chat_json(
            f"Classify this command into one verb.\nVerbs: {', '.join(VERBS)}\n"
            f"Command: {text}",
            INTENT_SCHEMA, model=ROUTER_MODEL, temperature=0.0, max_tokens=60)
        verb = str(data.get("verb", "")).lower()
        if verb in VERBS:
            return Intent(verb=verb, ticker=resolve_ticker(text), raw=text, via="model")
    except Exception:  # noqa: BLE001
        pass
    # Unparseable, but a ticker on its own is unambiguous enough to act on.
    ticker = resolve_ticker(text)
    return Intent(verb="investigate" if ticker else "status", ticker=ticker,
                  raw=text, via="fallback")
