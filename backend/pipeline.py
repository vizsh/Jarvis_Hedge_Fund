"""Intent -> events. Everything the UI renders originates here.

Two rules hold throughout:

* The risk engine is the only thing that decides APPROVED/REJECTED, and no LLM output
  reaches it -- desks produce a stance, the firewall produces a verdict.
* Nothing executes without an explicit human `execute` intent. The pipeline stages a
  proposal and stops; approving it is a separate command.
"""
from __future__ import annotations

import asyncio

from agents.desks import DESKS
from agents.evidence import build_pack
from agents.llm import ANALYST_MODEL, available
from agents.orchestrator import fuse, provenance_graph, run_desks
from agents.persist import save_decision, save_run
from agents.schema import Stance
from backend.bus import EventBus
from backend.intents import Intent
from backend.session import Session, latest_clock
from core.events import EventType
from risk.engine import RiskEngine
from risk.policy import Policy
from risk.portfolio import Proposal
from risk.seed import DEMO_TRADE

DEFAULT_TICKER = "TCS.NS"


# ---------------------------------------------------------------------------------
# phase 0: cold boot
# ---------------------------------------------------------------------------------
async def boot(session: Session, bus: EventBus, pace: float = 0.12) -> None:
    from core.events import mock_boot_sequence

    for event in mock_boot_sequence():
        bus.publish(event)
        await asyncio.sleep(pace)

    for row in session.conn.execute(
            "SELECT name, kind, rows, ingested_at FROM sources ORDER BY name"):
        bus.emit(EventType.SOURCE_STATUS, source=row["name"], online=True,
                 rows=row["rows"], latency_ms=0, kind=row["kind"])
        await asyncio.sleep(pace / 2)

    if not available():
        bus.emit(EventType.BOOT, line="ollama unreachable - desks will fail",
                 level="fail", delay_ms=0)

    bus.emit(EventType.CLOCK, sim_clock=session.pit.clock_iso, live=False)
    emit_telemetry(session, bus)


def emit_telemetry(session: Session, bus: EventBus, orb: str | None = None) -> None:
    if orb:
        session.orb = orb
    session.counters.tick += 1
    c = session.counters
    bus.emit(EventType.TELEMETRY, tick=c.tick, orb=session.orb, model=session.model,
             claims_rejected=c.claims_rejected, violations_blocked=c.violations_blocked,
             claims_accepted=c.claims_accepted, nav=session.nav(),
             sim_clock=session.pit.clock_iso, visible=session.pit.visible_counts())


def say(bus: EventBus, text: str) -> None:
    """Template speech. Deterministic by design -- the spoken line must match the
    numbers on screen exactly, which a generated sentence cannot guarantee."""
    bus.emit(EventType.SPEECH, text=text, final=True)


