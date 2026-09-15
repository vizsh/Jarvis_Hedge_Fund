"""Drive the live backend over the WebSocket, exactly as the frontend will.

    python -m uvicorn backend.app:app --port 8000     # terminal 1
    python tools/demo_backend.py                      # terminal 2

This is the whole demo script end to end. If this runs clean, the frontend has nothing
to do but render the events it prints.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx
import websockets

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

WS = "ws://localhost:8000/ws"
API = "http://localhost:8000"

SCRIPT = [
    # Reset first. The backend session persists across runs, so without this the
    # script inherits the previous run's clock and the verdicts change under you.
    ("reset", "restore the opening fund and clock", 0.5),
    ("boot", None, 2.5),
    ("analyse TCS", "four desks deliberate over point-in-time evidence", 0.5),
    ("buy 30 shares of Persistent", "the firewall blocks it and solves for the size", 0.5),
    ("what if we relax the sector cap to 40%", "policy simulator flips the verdict", 0.5),
    ("rewind to 2020-03-23", "the Covid bottom, in real time", 0.5),
    ("analyse TCS", "same desks, a world that stops at 23 March 2020", 0.5),
    ("show me the portfolio", None, 0.5),
]

INTERESTING = {"boot", "source.status", "clock", "intent", "agent.state", "claim",
               "claim.rejected", "conviction", "proposal", "risk.decision",
               "execution", "speech", "error"}


def render(payload: dict, kind: str) -> str:
    if kind == "boot":
        return payload.get("line", "")
    if kind == "source.status":
        return f"{payload['source']} online, {payload['rows']:,} rows"
    if kind == "clock":
        return f"clock -> {payload['sim_clock'][:10]}"
    if kind == "intent":
        return f"{payload['verb']} {payload.get('ticker') or ''} (via {payload['via']})"
    if kind == "agent.state":
        return f"{payload['desk']}: {payload['state']} {payload.get('note') or ''}"
    if kind == "claim":
        return (f"{payload['desk']:<12} [{payload['stance']:<7}] {payload['claim'][:64]} "
                f"<- {','.join(payload['source_ids'])}")
    if kind == "claim.rejected":
        return f"{payload['desk']:<12} DROPPED ({payload['reason']}) {payload['claim'][:50]}"
    if kind == "conviction":
        line = (f"conviction {payload['score']:.2f}  agreement {payload['agreement']:.2f}"
                f"  net {payload['net_stance']:+.2f}")
        return line + ("   ** GROUPTHINK **" if payload.get("groupthink") else "")
    if kind == "proposal":
        return f"{payload['side']} {payload['shares']} {payload['ticker']} @ {payload['price']:,.2f}"
    if kind == "risk.decision":
        verdict = "APPROVED" if payload["approved"] else "REJECTED"
        bits = [f"{verdict} under {payload['policy_version']}"]
        bits += [f"! {v['code']}: {v['message']}" for v in payload.get("violations", [])]
        if payload.get("remedy"):
            bits.append(f"remedy: {payload['remedy']['explanation']}")
        if cf := payload.get("counterfactual"):
            bits.append(f"counterfactual: was_approved={cf['was_approved']} "
                        f"now_approved={cf['now_approved']}")
        return "\n           ".join(bits)
    if kind == "execution":
        return (f"PAPER FILL {payload['side']} {payload['shares']} {payload['ticker']}"
                f"  NAV {payload['nav_after']:,.0f}")
    if kind == "speech":
        return f"JARVIS: {payload['text']}"
    if kind == "error":
        return f"ERROR in {payload['where']}: {payload['message']}"
    return json.dumps(payload)[:100]


async def main() -> None:
    async with httpx.AsyncClient() as http:
        health = (await http.get(f"{API}/health")).json()
        print(f"\n  backend up: protocol v{health['protocol']}, "
              f"ollama={health['ollama']}\n")

    async with websockets.connect(WS, max_size=None) as socket:
        async def listen() -> None:
            async for raw in socket:
                event = json.loads(raw)
                kind = event["type"]
                if kind in INTERESTING:
                    print(f"  {kind:<14} {render(event['payload'], kind)}")

        pump = asyncio.create_task(listen())
        for command, note, pause in SCRIPT:
            print(f"\n{'=' * 78}")
            print(f"  >>> {command}" + (f"   ({note})" if note else ""))
            print("=" * 78)
            if command == "boot":
                await socket.send(json.dumps({"type": "boot"}))
                await asyncio.sleep(4.0)
                continue
            await socket.send(json.dumps({"type": "command", "text": command}))
            await asyncio.sleep(pause)
            # desks take ~15s; everything else is instant
            await asyncio.sleep(22.0 if "analyse" in command else 1.5)
        pump.cancel()
    print(f"\n{'=' * 78}\n  script complete\n")


if __name__ == "__main__":
    asyncio.run(main())
