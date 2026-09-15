"""Backend tests: the pipeline drives the demo script without an LLM in the path.

The desk calls are stubbed. That is the point -- rewind, the risk firewall, the policy
simulator and paper execution must all work with the model layer removed, because on
the day the model is the least reliable component in the room.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from backend.bus import EventBus
from backend.intents import Intent, parse_pattern
from backend.pipeline import handle
from backend.session import Session
from core.events import EventType

DB = Path(__file__).resolve().parent.parent / "data" / "snapshot.db"
pytestmark = pytest.mark.skipif(not DB.exists(), reason="snapshot not built")


@pytest.fixture
def rig():
    """The scripted demo runs on the INSTITUTIONAL profile.

    The default is now `retail` (15% per stock, 35% per sector), under which the demo
    trade is perfectly legal -- these tests describe the fund walkthrough, so they pin
    the fund profile and size the book from live prices rather than the old hardcoded
    seed, which no longer matches the snapshot.
    """
    from backend import portfolios
    from risk.engine import RiskEngine
    from risk.policy import Policy

    session = Session.create()
    session.reprice()
    session.policy = Policy.from_profile("fund")
    session.engine = RiskEngine(session.policy)

    demo = next(p for p in portfolios.PRESETS if p["key"] == "demo_fund")
    cash, positions = portfolios.preset_to_positions(demo, session.prices,
                                                     nav=10_000_000)
    session.set_portfolio("Demo fund", cash, positions)
    return session, EventBus()


def run(session, bus, text: str) -> list:
    intent = parse_pattern(text)
    assert intent is not None, f"no deterministic pattern for {text!r}"
    asyncio.run(handle(session, bus, intent))
    return bus.history()


def kinds(events) -> list[str]:
    return [e.type.value for e in events]


def last(events, type_: EventType) -> dict:
    hits = [e.payload for e in events if e.type is type_]
    assert hits, f"no {type_.value} event emitted"
    return hits[-1]


# --- time machine ------------------------------------------------------------------
def test_rewind_moves_the_clock_and_shrinks_the_visible_world(rig):
    session, bus = rig
    before = session.pit.visible_counts()["prices"]
    events = run(session, bus, "rewind to 2020-03-23")
    assert last(events, EventType.CLOCK)["sim_clock"].startswith("2020-03-23")
    assert session.pit.visible_counts()["prices"] < before


def test_rewind_remarks_the_book_to_historical_prices(rig):
    """Rewinding must reprice the fund too.

    If the agents read 2020 but the portfolio stays marked at 2026 prices, lookahead
    walks straight into the risk engine -- the one place it must never reach.
    """
    session, bus = rig
    nav_now = session.nav()
    run(session, bus, "rewind to 2020-03-23")
    assert session.nav() != nav_now
    assert session.prices["TCS.NS"] == pytest.approx(
        session.pit.last_close("TCS.NS"), rel=0.01)


# --- risk firewall -----------------------------------------------------------------
def test_demo_trade_is_blocked_with_a_remedy(rig):
    session, bus = rig
    events = run(session, bus, "buy 30 shares of Persistent")
    decision = last(events, EventType.RISK_DECISION)
    assert decision["approved"] is False
    assert decision["violations"][0]["code"] == "SECTOR_LIMIT"
    assert decision["remedy"]["max_shares"] > 0
    assert session.counters.violations_blocked >= 1


def test_blocked_trade_is_never_executed(rig):
    session, bus = rig
    before = dict(session.portfolio.positions)
    run(session, bus, "buy 30 shares of Persistent")
    assert session.portfolio.positions == before, "a blocked trade mutated the book"


def test_compliant_trade_stages_then_executes_on_approval(rig):
    session, bus = rig
    run(session, bus, "buy 5 shares of Persistent")
    assert session.pending is not None, "compliant trade was not staged"
    held = session.portfolio.positions.get("PERSISTENT.NS", 0)

    events = run(session, bus, "execute")
    fill = last(events, EventType.EXECUTION)
    assert fill["paper"] is True
    assert session.portfolio.positions["PERSISTENT.NS"] == held + 5
    assert session.pending is None


def test_nothing_executes_without_an_explicit_approval(rig):
    session, bus = rig
    before = dict(session.portfolio.positions)
    run(session, bus, "buy 5 shares of Persistent")
    assert session.portfolio.positions == before, "staging alone changed the book"


def test_staged_trade_is_regated_against_current_state(rig):
    """An approval is only valid against the book it was made on."""
    session, bus = rig
    run(session, bus, "buy 5 shares of Persistent")
    assert session.pending is not None
    # Move the world under the staged approval.
    session.portfolio = session.portfolio.apply("PERSISTENT.NS", "BUY", 400,
                                                session.prices["PERSISTENT.NS"])
    events = run(session, bus, "execute")
    assert last(events, EventType.RISK_DECISION)["approved"] is False


# --- policy simulator ---------------------------------------------------------------
def test_policy_simulator_flips_the_verdict(rig):
    session, bus = rig
    run(session, bus, "buy 30 shares of Persistent")
    events = run(session, bus, "what if we relax the sector cap to 40%")
    decision = last(events, EventType.RISK_DECISION)
    assert decision["policy_version"].endswith("+sim")
    assert decision["counterfactual"]["was_approved"] is False
    assert decision["counterfactual"]["now_approved"] is True


def test_simulating_does_not_mutate_the_live_policy(rig):
    session, bus = rig
    run(session, bus, "what if we relax the sector cap to 40%")
    assert session.policy.limits.max_sector_pct == 0.30
    assert session.policy.version == "fund-v1"   # profile-scoped since the rewrite


# --- housekeeping -------------------------------------------------------------------
def test_reset_restores_the_opening_fund(rig):
    session, bus = rig
    before = dict(session.portfolio.positions)
    run(session, bus, "buy 5 shares of Persistent")
    run(session, bus, "execute")
    assert session.portfolio.positions != before
    run(session, bus, "reset")
    from risk.seed import seed_fund
    assert session.portfolio.positions == seed_fund().positions


def test_every_command_emits_an_intent_and_telemetry(rig):
    session, bus = rig
    events = run(session, bus, "show me the portfolio")
    assert EventType.INTENT.value in kinds(events)
    assert EventType.TELEMETRY.value in kinds(events)


def test_pipeline_errors_surface_as_events_not_crashes(rig):
    session, bus = rig
    asyncio.run(handle(session, bus, Intent(verb="rewind", args={"date": None})))
    assert EventType.ERROR.value in kinds(bus.history())


def test_bus_drops_events_for_a_stalled_client_not_the_pipeline(rig):
    """A wedged browser tab must not be able to stop the agents mid-run."""
    _, bus = rig
    q = bus.subscribe()
    for _ in range(bus._replay.maxlen + 50):
        bus.emit(EventType.TELEMETRY, tick=1)
    assert bus.dropped > 0
    assert q.qsize() <= 256


def _speech(events) -> str:
    lines = [e.payload["text"] for e in events if e.type is EventType.SPEECH]
    assert lines, "no speech emitted"
    return lines[-1]


def test_simulator_speech_agrees_with_the_verdict(rig):
    """The spoken line must never contradict the verdict on screen.

    It did: collapsing the outcome into two branches made JARVIS say "still blocks"
    over an APPROVED decision, because "was already compliant" fell through to the
    wrong branch.
    """
    session, bus = rig
    run(session, bus, "buy 30 shares of Persistent")
    events = run(session, bus, "what if we relax the sector cap to 40%")
    decision = last(events, EventType.RISK_DECISION)
    spoken = _speech(events)
    assert decision["approved"] is True
    assert "unblocks" in spoken and "still blocks" not in spoken


def test_simulator_says_nothing_changed_when_trade_was_already_compliant(rig):
    session, bus = rig
    run(session, bus, "buy 1 shares of Persistent")
    events = run(session, bus, "what if we relax the sector cap to 40%")
    assert "already within limits" in _speech(events)


def test_simulator_says_still_blocks_when_relaxation_is_insufficient(rig):
    session, bus = rig
    run(session, bus, "buy 3000 shares of Persistent")
    events = run(session, bus, "what if we relax the sector cap to 31%")
    assert last(events, EventType.RISK_DECISION)["approved"] is False
    assert "still blocks" in _speech(events)


# --- remedy governance --------------------------------------------------------------
def test_blocked_trade_leaves_nothing_staged(rig):
    """A breach must not stage anything. The remedy is an offer, not an approval."""
    session, bus = rig
    run(session, bus, "buy 30 shares of Persistent")
    assert session.pending is None
    assert session.remedy is not None
    assert session.remedy["shares"] < 30


def test_bare_execute_after_a_block_does_not_fill(rig):
    """The failure the dry run caught: "buy 30" was refused, "execute" then booked 21 --
    the system substituting its own number for the instruction and acting on it."""
    session, bus = rig
    before = dict(session.portfolio.positions)
    run(session, bus, "buy 30 shares of Persistent")
    events = run(session, bus, "execute")
    assert session.portfolio.positions == before
    assert not [e for e in events if e.type is EventType.EXECUTION]
    assert "remedy" in _speech(events).lower()


def test_accepting_the_remedy_books_the_smaller_trade(rig):
    session, bus = rig
    run(session, bus, "buy 30 shares of Persistent")
    offered = session.remedy["shares"]
    held = session.portfolio.positions.get("PERSISTENT.NS", 0)

    events = run(session, bus, "accept the remedy")
    fill = last(events, EventType.EXECUTION)
    assert fill["shares"] == offered
    assert session.portfolio.positions["PERSISTENT.NS"] == held + offered
    assert session.remedy is None


def test_accepting_with_no_offer_does_nothing(rig):
    session, bus = rig
    before = dict(session.portfolio.positions)
    events = run(session, bus, "accept the remedy")
    assert session.portfolio.positions == before
    assert "no remedy" in _speech(events).lower()


def test_approved_trade_clears_any_stale_remedy(rig):
    session, bus = rig
    run(session, bus, "buy 30 shares of Persistent")
    assert session.remedy is not None
    run(session, bus, "buy 1 shares of Persistent")
    assert session.remedy is None
    assert session.pending is not None


def test_unknown_ticker_short_circuits_before_the_desks(rig):
    """Typing a ticker outside the universe must not cost fifteen seconds of dead air."""
    session, bus = rig
    events = run(session, bus, "analyse ZOMATO")
    assert not [e for e in events if e.type is EventType.AGENT_STATE]
    assert EventType.ERROR.value in kinds(events)


def test_remedy_lapses_when_the_clock_moves(rig):
    """It was priced against the book at that instant; after a rewind it is arithmetic
    about a different world."""
    session, bus = rig
    run(session, bus, "buy 30 shares of Persistent")
    assert session.remedy is not None
    run(session, bus, "rewind to 2020-06-30")
    assert session.remedy is None
    assert session.pending is None

    before = dict(session.portfolio.positions)
    events = run(session, bus, "accept the remedy")
    assert session.portfolio.positions == before
    assert not [e for e in events if e.type is EventType.EXECUTION]
