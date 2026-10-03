"""Hindi explainer: numbers are the contract. A fluent sentence with a wrong figure is the
failure that matters, because the reader cannot easily spot it."""
from __future__ import annotations

import asyncio
import re

import pytest

from backend import explain, portfolios
from backend import hindi_rules as H
from backend import vernacular as V
from backend.session import Session


@pytest.fixture(scope="module")
def session() -> Session:
    s = Session.create()
    s.reprice()
    d = portfolios.load(s.conn, "preset_typical_retail")
    if not d:
        pytest.skip("example portfolio not seeded")
    s.set_portfolio(d["name"], d["cash"], d["positions"], "preset_typical_retail")
    return s


QUESTIONS = ["how am I doing", "why is my risk high", "what should I sell", "am I diversified",
             "what if the market drops 20%", "what happened in covid", "should I buy more TCS",
             "should I buy Nestle India", "what is my worst case", "what if technology falls 30%"]


def _sentences(session):
    conv = explain.Conversation()
    for q in QUESTIONS:
        a = explain.answer(q, session.pit, session.portfolio, session.prices, session.policy, convo=conv)
        for t in [a.headline, *a.bullets, a.action, *a.follow_ups]:
            for sent in re.split(r"(?<=[.!?])\s+", t or ""):
                if sent:
                    yield sent


def test_a_swapped_fraction_is_rejected():
    """The first model trial turned "94 out of 100" into "94 में से 100"."""
    assert not V.numbers_preserved("I score it 94 out of 100.", "मैं इसे 94 में से 100 अंक देता हूँ।")
    assert V.numbers_preserved("I score it 94 out of 100.", "मैं इसे 100 में से 94 अंक देता हूँ।")


def test_a_dropped_or_changed_number_is_rejected():
    assert not V.numbers_preserved("You would lose about ₹1.83 lakh.", "आपको नुकसान होगा।")
    assert not V.numbers_preserved("It fell 26%.", "यह 62% गिरा।")


def test_exact_rules_cover_almost_everything_the_explainer_says(session):
    sents = list(_sentences(session))
    hits = sum(1 for s in sents if H.exact(s) is not None)
    assert hits / len(sents) >= 0.95, f"only {hits}/{len(sents)} sentences have exact Hindi"


def test_every_exact_translation_keeps_its_numbers(session):
    for s in _sentences(session):
        hi = H.exact(s)
        if hi:
            assert V.numbers_preserved(s, hi), f"{s!r} -> {hi!r}"
            assert V.looks_hindi(hi), hi


def test_localized_answer_keeps_followups_askable_in_english(session):
    a = explain.answer("why is my risk high", session.pit, session.portfolio, session.prices,
                       session.policy)
    out = asyncio.run(V.localize_answer(a, "hi"))["answer"]
    assert out["lang"] == "hi" and V.looks_hindi(out["headline"])
    assert out["follow_ups"] == a.follow_ups, "chips must still send English questions"
    assert len(out["follow_ups_hi"]) == len(a.follow_ups) and all(V.looks_hindi(c) for c in out["follow_ups_hi"])


def test_spoken_line_is_cut_from_the_shown_hindi(session):
    a = explain.answer("what should I sell", session.pit, session.portfolio, session.prices,
                       session.policy)
    loc = asyncio.run(V.localize_answer(a, "hi"))
    assert loc["spoken"] and loc["spoken"].split("।")[0] in loc["full"]
    # whatever figures are spoken must be figures that are also on screen
    assert V.numbers_preserved(loc["spoken"], loc["full"])


def test_english_mode_is_untouched(session):
    a = explain.answer("how am I doing", session.pit, session.portfolio, session.prices, session.policy)
    loc = asyncio.run(V.localize_answer(a, "en"))
    assert loc["translated"] is False and loc["answer"]["headline"] == a.headline


def test_known_hindi_questions_map_back_to_english_without_the_model():
    for en in ("Why is my risk high?", "What should I sell?", "Am I diversified?"):
        hi = H.exact(en)
        assert asyncio.run(V.to_english(hi)) == en
