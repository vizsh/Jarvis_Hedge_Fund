"""Routing tests: question vs command.

This is the highest-stakes classifier in the product. Before it existed, the command bar
ran an imperative parser over everything the user typed, so:

    "what should I sell"            tried to PLACE A TRADE
    "what if the market drops 20%"  changed the risk policy
    "should I buy more TCS"         proposed an order

Voice used the same parser, which is why a perfectly transcribed sentence still did the
wrong thing -- the microphone was never the problem.

The asymmetry these tests encode: mistaking a question for a trade is far worse than
mistaking a trade for a question. One of them moves money. So an imperative has to
prove itself with an object, and everything else falls to the explainer, which cannot
do anything destructive.
"""
from __future__ import annotations

import pytest

from backend.router import route


def kind(text: str) -> str:
    return route(text).kind


def verb(text: str) -> str | None:
    r = route(text)
    return r.intent.verb if r.intent else None


# --- questions must never act -------------------------------------------------------
@pytest.mark.parametrize("text", [
    "how am I doing",
    "why is my risk high",
    "what should I sell",
    "what if the market drops 20%",
    "am I diversified",
    "what happened in covid",
    "what does beta mean",
    "is my portfolio safe",
    "how much would I lose in a crash",
    "tell me about my portfolio",
    "what is my worst case",
])
def test_questions_are_answered_not_acted_on(text):
    assert kind(text) == "question", f"{text!r} would have triggered an action"


@pytest.mark.parametrize("text", [
    "should I buy more TCS",
    "shall I sell Infosys",
    "would you sell TCS",
    "can I buy 50 TCS",
    "is it worth buying HDFC Bank",
])
def test_advisory_phrasing_never_places_a_trade(text):
    """The worst available misroute: these have a trade verb AND a ticker, so the
    naive parser read them as orders. Asking for an opinion is not an instruction."""
    assert kind(text) == "question", f"{text!r} would have placed a trade"


def test_stress_question_does_not_rewrite_the_policy():
    """"What if the market drops 20%" is a stress question. It used to match the
    policy simulator and change a limit."""
    assert verb("what if the market drops 20%") != "simulate"
    assert kind("what if the market drops 20%") == "question"


# --- commands must still act --------------------------------------------------------
@pytest.mark.parametrize("text,expected", [
    ("analyse TCS", "investigate"),
    ("look at Infosys", "investigate"),
    ("analyse Sun Pharma", "investigate"),
    ("TCS", "investigate"),
    ("buy 30 shares of Persistent", "propose"),
    ("sell 100 TCS", "propose"),
    ("buy 20 Maruti Suzuki", "propose"),
    ("rewind to 2020-03-23", "rewind"),
    ("what if we relax the sector cap to 40%", "simulate"),
    ("execute", "execute"),
    ("accept the remedy", "accept"),
    ("reset", "reset"),
    ("show me the portfolio", "status"),
    ("rebalance my portfolio", "rebalance"),
])
def test_imperatives_still_act(text, expected):
    assert kind(text) == "command", f"{text!r} stopped being a command"
    assert verb(text) == expected


def test_a_verb_without_an_object_is_a_question():
    """"analyse" alone is someone thinking aloud, not an instruction."""
    assert kind("analyse") == "question"
    assert kind("tell me about my portfolio") == "question"


def test_trade_verb_without_a_target_is_a_question():
    assert kind("I want to sell something") == "question"
    assert kind("thinking about buying") == "question"


def test_routing_reason_is_recorded():
    """Every decision carries why it was made, so a misroute is debuggable rather
    than mysterious."""
    for text in ("analyse TCS", "how am I doing", "should I buy TCS"):
        assert route(text).why


# --- ticker resolution across the FULL universe -------------------------------------
@pytest.mark.parametrize("text,expected", [
    ("analyse Nestle India", "NESTLEIND.NS"),
    ("analyse Sun Pharma", "SUNPHARMA.NS"),
    ("analyse Maruti Suzuki", "MARUTI.NS"),
    ("analyse Reliance Industries", "RELIANCE.NS"),
    ("analyse ONGC", "ONGC.NS"),
])
def test_names_outside_the_alias_table_resolve(text, expected):
    """The alias table covered about twenty names; the universe has fifty-six. Every
    question about the other thirty-six used to resolve to nothing."""
    assert route(text).intent.ticker == expected
