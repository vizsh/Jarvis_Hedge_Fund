"""Was the desk right? Scored against what actually happened next.

This is the one place the project shows a real performance number instead of a backtest
it would have to defend. Every claim carries the sim clock it was made at, so the
forward return is simply a lookup in the snapshot — no simulation, no assumptions.

Scoring:
    forward return  = close(clock + horizon) / close(clock) - 1
    a bull claim is right when that is positive, a bear claim when it is negative
    neutral claims are excluded — they make no directional call, so they cannot be wrong

Hit rate answers "how often", Brier answers "how well-calibrated". A desk that is right
60% of the time while claiming 0.9 confidence is worse than one right 55% of the time
claiming 0.55, and only Brier shows that. Lower is better; 0.25 is the score you get by
always saying "coin flip", so anything above that is worse than useless.

READ THE HONESTY NOTE. `PointInTimeStore` guarantees the desks could not SEE the future
in their inputs. It cannot do anything about the fact that an LLM trained on internet
text has already read what happened in 2020. These numbers are therefore an upper bound
on skill, not a measurement of it, and the UI says so.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

HORIZONS = (7, 30)          # calendar days
NEUTRAL_BRIER = 0.25        # what you score by always guessing 50/50


@dataclass
class DeskScore:
    desk: str
    n: int = 0
    hits: int = 0
    brier_sum: float = 0.0
    bull: int = 0
    bear: int = 0
    by_horizon: dict[int, dict[str, float]] = field(default_factory=dict)

    @property
    def bear_share(self) -> float:
        return self.bear / self.n if self.n else 0.0

    @property
    def one_sided(self) -> bool:
        """A desk that nearly always says the same thing carries no information,
        however often it happens to be right.

        Widened from 0.85/0.15 to 0.80/0.20 after the two-pass Red Team change. Forcing
        the dissenter to oppose a mostly-bearish consensus swung it from 74% bear to
        83% BULL -- its hit rate improved, but a desk that is always long in a market
        that mostly rises is not demonstrating skill, and the old threshold missed it
        by two points. The flag has to catch one-sidedness in both directions or it
        only ever polices the bias we happened to see first.
        """
        return self.n >= 8 and (self.bear_share >= 0.80 or self.bear_share <= 0.20)

    @property
    def hit_rate(self) -> float:
        return self.hits / self.n if self.n else 0.0

    @property
    def brier(self) -> float:
        return self.brier_sum / self.n if self.n else 0.0

    @property
    def beats_coin_flip(self) -> bool:
        return self.n > 0 and self.brier < NEUTRAL_BRIER

    def as_dict(self) -> dict[str, Any]:
        return {"desk": self.desk, "n": self.n, "hit_rate": round(self.hit_rate, 3),
                "brier": round(self.brier, 3), "beats_coin_flip": self.beats_coin_flip,
                "bull": self.bull, "bear": self.bear,
                "bear_share": round(self.bear_share, 3), "one_sided": self.one_sided,
                "by_horizon": {str(k): v for k, v in self.by_horizon.items()}}


def _close_on_or_after(conn: sqlite3.Connection, ticker: str, date: str) -> float | None:
    row = conn.execute(
        "SELECT close FROM prices WHERE ticker = ? AND date >= ? ORDER BY date LIMIT 1",
        (ticker, date)).fetchone()
    return row["close"] if row else None


def _close_on_or_before(conn: sqlite3.Connection, ticker: str, date: str) -> float | None:
    row = conn.execute(
        "SELECT close FROM prices WHERE ticker = ? AND date <= ? ORDER BY date DESC LIMIT 1",
        (ticker, date)).fetchone()
    return row["close"] if row else None


def forward_return(conn: sqlite3.Connection, ticker: str, clock: str,
                   horizon_days: int) -> float | None:
    """None when the horizon runs past the end of the snapshot — an unresolved call,
    which must be excluded rather than counted as a miss."""
    start = _close_on_or_before(conn, ticker, clock[:10])
    if not start:
        return None
    target = (datetime.fromisoformat(clock[:10]) + timedelta(days=horizon_days)).date()
    end = _close_on_or_after(conn, ticker, target.isoformat())
    if not end:
        return None
    # Guard against the lookup silently returning the same bar for both legs.
    last = conn.execute("SELECT MAX(date) AS d FROM prices WHERE ticker = ?",
                        (ticker,)).fetchone()["d"]
    if last and target.isoformat() > last:
        return None
    return end / start - 1


def score(conn: sqlite3.Connection, horizons: tuple[int, ...] = HORIZONS
          ) -> dict[str, Any]:
    rows = conn.execute(
        "SELECT desk, ticker, stance, weight, sim_clock FROM claims "
        "WHERE accepted = 1 AND sim_clock IS NOT NULL AND stance != 'neutral'"
    ).fetchall()

    desks: dict[str, DeskScore] = {}
    unresolved = 0
    for row in rows:
        ret = None
        per_horizon: dict[int, tuple[bool, float]] = {}
        for h in horizons:
            r = forward_return(conn, row["ticker"], row["sim_clock"], h)
            if r is None:
                continue
            went_up = r > 0
            correct = (row["stance"] == "bull") == went_up
            # Treat the claim weight as confidence in its own direction.
            p_up = 0.5 + (row["weight"] / 2) * (1 if row["stance"] == "bull" else -1)
            brier = (p_up - (1.0 if went_up else 0.0)) ** 2
            per_horizon[h] = (correct, brier)
            ret = r

        if not per_horizon:
            unresolved += 1
            continue

        d = desks.setdefault(row["desk"], DeskScore(desk=row["desk"]))
        # Headline numbers use the shortest resolved horizon; the rest are broken out.
        first = min(per_horizon)
        correct, brier = per_horizon[first]
        d.n += 1
        d.hits += int(correct)
        d.brier_sum += brier
        if row["stance"] == "bull":
            d.bull += 1
        else:
            d.bear += 1
        for h, (c, b) in per_horizon.items():
            bucket = d.by_horizon.setdefault(h, {"n": 0, "hits": 0, "brier_sum": 0.0})
            bucket["n"] += 1
            bucket["hits"] += int(c)
            bucket["brier_sum"] += b

    for d in desks.values():
        for h, bucket in d.by_horizon.items():
            n = bucket["n"] or 1
            bucket["hit_rate"] = round(bucket["hits"] / n, 3)
            bucket["brier"] = round(bucket["brier_sum"] / n, 3)
            bucket.pop("brier_sum", None)

    total = sum(d.n for d in desks.values())
    all_bear = sum(d.bear for d in desks.values())
    return {
        "bear_share": round(all_bear / total, 3) if total else 0.0,
        "systematic_bias": total >= 20 and (all_bear / total >= 0.7 or all_bear / total <= 0.3),
        "desks": [d.as_dict() for d in
                  sorted(desks.values(), key=lambda x: -x.n)],
        "total_scored": total,
        "unresolved": unresolved,
        "horizons": list(horizons),
        "neutral_brier": NEUTRAL_BRIER,
        # Surfaced in the UI. An LLM trained on internet text has already read 2020;
        # point-in-time control over the INPUTS cannot undo that.
        "caveat": ("Scored against actual forward returns. The desks could not see the "
                   "future in their inputs, but the base model has read the outcomes "
                   "in training — treat this as an upper bound on skill, not a "
                   "measurement of it."),
        "sample_warning": total < 40,
    }


def ensure_sim_clock_column(conn: sqlite3.Connection) -> None:
    """Older snapshots predate the column. Added in place so an existing database keeps
    its claims instead of being rebuilt."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(claims)")}
    if "sim_clock" not in cols:
        conn.execute("ALTER TABLE claims ADD COLUMN sim_clock TEXT")
        conn.commit()
