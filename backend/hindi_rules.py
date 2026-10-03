"""Exact Hindi for the sentences the explainer actually says.

The explainer is templated, so most of what it says is a known sentence with numbers
dropped in. Those are translated by hand here: instant, and the numbers are placed by code,
so they cannot come out wrong. The language model is only asked about sentences that match
nothing in this table (see vernacular.py).
"""
from __future__ import annotations

import re

SECTORS = {
    "technology": "टेक्नोलॉजी", "banks & finance": "बैंक और वित्त", "oil & energy": "तेल और ऊर्जा",
    "consumer goods": "उपभोक्ता सामान", "metals & materials": "धातु और सामग्री",
    "automobiles": "ऑटोमोबाइल", "pharma & healthcare": "फार्मा और स्वास्थ्य",
    "infrastructure": "इंफ्रास्ट्रक्चर", "power & utilities": "बिजली और यूटिलिटी",
    "telecom": "टेलीकॉम", "consumer discretionary": "ऐच्छिक उपभोक्ता सामान",
    "single-stock": "एक शेयर", "sector": "उद्योग", "position": "एक शेयर",
}
WINDOWS = {
    "covid crash": "कोविड क्रैश", "covid recovery": "कोविड के बाद की रिकवरी",
    "2022 rate shock": "2022 का ब्याज दर झटका", "jan 2023 selloff": "जनवरी 2023 की बिकवाली",
}
KINDS = {"retail investor": "आम निवेशक", "serious private investor": "गंभीर निजी निवेशक",
         "boutique fund": "बुटीक फंड"}
UNIT = {"lakh": "लाख", "crore": "करोड़"}


def _s(x: str) -> str:
    x = x.strip().strip(".").lower()
    return SECTORS.get(x, x)


def _list(x: str) -> str:
    parts = re.split(r",\s*", x)
    return ", ".join(_s(p) for p in parts if p.strip())


def _m(amount: str, unit: str | None) -> str:
    return f"₹{amount} {UNIT[unit]}" if unit else f"₹{amount}"


def _mp(n: str, u: str) -> str:
    return rf"₹(?P<{n}>[\d,\.]+)(?: (?P<{u}>lakh|crore))?"


R = re.compile
FALLS = lambda m: ("बाज़ार" if m[1].lower() == "the market" else _s(m[1]))   # noqa: E731

