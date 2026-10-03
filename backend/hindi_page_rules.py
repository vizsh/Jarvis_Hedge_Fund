"""Exact Hindi for the backend sentences shown on the Protect, Govern and Learn pages: the tip
scanner, the tax shield, the risk firewall, the rebalance simulator and the stress tests.

Like hindi_rules.py: fixed sentences are looked up, templated ones are matched and the
figures are placed by code, so a number can never come out different. Anything that matches
nothing here goes to the guarded model fallback in vernacular.py, or stays English.
"""
from __future__ import annotations

import re

from backend.hindi_rules import R, SECTORS

# --------------------------------------------------------------------- fixed sentences
STATIC: dict[str, str] = {
    # scanner: tactic names and why each is a warning sign
    "Promises guaranteed returns": "पक्के मुनाफ़े का वादा",
    "Promises a huge multiple": "कई गुना मुनाफ़े का वादा",
    "Pushes you to act now": "तुरंत कदम उठाने का दबाव",
    "Claims inside or operator knowledge": "अंदरूनी या ऑपरेटर की जानकारी का दावा",
    "Pushes you to a paid or private group": "पैसे वाले या प्राइवेट ग्रुप में बुलाना",
    "Tells you to ignore losses": "नुक़सान को नज़रअंदाज़ करने की सलाह",
    "Claims SEBI registration (verify it)": "सेबी पंजीकरण का दावा (जाँच लें)",
    "No one can guarantee a market return. Registered advisers are barred from promising one.":
        "बाज़ार का रिटर्न कोई पक्का नहीं कर सकता। पंजीकृत सलाहकारों को ऐसा वादा करने की मनाही है।",
    "Claims of 5x or 10x in weeks are the standard hook of pump-and-dump groups.":
        "हफ़्तों में 5 गुना या 10 गुना का दावा पंप-एंड-डंप ग्रुपों का पुराना चारा है।",
    "Manufactured urgency is meant to stop you checking anything.":
        "बनावटी जल्दबाज़ी का मक़सद आपको कुछ भी जाँचने से रोकना है।",
    "Trading on inside information is illegal; real insiders do not post it in groups.":
        "अंदरूनी जानकारी पर सौदा करना ग़ैरक़ानूनी है; असली अंदरूनी लोग इसे ग्रुपों में नहीं डालते।",
    "Tips sold through private groups are the usual route for unregistered advice.":
        "प्राइवेट ग्रुपों में बिकने वाली टिप्स बिना पंजीकरण की सलाह का आम रास्ता हैं।",
    "Advice that ignores downside is advice that ignores your capital.":
        "जो सलाह नुक़सान को नज़रअंदाज़ करती है, वह आपकी पूँजी को नज़रअंदाज़ करती है।",
    "Check any adviser at sebi.gov.in under Intermediaries before acting. Scam groups often claim it.":
        "कुछ भी करने से पहले किसी भी सलाहकार को sebi.gov.in पर \"Intermediaries\" में जाँचिए। ठग ग्रुप अक्सर यह दावा करते हैं।",
    "UNVERIFIED — LIKELY A PUMP OR SCAM": "जाँच में नहीं टिका — पंप या ठगी की आशंका",
    "CAUTION — DO NOT ACT ON THIS ALONE": "सावधान — सिर्फ़ इसके भरोसे कुछ न करें",
    "NO RED FLAGS FOUND — STILL NOT ADVICE": "कोई ख़तरे की निशानी नहीं मिली — फिर भी यह सलाह नहीं है",
    "A checker, not advice. It tests claims against dated data on file; it cannot know what is not on file.":
        "यह जाँचने वाला है, सलाह नहीं। यह दावों को दर्ज तारीख़ वाले डेटा से परखता है; जो दर्ज नहीं है, वह नहीं जान सकता।",
    "Nothing in it is alarming, but nothing in it is supported either.":
        "इसमें कुछ डरावना नहीं है, पर कुछ भी साबित भी नहीं होता।",
    "Check any adviser at sebi.gov.in before paying or acting.":
        "पैसे देने या कुछ करने से पहले किसी भी सलाहकार को sebi.gov.in पर जाँचिए।",
    "No company was named, so there is nothing to check this against.":
        "कोई कंपनी नहीं बताई गई, इसलिए इसे परखने के लिए कुछ नहीं है।",
    "No two comparable filings on record, so this number cannot be checked.":
        "दर्ज में तुलना लायक़ दो रिपोर्टें नहीं हैं, इसलिए यह आँकड़ा जाँचा नहीं जा सकता।",
    "A target is an opinion; no filing can confirm it.": "टारगेट एक राय है; कोई रिपोर्ट उसे पक्का नहीं कर सकती।",
    "No price history held for this name.": "इस नाम का दामों का इतिहास हमारे पास नहीं है।",
    # tax shield
    "Add what you paid to see the tax on selling this.": "इसे बेचने पर टैक्स देखने के लिए बताइए कि आपने कितने में ख़रीदा।",
    "Already long-term. Selling uses the lower 12.5% rate.": "पहले से लंबी अवधि का है। बेचने पर कम 12.5% की दर लगेगी।",
    "Arithmetic on published rates, holding by holding. Not tax advice.": "प्रकाशित दरों पर हिसाब, शेयर-दर-शेयर। यह टैक्स की सलाह नहीं है।",
    # simulator / sandbox
    "Roughly neutral. The main cost here is the trading itself.": "लगभग बराबर। यहाँ मुख्य लागत सौदे करने की ही है।",
    "This is not an improvement on the numbers that matter. Worth knowing before you commit it.":
        "जो आँकड़े मायने रखते हैं उन पर यह सुधार नहीं है। पक्का करने से पहले यह जान लेना ज़रूरी है।",
    "Largest size the firewall would approve": "सबसे बड़ा आकार जिसे दीवार मंज़ूर करेगी",
    "compliant counter-offer": "सीमा के भीतर वाला जवाबी प्रस्ताव",
    "rebalance plan": "संतुलन योजना", "sandbox commit": "रखे गए सौदे पक्के किए",
    "Sample entry for the tamper demo": "छेड़छाड़ परीक्षण के लिए नमूना प्रविष्टि",

    # "Every number is a door" (backend/drilldown.py)
    "Total value": "कुल क़ीमत", "Effective holdings": "असल में कितने शेयर", "Market sensitivity": "बाज़ार से संवेदनशीलता",
    "Worst fall so far": "अब तक की सबसे बड़ी गिरावट", "Cash buffer": "नक़द बफ़र", "Cash": "नक़द",
    "Shares held": "रखे हुए शेयर", "Last close": "पिछला बंद भाव", "Position value": "हिस्से की क़ीमत",
    "Single-stock excess": "एक शेयर की अधिकता", "Industry excess": "उद्योग की अधिकता", "Cash shortfall": "नक़द की कमी", "Breadth": "विविधता",
    "not invested": "निवेश नहीं किया गया", "as entered by you": "जैसा आपने दर्ज किया", "Cash is held as entered.": "नक़द वैसा ही है जैसा दर्ज किया गया।",
    "Every holding priced at its last close on or before the simulation clock, multiplied by the shares you hold, plus cash.":
        "हर शेयर का भाव सिमुलेशन की घड़ी तक के आख़िरी बंद भाव से, आपके रखे शेयरों से गुणा करके, फिर नक़द जोड़कर।",
    "This is the number every weight and limit in the product is a percentage of, so it is worth knowing exactly what is in it.":
        "इस उत्पाद का हर वज़न और हर सीमा इसी आँकड़े का प्रतिशत है, इसलिए ठीक-ठीक जानना ज़रूरी है कि इसमें क्या-क्या है।",
    "Companies in one industry fall together. This is the number that says how much of your money one bad industry can reach.":
        "एक उद्योग की कंपनियाँ साथ गिरती हैं। यह आँकड़ा बताता है कि एक बुरा उद्योग आपके कितने पैसे तक पहुँच सकता है।",
    "One company can fail on its own. This caps what that costs you.": "एक कंपनी अकेले भी डूब सकती है। यह सीमा तय करती है कि इसमें आपका कितना नुक़सान हो।",
    "100 minus four capped penalties. The caps sum to 100, so no single dimension can drive the score to zero on its own.":
        "100 में से चार सीमित कटौतियाँ घटाई जाती हैं। सीमाओं का जोड़ 100 है, इसलिए कोई एक पहलू अकेले स्कोर को शून्य नहीं कर सकता।",
    "The formula is published rather than hidden so you can disagree with the weights. Changing your profile changes the limits and therefore this score — the portfolio has not moved.":
        "सूत्र छिपाया नहीं, सामने रखा गया है ताकि आप वज़नों से असहमत हो सकें। प्रोफ़ाइल बदलने से सीमाएँ बदलती हैं और इसलिए यह स्कोर भी — पोर्टफ़ोलियो नहीं हिला।",
    "A beta of 1.2 means that when the market drops 10%, a basket like this has tended to drop about 12%. It cuts both ways.":
        "1.2 के बीटा का मतलब है कि बाज़ार 10% गिरे तो ऐसी टोकरी लगभग 12% गिरती रही है। यह दोनों तरफ़ असर करता है।",
    "Your current share counts are priced back through every day in the snapshot; this is the largest peak-to-trough fall in that series.":
        "आपके मौजूदा शेयरों को स्नैपशॉट के हर दिन के भाव पर आँका जाता है; यह उस श्रृंखला की सबसे बड़ी ऊँचाई-से-निचाई की गिरावट है।",
    "This is not a forecast. It is what this exact basket has already lived through — and it is the number that decides whether somebody sells at the bottom.":
        "यह पूर्वानुमान नहीं है। यह वही है जिससे यह टोकरी पहले ही गुज़र चुकी है — और यही आँकड़ा तय करता है कि कोई सबसे निचले भाव पर बेचेगा या नहीं।",
    "Cash is what lets you buy when prices fall, instead of having to sell something first at the worst possible moment.":
        "नक़द वह है जिससे दाम गिरने पर आप ख़रीद सकते हैं, बजाय इसके कि सबसे बुरे वक़्त पर पहले कुछ बेचना पड़े।",
    "Only bars dated on or before the simulation clock are visible. Rewinding the clock hides later data at the query, not in the application, so no calculation here can see the future.":
        "सिर्फ़ सिमुलेशन की घड़ी तक की तारीख़ वाले भाव दिखते हैं। घड़ी पीछे करने पर बाद का डेटा क्वेरी पर ही छिप जाता है, ऐप में नहीं, इसलिए यहाँ कोई भी गणना भविष्य नहीं देख सकती।",
    # stress windows
    "The fastest bear market in history.": "इतिहास की सबसे तेज़ मंदी।",
    "The nine months after the bottom.": "सबसे निचले बिंदु के बाद के नौ महीने।",
    "Inflation, rate rises, and a long grind down.": "महँगाई, ब्याज दरों में बढ़ोतरी, और लंबी धीमी गिरावट।",
    "A sharp, concentrated shock to Indian large caps.": "भारतीय बड़ी कंपनियों को लगा तेज़, केंद्रित झटका।",
    "Covid crash": "कोविड की गिरावट", "Covid recovery": "कोविड के बाद की रिकवरी",
    "2022 rate shock": "2022 की ब्याज दरों की मार", "Jan 2023 selloff": "जनवरी 2023 की बिकवाली",
    "Market falls 10%": "बाज़ार 10% गिरे", "Market falls 20%": "बाज़ार 20% गिरे",
    "Technology falls 30%": "टेक्नोलॉजी 30% गिरे", "Banks fall 25%": "बैंक 25% गिरें",
}