# ---------------------------------------------------------------------------------
# investigate
# ---------------------------------------------------------------------------------
async def do_investigate(session: Session, bus: EventBus, ticker: str) -> None:
    emit_telemetry(session, bus, orb="thinking")
    bus.emit(EventType.GRAPH_RESET)

    pack = build_pack(session.pit, ticker)

    # A ticker outside the universe (or one with nothing published yet at this clock)
    # yields a pack with no price data. Running four desks over it costs fifteen
    # seconds and returns confident nonsense -- on stage that is a typo turning into
    # dead air. Say so immediately instead.
    if session.pit.last_close(ticker) is None:
        bus.emit(EventType.ERROR, where="investigate",
                 message=f"No data for {ticker} at {session.pit.clock_iso[:10]}.")
        say(bus, f"I have no price history for {ticker} at this date, so there is "
                 f"nothing for the desks to reason about. The universe is in "
                 f"config/universe.yaml.")
        emit_telemetry(session, bus, orb="idle")
        return

    bus.emit(EventType.GRAPH_NODE, id=ticker, label=ticker, kind="ticker",
             detail=f"{len(pack.items)} evidence items at {session.pit.clock_iso[:10]}")

    for item in pack.items:
        bus.emit(EventType.GRAPH_NODE, id=item.id, label=item.text[:70], kind="fact",
                 detail=f"{item.source_name} · {item.published_at[:10]}",
                 uri=item.source_uri)

    for desk in DESKS:
        bus.emit(EventType.AGENT_STATE, desk=desk.name, state="thinking")

    reports = await run_desks(pack)

    for report in reports:
        bus.emit(EventType.AGENT_STATE, desk=report.desk,
                 state="failed" if report.error else "done",
                 note=report.error or f"{report.latency_ms} ms")
        desk_id = f"desk:{report.desk}"
        bus.emit(EventType.GRAPH_NODE, id=desk_id, label=report.desk, kind="claim",
                 detail=f"{len(report.accepted)} accepted / {len(report.rejected)} dropped")
        bus.emit(EventType.GRAPH_EDGE, src=ticker, dst=desk_id, kind="desk")

        for n, claim in enumerate(report.accepted):
            bus.emit(EventType.CLAIM, desk=report.desk, claim=claim.claim,
                     stance=claim.stance.value, weight=claim.weight,
                     source_ids=claim.source_ids)
            cid = f"claim:{report.desk}:{n}"
            bus.emit(EventType.GRAPH_NODE, id=cid, label=claim.claim[:70], kind="claim",
                     detail=f"{claim.stance.value} w={claim.weight:.2f}")
            bus.emit(EventType.GRAPH_EDGE, src=desk_id, dst=cid, kind=claim.stance.value)
            for eid in claim.source_ids:
                bus.emit(EventType.GRAPH_EDGE, src=cid, dst=eid, kind="cites")

        for claim, reason in report.rejected:
            bus.emit(EventType.CLAIM_REJECTED, desk=report.desk, claim=claim.claim,
                     reason=reason.value)

    verdict = fuse(pack, reports)
    session.counters.claims_accepted += verdict.claims_accepted
    session.counters.claims_rejected += verdict.claims_rejected
    session.counters.investigations += 1
    session.last_run_id = save_run(session.conn, reports, verdict)

    bus.emit(EventType.CONVICTION, score=verdict.conviction,
             agreement=verdict.agreement, net_stance=verdict.net_stance,
             evidence_quality=verdict.evidence_quality,
             groupthink=verdict.groupthink, dissent=verdict.dissent,
             conceded=verdict.conceded,
             claims_accepted=verdict.claims_accepted,
             claims_rejected=verdict.claims_rejected)

    stance = ("bullish" if verdict.net_stance > 0.15 else
              "bearish" if verdict.net_stance < -0.15 else "mixed")
    line = (f"{ticker}: desks are {stance}, conviction {verdict.conviction:.2f}. "
            f"{verdict.claims_accepted} claims accepted, "
            f"{verdict.claims_rejected} dropped for citation failure.")
    if verdict.groupthink:
        line += (" Warning: all desks agreed and the red team found no counter-case, "
                 "so conviction has been discounted rather than confirmed.")
    say(bus, line)
    emit_telemetry(session, bus, orb="alert" if verdict.groupthink else "idle")


# ---------------------------------------------------------------------------------
# time machine
# ---------------------------------------------------------------------------------
async def do_rewind(session: Session, bus: EventBus, date: str | None) -> None:
    if not date:
        bus.emit(EventType.ERROR, where="rewind", message="No date understood.")
        return
    session.set_clock(date)
    # A remedy is priced against the book at the moment it was offered. Once the clock
    # moves, that arithmetic is about a different world, so the offer lapses rather
    # than sitting around waiting to be accepted against numbers that no longer hold.
    session.pending = None
    session.remedy = None
    bus.emit(EventType.CLOCK, sim_clock=session.pit.clock_iso, live=False)
    counts = session.pit.visible_counts()
    say(bus, f"Clock set to {date}. The desks can now see {counts['prices']:,} price "
             f"rows and {counts['signals']:,} signals. Nothing published after this "
             f"date is reachable.")
    emit_telemetry(session, bus, orb="idle")


