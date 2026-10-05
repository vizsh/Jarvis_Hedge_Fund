"""The assistant must be right, not merely fluent: correct routing, figures that equal the
calculators, Hindi that keeps the numbers, and a refusal to guess when it does not know."""
from __future__ import annotations

import re

import pytest

from analysis import goal as goal_mod
from analysis import tools
from backend import assistant as A
from backend import explain, portfolios, practice
from backend import vernacular as V
from backend.intent_data import EXAMPLES
from backend.session import Session
from tests.chat_eval_blind import BLIND
from tests.chat_eval_data import EVAL


@pytest.fixture(scope="module")
def session() -> Session:
    s = Session.create()
    s.reprice()
    d = portfolios.load(s.conn, "preset_typical_retail")
    if not d:
        pytest.skip("example portfolio not seeded")
    s.set_portfolio(d["name"], d["cash"], d["positions"], "preset_typical_retail")
    return s


@pytest.fixture(autouse=True)
def _no_saved_funds_leak(session):
    """The test session shares the app database: never leave a user's saved funds changed."""
    before = A.my_funds(session.conn)
    for f in before:
        A.set_my_fund(session.conn, f, False)
    yield
    for f in A.my_funds(session.conn):
        A.set_my_fund(session.conn, f, False)
    for f in before:
        A.set_my_fund(session.conn, f, True)


def ask(session, q, lang="en", convo=None, level="normal"):
    ctx = A.Ctx(session.pit, session.portfolio, session.prices, session.policy, session.conn,
                convo if convo is not None else explain.Conversation(), lang, level)
    return A.answer(q, ctx)


# ----------------------------------------------------------------------------- routing
def _score(data):
    right = wrong = asked = 0
    for text, want in data:
        got, _ = A.detect(text)
        if got == want:
            right += 1
        elif got in ("clarify",):
            asked += 1
        else:
            wrong += 1
    return right, wrong, asked


def test_router_accuracy_on_both_sets():
    r1, w1, a1 = _score(EVAL)
    r2, w2, a2 = _score(BLIND)
    assert r1 / len(EVAL) >= 0.97, (r1, w1, a1)
    assert r2 / len(BLIND) >= 0.95, (r2, w2, a2)


def test_a_confident_wrong_answer_is_rarer_than_asking():
    """Not understanding should mean asking, not answering a different question."""
    for data in (EVAL, BLIND):
        _, wrong, _ = _score(data)
        assert wrong / len(data) <= 0.01


def test_blind_sentences_are_not_in_the_training_data():
    """The first set doubles as a rule regression suite and may overlap the examples; the blind
    set is the honest generalisation measure, so it must not."""
    seen = {A._mask(x) for items in EXAMPLES.values() for x in items}
    leaked = [t for t, _ in BLIND if A._mask(t) in seen]
    assert not leaked, leaked


def test_similarity_model_surfaces_the_right_intent_in_its_top_three():
    """The trained model only SUGGESTS (it was right about half the time as a decider), so what
    matters is that the intent the person meant is among its top three suggestions."""
    hit = tot = 0
    for label, items in EXAMPLES.items():
        if label == "chitchat":
            continue
        for it in items:
            tot += 1
            hit += label in [i for i, _ in A.knn_rank(it, exclude=it)[:3]]
    assert hit / tot >= 0.70, (hit, tot)


def test_gibberish_and_offtopic_are_not_answered_as_money_advice(session):
    assert ask(session, "asdf qwerty zxcv").kind == "clarify"
    assert ask(session, "what is the weather in delhi").kind == "out_of_scope"
    assert ask(session, "which stock will double next year").kind == "predict"


