"""Hindi input: figures read in code, intent chosen from a closed list, no free translation."""
from __future__ import annotations

import asyncio

import pytest

from backend import assistant as A
from backend import hindi_input as H
from backend import portfolios
from backend import vernacular as V
from backend.session import Session
from tests import hindi_eval as E


def conv(text, **kw):
    return asyncio.run(H.convert(text, use_model=False, **kw))


@pytest.mark.parametrize("text,want", [
    ("तीन लाख", 300000), ("चालीस हज़ार", 40000), ("डेढ़ करोड़", 15000000), ("सवा लाख", 125000), ("साढ़े तीन लाख", 350000),
    ("पचास", 50), ("दो सौ बीस", 220), ("एक करोड़ बीस लाख", 12000000), ("५०,००० रुपये", 50000), ("50,000 रुपये", 50000),
    ("पच्चीस लाख", 2500000), ("निन्यानवे", 99), ("पंद्रह", 15), ("पन्द्रह", 15), ("5 लाख", 500000),
])
def test_spoken_and_written_hindi_numbers_are_read_exactly(text, want):
    q = H.quantities(text)
    assert q and q[0]["v"] == want, (text, q)


def test_units_are_told_apart():
    q = H.quantities("दो प्रतिशत फीस बीस साल छह महीने पांच लाख रुपये")
    assert [(x["v"], x["kind"]) for x in q] == [(2, "pct"), (20, "years"), (6, "months"), (500000, "money")]
    m = H.quantities("दस हज़ार रुपये महीने की एसआईपी")
    assert m[0]["monthly"] and m[0]["v"] == 10000


def _intent(q):
    if q is None:
        return "clarify"
    return "analyse" if q.lower().startswith("analyse") else "more" if q == "Tell me more" else A.detect(q)[0]


def _score(data):
    right = wrong = asked = 0
    for text, want, figs in data:
        q, _ = conv(text)
        got = _intent(q)
        if got == want and all(f in (q or "") for f in figs):
            right += 1
        elif got == "clarify":
            asked += 1
        else:
            wrong += 1
    return right, wrong, asked


@pytest.mark.parametrize("name,data,floor", [("tune", E.HI_TUNE, 0.97), ("blind", E.HI_BLIND, 0.95), ("blind2", E.HI_BLIND2, 0.95), ("heard", E.HI_HEARD, 1.0)])
def test_hindi_routing_accuracy_with_no_confident_wrong_answer(name, data, floor):
    right, wrong, asked = _score(data)
    assert wrong == 0, (name, right, wrong, asked)
    assert right / len(data) >= floor, (name, right, len(data))


def test_nothing_is_invented_the_english_has_only_fixed_words_and_names_that_were_said():
    # the old free translation turned these into fund and company names nobody said
    for text in ("मेरा पोर्टफोलियो कैसा चल रहा है", "किसी ने फोन पर मेरा ओटीपी माँगा", "दो प्रतिशत फीस बीस साल में कितनी पड़ती है"):
        q, _ = conv(text)
        for banned in ("ICICI", "Prudential", "Airtel", "Fidelity", "Equity Fund"):
            assert banned not in q, (text, q)


def test_unknown_hindi_is_passed_through_so_the_assistant_asks_in_hindi():
    q, how = conv("आज मौसम कैसा रहेगा")
    assert q is None and how == "none"


def test_model_fallback_only_picks_from_the_closed_list_and_needs_confidence(monkeypatch):
    async def fake(text):
        return "xray", 0.9
    monkeypatch.setattr(A, "llm_intent", fake)
    assert asyncio.run(H.convert("मेरी जमा पूंजी का अंदाज़ा दीजिए")) == ("How am I doing?", "model")

    async def unsure(text):
        return "xray", 0.4
    monkeypatch.setattr(A, "llm_intent", unsure)
    assert asyncio.run(H.convert("मेरी जमा पूंजी का अंदाज़ा दीजिए"))[0] is None

    async def silly(text):
        return "out_of_scope", 0.99
    monkeypatch.setattr(A, "llm_intent", silly)
    assert asyncio.run(H.convert("आज मौसम कैसा रहेगा"))[0] is None


@pytest.fixture(scope="module")
def session():
    s = Session.create()
    s.reprice()
    d = portfolios.load(s.conn, "preset_typical_retail")
    s.set_portfolio(d["name"], d["cash"], d["positions"], "preset_typical_retail")
    return s


def test_end_to_end_typed_hindi_gets_a_hindi_answer_with_the_right_figures(session, monkeypatch):
    from backend import app as app_mod
    monkeypatch.setattr(app_mod, "session", session)
    out = asyncio.run(app_mod.ask(app_mod.AskIn(question="दो प्रतिशत फीस बीस साल में कितनी पड़ती है", lang="hi")))
    assert out["kind"] == "fee_drag" and out["lang"] == "hi" and V.looks_hindi(out["headline"])
    assert "2.58" in out["headline"]                           # the same figure as the English answer
    out2 = asyncio.run(app_mod.ask(app_mod.AskIn(question="तीन लाख रुपये हैं और चालीस हज़ार महीने का खर्च है कितने महीने चलेंगे", lang="hi")))
    assert out2["kind"] == "emergency" and "7.5" in out2["headline"]
    gibberish = asyncio.run(app_mod.ask(app_mod.AskIn(question="आज मौसम कैसा रहेगा", lang="hi")))
    assert gibberish["kind"] in ("clarify", "out_of_scope") and V.looks_hindi(gibberish["headline"])