RULES = [
    (R(r"^Your portfolio looks well spread out\.$"), lambda m: "आपका पोर्टफोलियो अच्छी तरह फैला हुआ है।"),
    (R(r"^Your portfolio is in reasonable shape, with one or two things to watch\.$"),
     lambda m: "आपका पोर्टफोलियो ठीक-ठाक है, बस एक-दो बातों पर नज़र रखनी है।"),
    (R(r"^Your portfolio is more concentrated than is comfortable\.$"),
     lambda m: "आपका पैसा ज़रूरत से ज़्यादा एक जगह जमा है।"),
    (R(r"^Your portfolio is heavily concentrated and would be hit hard by one bad sector\.$"),
     lambda m: "आपका पैसा बहुत ज़्यादा एक जगह जमा है, एक बुरे उद्योग से भारी चोट लग सकती है।"),
    (R(r"^I score it (\d+) out of (\d+) against (.+?) limits — no more than (\d+)% in one stock, (\d+)% in one industry, and at least (\d+)% kept in cash\.$"),
     lambda m: f"मैं इसे {m[2]} में से {m[1]} अंक देता हूँ ({KINDS.get(m[3].lower(), m[3])} की सीमाओं के हिसाब से) — एक शेयर में {m[4]}% से ज़्यादा नहीं, एक उद्योग में {m[5]}% से ज़्यादा नहीं, और कम से कम {m[6]}% नकद रखना।"),
    (R(r"^I score it (\d+) out of (\d+) against (.+?) limits\.$"),
     lambda m: f"मैं इसे {m[2]} में से {m[1]} अंक देता हूँ ({KINDS.get(m[3].lower(), m[3])} की सीमाओं के हिसाब से)।"),
    (R(r"^You hold " + _mp("x", "u") + r" across (\d+) stocks in (\d+) industries\.$"),
     lambda m: f"आपके पास {m[4]} उद्योगों के {m[3]} शेयरों में {_m(m['x'], m['u'])} हैं।"),
    (R(r"^Your biggest industry is (.+?) at (\d+)% of your money\.$"),
     lambda m: f"आपका सबसे बड़ा उद्योग {_s(m[1])} है, आपके पैसे का {m[2]}%।"),
    (R(r"^This mix has fallen (\d+)% from a high point before, on the history we hold\.$"),
     lambda m: f"हमारे पास मौजूद इतिहास में यह पोर्टफोलियो पहले एक ऊँचाई से {m[1]}% गिर चुका है।"),
    (R(r"^(One|Two|Three|\d+) things? stands? out\.$"),
     lambda m: {"One": "एक बात ध्यान देने लायक है।", "Two": "दो बातें ध्यान देने लायक हैं।",
                "Three": "तीन बातें ध्यान देने लायक हैं।"}.get(m[1], f"{m[1]} बातें ध्यान देने लायक हैं।")),
    (R(r"^None of it is severe, but it is worth knowing\.$"),
     lambda m: "इनमें से कुछ भी गंभीर नहीं है, लेकिन इसे जानना ज़रूरी है।"),
    (R(r"^The first one is the serious one\.$"), lambda m: "पहली बात गंभीर है।"),
    (R(r"^(.+?) is (\d+)% of your money\.$"), lambda m: f"{_s(m[1])} आपके पैसे का {m[2]}% है।"),
    (R(r"^Above the (\d+)% (sector|single-stock|position) limit\.$"),
     lambda m: f"यह {m[1]}% की {_s(m[2])} वाली सीमा से ऊपर है।"),
    (R(r"^Companies in the same sector tend to fall together, so this is less spread out than the number of stocks suggests\.$"),
     lambda m: "एक ही उद्योग की कंपनियाँ अक्सर साथ-साथ गिरती हैं, इसलिए आपका पैसा शेयरों की गिनती से कम बँटा हुआ है।"),
    (R(r"^This basket has fallen (\d+)% from a peak before\.$"),
     lambda m: f"यह पोर्टफोलियो पहले एक ऊँचाई से {m[1]}% गिर चुका है।"),
    (R(r"^Measured on the history we hold, with your current share counts\.$"),
     lambda m: "यह हमारे पास मौजूद इतिहास और आपके मौजूदा शेयरों के हिसाब से नापा गया है।"),
    (R(r"^It is what this mix has already survived, not a forecast\.$"),
     lambda m: "यह वह है जो यह पोर्टफोलियो पहले झेल चुका है, भविष्य का अनुमान नहीं।"),
    (R(r"^Ask me what to sell and I will work out the smallest change that fixes it\.$"),
     lambda m: "मुझसे पूछिए क्या बेचना है, मैं सबसे छोटा बदलाव बता दूँगा जो इसे ठीक कर दे।"),
    (R(r"^Selling about " + _mp("x", "u") + r" across (\d+) holdings? would bring you inside every limit\.$"),
     lambda m: f"लगभग {_m(m['x'], m['u'])} के {m[3]} शेयर बेचने से आप हर सीमा के अंदर आ जाएँगे।"),
    (R(r"^Sell (\d+) (.+?) — about " + _mp("x", "u") + r" — to get under the (.+?) limit\.$"),
     lambda m: f"{m[2]} के {m[1]} शेयर बेचिए — लगभग {_m(m['x'], m['u'])} — ताकि {_s(m[5])} की सीमा के नीचे आ जाएँ।"),
    (R(r"^That money goes to cash\.$"), lambda m: "वह पैसा नकद में रहेगा।"),
    (R(r"^You do not have to buy anything with it today\.$"), lambda m: "आज उससे कुछ खरीदना ज़रूरी नहीं है।"),
    (R(r"^Nothing needs selling\. You are inside every limit\.$"),
     lambda m: "कुछ बेचने की ज़रूरत नहीं है। आप हर सीमा के अंदर हैं।"),
    (R(r"^You own (\d+) stocks across (\d+) industries, but it behaves like about (\d+) positions\.$"),
     lambda m: f"आपके पास {m[2]} उद्योगों में {m[1]} शेयर हैं, लेकिन यह लगभग {m[3]} शेयरों जैसा व्यवहार करता है।"),
    (R(r"^Biggest: (.+)$"),
     lambda m: "सबसे बड़े: " + ", ".join(f"{_s(a)} {b}%" for a, b in re.findall(r"([a-z][a-z &]*?) (\d+)%", m[1]))),
    (R(r"^You own nothing in (.+?)\.$"), lambda m: f"इनमें आपके पास कुछ नहीं है: {_list(m[1])}।"),
    (R(r"^You have at least something in every industry we cover\.$"),
     lambda m: "हमारे दायरे के हर उद्योग में आपका कुछ न कुछ पैसा है।"),
    (R(r"^Spreading into industries you do not own is usually cheaper than buying more of what you already hold\.$"),
     lambda m: "जिन उद्योगों में आपका पैसा नहीं है, उनमें फैलाना आमतौर पर पहले से मौजूद शेयर और खरीदने से सस्ता पड़ता है।"),
    (R(r"^If (.+?) falls (\d+)%, you would lose about " + _mp("x", "u") + r"\.$"),
     lambda m: f"अगर {FALLS(m)} {m[2]}% गिरे, तो आपको लगभग {_m(m['x'], m['u'])} का नुकसान होगा।"),
    (R(r"^That is (\d+)% of your money — " + _mp("a", "ua") + r" becomes " + _mp("b", "ub") + r"\.$"),
     lambda m: f"यह आपके पैसे का {m[1]}% है — {_m(m['a'], m['ua'])} घटकर {_m(m['b'], m['ub'])} रह जाएँगे।"),
    (R(r"^That is (\d+)% of your money, taking you from " + _mp("a", "ua") + r" to " + _mp("b", "ub") + r"\.$"),
     lambda m: f"यह आपके पैसे का {m[1]}% है, यानी {_m(m['a'], m['ua'])} से घटकर {_m(m['b'], m['ub'])}।"),
    (R(r"^Hardest hit: (.+?)\.$"), lambda m: f"सबसे ज़्यादा असर: {m[1]}।"),
    (R(r"^This is a what-if with the same fall applied to everything, not a forecast\.$"),
     lambda m: "यह 'अगर ऐसा हो' वाली गणना है, जिसमें हर चीज़ पर बराबर गिरावट लगाई गई है — भविष्यवाणी नहीं।"),
    (R(r"^In the (.+?), you would (lose|gain) about " + _mp("x", "u") + r"\.$"),
     lambda m: f"{WINDOWS.get(m[1].lower(), m[1])} में आपको लगभग {_m(m['x'], m['u'])} का {'नुकसान' if m[2] == 'lose' else 'फ़ायदा'} होता।"),
    (R(r"^The (.+?) moved (-?\d+)%, so you would have done (better|worse) than the market by (\d+)%\.$"),
     lambda m: f"{m[1]} {m[2]}% हिला, इसलिए आपका प्रदर्शन बाज़ार से {m[4]}% {'बेहतर' if m[3] == 'better' else 'कमज़ोर'} रहता।"),
    (R(r"^Those are the real prices from that window\.$"), lambda m: "ये उसी दौर की असली कीमतें हैं।"),
    (R(r"^Your worst case in the scenarios I test is the (.+?): you would lose about " + _mp("x", "u") + r"\.$"),
     lambda m: f"मेरे परखे हुए हालातों में आपका सबसे बुरा मामला {WINDOWS.get(m[1].lower(), m[1])} है: आपको लगभग {_m(m['x'], m['u'])} का नुकसान होगा।"),
    (R(r"^This is what actually happened to these companies in that window, not a prediction\.$"),
     lambda m: "उस दौर में इन कंपनियों के साथ सचमुच यही हुआ था — यह भविष्यवाणी नहीं है।"),
    (R(r"^Adding about (\d+)% more would break your own limits: (.+?) would reach (\d+)%, past your (\d+)% (single-stock|sector) limit\.$"),
     lambda m: f"लगभग {m[1]}% और जोड़ने से आपकी अपनी सीमा टूटेगी: {_s(m[2])} {m[3]}% तक पहुँच जाएगा, जो आपकी {m[4]}% की {_s(m[5])} वाली सीमा से ऊपर है।"),
    (R(r"^Adding about (\d+)% more keeps you inside every limit — (.+?) would be (\d+)% and (.+?) (\d+)%\.$"),
     lambda m: f"लगभग {m[1]}% और जोड़ने पर भी आप हर सीमा के अंदर रहेंगे — {_s(m[2])} {m[3]}% होगा और {_s(m[4])} {m[5]}%।"),
    (R(r"^You already hold (.+?) at (\d+)% of your money, in (.+?) which is (\d+)%\.$"),
     lambda m: f"{m[1]} पहले से आपके पैसे का {m[2]}% है, जो {_s(m[3])} उद्योग में आता है और वह {m[4]}% है।"),
    (R(r"^You do not hold (.+?) today\.$"), lambda m: f"आज आपके पास {m[1]} नहीं है।"),
    (R(r"^It sits in (.+?), which is already (\d+)% of your money\.$"),
     lambda m: f"यह {_s(m[1])} में आता है, जो पहले से आपके पैसे का {m[2]}% है।"),
    (R(r"^It moves almost in step with (.+?) — correlation ([\d\.]+) — so it adds less spread than it looks\.$"),
     lambda m: f"यह {m[1]} के लगभग साथ-साथ चलता है — सहसंबंध {m[2]} — इसलिए इससे उतना बँटवारा नहीं होता जितना दिखता है।"),
    (R(r"^I will not tell you whether it goes up — my desks score worse than a coin flip at that\.$"),
     lambda m: "मैं यह नहीं बताऊँगा कि यह बढ़ेगा या नहीं — इस काम में मेरे विश्लेषक सिक्का उछालने से भी खराब हैं।"),
    (R(r"^I can tell you this would concentrate you further\.$"),
     lambda m: "मैं इतना बता सकता हूँ कि इससे आपका पैसा और ज़्यादा एक जगह सिमट जाएगा।"),
    (R(r"^That is a statement about your concentration, not a view on the price\.$"),
     lambda m: "यह आपके पैसे के एक जगह जमा होने के बारे में है, कीमत पर कोई राय नहीं।"),
    (R(r"^Ask me to find diversifiers if you want the opposite effect\.$"),
     lambda m: "उल्टा असर चाहिए तो मुझसे पैसा बाँटने वाले शेयर ढूँढने को कहिए।"),
    (R(r"^(.+?) and (.+?) move almost in step — correlation ([\d\.]+)\.$"),
     lambda m: f"{m[1]} और {m[2]} लगभग साथ-साथ चलते हैं — सहसंबंध {m[3]}।"),
    (R(r"^Together they are (\d+)% of your money, so that pair behaves like a single position of that size\.$"),
     lambda m: f"ये दोनों मिलकर आपके पैसे का {m[1]}% हैं, यानी यह जोड़ी उतने बड़े एक ही शेयर की तरह चलती है।"),
    (R(r"^Average correlation across everything you own is ([\d\.]+)\.$"),
     lambda m: f"आपके सारे शेयरों का औसत सहसंबंध {m[1]} है।"),
    (R(r"^Lower is better spread\.$"), lambda m: "यह जितना कम हो, पैसा उतना बेहतर बँटा है।"),
    (R(r"^Also closely linked: (.+)\.$"), lambda m: f"इनके अलावा भी आपस में जुड़े हुए: {m[1]}।"),
    (R(r"^Selling one of a closely linked pair usually spreads you out more than buying something new\.$"),
     lambda m: "आपस में जुड़ी जोड़ी में से एक को बेचना आमतौर पर कुछ नया खरीदने से ज़्यादा बँटवारा देता है।"),
    # follow-up questions (display only: the English text is what actually gets asked)
    (R(r"^What if (.+?) falls (\d+)%\?$"), lambda m: f"अगर {_s(m[1])} {m[2]}% गिरे तो?"),
    (R(r"^Why is my risk high\?$"), lambda m: "मेरा जोखिम ज़्यादा क्यों है?"),
    (R(r"^Am I diversified\?$"), lambda m: "क्या मेरा पैसा ठीक से बँटा है?"),
    (R(r"^What should I sell\?$"), lambda m: "मुझे क्या बेचना चाहिए?"),
    (R(r"^(How much would|What would) that cost me in tax\?$"), lambda m: "इसमें मुझे कितना टैक्स लगेगा?"),
    (R(r"^Show me the full rebalance plan$"), lambda m: "पूरी रीबैलेंस योजना दिखाइए"),
    (R(r"^What if I do nothing\?$"), lambda m: "अगर मैं कुछ न करूँ तो?"),
    (R(r"^What should I buy to spread out\?$"), lambda m: "पैसा बाँटने के लिए मुझे क्या खरीदना चाहिए?"),
    (R(r"^What moves together\?$"), lambda m: "कौन-से शेयर साथ-साथ चलते हैं?"),
    (R(r"^What happened in Covid\?$"), lambda m: "कोविड में क्या हुआ था?"),
    (R(r"^What does (.+?) move with\?$"), lambda m: f"{m[1]} किसके साथ चलता है?"),
    (R(r"^What should I sell to make room\?$"), lambda m: "जगह बनाने के लिए मुझे क्या बेचना चाहिए?"),
    (R(r"^Find me something that spreads me out$"), lambda m: "मुझे ऐसा शेयर ढूँढिए जो पैसा बाँटे"),
    (R(r"^How am I doing\?$"), lambda m: "मेरा हाल कैसा है?"),
]


