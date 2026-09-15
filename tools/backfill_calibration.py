"""Run the desks across historical dates so calibration has something real to score.

    python tools/backfill_calibration.py              # ~4 min, 18 investigations
    python tools/backfill_calibration.py --dates 10 --tickers TCS.NS INFY.NS

Each investigation runs at a past clock, so `PointInTimeStore` hides everything after
it and the forward return needed to grade the call is already sitting in the snapshot.

Dates are chosen to span regimes rather than clustering in one market — a desk that
only ever saw a bull run tells you nothing about its calibration.

Honest framing, and it belongs on the slide: point-in-time control stops the desks
SEEING the future in their inputs. It does nothing about the base model having read
2020 during training. Treat the result as an upper bound on skill.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.llm import available, warm_up                 # noqa: E402
from agents.orchestrator import investigate               # noqa: E402
from agents.persist import save_run                       # noqa: E402
from backend.calibration import ensure_sim_clock_column, score  # noqa: E402
from core.db import init                                  # noqa: E402
from core.pit import PointInTimeStore                     # noqa: E402

# Spread across regimes: pre-Covid, crash, recovery, the 2022 drawdown, and calm.
DATES = [
    "2019-11-15", "2020-02-20", "2020-03-23", "2020-06-30", "2020-11-10",
    "2021-04-15", "2021-10-20", "2022-01-18", "2022-06-16", "2022-11-08",
    "2023-03-14", "2023-09-12", "2024-02-20", "2024-08-05", "2025-01-15",
]
TICKERS = ["TCS.NS", "INFY.NS", "HDFCBANK.NS"]
RULE = "-" * 78


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dates", type=int, default=6, help="how many dates to sample")
    ap.add_argument("--tickers", nargs="*", default=TICKERS)
    ap.add_argument("--db", default="data/snapshot.db")
    args = ap.parse_args()

    if not available():
        print("\n  Ollama is not reachable. Start it and retry.\n")
        return

    conn = init(args.db)
    ensure_sim_clock_column(conn)

    # Even spread across the window rather than the first N, which would all be Covid.
    step = max(1, len(DATES) // args.dates)
    dates = DATES[::step][: args.dates]
    total = len(dates) * len(args.tickers)

    print(f"\n  Backfilling calibration: {len(dates)} dates x {len(args.tickers)} "
          f"tickers = {total} investigations")
    print(f"  ~{total * 15 // 60} min at ~15s each\n{RULE}")
    await warm_up()

    done = 0
    for date in dates:
        pit = PointInTimeStore(conn, date)
        for ticker in args.tickers:
            if pit.last_close(ticker) is None:
                print(f"  {date}  {ticker:<14} no data at this clock, skipped")
                continue
            pack, reports, verdict = await investigate(pit, ticker)
            save_run(conn, reports, verdict)
            done += 1
            failed = [r.desk for r in reports if r.error]
            print(f"  {date}  {ticker:<14} {verdict.claims_accepted} claims  "
                  f"net {verdict.net_stance:+.2f}  conviction {verdict.conviction:.2f}"
                  f"{'  FAILED: ' + ','.join(failed) if failed else ''}"
                  f"  [{done}/{total}]")

    print(f"{RULE}\n")
    result = score(conn)
    print(f"  CALIBRATION  ({result['total_scored']} directional claims scored, "
          f"{result['unresolved']} unresolved)\n")
    print(f"  {'DESK':<14} {'N':>4} {'HIT':>7} {'BRIER':>7}   vs coin flip")
    for d in result["desks"]:
        verdict = "better" if d["beats_coin_flip"] else "WORSE"
        print(f"  {d['desk']:<14} {d['n']:>4} {d['hit_rate']:>6.1%} {d['brier']:>7.3f}"
              f"   {verdict}")
    print(f"\n  A Brier of {result['neutral_brier']} is what you score by always saying "
          f"'coin flip'.\n  Lower is better; above it is worse than useless.\n")
    if result["sample_warning"]:
        print("  Sample is small — treat these as indicative, not established.\n")
    print(f"  {result['caveat']}\n")


if __name__ == "__main__":
    asyncio.run(main())
