"""Plain-language answers. Computed numbers, templated words.

The rule that makes this both simple AND accurate: **the model never produces a number.**
Every figure in every answer is computed in Python from the snapshot; the templates only
decide how to say it. That is why the answers can be phrased for someone with no finance
background without becoming vague — simplicity is a writing problem here, not a
modelling one.

Writing rules, applied deliberately:
  - Lead with the answer, not the method.
  - One idea per sentence. No sentence over about 20 words.
  - Money in rupees with Indian grouping (lakh/crore), never "1.2e6".
  - No jargon without an immediate gloss. "Beta" becomes "how much you move when the
    market moves", every time, not once.
  - Say what it means for the person, not what the metric is called.

Every answer carries `detail` for the expert view, so simplifying the headline never
costs the underlying number.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from analysis import factors, stress, xray
from core import universe
from core.pit import PointInTimeStore
from risk.policy import Policy
from risk.portfolio import Portfolio


# --------------------------------------------------------------------------- money
def rupees(amount: float) -> str:
    """Indian conventions, because the audience is Indian and '₹1,200,000' reads wrong."""
    a = abs(amount)
    sign = "-" if amount < 0 else ""
    if a >= 1_00_00_000:
        return f"{sign}₹{a / 1_00_00_000:.2f} crore"
    if a >= 1_00_000:
        return f"{sign}₹{a / 1_00_000:.2f} lakh"
    if a >= 1_000:
        return f"{sign}₹{a:,.0f}"
    return f"{sign}₹{a:.0f}"


def pct(x: float) -> str:
    return f"{x * 100:.0f}%"


# --------------------------------------------------------------------------- glossary
GLOSSARY: dict[str, str] = {
    "beta": "How much your portfolio moves when the market moves. A beta of 1.2 means "
            "that when the market drops 10%, you have tended to drop about 12%.",
    "drawdown": "The worst fall from a high point to a low point. It is the loss you "
                "would have lived through if you bought at the worst moment.",
    "volatility": "How much your value jumps around day to day. Higher means a bumpier "
                  "ride, not necessarily a worse outcome.",
    "sector": "A group of companies in the same business. Banks are one sector, "
              "technology another. Companies in a sector tend to rise and fall together.",
    "sector cap": "A limit on how much of your money can sit in one industry. It exists "
                  "because companies in the same industry fall together.",
    "concentration": "How much of your money sits in a few places. High concentration "
                     "means one bad result hurts a lot.",
    "nav": "The total value of everything you own, including cash.",
    "cash buffer": "Money kept aside, not invested. It lets you buy when prices fall "
                   "instead of having to sell something first.",
    "hhi": "A concentration measure. We show it as 'effective holdings' instead: how "
           "many positions you really have, once the big ones are accounted for.",
    "effective holdings": "How many positions you really have. If one stock is 60% of "
                          "your money, holding twenty names still behaves like holding two.",
    "brier score": "A score for how well-calibrated a prediction is. Lower is better. "
                   "0.25 is what you get by always saying 'a coin flip'.",
    "point in time": "Only using information that existed on a chosen date. It stops a "
                     "test from cheating by peeking at what happened next.",
    "groupthink": "When every analyst agrees. Because they all read the same evidence "
                  "with the same model, agreement does not mean they are right.",
    "conviction": "How strongly the system believes its own view, after discounting for "
                  "weak evidence and for everyone agreeing with each other.",
    "paper trading": "Practice trades. Nothing is bought or sold, and no real money "
                     "moves.",
}


@dataclass
class Answer:
    headline: str
    bullets: list[str] = field(default_factory=list)
    action: str | None = None
    detail: str | None = None
    kind: str = "general"
    data: dict[str, Any] = field(default_factory=dict)
    # Where to go next. An answer with no exit leaves the user exactly where the panel
    # wall left them: holding a fact and no idea what to do with it.
    follow_ups: list[str] = field(default_factory=list)
    level: str = "normal"                # normal | simple | maths
    subject: str | None = None           # the ticker this answer was about, if any

    def spoken(self) -> str:
        """What JARVIS says aloud. Headline plus at most two supporting facts --
        a spoken paragraph of six bullets is unlistenable."""
        parts = [self.headline, *self.bullets[:2]]
        if self.action:
            parts.append(self.action)
        return " ".join(parts)

    def as_dict(self) -> dict[str, Any]:
        return {"headline": self.headline, "bullets": self.bullets,
                "action": self.action, "detail": self.detail, "kind": self.kind,
                "data": self.data, "follow_ups": self.follow_ups,
                "level": self.level, "subject": self.subject}


# --------------------------------------------------------------------------- router
QUESTIONS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(what|how).{0,20}\b(is|are|does|do)\b.{0,30}\b(mean|beta|drawdown|"
                r"volatility|sector cap|concentration|nav|brier|groupthink|conviction|"
                r"point in time|paper trading|cash buffer)\b", re.I), "define"),
    (re.compile(r"\b(what if|if the market|crash|stress|worst case|downturn|falls?)\b", re.I),
     "stress"),
    (re.compile(r"\b(what|which).{0,20}\b(sell|trim|reduce|fix|do about|should i do)\b", re.I),
     "fix"),
    (re.compile(r"\b(why|what).{0,25}\b(risk|risky|wrong|concern|problem|bad|score|grade)\b",
                re.I), "why"),
    (re.compile(r"\b(how am i doing|how is my|health|x-?ray|check my|review my|summar)", re.I),
     "xray"),
    # Correlation questions must be caught BEFORE the diversification rule: "what does
    # it move with" is about one pair, not about the shape of the whole book. This also
    # exists because the follow-up chips offer exactly this question -- a suggested
    # question with no answer behind it is worse than no suggestion at all.
    (re.compile(r"\b(move[sd]?\s+(?:with|together|in step)|correlat|same\s+bet|"
                r"overlap|duplicat|go(?:es)?\s+up\s+and\s+down\s+with)\b", re.I),
     "correlation"),
    (re.compile(r"\b(diversif|spread|concentrat)", re.I), "diversification"),
    # "Should I buy X" is the commonest question a private investor asks, and it was
    # falling through to a generic summary. Placed before the covid/stress rule so
    # "should I buy more TCS" is not captured by an unrelated keyword.
    # Gerunds matter: "is it worth adding ONGC" is the same question as "should I add
    # ONGC", and a bare \b(add)\b misses it.
    (re.compile(r"\b(should|shall|can|could|would|worth)\b.{0,30}"
                r"\b(buy(?:ing)?|add(?:ing)?|get(?:ting)?|invest(?:ing)?|"
                r"pick(?:ing)?\s*up|top(?:ping)?\s*up)\b", re.I), "should_buy"),
    (re.compile(r"\b(covid|2020|2022|crash of|back then)\b", re.I), "stress"),
    (re.compile(r"\b(explain|simpler|simply|plain english|don'?t understand|eli5)\b", re.I),
     "simplify"),
]


def classify(text: str) -> str:
    for rx, kind in QUESTIONS:
        if rx.search(text):
            return kind
    return "xray"


# --------------------------------------------------------------- conversation memory
# Anything that reads as "the thing we were just discussing". Without this, every
# question has to name its subject again, which is not how anybody talks: the natural
# second question after "should I buy Infosys" is "and what does it correlate with",
# and that used to resolve to nothing.
PRONOUN = re.compile(r"\b(it|that|this|them|those|the same|there)\b", re.I)

# Phrasings that only make sense as a continuation of the previous answer.
CONTINUATION = re.compile(
    r"^\s*(and|what about|how about|why|ok(?:ay)?(?:,)?\s+(?:and|but|so)|"
    r"so\b|then\b|what if i)\b", re.I)


@dataclass
class Conversation:
    """What was just said, so the next sentence does not have to repeat it.

    Deliberately tiny: the last subject and the last answer kind. A full dialogue state
    machine would be a week of work and would mostly be wrong; these two fields cover
    the overwhelming majority of real follow-ups.
    """
    last_ticker: str | None = None
    last_kind: str | None = None
    last_headline: str | None = None
    turns: int = 0

    def resolve(self, text: str) -> str:
        """Substitute the remembered subject into a pronoun, when one is needed.

        Only rewrites when the sentence has a pronoun AND no company of its own -- a
        question that names a different company must never be hijacked by memory.
        """
        from backend.intents import resolve_ticker
        if not self.last_ticker:
            return text
        if resolve_ticker(text):
            return text
        if PRONOUN.search(text) or CONTINUATION.match(text):
            name = universe.name(self.last_ticker)
            return PRONOUN.sub(name, text, count=1) if PRONOUN.search(text) \
                else f"{text} {name}"
        return text

    def remember(self, answer: "Answer") -> None:
        self.turns += 1
        self.last_kind = answer.kind
        self.last_headline = answer.headline
        if answer.subject:
            self.last_ticker = answer.subject

    def as_dict(self) -> dict[str, Any]:
        return {"last_ticker": self.last_ticker, "last_kind": self.last_kind,
                "turns": self.turns}


# ------------------------------------------------------------------------ follow-ups
# Two or three next moves per answer kind. These are the single cheapest way to stop a
# user having to invent the next question -- which is the point at which most people
# put the tool down.
FOLLOW_UPS: dict[str, list[str]] = {
    "xray": ["Why is my risk high?", "Am I diversified?",
             "What if the market drops 20%?"],
    "why": ["What should I sell?", "How much would that cost me in tax?",
            "What if I do nothing?"],
    "fix": ["What would that cost me in tax?", "Show me the full rebalance plan",
            "What if I do nothing?"],
    "diversification": ["What should I buy to spread out?", "What moves together?",
                        "Why is my risk high?"],
    "stress": ["What should I sell?", "What happened in Covid?",
               "Am I diversified?"],
    "should_buy": ["What does it move with?", "What should I sell to make room?",
                   "Find me something that spreads me out"],
    "define": ["How am I doing?", "Why is my risk high?"],
    "empty": ["Load an example portfolio", "How am I doing?"],
    "general": ["How am I doing?", "Why is my risk high?", "What should I sell?"],
}


def follow_ups_for(answer: Answer, report: xray.XRay | None = None) -> list[str]:
    """Next moves, specialised by what the answer actually found.

    A static list per kind is already useful; making it react to the finding is what
    makes it feel like the system is paying attention. If the answer just said
    technology is 48%, the obvious next question mentions technology.
    """
    base = list(FOLLOW_UPS.get(answer.kind, FOLLOW_UPS["general"]))

    if answer.kind in ("why", "xray") and report and report.findings:
        worst = next((f for f in report.findings
                      if f.severity in ("high", "medium")), None)
        if worst and worst.code == "SECTOR_CONCENTRATION" and report.top_sector:
            label = universe.sector_label(report.top_sector[0]).lower()
            base.insert(0, f"What if {label} falls 30%?")
        elif worst and worst.code == "POSITION_CONCENTRATION" and report.top_holding:
            base.insert(0, f"Should I sell some {universe.name(report.top_holding[0])}?")
        elif worst and worst.code == "LOW_CASH":
            base.insert(0, "How much cash should I keep?")

    if answer.kind == "should_buy" and answer.subject:
        name = universe.name(answer.subject)
        base = [f"What does {name} move with?",
                "What should I sell to make room?",
                "Find me something that spreads me out"]

    # Never repeat the question that was just asked back at the user.
    asked = (answer.headline or "").lower()
    out = [q for q in base if q.lower()[:24] not in asked]
    seen: set[str] = set()
    unique = [q for q in out if not (q.lower() in seen or seen.add(q.lower()))]
    return unique[:3]


# ------------------------------------------------------------------- explain-back
def simplify(answer: Answer) -> Answer:
    """The same truth, shorter and with the qualifiers removed.

    This is the "I did not understand that" path. The temptation is to make it vaguer,
    which is the opposite of helpful -- what people need is fewer clauses and no
    subordinate detail, with the number still in it.
    """
    head = answer.headline
    # Drop everything after the first em-dash or semicolon: those clauses are always
    # the qualification, never the answer.
    head = re.split(r"\s+[—;]\s+", head)[0].strip()
    if not head.endswith("."):
        head += "."
    kept = answer.bullets[:1]
    return Answer(
        headline=head,
        bullets=kept,
        action="Ask me to show the maths if you want the workings.",
        detail=answer.detail, kind=answer.kind, data=answer.data,
        follow_ups=answer.follow_ups, level="simple", subject=answer.subject)


def with_maths(answer: Answer) -> Answer:
    """Everything, including the workings. The opposite end of the same dial."""
    bullets = list(answer.bullets)
    if answer.detail:
        bullets.append(answer.detail)
    bullets.append("Every number here is computed in Python from the snapshot at the "
                   "current clock. The language model never produces a figure — it only "
                   "chooses how to phrase one.")
    return Answer(
        headline=answer.headline, bullets=bullets, action=answer.action,
        detail=answer.detail, kind=answer.kind, data=answer.data,
        follow_ups=answer.follow_ups, level="maths", subject=answer.subject)


def define(text: str) -> Answer | None:
    low = text.lower()
    for term in sorted(GLOSSARY, key=len, reverse=True):
        if term in low:
            return Answer(headline=GLOSSARY[term], kind="define",
                          detail=f"Term: {term}")
    return None


# --------------------------------------------------------------------------- answers
def answer(text: str, pit: PointInTimeStore, portfolio: Portfolio,
           prices: dict[str, float], policy: Policy,
           convo: Conversation | None = None, level: str = "normal") -> Answer:
    """One question in, one plain-language answer out.

    `convo` lets a follow-up refer back ("what does it move with") without naming its
    subject again. `level` is the explain-back dial: the same answer, said shorter or
    said with the workings shown.
    """
    # Resolve pronouns BEFORE classifying: "and what about it" classifies very
    # differently once "it" has become "Infosys".
    resolved = convo.resolve(text) if convo else text
    kind = classify(resolved)

    if kind == "simplify" and convo and convo.last_kind:
        # "explain that simpler" is not a new question, it is the same one at a
        # different level. Re-run the previous kind rather than falling to a summary.
        kind = convo.last_kind
        level = "simple"

    if kind == "define":
        if (a := define(resolved)):
            a.follow_ups = follow_ups_for(a)
            return _leveled(a, level, convo)
        kind = "xray"

    if not portfolio.positions:
        empty = Answer(
            headline="You have not added any holdings yet.",
            bullets=["Add what you own, or load one of the example portfolios, and I "
                     "can tell you where your risk is."],
            kind="empty")
        empty.follow_ups = follow_ups_for(empty)
        return empty

    report = xray.analyse(pit, portfolio, prices, policy)

    if kind == "stress":
        out = _stress_answer(resolved, pit, portfolio, prices, report)
    elif kind == "fix":
        out = _fix_answer(report, portfolio, prices, policy)
    elif kind == "why":
        out = _why_answer(report)
    elif kind == "diversification":
        out = _diversification_answer(report, portfolio, prices)
    elif kind == "correlation":
        out = _correlation_answer(resolved, pit, portfolio, prices)
    elif kind == "should_buy":
        out = _should_buy_answer(resolved, pit, report, portfolio, prices, policy)
    else:
        out = _xray_answer(report)

    if not out.subject:
        out.subject = out.data.get("ticker")
    out.follow_ups = follow_ups_for(out, report)
    return _leveled(out, level, convo)


def _leveled(out: Answer, level: str, convo: Conversation | None) -> Answer:
    if level == "simple":
        out = simplify(out)
    elif level == "maths":
        out = with_maths(out)
    if convo:
        convo.remember(out)
    return out


def _grade_sentence(report: xray.XRay) -> str:
    return {
        "A": "Your portfolio looks well spread out.",
        "B": "Your portfolio is in reasonable shape, with one or two things to watch.",
        "C": "Your portfolio is more concentrated than is comfortable.",
        "D": "Your portfolio is heavily concentrated and would be hit hard by one bad sector.",
        "E": "Your portfolio is very concentrated. One bad year in one industry could "
             "do serious damage.",
    }[report.grade]


def _xray_answer(report: xray.XRay) -> Answer:
    bullets = [f"You hold {rupees(report.nav)} across {report.holdings} stocks in "
               f"{report.sectors} industries."]
    if report.top_sector:
        code, w = report.top_sector
        bullets.append(f"Your biggest industry is {universe.sector_label(code).lower()} "
                       f"at {pct(w)} of your money.")
    if report.effective_holdings < report.holdings * 0.7:
        bullets.append(f"You own {report.holdings} stocks, but because a few are much "
                       f"bigger than the rest it behaves like about "
                       f"{report.effective_holdings:.0f}.")
    if report.max_drawdown:
        bullets.append(f"This mix has fallen {pct(abs(report.max_drawdown))} from a "
                       f"high point before, on the history we hold.")

    high = [f for f in report.findings if f.severity == "high"]
    action = (f"The thing to fix first: {high[0].headline.lower()}." if high else None)
    return Answer(
        headline=f"{_grade_sentence(report)} I score it {report.score} out of 100 "
                 f"against {report.profile_name.lower()} limits — "
                 f"{report.limits_describe}.",
        bullets=bullets, action=action, kind="xray",
        detail=(f"HHI {report.hhi:.3f} · effective holdings "
                f"{report.effective_holdings:.1f} · annualised volatility "
                f"{pct(report.volatility_annual) if report.volatility_annual else 'n/a'} "
                f"· beta {report.beta if report.beta else 'n/a'} vs "
                f"{universe.benchmark_label()}"),
        data=report.as_dict())


def _why_answer(report: xray.XRay) -> Answer:
    ranked = [f for f in report.findings if f.severity in ("high", "medium")]
    if not ranked:
        return Answer(headline="Nothing in your portfolio breaches your limits right now.",
                      bullets=[f.detail for f in report.findings[:1]],
                      kind="why", data=report.as_dict())
    worst = ranked[0].severity
    lead = ("Two things stand out." if len(ranked) == 2 else
            f"{len(ranked)} things stand out." if len(ranked) > 2 else
            "One thing stands out.")
    return Answer(
        headline=f"{lead} " + ("None of it is severe, but it is worth knowing."
                               if worst != "high" else
                               "The first one is the serious one."),
        bullets=[f"{f.headline}. {f.detail}" for f in ranked[:3]],
        action="Ask me what to sell and I will work out the smallest change that fixes it.",
        kind="why",
        detail="Findings ranked by severity: " + ", ".join(f.code for f in ranked),
        data=report.as_dict())


def _fix_answer(report: xray.XRay, portfolio: Portfolio, prices: dict[str, float],
                policy: Policy) -> Answer:
    """Concrete, smallest-change remediation -- computed, not suggested."""
    lim = policy.limits
    nav = portfolio.nav(prices)
    weights = portfolio.weights(prices)

    trims: list[tuple[str, int, float, str]] = []
    for ticker, w in sorted(weights.items(), key=lambda kv: -kv[1]):
        price = prices.get(ticker, 0.0)
        if not price or w <= lim.max_position_pct:
            continue
        target_value = lim.max_position_pct * nav
        excess = portfolio.positions[ticker] * price - target_value
        shares = int(excess // price)
        if shares > 0:
            trims.append((ticker, shares, shares * price, "single-stock limit"))

    sectors: dict[str, float] = {}
    for ticker, w in weights.items():
        sectors[universe.sector(ticker)] = sectors.get(universe.sector(ticker), 0.0) + w
    for code, w in sorted(sectors.items(), key=lambda kv: -kv[1]):
        if w <= lim.max_sector_pct:
            continue
        excess_value = (w - lim.max_sector_pct) * nav
        # Trim the largest holding in the offending sector first: it is the one doing
        # the most damage and the fewest trades fix it.
        in_sector = sorted(((t, weights[t]) for t in weights
                            if universe.sector(t) == code), key=lambda kv: -kv[1])
        for ticker, _ in in_sector:
            if excess_value <= 0:
                break
            price = prices.get(ticker, 0.0)
            if not price:
                continue
            already = sum(s for t, s, _, _ in trims if t == ticker)
            available = portfolio.positions[ticker] - already
            shares = min(available, int(excess_value // price) + 1)
            if shares > 0:
                trims.append((ticker, shares, shares * price,
                              f"{universe.sector_label(code).lower()} limit"))
                excess_value -= shares * price

    if not trims:
        return Answer(
            headline="Nothing needs selling. You are inside every limit.",
            bullets=[f"Your largest position is "
                     f"{pct(max(weights.values())) if weights else '0%'} and your cash "
                     f"buffer is {pct(portfolio.cash / nav)}."],
            kind="fix", data=report.as_dict())

    merged: dict[str, tuple[int, float, str]] = {}
    for ticker, shares, value, why in trims:
        s, v, w = merged.get(ticker, (0, 0.0, why))
        merged[ticker] = (s + shares, v + value, w)

    total = sum(v for _, v, _ in merged.values())
    bullets = [f"Sell {shares} {universe.name(t)} — about {rupees(value)} — to get "
               f"under the {why}."
               for t, (shares, value, why) in
               sorted(merged.items(), key=lambda kv: -kv[1][1])]
    return Answer(
        headline=f"Selling about {rupees(total)} across {len(merged)} "
                 f"{'holding' if len(merged) == 1 else 'holdings'} would bring you "
                 f"inside every limit.",
        bullets=bullets,
        action="That money goes to cash. You do not have to buy anything with it today.",
        kind="fix",
        detail="Computed as the smallest reduction that clears each breached cap, "
               "largest offender first.",
        data={"trims": [{"ticker": t, "name": universe.name(t), "shares": s,
                         "value": v, "reason": w}
                        for t, (s, v, w) in merged.items()],
              "total": total})


def _diversification_answer(report: xray.XRay, portfolio: Portfolio,
                            prices: dict[str, float]) -> Answer:
    weights = portfolio.weights(prices)
    sectors: dict[str, float] = {}
    for ticker, w in weights.items():
        sectors[universe.sector(ticker)] = sectors.get(universe.sector(ticker), 0.0) + w
    ranked = sorted(sectors.items(), key=lambda kv: -kv[1])
    missing = [s for s in universe.sector_names() if s not in sectors][:4]

    return Answer(
        headline=f"You own {report.holdings} stocks across {report.sectors} industries, "
                 f"but it behaves like about {report.effective_holdings:.0f} positions.",
        bullets=[f"Biggest: " + ", ".join(
                     f"{universe.sector_label(c).lower()} {pct(w)}" for c, w in ranked[:3]),
                 (f"You own nothing in " +
                  ", ".join(universe.sector_label(s).lower() for s in missing) + ".")
                 if missing else "You have at least something in every industry we cover."],
        action="Spreading into industries you do not own is usually cheaper than "
               "buying more of what you already hold.",
        kind="diversification",
        detail=f"HHI {report.hhi:.3f}; effective holdings = 1/HHI = "
               f"{report.effective_holdings:.1f}",
        data=report.as_dict())


def _correlation_answer(text: str, pit: PointInTimeStore, portfolio: Portfolio,
                        prices: dict[str, float]) -> Answer:
    """"What does it move with?" -- the question people ask second and understand least.

    Two stocks at 0.9 correlation are one bet wearing two names, and no amount of
    counting holdings reveals that. Named company gives the pairwise view; no company
    gives the whole book's worst pairs.
    """
    from backend.intents import resolve_ticker

    held = list(portfolio.positions)
    if len(held) < 2:
        return Answer(headline="You need at least two holdings before anything can "
                               "move together.", kind="correlation")

    matrix = factors.correlation_matrix(pit, held)
    weights = portfolio.weights(prices)
    ticker = resolve_ticker(text)

    if ticker and ticker in matrix:
        pairs = [(t, r) for t, r in matrix.get(ticker, {}).items()
                 if t != ticker and r is not None]
        if not pairs:
            return Answer(headline=f"I do not have enough overlapping history to say "
                                   f"what {universe.name(ticker)} moves with.",
                          kind="correlation", subject=ticker)
        pairs.sort(key=lambda kv: -kv[1])
        top = pairs[:3]
        worst_name, worst_r = top[0]
        close = [f"{universe.name(t)} ({r:.2f})" for t, r in top]
        verdict = ("almost the same bet" if worst_r >= 0.85 else
                   "very closely linked" if worst_r >= 0.7 else
                   "loosely linked" if worst_r >= 0.4 else
                   "largely independent")
        return Answer(
            headline=f"{universe.name(ticker)} moves most closely with "
                     f"{universe.name(worst_name)} — correlation {worst_r:.2f}, which "
                     f"is {verdict}.",
            bullets=["Closest three: " + ", ".join(close) + ".",
                     "A correlation of 1.0 means they move identically; 0 means they "
                     "move independently. Anything above about 0.7 means owning both "
                     "spreads your risk far less than it looks."],
            action=("Holding both is closer to holding one larger position than to "
                    "holding two." if worst_r >= 0.7 else
                    "These are genuinely separate bets, which is what you want."),
            kind="correlation", subject=ticker,
            detail=f"Pairwise Pearson correlation of daily returns to "
                   f"{pit.clock_iso[:10]}: " +
                   ", ".join(f"{t} {r:.3f}" for t, r in top),
            data={"ticker": ticker, "pairs": [{"ticker": t, "name": universe.name(t),
                                               "r": r} for t, r in top]})

    # No company named: report the worst pairs across the whole book.
    pairs = factors.correlated_pairs(matrix, weights)
    avg = factors.diversification_ratio(matrix, weights)
    if not pairs:
        return Answer(
            headline=f"Nothing you own moves unusually closely together. Average "
                     f"correlation across the book is {avg:.2f}.",
            bullets=["That means your holdings are genuinely separate bets rather than "
                     "one bet held several times."],
            kind="correlation", data={"avg_correlation": avg})

    lead = pairs[0]
    a, b = universe.name(lead["a"]), universe.name(lead["b"])
    return Answer(
        headline=f"{a} and {b} move almost in step — correlation "
                 f"{lead['correlation']:.2f}.",
        bullets=[f"Together they are {pct(lead.get('combined_weight', 0.0))} of your "
                 f"money, so that pair behaves like a single position of that size.",
                 f"Average correlation across everything you own is {avg:.2f}. "
                 f"Lower is better spread."]
        + ([f"Also closely linked: " + ", ".join(
            f"{universe.name(p['a'])}/{universe.name(p['b'])} ({p['correlation']:.2f})"
            for p in pairs[1:3]) + "."] if len(pairs) > 1 else []),
        action="Selling one of a closely linked pair usually spreads you out more than "
               "buying something new.",
        kind="correlation",
        detail=f"{len(pairs)} pairs above the reporting threshold; average pairwise "
               f"correlation {avg:.3f}.",
        data={"pairs": pairs, "avg_correlation": avg})


def _should_buy_answer(text: str, pit: PointInTimeStore, report: xray.XRay,
                       portfolio: Portfolio, prices: dict[str, float],
                       policy: Policy) -> Answer:
    """"Should I buy more X?" answered with what it would DO, not with a view.

    This system has no opinion on whether a stock will rise -- its own calibration
    panel says its desks are worse than a coin flip at that. What it can say precisely
    is what adding X does to your concentration and your correlation, which is the part
    a person cannot compute in their head and the part that actually bites.
    """
    # `universe.resolve` matches a symbol or a company NAME; it cannot find one inside
    # a sentence, so passing "should I buy more TCS" to it returned None and silently
    # fell back to the generic summary. `resolve_ticker` scans the text for an alias.
    from backend.intents import resolve_ticker

    ticker = resolve_ticker(text)
    if not ticker:
        return Answer(
            headline="Which company did you mean?",
            bullets=["Name it and I will tell you what adding it would do to your "
                     "concentration — for example, \"should I buy more Infosys\"."],
            kind="should_buy")

    lim = policy.limits
    nav = portfolio.nav(prices)
    price = prices.get(ticker) or 0.0
    held = portfolio.positions.get(ticker, 0)
    cur_w = held * price / nav if nav else 0.0
    sector = universe.sector(ticker)
    sec_w = portfolio.sector_value(sector, prices, universe.sectors()) / nav if nav else 0.0

    # What a typical top-up would do: 5% of the portfolio.
    add_value = nav * 0.05
    new_w = (held * price + add_value) / nav if nav else 0.0
    new_sec = sec_w + 0.05

    bullets = []
    if held:
        bullets.append(f"You already hold {universe.name(ticker)} at {pct(cur_w)} of "
                       f"your money, in {universe.sector_label(sector).lower()} which "
                       f"is {pct(sec_w)}.")
    else:
        bullets.append(f"You do not hold {universe.name(ticker)} today. It sits in "
                       f"{universe.sector_label(sector).lower()}, which is already "
                       f"{pct(sec_w)} of your money.")

    breaches = []
    if new_w > lim.max_position_pct:
        breaches.append(f"{universe.name(ticker)} would reach {pct(new_w)}, past your "
                        f"{pct(lim.max_position_pct)} single-stock limit")
    if new_sec > lim.max_sector_pct:
        breaches.append(f"{universe.sector_label(sector).lower()} would reach "
                        f"{pct(new_sec)}, past your {pct(lim.max_sector_pct)} limit")

    # Correlation to what is already owned is the non-obvious part.
    corr_note = None
    others = [t for t in portfolio.positions if t != ticker]
    if others:
        matrix = factors.correlation_matrix(pit, others + [ticker])
        pairs = [(t, matrix.get(ticker, {}).get(t)) for t in others]
        pairs = [(t, r) for t, r in pairs if r is not None]
        if pairs:
            worst = max(pairs, key=lambda kv: kv[1])
            if worst[1] >= 0.7:
                corr_note = (f"It moves almost in step with "
                             f"{universe.name(worst[0])} — correlation {worst[1]:.2f} — "
                             f"so it adds less spread than it looks.")

    if breaches:
        headline = (f"Adding about 5% more would break your own limits: "
                    f"{breaches[0]}.")
        action = ("I will not tell you whether it goes up — my desks score worse than "
                  "a coin flip at that. I can tell you this would concentrate you further.")
    else:
        headline = (f"Adding about 5% more keeps you inside every limit — "
                    f"{universe.name(ticker)} would be {pct(new_w)} and "
                    f"{universe.sector_label(sector).lower()} {pct(new_sec)}.")
        action = ("That is a statement about your concentration, not a view on the "
                  "price. Ask me to find diversifiers if you want the opposite effect.")

    if corr_note:
        bullets.append(corr_note)

    return Answer(headline=headline, bullets=bullets, action=action,
                  kind="should_buy",
                  detail=f"{ticker} at {price:,.2f}; position {pct(cur_w)} -> "
                         f"{pct(new_w)}, sector {pct(sec_w)} -> {pct(new_sec)}",
                  data={"ticker": ticker, "would_breach": bool(breaches)})


def _stress_answer(text: str, pit: PointInTimeStore, portfolio: Portfolio,
                   prices: dict[str, float], report: xray.XRay) -> Answer:
    # A named crisis in the question wins; a percentage falls back to a uniform shock.
    low = text.lower()
    chosen = None
    if "covid" in low or "2020" in low:
        chosen = stress.find("covid")
    elif "2022" in low or "rate" in low:
        chosen = stress.find("rate_shock_2022")
    elif (m := re.search(r"(\d{1,2})\s*%", low)):
        pct_drop = int(m.group(1))
        scope = "ALL"
        for code in universe.sector_names():
            if universe.sector_label(code).split(" ")[0].lower() in low or code.lower() in low:
                scope = code
                break
        if "tech" in low:
            scope = "IT"
        # Label by what is actually being shocked. Calling a technology-only shock
        # "Market falls 30%" made the headline contradict its own numbers.
        what = "The market" if scope == "ALL" else universe.sector_label(scope)
        chosen = {"key": "custom", "label": f"{what} falls {pct_drop}%",
                  "scope": scope, "shock": -pct_drop / 100}

    if chosen and "shock" in chosen:
        result = stress.run_hypothetical(portfolio, chosen, prices)
    elif chosen:
        result = stress.run_historical(pit, portfolio, chosen, prices)
    else:
        allr = stress.run_all(pit, portfolio, prices)
        if not allr["worst_case"]:
            return Answer(headline="I could not price your holdings in any of the "
                                   "stress windows.", kind="stress")
        w = allr["worst_case"]
        return Answer(
            headline=f"Your worst case in the scenarios I test is the "
                     f"{w['label'].lower()}: you would lose about "
                     f"{rupees(abs(w['value_change']))}.",
            bullets=[f"That is {pct(abs(w['portfolio_return']))} of your money, taking "
                     f"you from {rupees(w['nav_before'])} to {rupees(w['nav_after'])}.",
                     f"Hardest hit: " + ", ".join(n for n, _ in w["worst"][:3]) + "."],
            action="This is what actually happened to these companies in that window, "
                   "not a prediction.",
            kind="stress", detail=f"Coverage {pct(w['coverage'])} of NAV priced in window.",
            data=allr)

    bench = ""
    if result.benchmark_return is not None:
        diff = result.portfolio_return - result.benchmark_return
        bench = (f" The {universe.benchmark_label()} moved "
                 f"{pct(result.benchmark_return)}, so you would have done "
                 f"{'worse' if diff < 0 else 'better'} than the market by "
                 f"{pct(abs(diff))}.")

    verb = "lose" if result.portfolio_return < 0 else "gain"
    # Historical windows read as "In the Covid crash"; hypotheticals read as
    # "If technology falls 30%". Forcing both through one preposition produced
    # "In market falls 20%".
    opener = (f"In the {result.label.lower()}" if result.kind == "historical"
              else f"If {result.label[0].lower()}{result.label[1:]}")
    return Answer(
        headline=f"{opener}, you would {verb} about "
                 f"{rupees(abs(result.value_change))}.",
        bullets=[f"That is {pct(abs(result.portfolio_return))} of your money — "
                 f"{rupees(result.nav_before)} becomes {rupees(result.nav_after)}."
                 + bench] +
                ([f"Hardest hit: " + ", ".join(universe.name(t) for t, _ in result.worst[:3])
                  + "."] if result.worst else []),
        action=("Those are the real prices from that window." if result.kind == "historical"
                else "This is a what-if with the same fall applied to everything, not a "
                     "forecast."),
        kind="stress",
        detail=f"{result.kind}; coverage {pct(result.coverage)} of NAV priced.",
        data=result.as_dict())
