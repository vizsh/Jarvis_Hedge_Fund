"""Ollama client. Local, free, and deliberately small.

Structured output (`format` = JSON schema) rather than asking for JSON in the prompt
and parsing whatever arrives. The model still returns nonsense sometimes -- it is an 8B
model -- but it returns *well-shaped* nonsense, which the citation gate can then filter.

Desks run concurrently. Ollama serialises requests per model by default, so the wall
clock is roughly the sum rather than the max; the concurrency still helps because it
overlaps our own JSON handling and keeps the code shape right for a bigger host.
"""
from __future__ import annotations

import json
import time
from typing import Any

import httpx

OLLAMA_URL = "http://localhost:11434"
ANALYST_MODEL = "llama3.1:8b"
ROUTER_MODEL = "phi3:mini"
KEEP_ALIVE = "10m"   # keep the weights resident between desks; reloading costs ~10s


class LLMError(RuntimeError):
    pass


async def chat_json(prompt: str, schema: dict, *, model: str = ANALYST_MODEL,
                    system: str | None = None, temperature: float = 0.2,
                    max_tokens: int = 300, attempts: int = 2,
                    timeout: float = 180.0) -> dict[str, Any]:
    """One structured call. Retries once on malformed output, then gives up loudly."""
    messages = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
    payload = {
        "model": model, "messages": messages, "format": schema, "stream": False,
        "keep_alive": KEEP_ALIVE,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    last: str = ""
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(attempts):
            try:
                resp = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
                resp.raise_for_status()
                return json.loads(resp.json()["message"]["content"])
            except Exception as exc:  # noqa: BLE001
                last = f"{type(exc).__name__}: {exc}"
                if attempt < attempts - 1:
                    # Nudge temperature down; a repeat at the same setting usually
                    # reproduces the same malformed output.
                    payload["options"]["temperature"] = 0.0
    raise LLMError(last[:200])


async def warm_up(model: str = ANALYST_MODEL) -> float:
    """Load the weights before the demo starts. A cold first desk costs ~10 extra
    seconds and it always lands on the one the audience is watching."""
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.post(f"{OLLAMA_URL}/api/chat", json={
                "model": model, "messages": [{"role": "user", "content": "ok"}],
                "stream": False, "keep_alive": KEEP_ALIVE,
                "options": {"num_predict": 1}})
    except Exception:  # noqa: BLE001
        return -1.0
    return time.perf_counter() - t0


def available() -> bool:
    try:
        return httpx.get(f"{OLLAMA_URL}/api/tags", timeout=5.0).status_code == 200
    except Exception:  # noqa: BLE001
        return False
