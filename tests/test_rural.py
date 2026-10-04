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
    ("why has my subsidy not come", "dbt_trace"),
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
    ("मेरा पैसा क्यों नहीं आया आधार लिंक नहीं है", "dbt_trace"),
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


# ---- A3: insurance policy check -------------------------------------------------------------
def test_policy_irr_is_the_rate_that_equates_premiums_and_payout():
    r = rural.irr_pct(50000, 10, 20, 1000000)
    pv_p = sum(50000 / (1 + r / 100) ** t for t in range(10)); pv_m = 1000000 / (1 + r / 100) ** 20
    assert abs(pv_p - pv_m) / pv_m < 1e-3            # the rate is rounded to 2 decimals
    assert rural.irr_pct(100000, 1, 1, 110000) == 10.0
    assert rural.irr_pct(1000, 5, 5, 4000) < 0                  # getting back less than you paid
    assert rural.irr_pct(1000, 5, 3, 9000) is None             # term shorter than the paying years


def test_policy_verdict_bands_and_safe_deposit_comparison():
    low = rural.policy_check(50000, 10, 20, 1000000, 500000)
    assert low["band"] == "amber" and low["alt_gap"] > 0 and low["cover_ratio"] == 10.0
    assert rural.policy_check(50000, 10, 20, 600000)["band"] == "red"
    assert rural.policy_check(1000, 5, 5, 4000)["band"] == "red"


def test_policy_term_plus_deposit_split_is_computed_not_asserted():
    r = rural.policy_check(24000, 12, 12, 400000, 5000000, 3000)
    assert r["split"]["invest"] == 21000 and r["split"]["cover"] == 5000000
    assert r["split"]["fv"] == round(rural._fv_deposits(21000, 12, 12, rural.SAFE_RATE))


def test_policy_refund_call_is_flagged_as_a_scam():
    r = rural.policy_check(1, 1, 1, 1, text="your policy bonus is pending, pay GST fee to release it")
    assert r["scam"] and r["band"] == "red" and "Do not pay" in r["headline"]
    assert not rural.policy_check(50000, 10, 20, 1000000, text="my agent explained the policy clearly and gave me a written illustration")["scam"]


def test_policy_questions_route_and_numbers_match_the_calculator():
    q = "my LIC endowment premium is 50000 a year for 10 years and maturity is 10 lakh after 20 years, cover 5 lakh"
    a = A.answer(q, _ctx())
    assert a.data["intent"] == "policy_check" and a.data["policy"]["irr_pct"] == rural.irr_pct(50000, 10, 20, 1000000)
    assert A.answer("bank manager sold me a policy, is it worth it", _ctx()).data["intent"] == "policy_check"
    english, _ = asyncio.run(H.convert("मेरी बीमा पॉलिसी का प्रीमियम पचास हज़ार रुपये साल का है, दस साल तक भरता हूँ, बीस साल बाद दस लाख रुपये मिलेंगे", use_model=False))
    assert A.rule_intent(english) == "policy_check" and "50000" in english and "10 lakh" in english


# ---- A4: UPI safety --------------------------------------------------------------------------
UPI_TRICKS = [
    ("the buyer on OLX sent a QR code, I should scan it to receive money", "qr_receive"),
    ("they said enter my PIN to receive the refund", "receive_pin"),
    ("I got a collect request, approve it to get a refund", "collect"),
    ("install AnyDesk so they can fix my account", "remote_app"),
    ("I found a customer care number on Google for my refund", "customer_care"),
    ("click this link to update KYC or your account will be blocked", "refund_link"),
    ("you won a lottery prize, pay a fee to claim", "prize"),
    ("कहा पैसा पाने के लिए पिन डालो", "receive_pin"),
    ("बिजली कट जाएगी लिंक भेजा है", "kyc"),
]


@pytest.mark.parametrize("text,case", UPI_TRICKS)
def test_upi_tricks_are_named_and_marked_red_or_amber(text, case):
    r = rural.upi_check(text)
    assert r["matched"] == case and r["level"] in ("red", "amber") and r["do"]


def test_every_tappable_situation_matches_a_trick():
    for en, _hi in rural.UPI_MENU:
        assert rural.upi_check(en)["matched"], en


