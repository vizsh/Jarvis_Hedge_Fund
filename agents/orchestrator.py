"""Fan out the desks, gate their claims, fuse a verdict.

The fusion is deliberately arithmetic, not another LLM call. Asking a model to
summarise four other models compounds their errors and destroys traceability -- every
number in the Verdict can be recomputed by hand from the accepted claims.

Groupthink deserves a note. Four desks running the same 8B model over overlapping
evidence will agree far more often than four independent analysts would, and that
agreement carries almost no information. So near-unanimity is treated as a WARNING and
discounts conviction, rather than confirming it. An investment system that gets more
confident the more its correlated components agree is one that fails hardest exactly
when it is most certain.
"""
from __future__ import annotations

import asyncio

from agents.desks import ANALYST_DESKS, DESKS, RED_TEAM, Desk, consensus_brief, run_desk
from agents.evidence import EvidencePack, build_pack
from agents.llm import ANALYST_MODEL
from agents.schema import DeskReport, Stance, Verdict
from core.pit import PointInTimeStore

# Measured across the three analysts only. 0.80 means four fifths of the claim weight
# sits on one side -- with three desks that is a near-unanimous reading.
#
# This was 0.90 when the Red Team's own claims were counted into the consensus, which
# inflated agreement toward 1.00 and made the flag fire for the wrong reason. Excluding
# the dissenter gives an honest number and needs an honest threshold to match.
GROUPTHINK_AGREEMENT = 0.80

# Unanimity with no counter-case is worth half. Unanimity WITH a real counter-case on
# the table is still worth flagging -- correlated agents agreeing tells you little
# either way -- but it is less bad, because you can at least weigh the other side.
DISCOUNT_NO_DISSENT = 0.5
DISCOUNT_WITH_DISSENT = 0.75


async def run_desks(pack: EvidencePack, desks: tuple[Desk, ...] = ANALYST_DESKS, on_event=None
                    ) -> list[DeskReport]:
    """Two passes, because a blind dissenter is not a dissenter.

    Pass 1 runs the analysts in parallel. Pass 2 shows the Red Team what they actually
    concluded and asks it to oppose that specific position. The cost is wall clock --
    the passes are inherently sequential -- and it buys dissent that is about something.

    `on_event(kind, payload)` (optional, synchronous) is told as each step really happens, so a UI can show the
    work as it unfolds instead of after it: "analysts_start", "desk_done" (each desk the moment it finishes) and
    "red_start" (with the analysts' reports and the stance the Red Team must oppose).
    """
    def tell(kind: str, payload) -> None:
        if on_event is not None:
            on_event(kind, payload)

    async def one(d: Desk) -> DeskReport:
        r = await run_desk(d, pack)
        tell("desk_done", r)
        return r

    tell("analysts_start", [d.name for d in desks])
    analysts = list(await asyncio.gather(*(one(d) for d in desks)))
    consensus, oppose = consensus_brief(analysts)
    tell("red_start", {"analysts": analysts, "oppose": oppose})

    # With no analyst claims there is nothing to dissent from, so the Red Team runs
    # unconstrained rather than being forced into an arbitrary stance.
    red = await run_desk(RED_TEAM, pack, consensus, oppose if consensus else "")
    tell("desk_done", red)
    return [*analysts, red]


