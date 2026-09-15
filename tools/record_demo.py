"""Capture a golden take of the demo, for replay when the venue is hostile.

    python -m uvicorn backend.app:app --port 8000     # terminal 1
    python tools/record_demo.py                       # terminal 2, ~2 minutes

Runs the script from config/script.yaml against the live backend while recording, then
writes data/recordings/demo.jsonl. After that:

    curl -X POST "http://localhost:8000/replay/start?name=demo"

or press R in the HUD. Replay needs no Ollama, no mic, and no snapshot database.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

API = "http://localhost:8000"
# The desks genuinely take ~15s; anything else settles instantly.
SLOW = 26.0
FAST = 2.5


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="demo")
    ap.add_argument("--api", default=API)
    args = ap.parse_args()

    async with httpx.AsyncClient(base_url=args.api, timeout=60) as http:
        health = (await http.get("/health")).json()
        if not health.get("ollama"):
            print("\n  Ollama is down. Recording a take without it would capture the\n"
                  "  failure, which is the opposite of what this is for.\n")
            return

        script = (await http.get("/script")).json()
        steps = script.get("steps", [])
        print(f"\n  Recording '{args.name}' — {len(steps)} steps\n{'-' * 74}")

        # Reset first so the take always starts from the opening fund, whatever the
        # session was doing beforehand.
        await http.post("/command", json={"text": "reset"})
        await asyncio.sleep(1.5)
        await http.post("/record/start", params={"name": args.name})

        for i, step in enumerate(steps, 1):
            command = str(step.get("command", "")).strip()
            print(f"  [{i}/{len(steps)}] {step.get('key', ''):<12} {command}")
            if command == "@boot":
                await http.post("/boot")
                await asyncio.sleep(5.0)
                continue
            if command in ("@none", ""):
                # Narration-only beat. Still worth a pause so the replay has the same
                # rhythm as the live run.
                await asyncio.sleep(2.0)
                continue
            await http.post("/command", json={"text": command})
            await asyncio.sleep(SLOW if "analyse" in command else FAST)

        result = (await http.post("/record/stop")).json()
        print(f"{'-' * 74}\n  saved {result.get('rows')} rows -> {result.get('path')}\n")
        print("  replay it with:")
        print(f'    curl -X POST "{args.api}/replay/start?name={args.name}"')
        print("  or press R in the HUD.\n")


if __name__ == "__main__":
    asyncio.run(main())
