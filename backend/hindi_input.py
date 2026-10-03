"""Understanding Hindi questions, typed or spoken.

The assistant's router reads English. The old bridge asked a language model to translate the Hindi
freely, and it invented words that were never said ("ICICI Prudential Long Term Equity Fund",
"Airtel portfolio"). This module never translates freely. Instead:

  1. numbers are read in code: digits, Devanagari digits and spoken Hindi ("तीन लाख", "चालीस हज़ार",
     "डेढ़ करोड़") become exact figures;
  2. the *intent* comes from Hindi keyword rules, or - when no rule fits - from the local model
     picking ONE intent from a closed list (it cannot invent a fund or a figure);
  3. a fixed English question for that intent is built from the figures found in step 1.

The English question is then answered exactly like a typed English one, in Hindi. Anything it
cannot place is passed through unchanged, so the assistant asks "did you mean..." (in Hindi)
instead of guessing.
"""
from __future__ import annotations

import re
from typing import Any, Callable

from backend.practice_hi import norm

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def has_devanagari(text: str) -> bool:
    return bool(DEVANAGARI.search(text or ""))


# ------------------------------------------------------------------ number words
_ONES = ("शून्य एक दो तीन चार पांच छह सात आठ नौ दस ग्यारह बारह तेरह चौदह पंद्रह सोलह सत्रह अठारह उन्नीस बीस "
         "इक्कीस बाईस तेईस चौबीस पच्चीस छब्बीस सत्ताईस अट्ठाईस उनतीस तीस इकतीस बत्तीस तैंतीस चौंतीस पैंतीस छत्तीस सैंतीस अड़तीस उनतालीस चालीस "
         "इकतालीस बयालीस तैंतालीस चौवालीस पैंतालीस छियालीस सैंतालीस अड़तालीस उनचास पचास इक्यावन बावन तिरपन चौवन पचपन छप्पन सत्तावन अट्ठावन उनसठ साठ "
         "इकसठ बासठ तिरसठ चौंसठ पैंसठ छियासठ सड़सठ अड़सठ उनहत्तर सत्तर इकहत्तर बहत्तर तिहत्तर चौहत्तर पचहत्तर छिहत्तर सतहत्तर अठहत्तर उनासी अस्सी "
         "इक्यासी बयासी तिरासी चौरासी पचासी छियासी सत्तासी अट्ठासी नवासी नब्बे इक्यानवे बानवे तिरानवे चौरानवे पंचानवे छियानवे सत्तानवे अट्ठानवे निन्यानवे").split()
NUM: dict[str, float] = {norm(w): float(i) for i, w in enumerate(_ONES)}
NUM.update({norm(k): v for k, v in {"पाँच": 5, "पन्द्रह": 15, "छः": 6, "छ": 6, "डेढ़": 1.5, "ढाई": 2.5, "सवा": 1.25, "पौन": 0.75,
                                    "आधा": 0.5, "साढ़े": 0.5}.items()})
MULT: dict[str, float] = {norm(k): v for k, v in {"सौ": 100, "सैकड़ा": 100, "हज़ार": 1e3, "हजार": 1e3, "लाख": 1e5, "करोड़": 1e7, "करोड": 1e7}.items()}
UNITS_PCT = {norm(x) for x in ("प्रतिशत", "परसेंट", "फीसदी", "फ़ीसदी", "प्रतिशत्")}
UNITS_YEAR = {norm(x) for x in ("साल", "सालों", "वर्ष", "वर्षों", "बरस")}
UNITS_MONTH = {norm(x) for x in ("महीने", "महीना", "माह", "महीनों", "मासिक")}
_TOKEN = re.compile(r"[ऀ-ॿ]+|\d[\d,]*(?:\.\d+)?%?|₹|%|[A-Za-z][A-Za-z&'.-]*")


