"""Standing rules: the things you want to be told about without asking again.

Everything else in this product is pull — you ask, it answers. That makes it a tool you
open when you already suspect something, which is the wrong moment. A watch is push:
you say once what would worry you, and the system checks it every time the state moves.

Rules are deliberately about *your own limits*, not about price. "Tell me if TCS hits
₹4,000" is a different product and a worse one; it invites you to trade on a number
with no meaning attached. "Tell me if technology goes past 40% of my money" is a rule
about the shape of your risk, which is the thing this system actually understands.

Evaluation is pure and synchronous. A rule is a metric, a comparison and a threshold —
no scheduler, no background thread, no state machine. It is re-evaluated whenever the
caller asks, and the caller is the same state-change path that already redraws the HUD.
"""
from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from typing import Any

from analysis import stress as stress_mod
from analysis import xray as xray_mod
from core import universe
from core.pit import PointInTimeStore
from risk.policy import Policy
from risk.portfolio import Portfolio

SCHEMA = """
CREATE TABLE IF NOT EXISTS watches (
    id           TEXT PRIMARY KEY,
    portfolio_id TEXT,
    metric       TEXT NOT NULL,
    op           TEXT NOT NULL,
    threshold    REAL NOT NULL,
    subject      TEXT,
    label        TEXT NOT NULL,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
    last_state   TEXT
);
"""

# What can be watched, and how to say it. Keeping this a closed set is what lets the
# UI offer a sentence-builder instead of a query language.
METRICS: dict[str, dict[str, Any]] = {
    "sector_weight": {
        "label": "an industry's share of my money",
        "needs_subject": True,
        "unit": "pct",
        "default": 0.40,
        "blurb": "Concentration in one industry is the commonest way a private "
                 "portfolio quietly becomes one bet.",
    },
    "position_weight": {
        "label": "one holding's share of my money",
        "needs_subject": True,
        "unit": "pct",
        "default": 0.20,
        "blurb": "Caps what a single company failing can cost you.",
    },
    "cash_pct": {
        "label": "my cash buffer",
        "needs_subject": False,
        "unit": "pct",
        "default": 0.05,
        "blurb": "Below this you would have to sell something to buy anything.",
    },
    "score": {
        "label": "my portfolio score",
        "needs_subject": False,
        "unit": "points",
        "default": 60,
        "blurb": "The single summary number, measured against your own limits.",
    },
    "effective_holdings": {
        "label": "how many positions it really behaves like",
        "needs_subject": False,
        "unit": "count",
        "default": 6,
        "blurb": "Falls when your biggest holdings grow, even if you buy nothing.",
    },
    "worst_case_loss": {
        "label": "my worst tested loss",
        "needs_subject": False,
        "unit": "pct",
        "default": 0.30,
        "blurb": "What the worst historical window would do to today's basket.",
    },
    "drawdown": {
        "label": "the worst fall this basket has had",
        "needs_subject": False,
        "unit": "pct",
        "default": 0.30,
        "blurb": "A fact about the holdings, recomputed as the holdings change.",
    },
}

OPS = {"above": ">", "below": "<"}


@dataclass
class Watch:
    id: str
    metric: str
    op: str                       # above | below
    threshold: float
    subject: str | None
    label: str
    last_state: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, "metric": self.metric, "op": self.op,
                "threshold": self.threshold, "subject": self.subject,
                "label": self.label, "last_state": self.last_state}


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


# --------------------------------------------------------------------------- storage
def sentence(metric: str, op: str, threshold: float, subject: str | None) -> str:
    """The rule, read back as English. A rule you cannot read is a rule you cannot trust."""
    spec = METRICS.get(metric, {})
    unit = spec.get("unit", "")
    value = (f"{threshold * 100:.0f}%" if unit == "pct"
             else f"{threshold:.0f}" + (" points" if unit == "points" else ""))
    what = spec.get("label", metric)
    if spec.get("needs_subject") and subject:
        name = (universe.sector_label(subject) if metric == "sector_weight"
                else universe.name(subject))
        what = f"{name}'s share of my money"
    return f"Tell me if {what} goes {op} {value}"


def add(conn: sqlite3.Connection, portfolio_id: str | None, metric: str, op: str,
        threshold: float, subject: str | None = None) -> Watch:
    if metric not in METRICS:
        raise ValueError(f"unknown metric {metric!r}")
    if op not in OPS:
        raise ValueError(f"unknown comparison {op!r}")
    watch = Watch(id=uuid.uuid4().hex[:10], metric=metric, op=op,
                  threshold=float(threshold), subject=subject,
                  label=sentence(metric, op, float(threshold), subject))
    conn.execute(
        "INSERT INTO watches (id, portfolio_id, metric, op, threshold, subject, label) "
        "VALUES (?,?,?,?,?,?,?)",
        (watch.id, portfolio_id, watch.metric, watch.op, watch.threshold,
         watch.subject, watch.label))
    conn.commit()
    return watch


def remove(conn: sqlite3.Connection, watch_id: str) -> bool:
    cur = conn.execute("DELETE FROM watches WHERE id = ?", (watch_id,))
    conn.commit()
    return cur.rowcount > 0


