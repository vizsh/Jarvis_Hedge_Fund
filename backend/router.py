"""One entry point for everything the user types or says.

Before this there were two disconnected systems. The command bar parsed IMPERATIVES
("analyse TCS", "rewind to 2020"), and a separate Ask panel answered QUESTIONS. A user
typing a question into the box they are looking at got routed through the imperative
parser, which produced results ranging from useless to alarming:

    "what should I sell"            -> tried to PLACE A TRADE
    "what if the market drops 20%"  -> opened the policy simulator and changed a limit
    "how am I doing"                -> matched nothing, guessed by a small model
    "am I diversified"              -> matched nothing

Voice went through the same parser, so a perfectly transcribed sentence still produced
the wrong action. The microphone was never the problem.

The rule here is deliberately conservative: **an imperative must prove itself.** A
command pattern only wins if its object is present too -- a verb with no ticker, no
date and no quantity is almost always someone asking a question, not issuing an order.
Everything that does not prove itself goes to the explainer, which is far better at
questions and cannot do anything destructive.

Ambiguity resolves toward the safe side on purpose. Mistaking a question for a trade is
a much worse failure than mistaking a trade for a question: one of them moves money.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from backend.intents import Intent, parse_date, resolve_ticker, unresolved_symbol

# --- imperatives, each requiring its object ----------------------------------------
BUY_SELL = re.compile(r"\b(buy|sell|purchase|add|trim|reduce|offload)\b", re.I)
QTY = re.compile(r"\b\d{1,7}\b")
INVESTIGATE = re.compile(r"\b(analys[ei]|analyz[ei]|investigate|research|look\s+at|"
                         r"check\s+out|pull\s+up|tell\s+me\s+about)\b", re.I)
REWIND = re.compile(r"\b(rewind|go\s+back|take\s+(?:us|me)\s+back|travel\s+back|"
                    r"set\s+the\s+clock|jump\s+to)\b", re.I)
# The policy simulator changes a LIMIT. It must mention one, or "what if the market
# drops 20%" -- a stress question -- silently rewrote the user's risk policy.
SIMULATE = re.compile(r"\b(relax|tighten|loosen|raise|lower|change)\b.{0,30}"
                      r"\b(cap|limit|policy)\b", re.I)
SIMULATE_ALT = re.compile(r"\bwhat\s+if\b.{0,40}\b(cap|limit|policy)\b", re.I)
EXECUTE = re.compile(r"^\s*(execute|approve|confirm|book\s+it|do\s+it|place\s+it)\b", re.I)
ACCEPT = re.compile(r"\b(accept|take)\b.{0,24}\b(remedy|reduction|smaller|counter)\b"
                    r"|\bremed(?:y|ies)\b", re.I)
RESET = re.compile(r"^\s*(reset|start\s+over|restore|clear)\b", re.I)
STATUS = re.compile(r"^\s*(show\s+me\s+(?:the\s+)?(?:portfolio|positions|holdings)|"
                    r"portfolio|positions|holdings|status)\s*\??$", re.I)
REBALANCE = re.compile(r"\b(rebalance|fix\s+(?:my|the)\s+portfolio|"
                       r"bring\s+me\s+(?:back\s+)?in\s*line)\b", re.I)


# Advisory phrasing is ALWAYS a question, whatever verbs and objects follow it.
# "should I buy more TCS" has a trade verb and a ticker and would otherwise have been
# routed as an order -- which is the single worst misroute available here, because it
# is the one that moves money.
ADVISORY = re.compile(
    r"^\s*(should|shall|can|could|would|ought|is\s+it\s+worth|do\s+you\s+think|"
    r"what\s+do\s+you\s+think|any\s+thoughts|worth)\b", re.I)


@dataclass
class Route:
    kind: str                 # "command" | "question"
    intent: Intent | None = None
    text: str = ""
    why: str = ""             # for the log; makes misroutes debuggable


def route(text: str) -> Route:
    raw = (text or "").strip()
    if not raw:
        return Route("question", text=raw, why="empty")

    # Asked for an opinion, not given an order. Decided before anything else.
    if ADVISORY.match(raw):
        return Route("question", text=raw, why="advisory phrasing")

    ticker = resolve_ticker(raw)
    date = parse_date(raw)
    qty = QTY.search(raw)

    # --- trade: needs a side AND something to trade -------------------------------
    # "what should I sell" has a side and nothing else. That is a question.
    if BUY_SELL.search(raw) and (ticker or (qty and re.search(
            r"\b(buy|sell)\b\s+\d", raw, re.I))):
        side = "SELL" if re.search(r"\b(sell|trim|reduce|offload)\b", raw, re.I) else "BUY"
        intent = Intent(verb="propose", ticker=ticker, raw=raw,
                        args={"side": side,
                              "shares": int(qty.group()) if qty else None})
        if not ticker and (unknown := unresolved_symbol(raw)):
            intent.args["unresolved"] = unknown
        return Route("command", intent, raw, "trade verb with an object")

    # --- rewind: needs a date ------------------------------------------------------
    if REWIND.search(raw):
        if date:
            return Route("command", Intent(verb="rewind", raw=raw, args={"date": date}),
                         raw, "rewind with a date")
        return Route("command", Intent(verb="rewind", raw=raw, args={"date": None}),
                     raw, "rewind without a date (will report)")

    # --- policy simulator: must name a limit --------------------------------------
    if SIMULATE.search(raw) or SIMULATE_ALT.search(raw):
        args: dict = {}
        if pctm := re.search(r"(\d{1,3})\s*(?:%|percent)", raw, re.I):
            args["max_sector_pct"] = int(pctm.group(1)) / 100
        return Route("command", Intent(verb="simulate", raw=raw, args=args),
                     raw, "policy change naming a limit")

    # --- single-word imperatives ---------------------------------------------------
    if EXECUTE.search(raw):
        return Route("command", Intent(verb="execute", raw=raw), raw, "execute")
    if ACCEPT.search(raw):
        return Route("command", Intent(verb="accept", raw=raw), raw, "accept remedy")
    if RESET.search(raw):
        return Route("command", Intent(verb="reset", raw=raw), raw, "reset")
    if STATUS.match(raw):
        return Route("command", Intent(verb="status", raw=raw), raw, "status")
    if REBALANCE.search(raw):
        return Route("command", Intent(verb="rebalance", raw=raw), raw, "rebalance")

    # --- investigate: needs a ticker ----------------------------------------------
    if INVESTIGATE.search(raw):
        if ticker:
            return Route("command", Intent(verb="investigate", ticker=ticker, raw=raw),
                         raw, "investigate with a ticker")
        if (unknown := unresolved_symbol(raw)):
            return Route("command",
                         Intent(verb="investigate", raw=raw,
                                args={"unresolved": unknown}),
                         raw, "investigate with an unknown symbol")
        # "tell me about my portfolio" is a question, not an investigation.
        return Route("question", text=raw, why="investigate verb with no ticker")

    # A bare ticker on its own is unambiguous: "TCS" means look at TCS.
    if ticker and len(raw.split()) <= 2:
        return Route("command", Intent(verb="investigate", ticker=ticker, raw=raw),
                     raw, "bare ticker")

    # --- everything else is a question --------------------------------------------
    return Route("question", text=raw, why="no imperative proved itself")