_MONEY = r"₹[\d,\.]+(?: lakh| crore)?"
KINDS_P = {"retail investor": "आम निवेशक", "serious private investor": "गंभीर निजी निवेशक", "boutique fund": "बुटीक फंड"}


def _hm(x: str) -> str:
    return x.replace(" lakh", " लाख").replace(" crore", " करोड़")


def exact(s: str):
    from backend.hindi_rules import exact as _e
    return _e(s)

_LABEL_LOWER = {k.lower(): v for k, v in STATIC.items() if k[0].isupper() and len(k) < 45}


def _sec(x: str) -> str:
    """A sector shown as a code (IT) or a label (Technology) -> Hindi."""
    x = x.strip()
    if x.lower() in SECTORS:
        return SECTORS[x.lower()]
    try:
        from core import universe
        lab = universe.sector_label(x).lower()
        return SECTORS.get(lab, x)
    except Exception:  # noqa: BLE001
        return x


def _days(n: str) -> str:
    return f"{n} दिन"


_kind = {"net income": "शुद्ध मुनाफ़ा", "revenue": "आमदनी"}

RULES = [
    # ---- scanner
    (R(r"^It uses (\d+) scam-style tactics?: (.+)\.$"),
     lambda m: f"इसमें ठगी जैसी {m[1]} {'चाल है' if m[1] == '1' else 'चालें हैं'}: " + ", ".join(_LABEL_LOWER.get(p.strip(), p.strip()) for p in m[2].split(",")) + "।"),
    (R(r"^(\d+) claims? contradicted by the data we hold\.$"), lambda m: f"{m[1]} {'दावा' if m[1] == '1' else 'दावे'} हमारे पास मौजूद डेटा से ग़लत निकले।" if m[1] != "1" else f"{m[1]} दावा हमारे पास मौजूद डेटा से ग़लत निकला।"),
    (R(r"^(\d+) claims? roughly supported\.$"), lambda m: f"{m[1]} {'दावा लगभग सही निकला' if m[1] == '1' else 'दावे लगभग सही निकले'}।"),
    (R(r"^It names (.+), which we have no data on, so nothing about it can be checked\.$"),
     lambda m: f"इसमें {m[1]} का नाम है, जिसका हमारे पास कोई डेटा नहीं, इसलिए उसके बारे में कुछ जाँचा नहीं जा सकता।"),
    (R(r"^Our data shows (net income|revenue) moved ([+-][\d.]+)% from the previous period; the tip says ([+-]\d+)%\.$"),
     lambda m: f"हमारे डेटा में {_kind[m[1]]} पिछली अवधि से {m[2]}% बदला; टिप कहती है {m[3]}%।"),
    (R(r"^That target is ([+-]\d+)% from the last close of ([\d,\.]+)\. Calls above \+60% in a short window are a classic pump marker\.$"),
     lambda m: f"वह टारगेट पिछले बंद भाव {m[2]} से {m[1]}% दूर है। कम समय में +60% से ऊपर के दावे पंप की क्लासिक निशानी हैं।"),
    (R(r"^That target is ([+-]\d+)% from the last close of ([\d,\.]+)\. A target is an opinion; no filing can confirm it\.$"),
     lambda m: f"वह टारगेट पिछले बंद भाव {m[2]} से {m[1]}% दूर है। टारगेट एक राय है; कोई रिपोर्ट उसे पक्का नहीं कर सकती।"),
    (R(r"^Price on (\d{4}-\d{2}-\d{2})$"), lambda m: f"{m[1]} का भाव"),
    (R(r"^Price is ([+-][\d.]+)% over the last (1 month|3 months) \(close ([\d,\.]+) on (\d{4}-\d{2}-\d{2})\)\.$"),
     lambda m: f"भाव पिछले {'1 महीने' if m[2] == '1 month' else '3 महीनों'} में {m[1]}% रहा ({m[4]} को बंद भाव {m[3]})।"),
    # ---- tax shield
    (R(r"^Down ₹([\d,]+)\. A realised loss can be set against gains this year\.$"),
     lambda m: f"₹{m[1]} का घाटा। पक्का हुआ घाटा इस साल के मुनाफ़े से घटाया जा सकता है।"),
    (R(r"^Wait (\d+) more days? to cross 12 months and save ₹([\d,]+)\.$"),
     lambda m: f"12 महीने पार करने के लिए {_days(m[1])} और रुकिए और ₹{m[2]} बचाइए।"),
    (R(r"^(\d+) days? to the long-term mark; selling today is taxed at 20%\.$"),
     lambda m: f"लंबी अवधि में आने में {_days(m[1])} बाक़ी हैं; आज बेचने पर 20% टैक्स लगेगा।"),
    # ---- risk firewall
    (R(r"^Cannot sell (\d+) shares of (.+?): position holds (\d+)\.$"),
     lambda m: f"{m[2]} के {m[1]} शेयर नहीं बेचे जा सकते: आपके पास {m[3]} हैं।"),
    (R(r"^(.+?) would reach ([\d.]+)% of NAV, above the ([\d.]+)% single-position ceiling\.$"),
     lambda m: f"{m[1]} आपकी कुल क़ीमत का {m[2]}% हो जाएगा, जो एक शेयर की {m[3]}% की सीमा से ऊपर है।"),
    (R(r"^(.+?) exposure would rise to ([\d.]+)%, above the ([\d.]+)% sector cap\.$"),
     lambda m: f"{_sec(m[1])} में हिस्सा बढ़कर {m[2]}% हो जाएगा, जो {m[3]}% की उद्योग-सीमा से ऊपर है।"),
    (R(r"^Cash would fall to ([\d.]+)%, below the ([\d.]+)% minimum reserve\.$"),
     lambda m: f"नक़द गिरकर {m[1]}% रह जाएगा, जो {m[2]}% के न्यूनतम रिज़र्व से नीचे है।"),
    (R(r"^Reduce to (\d+) shares - shorting is disabled\.$"), lambda m: f"{m[1]} शेयरों तक घटाइए — बिना शेयर के बेचना बंद है।"),
    (R(r"^No size of this trade is compliant - (.+?) is already at its limit\. Reduce exposure elsewhere first\.$"),
     lambda m: f"इस सौदे का कोई भी आकार सीमा में नहीं बैठता — {_binding(m[1])} पहले से अपनी सीमा पर है। पहले कहीं और हिस्सा घटाइए।"),
    (R(r"^Reduce from (\d+) to (\d+) shares - (.+?) binds, leaving (.+?) at ([\d.]+)% and cash at ([\d.]+)%\.$"),
     lambda m: f"{m[1]} से घटाकर {m[2]} शेयर कीजिए — {_binding(m[3])} बाँधती है, जिससे {_sec(m[4])} {m[5]}% और नक़द {m[6]}% रहेगा।"),
    (R(r"^no more than (\d+)% in one stock, (\d+)% in one industry, and at least (\d+)% kept in cash$"),
     lambda m: f"एक शेयर में अधिकतम {m[1]}%, एक उद्योग में {m[2]}%, और कम से कम {m[3]}% नक़द रखना"),
    # ---- simulator
    (R(r"^This puts you inside every limit you set, and the score goes up (\d+) points\.$"),
     lambda m: f"इससे आप अपनी तय हर सीमा के भीतर आ जाते हैं, और स्कोर {m[1]} अंक बढ़ता है।"),
    (R(r"^Better on balance — (\d+) points — but not everything is resolved\.$"),
     lambda m: f"कुल मिलाकर बेहतर — {m[1]} अंक — पर सब कुछ सुलझा नहीं है।"),
    (R(r"^(.+?): no price or zero size$"), lambda m: f"{m[1]}: भाव नहीं है या आकार शून्य है"),
    (R(r"^(.+?): you do not hold (\d+) shares$"), lambda m: f"{m[1]}: आपके पास {m[2]} शेयर नहीं हैं"),
    # ---- standing rules (watchlist)
    (R(r"^Tell me if (.+?) goes (above|below) ([\d.]+%?(?: points)?)$"), lambda m: _watch(m)),
    (R(r"^You are at (\d+)% today\.$"), lambda m: f"आज आप {m[1]}% पर हैं।"),
    (R(r"^(.+?) is (\d+)% today\.$"), lambda m: f"{m[1]} आज {m[2]}% है।"),
    (R(r"^You score (\d+) today\.$"), lambda m: f"आज आपका स्कोर {m[1]} है।"),
    (R(r"^A thin buffer forces you to sell to buy\.$"), lambda m: "पतला बफ़र आपको ख़रीदने के लिए बेचने पर मजबूर करता है।"),
    (R(r"^Recomputed as your holdings change\.$"), lambda m: "आपके शेयर बदलने पर दोबारा निकाला जाता है।"),

    # ---- "Every number is a door"
    (R(r"^(" + "|".join(re.escape(k) for k in SECTORS) + r") exposure$", re.I), lambda m: f"{_sec(m[1])} में हिस्सा"),
    (R(r"^([A-Z][A-Za-z&'. ]{1,28}) weight$"), lambda m: f"{m[1]} का वज़न"),
    (R(r"^Score (\d+) / 100$"), lambda m: f"स्कोर {m[1]} / 100"),
    (R(r"^(\d+) shares at ₹([\d,\.]+)$"), lambda m: f"{m[1]} शेयर, ₹{m[2]} के भाव पर"),
    (R(r"^([\d.]+)% of everything you own$"), lambda m: f"आपके कुल पैसे का {m[1]}%"),
    (R(r"^on or before (\d{4}-\d{2}-\d{2})$"), lambda m: f"{m[1]} को या उससे पहले"),
    (R(r"^contributes ([\d.]+) to the concentration index$"), lambda m: f"संकेंद्रण सूचकांक में {m[1]} जोड़ता है"),
    (R(r"^([\d.]+)% over the ([\d.]+)% cap, across all names · caps at -35$"), lambda m: f"{m[2]}% की सीमा से {m[1]}% ऊपर, सभी शेयर मिलाकर · अधिकतम -35"),
    (R(r"^([\d.]+)% over the ([\d.]+)% cap · caps at -30$"), lambda m: f"{m[2]}% की सीमा से {m[1]}% ऊपर · अधिकतम -30"),
    (R(r"^([\d.]+)% held against a ([\d.]+)% requirement · caps at -10$"), lambda m: f"{m[2]}% की ज़रूरत के मुक़ाबले {m[1]}% रखा है · अधिकतम -10"),
    (R(r"^([\d.]+) effective positions against a target of 8 · caps at -25$"), lambda m: f"8 के लक्ष्य के मुक़ाबले असल में {m[1]} शेयर · अधिकतम -25"),
    (R(r"^(" + _MONEY + r") across (\d+) holdings?, divided by a total value of (" + _MONEY + r"), gives ([\d.]+)%\. Your limit is ([\d.]+)%\.$"),
     lambda m: f"{_hm(m[1])} कुल {m[2]} शेयरों में, {_hm(m[3])} की कुल क़ीमत से भाग देने पर {m[4]}% आता है। आपकी सीमा {m[5]}% है।"),
    (R(r"^(\d+) shares x ₹([\d,\.]+) = (" + _MONEY + r"), which is ([\d.]+)% of (" + _MONEY + r")\.$"),
     lambda m: f"{m[1]} शेयर x ₹{m[2]} = {_hm(m[3])}, जो {_hm(m[5])} का {m[4]}% है।"),
    (R(r"^Square every weight and add them up — that is the Herfindahl index, ([\d.]+) here\. One divided by it gives ([\d.]+)\.$"),
     lambda m: f"हर वज़न का वर्ग करके जोड़िए — यही हर्फ़िनडाल सूचकांक है, यहाँ {m[1]}। एक को इससे भाग देने पर {m[2]} आता है।"),
    (R(r"^You hold (\d+) stocks, but the big ones dominate, so the risk behaves like about (\d+) equal positions\. Counting names overstates how spread out you are\.$"),
     lambda m: f"आपके पास {m[1]} शेयर हैं, पर बड़े वाले हावी हैं, इसलिए जोखिम लगभग {m[2]} बराबर शेयरों जैसा चलता है। नाम गिनने से लगता है कि आप ज़्यादा बँटे हैं, जो सच नहीं।"),
    (R(r"^Covariance of your daily returns with (.+?), divided by the variance of the benchmark, over the history in the snapshot up to (\d{4}-\d{2}-\d{2})\.$"),
     lambda m: f"आपके रोज़ के रिटर्न का {m[1]} के साथ सहप्रसरण, बेंचमार्क के प्रसरण से भाग देकर, {m[2]} तक के स्नैपशॉट के इतिहास पर।"),
    (R(r"^(" + _MONEY + r") divided by (" + _MONEY + r")\.$"), lambda m: f"{_hm(m[1])} को {_hm(m[2])} से भाग देने पर।"),
    (R(r"^Measured against (.+?): (.+)$"), lambda m: f"{KINDS_P.get(m[1].lower(), m[1])} के हिसाब से नापा गया: {exact(m[2]) or m[2]}"),
    (R(r"^(" + _MONEY + r")$"), lambda m: _hm(m[1])),
    # ---- stress
    (R(r"^A uniform (\d+)% fall applied to (everything you hold|.+?)\. A what-if, not a forecast\.$"),
     lambda m: f"{'आपके सभी शेयरों' if m[2] == 'everything you hold' else _sec(m[2])} पर लगी एक समान {m[1]}% गिरावट। यह एक \"अगर ऐसा हो\" है, पूर्वानुमान नहीं।"),
]

