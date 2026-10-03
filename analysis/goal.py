"""Goal fan: a range of outcomes for this portfolio plus a monthly SIP. Resamples this
portfolio's own past monthly-sized blocks of daily returns (so fat tails and crashes stay in)
-- a spread of possibilities, never a forecast."""
from __future__ import annotations

from typing import Any

import numpy as np

from core.pit import PointInTimeStore
from risk.portfolio import Portfolio


def _daily_returns(pit: PointInTimeStore, pf: Portfolio, prices: dict[str, float]) -> np.ndarray:
    vals = {t: s * prices.get(t, 0.0) for t, s in pf.positions.items()}
    tot = sum(vals.values())
    if tot <= 0:
        return np.array([])
    out = None
    for t, v in vals.items():
        rows = pit.prices(t, 1500)
        c = np.array([r["close"] for r in rows], dtype=float)
        if len(c) < 120:
            continue
        r = np.diff(c) / c[:-1]
        w = v / tot
        out = w * r if out is None else _add(out, w * r)
    return out if out is not None else np.array([])


def _add(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    n = min(len(a), len(b))                      # align on the most recent days
    return a[-n:] + b[-n:]


def fan(pit: PointInTimeStore, pf: Portfolio, prices: dict[str, float], monthly: float,
        years: int, target: float, haircut: float = 0.0, paths: int = 2000, seed: int = 7) -> dict[str, Any]:
    r = _daily_returns(pit, pf, prices)
    if len(r) < 250:
        return {"ok": False}
    start = pf.nav(prices)
    rng = np.random.default_rng(seed)
    months = years * 12
    blocks = len(r) - 21
    idx = rng.integers(0, blocks, size=(paths, months))
    # compounded return of a 21-day block starting at each index
    cum = np.cumprod(1 + r)
    cum = np.concatenate([[1.0], cum])
    mret = cum[idx + 21] / cum[idx]
    mret = mret * (1 - haircut) ** (1 / 12)   # 'what if the next years are worse than the past'
    val = np.full(paths, start)
    traj = np.empty((paths, months + 1))
    traj[:, 0] = val
    for m in range(months):
        val = val * mret[:, m] + monthly
        traj[:, m + 1] = val
    qs = np.percentile(traj, [10, 50, 90], axis=0)
    step = max(1, months // 24)
    pts = [{"month": int(m), "p10": round(float(qs[0][m])), "p50": round(float(qs[1][m])),
            "p90": round(float(qs[2][m]))} for m in range(0, months + 1, step)]
    if pts[-1]["month"] != months:
        pts.append({"month": months, "p10": round(float(qs[0][-1])), "p50": round(float(qs[1][-1])),
                    "p90": round(float(qs[2][-1]))})
    invested = start + monthly * months
    return {"ok": True, "points": pts, "start": round(start), "invested": round(invested),
            "prob_target": round(float((traj[:, -1] >= target).mean()), 3),
            "prob_loss": round(float((traj[:, -1] < invested).mean()), 3),
            "target": target, "years": years, "monthly": monthly,
            "haircut": haircut, "history_years": round(len(r) / 250, 1)}
