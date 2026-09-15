"""Build the frozen snapshot. Run once, walk away, keep coding.

    python tools/ingest.py                 # everything
    python tools/ingest.py --only prices   # one source
    python tools/ingest.py --skip nse      # dodge a flaky endpoint

A dead source degrades the run, it never fails it. NSE in particular goes down without
warning, and the demo must not depend on any single endpoint being alive.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.db import DB_PATH, init                      # noqa: E402
from ingest import sources as S                        # noqa: E402
from ingest.base import PitSafety, SourceResult, Writer, utcnow  # noqa: E402

CONFIG = Path(__file__).resolve().parent.parent / "config" / "universe.yaml"
RULE = "-" * 78


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DB_PATH))
    ap.add_argument("--only", nargs="*", default=None,
                    help="prices ratios quarterly edgar news gdelt fred nse")
    ap.add_argument("--skip", nargs="*", default=["nse"])
    args = ap.parse_args()

    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    india = list(cfg["india"]["sector_map"])
    us = list(cfg["us"]["sector_map"])
    tickers = india + us
    start = str(cfg.get("history_start", "2019-06-01"))
    since = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)

    # The benchmark index is priced like any other series so the X-ray can compare
    # a portfolio against it.
    benchmark = (cfg.get("benchmark") or {}).get("ticker")
    if benchmark:
        tickers = tickers + [benchmark]

    # GDELT and Google News need names, not tickers -- "TCS.NS" returns nothing useful.
    queries = {t: t.replace(".NS", "").replace("BANK", " Bank") + " stock"
               for t in tickers if not t.startswith("^")}

    def want(name: str) -> bool:
        if args.only:
            return name in args.only
        return name not in (args.skip or [])

    conn = init(args.db)
    w = Writer(conn)
    results: list[SourceResult] = []

    print(f"\n  Building frozen snapshot -> {args.db}")
    print(f"  {len(india)} Indian + {len(us)} US tickers, history from {start}\n{RULE}")

    if want("prices"):
        rows, r = S.fetch_prices(tickers, start)
        w.prices(rows)
        results.append(r)
        print("  " + r.status_line)

    if want("ratios"):
        sigs, r = S.fetch_yf_fundamentals(tickers)
        w.signals(sigs)
        results.append(r)
        print("  " + r.status_line)

    if want("quarterly"):
        sigs, r = S.fetch_yf_quarterly(tickers)
        w.signals(sigs)
        results.append(r)
        print("  " + r.status_line)

    if want("edgar"):
        sigs, r = S.fetch_edgar(cfg["us"]["cik"], since)
        w.signals(sigs)
        results.append(r)
        print("  " + r.status_line)

    if want("news"):
        # Bounded: ~1.5s per ticker, and 50 of them would add a minute for headlines
        # only a handful of names actually need.
        picked = cfg.get("news_tickers") or list(queries)
        rows, r = S.fetch_google_news(
            {t: queries[t] for t in picked if t in queries})
        w.documents(rows)
        results.append(r)
        print("  " + r.status_line)

    if want("gdelt"):
        picked = cfg.get("gdelt_tickers") or list(queries)
        sigs, r = S.fetch_gdelt_tone(
            {t: queries[t] for t in picked if t in queries}, since)
        w.signals(sigs)
        results.append(r)
        print("  " + r.status_line)

    if want("fred"):
        sigs, r = S.fetch_fred(cfg["macro"]["fred_series"], since)
        w.signals(sigs)
        results.append(r)
        print("  " + r.status_line)

    if want("nse"):
        rows, r = S.fetch_nse_announcements()
        w.documents(rows)
        results.append(r)
        print("  " + r.status_line)

    for r in results:
        w.record_source(r)

    print(RULE)
    online = [r for r in results if r.online]
    total = sum(r.rows for r in online)
    print(f"  {len(online)}/{len(results)} sources online, {total:,} rows\n")

    # The honesty report. Worth putting on a slide: it is the difference between
    # claiming point-in-time discipline and demonstrating it per source.
    print("  POINT-IN-TIME HONESTY")
    for tier, note in [
        (PitSafety.EXACT, "publication date known -- replay is trustworthy"),
        (PitSafety.APPROXIMATED, "statutory lag applied -- directionally honest"),
        (PitSafety.SNAPSHOT_ONLY, "no history -- vanishes on rewind, by design"),
    ]:
        names = [r.name for r in online if r.pit_safety is tier]
        if names:
            print(f"    {tier.value:<14} {', '.join(names)}")
            print(f"    {'':<14} {note}")

    counts = {t: conn.execute(f"SELECT COUNT(*) c FROM {t}").fetchone()["c"]
              for t in ("prices", "signals", "documents")}
    print(f"\n  SNAPSHOT  prices={counts['prices']:,}  signals={counts['signals']:,}  "
          f"documents={counts['documents']:,}\n")

    if noisy := [r for r in results if r.warnings]:
        print("  WARNINGS (partial failures, rows still written):")
        for r in noisy:
            for wmsg in r.warnings:
                print(f"    {r.name}: {wmsg}")
        print()

    if failed := [r for r in results if not r.online]:
        print("  DEGRADED (run continued):")
        for r in failed:
            print(f"    {r.name}: {r.error}")
        print()


if __name__ == "__main__":
    main()
