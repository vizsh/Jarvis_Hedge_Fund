import pytest

from backend import guide as G


@pytest.fixture(autouse=True)
def _clean():
    G.STATE.clear(); G.LAST_SCHEMES.clear()


def run(cid, tool, first, answers, lang="en"):
    g = G.begin(tool, first, lang, cid)
    trail = [g]
    for a in answers:
        g = G.fill(cid, a, lang)
        trail.append(g)
    return trail


def test_loan_takes_what_it_can_from_the_sentence_and_asks_only_for_the_rest():
    g = G.begin("loan", "my sahukar charges 5 rupees per hundred a month", "en", "c")
    assert g["ask"]["slot"] == "principal" and g["params"]["rate"] == "5.0"
    g = G.fill("c", "50000", "en"); assert g["ask"]["slot"] == "months"
    g = G.fill("c", "2 years", "en")
    assert g["done"] and g["route"] == "/rural" and g["params"]["months"] == "24" and g["params"]["run"] == "1"
    assert "60% a year" in g["say"] and "c" not in G.STATE


def test_a_complete_sentence_runs_at_once():
    g = G.begin("loan", "what does 5 rupees per hundred a month cost on 50000 for 10 months", "en", "c")
    assert g["done"] and g["params"]["principal"] == "50000.0"


def test_schemes_conversation_uses_choices_and_remembers_the_result_for_documents():
    t = run("c", "schemes", "", ["I am 42", "woman", "farmer", "own land", "yes", "yes"])
    assert [x["ask"]["slot"] for x in t[:-1]] == ["age", "gender", "work", "land", "poor", "bank"]
    assert t[-1]["done"] and "pm_kisan" in G.LAST_SCHEMES["c"]
    d = G.begin("docs", "", "en", "c")                       # schemes carried over: only the papers are asked
    assert d["ask"]["slot"] == "have"
    d = G.fill("c", "aadhaar, bank passbook", "en")
    assert d["done"] and "aadhaar" in d["params"]["have"] and d["say"]


def test_income_slots_and_hindi():
    g = G.begin("income", "", "hi", "c")
    g = G.fill("c", "अक्टूबर में 1.2 लाख और अप्रैल में 60 हज़ार", "hi")
    assert g["ask"]["slot"] == "cost"
    g = G.fill("c", "आठ हज़ार", "hi"); g = G.fill("c", "कोई नहीं", "hi")
    assert g["done"] and "आमदनी" in g["say"] or "कमाई" in g["say"]


def test_unparseable_answer_reasks_then_lets_a_new_question_through():
    G.begin("loan", "", "en", "c")
    r = G.fill("c", "hmm", "en")
    assert r["retry"] and r["ask"]["slot"] == "principal"
    assert G.fill("c", "which government schemes can I get", "en") is None      # second miss + a clear question: released
    assert "c" not in G.STATE


def test_cancel_and_navigation():
    G.begin("loan", "", "en", "c")
    assert G.fill("c", "cancel", "en")["cancelled"] and not G.active("c")
    a = G.intercept("open the protect page", "en", "c")
    assert a.data["guide"]["route"] == "/protect" and a.follow_ups
    a = G.intercept("सुरक्षा पेज खोलिए", "hi", "c"); assert a.data["guide"]["route"] == "/protect"
    a = G.intercept("take me to the moneylender check", "en", "c"); assert a.data["guide"]["ask"]["slot"] == "principal"
    assert G.intercept("show me how my portfolio is doing today please", "en", "z") is None     # long question: not navigation


def test_open_while_a_question_is_pending_navigates_instead_of_failing():
    G.begin("loan", "", "en", "c")
    a = G.intercept("open the learn page", "en", "c")
    assert a.data["guide"]["route"] == "/learn" and not G.active("c")


# ---- fee drag, emergency, goal (answered by the existing handlers) -----------------------------
@pytest.fixture
def ctx_factory():
    from backend import assistant, portfolios
    from backend.session import Session
    s = Session.create(); s.reprice()
    d = portfolios.load(s.conn, "preset_typical_retail")
    s.set_portfolio(d["name"], d["cash"], d["positions"], "preset_typical_retail")
    G.ctx_factory = lambda lang: assistant.Ctx(s.pit, s.portfolio, s.prices, s.policy, s.conn, None, lang)
    yield
    G.ctx_factory = None


def test_emergency_asks_two_things_then_opens_the_meter_with_the_answer(ctx_factory):
    g = G.begin("emergency", "how long will my savings last", "en", "c")
    assert g["route"] == "/practice" and g["ask"]["slot"] == "cash"
    g = G.fill("c", "3 lakh", "en"); assert g["ask"]["slot"] == "exp" and not g["navigate"]
    g = G.fill("c", "40000", "en")
    assert g["done"] and g["params"]["cash"] == "300000.0" and "7.5 months" in g["say"] and g["params"]["run"] == "1"


def test_fee_drag_flow_and_skipping_the_optional_fee(ctx_factory):
    G.begin("fee", "what does the fund fee cost me", "en", "c")
    G.fill("c", "every month", "en"); G.fill("c", "10000", "en"); g = G.fill("c", "20 years", "en")
    assert g["ask"]["slot"] == "fee" and g["ask"]["optional"]
    g = G.fill("c", "skip", "en")
    assert g["done"] and g["params"]["monthly"] == "10000.0" and g["params"]["years"] == "20" and "2% fee" in g["say"]


def test_goal_flow_in_hindi_and_figures_come_from_the_calculator(ctx_factory):
    G.begin("goal", "", "hi", "c")
    G.fill("c", "पचास लाख", "hi"); G.fill("c", "दस हज़ार", "hi"); g = G.fill("c", "पंद्रह साल", "hi")
    assert g["done"] and g["route"] == "/learn" and g["params"]["target"] == "5000000.0" and g["params"]["years"] == "15"
    assert "50.00 लाख" in g["say"] or "50 लाख" in g["say"]


def test_sentences_with_everything_prefill_all_slots(ctx_factory):
    g = G.begin("fee", "what does a 2% fee cost on 5 lakh over 20 years", "en", "c")
    assert g["done"] and g["params"]["lump"] == "500000.0"
    g = G.begin("emergency", "how long will 3 lakh last if I spend 40000 a month", "en", "c")
    assert g["done"]


def test_vague_fee_question_asks_instead_of_guessing(ctx_factory):
    g = G.begin("fee", "what does the fund fee cost me", "en", "c")
    assert not g["done"] and g["ask"]["slot"] == "mode"


def test_forget_clears_one_conversation_only(ctx_factory):
    G.begin("loan", "my sahukar charges 5 rupees per hundred a month", "en", "a")
    G.begin("loan", "", "en", "b")
    G.LAST_SCHEMES["a"] = ["pm_kisan"]
    G.forget("a")
    assert not G.active("a") and "a" not in G.LAST_SCHEMES and G.active("b")


def test_upi_coach_asks_what_is_happening_then_names_the_trick():
    g = G.begin("upi", "", "en", "c")
    assert g["ask"]["slot"] == "text" and len(g["ask"]["choices"]) == 8
    g = G.fill("c", "A buyer sent a QR code to pay me", "en")
    assert g["done"] and "QR" in g["say"] and g["params"]["run"] == "1"
    done = G.begin("upi", "a buyer on olx sent a qr code to pay me, scan to receive", "en", "c")
    assert done["done"]
