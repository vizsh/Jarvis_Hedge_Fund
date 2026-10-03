"""Guided flows: jobs, not panels.

"My money / Fund desk / Machinery" are *audiences*. Nobody arrives at a portfolio tool
wanting an audience; they arrive wanting a job done — check my health, fix the thing
you just told me about, decide whether to buy this, get ready for tax season. A flow is
that job expressed as a short sequence of beats.

The design rule is that **a flow never asks the user to go and look somewhere**. Each
step carries what to say, which panel to raise, and which endpoint holds the numbers,
so the app opens the right thing at the right moment. That is the entire difference
between guiding and being guided.

Steps are small and declarative on purpose. The frontend is a renderer here, not a
decision-maker: adding a job is adding data to this file, not writing a component.

Step kinds
  say      narrate a beat; optionally speak it aloud
  show     raise a panel and fetch its endpoint
  choose   put two or more options to the user, each with a consequence
  ask      run a question through the explainer and show the answer
  confirm  a real, reversible commitment (staged in the sandbox, never a live fill)
  done     closing line, with what changed

Every flow ends in `done`. A flow that trails off leaves the user exactly where the
panel wall left them -- holding information and no next move.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Step:
    kind: str                              # say | show | choose | ask | confirm | done
    text: str = ""
    panel: str | None = None               # which panel the shell should raise
    endpoint: str | None = None            # where the numbers for this beat live
    question: str | None = None            # for kind="ask"
    options: list[dict[str, Any]] = field(default_factory=list)
    speak: bool = True                     # read this beat aloud in guided voice mode
    note: str | None = None                # small print under the beat

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "text": self.text, "panel": self.panel,
                "endpoint": self.endpoint, "question": self.question,
                "options": self.options, "speak": self.speak, "note": self.note}


@dataclass
class Flow:
    id: str
    title: str                             # what the user wants, in their words
    subtitle: str
    icon: str
    minutes: int                           # honest time cost, shown on the tile
    steps: list[Step]
    audience: str = "everyone"             # everyone | investor | desk

    def as_dict(self, with_steps: bool = True) -> dict[str, Any]:
        out = {"id": self.id, "title": self.title, "subtitle": self.subtitle,
               "icon": self.icon, "minutes": self.minutes, "audience": self.audience,
               "step_count": len(self.steps)}
        if with_steps:
            out["steps"] = [s.as_dict() for s in self.steps]
        return out


# --------------------------------------------------------------------------- the jobs
FLOWS: dict[str, Flow] = {}


def _register(flow: Flow) -> Flow:
    FLOWS[flow.id] = flow
    return flow


_register(Flow(
    id="health_check",
    title="Check my portfolio's health",
    subtitle="A three-minute read on what you own and what could go wrong with it",
    icon="pulse",
    minutes=3,
    steps=[
        Step("say", "Let me look at what you own. I will go through three things: how "
                    "it is spread out, what it has already survived, and what would "
                    "happen if things went badly."),
        Step("show", "Here is the shape of it. The grade is measured against the limits "
                     "you chose, not against anyone else's portfolio.",
             panel="xray", endpoint="/xray"),
        Step("ask", "First, how spread out you really are.",
             question="Am I diversified?", panel="xray"),
        Step("show", "This is what the basket did through the worst windows we have "
                     "prices for. These are facts about your holdings, not forecasts.",
             panel="stress", endpoint="/stress"),
        Step("ask", "And the honest summary.", question="Why is my risk high?"),
        Step("done", "That is the health check. If anything above bothered you, the "
                     "action list on the left has the fix for each one.",
             panel="actions"),
    ],
))

_register(Flow(
    id="fix_finding",
    title="Fix a problem you told me about",
    subtitle="Turn one finding into a concrete, costed set of trades",
    icon="wrench",
    minutes=4,
    steps=[
        Step("say", "We will fix one thing properly rather than everything vaguely. "
                    "First, what is actually wrong."),
        Step("show", "This is the finding and the number behind it.",
             panel="xray", endpoint="/xray"),
        Step("ask", "Here is the smallest change that resolves it.",
             question="What should I sell?", panel="rebalance"),
        Step("choose", "Three ways to go. None of them is wrong — they cost different "
                       "things.",
             options=[
                 {"key": "minimal", "label": "Sell just enough",
                  "consequence": "Smallest trade, smallest tax bill. You stay close to "
                                 "the limit, so a price move can put you back over it.",
                  "endpoint": "/rebalance?deploy=false"},
                 {"key": "full", "label": "Rebalance properly",
                  "consequence": "More trading and more tax, but it puts real distance "
                                 "between you and every limit.",
                  "endpoint": "/rebalance?deploy=true"},
                 {"key": "nothing", "label": "Do nothing for now",
                  "consequence": "Perfectly valid. The finding stays on your list and "
                                 "I will keep raising it.",
                  "endpoint": None},
             ]),
        Step("show", "Here is what that costs, including the tax where I know what you "
                     "paid.", panel="rebalance", endpoint="/rebalance"),
        Step("confirm", "I can stage these trades so you can see the portfolio they "
                        "produce before anything is committed.",
             note="Staging changes nothing. You will see before and after side by side "
                  "and can throw it away."),
        Step("done", "Done. The finding should be gone from your action list.",
             panel="actions"),
    ],
))

_register(Flow(
    id="should_i_buy",
    title="Decide whether to buy something",
    subtitle="Run a name past the desks, the limits and your own portfolio",
    icon="search",
    minutes=5,
    steps=[
        Step("say", "Tell me the company and I will do three things: check it against "
                    "your limits, look at what it overlaps with, and put it to the "
                    "research desks."),
        Step("ask", "First, whether it even fits.", question="Should I buy more of it?"),
        Step("show", "This is what it would overlap with. Two stocks that move together "
                     "are one bet wearing two names.",
             panel="correlation", endpoint="/correlation"),
        Step("show", "Now the desks. Four of them argue, a red team argues back, and "
                     "any claim without a citation is thrown away before you see it.",
             panel="desks", endpoint=None,
             note="This takes about fifteen seconds and runs entirely on your machine."),
        Step("say", "Read the conviction number with the calibration record next to it. "
                    "These desks have historically scored worse than a coin flip, and "
                    "the product tells you that rather than hiding it."),
        Step("done", "Whatever you decide, the risk firewall still checks the size "
                     "before anything is staged.", panel="actions"),
    ],
))

_register(Flow(
    id="tax_plan",
    title="Get ready for tax season",
    subtitle="What selling would cost, and what waiting would save",
    icon="receipt",
    minutes=4,
    audience="investor",
    steps=[
        Step("say", "Tax changes which trade is the right trade. Let me show you where "
                    "you stand before you sell anything."),
        Step("show", "These are the purchases I know about. Anything missing is a gap I "
                     "will not guess at.", panel="lots", endpoint="/lots"),
        Step("show", "Here is what your current plan would cost in tax, line by line.",
             panel="tax", endpoint="/rebalance"),
        Step("say", "Two rates matter. Under a year, gains are taxed at 20%. Past a "
                    "year, 12.5%, and the first ₹1.25 lakh of long-term gains each year "
                    "is exempt. The gap between those is often worth waiting for."),
        Step("choose", "Where there is a holding close to the one-year mark:",
             options=[
                 {"key": "wait", "label": "Wait for the lower rate",
                  "consequence": "You keep the market risk for a few more weeks and pay "
                                 "the lower rate at the end of it.", "endpoint": None},
                 {"key": "sell", "label": "Sell now anyway",
                  "consequence": "You take the higher rate but remove the risk today. "
                                 "Sometimes that is the better trade.", "endpoint": None},
             ]),
        Step("done", "Nothing here is tax advice. It is arithmetic on the rates, with "
                     "every input shown.", panel="actions"),
    ],
))

_register(Flow(
    id="stress_test",
    title="See what happens if it goes wrong",
    subtitle="Real crashes, replayed against the exact basket you hold",
    icon="storm",
    minutes=3,
    steps=[
        Step("say", "I am going to take your current share counts and run them through "
                    "windows that actually happened. No models, no assumptions."),
        Step("show", "Every one of these is a real window with real prices.",
             panel="stress", endpoint="/stress"),
        Step("ask", "The one people ask about first.",
             question="What happened in Covid?"),
        Step("say", "Worth saying plainly: coverage matters. Where a holding had not "
                    "listed yet, I say so rather than quietly filling the gap."),
        Step("ask", "And the number that decides whether you would have sold at the "
                    "bottom.", question="What is my worst case?"),
        Step("done", "If those numbers are bigger than you are comfortable with, that is "
                     "a position-sizing decision, not a forecasting one.",
             panel="actions"),
    ],
))

_register(Flow(
    id="deploy_cash",
    title="Put idle cash to work",
    subtitle="Where new money can go without making an existing problem worse",
    icon="coins",
    minutes=4,
    steps=[
        Step("say", "Cash is the only position with no downside and no upside. Let me "
                    "find where it could go without concentrating you further."),
        Step("show", "These names are the least correlated with what you already own — "
                     "the ones that actually add something.",
             panel="screener", endpoint="/screen/diversifiers"),
        Step("show", "And here is what buying into your existing names would do to the "
                     "limits.", panel="xray", endpoint="/xray"),
        Step("confirm", "I can stage a deployment that respects every limit.",
             note="Buys are sized at 95% of the available headroom so trading costs "
                  "cannot push the result back over the line."),
        Step("done", "Staged, not executed. Nothing moves until you commit it.",
             panel="actions"),
    ],
))

_register(Flow(
    id="rebalance",
    title="Rebalance the whole portfolio",
    subtitle="The smallest set of trades that brings everything inside its limits",
    icon="scales",
    minutes=5,
    audience="desk",
    steps=[
        Step("say", "There are many ways to fix a portfolio. I look for the one that "
                    "moves the least money, because every trade costs something."),
        Step("show", "Here is where you are now against every limit.",
             panel="xray", endpoint="/xray"),
        Step("show", "And the plan. Each line says why that trade exists.",
             panel="rebalance", endpoint="/rebalance"),
        Step("show", "The same plan, costed for tax where I know your purchase price.",
             panel="tax", endpoint="/rebalance"),
        Step("confirm", "Stage the plan and compare the portfolio it produces against "
                        "the one you have.",
             note="You will see both side by side before anything commits."),
        Step("done", "Compliant on every limit, or I will tell you which one it could "
                     "not reach and why.", panel="actions"),
    ],
))

_register(Flow(
    id="add_basis",
    title="Add what you paid",
    subtitle="Purchase prices unlock every tax number in the product",
    icon="tag",
    minutes=3,
    audience="investor",
    steps=[
        Step("say", "I can see what you own but not what you paid for it. Cost basis is "
                    "something only you know, and I will never guess it."),
        Step("show", "These are the holdings with no purchase price on file.",
             panel="lots", endpoint="/lots"),
        Step("say", "An approximate date is far better than nothing. The rate depends "
                    "only on whether you crossed one year."),
        Step("done", "With those in, the tax panel and the holding-period countdowns "
                     "start working.", panel="tax"),
    ],
))

_register(Flow(
    id="onboarding",
    title="Set this up for my money",
    subtitle="Three questions, then everything here is about your portfolio",
    icon="spark",
    minutes=2,
    steps=[
        Step("say", "Right now you are looking at an example. Three questions and it "
                    "becomes yours.", speak=True),
        Step("show", "Add what you own. Paste it, pick from the list, or start from a "
                     "portfolio that looks like yours.",
             panel="builder", endpoint="/portfolios"),
        Step("choose", "How much risk are you actually willing to carry?",
             options=[
                 {"key": "retail", "label": "I am investing my own savings",
                  "consequence": "Limits of 15% in one stock, 35% in one industry, 5% "
                                 "kept in cash.", "endpoint": "/profiles/retail"},
                 {"key": "balanced", "label": "I want to be a bit stricter",
                  "consequence": "10% in one stock, 35% in one industry, 8% cash.",
                  "endpoint": "/profiles/balanced"},
                 {"key": "fund", "label": "Hold me to institutional limits",
                  "consequence": "5% in one stock, 30% in one industry, 10% cash. Most "
                                 "private portfolios fail these badly.",
                  "endpoint": "/profiles/fund"},
             ]),
        Step("show", "Here is your portfolio, measured against the limits you just "
                     "picked.", panel="xray", endpoint="/xray"),
        Step("done", "That is it. The list on the left is now about your money.",
             panel="actions"),
    ],
))


# --------------------------------------------------------------------------- lookup
def localize(d: dict[str, Any], lang: str) -> dict[str, Any]:
    """Overlay the hand-written Hindi wording on a flow (or tile) dict. Anything without a Hindi
    entry keeps its English, so a flow added later still works before it is translated."""
    if lang != "hi":
        return d
    from backend.flows_hi import FLOWS_HI
    hi = FLOWS_HI.get(d["id"])
    if not hi:
        return d
    out = dict(d, title=hi["title"], subtitle=hi["subtitle"], lang="hi")
    if "steps" in d:
        steps = []
        for i, st in enumerate(d["steps"]):
            h = hi["steps"][i] if i < len(hi["steps"]) else {}
            st = dict(st)
            if h.get("text"):
                st["text"] = h["text"]
            if h.get("note"):
                st["note"] = h["note"]
            if h.get("options"):
                st["options"] = [dict(o, label=ho["label"], consequence=ho["consequence"])
                                 for o, ho in zip(st["options"], h["options"])]
            steps.append(st)
        out["steps"] = steps
    return out


def listing(audience: str | None = None, lang: str = "en") -> list[dict[str, Any]]:
    """Tiles for the launcher, without dragging every step over the wire."""
    flows = FLOWS.values()
    if audience and audience != "everyone":
        flows = [f for f in flows if f.audience in ("everyone", audience)]
    return [localize(f.as_dict(with_steps=False), lang) for f in flows]


def get(flow_id: str) -> Flow | None:
    return FLOWS.get(flow_id)
