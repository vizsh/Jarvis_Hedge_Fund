"""Scam recovery coach: complete in both languages, ordered sensibly, and it never invents a fact."""
from __future__ import annotations

import pytest

from backend import portfolios, recovery
from backend import vernacular as V
from backend.session import Session


def test_every_situation_has_a_complete_plan_in_both_languages():
    assert set(recovery.PLAN) == set(recovery.TYPES)
    for kind in recovery.TYPES:
        for lang in ("en", "hi"):
            plan = recovery.plan(kind, lang)
            assert len(plan["steps"]) >= 6 and plan["helpline"] == "1930"
            for s in plan["steps"]:
                assert s["title"] and s["detail"]
                if lang == "hi":
                    assert V.looks_hindi(s["title"]) and V.looks_hindi(s["detail"]), (kind, s["id"])
    for sid, s in recovery.STEPS.items():
        assert len(s["en"]) == 2 and len(s["hi"]) == 2, sid


def test_the_first_steps_are_the_urgent_ones():
    # cutting access / blocking the account comes before paperwork
    assert recovery.PLAN["remote_app"][0] == "remove_app"
    assert recovery.PLAN["upi_card"][0] == "block_bank"
    assert recovery.PLAN["invest"][0] == "stop_payments"
    for kind, ids in recovery.PLAN.items():
        mins = [recovery.STEPS[i]["mins"] for i in ids]
        assert mins[0] <= 30, kind                                    # the very first step is a do-it-now step
        assert ids.index("report_1930") < ids.index("monitor") if "report_1930" in ids else True


def test_drafts_use_only_what_the_person_gave_and_mark_the_gaps():
    d = recovery.drafts("upi_card", "en", 50000, "3 Oct 2026, 2:15 pm", "UTR123456", "98xxxxxx12", "State Bank", "A. Kumar")
    for key in ("script", "portal", "letter"):
        for fact in ("UTR123456", "98xxxxxx12", "3 Oct 2026, 2:15 pm"):
            assert fact in d[key], (key, fact)
    assert "₹50,000" in d["script"] and "State Bank" in d["letter"] and "A. Kumar" in d["letter"]
    blank = recovery.drafts("upi_card", "en")
    assert "[transaction ID / UTR]" in blank["script"] and "[amount]" in blank["portal"]
    assert "refund is guaranteed" not in blank["letter"].lower()          # never promises an outcome


def test_hindi_drafts_are_hindi_and_keep_the_figures():
    d = recovery.drafts("shared_code", "hi", 120000, "आज दोपहर", "UTR9", "9876543210", "HDFC", "रमेश")
    for key in ("script", "portal", "letter"):
        assert V.looks_hindi(d[key]) and "UTR9" in d[key] and "9876543210" in d[key]
    assert "1,20,000" in d["script"] or "1.20 लाख" in d["script"]


@pytest.mark.parametrize("text,kind", [
    ("I installed anydesk and they took money", "remote_app"),
    ("a man posing as police made me transfer 2 lakh", "digital_arrest"),
    ("I paid 50000 into a trading app for guaranteed returns", "invest"),
    ("I shared my otp and money was debited", "shared_code"),
    ("I clicked a link and filled my details", "link_clicked"),
    ("50000 was debited from my account by a fraud", "upi_card"),
])
def test_the_situation_is_read_from_a_sentence(text, kind):
    assert recovery.guess_type(text) == kind


@pytest.fixture(scope="module")
def session():
    s = Session.create()
    s.reprice()
    d = portfolios.load(s.conn, "preset_typical_retail")
    s.set_portfolio(d["name"], d["cash"], d["positions"], "preset_typical_retail")
    return s


def test_the_chatbot_gives_the_ordered_plan_after_a_scam(session):
    from backend import assistant as A
    from backend import explain
    ctx = A.Ctx(session.pit, session.portfolio, session.prices, session.policy, session.conn, explain.Conversation(), "en")
    a = A.answer("I lost 50000 rupees on UPI to a fake bank officer", ctx)
    assert a.kind == "scam_recovery" and a.data["recovery_type"] in recovery.TYPES
    text = " ".join([a.headline, *a.bullets, a.action or ""])
    assert "1930" in text and "cybercrime.gov.in" in text
    assert a.visual["page"] == "protect" and a.visual["params"]["amount"] == 50000
    assert len(a.table["rows"]) == len(recovery.plan(a.data["recovery_type"])["steps"])
    hi = A.answer("I lost 50000 rupees on UPI to a fake bank officer", A.Ctx(session.pit, session.portfolio, session.prices,
                  session.policy, session.conn, explain.Conversation(), "hi"))
    assert hi.lang == "hi" and V.looks_hindi(hi.headline)
