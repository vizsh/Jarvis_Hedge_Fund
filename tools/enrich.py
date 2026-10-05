"""Fetch the richer company data for every company in the universe (network; a few minutes). Safe to re-run: each
run adds a dated snapshot, which is how ownership trends accumulate."""
from __future__ import annotations

import sys
import time

from core import universe
from core.db import DB_PATH, init
from ingest.base import Writer
from ingest.enrich import fetch_enriched


def main(tickers: list[str] | None = None) -> None:
    conn = init(str(DB_PATH))
    w = Writer(conn)
    tickers = tickers or [t for t in universe.tickers() if t.upper().endswith((".NS", ".BO"))]
    ok = 0
    for i, tk in enumerate(tickers, 1):
        try:
            sigs = fetch_enriched(tk)
            w.signals(sigs)
            ok += 1 if sigs else 0
            print(f"[{i}/{len(tickers)}] {tk}: {len(sigs)} signals", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"[{i}/{len(tickers)}] {tk}: failed ({type(e).__name__})", flush=True)
        time.sleep(0.4)
    conn.commit()
    print(f"done: {ok}/{len(tickers)} companies enriched")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