_WHAT = {"my cash buffer": "मेरा नक़द बफ़र", "my portfolio score": "मेरा पोर्टफ़ोलियो स्कोर",
         "how many positions it really behaves like": "वह असल में कितने शेयरों जैसा चलता है",
         "my worst tested loss": "मेरा सबसे बुरा जाँचा गया नुक़सान", "the worst fall this basket has had": "इस टोकरी की अब तक की सबसे बड़ी गिरावट",
         "an industry's share of my money": "किसी उद्योग का मेरे पैसे में हिस्सा", "one holding's share of my money": "किसी एक शेयर का मेरे पैसे में हिस्सा"}


def _watch(m) -> str:
    what, op, val = m[1], m[2], m[3]
    mine = re.match(r"^(.+?)'s share of my money$", what)
    w = f"{_sec(mine[1])} का मेरे पैसे में हिस्सा" if mine else _WHAT.get(what, what)
    val = val.replace(" points", " अंक")
    return f"मुझे बताइए अगर {w} {val} से {'ऊपर' if op == 'above' else 'नीचे'} जाए"


_BIND = {"POSITION_LIMIT": "एक शेयर की सीमा", "SECTOR_LIMIT": "उद्योग की सीमा", "CASH_RESERVE": "नक़द रिज़र्व"}


def _binding(x: str) -> str:
    return _BIND.get(x.strip(), x)
