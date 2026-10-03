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
