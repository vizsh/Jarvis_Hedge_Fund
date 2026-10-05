"""The understanding layer: the whole sentence decides the answer, not one keyword in it."""
import re

import pytest

from backend import assistant, explain, knowledge, scams, tours, understand
from backend.session import Session

# an explanation may say how buying works; it must never tell anyone to buy or sell, or predict a price
ADVICE = re.compile(r"(bullish|bearish|target price|will rise|will fall|undervalued|overvalued|you should (buy|sell)|i recommend|buy now|sell now)", re.I)
SIGNAL_WORDS = re.compile(r"\b(buy|sell|hold|bullish|bearish|target price|will rise|will fall|outperform|underperform|upside|undervalued|overvalued)\b", re.I)


@pytest.fixture(scope="module")
def session():
    from backend import portfolios
    s = Session.create()
    s.reprice()
    d = portfolios.load(s.conn, "preset_typical_retail")
    s.set_portfolio(d["name"], d["cash"], d["positions"], "preset_typical_retail")
    return s


def ask(session, q, lang="en", route=""):
    import asyncio
    ctx = assistant.Ctx(pit=session.pit, portfolio=session.portfolio, prices=session.prices, policy=session.policy, conn=session.conn,
                        convo=explain.Conversation(), lang=lang)
    understand.REQ_ROUTE.set(route)
    return asyncio.run(assistant.aanswer(q, ctx))


def text_of(a, notes=True):
    """Everything shown. `notes=False` leaves out the standing disclaimer ("not a recommendation to buy or sell")."""
    parts = [a.headline, *a.bullets] + ([a.action or "", a.detail or ""] if notes else [])
    if a.table:
        parts += [c for row in a.table["rows"] for c in row]
    for s in (a.data or {}).get("sections", []):
        parts += [i["title"] + " " + i["why"] for i in s["items"]]
    return " ".join(parts)


# ------------------------------------------------------------------------------------------------ app questions
@pytest.mark.parametrize("q,tour", [
    ("how do I use the fee slider", "fee"),
    ("walk me through the audit record", "audit"),
    ("how does the overlap checker work", "overlap"),
    ("explain the emergency meter", "emergency"),
    ("how do I use the tip checker", "tip"),
    ("show me how the research page works", "research"),
    ("how does the WhatsApp feature work", "whatsapp"),
    ("explain the Govern page", "govern"),
    ("how do I use the scam check feature", "protect"),
    ("how does this prototype work", "overview"),
])
def test_a_question_about_a_feature_gets_its_own_guided_tour(session, q, tour):
    a = ask(session, q)
    assert a.kind == "feature_help" and a.data["tour"] == tour, (q, a.kind, a.data.get("tour"))
    assert a.table and len(a.table["rows"]) == len(tours.BY_ID[tour]["steps"])


def test_this_feature_means_the_page_that_is_open(session):
    assert ask(session, "help me understand this feature", route="/practice?tool=fee").data["tour"] == "fee"
    assert ask(session, "help me understand this feature", route="/govern").data["tour"] == "govern"
    assert ask(session, "help me understand this feature", route="/protect?tool=tip").data["tour"] == "tip"


def test_a_portfolio_question_is_not_mistaken_for_a_question_about_the_app(session):
    assert ask(session, "explain my portfolio risk").kind != "feature_help"
    assert ask(session, "how is my portfolio doing").kind != "feature_help"


def test_every_tour_is_complete_in_both_languages():
    for t in tours.TOURS:
        assert t["steps"], t["id"]
        for s in t["steps"]:
            assert s["title"]["en"] and s["title"]["hi"] and s["body"]["en"] and s["body"]["hi"], t["id"]
            assert s["route"].startswith("/"), t["id"]
            # a spotlight selector must be a selector, never prose
            assert s["sel"] is None or not re.search(r"[.!?]\s", s["sel"]), (t["id"], s["sel"])
        assert re.search(r"[ऀ-ॿ]", t["title"]["hi"] + t["what"]["hi"] + t["example"]["hi"]), t["id"]


def test_every_tour_example_question_opens_that_tour(session):
    for t in tours.TOURS:
        assert ask(session, t["example"]["en"]).data.get("tour") is not None, t["example"]["en"]


# ------------------------------------------------------------------------------------------------ companies
def test_analyse_a_company_gives_facts_a_chart_and_both_sides_without_a_signal(session):
    for q in ("analyse TCS for me", "how is HDFC bank doing", "Is Infosys a good stock to look at right now? show me the chart"):
        a = ask(session, q)
        assert a.kind == "stock_analysis", q
        ch = a.data["chart"]
        assert ch and ch["kind"] == "price" and len(ch["points"]) > 100 and ch["source"] in ("live", "snapshot")
        assert [s["kind"] for s in a.data["sections"]] == ["good", "watch"]
        assert a.facts and a.visual["page"] == "research" and a.data["investigate"].startswith("Investigate")
        assert not SIGNAL_WORDS.search(text_of(a, notes=False)), (q, SIGNAL_WORDS.search(text_of(a, notes=False)).group(0))


def test_comparing_two_companies_gives_one_table_and_a_rebased_chart(session):
    a = ask(session, "compare reliance and hdfc bank")
    assert a.kind == "stock_compare" and len(a.table["columns"]) == 3
    assert a.data["chart"]["kind"] == "compare" and all(s["points"][0][1] == 100.0 for s in a.data["chart"]["series"])
    assert ask(session, "which stock is better TCS or Infosys").kind == "stock_compare"
    assert not SIGNAL_WORDS.search(text_of(a, notes=False))


def test_should_i_buy_still_gets_the_portfolio_fit_answer_and_an_unknown_company_is_not_guessed(session):
    assert ask(session, "should I buy infosys").data["intent"] == "should_buy"
    a = ask(session, "analyse zzqqxx")
    assert a.kind in ("stock_unknown", "clarify") and a.kind != "stock_analysis"


