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


# ---- C3: sell now or hold ------------------------------------------------------------------
HIST = "Oct 2021: 2000\nFeb 2022: 2150\nOct 2022, 2100\n2023-02-10 2400\n2023-10 2250\n2024-02-05 2300\nOct 2024 2400\nFeb 2025 2350"


def test_hold_breakeven_is_the_arithmetic():
    r = rural.hold_or_sell(50, 2100, 4, 2400, 10, 1, 20, 12)
    keep = 0.99 ** 4
    expect = (50 * 2100 * (1 + 0.12 * 4 / 12) + 50 * 10 * 4 + 50 * 20) / (50 * keep)
    assert abs(r["breakeven_price"] - round(expect, 1)) < 0.06
    assert r["gain"] == round(50 * keep * 2400 - (50 * 10 * 4 + 50 * 20) - 50 * 2100 * (1 + 0.12 * 4 / 12))
    # no costs and no interest: break-even is today's price
    z = rural.hold_or_sell(10, 1000, 3, None, 0, 0, 0, 0)
    assert z["breakeven_price"] == 1000.0 and z["rise_needed_pct"] == 0.0


def test_expensive_money_makes_waiting_hard_to_justify():
    cheap = rural.hold_or_sell(50, 2100, 6, 2300, 0, 0, 0, 4)
    dear = rural.hold_or_sell(50, 2100, 6, 2300, 0, 0, 0, 60)          # moneylender-rate debt
    assert dear["rise_needed_pct"] > cheap["rise_needed_pct"] and dear["gain"] < cheap["gain"] and dear["band"] == "red"


def test_history_parser_reads_common_formats_and_ignores_noise():
    got = rural.parse_prices(HIST + "\nnot a price line\nOct 2020")
    assert len(got) == 8 and (2022, 10, 2100.0) in got and (2023, 2, 2400.0) in got and (2021, 10, 2000.0) in got


def test_history_hit_rate_counts_years_from_the_pasted_data_only():
    r = rural.hold_or_sell(50, 2100, 4, None, 10, 1, 20, 12, HIST, 10)
    assert [y["year"] for y in r["years"]] == [2021, 2022, 2023, 2024]
    assert r["years"][1]["rise_pct"] == round((2400 / 2100 - 1) * 100, 1)
    n_enough = sum(1 for y in r["years"] if y["rise_pct"] >= r["rise_needed_pct"])
    assert r["history"]["enough"] == n_enough and r["history"]["n"] == 4
    assert all(s["years"] >= 1 for s in r["season"])


def test_hold_never_invents_prices_without_history():
    r = rural.hold_or_sell(50, 2100, 4)
    assert r["history"] is None and r["years"] == [] and r["gain"] is None and r["band"] == "amber"


def test_hold_questions_route_prefill_and_hindi():
    from backend import guide as G
    q = "I have 50 quintals of wheat at 2100 a quintal, wait 4 months, expect 2400 later"
    assert A.answer(q, _ctx()).data["intent"] == "hold_sell"
    assert A._hold_args(q) == {"qty": 50.0, "months": 4, "price_now": 2100.0, "price_later": 2400.0}
    G.STATE.clear()
    g = G.begin("hold", q, "en", "h")                       # everything required is in the sentence: only the optional storage cost is asked
    assert g["ask"]["slot"] == "storage" and g["ask"]["optional"] and g["params"]["price_later"] == "2400.0"
    assert G.fill("h", "skip", "en")["done"]
    english, _ = asyncio.run(H.convert("मेरे पास पचास क्विंटल गेहूँ है, भाव दो हज़ार एक सौ है, चार महीने रुकूँ तो चौबीस सौ की उम्मीद है, अभी बेचूँ या रुकूँ", use_model=False))
    assert A.rule_intent(english) == "hold_sell" and "50 quintals" in english and "2100" in english and "2400" in english


# ---- E1: daily-wage saving -----------------------------------------------------------------
def test_recurring_deposit_maturity_matches_the_standard_calculator_and_zero_rate_is_plain_addition():
    assert 12400 < rural.rd_maturity(1000, 12, 6.7) < 12480            # ~12,44x is what RD calculators give
    assert rural.rd_maturity(500, 24, 0) == 12000
    assert rural.rd_maturity(1000, 0, 6.7) == 0


