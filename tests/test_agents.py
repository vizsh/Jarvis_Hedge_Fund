"""Citation gate and fusion tests. No LLM required -- these are pure functions.

The gate showed zero rejections on its first live run, which proves nothing on its own:
a gate that never fires and a gate that does not work look identical from the outside.
These tests force both failure modes.
"""
from __future__ import annotations

import pytest

from agents.desks import apply_citation_gate
from agents.evidence import EvidencePack
from agents.orchestrator import fuse
from agents.schema import Claim, DeskReport, RejectReason, Stance


@pytest.fixture
def pack() -> EvidencePack:
    p = EvidencePack(ticker="TCS.NS", sim_clock="2026-09-01T00:00:00+00:00")
    p.add("last close 2369", "yfinance", "2026-09-01", 1.0, kind="quant")
    p.add("RSI(14) 52", "yfinance (computed)", "2026-09-01", 1.0, kind="quant")
    p.add("press tone -1.79", "GDELT", "2026-09-01", 0.6, kind="narrative")
    return p


def _claim(text="c", stance=Stance.BULL, weight=0.5, ids=("E1",)) -> Claim:
    return Claim(claim=text, stance=stance, weight=weight, source_ids=list(ids))


def test_well_cited_claim_is_accepted(pack):
    ok, bad = apply_citation_gate([_claim(ids=("E1", "E2"))], pack)
    assert len(ok) == 1 and not bad


def test_uncited_claim_is_dropped(pack):
    ok, bad = apply_citation_gate([_claim(ids=())], pack)
    assert not ok
    assert bad[0][1] is RejectReason.NO_CITATION


def test_fabricated_citation_is_dropped(pack):
    """The dangerous one: a made-up id looks rigorous on screen."""
    ok, bad = apply_citation_gate([_claim(ids=("E9",))], pack)
    assert not ok
    assert bad[0][1] is RejectReason.UNKNOWN_CITATION


def test_partially_fabricated_citation_is_dropped(pack):
    """One real id does not launder an invented one alongside it."""
    ok, bad = apply_citation_gate([_claim(ids=("E1", "E42"))], pack)
    assert not ok
    assert bad[0][1] is RejectReason.UNKNOWN_CITATION


def test_empty_claim_is_dropped(pack):
    ok, bad = apply_citation_gate([_claim(text="   ")], pack)
    assert bad[0][1] is RejectReason.EMPTY_CLAIM


def test_gate_is_all_or_nothing_per_claim(pack):
    good, bogus = _claim(text="real", ids=("E1",)), _claim(text="fake", ids=("E7",))
    ok, bad = apply_citation_gate([good, bogus], pack)
    assert [c.claim for c in ok] == ["real"]
    assert [c.claim for c, _ in bad] == ["fake"]


# --- fusion ----------------------------------------------------------------------
def _report(desk: str, claims: list[Claim]) -> DeskReport:
    return DeskReport(desk=desk, ticker="TCS.NS", accepted=claims)


def test_net_stance_spans_bear_to_bull(pack):
    bull = fuse(pack, [_report("Quant", [_claim(stance=Stance.BULL, weight=1.0)])])
    bear = fuse(pack, [_report("Quant", [_claim(stance=Stance.BEAR, weight=1.0)])])
    assert bull.net_stance == 1.0
    assert bear.net_stance == -1.0


def test_unanimity_without_dissent_is_flagged_as_groupthink(pack):
    """Correlated agents agreeing is not evidence. It must not raise conviction."""
    reports = [_report(d, [_claim(stance=Stance.BULL, weight=1.0)])
               for d in ("Fundamental", "Quant", "Narrative", "Red Team")]
    v = fuse(pack, reports)
    assert v.agreement == 1.0
    assert v.groupthink is True
    assert v.conviction < abs(v.net_stance) * v.evidence_quality


def test_dissent_is_surfaced_but_does_not_clear_the_flag(pack):
    """Deliberate change from the first design.

    Dissent used to clear the groupthink flag. Once the Red Team was made to run second
    and forced to oppose, it finds a counter-case essentially every time — so "dissent
    exists" became as uninformative as the bearish bias it replaced. Unanimity among
    correlated analysts is now flagged regardless, and the counter-case only softens
    the discount.
    """
    reports = [
        _report("Fundamental", [_claim(stance=Stance.BULL, weight=1.0)]),
        _report("Quant", [_claim(stance=Stance.BULL, weight=1.0)]),
        _report("Narrative", [_claim(stance=Stance.BULL, weight=1.0)]),
        _report("Red Team", [_claim(text="margins are peaking", stance=Stance.BEAR,
                                    weight=0.2)]),
    ]
    v = fuse(pack, reports)
    assert v.groupthink is True
    assert v.dissent == "margins are peaking"