# ------------------------------------------------------------------------------------------------ scams
@pytest.mark.parametrize("q,scam", [
    ("I got a call from someone saying they are from SBI and asked for my OTP, what do I do", "bank_otp"),
    ("someone from police called me on video says I am under digital arrest", "digital_arrest"),
    ("I got a message that my electricity will be cut tonight call this number", "sim_utility"),
    ("a loan app is threatening to send my photos to my contacts", "loan_app"),
    ("I am being offered a part time job to like youtube videos and earn 3000 a day", "task_job"),
    ("a courier parcel in my name has drugs and customs wants a fee", "courier"),
    ("he asked me to install anydesk to fix my bank problem", "remote_app"),
])
def test_each_scam_gets_its_own_script_not_one_reply_for_the_word_scam(session, q, scam):
    a = ask(session, q)
    assert a.kind == "scam_help" and a.data["scam"] == scam, (q, a.kind, a.data.get("scam"))
    assert a.table and len(a.table["rows"]) == 3 and "1930" in " ".join(f["value"] for f in a.facts)


def test_after_a_loss_it_gives_the_recovery_steps_not_the_warning(session):
    assert ask(session, "my father lost 50000 on a whatsapp stock group, how do I recover it").kind == "scam_recovery"


def test_every_scam_script_is_complete_in_both_languages():
    for s in scams.SCAMS:
        for k in ("head", "says", "truth", "now", "never"):
            assert s[k]["en"] and s[k]["hi"], (s["id"], k)
        assert len(s["says"]["en"]) == len(s["truth"]["en"]) == 3 == len(s["says"]["hi"]) == len(s["truth"]["hi"])


# ------------------------------------------------------------------------------------------------ general money questions
@pytest.mark.parametrize("q,cid", [
    ("what is the difference between SIP and lumpsum", "sip_vs_lumpsum"),
    ("I have 5 lakh, how should I split it between FD and mutual funds", "fd_vs_mf"),
    ("how are mutual funds taxed", "tax_basics"),
    ("what is pe ratio", "pe_ratio"),
    ("is gold a good investment", "gold"),
    ("what should I do when the market falls", "market_falls"),
    ("is it better to buy a house or rent", "rent_vs_buy"),
    ("how do I check if my advisor is sebi registered", "check_advisor"),
    ("can i trust a youtube finance channel", "check_advisor"),
    ("do you make up numbers", "how_accurate"),
    ("is my data private", "privacy"),
    ("should i prepay my home loan", "emi_loans"),
    ("how do I become rich", "start_investing"),
    ("what is diversification", "diversification_idea"),
])
def test_a_general_money_question_gets_the_matching_explanation(session, q, cid):
    a = ask(session, q)
    assert a.kind == "concept" and a.data["concept"] == cid, (q, a.kind, a.data.get("concept"))
    assert len(a.bullets) >= 3 and a.action


def test_a_question_with_figures_still_goes_to_the_calculator(session):
    assert ask(session, "What does a 2% fee cost over 20 years?").data["intent"] == "fee_drag"
    assert ask(session, "how long will 3 lakh last if I spend 40000 a month").data["intent"] == "emergency"


def test_knowledge_is_complete_in_both_languages_and_never_gives_a_signal():
    for c in knowledge.CONCEPTS:
        assert c["head"]["en"] and c["head"]["hi"] and len(c["points"]["en"]) == len(c["points"]["hi"]) >= 3, c["id"]
        assert c["watch"]["en"] and c["watch"]["hi"], c["id"]
        assert re.search(r"[ऀ-ॿ]", c["head"]["hi"]), c["id"]
        en = " ".join([c["head"]["en"], *c["points"]["en"], c["watch"]["en"]])
        assert not ADVICE.search(en), (c["id"], ADVICE.search(en).group(0))
        if c["table"]:
            assert len(c["table"]["rows"]["en"]) == len(c["table"]["rows"]["hi"]), c["id"]
            assert len(c["table"]["columns"]["en"]) == len(c["table"]["columns"]["hi"]), c["id"]


def test_every_follow_up_chip_offered_by_a_concept_or_a_stock_answer_is_answerable(session):
    chips = set()
    for q in ("what is the difference between SIP and lumpsum", "how are mutual funds taxed", "is gold a good investment", "analyse TCS", "compare reliance and hdfc bank",
              "how do I use the fee slider"):
        chips.update(ask(session, q).follow_ups)
    for c in knowledge.CONCEPTS:
        chips.update(q for q, _ in c["follow"])
    for chip in chips:
        assert ask(session, chip).kind not in ("clarify", "out_of_scope"), chip


def test_answers_are_written_in_hindi_when_asked_in_hindi(session):
    for q in ("what is the difference between SIP and lumpsum", "analyse TCS", "how do I use the fee slider", "someone from police called me on video says I am under digital arrest"):
        a = ask(session, q, "hi")
        assert a.lang == "hi" and re.search(r"[ऀ-ॿ]", a.headline), q
        assert a.follow_ups_hi and len(a.follow_ups_hi) == len(a.follow_ups), q


def test_explain_like_i_am_ten_shortens_the_answer(session):
    full = ask(session, "what is compounding")
    short = ask(session, "explain compounding like I am 10")
    assert short.kind == "concept" and len(short.bullets) < len(full.bullets)


def test_why_did_my_portfolio_fall_is_answered_from_the_attribution_not_a_stress_test(session):
    a = ask(session, "why did my portfolio fall")
    assert a.kind == "portfolio_move" and a.table["rows"] and a.data["window"] in ("1m", "3m")
    assert "points" in a.headline or "ahead" in a.headline or "behind" in a.headline
