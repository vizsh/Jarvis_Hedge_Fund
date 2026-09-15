"""Grammar-repair tests. No model load required -- these are pure string functions.

Whisper mangles tickers far more often than ordinary words, because they are not words.
Every case below is a real transcription observed while wiring this up, not a guess.
"""
from __future__ import annotations

import pytest

from backend.intents import parse_pattern
from voice.stt import snap_to_grammar


@pytest.mark.parametrize("heard,expect_text,expect_verb,expect_ticker", [
    # The homophone that matters most: "buy" and "by" are indistinguishable, and
    # getting it wrong means a trade command silently becomes nothing.
    ("By 30 shares of persistent.", "buy 30 shares of Persistent.", "propose", "PERSISTENT.NS"),
    ("Analyze TCS.", "analyse TCS.", "investigate", "TCS.NS"),
    ("a nice tics", "analyse TCS", "investigate", "TCS.NS"),
    ("and allies emphasis", "analyse Mphasis", "investigate", "MPHASIS.NS"),
    ("re wind to march 23rd 2020", "rewind to march 23 2020", "rewind", None),
    ("cell 100 wipro", "sell 100 Wipro", "propose", "WIPRO.NS"),
    ("execute it", "execute", "execute", None),
])
def test_repaired_transcripts_parse_to_the_right_intent(heard, expect_text, expect_verb,
                                                        expect_ticker):
    text, _ = snap_to_grammar(heard)
    assert text == expect_text
    intent = parse_pattern(text)
    assert intent is not None, f"{text!r} matched no pattern"
    assert intent.verb == expect_verb
    assert intent.ticker == expect_ticker


def test_multiword_repair_does_not_leave_a_duplicate():
    """"i see i see i bank" expanded to "ICICI Bank" and the spoken "bank" survived."""
    text, repaired = snap_to_grammar("analise i see i see i bank")
    assert repaired
    assert text.lower().count("bank") == 1
    assert parse_pattern(text).ticker == "ICICIBANK.NS"


def test_clean_transcript_is_left_alone():
    text, repaired = snap_to_grammar("rewind to 2020-03-23")
    assert text == "rewind to 2020-03-23"
    assert not repaired


def test_unknown_head_word_snaps_to_the_nearest_verb():
    """The long tail, without a dictionary entry per mishearing."""
    text, repaired = snap_to_grammar("analyse-ish TCS")
    assert repaired
    assert text.startswith("analyse")


def test_repair_never_invents_a_ticker_from_nothing():
    """A wrong ticker is worse than none: it would route a trade to the wrong stock."""
    text, _ = snap_to_grammar("show me the portfolio")
    assert parse_pattern(text).ticker is None


def test_shares_survive_repair():
    """Losing the quantity turns a sized order into a default one."""
    text, _ = snap_to_grammar("By 250 shares of wipro")
    intent = parse_pattern(text)
    assert intent.args["shares"] == 250
    assert intent.args["side"] == "BUY"
