"""Record a run, replay it later with original timing.

This is demo insurance, and it is the difference between a bad venue costing you a
slide and costing you the whole demo. Ollama can die, the GPU can get throttled, the
mic can vanish, the snapshot can be missing — replay needs none of them.

For that to be true, a recording has to be **self-contained**. Recording only the
WebSocket event stream is not enough: the panels also fetch `/state` and `/prices`, and
during replay those would answer from a live session that knows nothing about the
recorded run, so the HUD would show 2026 numbers under a 2020 clock. So we capture
state snapshots alongside the events and serve those instead while replaying.

Honesty note: replay raises a visible REPLAY flag in the UI and in `/health`. A fallback
you cannot distinguish from the live system is a lie waiting to be found, and "yes,
that clip is a recording, here is the live one" is a fine answer to have ready.
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.bus import EventBus
from core.events import Event, EventType

RECORDINGS = Path(__file__).resolve().parent.parent / "data" / "recordings"
STATE_EVENTS = {"clock", "execution", "risk.decision", "telemetry"}


@dataclass
class Recorder:
    """Subscribes to the bus and writes a timestamped JSONL take."""
    bus: EventBus
    name: str
    session: Any = None
    started: float = field(default_factory=time.monotonic)
    rows: list[dict] = field(default_factory=list)
    _task: asyncio.Task | None = None

    def start(self) -> None:
        queue = self.bus.subscribe()
        self.started = time.monotonic()
        self.rows = []
        # Snapshot the opening state so a replay does not begin on whatever the live
        # session happens to hold.
        self._snapshot()

        async def pump() -> None:
            try:
                while True:
                    event = await queue.get()
                    self.rows.append({
                        "t": round(time.monotonic() - self.started, 3),
                        "kind": "event",
                        "data": json.loads(event.dumps()),
                    })
                    if event.type.value in STATE_EVENTS:
                        self._snapshot()
            except asyncio.CancelledError:
                pass
            finally:
                self.bus.unsubscribe(queue)

        self._task = asyncio.create_task(pump())

    def _snapshot(self) -> None:
        if not self.session:
            return
        try:
            self.rows.append({
                "t": round(time.monotonic() - self.started, 3),
                "kind": "state",
                "data": self.session.snapshot(),
            })
        except Exception:  # noqa: BLE001
            pass  # a broken snapshot must never kill the run being recorded

    def stop(self) -> Path:
        if self._task:
            self._task.cancel()
            self._task = None
        RECORDINGS.mkdir(parents=True, exist_ok=True)
        path = RECORDINGS / f"{self.name}.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for row in self.rows:
                fh.write(json.dumps(row, separators=(",", ":")) + "\n")
        return path


@dataclass
class Player:
    """Replays a take through the bus, preserving the original gaps."""
    bus: EventBus
    path: Path
    speed: float = 1.0
    max_gap: float = 3.0     # a 14s desk wait is dead air on stage; cap every pause
    active: bool = False
    state: dict | None = None
    on_clock: Any = None     # called with each replayed sim_clock, to keep /prices in step
    _task: asyncio.Task | None = None
    progress: float = 0.0

    @property
    def name(self) -> str:
        return self.path.stem

    def load(self) -> list[dict]:
        rows = []
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    def start(self, on_finish=None) -> None:
        rows = self.load()
        self.active = True
        self.progress = 0.0

        # Clear the HUD before the take starts. You press R *because* the live run went
        # wrong, so there is almost always a half-built graph and a stale verdict on
        # screen; without this the recording plays on top of the wreckage.
        self.bus.emit(EventType.GRAPH_RESET)

        async def play() -> None:
            previous = 0.0
            total = rows[-1]["t"] if rows else 1.0
            try:
                for row in rows:
                    gap = min((row["t"] - previous) / max(self.speed, 0.05), self.max_gap)
                    if gap > 0.001:
                        await asyncio.sleep(gap)
                    previous = row["t"]
                    self.progress = row["t"] / total if total else 1.0

                    if row["kind"] == "state":
                        # Served by /state while replaying, so the panels agree with
                        # the event stream instead of with the live session.
                        self.state = row["data"]
                        continue

                    payload = row["data"]
                    if payload.get("type") == "clock" and self.on_clock:
                        self.on_clock(payload["payload"]["sim_clock"])
                    self.bus.publish(Event(
                        v=payload.get("v", 1),
                        type=EventType(payload["type"]),
                        seq=payload.get("seq", 0),
                        ts=time.time(),
                        payload=payload.get("payload", {}),
                    ))
            except asyncio.CancelledError:
                pass
            finally:
                self.active = False
                self.progress = 1.0
                if on_finish:
                    on_finish()

        self._task = asyncio.create_task(play())

    def stop(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None
        self.active = False


def list_takes() -> list[dict]:
    if not RECORDINGS.exists():
        return []
    out = []
    for path in sorted(RECORDINGS.glob("*.jsonl")):
        try:
            lines = sum(1 for _ in path.open(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            lines = 0
        out.append({"name": path.stem, "rows": lines,
                    "bytes": path.stat().st_size,
                    "modified": path.stat().st_mtime})
    return out
