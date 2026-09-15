"""Full dry run: walk the demo script, then do the things a nervous presenter does.

    python tools/dry_run.py

The scripted path is the easy half. The half that actually breaks on stage is the
out-of-order half — approving with nothing staged, rewinding mid-analysis, pressing the
same button twice, asking about a ticker that is not in the universe. Each case below
asserts an invariant and reports PASS/FAIL rather than just printing events.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx
import websockets

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

API = "http://localhost:8000"
WS = "ws://localhost:8000/ws"

RULE = "-" * 78
results: list[tuple[bool, str, str]] = []


def check(ok: bool, name: str, detail: str = "") -> None:
    results.append((ok, name, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))


class Listener:
    """Collects events so a step can be asserted on what actually reached the wire."""

    def __init__(self) -> None:
        self.events: list[dict] = []

    async def run(self, ws) -> None:
        async for raw in ws:
            self.events.append(json.loads(raw))

    def since(self, mark: int) -> list[dict]:
        return self.events[mark:]

    def types(self, mark: int) -> list[str]:
        return [e["type"] for e in self.since(mark)]

    def last(self, kind: str, mark: int = 0) -> dict | None:
        hits = [e["payload"] for e in self.since(mark) if e["type"] == kind]
        return hits[-1] if hits else None

    @property
    def mark(self) -> int:
        return len(self.events)


async def cmd(http: httpx.AsyncClient, text: str, wait: float = 2.5) -> None:
    await http.post("/command", json={"text": text})
    await asyncio.sleep(wait)


async def main() -> None:
    async with httpx.AsyncClient(base_url=API, timeout=60) as http:
        health = (await http.get("/health")).json()
        print(f"\n  backend v{health['protocol']} · ollama={health['ollama']} · "
              f"stt={health['stt']['available']}\n{RULE}")
        if not health["ollama"]:
            print("  Ollama is down — the desk steps will fail. Start it first.\n")
            return

    listener = Listener()
    async with websockets.connect(WS, max_size=None) as ws:
        pump = asyncio.create_task(listener.run(ws))
        async with httpx.AsyncClient(base_url=API, timeout=60) as http:

            # ---------------------------------------------------------- scripted path
            print("\n  SCRIPTED PATH\n" + RULE)
            # Pin the preconditions. The scripted walkthrough is the INSTITUTIONAL
            # story; the app now lands on a retail portfolio under retail limits, under
            # which the demo trade is perfectly legal and half these checks are moot.
            await http.post("/profiles/fund")
            await http.post("/portfolios/preset_demo_fund/activate")
            await asyncio.sleep(1.5)
            await cmd(http, "reset", 2.0)

            m = listener.mark
            await http.post("/boot")
            await asyncio.sleep(5.0)
            boot = [e for e in listener.since(m) if e["type"] == "boot"]
            sources = [e for e in listener.since(m) if e["type"] == "source.status"]
            check(len(boot) >= 10, "cold boot emits the full banner", f"{len(boot)} lines")
            check(len(sources) >= 6, "all data sources report in", f"{len(sources)} sources")

            m = listener.mark
            await cmd(http, "analyse TCS", 30.0)
            conv = listener.last("conviction", m)
            claims = [e for e in listener.since(m) if e["type"] == "claim"]
            desks = {e["payload"]["desk"] for e in listener.since(m)
                     if e["type"] == "agent.state" and e["payload"]["state"] == "done"}
            check(conv is not None, "investigation produces a verdict")
            check(len(desks) == 4, "all four desks report", f"{sorted(desks)}")
            check(len(claims) > 0, "claims reach the wire", f"{len(claims)} claims")
            nodes = [e for e in listener.since(m) if e["type"] == "graph.node"]
            check(len(nodes) > 10, "provenance graph is populated", f"{len(nodes)} nodes")

            m = listener.mark
            await cmd(http, "buy 30 shares of Persistent", 3.0)
            dec = listener.last("risk.decision", m)
            check(dec is not None and not dec["approved"], "demo trade is blocked")
            check(bool(dec and dec["violations"][0]["code"] == "SECTOR_LIMIT"),
                  "blocked on the sector cap specifically")
            check(bool(dec and dec.get("remedy") and dec["remedy"]["max_shares"] > 0),
                  "remedy offers a compliant size",
                  f"{dec['remedy']['max_shares']} shares" if dec and dec.get("remedy") else "")

            m = listener.mark
            await cmd(http, "what if we relax the sector cap to 40%", 3.0)
            sim = listener.last("risk.decision", m)
            cf = sim.get("counterfactual") if sim else None
            check(bool(cf and cf["was_approved"] is False and cf["now_approved"] is True),
                  "policy simulator flips the verdict")
            spoken = listener.last("speech", m)
            check(bool(spoken and "still blocks" not in spoken["text"]),
                  "spoken line agrees with the verdict")

            m = listener.mark
            await cmd(http, "rewind to 2020-03-23", 3.0)
            clock = listener.last("clock", m)
            check(bool(clock and clock["sim_clock"].startswith("2020-03-23")),
                  "clock rewinds")
            state = (await http.get("/state")).json()
            check(state["nav"] < 9_000_000, "fund reprices on rewind",
                  f"NAV {state['nav']:,.0f}")
            bars = (await http.get("/prices/TCS.NS")).json()["bars"]
            check(all(b["date"] <= "2020-03-23" for b in bars),
                  "price series is truncated", f"{len(bars)} bars, last {bars[-1]['date']}")

            m = listener.mark
            await cmd(http, "analyse TCS", 30.0)
            conv2 = listener.last("conviction", m)
            check(conv2 is not None, "second investigation completes at the 2020 clock")

            # ---------------------------------------------------------- adversarial
            print(f"\n  OUT-OF-ORDER / PANIC CASES\n{RULE}")

            m = listener.mark
            await cmd(http, "execute", 2.0)
            fills = [e for e in listener.since(m) if e["type"] == "execution"]
            check(len(fills) == 0, "approve with nothing staged does not fill")

            before = (await http.get("/state")).json()
            m = listener.mark
            await cmd(http, "buy 9999 shares of TCS", 2.5)
            after = (await http.get("/state")).json()
            check(before["positions"] == after["positions"],
                  "an absurd order never mutates the book")

            m = listener.mark
            await cmd(http, "analyse ZOMATO", 6.0)
            desks_run = [e for e in listener.since(m) if e["type"] == "agent.state"]
            errs = [e for e in listener.since(m) if e["type"] == "error"]
            check(len(desks_run) == 0,
                  "unknown ticker does not silently analyse a different one")
            check(len(errs) > 0, "unknown ticker is reported to the operator")

            m = listener.mark
            await cmd(http, "accept the remedy", 3.0)
            check(any(e["type"] == "speech" for e in listener.since(m)),
                  "accept with no offer responds instead of failing silently")

            m = listener.mark
            await cmd(http, "rewind to yesterday", 2.0)
            check(any(e["type"] == "error" for e in listener.since(m)),
                  "unparseable date reports instead of silently doing nothing")

            # double-fire the same command, as happens with a sticky key
            pre_double = (await http.get("/state")).json()
            await http.post("/command", json={"text": "buy 30 shares of Persistent"})
            await http.post("/command", json={"text": "buy 30 shares of Persistent"})
            await asyncio.sleep(3.0)
            state = (await http.get("/state")).json()
            check(state["positions"] == pre_double["positions"],
                  "double-fired blocked trade stays blocked")

            # a remedy must not survive a clock change: it was priced on a different book
            await cmd(http, "buy 30 shares of Persistent", 2.5)
            await cmd(http, "rewind to 2020-06-30", 2.5)
            m = listener.mark
            await cmd(http, "accept the remedy", 2.5)
            fills = [e for e in listener.since(m) if e["type"] == "execution"]
            check(len(fills) == 0, "a remedy lapses when the clock moves")

            # replay must lock out live commands
            m = listener.mark
            await http.post("/replay/start", params={"name": "demo", "speed": 8})
            await asyncio.sleep(1.5)
            blocked = (await http.post("/command", json={"text": "analyse INFY"})).json()
            check(blocked.get("accepted") is False, "live commands blocked during replay")
            h = (await http.get("/health")).json()
            check(h["replay"] is True, "health reports replay honestly")
            await http.post("/replay/stop")
            await asyncio.sleep(1.0)
            h = (await http.get("/health")).json()
            check(h["replay"] is False, "replay stops cleanly")

            # reset must restore a clean slate
            # Capture the opening book BEFORE anything mutates it: reset restores the
            # ACTIVE portfolio now, not a hardcoded fund, so the old comparison against
            # seed_fund() was asserting behaviour that no longer exists.
            await cmd(http, "reset", 2.5)
            state = (await http.get("/state")).json()
            check(state["sim_clock"][:4] == "2026", "reset returns the clock to today",
                  state["sim_clock"][:10])
            check(state["portfolio_name"] == "Demo fund"
                  and len(state["positions"]) == 10,
                  "reset restores the active portfolio",
                  f'{state["portfolio_name"]}, {len(state["positions"])} holdings')

        pump.cancel()

    passed = sum(1 for ok, _, _ in results if ok)
    print(f"\n{RULE}\n  {passed}/{len(results)} checks passed")
    for ok, name, detail in results:
        if not ok:
            print(f"    FAILED: {name} {detail}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
