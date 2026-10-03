import asyncio

import pytest

from backend import assistant as A
from backend import explain, portfolios, rural
from backend import hindi_input as H
from backend.session import Session


def _ctx(lang="en"):
    s = Session.create(); s.reprice()
    d = portfolios.load(s.conn, "preset_typical_retail")
    s.set_portfolio(d["name"], d["cash"], d["positions"], "preset_typical_retail")
    return A.Ctx(s.pit, s.portfolio, s.prices, s.policy, s.conn, explain.Conversation(), lang)


# ---- A1 loans: the numbers equal the arithmetic ---------------------------------------------
def test_loan_interest_only_is_simple_interest():
    r = rural.loan_cost(50000, 5, "per100_month", 10, "interest_only")
    assert r["yearly_pct"] == 60.0 and r["interest"] == 25000 and r["total"] == 75000 and r["band"] == "red"


def test_loan_compound_and_units_agree():
    r = rural.loan_cost(10000, 3, "pct_month", 12, "bullet_compound")
    assert r["total"] == round(10000 * 1.03 ** 12) and round(r["yearly_pct"], 1) == round((1.03 ** 12 - 1) * 100, 1)
    assert rural.loan_cost(10000, 36, "pct_year", 12)["interest"] == rural.loan_cost(10000, 3, "per100_month", 12)["interest"]
    assert rural.loan_cost(10000, 300, "rs_per_month", 12)["monthly_pct"] == 3.0


def test_loan_alternatives_are_cheaper_and_savings_positive():
    r = rural.loan_cost(50000, 5, "per100_month", 10)
    assert all(a["interest"] < r["interest"] and a["saves"] > 0 for a in r["alternatives"])
    assert rural.loan_cost(50000, 1, "pct_year", 12)["band"] == "green"


# ---- A2 offers: scams flagged, ordinary offers not -----------------------------------------
SCAMS = [
    "Pay 10000 now get 20000 in 6 months guaranteed. Bring 3 friends. Only today!",
    "Our committee doubles your money in 3 months, no risk, pay joining fee first",
    "Join our VIP telegram group, daily returns on crypto trading app, 100% guaranteed",
    "You have won a lottery prize, pay a processing fee to receive the gift",
    "पैसा दोगुना होगा, पक्का मुनाफा, दोस्तों को जोड़ें, सिर्फ आज",
]
BENIGN = [
    "Bank says the recurring deposit pays 6.8% a year, passbook and receipt provided.",
    "The post office savings scheme gives a fixed rate set by the government each quarter.",
    "My SHG gives loans at 12% a year with a written register.",
    "बैंक की आवर्ती जमा पर पासबुक और रसीद मिलेगी, ब्याज 6.8% सालाना।",
]


@pytest.mark.parametrize("text", SCAMS)
def test_scam_offers_are_red_or_amber_at_least(text):
    assert rural.scheme_check(text)["level"] in ("red", "amber")
    assert rural.scheme_check(text)["score"] >= 40


@pytest.mark.parametrize("text", BENIGN)
def test_ordinary_offers_are_never_red(text):
    assert rural.scheme_check(text)["level"] != "red"


def test_implied_return_math_and_never_calls_anything_safe():
    assert round(rural.implied_return(10000, 20000, 12), 1) == 100.0
    r = rural.scheme_check("a calm note about a bank deposit")
    assert "not proof" in r["verdict"] or "सुरक्षित" in r["verdict"]


# ---- B1 schemes ----------------------------------------------------------------------------
def ids(p):
    return {s["id"] for s in rural.entitlements(p)["schemes"]}


def test_landowning_farmer_gets_kisan_and_credit_but_taxpayer_does_not_get_pm_kisan():
    base = {"age": 40, "gender": "male", "land": "own", "work": "farmer", "bank": True}
    assert {"pm_kisan", "kcc", "pmfby"} <= ids(base)
    assert "pm_kisan" not in ids({**base, "taxpayer": True})


def test_age_windows_and_missing_bank():
    assert "pmjjby" in ids({"age": 30, "bank": True}) and "pmjjby" not in ids({"age": 55, "bank": True})
    assert "pmsby" in ids({"age": 60, "bank": True}) and "pmsby" not in ids({"age": 75, "bank": True})
    assert "jandhan" in ids({"age": 30, "bank": False}) and "pmjjby" not in ids({"age": 30, "bank": False})


