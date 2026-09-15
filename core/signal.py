"""The Signal primitive.

Every one of the six data sources normalises into this. Two payoffs:
  1. multi-source ingestion becomes tractable (one table, one writer)
  2. the provenance graph populates itself — a Signal already carries its own citation
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SourceType(str, Enum):
    PRICE = "price"              # yfinance OHLC
    FUNDAMENTAL = "fundamental"  # EDGAR companyfacts, yfinance
    ANNOUNCEMENT = "announcement"  # NSE corporate filings
    NEWS = "news"                # Google News RSS
    TONE = "tone"                # GDELT machine-coded tone
    MACRO = "macro"              # FRED, RBI
    DERIVED = "derived"          # computed indicator (RSI, SMA) — still carries parents


class Latency(str, Enum):
    REALTIME = "realtime"
    DAILY = "daily"
    QUARTERLY = "quarterly"


def _utc(v: Any) -> datetime:
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v, tz=timezone.utc)
    if isinstance(v, str):
        v = datetime.fromisoformat(v.replace("Z", "+00:00"))
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    return v.astimezone(timezone.utc)


class Signal(BaseModel):
    """One observation, with the two timestamps that make replay honest.

    as_of        — the instant the fact describes (e.g. quarter end 2024-03-31)
    published_at — the instant the fact became KNOWABLE (e.g. filing date 2024-05-14)

    Point-in-time filtering uses published_at, never as_of. Filtering on as_of is the
    classic lookahead bug: a Q1 result is stamped March but nobody could read it
    until May.
    """
    id: str
    ticker: str | None = None
    kind: str                       # "close", "pe_ratio", "headline", "repo_rate", ...
    source_type: SourceType
    value_num: float | None = None
    value_text: str | None = None

    as_of: datetime
    published_at: datetime

    source_name: str                # "yfinance", "EDGAR", "GDELT", ...
    source_uri: str | None = None   # click-through target in the provenance graph
    confidence: float = 1.0
    latency_class: Latency = Latency.DAILY

    @field_validator("as_of", "published_at", mode="before")
    @classmethod
    def _coerce(cls, v: Any) -> datetime:
        return _utc(v)

    @field_validator("published_at")
    @classmethod
    def _publish_not_before_asof(cls, v: datetime, info: Any) -> datetime:
        as_of = info.data.get("as_of")
        if as_of and v < as_of:
            # A fact published before the period it describes is a data bug, and
            # silently accepting it reintroduces exactly the lookahead we're preventing.
            raise ValueError(f"published_at {v} precedes as_of {as_of} for {info.data.get('kind')}")
        return v

    @property
    def value(self) -> float | str | None:
        return self.value_num if self.value_num is not None else self.value_text

    def citation(self) -> dict[str, Any]:
        """What the provenance graph renders when you click the node."""
        return {
            "id": self.id,
            "source": self.source_name,
            "uri": self.source_uri,
            "kind": self.kind,
            "as_of": self.as_of.isoformat(),
            "published_at": self.published_at.isoformat(),
            "value": self.value,
        }
