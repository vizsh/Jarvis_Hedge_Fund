"""Tax shield: for each holding, what selling NOW costs versus waiting for the 12-month mark.

Cost basis is something only the owner knows, so a holding with no purchase record is
reported as such rather than guessed. Rates are the published ones in analysis/tax.py.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from analysis import tax as T
from core import universe


def shield(portfolio, prices: dict[str, float], lots: dict, asof: date) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    total_saving = 0.0
    for ticker, shares in sorted(portfolio.positions.items()):
        price = prices.get(ticker, 0.0)
        lot = lots.get(ticker)
        row: dict[str, Any] = {"ticker": ticker, "name": universe.name(ticker),
                               "shares": shares, "price": price, "value": shares * price}
        if not lot or not price:
            row.update(status="NO_BASIS",
                       action="Add what you paid to see the tax on selling this.")
            rows.append(row)
            continue
        held = lot.held_days(asof)
        gain = (price - lot.buy_price) * shares
        to_long = max(0, T.LONG_TERM_DAYS - held)
        row.update(buy_price=lot.buy_price, buy_date=lot.buy_date, held_days=held,
                   gain=round(gain, 2), days_to_long_term=to_long,
                   term="long" if to_long == 0 else "short")
        if gain <= 0:
            row.update(status="LOSS", tax_now=0.0, tax_if_wait=0.0, saving=0.0,
                       action=f"Down ₹{abs(gain):,.0f}. A realised loss can be set against gains this year.")
        elif to_long == 0:
            tax = gain * T.LONG_TERM_RATE
            row.update(status="LONG_TERM", tax_now=round(tax, 2), tax_if_wait=round(tax, 2),
                       saving=0.0, action="Already long-term. Selling uses the lower 12.5% rate.")
        else:
            now, wait = gain * T.SHORT_TERM_RATE, gain * T.LONG_TERM_RATE
            saving = now - wait
            near = to_long <= 90
            row.update(status="WAIT" if near else "SHORT_TERM",
                       tax_now=round(now, 2), tax_if_wait=round(wait, 2), saving=round(saving, 2),
                       action=(f"Wait {to_long} more day{'s' if to_long != 1 else ''} to cross 12 months "
                               f"and save ₹{saving:,.0f}.") if near else
                              f"{to_long} days to the long-term mark; selling today is taxed at 20%.")
            if near:
                total_saving += saving
        rows.append(row)
    order = {"WAIT": 0, "SHORT_TERM": 1, "LONG_TERM": 2, "LOSS": 3, "NO_BASIS": 4}
    rows.sort(key=lambda r: (order.get(r["status"], 9), r.get("days_to_long_term", 999)))
    return {"asof": asof.isoformat(), "rows": rows, "total_saving": round(total_saving, 2),
            "rates": {"short": T.SHORT_TERM_RATE, "long": T.LONG_TERM_RATE,
                      "exemption": T.LTCG_EXEMPTION},
            "caveat": "Arithmetic on published rates, holding by holding. Not tax advice."}