# ---------------------------------------------------------------------------------
# propose -> risk firewall (stages only; never executes)
# ---------------------------------------------------------------------------------
def _decide(session: Session, engine: RiskEngine, ticker: str, side: str,
            shares: int) -> tuple[Proposal, object]:
    price = session.prices.get(ticker) or session.pit.last_close(ticker) or 0.0
    proposal = Proposal(ticker=ticker, side=side, shares=shares, price=float(price))
    return proposal, engine.evaluate(session.portfolio, proposal, session.prices,
                                     session.sectors)


async def do_propose(session: Session, bus: EventBus, ticker: str | None,
                     side: str | None, shares: int | None) -> None:
    ticker = ticker or DEMO_TRADE["ticker"]
    side = side or DEMO_TRADE["side"]
    shares = shares or DEMO_TRADE["shares"]

    proposal, decision = _decide(session, RiskEngine(session.policy), ticker, side, shares)
    session.requested = {"ticker": ticker, "side": side, "shares": shares,
                         "price": proposal.price}
    bus.emit(EventType.PROPOSAL, ticker=ticker, side=side, shares=shares,
             price=proposal.price, rationale="staged for human approval")

    bus.emit(EventType.RISK_DECISION, approved=decision.approved,
             policy_version=decision.policy_version,
             violations=[v.model_dump() for v in decision.violations],
             remedy=decision.remedy.model_dump() if decision.remedy else None,
             metrics=decision.metrics)

    if decision.approved:
        session.pending = {"ticker": ticker, "side": side, "shares": shares,
                           "price": proposal.price}
        session.remedy = None
        say(bus, f"{side} {shares} {ticker} is within all policy limits. "
                 f"Awaiting your approval to book it.")
        emit_telemetry(session, bus, orb="idle")
        return

    session.counters.violations_blocked += len(decision.violations)
    session.pending = None          # nothing is approved after a breach
    first = decision.violations[0].message if decision.violations else "Policy breach."
    spoken = f"Blocked. {first}"
    if decision.remedy and decision.remedy.max_shares > 0:
        session.remedy = {"ticker": ticker, "side": side,
                          "shares": decision.remedy.max_shares, "price": proposal.price}
        spoken += (f" {decision.remedy.explanation} Say 'accept the remedy' to take "
                   f"that instead.")
    say(bus, spoken)
    save_decision(session.conn, session.last_run_id or "-",
                  _blank_verdict(session), ticker, side, shares, proposal.price,
                  False, [v.code for v in decision.violations], decision.policy_version)
    emit_telemetry(session, bus, orb="alert")


def _blank_verdict(session: Session):
    from agents.schema import Verdict
    return Verdict(ticker="-", sim_clock=session.pit.clock_iso, net_stance=0.0,
                   agreement=0.0, evidence_quality=0.0, conviction=0.0,
                   groupthink=False)


# ---------------------------------------------------------------------------------
# policy simulator
# ---------------------------------------------------------------------------------
async def do_simulate(session: Session, bus: EventBus, ticker: str | None,
                      **overrides: float) -> None:
    if not overrides:
        overrides = {"max_sector_pct": 0.35}
    relaxed = session.policy.with_limit(**overrides)
    req = session.requested or {}
    ticker = ticker or req.get("ticker") or DEMO_TRADE["ticker"]
    shares = req.get("shares") or DEMO_TRADE["shares"]

    _, strict = _decide(session, RiskEngine(session.policy), ticker, "BUY", shares)
    _, loose = _decide(session, RiskEngine(relaxed), ticker, "BUY", shares)

    bus.emit(EventType.RISK_DECISION, approved=loose.approved,
             policy_version=loose.policy_version,
             violations=[v.model_dump() for v in loose.violations],
             remedy=loose.remedy.model_dump() if loose.remedy else None,
             metrics=loose.metrics,
             counterfactual={"from": session.policy.version,
                             "to": relaxed.version,
                             "overrides": overrides,
                             "was_approved": strict.approved,
                             "now_approved": loose.approved})
    # Three outcomes, not two. Collapsing "was already compliant" into "still blocks"
    # made the spoken line contradict the APPROVED verdict on screen.
    if loose.approved and not strict.approved:
        outcome = "unblocks the trade"
    elif loose.approved:
        outcome = "changes nothing - the trade was already within limits"
    else:
        outcome = "still blocks the trade"
    limit = ", ".join(f"{k.replace('_', ' ')} to {v:.0%}" for k, v in overrides.items())
    say(bus, f"Under policy {relaxed.version}, relaxing {limit} {outcome}.")
    emit_telemetry(session, bus, orb="idle")