# ----------------------------------------------------------------------------- parsing
@pytest.mark.parametrize("text,lump,monthly,years,pcts", [
    ("invest 5 lakh at 2% fee for 20 years", 500000, None, 20, [2.0]),
    ("SIP of 10k per month for 15 years", None, 10000, 15, []),
    ("I have Rs. 3,50,000 and spend 40000 a month", 350000, 40000, None, []),
    ("1.5 cr for 10 yrs with a 1.5 percent fee", 15000000, None, 10, [1.5]),
    ("₹50,000 once and 5k monthly over 12 years", 50000, 5000, 12, []),
    ("covid 2020 crash", None, None, None, []),
])
def test_quantity_parsing(text, lump, monthly, years, pcts):
    roles = tools.money_roles(text)
    q = tools.quantities(text)
    assert roles["lump"] == lump and roles["monthly"] == monthly
    assert (int(q["years"][0]["v"]) if q["years"] else None) == years
    assert [p["v"] for p in q["pct"]] == pcts


# ----------------------------------------------------------------------------- figures
def test_fee_answer_equals_the_calculator(session):
    a = ask(session, "what does a 2% fee cost over 20 years")
    want = tools.fee_drag(100000, 0, 20, 12.0, 2.0, 0.2)
    assert a.data["fee_drag"]["lost_vs_low"] == want["lost_vs_low"]
    assert tools.inr(want["lost_vs_low"]) in a.headline
    assert any(tools.inr(want["final_high"]) == f["value"] for f in a.facts)


def test_fee_answer_reads_sip_years_and_two_fees(session):
    a = ask(session, "compare a 1.5% fee against 0.5% on a 10000 a month sip for 15 years")
    d = a.data["fee_drag"]
    assert (d["monthly"], d["principal"], d["years"], d["fee_pct"], d["low_fee_pct"]) == (10000, 0, 15, 1.5, 0.5)
    assert d == tools.fee_drag(0, 10000, 15, 12.0, 1.5, 0.5) | {}


def test_fee_calculator_matches_a_closed_form():
    # lump sum, no contributions: P * (1+net)^years exactly, however it is compounded monthly
    r = tools.fee_drag(100000, 0, 10, 12.0, 2.0, 0.0)
    assert abs(r["final_high"] - 100000 * 1.10 ** 10) < 2
    assert abs(r["final_free"] - 100000 * 1.12 ** 10) < 2
    assert tools.fee_drag(0, 5000, 5, 0.0, 0.0, 0.0)["final_high"] == 5000 * 60      # zero return


def test_emergency_runway_and_shortfall(session):
    a = ask(session, "how long will 3 lakh last if I spend 40000 a month")
    e = a.data["emergency"]
    assert e["runway_cash"] == 7.5 and e["band"] == "green" and e["shortfall"] == 0
    b = ask(session, "I have 1 lakh and spend 40000 a month, how long will it last")
    assert b.data["emergency"]["runway_cash"] == 2.5 and b.data["emergency"]["band"] == "red"
    assert b.data["emergency"]["shortfall"] == 140000
    assert "2.5 months" in b.headline


def test_emergency_asks_when_it_is_missing_a_number(session):
    a = ask(session, "how long will my savings last")
    assert "emergency" not in a.data and ("monthly" in a.headline.lower() or "spending" in a.headline.lower())


def test_overlap_numbers_equal_the_overlap_engine(session):
    a = ask(session, "do large cap fund a and bluechip fund b overlap")
    o = practice.overlap("largecap_a", "bluechip_b", lambda t: t)
    assert a.data["overlap_pct"] == o["overlap_pct"]
    assert A._pc(o["overlap_pct"]) + "%" in a.headline
    c = ask(session, "do the technology fund and the healthcare fund overlap")
    assert c.data["overlap_pct"] == 0 and "no stocks" in " ".join(c.bullets).lower()


def test_goal_answer_equals_the_simulation(session):
    a = ask(session, "will 10000 a month reach 50 lakh in 15 years")
    want = goal_mod.fan(session.pit, session.portfolio, session.prices, 10000, 15, 5_000_000)
    assert a.data["goal"]["prob_target"] == want["prob_target"]
    assert f"{want['prob_target'] * 100:.0f}%" in a.headline


