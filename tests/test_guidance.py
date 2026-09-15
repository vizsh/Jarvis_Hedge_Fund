"""The guidance layer: actions, flows, palette, drill-down, watches, sandbox.

These are the pieces that turn a wall of panels into something that proposes. The
properties worth pinning are not "does it render" but the ones that make guidance
trustworthy:

  - an action that says "Fix this" must actually carry a flow that fixes it
  - the palette must find a capability from the words a worried person would type,
    not from the word the codebase happens to use
  - a drill-down's components must add up to the number it is explaining
  - the sandbox must never touch the live book, and must never launder a breach
"""
from __future__ import annotations

import pytest

from analysis import tax as tax_mod
from backend import actions as actions_mod
from backend import drilldown, explain, flows, palette, sandbox, watchlist
from backend.session import Session
from risk.portfolio import Portfolio


@pytest.fixture(scope="module")
def session() -> Session:
    s = Session.create()
    s.reprice()
    watchlist.ensure_schema(s.conn)
    return s


@pytest.fixture(scope="module")
def book(session) -> Portfolio:
    """A deliberately concentrated retail book, so there is something to advise on."""
    picks = {"TCS.NS": 63, "INFY.NS": 115, "HCLTECH.NS": 60, "WIPRO.NS": 242,
             "HDFCBANK.NS": 183, "ICICIBANK.NS": 79}
    held = {t: n for t, n in picks.items() if session.prices.get(t)}
    if len(held) < 4:
        pytest.skip("snapshot is missing the tickers this fixture needs")
    return Portfolio(cash=85_000.0, positions=held)


# ------------------------------------------------------------------- action queue
def test_queue_is_ranked_and_capped(session, book):
    q = actions_mod.build(session.pit, book, session.prices, session.policy, limit=4)
    assert q["actions"], "a concentrated book should produce something to do"
    assert len(q["actions"]) <= 4
    ranks = [a["rank"] for a in q["actions"]]
    assert ranks == sorted(ranks, reverse=True), "queue is not ranked"


def test_every_action_offers_a_way_to_act(session, book):
    """A row that says "Fix this" and does nothing is worse than no row."""
    q = actions_mod.build(session.pit, book, session.prices, session.policy)
    for a in q["actions"]:
        assert a["flow"] or a["question"], f"{a['id']} has no way to act on it"
        if a["flow"]:
            assert flows.get(a["flow"]), f"{a['id']} points at a flow that does not exist"


def test_every_action_explains_why_it_matters(session, book):
    q = actions_mod.build(session.pit, book, session.prices, session.policy)
    for a in q["actions"]:
        assert len(a["why"]) > 40, f"{a['id']} has no teaching line"
        assert a["title"] and a["detail"]


def test_a_deadline_outranks_a_standing_breach():
    """The ranking property that is easy to get wrong: a door that is closing beats a
    problem that will still be there next week, at equal severity and stake."""
    standing = actions_mod.Action(id="a", severity="opportunity", title="t",
                                  detail="d", why="w", stake=50_000)
    expiring = actions_mod.Action(id="b", severity="opportunity", title="t",
                                  detail="d", why="w", stake=50_000,
                                  deadline_days=5)
    assert expiring.score() > standing.score()


def test_stake_is_damped_not_linear():
    """Without damping one large breach drowns out every other row on the list."""
    small = actions_mod.Action(id="a", severity="important", title="t", detail="d",
                               why="w", stake=10_000)
    huge = actions_mod.Action(id="b", severity="important", title="t", detail="d",
                              why="w", stake=1_000_000)
    assert huge.score() > small.score()
    assert huge.score() < small.score() * 10, "stake is dominating the ranking"


def test_an_empty_portfolio_is_told_what_to_do_first(session):
    q = actions_mod.build(session.pit, Portfolio(cash=0.0, positions={}),
                          session.prices, session.policy)
    assert q["actions"][0]["flow"] == "onboarding"


def test_informational_findings_do_not_promise_a_fix(session, book):
    """"This basket fell 26% once" is a fact, not a breach. Offering "Fix this" next to
    it promises something the product cannot deliver."""
    q = actions_mod.build(session.pit, book, session.prices, session.policy, limit=20)
    for a in q["actions"]:
        if a["data"].get("code") in actions_mod.INFORMATIONAL:
            assert a["cta"] != "Fix this"
            assert a["flow"] == actions_mod.INFORMATIONAL[a["data"]["code"]]