def quantities(text: str) -> list[dict[str, Any]]:
    """Every figure in a sentence with what it is measured in: money / pct / years / months / plain."""
    t = norm(text.translate(_DIGITS))
    toks = _TOKEN.findall(t)
    out: list[dict[str, Any]] = []
    i = 0
    while i < len(toks):
        tok = toks[i]
        plain = tok.replace(",", "").rstrip("%")
        is_num = bool(re.fullmatch(r"\d+(?:\.\d+)?", plain)) or tok in NUM
        is_mult = tok in MULT
        if not (is_num or is_mult):
            i += 1
            continue
        total, cur, j, saw_mult, pct_sign = 0.0, 0.0, i, False, tok.endswith("%")
        while j < len(toks):
            u = toks[j]
            up = u.replace(",", "").rstrip("%")
            if re.fullmatch(r"\d+(?:\.\d+)?", up):
                cur += float(up)
                pct_sign = pct_sign or u.endswith("%")
            elif u in NUM:
                cur += NUM[u]
            elif u in MULT:
                m = MULT[u]
                if m == 100:
                    cur = (cur or 1) * 100
                else:
                    total += (cur or 1) * m
                    cur = 0.0
                    saw_mult = True
            else:
                break
            j += 1
        value = total + cur
        nxt = toks[j] if j < len(toks) else ""
        after2 = " ".join(toks[j:j + 3])
        prev = toks[i - 1] if i else ""
        kind = ("pct" if pct_sign or nxt in UNITS_PCT or nxt == "%" else
                "years" if nxt in UNITS_YEAR else
                "months" if nxt in UNITS_MONTH and value <= 120 else
                "money" if saw_mult or nxt in (norm("रुपये"), norm("रुपए"), norm("रूपये"), "₹") or prev == "₹" or value >= 1000 else "plain")
        monthly = bool(re.search(norm("(महीने|मासिक|हर माह|एसआईपी|sip)"), after2) or prev in UNITS_MONTH) and kind == "money"
        out.append({"v": value, "kind": kind, "at": i, "monthly": monthly})
        i = max(j, i + 1)
    return out


