"""Recorder / Player tests.

This is the demo's insurance policy, so it gets tested like one: the take must replay
the same decisions in the same order, and it must not need the model layer to do it.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from backend.bus import EventBus
from backend.recorder import Player, Recorder
from core.events import EventType, ev


class FakeSession:
    """Stands in for a live session so the recorder has state to snapshot."""
    def __init__(self) -> None:
        self.nav = 10_000_000.0

    def snapshot(self) -> dict:
        return {"sim_clock": "2026-09-14T00:00:00+00:00", "nav": self.nav}


async def _record(tmp_path: Path, monkeypatch) -> tuple[EventBus, Path]:
    monkeypatch.setattr("backend.recorder.RECORDINGS", tmp_path)
    bus = EventBus()
    rec = Recorder(bus=bus, name="t", session=FakeSession())
    rec.start()
    await asyncio.sleep(0)

    bus.emit(EventType.CLOCK, sim_clock="2020-03-23T00:00:00+00:00")
    bus.emit(EventType.CLAIM, desk="Quant", claim="c", stance="bear",
             weight=0.8, source_ids=["E1"])
    bus.emit(EventType.CLAIM_REJECTED, desk="Fundamental", claim="x", reason="no_citation")
    bus.emit(EventType.CONVICTION, score=0.49, agreement=1.0, groupthink=True,
             net_stance=-1.0, evidence_quality=0.98,
             claims_accepted=7, claims_rejected=1)
    bus.emit(EventType.RISK_DECISION, approved=False, policy_version="v1",
             violations=[{"code": "SECTOR_LIMIT", "message": "m",
                          "measured": 0.304, "limit": 0.30, "headroom": -0.004}],
             remedy=None)
    await asyncio.sleep(0.05)
    path = rec.stop()
    return bus, path


@pytest.mark.asyncio
async def test_recording_is_written_and_replays_in_order(tmp_path, monkeypatch):
    _, path = await _record(tmp_path, monkeypatch)
    assert path.exists()

    fresh = EventBus()
    seen: list[str] = []
    q = fresh.subscribe()
    player = Player(bus=fresh, path=path, speed=50.0)
    player.start()
    await asyncio.sleep(1.0)

    while not q.empty():
        seen.append(q.get_nowait().type.value)

    # graph.reset is injected by the player before the take.
    assert seen[0] == "graph.reset"
    body = [s for s in seen if s != "graph.reset"]
    assert body == ["clock", "claim", "claim.rejected", "conviction", "risk.decision"]


@pytest.mark.asyncio
async def test_replay_preserves_the_decisions_not_just_the_event_types(tmp_path, monkeypatch):
    """A replay that loses the numbers is a screensaver, not a fallback."""
    _, path = await _record(tmp_path, monkeypatch)

    fresh = EventBus()
    q = fresh.subscribe()
    Player(bus=fresh, path=path, speed=50.0).start()
    await asyncio.sleep(1.0)

    payloads = {}
    while not q.empty():
        e = q.get_nowait()
        payloads[e.type.value] = e.payload

    assert payloads["conviction"]["groupthink"] is True
    assert payloads["conviction"]["score"] == 0.49
    assert payloads["risk.decision"]["violations"][0]["code"] == "SECTOR_LIMIT"
    assert payloads["claim.rejected"]["reason"] == "no_citation"


@pytest.mark.asyncio
async def test_state_snapshots_are_captured_for_offline_panels(tmp_path, monkeypatch):
    """Without these, /state answers from the live session and the HUD shows 2026
    numbers under a 2020 clock."""
    _, path = await _record(tmp_path, monkeypatch)
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l]
    states = [r for r in rows if r["kind"] == "state"]
    assert states, "no state snapshots recorded"
    assert states[0]["data"]["nav"] == 10_000_000.0


@pytest.mark.asyncio
async def test_player_caps_long_gaps(tmp_path, monkeypatch):
    """A 15s desk wait is dead air on stage; every pause is capped."""
    monkeypatch.setattr("backend.recorder.RECORDINGS", tmp_path)
    path = tmp_path / "gap.jsonl"
    path.write_text(
        json.dumps({"t": 0.0, "kind": "event", "data": json.loads(ev(EventType.CLOCK).dumps())}) + "\n" +
        json.dumps({"t": 30.0, "kind": "event", "data": json.loads(ev(EventType.SPEECH).dumps())}) + "\n",
        encoding="utf-8")

    bus = EventBus()
    q = bus.subscribe()
    player = Player(bus=bus, path=path, speed=1.0, max_gap=0.2)
    player.start()
    await asyncio.sleep(0.9)
    kinds = []
    while not q.empty():
        kinds.append(q.get_nowait().type.value)
    assert "speech" in kinds, "a 30s recorded gap was not capped"


@pytest.mark.asyncio
async def test_replay_needs_no_model_or_snapshot(tmp_path, monkeypatch):
    """The whole point. Player touches the file and the bus, nothing else."""
    import backend.recorder as mod
    source = Path(mod.__file__).read_text(encoding="utf-8")
    for forbidden in ("ollama", "chat_json", "PointInTimeStore", "RiskEngine", "whisper"):
        assert forbidden not in source, f"recorder imports {forbidden}"