def test_panic_answer_uses_real_replay(session):
    from analysis import panic
    a = ask(session, "what if I had sold during the covid crash")
    r = panic.replay(session.pit, session.portfolio, session.prices, "covid")
    assert tools.inr(r["trough_value"]) in a.headline


# ----------------------------------------------------------------------------- my funds
def test_my_funds_can_be_saved_and_compared(session):
    ask(session, "remove all my funds")
    a = ask(session, "which of my mutual funds overlap")
    assert "at least two" in a.headline.lower()
    ask(session, "I own large cap fund a and bluechip fund b")
    assert set(A.my_funds(session.conn)) == {"largecap_a", "bluechip_b"}
    b = ask(session, "which of my mutual funds overlap")
    assert b.data["overlap_pct"] > 80
    ask(session, "remove the bluechip fund from my funds")
    assert A.my_funds(session.conn) == ["largecap_a"]
    ask(session, "clear all my saved funds")
    assert A.my_funds(session.conn) == []


def test_weak_fund_words_do_not_hijack_stock_questions(session):
    assert A.find_funds("is TCS a tech stock") == []
    assert A.find_funds("compare the technology fund and the banking fund") == ["it_fund", "bank_fund"]
    assert A.find_funds("fund A and fund B") == ["largecap_a", "bluechip_b"]


# ----------------------------------------------------------------------------- Hindi and chips
HINDI_QS = ["do large cap fund a and bluechip fund b overlap", "what does a 2% fee cost over 20 years",
            "how long will 3 lakh last if I spend 40000 a month", "will 10000 a month reach 50 lakh in 15 years",
            "what if I had sold during the covid crash", "is my ledger intact", "give me my weekly digest"]


def _nums(text):
    return V._numbers(text)


@pytest.mark.parametrize("q", HINDI_QS)
def test_hindi_answers_keep_every_headline_number(session, q):
    en, hi = ask(session, q, "en"), ask(session, q, "hi")
    assert hi.lang == "hi" and V.looks_hindi(hi.headline)
    # English "₹1.00 lakh" and Hindi "1.00 लाख रुपये" carry the same digits
    for n, c in _nums(en.headline).items():
        if n in ("1", "2", "3", "4", "5"):        # tiny numerals can be words in either language
            continue
        assert _nums(hi.headline)[n] >= 1, (q, n, en.headline, hi.headline)
    assert [f["label"] for f in hi.facts] != [f["label"] for f in en.facts] or not hi.facts


def test_every_suggested_followup_is_routed_somewhere_useful(session):
    seen = set()
    for q in [*HINDI_QS, "someone called asking for my otp", "which mutual funds do you have", "what can you do",
              "I own the technology fund", "what is inside the banking fund", "hello"]:
        a = ask(session, q)
        for chip in a.follow_ups:
            seen.add(chip)
    assert seen
    for chip in seen:
        got = ask(session, chip)                      # the whole understanding layer, not just the older keyword rules
        assert got.kind not in ("clarify", "out_of_scope"), chip


def test_hindi_chips_pair_up_with_english_questions(session):
    a = ask(session, "do large cap fund a and bluechip fund b overlap", "hi")
    assert len(a.follow_ups_hi) == len(a.follow_ups) and all(V.looks_hindi(x) for x in a.follow_ups_hi)


def test_simpler_applies_to_tool_answers(session):
    convo = explain.Conversation()
    ask(session, "what does a 2% fee cost over 20 years", convo=convo)
    s = ask(session, "explain that simpler", convo=convo)
    assert s.kind == "fee_drag" and len(s.bullets) <= 1 and s.table is None


# ----------------------------------------------------------------------------- safety of content
def test_tip_scanner_flags_an_obvious_scam(session):
    a = ask(session, "is this telegram tip legit: SURE SHOT! TCS profit up 300%, target 9000, guaranteed returns, join my VIP group today")
    assert a.kind == "tip_scan" and "SCAM" in a.headline.upper()


