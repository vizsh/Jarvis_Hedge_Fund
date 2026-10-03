"""Event bus: one publisher, many WebSocket subscribers.

Every subscriber gets its own bounded queue. If a client stalls, its queue fills and we
drop ITS events rather than blocking the pipeline -- a wedged browser tab must never be
able to stop the agents mid-run during a demo.

A short replay buffer is kept so a client that connects late (or reconnects after the
laptop sleeps) can catch up on the boot sequence instead of staring at a blank screen.
"""
from __future__ import annotations

import asyncio
from collections import deque

from core.events import Event, EventType, ev

MAX_QUEUE = 256
REPLAY = 400


class EventBus:
    def __init__(self) -> None:
        self._subs: set[asyncio.Queue[Event]] = set()
        self._replay: deque[Event] = deque(maxlen=REPLAY)
        self.dropped = 0

    def subscribe(self) -> asyncio.Queue[Event]:
        q: asyncio.Queue[Event] = asyncio.Queue(maxsize=MAX_QUEUE)
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[Event]) -> None:
        self._subs.discard(q)

    def history(self) -> list[Event]:
        return list(self._replay)

    def publish(self, event: Event) -> Event:
        self._replay.append(event)
        for q in self._subs:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                self.dropped += 1
        return event

    # Optional hook: given the payload of a SPEECH event, return the payload to emit now, or
    # None to hold it back (the hook then emits a translated version itself). This is the
    # single place every spoken line passes through, so no code path can talk in the wrong
    # language -- the English announcement that played over Hindi text came from a path
    # that never went near the translator.
    speech_filter = None

    def emit(self, type_: EventType, **payload) -> Event | None:
        if type_ is EventType.SPEECH and self.speech_filter is not None:
            payload = self.speech_filter(payload)
            if payload is None:
                return None
        return self.publish(ev(type_, **payload))

    @property
    def subscribers(self) -> int:
        return len(self._subs)
