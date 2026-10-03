from backend import assistant as A
from backend import explain, portfolios
from backend.router import route
from backend.session import Session


def _ctx():
    s = Session.create(); s.reprice()
    d = portfolios.load(s.conn, "preset_typical_retail")
    s.set_portfolio(d["name"], d["cash"], d["positions"], "preset_typical_retail")
    return A.Ctx(s.pit, s.portfolio, s.prices, s.policy, s.conn, explain.Conversation(), "en")


def test_question_forms_are_questions_not_orders():
    for q in ["tell me if i can buy the hdfc stock based on its fundamentals",
              "can I buy HDFC Bank", "let me know whether to buy TCS", "is Infosys ok to buy"]:
        assert route(q).kind == "question", q


def test_buy_advice_is_plain_and_complete():
    a = A.answer("tell me if i can buy the hdfc stock based on its fundamentals and my portfolio diversification", _ctx())
    assert a.data["intent"] == "should_buy"
    text = " ".join([a.headline, *a.bullets, a.action or ""])
    assert "choice is yours" in text and "POSITION_LIMIT" not in text and "NAV" not in text
    assert {f["label"] for f in a.facts} >= {"Company numbers", "Fit with you", "Room to add"}


def test_over_limit_sector_is_a_clear_no():
    a = A.answer("should I buy TCS", _ctx())          # Technology already above its sector limit
    assert a.data["fit"] == "bad" and a.headline.startswith("Not now")