def test_required_saving_reaches_the_inflated_goal_exactly():
    r = rural.daily_saving("daughter", 100000, 60, None, 400, 26, 6.7, 6.0)
    assert r["target_future"] == round(100000 * 1.06 ** 5)
    assert abs(rural.rd_maturity(r["need_monthly_rd"], 60, 6.7) - r["target_future"]) < 60       # rounded to the rupee
    assert r["need_monthly_rd"] < r["need_monthly_cash"]                                       # interest does some of the work
    assert r["interest_rd"] == r["target_future"] - r["deposited_rd"] or abs(r["interest_rd"] - (r["target_future"] - r["deposited_rd"])) <= 60


def test_daily_amount_mode_and_months_to_goal_are_consistent():
    r = rural.daily_saving("other", None, 60, 10)
    assert r["monthly"] == 260 and r["matures"] == round(rural.rd_maturity(260, 60, 6.7)) and r["interest"] == r["matures"] - r["put_in"]
    n = rural.months_to_reach(50000, 1300, 6.7)
    assert rural.rd_maturity(1300, n, 6.7) >= 50000 > rural.rd_maturity(1300, n - 1, 6.7)
    assert rural.months_to_reach(1000, 0, 6.7) is None


def test_saving_that_eats_too_much_of_the_wage_is_called_unrealistic_with_a_longer_plan():
    r = rural.daily_saving("house", 200000, 12, None, 300)
    assert r["band"] == "red" and r["wage_share_pct"] > 30 and any("longer" in b.lower() or "take longer" in b.lower() for b in r["bullets"])
    assert rural.daily_saving("house", 20000, 60, None, 500)["band"] == "green"


def test_saving_questions_route_parse_and_do_not_steal_the_portfolio_goal():
    from backend import guide as G
    q = "I want 1 lakh for my daughter's marriage in 5 years, I earn 400 a day"
    assert A.answer(q, _ctx()).data["intent"] == "saving_goal"
    assert A._saving_args(q) == {"goal": "daughter", "daily_wage": 400.0, "months": 60, "target": 100000.0}
    assert A._saving_args("I can save 10 rupees a day for 3 years")["daily"] == 10.0
    assert A.answer("Will 10000 a month reach 50 lakh in 15 years?", _ctx()).data["intent"] == "goal"
    G.STATE.clear()
    g = G.begin("saving", q, "en", "s")                     # goal, cost, time and wage all came from the sentence
    assert g["done"] and g["params"]["goal"] == "daughter" and g["params"]["months"] == "60"
    english, _ = asyncio.run(H.convert("बेटी की शादी के लिए पाँच साल में एक लाख चाहिए, रोज़ कितना बचाऊँ", use_model=False))
    assert A.rule_intent(english) == "saving_goal" and "1 lakh" in english and "5 years" in english


# ---- E2: self-help group ledger -------------------------------------------------------------
def _group():
    L = {"group": "Jyoti SHG", "rate": 2, "loan_multiple": 3,
         "members": [{"id": "a", "name": "Sita"}, {"id": "b", "name": "Gita"}, {"id": "c", "name": "Rani"}], "entries": []}
    E = L["entries"]
    for mo in ("2025-01", "2025-02", "2025-03"):
        for m in ("a", "b", "c"):
            if m == "c" and mo != "2025-01":
                continue
            E.append({"date": mo + "-10", "member": m, "type": "saving", "amount": 500})
    E += [{"date": "2025-01-15", "member": "a", "type": "loan", "amount": 3000}, {"date": "2025-02-14", "member": "a", "type": "repay", "amount": 1000},
          {"date": "2025-03-01", "member": "b", "type": "fine", "amount": 20}]
    return L