def test_scam_help_gives_the_real_helpline_and_never_asks_for_secrets(session):
    a = ask(session, "I lost money to a fake call what do I do")
    text = " ".join([a.headline, *a.bullets, a.action or ""])
    assert "1930" in text and "cybercrime.gov.in" in text
    b = ask(session, "someone asked for my otp")
    whole = " ".join([b.headline, *b.bullets, b.action or ""]).lower()
    assert "never" in whole or "no bank" in whole


def test_predictions_are_refused_politely(session):
    a = ask(session, "which stock will double next year")
    assert a.kind == "predict" and "predict" in a.headline.lower()


def test_ledger_answer_reflects_the_real_chain(session):
    a = ask(session, "is my ledger intact")
    assert a.kind == "ledger" and ("intact" in a.headline.lower() or "tamper" in a.headline.lower())


# ----------------------------------------------------------------------------- no crashes
@pytest.mark.parametrize("lang", ["en", "hi"])
def test_every_evaluation_sentence_produces_a_complete_answer(session, lang):
    for text, _ in (*EVAL, *BLIND):
        a = ask(session, text, lang)
        assert a.headline and isinstance(a.follow_ups, list), text
        d = a.as_dict()
        assert set(("facts", "table", "visual", "lang", "follow_ups_hi")) <= set(d)
        if a.table:
            assert all(len(r) == len(a.table["columns"]) for r in a.table["rows"]), text
        for f in a.facts:
            assert f["value"] and not re.search(r"nan|inf\b", f["value"], re.I), (text, f)


# ----------------------------------------------------------------------------- third set + LLM stage
def test_third_set_after_tuning_has_no_confident_wrong_answers():
    from tests.chat_eval_blind3 import BLIND3
    right, wrong, asked = _score(BLIND3)
    assert wrong == 0 and right / len(BLIND3) >= 0.95, (right, wrong, asked)


def _run(coro):
    import asyncio
    return asyncio.run(coro)


def test_llm_stage_runs_the_calculator_for_the_intent_it_picks(session, monkeypatch):
    async def fake(text):
        return "fee_drag", 0.9
    monkeypatch.setattr(A, "llm_intent", fake)
    ctx = A.Ctx(session.pit, session.portfolio, session.prices, session.policy, session.conn, explain.Conversation(), "en")
    out = _run(A.aanswer("zork flim blorp", ctx))
    assert out.kind == "fee_drag" and out.data["routed_by"] == "llm" and "fee_drag" in out.data


def test_llm_stage_is_ignored_when_unsure_or_unavailable(session, monkeypatch):
    for result in (("fee_drag", 0.4), ("none", 0.99), (None, 0.0)):
        async def fake(text, r=result):
            return r
        monkeypatch.setattr(A, "llm_intent", fake)
        ctx = A.Ctx(session.pit, session.portfolio, session.prices, session.policy, session.conn, explain.Conversation(), "en")
        assert _run(A.aanswer("zork flim blorp", ctx)).kind == "clarify"


def test_specific_rules_are_never_overruled_by_the_model(session, monkeypatch):
    called = []

    async def fake(text):
        called.append(text)
        return "xray", 0.99
    monkeypatch.setattr(A, "llm_intent", fake)
    ctx = A.Ctx(session.pit, session.portfolio, session.prices, session.policy, session.conn, explain.Conversation(), "en")
    out = _run(A.aanswer("what does a 2% fee cost over 20 years", ctx))
    assert out.kind == "fee_drag" and not called


def test_a_long_loose_keyword_match_can_be_corrected_by_a_confident_model(session, monkeypatch):
    async def fake(text):
        return "correlation", 0.9
    monkeypatch.setattr(A, "llm_intent", fake)
    q = "i wonder whether several of the companies i hold might all dip at the same moment in a crash"
    ctx = A.Ctx(session.pit, session.portfolio, session.prices, session.policy, session.conn, explain.Conversation(), "en")
    assert A.detect(q)[1] in ("legacy", "none")
    assert _run(A.aanswer(q, ctx)).data["intent"] in ("correlation", "clarify")