# ---------------------------------------------------------------------------------
# execute (paper only)
# ---------------------------------------------------------------------------------
async def do_execute(session: Session, bus: EventBus) -> None:
    if session.policy.governance.broker_execution:
        bus.emit(EventType.ERROR, where="execute",
                 message="Broker execution is disabled in this build.")
        return
    if not session.pending:
        if session.remedy:
            r = session.remedy
            say(bus, f"Nothing is approved. The firewall offered {r['shares']} "
                     f"{r['ticker']} instead of what you asked for — say 'accept the "
                     f"remedy' if you want that trade.")
        else:
            say(bus, "There is no staged trade to approve.")
        return

    p = session.pending
    _, decision = _decide(session, RiskEngine(session.policy), p["ticker"], p["side"],
                          p["shares"])
    if not decision.approved:
        # State moved under us (clock rewind, earlier fill). Re-gate rather than trust
        # the staged verdict -- an approval is only valid against the book it was made on.
        session.counters.violations_blocked += len(decision.violations)
        say(bus, "Re-checked against current state and it no longer passes. Not booked.")
        bus.emit(EventType.RISK_DECISION, approved=False,
                 policy_version=decision.policy_version,
                 violations=[v.model_dump() for v in decision.violations],
                 remedy=decision.remedy.model_dump() if decision.remedy else None)
        session.pending = None
        return

    session.portfolio = session.portfolio.apply(
        p["ticker"], p["side"], p["shares"], p["price"],
        session.policy.execution.cost_bps)
    session.counters.trades_executed += 1
    session.pending = None
    nav = session.nav()
    try:
        from backend import ledger
        ledger.record(session.conn, sim_clock=session.pit.clock_iso, kind="TRADE",
                      ticker=p["ticker"], side=p["side"], shares=p["shares"], price=p["price"],
                      cost=p["shares"] * p["price"] * session.policy.execution.cost,
                      nav_after=nav, reason="approved by operator after firewall check",
                      policy=session.policy.profile)
    except Exception:  # noqa: BLE001 - never let bookkeeping break an approved trade
        pass

    bus.emit(EventType.EXECUTION, ticker=p["ticker"], side=p["side"],
             shares=p["shares"], price=p["price"], nav_after=nav, paper=True)
    say(bus, f"Paper trade booked: {p['side']} {p['shares']} {p['ticker']}. "
             f"Net asset value {nav:,.0f}. No broker was contacted.")
    emit_telemetry(session, bus, orb="idle")


async def do_rebalance(session: Session, bus: EventBus) -> None:
    """Describe the plan in words. Booking it stays an explicit click in the panel --
    a spoken "rebalance" is a request to see the plan, not authority to trade."""
    from analysis import rebalance as rb
    plan = rb.plan(session.pit, session.portfolio, session.prices, session.policy)
    d = plan.as_dict()
    if not d["trade_count"]:
        say(bus, "Nothing needs changing. You are inside every limit.")
    else:
        sells = sum(1 for t in d["trades"] if t["side"] == "SELL")
        buys = d["trade_count"] - sells
        say(bus, f"I can bring you back inside your limits with {d['trade_count']} "
                 f"trades — {sells} to sell"
                 + (f" and {buys} to buy" if buys else "")
                 + f". Your biggest industry drops from "
                 f"{d['before']['top_sector']:.0%} to {d['after']['top_sector']:.0%}. "
                 f"Open the rebalance panel to see them and book it yourself.")
    emit_telemetry(session, bus, orb="idle")


async def do_accept(session: Session, bus: EventBus) -> None:
    """Explicitly take the firewall's counter-offer. Separate verb, on purpose: the
    operator has to say they want the smaller trade."""
    if not session.remedy:
        say(bus, "There is no remedy on offer.")
        return
    r = session.remedy
    session.remedy = None
    await do_propose(session, bus, r["ticker"], r["side"], r["shares"])
    if session.pending:
        await do_execute(session, bus)


