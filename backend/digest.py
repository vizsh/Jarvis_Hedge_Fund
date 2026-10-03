"""Weekly digest: a spoken, roughly one-minute summary of the portfolio.

Deterministic. Every figure is computed here from stored prices and the x-ray; the Hindi and
English sentences are fixed templates with the numbers dropped in, so nothing is paraphrased
by a model and nothing can be mistranslated. About 140 words is the spoken minute.
"""
from __future__ import annotations

from typing import Any

from analysis import tools, xray
from backend.hindi_rules import SECTORS
from core import universe

TIPS = [
    ("No bank, police officer or government office will ever ask for your OTP, PIN or CVV on a call. If anyone does, hang up and call the number printed on your card.",
     "कोई बैंक, पुलिस अधिकारी या सरकारी दफ़्तर फ़ोन पर आपसे OTP, पिन या CVV कभी नहीं माँगता। कोई माँगे तो फ़ोन काटिए और कार्ड पर छपे नंबर पर ख़ुद फ़ोन कीजिए।"),
    ("A guaranteed return is the oldest scam line there is. Genuine investments always say your money can go down as well as up.",
     "पक्के मुनाफ़े का वादा सबसे पुरानी ठगी की बात है। असली निवेश हमेशा बताता है कि पैसा बढ़ भी सकता है और घट भी सकता है।"),
    ("There is no such thing as a digital arrest. Police and courts never arrest anyone over a phone or video call, and never ask you to move money to a safe account.",
     "डिजिटल अरेस्ट जैसी कोई चीज़ नहीं होती। पुलिस या अदालत फ़ोन या वीडियो कॉल पर गिरफ़्तार नहीं करती और सुरक्षित खाते में पैसे डालने को नहीं कहती।"),
    ("Two mutual funds with different names can hold almost the same shares. Check how much they overlap before you pay two fees for one portfolio.",
     "अलग नाम वाले दो म्यूचुअल फ़ंड लगभग एक ही शेयर रख सकते हैं। दो फ़ीस देने से पहले जाँच लीजिए कि वे कितने मिलते-जुलते हैं।"),
    ("Keep six months of expenses in an easy-to-reach account before you invest anything you cannot afford to see fall.",
     "जो पैसा गिरता देखना आपको भारी पड़े, उसे लगाने से पहले छह महीने का ख़र्च आसानी से मिलने वाले खाते में रखिए।"),
    ("A small yearly fee looks harmless but compounds against you. Two percent a year can eat over a third of your gains across twenty years.",
     "सालाना छोटी फ़ीस मामूली लगती है, पर वह आपके ख़िलाफ़ बढ़ती जाती है। बीस साल में दो प्रतिशत की फ़ीस आपके मुनाफ़े का एक तिहाई से ज़्यादा खा सकती है।"),
]


def _week(pit, portfolio, prices) -> dict[str, Any] | None:
    """Portfolio value now versus five trading days ago, and the best and worst holding."""
    now = then = portfolio.cash
    moves: list[tuple[str, float]] = []
    for t, sh in portfolio.positions.items():
        rows = pit.prices(t, 8)
        if len(rows) < 6:
            now += sh * prices.get(t, 0.0)
            then += sh * prices.get(t, 0.0)
            continue
        p0, p1 = rows[-6]["close"], rows[-1]["close"]
        now += sh * p1
        then += sh * p0
        moves.append((t, p1 / p0 - 1))
    if not moves or then <= 0:
        return None
    moves.sort(key=lambda kv: kv[1])
    return {"now": now, "then": then, "change": now - then, "ret": now / then - 1,
            "best": moves[-1], "worst": moves[0]}