def test_other_rules():
    assert "ssy" in ids({"daughter": True}) and "ssy" not in ids({})
    assert "ujjwala" in ids({"gender": "female", "lpg": False, "poor": "yes"}) and "ujjwala" not in ids({"gender": "male", "lpg": False, "poor": "yes"})
    assert "pmjay" in ids({"age": 72}) and "oap" in ids({"age": 65, "poor": "yes"}) and "oap" not in ids({"age": 65, "poor": "no"})
    assert "vishwakarma" in ids({"work": "artisan"}) and "svanidhi" in ids({"work": "vendor"}) and "scholar" in ids({"student": True, "category": "sc"})


def test_every_scheme_has_documents_defined_and_official_pointer():
    for s in rural.SCHEMES:
        assert s["docs"] and all(d in rural.DOCS for d in s["docs"]), s["id"]
        assert s["link"] and s["where_en"] and s["gives_hi"], s["id"]
    assert all(s["hi"] for s in rural.SCHEMES)


# ---- B2 readiness --------------------------------------------------------------------------
def test_readiness_names_the_biggest_blocker_first_and_clears_when_complete():
    r = rural.readiness(["pm_kisan", "pmjjby", "pmsby"], [])
    assert r["steps"][0]["id"] in rural.CORE and r["steps"][0]["blocks"] == 3
    full = {d for s in rural.SCHEMES for d in s["docs"]}
    ok = rural.readiness(["pm_kisan", "pmjjby"], list(full))
    assert not ok["steps"] and all(s["ready"] for s in ok["schemes"])


# ---- C1 income -----------------------------------------------------------------------------
def test_income_plan_totals_and_gap():
    r = rural.income_plan([{"month": 10, "amount": 120000}, {"month": 4, "amount": 60000}], 8000, [{"month": 6, "amount": 20000}], 0)
    assert r["income_year"] == 180000 and r["cost_year"] == 8000 * 12 + 20000 and r["net_year"] == 64000
    assert "Jan" in r["short_months"] and r["peak_shortfall"] > 0 and r["band"] == "amber"
    assert sum(p["keep_aside"] for p in r["plan"]) > 0


def test_income_plan_flags_structural_deficit():
    r = rural.income_plan([{"month": 10, "amount": 50000}], 8000)
    assert r["band"] == "red" and r["net_year"] < 0


# ---- assistant, English and Hindi ----------------------------------------------------------
@pytest.mark.parametrize("q,intent", [
    ("my sahukar charges 5 rupees per hundred a month on 50000 for 10 months", "moneylender"),
    ("someone says pay 10000 and get 20000 in 6 months, is this scheme genuine", "scheme_check"),
    ("which government schemes can I get", "entitlements"),
    ("why has my subsidy not come", "docs_ready"),
    ("my income comes only after harvest, how do I manage", "income_plan"),
])
def test_assistant_routes_rural_questions(q, intent):
    a = A.answer(q, _ctx())
    assert a.data["intent"] == intent


def test_assistant_loan_numbers_match_calculator():
    a = A.answer("my sahukar charges 5 rupees per hundred a month on 50000 for 10 months", _ctx())
    assert a.data["loan"]["interest"] == 25000 and a.facts[0]["value"] == "60%"


@pytest.mark.parametrize("hi,intent", [
    ("साहूकार पाँच रुपये सैकड़ा महीने पर पचास हज़ार रुपये दस महीने के लिए", "moneylender"),
    ("किसी ने कहा पैसा दोगुना होगा गारंटी, क्या यह योजना असली है", "scheme_check"),
    ("मुझे कौन सी सरकारी योजनाएँ मिल सकती हैं", "entitlements"),
    ("मेरा पैसा क्यों नहीं आया आधार लिंक नहीं है", "docs_ready"),
    ("फसल के बाद ही पैसा आता है आमदनी का हिसाब कैसे रखूँ", "income_plan"),
])
def test_hindi_questions_reach_the_same_intents(hi, intent):
    english, _how = asyncio.run(H.convert(hi, use_model=False))
    assert english, hi
    assert A.rule_intent(english) == intent, english


def test_hindi_loan_figures_are_read_by_code():
    english, _ = asyncio.run(H.convert("साहूकार पाँच रुपये सैकड़ा महीने पर पचास हज़ार रुपये दस महीने के लिए", use_model=False))
    a = A.answer(english, _ctx("hi"))
    assert a.data["loan"]["interest"] == 25000 and a.lang == "hi"