# ---------------------------------------------------------------------------------
# explain / status / reset
# ---------------------------------------------------------------------------------
async def do_explain(session: Session, bus: EventBus) -> None:
    rows = session.conn.execute(
        "SELECT ticker, side, shares, approved, violations FROM decisions "
        "ORDER BY created_at DESC LIMIT 1").fetchone()
    if not rows:
        say(bus, "No decision has been recorded yet.")
        return
    codes = rows["violations"] or "[]"
    say(bus, f"The last decision on {rows['ticker']} was "
             f"{'approved' if rows['approved'] else 'rejected'}"
             f"{'' if rows['approved'] else f' under {codes}'}. "
             f"Every limit is in config/policy.yaml and enforced in code, not by a model.")


async def do_status(session: Session, bus: EventBus) -> None:
    ex = session.exposures()
    top = max(ex, key=ex.get) if ex else "-"
    say(bus, f"Net asset value {session.nav():,.0f}, cash "
             f"{session.portfolio.cash / session.nav():.0%}, largest sector {top} at "
             f"{ex.get(top, 0):.1%}. Clock {session.pit.clock_iso[:10]}.")
    emit_telemetry(session, bus)


async def do_reset(session: Session, bus: EventBus) -> None:
    """Restore the ACTIVE portfolio, not a hardcoded fund.

    This used to reload `seed_fund()` regardless of what was loaded, which quietly
    swapped the user's portfolio for a demo one on every reset -- and left the scripted
    walkthrough running against a book it had not been sized for.
    """
    from backend import portfolios
    from risk.seed import seed_fund

    restored = (portfolios.load(session.conn, session.portfolio_id)
                if session.portfolio_id else None)
    if restored:
        session.set_portfolio(restored["name"], restored["cash"],
                              restored["positions"], session.portfolio_id)
    else:
        session.portfolio = seed_fund()
    session.policy = Policy.from_profile(session.policy.profile)
    session.engine = RiskEngine(session.policy)
    session.pending = None
    session.requested = None
    session.remedy = None
    session.set_clock(latest_clock(session.conn))
    bus.emit(EventType.CLOCK, sim_clock=session.pit.clock_iso, live=False)
    bus.emit(EventType.GRAPH_RESET)
    say(bus, "Fund restored to its opening state.")
    emit_telemetry(session, bus, orb="idle")


# ---------------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------------
async def handle(session: Session, bus: EventBus, intent: Intent) -> None:
    bus.emit(EventType.INTENT, **intent.as_payload())
    try:
        if intent.verb == "investigate":
            if (unknown := intent.args.get("unresolved")):
                bus.emit(EventType.ERROR, where="investigate",
                         message=f"{unknown} is not in the universe.")
                say(bus, f"{unknown} is not in the covered universe, so I have nothing "
                         f"to analyse. Add it to config/universe.yaml and re-ingest.")
                emit_telemetry(session, bus, orb="idle")
            else:
                await do_investigate(session, bus, intent.ticker or DEFAULT_TICKER)
        elif intent.verb == "rewind":
            await do_rewind(session, bus, intent.args.get("date"))
        elif intent.verb == "propose":
            await do_propose(session, bus, intent.ticker, intent.args.get("side"),
                             intent.args.get("shares"))
        elif intent.verb == "simulate":
            overrides = {k: v for k, v in intent.args.items()
                         if k.endswith("_pct") and isinstance(v, (int, float))}
            await do_simulate(session, bus, intent.ticker, **overrides)
        elif intent.verb == "execute":
            await do_execute(session, bus)
        elif intent.verb == "accept":
            await do_accept(session, bus)
        elif intent.verb == "rebalance":
            await do_rebalance(session, bus)
        elif intent.verb == "explain":
            await do_explain(session, bus)
        elif intent.verb == "reset":
            await do_reset(session, bus)
        else:
            await do_status(session, bus)
    except Exception as exc:  # noqa: BLE001
        bus.emit(EventType.ERROR, where=intent.verb,
                 message=f"{type(exc).__name__}: {exc}"[:200])
        emit_telemetry(session, bus, orb="idle")
