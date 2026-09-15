"""Indian capital gains, and what they cost a rebalance.

A plan that ignores tax can cost more in tax than it saves in risk. That is not a
rounding error: selling a holding one week before it crosses twelve months roughly
doubles the rate on that gain.

Indian equity, as of the rules this is written against:

    SHORT TERM   held < 12 months   20% on the gain        (Sec 111A)
    LONG TERM    held >= 12 months  12.5% above a ₹1.25 lakh annual exemption (Sec 112A)

Two honesty constraints, both load-bearing:

1.  We do not know your purchase price or date -- nothing in this system ever asked.
    So cost basis is an INPUT, not an assumption. Where it is missing we say the tax is
    unknown rather than inventing a number, because a fabricated tax figure is worse
    than none: it would be acted on.

2.  This is an estimate, not advice. Surcharge, cess, set-off against carried-forward
    losses and your slab all move the real number. The UI says so every time.

The useful output is rarely the total. It is "wait 3 weeks on this one and the rate
halves", which is a decision a person can actually take.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from core import universe

SHORT_TERM_RATE = 0.20        # Sec 111A
LONG_TERM_RATE = 0.125        # Sec 112A
LTCG_EXEMPTION = 125_000      # per financial year
LONG_TERM_DAYS = 365
# Selling within this window of the long-term threshold is worth flagging: the wait is
# short and the rate difference is large.
NEAR_THRESHOLD_DAYS = 45


@dataclass
class Lot:
    """One purchase. Supplied by the user -- never inferred."""
    ticker: str
    shares: int
    buy_price: float
    buy_date: str             # ISO

    def held_days(self, asof: date) -> int:
        return (asof - datetime.fromisoformat(self.buy_date).date()).days


@dataclass
class TaxLine:
    ticker: str
    name: str
    shares: int
    proceeds: float
    gain: float | None
    term: str                 # short | long | unknown
    held_days: int | None
    rate: float | None
    tax: float | None
    days_to_long_term: int | None
    note: str

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class TaxEstimate:
    lines: list[TaxLine] = field(default_factory=list)
    total_tax: float = 0.0
    short_term_tax: float = 0.0
    long_term_tax: float = 0.0
    exemption_used: float = 0.0
    unknown_basis: int = 0
    deferrable: list[dict[str, Any]] = field(default_factory=list)
    caveat: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "lines": [l.as_dict() for l in self.lines],
            "total_tax": round(self.total_tax, 2),
            "short_term_tax": round(self.short_term_tax, 2),
            "long_term_tax": round(self.long_term_tax, 2),
            "exemption_used": round(self.exemption_used, 2),
            "exemption_limit": LTCG_EXEMPTION,
            "unknown_basis": self.unknown_basis,
            "deferrable": self.deferrable,
            "caveat": self.caveat,
        }


def estimate(sells: list[dict[str, Any]], lots: dict[str, Lot],
             asof: date | None = None) -> TaxEstimate:
    """Cost a set of sells.

    `sells` are {ticker, shares, price}; `lots` is the user's cost basis keyed by
    ticker. Anything without a lot is reported as unknown, never guessed.
    """
    asof = asof or date.today()
    out = TaxEstimate()
    ltcg_gains = 0.0

    for sell in sells:
        ticker = sell["ticker"]
        shares = int(sell["shares"])
        price = float(sell["price"])
        proceeds = shares * price
        lot = lots.get(ticker)

        if not lot:
            out.unknown_basis += 1
            out.lines.append(TaxLine(
                ticker=ticker, name=universe.name(ticker), shares=shares,
                proceeds=round(proceeds, 2), gain=None, term="unknown",
                held_days=None, rate=None, tax=None, days_to_long_term=None,
                note="No purchase price on record, so I cannot tell you the tax. "
                     "Add it and I will."))
            continue

        held = lot.held_days(asof)
        gain = (price - lot.buy_price) * shares
        long_term = held >= LONG_TERM_DAYS
        to_long = max(0, LONG_TERM_DAYS - held)

        if long_term:
            # The exemption applies to the year's aggregate, so it is consumed in the
            # order the sells are processed.
            taxable = max(0.0, gain)
            remaining = max(0.0, LTCG_EXEMPTION - ltcg_gains)
            sheltered = min(taxable, remaining)
            ltcg_gains += taxable
            tax = max(0.0, taxable - sheltered) * LONG_TERM_RATE
            out.long_term_tax += tax
            out.exemption_used += sheltered
            note = (f"Held {held} days. Long term at {LONG_TERM_RATE:.1%}"
                    + (f", {sheltered:,.0f} covered by the annual exemption."
                       if sheltered > 0 else "."))
        else:
            tax = max(0.0, gain) * SHORT_TERM_RATE
            out.short_term_tax += tax
            note = (f"Held {held} days. Short term at {SHORT_TERM_RATE:.0%}"
                    + (f" — {to_long} days short of the long-term rate."
                       if to_long <= NEAR_THRESHOLD_DAYS else "."))
            if to_long <= NEAR_THRESHOLD_DAYS and gain > 0:
                # The actionable finding: a short wait halves the rate.
                saving = gain * (SHORT_TERM_RATE - LONG_TERM_RATE)
                out.deferrable.append({
                    "ticker": ticker, "name": universe.name(ticker),
                    "days_to_wait": to_long,
                    "saving": round(saving, 2),
                    "gain": round(gain, 2),
                })

        out.total_tax += tax
        out.lines.append(TaxLine(
            ticker=ticker, name=universe.name(ticker), shares=shares,
            proceeds=round(proceeds, 2), gain=round(gain, 2),
            term="long" if long_term else "short", held_days=held,
            rate=LONG_TERM_RATE if long_term else SHORT_TERM_RATE,
            tax=round(tax, 2), days_to_long_term=None if long_term else to_long,
            note=note))

    out.deferrable.sort(key=lambda d: -d["saving"])
    out.caveat = (
        "An estimate on the gains you told me about. Surcharge, cess, your slab and "
        "any carried-forward losses will move the real number — this is not tax advice."
    )
    return out


def annotate_plan(plan: dict[str, Any], lots: dict[str, Lot],
                  asof: date | None = None) -> dict[str, Any]:
    """Attach a tax estimate to a rebalance plan, and say whether it is worth it.

    The comparison that matters is tax cost against risk reduction. A plan that costs
    ₹40,000 in tax to shave two points off a sector breach is a bad plan, and nobody
    finds that out until the bill arrives.
    """
    sells = [t for t in plan.get("trades", []) if t["side"] == "SELL"]
    est = estimate(sells, lots, asof)
    tax = est.as_dict()

    before, after = plan.get("before", {}), plan.get("after", {})
    sector_drop = (before.get("top_sector", 0) or 0) - (after.get("top_sector", 0) or 0)
    nav = before.get("nav") or 1
    tax["cost_of_compliance_pct"] = round((est.total_tax + plan.get("cost", 0)) / nav, 5)
    tax["sector_points_gained"] = round(sector_drop * 100, 2)
    if sector_drop > 0:
        tax["tax_per_point"] = round(est.total_tax / (sector_drop * 100), 2)
    return {**plan, "tax": tax}
