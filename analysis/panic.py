"""Panic-sell replay: what happened to THIS portfolio if it was sold during a real crash,
versus held. Uses actual closing prices; nothing is predicted."""
from __future__ import annotations

from typing import Any

from core.pit import PointInTimeStore
from risk.portfolio import Portfolio

EPISODES = {
    "covid": ("Covid crash", "2020-02-19", "2021-02-19"),
    "rate_shock_2022": ("2022 rate shock", "2022-01-17", "2023-01-17"),
    "adani_2023": ("Jan 2023 selloff", "2023-01-24", "2024-01-24"),
}


def replay(pit: PointInTimeStore, portfolio: Portfolio, prices: dict[str, float],
           key: str) -> dict[str, Any]:
    if key not in EPISODES or not portfolio.positions:
        return {"points": []}
    label, start, end = EPISODES[key]
    conn = pit.conn
    dates = [r["date"] for r in conn.execute(
        "SELECT DISTINCT date FROM prices WHERE date BETWEEN ? AND ? ORDER BY date", (start, end))]
    dates = dates[::3] if len(dates) > 120 else dates          # ~weekly keeps the payload small
    if len(dates) < 5:
        return {"points": []}
    series: dict[str, dict[str, float]] = {}
    for t in portfolio.positions:
        series[t] = {r["date"]: r["close"] for r in conn.execute(
            "SELECT date, close FROM prices WHERE ticker=? AND date BETWEEN ? AND ?", (t, start, end))}
    last: dict[str, float | None] = {t: None for t in series}
    pts, covered = [], 0.0
    now_val = sum(s * prices.get(t, 0.0) for t, s in portfolio.positions.items())
    for d in dates:
        v = portfolio.cash
        for t, sh in portfolio.positions.items():
            p = series[t].get(d) or last[t]
            if series[t].get(d):
                last[t] = series[t][d]
            v += sh * (p if p else prices.get(t, 0.0))      # not yet listed: carried at today's price
        pts.append({"date": d, "value": round(v, 2)})
    start_v = pts[0]["value"]
    trough = min(range(len(pts)), key=lambda i: pts[i]["value"])
    return {"key": key, "label": label, "points": pts, "start_value": start_v,
            "trough_index": trough, "trough_value": pts[trough]["value"],
            "end_value": pts[-1]["value"], "episodes": {k: v[0] for k, v in EPISODES.items()}}
