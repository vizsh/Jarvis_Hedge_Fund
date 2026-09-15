"""The Next Best Action queue: the app proposes, instead of waiting to be asked.

Every other panel in this product answers a question. That is only useful to someone
who already knows which question to ask, which is exactly the person who does not need
the product. This module inverts the direction: it reads the same snapshot every panel
reads, and produces a short ranked list of things worth *doing*, each one attached to
the flow that resolves it.

Ranking is deliberately not "severity, then alphabetical". Three things decide order:

  weight    how bad it is if ignored          (a breach beats a suggestion)
  stake     how much money is actually at risk (5% of a crore beats 5% of a lakh)
  urgency   whether a door is closing          (a tax deadline beats a standing breach)

The third term is the one people get wrong. A sector breach has been wrong for months
and will still be wrong next week; a holding that crosses into long-term capital gains
in nine days is a decision that expires. Sorting purely on severity buries the thing
you cannot do later underneath the thing you can.

Nothing here decides anything. Every action carries the flow that would resolve it and
the numbers behind it; a human still presses the button.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from analysis import rebalance as rebalance_mod
from analysis import stress as stress_mod
from analysis import tax as tax_mod
from analysis import xray as xray_mod
from core import universe
from core.pit import PointInTimeStore
from risk.policy import Policy
from risk.portfolio import Portfolio

# How much each class of finding counts before money and deadlines are applied.
WEIGHT = {"urgent": 100.0, "important": 60.0, "opportunity": 35.0, "ok": 5.0}

# A deadline inside this many days starts pulling an action up the list.
HORIZON_DAYS = 45.0

# Findings that describe the basket rather than break a rule. You cannot "fix" the fact
# that these holdings once fell 26%; you can only understand it and decide whether the
# number is one you are willing to sit through. Each maps to the flow that explains it.
INFORMATIONAL = {
    "DEEP_DRAWDOWN": "stress_test",
    "HIGH_BETA": "stress_test",
}


@dataclass
class Action:
    """One thing worth doing, phrased as an instruction rather than a statistic."""
    id: str
    severity: str                 # urgent | important | opportunity | ok
    title: str                    # plain English, imperative or plainly factual
    detail: str                   # one sentence of consequence
    why: str                      # why this matters at all -- the teaching line
    cta: str = "Show me"          # button label
    flow: str | None = None       # flow that resolves it
    question: str | None = None   # or, a question to put to the explainer
    stake: float = 0.0            # rupees exposed or saved
    deadline_days: int | None = None
    deadline_label: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    rank: float = 0.0

    def score(self) -> float:
        """Weight x money x closing-door.

        `stake` is scaled by the square root rather than used raw: a breach ten times
        larger matters more, but not ten times more, and without the damping a single
        large position drowns out every other action on the list.
        """
        base = WEIGHT.get(self.severity, 10.0)
        money = 1.0 + (max(self.stake, 0.0) ** 0.5) / 400.0
        urgency = 1.0
        if self.deadline_days is not None:
            urgency = 1.0 + max(0.0, HORIZON_DAYS - self.deadline_days) / HORIZON_DAYS
        return base * money * urgency

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, "severity": self.severity, "title": self.title,
                "detail": self.detail, "why": self.why, "cta": self.cta,
                "flow": self.flow, "question": self.question,
                "stake": round(self.stake, 2),
                "deadline_days": self.deadline_days,
                "deadline_label": self.deadline_label,
                "data": self.data, "rank": round(self.rank, 2)}


# --------------------------------------------------------------------------- helpers
def _rupees(amount: float) -> str:
    a = abs(amount)
    if a >= 1_00_00_000:
        return f"₹{a / 1_00_00_000:.2f} crore"
    if a >= 1_00_000:
        return f"₹{a / 1_00_000:.2f} lakh"
    return f"₹{a:,.0f}"


def _pct(x: float) -> str:
    return f"{x * 100:.0f}%"


# --------------------------------------------------------------------------- sources
def _from_xray(report: xray_mod.XRay, policy: Policy) -> list[Action]:
    """Turn X-ray findings into things to do.

    The X-ray already says what is wrong in plain language. What it never said is what
    to do about it, so every finding here gains a flow and a call to action.
    """
    out: list[Action] = []
    limits = policy.limits

    for f in report.findings:
        if f.severity == "good":
            continue
        # Money genuinely exposed by this finding, not the whole portfolio.
        stake = 0.0
        if f.code in ("SECTOR_CONCENTRATION", "POSITION_CONCENTRATION") and f.metric:
            over = max(0.0, f.metric - (limits.max_sector_pct
                                        if "SECTOR" in f.code else limits.max_position_pct))
            stake = over * report.nav
        elif f.metric:
            stake = abs(f.metric) * report.nav * 0.1

        severity = "urgent" if f.severity == "high" else "important"
        # Some findings are facts about the basket rather than breaches you can trade
        # your way out of. Offering "Fix this" next to "it fell 26% once" promises
        # something the product cannot deliver, so those get an explanation instead.
        if f.code in INFORMATIONAL:
            out.append(Action(
                id=f"xray:{f.code}",
                severity="opportunity",
                title=f.headline,
                detail=f.detail,
                why=_why_for(f.code),
                cta="What does that mean?",
                flow=INFORMATIONAL[f.code],
                stake=stake * 0.3,
                data={"code": f.code, "metric": f.metric, "source": "xray"},
            ))
            continue
        out.append(Action(
            id=f"xray:{f.code}",
            severity=severity,
            title=f.headline,
            detail=f.detail,
            why=_why_for(f.code),
            cta="Fix this",
            flow="fix_finding",
            stake=stake,
            data={"code": f.code, "metric": f.metric, "source": "xray"},
        ))

    # A cash buffer that is too THIN is a breach; one that is too fat is idle money.
    if report.cash_pct > 0.25:
        idle = (report.cash_pct - 0.15) * report.nav
        out.append(Action(
            id="xray:IDLE_CASH",
            severity="opportunity",
            title=f"{_pct(report.cash_pct)} of your money is sitting in cash",
            detail=f"About {_rupees(idle)} is uninvested beyond a sensible buffer.",
            why="Cash is safe and it also earns nothing. A buffer is for buying when "
                "prices fall; anything past that is a decision you have not made yet.",
            cta="Put it to work",
            flow="deploy_cash",
            stake=idle,
            data={"cash_pct": report.cash_pct, "idle": idle},
        ))
    return out


def _why_for(code: str) -> str:
    """The teaching line. Every action says why it matters, once, in plain words."""
    return {
        "SECTOR_CONCENTRATION":
            "Companies in the same industry fall together. Ten technology stocks in a "
            "technology downturn behave like one very large technology stock.",
        "POSITION_CONCENTRATION":
            "One company can go wrong on its own — a fraud, a lost contract, a bad "
            "quarter. A limit on any single name caps what that can cost you.",
        "LOW_CASH":
            "Without a cash buffer, the only way to buy anything is to sell something "
            "else, usually at the worst possible moment.",
        "DEEP_DRAWDOWN":
            "This is the fall you would have had to sit through. It is the number that "
            "decides whether you sell at the bottom.",
        "HIGH_BETA":
            "You move more than the market does, in both directions. Fine on the way "
            "up, painful on the way down.",
        "FALSE_DIVERSIFICATION":
            "Owning many names does not spread risk if a few of them hold most of the "
            "money. What counts is the effective number, not the headcount.",
    }.get(code,
          "This sits outside the limits you chose for yourself, which is the only "
          "yardstick that matters here.")


def _from_tax(lots: dict[str, tax_mod.Lot], portfolio: Portfolio,
              prices: dict[str, float], asof: date) -> list[Action]:
    """Deadlines. These are the actions that expire, so they get a countdown.

    Two distinct opportunities live here and they pull in opposite directions:
    a holding about to cross into long-term treatment is a reason to WAIT, and an
    unrealised loss is a reason to ACT before the financial year closes.
    """
    out: list[Action] = []

    for ticker, lot in lots.items():
        held = portfolio.positions.get(ticker, 0)
        if held <= 0:
            continue
        price = prices.get(ticker, 0.0)
        if not price:
            continue
        days = lot.held_days(asof)
        to_long = tax_mod.LONG_TERM_DAYS - days
        gain = (price - lot.buy_price) * min(held, lot.shares)

        # About to cross into long-term: selling now costs the higher rate.
        if 0 < to_long <= 60 and gain > 0:
            saving = gain * (tax_mod.SHORT_TERM_RATE - tax_mod.LONG_TERM_RATE)
            if saving > 200:
                out.append(Action(
                    id=f"tax:hold:{ticker}",
                    severity="opportunity",
                    title=f"{universe.name(ticker)} turns long-term in {to_long} days",
                    detail=f"Waiting saves about {_rupees(saving)} in tax on the gain "
                           f"you already have.",
                    why="Gains on shares held under a year are taxed at 20%; past a "
                        "year the rate drops to 12.5%. The only thing between the two "
                        "is the calendar.",
                    cta="Show the maths",
                    flow="tax_plan",
                    stake=saving,
                    deadline_days=to_long,
                    deadline_label=f"{to_long} days",
                    data={"ticker": ticker, "days_to_long_term": to_long,
                          "saving": saving},
                ))

        # Sitting on a loss: harvestable against gains before the year end.
        if gain < -1000:
            out.append(Action(
                id=f"tax:harvest:{ticker}",
                severity="opportunity",
                title=f"{universe.name(ticker)} is down {_rupees(abs(gain))}",
                detail="That loss can be set against gains you realise this year.",
                why="Realised losses subtract from realised gains before tax is "
                    "worked out. An unrealised loss does nothing at all.",
                cta="Show me",
                flow="tax_plan",
                stake=abs(gain) * tax_mod.SHORT_TERM_RATE,
                deadline_days=_days_to_fy_end(asof),
                deadline_label="this financial year",
                data={"ticker": ticker, "unrealised": gain},
            ))

    # Basis missing entirely: the tax engine cannot help until it is supplied.
    missing = [t for t in portfolio.positions if t not in lots]
    if missing:
        out.append(Action(
            id="tax:missing_basis",
            severity="important",
            title=f"I do not know what you paid for {len(missing)} of your holdings",
            detail="Without a purchase price I cannot tell you the tax on selling them.",
            why="Cost basis is something only you know. I will never guess it, because "
                "a guessed tax number is worse than no tax number.",
            cta="Add purchase prices",
            flow="add_basis",
            stake=0.0,
            data={"missing": missing[:8], "count": len(missing)},
        ))
    return out


def _days_to_fy_end(asof: date) -> int:
    """Indian financial year ends 31 March."""
    end = date(asof.year + (1 if asof.month > 3 else 0), 3, 31)
    return max(0, (end - asof).days)


def _from_rebalance(plan: dict[str, Any]) -> list[Action]:
    """If a compliant plan exists, offer it as one action rather than a table."""
    trades = plan.get("trades") or []
    if not trades:
        return []
    turnover = plan.get("turnover") or sum(abs(t.get("value", 0.0)) for t in trades)
    sells = sum(1 for t in trades if t.get("side") == "SELL")
    buys = len(trades) - sells
    bits = []
    if sells:
        bits.append(f"{sells} sell{'s' if sells != 1 else ''}")
    if buys:
        bits.append(f"{buys} buy{'s' if buys != 1 else ''}")
    # A plan that only exists to deploy idle cash is an opportunity; a plan that is the
    # route back INTO compliance is a live problem.
    fixes_a_breach = not (plan.get("before") or {}).get("compliant", True) \
        or plan.get("compliant_after") is True and any(
            t.get("side") == "SELL" for t in trades)
    return [Action(
        id="rebalance:plan",
        severity="important" if fixes_a_breach else "opportunity",
        title=f"{' and '.join(bits).capitalize()} would bring you inside every limit",
        detail=f"About {_rupees(turnover)} of trading, worked out to be the smallest "
               f"change that does it.",
        why="There are many ways to fix a concentrated portfolio. This is the one that "
            "moves the least money, because every trade costs something.",
        cta="Review the plan",
        flow="rebalance",
        stake=turnover * 0.1,
        data={"trade_count": len(trades), "turnover": turnover},
    )]


def _from_stress(stress: dict[str, Any], nav: float) -> list[Action]:
    worst = stress.get("worst_case")
    if not worst:
        return []
    ret = worst.get("portfolio_return", 0.0)
    if ret > -0.25:
        return []
    loss = abs(ret) * nav
    return [Action(
        id="stress:worst",
        severity="important",
        title=f"Your worst tested case loses {_rupees(loss)}",
        detail=f"That is {_pct(abs(ret))} of everything you own, in {worst.get('label')}.",
        why="This is not a forecast. It is what this exact basket did in a window that "
            "actually happened, which makes it the honest floor rather than a guess.",
        cta="Walk me through it",
        flow="stress_test",
        stake=loss * 0.05,
        data={"scenario": worst.get("key"), "loss": loss, "return": ret},
    )]


def _clean_bill(report: xray_mod.XRay) -> Action:
    return Action(
        id="ok:clean",
        severity="ok",
        title="Nothing needs fixing right now",
        detail=f"You score {report.score} out of 100 against {report.profile_name.lower()} "
               f"limits, and nothing sits outside them.",
        why="A clean bill is a statement about limits, not about returns. It means "
            "nothing here can hurt you more than you agreed to be hurt.",
        cta="Check anyway",
        question="How am I doing?",
        data={"score": report.score, "grade": report.grade},
    )


# --------------------------------------------------------------------------- build
def build(pit: PointInTimeStore, portfolio: Portfolio, prices: dict[str, float],
          policy: Policy, lots: dict[str, tax_mod.Lot] | None = None,
          limit: int = 6) -> dict[str, Any]:
    """The whole queue, ranked.

    Deliberately capped. A list of twenty things to do is a list of nothing to do --
    the point of this panel is that a person can read it in five seconds and act on
    the top one.
    """
    if not portfolio.positions:
        return {"actions": [Action(
            id="empty:add",
            severity="urgent",
            title="Tell me what you own",
            detail="Add your holdings, or load an example portfolio to look around.",
            why="Everything here is computed from your actual positions. Without them "
                "I would be describing someone else's money.",
            cta="Add holdings",
            flow="onboarding",
        ).as_dict()], "count": 1, "clean": False}

    report = xray_mod.analyse(pit, portfolio, prices, policy)
    actions = _from_xray(report, policy)

    try:
        plan = rebalance_mod.plan(pit, portfolio, prices, policy,
                                 deploy_cash=True).as_dict()
        actions += _from_rebalance(plan)
    except Exception:  # noqa: BLE001 - a failed plan must not blank the queue
        pass

    try:
        actions += _from_stress(stress_mod.run_all(pit, portfolio, prices), report.nav)
    except Exception:  # noqa: BLE001
        pass

    if lots:
        asof = datetime.fromisoformat(pit.clock_iso[:10]).date()
        try:
            actions += _from_tax(lots, portfolio, prices, asof)
        except Exception:  # noqa: BLE001
            pass

    if not actions:
        actions = [_clean_bill(report)]

    for a in actions:
        a.rank = a.score()
    actions.sort(key=lambda a: -a.rank)

    top = actions[:limit]
    return {
        "actions": [a.as_dict() for a in top],
        "count": len(actions),
        "hidden": max(0, len(actions) - len(top)),
        "clean": all(a.severity == "ok" for a in actions),
        "grade": report.grade,
        "score": report.score,
        "urgent": sum(1 for a in actions if a.severity == "urgent"),
    }
