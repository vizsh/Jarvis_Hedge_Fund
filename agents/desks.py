"""The four desks -- four prompts, one code path.

Fundamental, Quant, Narrative, and a Red Team whose job is to argue the other way.
The Red Team is not decoration: unanimity among agents drawing on the same evidence and
the same base model is a correlation artefact, not a signal, so we force a dissenting
voice and then measure whether it found anything.

Each desk sees only the slice of the evidence pack relevant to it. That is partly token
economy and partly discipline -- a "fundamental" desk reasoning off the RSI is not a
fundamental desk.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from agents.evidence import EvidencePack
from agents.llm import chat_json
from agents.schema import CLAIMS_SCHEMA, Claim, DeskReport, RejectReason, Stance

SYSTEM = (
    "You are one analyst desk inside an auditable investment system. "
    "Every claim you make MUST cite evidence ids from the pack you are given. "
    "Never invent an id. Never cite an id that is not in the pack. "
    "If the evidence does not support a claim, make fewer claims. "
    "Be specific and quantitative; refer to the actual numbers you were given."
)


@dataclass(frozen=True)
class Desk:
    name: str
    kinds: frozenset[str]
    brief: str
    max_claims: int = 2


ANALYST_DESKS: tuple[Desk, ...] = (
    Desk("Fundamental", frozenset({"fundamental", "macro"}),
         "Assess balance-sheet health, earnings quality and valuation. "
         "Note explicitly when a fundamental figure is stale or missing rather than "
         "guessing at it."),
    Desk("Quant", frozenset({"quant"}),
         "Assess price behaviour: trend against the moving average, momentum via RSI, "
         "realised volatility, and drawdown. Interpret the numbers you were given; "
         "do not compute new ones."),
    Desk("Narrative", frozenset({"narrative", "macro"}),
         "Assess press tone and headline flow. Distinguish durable narrative shifts "
         "from single-day noise, and say which you think this is."),
)

# The Red Team runs SECOND, on the analysts' actual output.
#
# Running it in parallel and blind was a design error that calibration exposed: it
# produced bear claims 82% of the time, which meant that whenever the analysts were
# also bearish -- which they were in 17 of 18 backfill runs -- the "dissent" agreed
# with the consensus and the groupthink detector had nothing to catch. A dissenter
# that cannot see what it is dissenting from is not a dissenter, it is a fourth
# analyst with a dramatic name.
RED_TEAM = Desk(
    "Red Team", frozenset({"quant", "fundamental", "narrative", "macro"}),
    "You are the designated dissenter, and you have been shown what the other desks "
    "concluded. Argue the STRONGEST case AGAINST their reading, using the same "
    "evidence. Name what they are over-reading. Your stance must OPPOSE theirs: if "
    "they are bearish you argue the bull case, if they are bullish you argue the bear "
    "case. If the evidence genuinely will not support a counter-case, return no "
    "claims at all -- saying nothing is a real and useful answer, and a forced "
    "objection is worse than none.",
    max_claims=2)

# Kept for the UI's desk list and for anything iterating all four.
DESKS: tuple[Desk, ...] = (*ANALYST_DESKS, RED_TEAM)


def _prompt(desk: Desk, pack: EvidencePack, consensus: str = "") -> str:
    return (
        f"TICKER: {pack.ticker}\n"
        f"AS OF: {pack.sim_clock[:10]} (you know nothing after this date)\n\n"
        f"DESK: {desk.name}\n{desk.brief}\n\n"
        f"{consensus}"
        f"EVIDENCE PACK (cite these ids and no others):\n"
        f"{pack.render(set(desk.kinds))}\n\n"
        f"Return at most {desk.max_claims} claims. Each claim needs: the claim text, "
        f"a stance (bull/bear/neutral), a weight 0-1 for how much it should count, "
        f"and source_ids listing the evidence ids it rests on."
    )


def consensus_brief(reports: list[DeskReport]) -> tuple[str, str]:
    """Summarise the analysts for the Red Team, and name the stance it must oppose.

    Returns (prompt block, stance to oppose). The stance is computed here rather than
    left to the model: asking an 8B model to infer the majority and then oppose it is
    two chances to go wrong where one will do.
    """
    bull = sum(c.weight for r in reports for c in r.accepted if c.stance is Stance.BULL)
    bear = sum(c.weight for r in reports for c in r.accepted if c.stance is Stance.BEAR)
    if not (bull or bear):
        return "", "neutral"

    majority = "bullish" if bull > bear else "bearish"
    oppose = "bull" if majority == "bearish" else "bear"

    lines = [f"  - [{r.desk}, {c.stance.value}] {c.claim}"
             for r in reports for c in r.accepted]
    block = (
        f"THE OTHER DESKS CONCLUDED ({majority}, {bull:.1f} bull vs {bear:.1f} bear):\n"
        + "\n".join(lines)
        + f"\n\nYour claims must take the '{oppose}' stance, or return none at all.\n\n"
    )
    return block, oppose


def apply_citation_gate(raw: list[Claim], pack: EvidencePack
                        ) -> tuple[list[Claim], list[tuple[Claim, RejectReason]]]:
    """The anti-hallucination mechanism, and it is mechanical rather than aspirational.

    Two failure modes are caught here:
      * a claim with no citations at all -- an unsupported assertion
      * a claim citing an id that is not in the pack -- a FABRICATED citation, which is
        the more dangerous one because it looks rigorous on screen

    Rejected claims are kept, not discarded, so the UI can show the counter. The count
    of things the model tried to sneak through is one of the more honest numbers in
    the whole system.
    """
    accepted: list[Claim] = []
    rejected: list[tuple[Claim, RejectReason]] = []
    valid = pack.ids
    for claim in raw:
        if not claim.claim.strip():
            rejected.append((claim, RejectReason.EMPTY_CLAIM))
        elif not claim.source_ids:
            rejected.append((claim, RejectReason.NO_CITATION))
        elif not set(claim.source_ids) <= valid:
            rejected.append((claim, RejectReason.UNKNOWN_CITATION))
        else:
            accepted.append(claim)
    return accepted, rejected


async def run_desk(desk: Desk, pack: EvidencePack, consensus: str = "",
                   oppose: str = "") -> DeskReport:
    t0 = time.perf_counter()
    report = DeskReport(desk=desk.name, ticker=pack.ticker)
    try:
        data = await chat_json(_prompt(desk, pack, consensus), CLAIMS_SCHEMA,
                               system=SYSTEM)
        raw: list[Claim] = []
        for entry in (data.get("claims") or [])[: desk.max_claims]:
            try:
                raw.append(Claim(**entry))
            except Exception:  # noqa: BLE001
                # Malformed individual claim: drop it rather than failing the desk.
                continue
        report.accepted, report.rejected = apply_citation_gate(raw, pack)
        if oppose:
            # Enforce the dissent mechanically. The model agrees with the consensus it
            # was just shown more often than not, and a "dissent" that echoes the
            # majority is the exact failure this two-pass design exists to remove.
            kept = [c for c in report.accepted if c.stance.value == oppose]
            report.conceded = len(report.accepted) - len(kept)
            report.accepted = kept
    except Exception as exc:  # noqa: BLE001
        report.error = f"{type(exc).__name__}: {exc}"[:160]
    report.latency_ms = int((time.perf_counter() - t0) * 1000)
    return report
