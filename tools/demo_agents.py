"""The full pass: PIT evidence -> four desks -> citation gate -> fused verdict.

    python tools/demo_agents.py                      # today
    python tools/demo_agents.py --clock 2020-03-23   # the Covid bottom, in real time
    python tools/demo_agents.py --ticker INFY.NS

Everything the desks see comes through PointInTimeStore, so rewinding the clock really
does change what they can reason about.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.llm import ANALYST_MODEL, available, warm_up   # noqa: E402
from agents.orchestrator import investigate                 # noqa: E402
from core.db import connect                                 # noqa: E402
from core.pit import PointInTimeStore                       # noqa: E402

RULE = "-" * 78


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", default="TCS.NS")
    ap.add_argument("--clock", default="2026-09-01")
    args = ap.parse_args()

    if not available():
        print("\n  Ollama is not reachable at localhost:11434. Start it and retry.\n")
        return

    print(f"\n  warming {ANALYST_MODEL} ...", end=" ", flush=True)
    print(f"{warm_up.__name__} {await warm_up():.1f}s")

    pit = PointInTimeStore(connect("data/snapshot.db"), args.clock)
    print(f"\n  INVESTIGATE {args.ticker}   clock {args.clock}   model {ANALYST_MODEL}")

    pack, reports, verdict = await investigate(pit, args.ticker)
    print(f"  evidence pack: {len(pack.items)} items, all published on or before "
          f"{args.clock}\n{RULE}")

    for r in reports:
        head = f"  {r.desk:<12} {r.latency_ms / 1000:>5.1f}s"
        if r.error:
            print(f"{head}  FAILED  {r.error}")
            continue
        print(f"{head}  {len(r.accepted)} accepted, {len(r.rejected)} rejected")
        for c in r.accepted:
            print(f"      [{c.stance.value:<7} w={c.weight:.2f}] {c.claim}")
            print(f"      {'':<17}cites {', '.join(c.source_ids)}")
        for c, reason in r.rejected:
            print(f"      [DROPPED {reason.value}] {c.claim[:64]}")

    print(RULE)
    print(f"  net stance        {verdict.net_stance:+.2f}   "
          f"(-1 bearish .. +1 bullish)")
    print(f"  agreement         {verdict.agreement:.2f}")
    print(f"  evidence quality  {verdict.evidence_quality:.2f}")
    print(f"  CONVICTION        {verdict.conviction:.2f}")
    if verdict.groupthink:
        print("  ** GROUPTHINK - LOW INFORMATION: desks agreed and the Red Team found\n"
              "     no counter-case. Conviction discounted, not confirmed. **")
    if verdict.dissent:
        print(f"  dissent           {verdict.dissent}")
    print(f"\n  claims accepted {verdict.claims_accepted}  |  "
          f"rejected for citation failure {verdict.claims_rejected}")
    print(f"{RULE}\n")


if __name__ == "__main__":
    asyncio.run(main())