def test_conviction_scales_with_evidence_quality(pack):
    """A claim resting on a 0.6-confidence source should not score like a 1.0 one."""
    strong = fuse(pack, [_report("Quant", [_claim(stance=Stance.BULL, weight=1.0,
                                                  ids=("E1",))])])
    weak = fuse(pack, [_report("Narrative", [_claim(stance=Stance.BULL, weight=1.0,
                                                    ids=("E3",))])])
    assert strong.conviction > weak.conviction


def test_no_claims_yields_zero_conviction_not_a_crash(pack):
    v = fuse(pack, [_report("Quant", [])])
    assert v.conviction == 0.0
    assert v.groupthink is False


def test_rejected_claims_are_counted_for_the_telemetry_rail(pack):
    r = DeskReport(desk="Quant", ticker="TCS.NS",
                   accepted=[_claim()],
                   rejected=[(_claim(ids=("E9",)), RejectReason.UNKNOWN_CITATION)])
    v = fuse(pack, [r])
    assert v.claims_accepted == 1
    assert v.claims_rejected == 1


# --- two-pass red team --------------------------------------------------------------
from agents.desks import consensus_brief  # noqa: E402


def test_consensus_brief_names_the_stance_to_oppose(pack):
    analysts = [
        _report("Quant", [_claim(stance=Stance.BEAR, weight=0.8)]),
        _report("Narrative", [_claim(stance=Stance.BEAR, weight=0.7)]),
    ]
    block, oppose = consensus_brief(analysts)
    assert oppose == "bull"
    assert "bearish" in block
    assert "must take the 'bull' stance" in block


def test_consensus_brief_is_empty_when_there_is_nothing_to_oppose(pack):
    block, oppose = consensus_brief([_report("Quant", [])])
    assert block == ""
    assert oppose == "neutral"


def test_red_team_is_excluded_from_the_consensus_it_tests(pack):
    """Counting the dissenter's weight into the majority inflated agreement toward 1.00
    and made the groupthink flag fire for the wrong reason."""
    reports = [
        _report("Fundamental", [_claim(stance=Stance.BEAR, weight=1.0)]),
        _report("Quant", [_claim(stance=Stance.BEAR, weight=1.0)]),
        _report("Narrative", [_claim(stance=Stance.BEAR, weight=1.0)]),
        _report("Red Team", [_claim(text="counter", stance=Stance.BULL, weight=0.9)]),
    ]
    v = fuse(pack, reports)
    assert v.agreement == 1.0           # the three analysts were unanimous
    assert v.net_stance < 0             # but the red team still moves the net stance
    assert v.dissent == "counter"


def test_unanimity_is_flagged_even_when_a_counter_case_exists(pack):
    """A forced dissenter always finds something, so "dissent exists" cannot be what
    clears the flag -- correlated agents agreeing still carries little information."""
    reports = [
        _report(d, [_claim(stance=Stance.BEAR, weight=1.0)])
        for d in ("Fundamental", "Quant", "Narrative")
    ] + [_report("Red Team", [_claim(text="c", stance=Stance.BULL, weight=0.5)])]
    v = fuse(pack, reports)
    assert v.groupthink is True


def test_unanimity_with_a_counter_case_is_discounted_less_than_without(pack):
    analysts = [_report(d, [_claim(stance=Stance.BEAR, weight=1.0)])
                for d in ("Fundamental", "Quant", "Narrative")]
    silent = fuse(pack, [*analysts, _report("Red Team", [])])
    voiced = fuse(pack, [*analysts,
                         _report("Red Team", [_claim(text="c", stance=Stance.BULL,
                                                     weight=0.5)])])
    assert silent.groupthink and voiced.groupthink
    assert voiced.conviction > silent.conviction


def test_conceded_claims_are_reported(pack):
    """The red team siding with the consensus it was told to oppose is the honest
    signal that it found no counter-case."""
    red = DeskReport(desk="Red Team", ticker="TCS.NS", accepted=[], conceded=2)
    v = fuse(pack, [_report("Quant", [_claim(stance=Stance.BEAR, weight=1.0)]), red])
    assert v.conceded == 2