def fuse(pack: EvidencePack, reports: list[DeskReport],
         model: str = ANALYST_MODEL) -> Verdict:
    bull = sum(c.weight for r in reports for c in r.accepted if c.stance is Stance.BULL)
    bear = sum(c.weight for r in reports for c in r.accepted if c.stance is Stance.BEAR)
    total = bull + bear

    net = (bull - bear) / total if total else 0.0

    cited = [e for r in reports for c in r.accepted for e in c.source_ids]
    quality = pack.mean_confidence(cited)

    # Did the designated dissenter actually find anything against the majority?
    #
    # Note the Red Team is excluded from the majority it is measured against -- it is
    # now forced to oppose, so counting its weight in `bull`/`bear` would let it move
    # the very consensus it is supposed to be testing.
    analysts = [r for r in reports if r.desk != "Red Team"]
    a_bull = sum(c.weight for r in analysts for c in r.accepted if c.stance is Stance.BULL)
    a_bear = sum(c.weight for r in analysts for c in r.accepted if c.stance is Stance.BEAR)
    majority = Stance.BULL if a_bull >= a_bear else Stance.BEAR
    opposing = Stance.BEAR if majority is Stance.BULL else Stance.BULL
    red = next((r for r in reports if r.desk == "Red Team"), None)
    dissent_claims = [c for c in (red.accepted if red else []) if c.stance is opposing]

    # Agreement is now measured across the ANALYSTS only, for the same reason.
    a_total = a_bull + a_bear
    agreement = max(a_bull, a_bear) / a_total if a_total else 0.0

    # High analyst agreement is flagged whether or not the Red Team found a counter-case.
    # The risk being detected is that correlated agents agreeing carries little
    # information, and a forced dissent does not make that stop being true.
    groupthink = bool(a_total) and agreement >= GROUPTHINK_AGREEMENT
    if groupthink:
        discount = DISCOUNT_WITH_DISSENT if dissent_claims else DISCOUNT_NO_DISSENT
    else:
        discount = 1.0
    conviction = abs(net) * quality * discount

    dissent = None
    if dissent_claims:
        dissent = max(dissent_claims, key=lambda c: c.weight).claim

    return Verdict(
        ticker=pack.ticker, sim_clock=pack.sim_clock,
        net_stance=round(net, 3), agreement=round(agreement, 3),
        evidence_quality=round(quality, 3), conviction=round(conviction, 3),
        groupthink=groupthink, dissent=dissent,
        conceded=red.conceded if red else 0,
        claims_accepted=sum(len(r.accepted) for r in reports),
        claims_rejected=sum(len(r.rejected) for r in reports),
        model=model,
    )


async def investigate(pit: PointInTimeStore, ticker: str
                      ) -> tuple[EvidencePack, list[DeskReport], Verdict]:
    """One full pass: gather PIT evidence, run the desks, fuse a verdict."""
    pack = build_pack(pit, ticker)
    reports = await run_desks(pack)
    return pack, reports, fuse(pack, reports)


def provenance_graph(pack: EvidencePack, reports: list[DeskReport]) -> dict:
    """Nodes and edges for the 3D graph -- the literal audit trail, not decoration.

    ticker -> desk -> claim -> evidence -> source. Clicking an evidence node in the UI
    surfaces the text and the source URI it came from.
    """
    nodes = [{"id": pack.ticker, "label": pack.ticker, "kind": "ticker"}]
    edges: list[dict] = []
    used: set[str] = set()

    for r in reports:
        desk_id = f"desk:{r.desk}"
        nodes.append({"id": desk_id, "label": r.desk, "kind": "claim",
                      "detail": f"{len(r.accepted)} accepted / {len(r.rejected)} rejected"})
        edges.append({"src": pack.ticker, "dst": desk_id, "kind": "desk"})
        for n, claim in enumerate(r.accepted):
            cid = f"claim:{r.desk}:{n}"
            nodes.append({"id": cid, "label": claim.claim[:70], "kind": "claim",
                          "detail": f"{claim.stance.value} w={claim.weight:.2f}"})
            edges.append({"src": desk_id, "dst": cid, "kind": claim.stance.value})
            for eid in claim.source_ids:
                item = pack.by_id(eid)
                if item and eid not in used:
                    used.add(eid)
                    nodes.append({"id": eid, "label": item.text[:70], "kind": "fact",
                                  "detail": f"{item.source_name} {item.published_at[:10]}",
                                  "uri": item.source_uri})
                edges.append({"src": cid, "dst": eid, "kind": "cites"})
    return {"nodes": nodes, "edges": edges}
