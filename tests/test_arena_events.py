"""The research visual is only honest if the server tells the UI about each step when it really happens."""
import asyncio

from agents import orchestrator as O
from agents.desks import ANALYST_DESKS
from agents.schema import Claim, DeskReport, Stance


class FakePack:
    ticker = "TEST.NS"


def _report(desk, stance=Stance.BULL, n=1):
    r = DeskReport(desk=desk, ticker="TEST.NS")
    r.accepted = [Claim(claim=f"{desk} claim {i}", stance=stance, weight=0.6, source_ids=["e1"]) for i in range(n)]
    return r


def test_each_desk_is_reported_as_it_finishes_and_red_team_starts_after_the_analysts(monkeypatch):
    order = []

    async def fake_run_desk(desk, pack, consensus="", oppose=""):
        await asyncio.sleep({"Fundamental": 0.03, "Quant": 0.01, "Narrative": 0.02}.get(desk.name, 0))
        return _report(desk.name, Stance.BEAR if desk.name == "Red Team" else Stance.BULL)

    monkeypatch.setattr(O, "run_desk", fake_run_desk)
    events = []
    reports = asyncio.run(O.run_desks(FakePack(), on_event=lambda k, p: events.append((k, p))))
    kinds = [k for k, _ in events]
    assert kinds[0] == "analysts_start" and kinds[-1] == "desk_done" and kinds.count("desk_done") == 4 and kinds.index("red_start") == 4
    assert [p.desk for k, p in events if k == "desk_done"][:3] == ["Quant", "Narrative", "Fundamental"]     # in the order they finished, not listed
    red = next(p for k, p in events if k == "red_start")
    assert red["oppose"] == "bear" and len(red["analysts"]) == 3 and [r.desk for r in reports][-1] == "Red Team"


def test_without_a_listener_nothing_changes(monkeypatch):
    async def fake_run_desk(desk, pack, consensus="", oppose=""):
        return _report(desk.name)
    monkeypatch.setattr(O, "run_desk", fake_run_desk)
    assert len(asyncio.run(O.run_desks(FakePack()))) == len(ANALYST_DESKS) + 1