def test_shg_interest_runs_on_the_balance_and_repayments_pay_interest_first():
    s = rural.shg_summary(_group(), "2025-03-31")
    sita = next(m for m in s["members"] if m["name"] == "Sita")
    # 30 days at 2% on 3000 = 60 interest, so the 1000 repayment is 60 interest + 940 principal
    assert sita["interest_paid"] == 60 and sita["outstanding"] == round(3000 - 940)
    # then 45 days at 2% a month on 2060
    assert sita["interest_due"] == round(2060 * 0.02 * 45 / 30) and sita["total_due"] == sita["outstanding"] + sita["interest_due"]


def test_shg_cash_identity_and_totals():
    s = rural.shg_summary(_group(), "2025-03-31")
    t = s["totals"]
    assert t["savings"] == 3500 and t["loans_out"] == 2060 and t["interest_income"] == 60 and t["fines"] == 20
    assert t["cash"] == t["savings"] + t["interest_income"] + t["fines"] - t["loans_out"] == 1520
    assert s["month"]["saving"] == 1000 and s["month"]["savers"] == 2 and "March 2025" in s["report"]


def test_shg_year_end_share_splits_interest_by_savings_and_adds_up():
    s = rural.shg_summary(_group(), "2025-03-31")
    shares = {m["name"]: m["year_end_share"] for m in s["members"]}
    assert shares["Sita"] == shares["Gita"] == 26 and shares["Rani"] == 9
    assert abs(sum(shares.values()) - s["totals"]["interest_income"]) <= 2


def test_shg_flags_missed_saving_overdue_and_overlending():
    s = rural.shg_summary(_group(), "2025-03-31")
    assert any("Rani" in a and "missed" in a for a in s["alerts"])
    L = _group(); L["entries"].append({"date": "2025-03-20", "member": "c", "type": "loan", "amount": 5000})
    s2 = rural.shg_summary(L, "2025-03-31")
    assert any("Rani" in a and "times their savings" in a for a in s2["alerts"])
    L2 = _group()
    s3 = rural.shg_summary(L2, "2025-06-30")                                # Sita stops repaying
    assert next(m for m in s3["members"] if m["name"] == "Sita")["overdue"] and any("Sita" in a and "not repaid" in a for a in s3["alerts"])
    L3 = _group(); L3["entries"].append({"date": "2025-03-25", "member": "b", "type": "loan", "amount": 9000})
    assert rural.shg_summary(L3, "2025-03-31")["totals"]["cash"] < 0 and "more than it has" in rural.shg_summary(L3, "2025-03-31")["alerts"][0]


def test_shg_can_lend_runs_three_checks_and_ignores_bad_entries():
    L = _group()
    assert rural.shg_can_lend(L, "b", 1000, "2025-03-31")["ok"]
    r = rural.shg_can_lend(L, "c", 1000, "2025-03-31")                      # Rani saved only 500 and missed months; 1000 is within cash and 3x savings
    assert not r["ok"] and [c["id"] for c in r["checks"] if not c["ok"]] == ["clean"]
    big = rural.shg_can_lend(L, "c", 2000, "2025-03-31")                    # more than the group has in hand and more than 3x her savings
    assert [c["id"] for c in big["checks"] if not c["ok"]] == ["cash", "limit", "clean"]
    L["entries"] += [{"date": "bad", "member": "a", "type": "saving", "amount": 99}, {"date": "2025-03-02", "member": "zz", "type": "saving", "amount": 99},
                     {"date": "2025-03-02", "member": "a", "type": "gift", "amount": 99}, {"date": "2025-03-02", "member": "a", "type": "saving", "amount": -5}]
    assert rural.shg_summary(L, "2025-03-31")["totals"]["savings"] == 3500


def test_shg_statements_exist_for_every_member_in_both_languages_and_route_works():
    for lang in ("en", "hi"):
        s = rural.shg_summary(_group(), "2025-03-31", lang)
        assert set(s["statements"]) == {"a", "b", "c"} and "Sita" in s["statements"]["a"]
    assert A.answer("how do I keep the accounts of our self help group", _ctx()).data["intent"] == "shg_ledger"
    from backend import guide as G
    g = G.intercept("open the group ledger", "en", "x").data["guide"]
    assert g["route"] == "/rural" and g["params"] == {"tool": "shg"} and g["done"]
