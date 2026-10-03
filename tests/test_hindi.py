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


def test_page_sentences_have_exact_hindi_with_every_number():
    cases = ["It uses 3 scam-style tactics: promises guaranteed returns, promises a huge multiple.",
             "Wait 12 more days to cross 12 months and save ₹1,267.",
             "IT exposure would rise to 52.1%, above the 35.0% sector cap.",
             "Reduce from 30 to 12 shares - SECTOR_LIMIT binds, leaving IT at 35.0% and cash at 7.2%.",
             "Price is +4.2% over the last 3 months (close 3,901.20 on 2026-09-12).",
             "A uniform 20% fall applied to everything you hold. A what-if, not a forecast.",
             "Our data shows net income moved +12.3% from the previous period; the tip says +80%.",
             "Cash would fall to 3.2%, below the 5.0% minimum reserve."]
    for en in cases:
        hi = H.exact(en)
        assert hi and V.looks_hindi(hi), en
        assert V.numbers_preserved(en, hi), (en, hi)


def test_every_scanner_and_stress_fixed_sentence_is_translated():
    from analysis import scanner, stress
    fixed = [x for f in scanner.FLAGS for x in (f[1], f[4])]
    fixed += [s["blurb"] for s in stress.HISTORICAL] + [s["label"] for s in (*stress.HISTORICAL, *stress.HYPOTHETICAL)]
    for en in fixed:
        assert H.exact(en), en


def test_every_drilldown_sentence_has_exact_hindi(session):
    from backend import drilldown
    metrics = ["nav", "sector", "position", "effective_holdings", "score", "beta", "max_drawdown", "cash"]
    from core import universe
    names = {universe.name(t) for t in universe.tickers()}          # company names are proper nouns
    missing = []
    for m in metrics:
        d = drilldown.explain_metric(m, session.pit, session.portfolio, session.prices, session.policy)
        texts = [d["title"], d["formula"], d["why"], d["provenance"]["rule"]]
        for c in d.get("components", []):
            texts += [c["label"], c.get("sub") or ""]
        for t in texts:
            if t and t not in names and not (H.exact_whole(t) or H.exact(t)):
                missing.append((m, t))
    assert not missing, missing[:5]


def test_company_names_are_not_transliterated_by_the_translate_endpoint():
    import asyncio
    from backend import app as app_mod
    out = asyncio.run(app_mod.translate_lines(app_mod.TranslateIn(lines=["TCS", "Infosys", "Total value"])))
    assert out["hindi"][:2] == ["TCS", "Infosys"] and V.looks_hindi(out["hindi"][2])
