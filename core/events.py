"""FROZEN WebSocket event contract.

This is the single interface between backend and frontend. Freeze it now; build the
frontend against `mock_boot_sequence()` immediately so the UI is demoable from hour 4
and every later step just swaps a mock for something real.

Rule: never remove or retype a field. Add optional fields only.
"""
from __future__ import annotations

import json
import time
from enum import Enum
from itertools import count
from typing import Any, Literal

from pydantic import BaseModel, Field

PROTOCOL_VERSION = 1


class EventType(str, Enum):
    # --- phase 0: cold boot ---
    BOOT = "boot"                      # one terminal line of the boot spew
    SOURCE_STATUS = "source.status"    # a data source came online / failed

    # --- time machine ---
    CLOCK = "clock"                    # sim clock moved; everything must re-render

    # --- input ---
    TRANSCRIPT = "transcript"          # STT partial/final
    INTENT = "intent"                  # parsed, typed command

    # --- agent mesh ---
    AGENT_STATE = "agent.state"        # idle|thinking|done|failed per desk
    CLAIM = "claim"                    # an agent claim WITH citations
    CLAIM_REJECTED = "claim.rejected"  # dropped: no citations. This is the anti-hallucination counter.
    CONSENSUS = "consensus"            # the analysts have finished: what they lean to, and what the Red Team must oppose
    CONVICTION = "conviction"          # fused score + groupthink flag

    # --- provenance graph ---
    GRAPH_NODE = "graph.node"
    GRAPH_EDGE = "graph.edge"
    GRAPH_RESET = "graph.reset"

    # --- governance ---
    PROPOSAL = "proposal"              # trade proposal from the desks
    RISK_DECISION = "risk.decision"    # APPROVED|REJECTED + violations + remedial delta
    EXECUTION = "execution"            # paper fill written to the ledger

    # --- ambient ---
    TELEMETRY = "telemetry"            # the always-on rail: latencies, counters
    SPEECH = "speech"                  # TTS chunk (drives the orb's speaking state)
    ERROR = "error"


AgentState = Literal["idle", "thinking", "done", "failed"]
OrbState = Literal["idle", "listening", "thinking", "speaking", "alert"]

_seq = count(1)


class Event(BaseModel):
    """Every message on the wire is one of these."""
    v: int = PROTOCOL_VERSION
    type: EventType
    seq: int = Field(default_factory=lambda: next(_seq))
    ts: float = Field(default_factory=time.time)
    payload: dict[str, Any] = Field(default_factory=dict)

    def dumps(self) -> str:
        return json.dumps(self.model_dump(mode="json"), separators=(",", ":"))


def ev(type_: EventType, **payload: Any) -> Event:
    return Event(type=type_, payload=payload)


# --------------------------------------------------------------------------------------
# Payload shapes — documented here so the frontend can be written before the backend is.
# --------------------------------------------------------------------------------------
PAYLOAD_SHAPES: dict[EventType, dict[str, str]] = {
    EventType.BOOT:            {"line": "str", "level": "'ok'|'warn'|'fail'", "delay_ms": "int"},
    EventType.SOURCE_STATUS:   {"source": "str", "online": "bool", "rows": "int", "latency_ms": "int"},
    EventType.CLOCK:           {"sim_clock": "iso8601", "live": "bool"},
    EventType.TRANSCRIPT:      {"text": "str", "final": "bool"},
    EventType.INTENT:          {"verb": "str", "ticker": "str|None", "args": "dict"},
    EventType.AGENT_STATE:     {"desk": "str", "state": "AgentState", "note": "str|None"},
    EventType.CLAIM:           {"desk": "str", "claim": "str", "stance": "'bull'|'bear'|'neutral'",
                                "weight": "float", "source_ids": "list[str]"},
    EventType.CLAIM_REJECTED:  {"desk": "str", "claim": "str", "reason": "str"},
    EventType.CONVICTION:      {"score": "float", "agreement": "float", "groupthink": "bool",
                                "dissent": "str|None"},
    EventType.GRAPH_NODE:      {"id": "str", "label": "str",
                                "kind": "'ticker'|'source'|'fact'|'claim'|'risk'",
                                "detail": "str|None", "uri": "str|None"},
    EventType.GRAPH_EDGE:      {"src": "str", "dst": "str", "kind": "str"},
    EventType.GRAPH_RESET:     {},
    EventType.PROPOSAL:        {"ticker": "str", "side": "'BUY'|'SELL'", "shares": "int",
                                "price": "float", "rationale": "str"},
    EventType.RISK_DECISION:   {"approved": "bool", "violations": "list[Violation]",
                                "remedy": "dict|None", "policy_version": "str"},
    EventType.EXECUTION:       {"ticker": "str", "side": "str", "shares": "int",
                                "price": "float", "nav_after": "float"},
    EventType.TELEMETRY:       {"claims_rejected": "int", "violations_blocked": "int",
                                "model": "str", "tick": "int", "orb": "OrbState"},
    EventType.SPEECH:          {"text": "str", "final": "bool"},
    EventType.ERROR:           {"where": "str", "message": "str"},
}


def mock_boot_sequence() -> list[Event]:
    """Phase 0 cold boot. Build the frontend against this before any backend exists."""
    lines = [
        ("JARVIS // ALPHA OS  v0.1  — glass-box governance layer", "ok", 40),
        ("resolving local inference host ................ ollama:11434", "ok", 120),
        ("loading analyst model ......................... llama3.1:8b", "ok", 260),
        ("loading intent router ......................... phi3:mini", "ok", 140),
        ("loading embedder ............................. nomic-embed-text", "ok", 120),
        ("mounting frozen snapshot ...................... data/snapshot.db", "ok", 200),
        ("point-in-time guard ........................... ARMED", "ok", 160),
        ("citation enforcement .......................... ARMED", "ok", 100),
        ("risk policy ................................... v1 loaded (4 limits)", "ok", 180),
        ("broker execution .............................. DISABLED (paper only)", "warn", 220),
        ("ALL SUBSYSTEMS NOMINAL", "ok", 300),
    ]
    return [ev(EventType.BOOT, line=l, level=lv, delay_ms=d) for l, lv, d in lines]