def build(pit, portfolio, prices, policy, lang: str = "en", week_no: int | None = None) -> dict[str, Any]:
    hi = lang == "hi"
    if not portfolio.positions:
        t = "आपने अभी कोई शेयर नहीं जोड़ा है। जोड़ते ही मैं हर हफ़्ते का सार बता सकूँगा।" if hi else \
            "You have not added any holdings yet. Add them and I can give you a weekly summary."
        return {"lang": lang, "sections": [], "spoken": t, "headline": t, "words": len(t.split())}
    report = xray.analyse(pit, portfolio, prices, policy)
    wk = _week(pit, portfolio, prices)
    money = tools.inr_hi if hi else tools.inr
    sections: list[dict[str, str]] = []

    if wk:
        up = wk["change"] >= 0
        pct = abs(wk["ret"]) * 100
        sections.append({"title": "इस हफ़्ते" if hi else "This week", "text": (
            f"आपका पोर्टफ़ोलियो इस हफ़्ते {pct:.1f} प्रतिशत {'बढ़ा' if up else 'गिरा'}, यानी {money(abs(wk['change']))} का "
            f"{'फ़ायदा' if up else 'नुक़सान'}। अब कुल क़ीमत {money(wk['now'])} है।" if hi else
            f"Your portfolio {'rose' if up else 'fell'} {pct:.1f}% this week, a {'gain' if up else 'loss'} of "
            f"{money(abs(wk['change']))}. It is now worth {money(wk['now'])}.")})
        b, w = wk["best"], wk["worst"]
        sections.append({"title": "सबसे आगे और पीछे" if hi else "Best and worst", "text": (
            f"सबसे अच्छा रहा {universe.name(b[0])}, {b[1] * 100:+.1f} प्रतिशत। सबसे कमज़ोर रहा {universe.name(w[0])}, {w[1] * 100:+.1f} प्रतिशत।" if hi else
            f"{universe.name(b[0])} did best at {b[1] * 100:+.1f}%, and {universe.name(w[0])} did worst at {w[1] * 100:+.1f}%.")})
    else:
        nav = report.nav
        sections.append({"title": "इस हफ़्ते" if hi else "This week", "text": (
            f"आपके पोर्टफ़ोलियो की कुल क़ीमत {money(nav)} है। इस हफ़्ते की तुलना के लिए पूरे दाम का इतिहास अभी नहीं है।" if hi else
            f"Your portfolio is worth {money(report.nav)}. There is not enough price history yet for a weekly comparison.")})

    sec = report.top_sector
    sec_name = universe.sector_label(sec[0]) if sec else ""
    sec_hi = SECTORS.get(sec_name.lower(), sec_name) if sec else ""
    sections.append({"title": "जोखिम" if hi else "Risk", "text": (
        f"आपका जोखिम स्कोर सौ में से {report.score} है, ग्रेड {report.grade}। "
        + (f"आपका सबसे बड़ा हिस्सा {sec_hi} में है, कुल का {sec[1] * 100:.0f} प्रतिशत।" if sec else "") if hi else
        f"Your risk score is {report.score} out of 100, grade {report.grade}. "
        + (f"Your biggest slice is {sec_name}, at {sec[1] * 100:.0f}% of the total." if sec else "")).strip()})

    n = week_no if week_no is not None else 0
    tip_en, tip_hi = TIPS[n % len(TIPS)]
    sections.append({"title": "इस हफ़्ते की सुरक्षा सीख" if hi else "Safety tip of the week", "text": tip_hi if hi else tip_en})

    intro = "नमस्कार। यह आपका साप्ताहिक सार है।" if hi else "Hello. Here is your weekly summary."
    outro = "बस इतना ही। सवाल पूछना हो तो मुझसे पूछिए।" if hi else "That is all for this week. Ask me anything you want to go deeper on."
    spoken = " ".join([intro, *[s["text"] for s in sections], outro])
    return {"lang": lang, "sections": sections, "spoken": spoken, "words": len(spoken.split()),
            "headline": sections[0]["text"], "week": wk and {k: (round(v, 4) if isinstance(v, float) else v)
                                                              for k, v in wk.items() if k in ("now", "then", "change", "ret")}}
