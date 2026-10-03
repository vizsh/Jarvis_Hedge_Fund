"""Plain calculators shared by the Practice page and the chatbot, so a number typed into a
slider and the same number asked aloud can never disagree. Pure functions, no I/O.

Conventions: end-of-month contributions, annual rates compounded monthly, fee subtracted
from the gross annual return (the usual simplification: net = gross - fee).
"""
from __future__ import annotations

import math
import re
from typing import Any

# ------------------------------------------------------------------ number parsing
_UNIT = {"crore": 1e7, "crores": 1e7, "cr": 1e7, "lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5,
         "l": 1e5, "k": 1e3, "thousand": 1e3, "hundred": 1e2, "million": 1e6, "mn": 1e6, "m": 1e6}
_NUM = r"\d[\d,]*(?:\.\d+)?"
_MONEY = re.compile(
    rf"(?P<cur>₹|rs\.?|inr|rupees?)?\s*(?P<n>{_NUM})\s*(?P<u>crores?|cr|lakhs?|lacs?|l|k|thousand|hundred|million|mn|m)?\b"
    rf"(?P<post>\s*(?:rupees?|rs\.?|inr))?", re.I)
_PCT = re.compile(rf"(?P<n>{_NUM})\s*(?:%|percent|per\s*cent|pc\b)", re.I)
_YEARS = re.compile(rf"(?P<n>{_NUM})\s*[- ]?\s*(?:years?|yrs?|y\b)", re.I)
_MONTHS = re.compile(rf"(?P<n>{_NUM})\s*[- ]?\s*(?:months?|mos?\b)", re.I)


def _f(s: str) -> float:
    return float(s.replace(",", ""))


def quantities(text: str) -> dict[str, list[dict[str, Any]]]:
    """Every figure in a sentence, typed. Money needs a currency sign or a unit (k, lakh,
    crore) or to be a plain number of 1000 or more that is not a percent/year/month."""
    t = text.replace("₹", "₹")
    taken: list[tuple[int, int]] = []
    out: dict[str, list[dict[str, Any]]] = {"pct": [], "years": [], "months": [], "money": []}

    def free(a: int, b: int) -> bool:
        return all(b <= x or a >= y for x, y in taken)

    for kind, rx in (("pct", _PCT), ("years", _YEARS), ("months", _MONTHS)):
        for m in rx.finditer(t):
            if free(*m.span()):
                taken.append(m.span())
                out[kind].append({"v": _f(m.group("n")), "at": m.start(), "ctx": t[max(0, m.start() - 28):m.start()].lower()})
    for m in _MONEY.finditer(t):
        a, b = m.span()
        if not free(a, b):
            continue
        v = _f(m.group("n"))
        unit = (m.group("u") or "").lower()
        # a bare "l" or "m" right after a number is only a unit when it is the whole word
        explicit = bool(m.group("cur") or m.group("post") or unit)
        if unit:
            v *= _UNIT[unit]
        if not explicit and v < 1000:
            continue
        # skip numbers that are part of a word like "fund a 2" or a year such as 2020
        if not explicit and 1900 <= v <= 2100 and float(m.group("n").replace(",", "")) == v:
            continue
        taken.append((a, b))
        out["money"].append({"v": v, "at": a, "ctx": t[max(0, a - 28):a].lower()})
    for k in out:
        out[k].sort(key=lambda q: q["at"])
    return out


_MONTHLY_CUE = re.compile(r"(sip|per month|a month|every month|each month|monthly|/month|/mo|"
                          r"month(?:ly)? (?:investment|contribution)|invest(?:ing)? \S{0,12} (?:each|every) month)", re.I)


def money_roles(text: str) -> dict[str, float | None]:
    """Which amount is the lump sum and which is the monthly one."""
    q = quantities(text)["money"]
    lump = monthly = None
    low = text.lower()
    for m in q:
        after = low[int(m["at"]):int(m["at"]) + 40]
        cue_after = re.search(r"^[^.,;]{0,18}?(?:per month|a month|every month|each month|monthly|/month|sip)", after)
        cue_before = re.search(r"(sip(?: of)?|monthly(?: of)?|every month|each month)\s*(?:rs\.?|₹|inr)?\s*$", m["ctx"])
        if (cue_after or cue_before) and monthly is None:
            monthly = m["v"]
        elif lump is None:
            lump = m["v"]
    return {"lump": lump, "monthly": monthly}


