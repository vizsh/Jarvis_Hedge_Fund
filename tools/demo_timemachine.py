"""The Time Machine, running against the real frozen snapshot.

    python tools/demo_timemachine.py

This is the claim no competing agent repo can make. Published 2026 work shows LLM
trading agents fail out-of-sample once lookahead is controlled, because the model has
already read the outcomes. Here the agents cannot read anything the clock has not
reached -- not because we asked them nicely, but because `PointInTimeStore` is the only
door into the data and it filters on `published_at`.

Watch the price, the headline count and the macro rails change as the clock moves, and
note that the yfinance trailing ratios DISAPPEAR when you rewind. They are snapshot-only
data with no history; showing a 2026 P/E on a 2020 dashboard would be a lookahead bug
with good lighting.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.db import init            # noqa: E402
from core.pit import PointInTimeStore  # noqa: E402

TICKER = "TCS.NS"
STOPS = [
    ("2020-01-15", "Before anyone had heard of it"),
    ("2020-02-20", "Two days before the peak"),
    ("2020-03-23", "The bottom, in real time"),
    ("2020-06-30", "Recovery underway"),
    ("2026-09-01", "Today"),
]
RULE = "-" * 78


def main() -> None:
    conn = init("data/snapshot.db")
    pit = PointInTimeStore(conn, STOPS[0][0])

    print(f"\n  TIME MACHINE -- {TICKER}, read only through PointInTimeStore\n{RULE}")
    print(f"  {'CLOCK':<12} {'CLOSE':>9} {'PRICES':>7} {'TONE':>7} {'10Y':>7} "
          f"{'VIX':>7}  {'P/E':>7}")
    print(RULE)

    for when, label in STOPS:
        pit.set_clock(when)
        close = pit.last_close(TICKER)
        counts = pit.visible_counts()
        tone = pit.latest(TICKER, "news_tone")   # GDELT global press tone
        # macro signals carry no ticker
        rates = pit.signals(kind="dgs10", limit=1)
        vix = pit.signals(kind="vixcls", limit=1)
        pe = pit.latest(TICKER, "pe_ratio")

        print(f"  {when:<12} {close or 0:>9,.0f} {counts['prices']:>7,} "
              f"{(tone.value_num if tone else 0):>7.2f} "
              f"{(rates[0].value_num if rates else 0):>7.2f} "
              f"{(vix[0].value_num if vix else 0):>7.2f}  "
              f"{(f'{pe.value_num:.1f}' if pe else '--'):>7}")
        print(f"  {'':<12} {label}")

    print(RULE)
    pit.set_clock("2020-02-20")
    peak = pit.last_close(TICKER)
    pit.set_clock("2020-03-23")
    trough = pit.last_close(TICKER)
    print(f"\n  At 2020-02-20 the agents see {peak:,.0f} and nothing else. The drawdown to "
          f"{trough:,.0f}\n  ({(trough / peak - 1) * 100:.1f}%) does not exist yet in any "
          f"query they can make.\n")
    print("  Note the P/E column: it is blank for every historical clock. yfinance only\n"
          "  serves today's ratio, so it is stamped at ingest time and correctly vanishes\n"
          "  on rewind rather than leaking 2026 knowledge into 2020.\n")


if __name__ == "__main__":
    main()