def exact(sentence: str) -> str | None:
    """Hindi for one English sentence, or None if it is not one the explainer templates."""
    s = sentence.strip()
    for rx, fn in RULES:
        m = rx.match(s)
        if m:
            try:
                return fn(m)
            except Exception:  # noqa: BLE001
                return None
    return None


# Sentences from the Protect / Govern / Learn pages (scanner, tax shield, risk firewall ...).
from backend import hindi_page_rules as _page   # noqa: E402  (needs R and SECTORS defined above)

RULES.extend(_page.RULES)


def exact(sentence: str) -> str | None:   # noqa: F811 - extends the lookup with the fixed-sentence table
    """Hindi for one English sentence, or None if it is not one the product templates."""
    s = sentence.strip()
    hit = _page.STATIC.get(s) or _page.STATIC.get(s.rstrip("."))
    if hit:
        return hit
    for rx, fn in RULES:
        m = rx.match(s)
        if m:
            try:
                return fn(m)
            except Exception:  # noqa: BLE001
                return None
    return None


def exact_whole(text: str) -> str | None:
    """Hindi for a fixed multi-sentence text: the fixed table, or a rule written for the whole
    text. A rule that only matched by letting one of its captures swallow a sentence boundary
    (". ") is rejected -- that would be a one-sentence rule misreading several sentences."""
    t = text.strip()
    hit = _page.STATIC.get(t)
    if hit:
        return hit
    for rx, fn in RULES:
        m = rx.match(t)
        if m and not any(g and ". " in g for g in m.groups()):
            try:
                return fn(m)
            except Exception:  # noqa: BLE001
                return None
    return None
