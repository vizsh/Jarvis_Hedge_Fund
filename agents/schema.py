"""Agent output contract.

Everything a desk says must survive Pydantic validation AND the citation gate before it
counts. A 8B model produces inconsistent output often enough that treating its text as
authoritative would be negligent -- in early testing it called a market "downturn" and
tagged the claim `bull` in the same object. That is not a reason to abandon the small
model; it is the reason the gate exists.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Stance(str, Enum):
    BULL = "bull"
    BEAR = "bear"
    NEUTRAL = "neutral"


class RejectReason(str, Enum):
    NO_CITATION = "no_citation"           # the model asserted something with no evidence
    UNKNOWN_CITATION = "unknown_citation"  # it cited evidence that does not exist
    EMPTY_CLAIM = "empty_claim"


class Claim(BaseModel):
    """One assertion from one desk. `source_ids` point into the evidence pack."""
    claim: str
    stance: Stance = Stance.NEUTRAL
    weight: float = Field(default=0.5, ge=0.0, le=1.0)
    source_ids: list[str] = Field(default_factory=list)


class DeskReport(BaseModel):
    desk: str
    ticker: str
    accepted: list[Claim] = Field(default_factory=list)
    rejected: list[tuple[Claim, RejectReason]] = Field(default_factory=list)
    latency_ms: int = 0
    error: str | None = None
    # Red Team only: claims dropped for agreeing with the consensus it was asked to
    # oppose. A high number here is the honest signal that it found no counter-case.
    conceded: int = 0

    @property
    def ok(self) -> bool:
        return self.error is None


class Verdict(BaseModel):
    """Fused output of all desks. Every number here is computed, not generated."""
    ticker: str
    sim_clock: str
    net_stance: float          # -1 fully bearish .. +1 fully bullish
    agreement: float           # share of weight on the majority stance
    evidence_quality: float    # mean confidence of cited evidence
    conviction: float          # |net| * quality, discounted for groupthink
    groupthink: bool
    dissent: str | None = None
    # Red Team claims dropped for siding with the consensus it was asked to oppose.
    conceded: int = 0
    claims_accepted: int = 0
    claims_rejected: int = 0
    model: str = ""


# The JSON schema handed to Ollama. Structured output is far more reliable than
# asking politely for JSON and parsing whatever comes back.
CLAIMS_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "stance": {"type": "string", "enum": ["bull", "bear", "neutral"]},
                    "weight": {"type": "number"},
                    "source_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["claim", "stance", "weight", "source_ids"],
            },
        }
    },
    "required": ["claims"],
}
