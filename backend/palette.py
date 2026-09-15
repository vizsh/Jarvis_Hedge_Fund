"""The command palette: everything this thing can do, in one searchable list.

Discoverability in this product currently depends on already knowing that "Fund desk"
contains the correlation matrix and that "Machinery" contains the calibration record.
Nobody knows that on their first visit, and nobody should have to. A palette makes
capability searchable instead of navigable — you type what you want in your own words
and the thing you wanted is the first result.

Two decisions worth stating:

  - Entries are indexed by **what a person would type**, not by what the feature is
    called internally. Somebody worried about concentration types "too much in one
    place", not "HHI". The `keywords` field carries those phrasings so the search finds
    them.
  - Everything is here, including the expert surfaces. The palette is the one place the
    product does not simplify by hiding, because a search result that does not exist is
    indistinguishable from a feature that does not exist.

Matching is a small deterministic scorer, not a model. It has to return the same result
every time and it has to run while somebody is typing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from backend import flows as flows_mod


@dataclass
class Entry:
    id: str
    label: str                       # what the row says
    hint: str                        # the one-line explanation underneath
    group: str                       # Ask | Do | Look at | Change | Present
    kind: str                        # question | flow | panel | endpoint | action
    payload: str                     # question text, flow id, panel name, or path
    keywords: list[str] = field(default_factory=list)
    shortcut: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, "label": self.label, "hint": self.hint,
                "group": self.group, "kind": self.kind, "payload": self.payload,
                "shortcut": self.shortcut}


def _questions() -> list[Entry]:
    """The things people actually want to know, phrased as they would say them."""
    return [
        Entry("q.health", "How am I doing?",
              "A plain summary of everything you own", "Ask", "question",
              "How am I doing?",
              ["health", "summary", "overview", "score", "grade", "how is my portfolio"]),
        Entry("q.risk", "Why is my risk high?",
              "The specific things that are outside your limits", "Ask", "question",
              "Why is my risk high?",
              ["risk", "danger", "problem", "wrong", "worried", "concern", "bad"]),
        Entry("q.sell", "What should I sell?",
              "The smallest change that brings you inside your limits", "Ask",
              "question", "What should I sell?",
              ["sell", "reduce", "trim", "fix", "cut", "what do i do"]),
        Entry("q.div", "Am I diversified?",
              "How many positions your risk really behaves like", "Ask", "question",
              "Am I diversified?",
              ["diversified", "spread out", "concentrated", "too much in one place",
               "all in one", "eggs in one basket"]),
        Entry("q.crash", "What if the market drops 20%?",
              "What a fall of that size would cost you", "Ask", "question",
              "What if the market drops 20%?",
              ["crash", "drop", "fall", "downturn", "lose", "worst case", "bear"]),
        Entry("q.covid", "What happened in Covid?",
              "This exact basket, replayed through the 2020 crash", "Ask", "question",
              "What happened in Covid?",
              ["covid", "2020", "pandemic", "history", "past crash"]),
        Entry("q.worst", "What is my worst case?",
              "The largest loss in any window we have prices for", "Ask", "question",
              "What is my worst case?",
              ["worst", "maximum loss", "how bad", "drawdown"]),
        Entry("q.beta", "What does beta mean?",
              "Plain-English definition, with your own number", "Ask", "question",
              "What does beta mean?",
              ["beta", "jargon", "define", "meaning", "explain term", "glossary"]),
    ]


def _panels() -> list[Entry]:
    return [
        Entry("p.actions", "My action list",
              "Ranked list of what is worth doing next", "Look at", "panel", "actions",
              ["todo", "what next", "actions", "tasks", "queue", "advice"]),
        Entry("p.xray", "Portfolio X-ray",
              "Grade, spread, and every finding", "Look at", "panel", "xray",
              ["xray", "x-ray", "health", "grade", "score", "breakdown"]),
        Entry("p.chart", "My money over time",
              "Your basket against the index", "Look at", "panel", "chart",
              ["chart", "graph", "performance", "history", "over time", "returns"]),
        Entry("p.positions", "What I own",
              "Every holding, weight and sector", "Look at", "panel", "positions",
              ["positions", "holdings", "stocks", "what i own", "shares"]),
        Entry("p.stress", "Stress tests",
              "Real crashes replayed against your holdings", "Look at", "panel",
              "stress", ["stress", "scenarios", "crash test", "what if"]),
        Entry("p.correlation", "What moves together",
              "Holdings that are secretly the same bet", "Look at", "panel",
              "correlation",
              ["correlation", "moves together", "same bet", "overlap", "duplicate"]),
        Entry("p.tax", "Tax on selling",
              "What a plan would cost, line by line", "Look at", "panel", "tax",
              ["tax", "capital gains", "ltcg", "stcg", "bill"]),
        Entry("p.rebalance", "Rebalance plan",
              "Smallest set of trades back to compliance", "Look at", "panel",
              "rebalance", ["rebalance", "plan", "trades", "fix everything"]),
        Entry("p.screener", "Find diversifiers",
              "Names that would actually add something", "Look at", "panel",
              "screener", ["screen", "find stocks", "ideas", "diversifiers", "buy"]),
        Entry("p.attribution", "Where returns came from",
              "Allocation versus selection, per sector", "Look at", "panel",
              "attribution",
              ["attribution", "where did returns come from", "brinson", "performance"]),
        Entry("p.calibration", "Track record",
              "How often the desks have actually been right", "Look at", "panel",
              "calibration",
              ["calibration", "brier", "track record", "accuracy", "were you right"]),
        Entry("p.watchlist", "My alerts",
              "Standing rules that check themselves", "Look at", "panel", "watchlist",
              ["alerts", "watch", "rules", "notify", "tell me if", "monitor"]),
        Entry("p.desks", "The research desks",
              "Four analysts, a red team, and the citation gate", "Look at", "panel",
              "desks", ["desks", "agents", "analysts", "research", "machinery"]),
    ]


def _commands() -> list[Entry]:
    return [
        Entry("c.report", "Print a one-page report",
              "Everything on one page you can keep or share", "Do", "action", "report",
              ["report", "print", "pdf", "export", "share", "summary page"]),
        Entry("c.builder", "Edit my holdings",
              "Add, remove or change what you own", "Change", "action", "builder",
              ["edit", "add holdings", "change portfolio", "my stocks", "import"]),
        Entry("c.profile", "Change my risk limits",
              "Retail, balanced or institutional", "Change", "action", "profile",
              ["limits", "profile", "strict", "risk level", "policy", "caps"]),
        Entry("c.sandbox", "Try a change without committing",
              "Stage trades and compare before and after", "Do", "action", "sandbox",
              ["try", "test", "simulate", "what would happen", "sandbox", "preview"]),
        Entry("c.reset", "Start over", "Restore the portfolio and clock", "Change",
              "endpoint", "reset", ["reset", "start over", "undo", "restore"]),
        Entry("c.presenter", "Presenter mode",
              "Teleprompter and the scripted walkthrough", "Present", "action",
              "presenter", ["present", "demo", "script", "teleprompter", "pitch"],
              shortcut="T"),
        Entry("c.replay", "Replay the golden take",
              "A recorded run, for when the live one fails", "Present", "endpoint",
              "/replay/start?name=demo",
              ["replay", "recording", "golden", "backup", "break glass"],
              shortcut="R"),
        Entry("c.mute", "Stop talking",
              "Silence the voice until you resume it", "Do", "action", "mute",
              ["quiet", "stop", "mute", "silence", "shut up", "stop talking"]),
    ]


def catalogue() -> list[Entry]:
    """Everything, with the flows folded in so jobs are searchable too."""
    entries = _questions() + _panels() + _commands()
    for flow in flows_mod.FLOWS.values():
        entries.append(Entry(
            id=f"f.{flow.id}",
            label=flow.title,
            hint=f"{flow.subtitle} · about {flow.minutes} min",
            group="Do", kind="flow", payload=flow.id,
            keywords=re.findall(r"[a-z]+", (flow.title + " " + flow.subtitle).lower()),
        ))
    return entries


def _score(entry: Entry, query: str) -> float:
    """Deterministic and cheap. Runs on every keystroke, so no model and no I/O."""
    q = query.lower().strip()
    if not q:
        return 0.0
    label = entry.label.lower()
    hint = entry.hint.lower()

    if label == q:
        return 1000.0
    if label.startswith(q):
        return 500.0
    score = 0.0
    if q in label:
        score += 200.0
    if q in hint:
        score += 60.0
    for kw in entry.keywords:
        if kw == q:
            score += 180.0
        elif kw.startswith(q) or q in kw:
            score += 70.0
        elif q.startswith(kw) and len(kw) > 3:
            score += 40.0
    # Every word of the query that lands somewhere counts, so "what do i sell" still
    # finds "What should I sell?" despite matching no single field exactly.
    words = [w for w in re.findall(r"[a-z0-9%]+", q) if len(w) > 2]
    hay = f"{label} {hint} {' '.join(entry.keywords)}"
    hits = sum(1 for w in words if w in hay)
    if words:
        score += 90.0 * (hits / len(words))
    return score


def search(query: str, limit: int = 8) -> list[dict[str, Any]]:
    """Ranked results, or a sensible default list when nothing has been typed yet."""
    entries = catalogue()
    if not query.strip():
        default = ["p.actions", "q.health", "f.health_check", "q.sell", "p.xray",
                   "f.fix_finding", "c.report", "c.sandbox"]
        by_id = {e.id: e for e in entries}
        return [by_id[i].as_dict() for i in default if i in by_id][:limit]

    scored = [(s, e) for e in entries if (s := _score(e, query)) > 30.0]
    scored.sort(key=lambda se: (-se[0], se[1].label))
    return [e.as_dict() for _, e in scored[:limit]]


def groups() -> dict[str, list[dict[str, Any]]]:
    """The whole catalogue, grouped — what the palette shows when browsing, not typing."""
    out: dict[str, list[dict[str, Any]]] = {}
    for e in catalogue():
        out.setdefault(e.group, []).append(e.as_dict())
    return out
