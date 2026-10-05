import re

import pytest

from analysis import proscons
from backend.session import Session

SIGNAL_WORDS = re.compile(r"\b(buy|sell|hold|bullish|bearish|target price|will rise|will fall|outperform|underperform|upside|undervalued|overvalued)\b", re.I)


@pytest.fixture(scope="module")
def sess():
    return Session.create()


def text_of(r):
    return " ".join([r["about"], *[x["title"] + " " + x["why"] for x in r["pros"] + r["cons"]], *r["gaps"], *r["for_you"]])


def test_summary_has_both_lists_and_never_gives_a_signal(sess):
    for tk in ("TCS.NS", "HDFCBANK.NS", "RELIANCE.NS", "INFY.NS"):
        r = proscons.pros_cons(sess.pit, tk, "en", {"weight": 0.1, "sector_weight": 0.4, "sector_limit": 0.35})
        assert r["about"] and r["gaps"] and len(r["how_to_read"]) == 2
        assert not SIGNAL_WORDS.search(text_of(r)), (tk, SIGNAL_WORDS.search(text_of(r)).group(0))
        assert "not say buy, sell or hold" in " ".join(r["how_to_read"])


def test_every_line_is_measured_and_explained(sess):
    r = proscons.pros_cons(sess.pit, "TCS.NS", "en")
    assert r["pros"] and r["cons"]                                    # the sample data has both sides for TCS
    for x in r["pros"] + r["cons"]:
        assert x["title"] and len(x["why"]) > 40 and any(ch.isdigit() for ch in x["why"]) or "news" in x["title"].lower()


def test_rules_follow_the_numbers(sess):
    f = proscons.pros_cons(sess.pit, "TCS.NS", "en")["facts"]
    titles = [x["title"] for x in proscons.pros_cons(sess.pit, "TCS.NS", "en")["pros"]]
    if f["pe"] and f["pe_peers"] and f["pe"] < f["pe_peers"] * 0.9:
        assert "Priced lower than similar companies" in titles
    cons = [x["title"] for x in proscons.pros_cons(sess.pit, "TCS.NS", "en")["cons"]]
    if f["year_return"] is not None and f["year_return"] < -10:
        assert "The price has fallen over the past year" in cons
    if f["worst_fall"] is not None and f["worst_fall"] < -25:
        assert "It has had a big fall from its peak" in cons


def test_missing_data_is_listed_not_guessed(sess):
    r = proscons.pros_cons(sess.pit, "RELIANCE.NS", "en")             # no fundamentals saved for it
    assert any("no figure saved" in g for g in r["gaps"]) and not any("Priced" in x["title"] for x in r["pros"] + r["cons"])


def test_portfolio_context_and_hindi(sess):
    r = proscons.pros_cons(sess.pit, "TCS.NS", "en", {"weight": 0.139, "sector_weight": 0.398, "sector_limit": 0.35})
    assert "13.9%" in r["for_you"][0] and "35%" in r["for_you"][0] and any("past your own limit" in x or "further past" in x for x in r["for_you"])
    hi = proscons.pros_cons(sess.pit, "TCS.NS", "hi")
    assert re.search(r"[ऀ-ॿ]", hi["about"]) and re.search(r"[ऀ-ॿ]", hi["pros"][0]["title"])
    assert not proscons.pros_cons(sess.pit, "TCS.NS", "en")["for_you"]


def test_chart_readings_are_tagged_explained_and_capped_so_one_fact_is_not_counted_four_times(sess):
    for tk in ("TCS.NS", "HDFCBANK.NS", "RELIANCE.NS", "SBIN.NS", "ITC.NS"):
        r = proscons.pros_cons(sess.pit, tk, "en")
        for side in ("pros", "cons"):
            assert sum(1 for x in r[side] if x["tag"] == "Price and trend") <= 3
            assert all(x["tag"] in {"The business", "Price and trend", "Size", "News"} for x in r[side])
        assert not SIGNAL_WORDS.search(text_of(r))
    titles = " ".join(x["title"] for tk in ("TCS.NS", "SBIN.NS") for x in proscons.pros_cons(sess.pit, tk, "en")["pros"] + proscons.pros_cons(sess.pit, tk, "en")["cons"])
    assert "long-term averages" in titles or "similar companies" in titles