def test_fourth_set_has_no_confident_wrong_answers_and_hinglish_is_asked_not_guessed():
    from tests.chat_eval_blind4 import BLIND4
    right, wrong, asked = _score(BLIND4)
    assert wrong == 0, (right, wrong, asked)
    for text in ("mere mutual funds ek jaise stocks rakhte hain kya", "kaun sa stock double hoga"):
        assert A.detect(text)[0] == "clarify"        # offline: asks; the local-model stage reads Hinglish


def test_scam_answer_picks_the_matching_rehearsal(session):
    assert ask(session, "someone called asking for my otp").visual["params"]["scenario"] == "kyc"
    assert ask(session, "a man on a video call says i am under digital arrest").visual["params"]["scenario"] == "police"


def test_every_glossary_term_has_hindi_and_hindi_mode_uses_it(session):
    from backend.glossary_hi import GLOSSARY_HI
    assert set(explain.GLOSSARY) <= set(GLOSSARY_HI)
    for term in ("expense ratio", "mutual fund", "beta", "digital arrest"):
        a = ask(session, f"what is {term}", "hi")
        if a.kind in ("concept", "scam_help"):       # a fuller hand-written explanation exists for this term
            assert a.lang == "hi" and V.looks_hindi(a.headline)
            continue
        assert a.lang == "hi" and a.headline == GLOSSARY_HI[term]
        assert V.looks_hindi(a.headline)


def test_tip_scan_labels_are_hindi_in_hindi_mode(session):
    a = ask(session, "is this telegram tip legit: SURE SHOT! TCS profit up 300%, target 9000, guaranteed returns, join my VIP group today", "hi")
    text = " ".join(a.bullets)
    assert "पक्के मुनाफ़े का वादा" in text and "Promises" not in text


def test_every_flow_has_complete_hindi_that_lines_up_with_english():
    from backend import flows
    from backend.flows_hi import FLOWS_HI
    assert set(flows.FLOWS) == set(FLOWS_HI)
    for fid, f in flows.FLOWS.items():
        hi = FLOWS_HI[fid]
        assert len(hi["steps"]) == len(f.steps), fid
        loc = flows.localize(f.as_dict(), "hi")
        for en, h in zip(f.steps, loc["steps"]):
            assert V.looks_hindi(h["text"]), (fid, h["text"])
            assert bool(en.note) == bool(h["note"]), (fid, en.text)
            assert len(en.options) == len(h["options"])
            assert all(V.looks_hindi(o["label"]) and V.looks_hindi(o["consequence"]) for o in h["options"])
            assert h["question"] == en.question and h["endpoint"] == en.endpoint     # behaviour is untouched
        # every figure in the English text is still in the Hindi (tax rates, limits)
        for en, h in zip(f.steps, loc["steps"]):
            for n in V._numbers(en.text + " ".join(o["consequence"] for o in en.options)):
                assert n in V._numbers(h["text"] + " ".join(o["consequence"] for o in h["options"])), (fid, n)


def test_each_request_uses_its_own_language_not_the_servers_last_one(session, monkeypatch):
    """Two screens in different languages must not override each other (the server-wide language
    used to make an English screen answer in Hindi after another screen chose it)."""
    import asyncio
    from backend import app as app_mod
    monkeypatch.setattr(app_mod, "session", session)
    app_mod.LANG = "hi"                                    # as if another screen had chosen Hindi
    try:
        en = asyncio.run(app_mod.ask(app_mod.AskIn(question="what does a 2% fee cost over 20 years", lang="en")))
        hi = asyncio.run(app_mod.ask(app_mod.AskIn(question="what does a 2% fee cost over 20 years", lang="hi")))
        assert en["lang"] == "en" and not V.looks_hindi(en["headline"])
        assert hi["lang"] == "hi" and V.looks_hindi(hi["headline"])
    finally:
        app_mod.LANG = "en"