def load(conn: sqlite3.Connection, portfolio_id: str | None = None) -> list[Watch]:
    if portfolio_id:
        rows = conn.execute(
            "SELECT * FROM watches WHERE portfolio_id IS NULL OR portfolio_id = ? "
            "ORDER BY created_at", (portfolio_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM watches ORDER BY created_at").fetchall()
    return [Watch(id=r["id"], metric=r["metric"], op=r["op"],
                  threshold=r["threshold"], subject=r["subject"], label=r["label"],
                  last_state=r["last_state"]) for r in rows]


def suggestions(report: xray_mod.XRay) -> list[dict[str, Any]]:
    """Rules worth offering, derived from what is already true.

    A blank rule-builder gets used by nobody. Offering "you are at 48% technology —
    watch 40%?" gets used, because the threshold is already anchored to something the
    person just read.
    """
    out: list[dict[str, Any]] = []
    if report.top_sector:
        code, w = report.top_sector
        out.append({"metric": "sector_weight", "op": "above", "subject": code,
                    "threshold": round(min(0.95, w + 0.05), 2),
                    "label": sentence("sector_weight", "above",
                                      round(min(0.95, w + 0.05), 2), code),
                    "because": f"You are at {w:.0%} today."})
    if report.top_holding:
        t, w = report.top_holding
        out.append({"metric": "position_weight", "op": "above", "subject": t,
                    "threshold": round(min(0.95, w + 0.05), 2),
                    "label": sentence("position_weight", "above",
                                      round(min(0.95, w + 0.05), 2), t),
                    "because": f"{universe.name(t)} is {w:.0%} today."})
    out.append({"metric": "cash_pct", "op": "below", "subject": None,
                "threshold": 0.05,
                "label": sentence("cash_pct", "below", 0.05, None),
                "because": "A thin buffer forces you to sell to buy."})
    out.append({"metric": "score", "op": "below", "subject": None, "threshold": 60,
                "label": sentence("score", "below", 60, None),
                "because": f"You score {report.score} today."})
    return out


# --------------------------------------------------------------------------- evaluate
def _current(metric: str, subject: str | None, report: xray_mod.XRay,
             portfolio: Portfolio, prices: dict[str, float],
             stress: dict[str, Any] | None) -> float | None:
    if metric == "sector_weight":
        sectors = dict(universe.sectors())
        nav = report.nav
        if not nav:
            return None
        return sum(portfolio.positions[t] * prices.get(t, 0.0)
                   for t in portfolio.positions
                   if sectors.get(t) == subject) / nav
    if metric == "position_weight":
        return portfolio.weights(prices).get(subject or "", 0.0)
    if metric == "cash_pct":
        return report.cash_pct
    if metric == "score":
        return float(report.score)
    if metric == "effective_holdings":
        return report.effective_holdings
    if metric == "drawdown":
        return abs(report.max_drawdown) if report.max_drawdown is not None else None
    if metric == "worst_case_loss":
        worst = (stress or {}).get("worst_case")
        return abs(worst["portfolio_return"]) if worst else None
    return None


def evaluate(conn: sqlite3.Connection, pit: PointInTimeStore, portfolio: Portfolio,
             prices: dict[str, float], policy: Policy,
             portfolio_id: str | None = None) -> dict[str, Any]:
    """Check every rule and report which ones are breached.

    `changed` is the useful field: a rule that was already breached an hour ago is not
    news, and a system that re-announces the same breach on every tick trains people to
    ignore it. Only transitions are worth interrupting somebody for.
    """
    watches = load(conn, portfolio_id)
    if not watches or not portfolio.positions:
        return {"watches": [w.as_dict() for w in watches], "breached": [],
                "changed": [], "count": len(watches)}

    report = xray_mod.analyse(pit, portfolio, prices, policy)
    need_stress = any(w.metric == "worst_case_loss" for w in watches)
    stress = stress_mod.run_all(pit, portfolio, prices) if need_stress else None

    breached: list[dict[str, Any]] = []
    changed: list[dict[str, Any]] = []
    out: list[dict[str, Any]] = []

    for w in watches:
        value = _current(w.metric, w.subject, report, portfolio, prices, stress)
        if value is None:
            out.append({**w.as_dict(), "value": None, "state": "unknown"})
            continue
        hit = value > w.threshold if w.op == "above" else value < w.threshold
        state = "breached" if hit else "ok"
        row = {**w.as_dict(), "value": round(value, 4), "state": state,
               "unit": METRICS[w.metric]["unit"]}
        out.append(row)
        if hit:
            breached.append(row)
        if state != (w.last_state or "ok"):
            changed.append(row)
            conn.execute("UPDATE watches SET last_state = ? WHERE id = ?",
                         (state, w.id))
    conn.commit()

    return {"watches": out, "breached": breached, "changed": changed,
            "count": len(out),
            "suggestions": suggestions(report) if not out else []}


def spoken(changed: list[dict[str, Any]]) -> str | None:
    """What JARVIS says when a rule flips. One sentence, or silence."""
    if not changed:
        return None
    first = changed[0]
    unit = first.get("unit")
    value = (f"{first['value'] * 100:.0f}%" if unit == "pct"
             else f"{first['value']:.0f}")
    verb = "is now out of" if first["state"] == "breached" else "is back within"
    what = first["label"].lower().removeprefix("tell me if ")
    more = (f" {len(changed) - 1} other rule{'s' if len(changed) > 2 else ''} also "
            f"changed." if len(changed) > 1 else "")
    return f"A rule you set {verb} range: {what}. It is {value}.{more}"