def _fmt(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def _m(v: float) -> str:
    """A rupee figure the English router reads: 25 lakh, 2 crore, 40000."""
    if v >= 1e7 and (v / 1e7) == round(v / 1e7, 2):
        return f"{_fmt(round(v / 1e7, 2))} crore"
    if v >= 1e5 and (v / 1e5) == round(v / 1e5, 2):
        return f"{_fmt(round(v / 1e5, 2))} lakh"
    return _fmt(v)


# ------------------------------------------------------------------ names
COMPANIES = {norm(k): v for k, v in {
    "टीसीएस": "TCS", "इन्फोसिस": "Infosys", "इंफोसिस": "Infosys", "रिलायंस": "Reliance", "एचडीएफसी बैंक": "HDFC Bank", "एचडीएफसी": "HDFC Bank",
    "आईसीआईसीआई": "ICICI Bank", "विप्रो": "Wipro", "आईटीसी": "ITC", "एसबीआई": "State Bank of India", "स्टेट बैंक": "State Bank of India",
    "एक्सिस": "Axis Bank", "कोटक": "Kotak", "मारुति": "Maruti", "टाटा स्टील": "Tata Steel", "अडानी": "Adani Enterprises", "बजाज फाइनेंस": "Bajaj Finance",
    "भारती एयरटेल": "Bharti Airtel", "एयरटेल": "Bharti Airtel", "नेस्ले": "Nestle India", "टाइटन": "Titan", "सन फार्मा": "Sun Pharma",
    "लार्सन": "Larsen", "टेक महिंद्रा": "Tech Mahindra", "एचसीएल": "HCL Technologies", "महिंद्रा": "Mahindra", "ओएनजीसी": "ONGC", "पर्सिस्टेंट": "Persistent",
    "ज़ोमैटो": "Zomato", "जोमैटो": "Zomato", "पेटीएम": "Paytm", "आईआरसीटीसी": "IRCTC", "टाटा मोटर्स": "Tata Motors", "एनटीपीसी": "NTPC",
}.items()}
TERMS = {norm(k): v for k, v in {
    "म्यूचुअल फंड": "mutual fund", "एसआईपी": "SIP", "एक्सपेंस रेशियो": "expense ratio", "बीटा": "beta", "ड्रॉडाउन": "drawdown", "वोलैटिलिटी": "volatility",
    "इंडेक्स फंड": "index fund", "ईटीएफ": "ETF", "ओटीपी": "OTP", "केवाईसी": "KYC", "डिजिटल अरेस्ट": "digital arrest", "चक्रवृद्धि": "compounding",
    "कंपाउंडिंग": "compounding", "निफ्टी": "Nifty", "सेबी": "SEBI", "इमरजेंसी फंड": "emergency fund", "ओवरलैप": "overlap", "सेक्टर": "sector",
}.items()}


FUNDS = {norm(k): v for k, v in {
    "लार्ज कैप फंड ए": "Large Cap Fund A", "लार्ज कैप फंड": "Large Cap Fund A", "लार्ज कैप": "Large Cap Fund A",
    "ब्लूचिप फंड बी": "Bluechip Fund B", "ब्लू चिप फंड बी": "Bluechip Fund B", "ब्लूचिप फंड": "Bluechip Fund B", "ब्लूचिप": "Bluechip Fund B", "ब्लू चिप": "Bluechip Fund B",
    "फ्लेक्सी कैप फंड सी": "Flexi Cap Fund C", "फ्लेक्सी कैप": "Flexi Cap Fund C", "फ्लेक्सीकैप": "Flexi Cap Fund C",
    "निफ्टी 50 इंडेक्स फंड": "Nifty 50 Index Fund", "निफ्टी इंडेक्स फंड": "Nifty 50 Index Fund", "इंडेक्स फंड": "Nifty 50 Index Fund",
    "टेक्नोलॉजी फंड": "technology fund", "आईटी फंड": "technology fund", "बैंकिंग फंड": "banking fund", "हेल्थकेयर फंड": "healthcare fund",
    "फार्मा फंड": "healthcare fund", "कंजप्शन फंड": "consumption fund", "कंजम्पशन फंड": "consumption fund",
}.items()}


def _funds(t: str) -> list[str]:
    """Fund names said in Hindi, in the order spoken, each once."""
    hits: list[tuple[int, str]] = []
    rest = t
    for k in sorted(FUNDS, key=len, reverse=True):
        i = rest.find(k)
        if i >= 0:
            hits.append((i, FUNDS[k]))
            rest = rest[:i] + " " * len(k) + rest[i + len(k):]
    seen: list[str] = []
    for _, name in sorted(hits):
        if name not in seen:
            seen.append(name)
    return seen


def _company(t: str) -> str | None:
    for k in sorted(COMPANIES, key=len, reverse=True):
        if k in t:
            return COMPANIES[k]
    return None


def _latin(text: str) -> str:
    """English words the speaker/transcriber left in Latin letters (fund and company names)."""
    return " ".join(re.findall(r"[A-Za-z][A-Za-z&.-]*(?:\s+[A-Za-z][A-Za-z&.-]*)*", text)).strip()


# ------------------------------------------------------------------ one builder per intent
Q = list[dict[str, Any]]


def _b_fee(t: str, q: Q, raw: str) -> str:
    pct = next((x["v"] for x in q if x["kind"] == "pct"), None)
    yrs = next((x["v"] for x in q if x["kind"] == "years"), None)
    money = [x for x in q if x["kind"] == "money"]
    s = f"What does a {_fmt(pct)}% fee cost" if pct else "What does a 2% fee cost"
    if money:
        m = money[0]
        s += f" on a {_m(m['v'])} a month sip" if m["monthly"] else f" on {_m(m['v'])}"
    s += f" over {_fmt(yrs)} years" if yrs else " over 20 years"
    return s + "?"


def _b_emergency(t: str, q: Q, raw: str) -> str:
    money = sorted([x for x in q if x["kind"] == "money"], key=lambda x: x["v"])
    if len(money) >= 2:
        monthly = next((x for x in money if x["monthly"]), money[0])
        cash = max((x for x in money if x is not monthly), key=lambda x: x["v"])
        return f"How long will {_m(cash['v'])} last if I spend {_m(monthly['v'])} a month?"
    return "How long will my savings last?"


def _b_goal(t: str, q: Q, raw: str) -> str:
    money = [x for x in q if x["kind"] == "money"]
    yrs = next((x["v"] for x in q if x["kind"] == "years"), None)
    if re.search(norm("करोड़पति"), t):                    # "when will I be a crorepati" names the target itself
        sip = next((x for x in money if x["monthly"]), money[0] if money else None)
        return f"How long will it take to reach 1 crore with a {_m(sip['v'])} a month sip?" if sip else "Can I become a crorepati with a sip?"
    if not money:
        return "Will my sip reach my goal?"
    sip = next((x for x in money if x["monthly"]), min(money, key=lambda x: x["v"]) if len(money) > 1 else None)
    target = max(money, key=lambda x: x["v"])
    if sip is None or sip is target:
        return f"Can I reach {_m(target['v'])} in {_fmt(yrs or 10)} years?"
    return f"Will {_m(sip['v'])} a month reach {_m(target['v'])} in {_fmt(yrs or 10)} years?"


def _b_panic(t: str, q: Q, raw: str) -> str:
    if re.search(r"2022|ब्याज", t):
        return "What if I had sold during the 2022 rate shock?"
    if re.search(r"2023|अडानी", t):
        return "What if I had sold during the January 2023 Adani selloff?"
    return "What if I had sold during the Covid crash?"


def _b_recovery(t: str, q: Q, raw: str) -> str:
    amt = next((x for x in q if x["kind"] == "money"), None)
    a = f" {_m(amt['v'])} rupees" if amt else ""
    if re.search(norm("ओटीपी|otp|पिन|सीवीवी|पासवर्ड"), t):
        return "I shared my OTP with a stranger" + (f" and lost{a}" if amt else "")
    if re.search(norm("एनीडेस्क|anydesk|टीमव्यूअर|ऐप|एप|रिमोट|स्क्रीन"), t):
        return "I installed anydesk and they took" + (a if amt else " money")
    if re.search(norm("पुलिस|सीबीआई|कस्टम|गिरफ्तार|अरेस्ट|वारंट"), t):
        return "A man posing as police made me transfer" + (a if amt else " money")
    if re.search(norm("निवेश|ट्रेडिंग|शेयर|क्रिप्टो|मुनाफ|रिटर्न|टिप"), t):
        return "I paid" + (a if amt else "") + " into a trading app for guaranteed returns"
    if re.search(norm("लिंक|वेबसाइट|फॉर्म|भरा"), t):
        return "I clicked a link and filled my details"
    return f"I lost{a if amt else ' money'} on UPI to a fraud"


def _b_scam_help(t: str, q: Q, raw: str) -> str:
    if re.search(norm("ओटीपी|otp|पिन|सीवीवी"), t):
        return "Someone asked for my OTP on a call"
    if re.search(norm("अरेस्ट|गिरफ्तार|पुलिस|सीबीआई|कस्टम|वारंट"), t):
        return "A man on a video call says I am under digital arrest"
    if re.search(norm("केवाईसी"), t):
        return "I got a call saying my KYC will expire today"
    return "Is this call a scam?"


def _b_stress(t: str, q: Q, raw: str) -> str:
    pct = next((x["v"] for x in q if x["kind"] == "pct"), 20)
    if re.search(norm("टेक्नोलॉजी|आईटी|तकनीक"), t):
        return f"What if technology falls {_fmt(pct)}%?"
    if re.search(norm("बैंक"), t):
        return f"What if banks fall {_fmt(pct)}%?"
    return f"What if the market drops {_fmt(pct)}%?"


def _b_define(t: str, q: Q, raw: str) -> str:
    for k in sorted(TERMS, key=len, reverse=True):
        if k in t:
            return f"What is {TERMS[k]}?"
    return "What does that mean?"


def _b_overlap(t: str, q: Q, raw: str) -> str:
    names = _funds(t) or ([_latin(raw)] if len(_latin(raw).split()) >= 4 else [])
    if len(names) >= 2:
        return f"Do {names[0]} and {names[1]} overlap?"
    return "Which of my mutual funds overlap?"


def _b_buy(t: str, q: Q, raw: str) -> str:
    c = _company(t) or _latin(raw)
    return f"Should I buy more {c}?" if c else "Should I buy more?"


def _b_analyse(t: str, q: Q, raw: str) -> str:
    c = _company(t) or _latin(raw)
    return f"analyse {c}" if c else "analyse TCS"


def _b_own(t: str, q: Q, raw: str) -> str:
    names = _funds(t) or ([_latin(raw)] if _latin(raw) else [])
    return "I own " + " and ".join(names) if names else "Which mutual funds do you have?"


BUILD: dict[str, Callable[[str, Q, str], str]] = {
    "fee_drag": _b_fee, "emergency": _b_emergency, "goal": _b_goal, "panic": _b_panic, "scam_recovery": _b_recovery,
    "scam_help": _b_scam_help, "stress": _b_stress, "define": _b_define, "fund_overlap": _b_overlap, "should_buy": _b_buy,
    "analyse": _b_analyse, "my_funds_add": _b_own,
    "digest": lambda *a: "Give me my weekly digest", "xray": lambda *a: "How am I doing?", "why": lambda *a: "Why is my risk high?",
    "fix": lambda *a: "What should I sell?", "diversification": lambda *a: "Am I diversified?",
    "correlation": lambda *a: "Which of my stocks move together?", "ledger": lambda *a: "Is my ledger intact?",
    "help": lambda *a: "What can you do?", "predict": lambda *a: "Which stock will double next year?",
    "fund_list": lambda *a: "Which mutual funds do you have?", "tip_scan": lambda *a: "Is this telegram tip legit?",
    "simplify": lambda *a: "Explain that simpler", "more": lambda *a: "Tell me more",
    "chitchat": lambda t, q, r: "Thanks" if re.search(norm("धन्यवाद|शुक्रिया"), t) else "Hello",
    "my_funds_show": lambda *a: "Show my funds", "fund_vs_direct": lambda *a: "Which of my stocks are already inside the index fund?",
}

_LOSS = norm(r"(कट गए|कट गया|कट गई|कट जाने|निकल गए|निकल गया|निकाल लिए|निकाल लिया|निकाल ली|खो दिए|खो दिया|गंवा|भेज दिए|भेज दिया|बता दिया|बता दी|दे दिया|दे दी|ले लिए|ले लिया|शिकार|ठगी हो|धोखा हो|चला गया|चले गए|लूट|चुरा|ट्रांसफर कर दिए|ट्रांसफर कर दिया)")
_SCAM = norm(r"(ठगी|ठग|धोखा|धोखाधड़ी|फ्रॉड|फ्राड|स्कैम|साइबर|जालसाज|ओटीपी|एनीडेस्क|डिजिटल अरेस्ट|अरेस्ट)")

# ordered: more specific first. (intent, regex over the normalised Hindi sentence)
RULES: list[tuple[str, re.Pattern]] = [(i, re.compile(norm(p))) for i, p in [
    ("more", r"(और बताइए|विस्तार से|पूरा बताइए|पूरा पढ़ि|और विस्तार)"),
    ("simplify", r"(आसान|सरल|सीधी भाषा).{0,20}(समझा|बता|कहि)|और सरल"),
    ("digest", r"(साप्ताहिक|हफ्ते का|इस हफ्ते|सप्ताह|डाइजेस्ट|हफ्ते भर|(हफ्ते|सप्ताह).{0,12}(रिपोर्ट|सार|सारांश|अपडेट))"),
    ("fee_drag", r"(फीस|शुल्क|चार्ज|एक्सपेंस|कमीशन).{0,40}(साल|कितनी|कितना|नुकसान|पड़|खा)|(साल|कितनी).{0,30}(फीस|शुल्क)"),
    ("panic", r"(कोविड|कोरोना|क्रैश|मंदी|गिरावट|अडानी).{0,40}(बेच|निकल)|(बेच|घबरा).{0,40}(कोविड|कोरोना|क्रैश|मंदी|गिरावट)|घबराकर बेच"),
    ("emergency", r"(कितने महीने|कितने दिन|कब तक).{0,25}(चल|टिक)|इमरजेंसी (फंड|पैसा)|नौकरी (चली|छूट|जाए|जाने)|आमदनी (रुक|बंद)|तनख्वाह (रुक|बंद)"),
    ("goal", r"((बन|बना|बनी|कमा)\s*(पा|जा|सक)|तक पहुंच|लक्ष्य|करोड़पति|रिटायर|बन पाएगा|बन जाएगा|बन जाएंगे|पहुंच|कितना हो जाएगा|कितना बन|कितने बन)"),
    ("stress", r"(अगर|यदि|तो).{0,25}(गिर|टूट|क्रैश)|(गिर|टूट).{0,15}(तो|अगर)"),
    ("scam_recovery", r"(" + _SCAM + r").{0,60}(" + _LOSS + r")|(" + _LOSS + r").{0,60}(" + _SCAM + r")|(मैंने|मेरे).{0,25}(ओटीपी|पिन|पासवर्ड).{0,15}(बता|दे|भेज)|पैसे वापस"),
    ("scam_help", r"(" + _SCAM + r"|केवाईसी|लिंक|फोन पर|कॉल|(पिन|सीवीवी|पासवर्ड).{0,15}(माँग|मांग|पूछ)|(अनजान|अजनबी).{0,20}(आदमी|व्यक्ति|कॉल|फोन))"),
    ("tip_scan", r"(टिप|टेलीग्राम|व्हाट्सऐप|ग्रुप).{0,40}(सही|असली|नकली|भरोसा|सच|ठीक)"),
    ("fund_overlap", r"(फंड|म्यूचुअल|योजना).{0,40}(एक ही चीज|लगभग वही|वही चीज|एक जैसे|मिलते|समान|ओवरलैप|दोहरा|वही शेयर|एक ही शेयर|एक जैसा|मिलता)"),
    ("fund_list", r"(कौन से|कितने|कौन-से).{0,12}(म्यूचुअल )?फंड.{0,25}(हैं|दिखा|जानते|है|सकते)"),
    ("my_funds_add", r"(मेरे पास|मैंने|मेरा).{0,30}(फंड|म्यूचुअल)"),
    ("why", r"(जोखिम|रिस्क|खतरा).{0,40}(क्यों|ज्यादा|ऊंचा|इतना|कारण)"),
    ("fix", r"(क्या बेच|कौन सा शेयर बेच|कौन-सा शेयर बेच|बेचना चाहिए|क्या घटा|कम करना चाहिए|(कौन सा|कौन-सा|कौन से).{0,20}(शेयर|स्टॉक).{0,25}(घटा|बेच|हटा|कम))"),
    ("define", r"(क्या होता है|क्या है|क्या होती है|मतलब|किसे कहते|क्या होते हैं)"),
    ("should_buy", r"(खरीद|खरीदूं|खरीदूँ|खरीदना|लेना चाहिए|लूं|लूँ|निवेश करूं)"),
    ("analyse", r"(विश्लेषण|एनालिसिस|एनालाइज|रिसर्च|जांच करो|जाँच करो|पड़ताल)"),
    ("diversification", r"(बंटा|बटा|डायवर्सिफाई|विविध|एक ही उद्योग|एक ही सेक्टर|एक सेक्टर|एक उद्योग|सारा पैसा एक|एक जगह|अलग-अलग जगह|अलग अलग)"),
    ("correlation", r"(एक साथ|साथ.{0,6}चल|एक जैसे चल|साथ-साथ).{0,25}(शेयर|स्टॉक)|(शेयर|स्टॉक).{0,25}(एक साथ|साथ.{0,6}चल)"),
    ("ledger", r"(बही|रिकॉर्ड|ऑडिट|छेड़छाड़).{0,30}(सुरक्षित|बदल|ठीक|सही|छेड़)|(किसी ने|क्या).{0,20}(बदल|छेड़)"),
    ("predict", r"(कौन सा|कौन-सा).{0,10}(शेयर|स्टॉक).{0,25}(दुगना|दोगुना|डबल|बढ़ेगा|मल्टीबैगर|चढ़ेगा)|(कल|अगले (महीने|हफ्ते)).{0,15}(बाजार|निफ्टी|सेंसेक्स)"),
    ("help", r"(क्या कर सकते|क्या-क्या कर|क्या क्या कर|कैसे इस्तेमाल|कैसे इस्तमाल|मदद|कुछ भी पूछ|क्या पूछ सकत)"),
    ("xray", r"(पोर्टफोलियो|निवेश|पैसा|पैसे).{0,25}(कैसा|कैसे|सेहत|हाल|चल रहा|ठीक|कैसी)|मेरा हाल|(कैसा|कैसे|कैसी).{0,8}(चल रहा|चल रही)"),
    ("chitchat", r"^(नमस्ते|नमस्कार|हेलो|हैलो|धन्यवाद|शुक्रिया|अलविदा)"),
]]


_VOCAB: list[str] | None = None
_WORD = re.compile(r"[\u0900-\u097F]+")


def _vocab() -> list[str]:
    """Every Hindi word the rules, numbers, units, companies, funds and terms know."""
    global _VOCAB
    if _VOCAB is None:
        words: set[str] = set(NUM) | set(MULT) | UNITS_PCT | UNITS_YEAR | UNITS_MONTH
        for k in (*COMPANIES, *TERMS, *FUNDS):
            words |= set(_WORD.findall(k))
        for _, rx in RULES:
            words |= set(_WORD.findall(rx.pattern))
        _VOCAB = sorted(w for w in words if len(w) >= 3)
    return _VOCAB


# spellings speech recognisers actually produce for words that carry figures and money
VARIANTS = {norm(k): norm(v) for k, v in {
    "लाक": "लाख", "लाख्ह": "लाख", "लाक्ख": "लाख", "हाजार": "हजार", "हजारो": "हजार", "हज़ार": "हजार", "करोण": "करोड़", "कडोर": "करोड़", "करोर": "करोड़",
    "रुप्ये": "रुपये", "रुपेय": "रुपये", "रूप्ये": "रुपये", "प्रतिषत": "प्रतिशत", "प्रतिशद": "प्रतिशत", "प्रतिसत": "प्रतिशत", "परसेन्ट": "परसेंट",
    "फीज": "फीस", "फिस": "फीस", "फीश": "फीस", "फ़ीस": "फीस", "सल": "साल", "साला": "साल", "मही": "महीने", "महिने": "महीने", "महीन": "महीने",
    "पोट": "पोर्टफोलियो", "पोर्टफोलीयो": "पोर्टफोलियो", "पोर्टफलियो": "पोर्टफोलियो", "अटीपी": "ओटीपी", "ओटिपी": "ओटीपी", "ओ टी पी": "ओटीपी",
    "मुच्वल": "म्यूचुअल", "मुचुअल": "म्यूचुअल", "म्यूचल": "म्यूचुअल", "फन्द": "फंड", "फण्ड": "फंड", "फंट": "फंड", "कुन": "कौन", "कोन": "कौन",
    "किने": "कितने", "कितणे": "कितने", "चलेगे": "चलेंगे", "चलेंगी": "चलेंगे", "ठगि": "ठगी", "धोका": "धोखा", "फ्रोड": "फ्रॉड", "स्केम": "स्कैम",
}.items()}
_CONS = "कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह"
_FOLD = str.maketrans({"ख": "क", "घ": "ग", "छ": "च", "झ": "ज", "ठ": "ट", "ढ": "ड", "थ": "त", "ध": "द", "फ": "प", "भ": "ब", "ष": "स", "श": "स", "ण": "न", "ङ": "न", "ञ": "न"})


def _skel(w: str) -> str:
    """Consonant skeleton with aspirates folded: लाक and लाख, हाजार and हजार collapse together."""
    return "".join(c for c in w.translate(_FOLD) if c in _CONS or c in "".join(_FOLD.values()))


def fix_spelling(text: str) -> str:
    """Snap each unknown word to the closest known one (high bar, so ordinary words are left alone).
    Only words of 4+ letters are corrected: short words are too easily confused."""
    import difflib
    vocab, known = _vocab(), set(_vocab())
    by_skel: dict[str, set[str]] = {}
    for v in vocab:
        by_skel.setdefault(_skel(v), set()).add(v)

    def one(m: re.Match) -> str:
        w = m.group(0)
        if w in known:
            return w
        if w in VARIANTS:
            return VARIANTS[w]
        if len(w) < 4:
            return w
        c = difflib.get_close_matches(w, vocab, n=1, cutoff=0.82)
        if c:
            return c[0]
        k = _skel(w)
        hit = by_skel.get(k) if len(k) >= 3 else None
        return next(iter(hit)) if hit and len(hit) == 1 else w
    return _WORD.sub(one, norm(text))


def intent_of(text: str) -> str | None:
    t = fix_spelling(text)
    for name, rx in RULES:
        if rx.search(t):
            return name
    return None


def build(intent: str, text: str) -> str | None:
    fn = BUILD.get(intent)
    if not fn:
        return None
    fixed = fix_spelling(text)
    return fn(fixed, quantities(fixed), text)


MODEL_OK = {"xray", "why", "fix", "stress", "diversification", "correlation", "fund_overlap", "fee_drag", "emergency", "goal", "panic",
            "digest", "scam_help", "scam_recovery", "tip_scan", "predict", "ledger", "help", "define", "fund_list", "simplify"}


async def convert(text: str, use_model: bool = True) -> tuple[str | None, str]:
    """(english question or None, how it was decided). None means 'ask the person'."""
    intent = intent_of(text)
    how = "rule"
    if intent is None and use_model:
        from backend import assistant
        picked, conf = await assistant.llm_intent(text)
        if picked in MODEL_OK and conf >= assistant.LLM_MIN:
            intent, how = picked, "model"
    if intent is None:
        return None, "none"
    return build(intent, text), how