# ------------------------------------------------------------------ formatting
def inr(x: float) -> str:
    a = abs(x)
    s = "-" if x < 0 else ""
    if a >= 1e7:
        return f"{s}₹{a / 1e7:.2f} crore"
    if a >= 1e5:
        return f"{s}₹{a / 1e5:.2f} lakh"
    return f"{s}₹{a:,.0f}"


def inr_hi(x: float) -> str:
    """Spoken-friendly Hindi: the word for rupees instead of the sign, so TTS reads it."""
    a = abs(x)
    s = "-" if x < 0 else ""
    if a >= 1e7:
        return f"{s}{a / 1e7:.2f} करोड़ रुपये"
    if a >= 1e5:
        return f"{s}{a / 1e5:.2f} लाख रुपये"
    return f"{s}{a:,.0f} रुपये"


# ------------------------------------------------------------------ fee drag
def _grow(principal: float, monthly: float, annual_net: float, months: int) -> float:
    r = (1 + annual_net) ** (1 / 12) - 1
    if abs(r) < 1e-12:
        return principal + monthly * months
    g = (1 + r) ** months
    return principal * g + monthly * (g - 1) / r


def fee_drag(principal: float, monthly: float, years: int, gross_pct: float = 12.0,
             fee_pct: float = 2.0, low_fee_pct: float = 0.2) -> dict[str, Any]:
    """What a fund fee costs over time, against a cheap alternative earning the same gross."""
    years = max(1, min(40, int(years)))
    g = gross_pct / 100
    hi, lo = fee_pct / 100, low_fee_pct / 100
    pts = []
    for y in range(years + 1):
        n = y * 12
        pts.append({"year": y, "high": round(_grow(principal, monthly, g - hi, n)),
                    "low": round(_grow(principal, monthly, g - lo, n)),
                    "free": round(_grow(principal, monthly, g, n))})
    end = pts[-1]
    invested = principal + monthly * years * 12
    lost = end["low"] - end["high"]
    return {"principal": principal, "monthly": monthly, "years": years, "gross_pct": gross_pct,
            "fee_pct": fee_pct, "low_fee_pct": low_fee_pct, "points": pts, "invested": round(invested),
            "final_high": end["high"], "final_low": end["low"], "final_free": end["free"],
            "lost_vs_low": round(lost), "lost_vs_free": round(end["free"] - end["high"]),
            "share_of_gain_lost": round((end["free"] - end["high"]) / (end["free"] - invested), 3)
            if end["free"] > invested else 0.0}


# ------------------------------------------------------------------ emergency fund
def emergency(cash: float, expenses: float, invest: float = 0.0, haircut_pct: float = 20.0,
              income: float = 0.0, target_months: int = 6) -> dict[str, Any]:
    """How long the money lasts if the salary stopped. `income` is any money still coming in
    (rent, a partner's pay): only the shortfall is drawn from savings."""
    expenses = max(1.0, expenses)
    burn = max(0.0, expenses - max(0.0, income))
    usable_inv = max(0.0, invest) * (1 - haircut_pct / 100)
    pool = cash + usable_inv
    runway_cash = math.inf if burn == 0 else cash / burn
    runway_all = math.inf if burn == 0 else pool / burn
    horizon = 24 if math.isinf(runway_all) else min(36, max(target_months, math.ceil(runway_all)) + 1)
    series = []
    bal = cash
    for m in range(horizon + 1):
        series.append({"month": m, "cash": round(max(0.0, bal)),
                       "with_investments": round(max(0.0, pool - burn * m))})
        bal -= burn
    need = target_months * expenses
    short = max(0.0, need - cash)
    band = "green" if runway_cash >= target_months else "amber" if runway_cash >= 3 else "red"
    return {"cash": cash, "expenses": expenses, "income": income, "burn": burn, "invest": invest,
            "haircut_pct": haircut_pct, "usable_investments": round(usable_inv),
            "runway_cash": None if math.isinf(runway_cash) else round(runway_cash, 1),
            "runway_all": None if math.isinf(runway_all) else round(runway_all, 1),
            "target_months": target_months, "target_amount": round(need), "shortfall": round(short),
            "save_per_month_12": round(short / 12), "band": band, "points": series}