# -------------------------------------------------------------------------- flows
def test_every_flow_is_well_formed():
    assert flows.FLOWS
    for flow in flows.FLOWS.values():
        assert flow.steps, f"{flow.id} has no steps"
        assert flow.steps[-1].kind == "done", f"{flow.id} does not end in a closing beat"
        for step in flow.steps:
            assert step.kind in {"say", "show", "choose", "ask", "confirm", "done"}
            assert step.text, f"{flow.id} has a silent step"
            if step.kind == "ask":
                assert step.question
            if step.kind == "choose":
                assert len(step.options) >= 2
                for opt in step.options:
                    assert opt["label"] and opt["consequence"]


def test_a_choice_always_includes_its_consequence():
    """A choice without a stated cost is not a choice, it is a nudge."""
    for flow in flows.FLOWS.values():
        for step in flow.steps:
            for opt in step.options:
                assert len(opt["consequence"]) > 25, f"{flow.id}/{opt['key']}"


def test_flow_questions_are_answerable(session, book):
    """Every scripted question must produce a real answer, not a generic fallback.

    This is the trap the follow-up chips fell into: suggesting a question the explainer
    had no handler for, so a confident-looking chip returned an unrelated summary.
    """
    for flow in flows.FLOWS.values():
        for step in flow.steps:
            if step.kind != "ask" or not step.question:
                continue
            a = explain.answer(step.question, session.pit, book, session.prices,
                               session.policy)
            assert a.headline, f"{flow.id}: {step.question!r} produced nothing"


# ------------------------------------------------------------------------ palette
@pytest.mark.parametrize("typed,expect", [
    ("too much in one place", "q.div"),
    ("eggs in one basket", "q.div"),
    ("what do i do", "q.sell"),
    ("tell me if", "p.watchlist"),
    ("crash", "q.crash"),
    ("print", "c.report"),
    ("shut up", "c.mute"),
    ("capital gains", "p.tax"),
    ("were you right", "p.calibration"),
])
def test_palette_finds_capability_from_natural_words(typed, expect):
    """Indexed by what a person would type, not by what the feature is called."""
    ids = [r["id"] for r in palette.search(typed, limit=5)]
    assert expect in ids, f"{typed!r} -> {ids}"


def test_palette_has_a_useful_default_list():
    rows = palette.search("", limit=8)
    assert rows and rows[0]["id"] == "p.actions"


def test_every_palette_flow_entry_resolves():
    for row in palette.catalogue():
        if row.kind == "flow":
            assert flows.get(row.payload), f"{row.id} points at a missing flow"


# --------------------------------------------------------------------- drill-down
def test_sector_components_sum_to_the_number(session, book):
    d = drilldown.explain_metric("sector", session.pit, book, session.prices,
                                 session.policy)
    total = sum(c["value"] for c in d["components"])
    nav = book.nav(session.prices)
    assert abs(total / nav - d["value"]) < 1e-6, "components do not add up to the metric"


def test_score_penalties_reconcile_to_the_score(session, book):
    """The published-formula claim has to survive arithmetic."""
    d = drilldown.explain_metric("score", session.pit, book, session.prices,
                                 session.policy)
    penalties = sum(c["value"] for c in d["components"])
    assert abs((100 + penalties) - d["value"]) <= 1.0


def test_every_drilldown_carries_provenance(session, book):
    for metric in ("nav", "sector", "position", "effective_holdings", "score",
                   "beta", "max_drawdown", "cash"):
        d = drilldown.explain_metric(metric, session.pit, book, session.prices,
                                     session.policy)
        assert "error" not in d, f"{metric} has no drill-down"
        assert d["formula"] and d["why"]
        assert d["provenance"]["clock"] == session.pit.clock_iso


def test_unknown_metric_says_what_is_available(session, book):
    d = drilldown.explain_metric("nonsense", session.pit, book, session.prices,
                                 session.policy)
    assert "error" in d and d["available"]


# ---------------------------------------------------------------------- watchlist
def test_a_rule_reads_back_as_english():
    line = watchlist.sentence("sector_weight", "above", 0.4, "IT")
    assert line.startswith("Tell me if") and "40%" in line


def test_rules_evaluate_and_detect_transitions(session, book):
    conn = session.conn
    conn.execute("DELETE FROM watches")
    conn.commit()
    watchlist.add(conn, None, "sector_weight", "above", 0.10, "IT")
    watchlist.add(conn, None, "score", "below", 1, None)

    first = watchlist.evaluate(conn, session.pit, book, session.prices, session.policy)
    states = {w["label"]: w["state"] for w in first["watches"]}
    assert "breached" in states.values(), "a 10% IT cap should be breached here"
    assert len(first["changed"]) >= 1, "first evaluation should report the transition"

    # Re-running with nothing changed must stay quiet: re-announcing the same breach
    # on every tick is how people learn to ignore the channel.
    second = watchlist.evaluate(conn, session.pit, book, session.prices, session.policy)
    assert second["changed"] == []
    conn.execute("DELETE FROM watches")
    conn.commit()