def test_mistaken_transfer_is_careful_not_called_a_certain_scam_and_ordinary_text_is_unmatched():
    r = rural.upi_check("he sent money by mistake and wants it back")
    assert r["matched"] == "mistaken_transfer" and r["level"] == "amber" and "Very likely" not in r["verdict"]
    assert rural.upi_check("I bought vegetables and paid the shopkeeper")["matched"] is None


def test_upi_drills_have_exactly_one_safe_answer_each_in_both_languages():
    for lang in ("en", "hi"):
        d = rural.upi_drills(lang)
        assert len(d["drills"]) >= 8 and len(d["rules"]) == 6
        for x in d["drills"]:
            assert sum(o["right"] for o in x["options"]) == 1 and len(x["options"]) == 3 and x["why"]


def test_upi_questions_route_to_the_coach_but_after_a_loss_to_the_recovery_coach():
    assert A.answer("a buyer on olx sent a qr code to pay me, scan to receive", _ctx()).data["intent"] == "upi_check"
    assert A.answer("is this UPI request safe", _ctx()).data["intent"] == "upi_check"
    assert A.answer("I lost 50000 rupees on UPI to a fake bank officer", _ctx()).kind == "scam_recovery"
    english, _ = asyncio.run(H.convert("कोई कहता है पैसा पाने के लिए पिन डालो फोनपे पर", use_model=False))
    assert A.rule_intent(english) == "upi_check"


# ---- B3: DBT / subsidy tracer ---------------------------------------------------------------
def _top(**kw):
    base = dict(scheme="pm_kisan", status="no_status", linked="yes", name_same="yes", merged="no", last_used="recent", aadhaar_mobile="yes")
    base.update(kw)
    return rural.dbt_trace(**base)["causes"][0]["id"]


def test_dbt_names_the_obvious_break_first():
    assert _top(linked="no") == "not_seeded"
    assert _top(name_same="no") == "name_mismatch"
    assert _top(status="not_applied") == "not_registered"
    assert _top(status="other_account") == "wrong_account"
    assert _top(status="rejected") == "rejected"
    assert _top(last_used="old") == "dormant"
    assert _top(merged="yes") == "merged_bank"
    assert _top(status="pending") == "pending"


def test_dbt_every_cause_has_steps_in_both_languages_and_ranking_is_sorted():
    for lang in ("en", "hi"):
        r = rural.dbt_trace("pension", "pending", "no", "no", "yes", "old", "no", "", lang)
        assert len(r["causes"]) >= 4 and all(c["steps"] and c["why"] for c in r["causes"])
        scores = [c["score"] for c in r["causes"]]
        assert scores == sorted(scores, reverse=True)


def test_dbt_fee_demand_is_called_a_fraud_or_bribe():
    assert rural.dbt_trace(text="he asked me a fee to release the money")["scam"]
    assert rural.dbt_trace(text="स्टेटस पेंडिंग है, किसी ने फ़ीस माँगी")["scam"]
    assert not rural.dbt_trace(text="my status says pending")["scam"]


def test_dbt_letters_fill_the_persons_details_and_keep_blanks_otherwise():
    r = rural.dbt_full("pm_kisan", name="Ramesh", village="Rampur", block="Sadar", bank="SBI Rampur", lang="en")
    assert "Ramesh" in r["letters"]["office"] and "Rampur" in r["letters"]["office"] and "SBI Rampur" in r["letters"]["bank"]
    assert "________" in rural.dbt_full("pm_kisan")["letters"]["office"]
    assert "निवेदन" not in rural.dbt_full("pm_kisan", lang="hi")["letters"]["office"] and "सेवा में" in rural.dbt_full("pm_kisan", lang="hi")["letters"]["office"]


def test_dbt_questions_route_and_prefill():
    from backend import guide as G
    assert A.answer("my pm kisan installment is stuck", _ctx()).data["intent"] == "dbt_trace"
    assert A.answer("my pension has not come", _ctx()).data["intent"] == "dbt_trace"
    assert A.answer("are my papers ready", _ctx()).data["intent"] == "docs_ready"
    G.STATE.clear()
    g = G.begin("dbt", "my pm kisan installment is pending and the name is different on the bank passbook", "en", "t")
    assert g["params"]["scheme"] == "pm_kisan" and g["params"]["status"] == "pending" and g["params"]["name_same"] == "no"
    assert g["ask"]["slot"] == "linked"
