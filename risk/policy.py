"""Policy loading. Declarative, versioned, hot-swappable for the what-if simulator."""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

POLICY_PATH = Path(__file__).resolve().parent.parent / "config" / "policy.yaml"
PROFILES_PATH = Path(__file__).resolve().parent.parent / "config" / "policies.yaml"


class Limits(BaseModel):
    max_position_pct: float = 0.05
    max_sector_pct: float = 0.30
    min_cash_pct: float = 0.10
    max_drawdown_pct: float = 0.05


class Execution(BaseModel):
    cost_bps: float = 15.0
    allow_short: bool = False
    allow_fractional: bool = False

    @property
    def cost(self) -> float:
        return self.cost_bps / 10_000.0


class Governance(BaseModel):
    broker_execution: bool = False
    require_citations: bool = True
    require_human_approval: bool = True


class Policy(BaseModel):
    version: str = "v1"
    name: str = "default"
    limits: Limits = Field(default_factory=Limits)
    execution: Execution = Field(default_factory=Execution)
    governance: Governance = Field(default_factory=Governance)

    profile: str = "fund"

    @classmethod
    def load(cls, path: Path | str = POLICY_PATH) -> "Policy":
        return cls(**yaml.safe_load(Path(path).read_text(encoding="utf-8")))

    @classmethod
    def profiles(cls, path: Path | str = PROFILES_PATH) -> dict:
        return yaml.safe_load(Path(path).read_text(encoding="utf-8"))

    @classmethod
    def from_profile(cls, key: str | None = None,
                     path: Path | str = PROFILES_PATH) -> "Policy":
        """Load a named profile.

        Governance is read from the top level, never from the profile: broker
        execution, citations and human approval are not things a profile gets to relax.
        """
        cfg = cls.profiles(path)
        key = key or cfg.get("default", "retail")
        spec = cfg["profiles"].get(key) or cfg["profiles"][cfg["default"]]
        return cls(version=f"{key}-v1", name=spec["name"], profile=key,
                   limits=Limits(**spec["limits"]),
                   execution=Execution(**spec.get("execution", {})),
                   governance=Governance(**cfg.get("governance", {})))

    def with_limit(self, **overrides: float) -> "Policy":
        """Used by the policy simulator: `policy.with_limit(max_sector_pct=0.35)`."""
        data = self.model_dump()
        data["limits"].update(overrides)
        data["version"] = f"{self.version}+sim"
        return Policy(**data)

    def describe(self) -> str:
        lim = self.limits
        return (f"no more than {lim.max_position_pct:.0%} in one stock, "
                f"{lim.max_sector_pct:.0%} in one industry, and at least "
                f"{lim.min_cash_pct:.0%} kept in cash")