def test_unknown_metric_is_refused(session):
    with pytest.raises(ValueError):
        watchlist.add(session.conn, None, "price_of_tcs", "above", 4000, None)


# ------------------------------------------------------------------------ sandbox
def test_staging_never_touches_the_live_book(session, book):
    before_cash = book.cash
    before_pos = dict(book.positions)
    staged = sandbox.Staged(trades=[{"ticker": "TCS.NS", "side": "SELL", "shares": 10}])
    sandbox.preview(session.pit, book, session.prices, session.policy, staged,
                    with_stress=False)
    assert book.cash == before_cash and book.positions == before_pos


def test_preview_reports_before_and_after(session, book):
    staged = sandbox.Staged(trades=[{"ticker": "TCS.NS", "side": "SELL", "shares": 20}])
    out = sandbox.preview(session.pit, book, session.prices, session.policy, staged,
                          with_stress=False)
    assert out["staged"] and out["before"] and out["after"]
    assert out["verdict"]
    assert out["after"]["nav"] < out["before"]["nav"], "trading should cost something"


def test_a_sell_you_cannot_cover_is_skipped_not_applied(session, book):
    staged = sandbox.Staged(trades=[{"ticker": "TCS.NS", "side": "SELL",
                                     "shares": 99_999}])
    out = sandbox.preview(session.pit, book, session.prices, session.policy, staged,
                          with_stress=False)
    assert out["skipped"], "an uncovered sell must be reported, not silently dropped"
    assert out["after"]["holdings"] == out["before"]["holdings"]


def test_deltas_only_list_what_changed(session, book):
    staged = sandbox.Staged(trades=[{"ticker": "TCS.NS", "side": "SELL", "shares": 15}])
    out = sandbox.preview(session.pit, book, session.prices, session.policy, staged,
                          with_stress=False)
    for d in out["deltas"]:
        assert d["before"] != d["after"], f"{d['key']} is listed but did not change"


# --------------------------------------------------------- conversation + answers
def test_pronouns_resolve_to_the_last_subject(session, book):
    convo = explain.Conversation()
    first = explain.answer("should I buy more Infosys", session.pit, book,
                           session.prices, session.policy, convo=convo)
    assert first.subject == "INFY.NS"
    second = explain.answer("what does it move with", session.pit, book,
                            session.prices, session.policy, convo=convo)
    assert second.kind == "correlation"
    assert second.subject == "INFY.NS", "the pronoun did not resolve"


def test_a_named_company_is_never_hijacked_by_memory(session, book):
    convo = explain.Conversation()
    explain.answer("should I buy more Infosys", session.pit, book, session.prices,
                   session.policy, convo=convo)
    out = explain.answer("what does TCS move with", session.pit, book, session.prices,
                         session.policy, convo=convo)
    assert out.subject == "TCS.NS", "memory overrode an explicitly named company"


def test_every_answer_offers_somewhere_to_go_next(session, book):
    for q in ("how am I doing", "why is my risk high", "what should I sell",
              "am I diversified", "what if the market drops 20%"):
        a = explain.answer(q, session.pit, book, session.prices, session.policy)
        assert a.follow_ups, f"{q!r} is a dead end"
        assert len(a.follow_ups) <= 3


def test_follow_ups_are_themselves_answerable(session, book):
    """The chips must not suggest questions the explainer cannot handle."""
    seen: set[str] = set()
    for q in ("how am I doing", "why is my risk high", "should I buy more TCS"):
        for chip in explain.answer(q, session.pit, book, session.prices,
                                   session.policy).follow_ups:
            seen.add(chip)
    for chip in seen:
        a = explain.answer(chip, session.pit, book, session.prices, session.policy)
        assert a.headline, f"suggested {chip!r} but cannot answer it"


def test_the_three_levels_differ(session, book):
    normal = explain.answer("how am I doing", session.pit, book, session.prices,
                            session.policy)
    simple = explain.answer("how am I doing", session.pit, book, session.prices,
                            session.policy, level="simple")
    maths = explain.answer("how am I doing", session.pit, book, session.prices,
                           session.policy, level="maths")
    assert len(simple.bullets) < len(normal.bullets) <= len(maths.bullets)
    assert simple.level == "simple" and maths.level == "maths"
    # Simplifying must not lose the number -- vaguer is not simpler.
    assert any(ch.isdigit() for ch in simple.headline)
