"""The guide: say what you want, it opens the right page, asks only for what is missing, and does it.

Flow for one conversation (`cid` = one browser tab):

    "my sahukar charges 5 rupees per hundred"   -> picks the Moneylender tool
    reads what it can from the sentence          -> rate is known
    asks for the rest, one question at a time    -> "How much money did you borrow?"
    the next thing you say (typed, spoken, or a tapped chip) fills that slot
    when nothing is missing it runs the tool, opens the page with the answer showing, and says it

Everything is deterministic: figures are read by code (English and Hindi), choices come from
keyword tables, and the numbers come from `backend/rural.py`. A model is never asked to invent an
answer. The front end only has to follow the `guide` payload on each answer: go to `route` with
`params`, show `ask` (question + tappable choices), speak the line.
"""
from __future__ import annotations

import contextvars
import re
from typing import Any, Callable

from analysis import tools
from backend import rural
from backend.explain import Answer

STATE: dict[str, dict[str, Any]] = {}          # cid -> {tool, params, awaiting, tries, lang}
LAST_SCHEMES: dict[str, list[str]] = {}        # cid -> scheme ids from the last "my schemes" run
DEV = re.compile(r"[ऀ-ॿ]")
CANCEL = re.compile(r"^\s*(cancel|stop|never ?mind|forget it|leave it|exit|quit|no thanks|रद्द|रुको|छोड़ो|छोड़ दो|रहने दो|बंद करो|कैंसिल)\W*$", re.I)
SKIP = re.compile(r"^\s*(skip|none|nothing|no|nope|nahi|नहीं|कुछ नहीं|छोड़ो|कोई नहीं|नहीं है)\W*$", re.I)


def _t(lang: str):
    return (lambda en, hi: hi if lang == "hi" else en)


# ------------------------------------------------------------------------------- reading figures
def figures(text: str) -> dict[str, list[float]]:
    """money, pct, months, years and bare numbers from English or Hindi (digits or number words)."""
    if DEV.search(text):
        from backend import hindi_input as H
        q = H.quantities(H.fix_spelling(text))
        out = {k: [x["v"] for x in q if x["kind"] == k] for k in ("money", "pct", "months", "years")}
    else:
        q = tools.quantities(text)
        out = {k: [x["v"] for x in q[k]] for k in ("money", "pct", "months", "years")}
    used = sum(len(v) for v in out.values())
    bare = [float(x.replace(",", "")) for x in re.findall(r"(?<![\w.])\d[\d,]*(?:\.\d+)?", text)]
    out["bare"] = bare if not used else []
    return out


def _first_number(text: str) -> float | None:
    f = figures(text)
    for k in ("money", "bare", "pct", "months", "years"):
        if f[k]:
            return f[k][0]
    return None


# ------------------------------------------------------------------------------- choice tables
def _c(*rows):
    return [(v, en, hi, re.compile(rx, re.I)) for v, en, hi, rx in rows]


GENDER = _c(("female", "Woman", "महिला", r"\b(female|woman|girl|lady|she)\b|महिला|औरत|स्त्री|लड़की"),
            ("male", "Man", "पुरुष", r"\b(male|man|boy|he)\b|पुरुष|पुरूष|आदमी|मर्द|लड़का"),
            ("other", "Other", "अन्य", r"\b(other|third)\b|अन्य"))
WORK = _c(("farm_labour", "Farm labourer", "खेत मज़दूर", r"farm labou?r|agricultur\w* labou?r|खेत ?(में )?(मज़दूर|मजदूर)|खेतिहर"),
          ("farmer", "Farmer", "किसान", r"farmer|kisan|farming|cultivat|किसान|खेती"),
          ("labour", "Daily-wage labourer", "दिहाड़ी मज़दूर", r"labou?r|daily wage|wage|मज़दूर|मजदूर|दिहाड़ी|मज़दूरी|मजदूरी"),
          ("vendor", "Street vendor", "फेरीवाला", r"vendor|hawker|cart|street|फेरी|रेहड़ी|ठेला|पटरी"),
          ("artisan", "Artisan", "कारीगर", r"artisan|carpenter|potter|weaver|tailor|blacksmith|barber|cobbler|कारीगर|बढ़ई|कुम्हार|बुनकर|दर्ज़ी|दर्जी|लोहार|नाई|मोची"),
          ("business", "Small business", "छोटा कारोबार", r"business|shop|trader|दुकान|कारोबार|व्यापार"),
          ("other", "Something else", "कुछ और", r"other|else|कुछ और|दूसरा"))
LAND = _c(("none", "No land", "ज़मीन नहीं", r"no land|landless|don.?t have (any )?land|none|नहीं|भूमिहीन|कोई ज़मीन नहीं|ज़मीन नहीं|जमीन नहीं"),
          ("tenant", "Rented / sharecrop", "बटाई / किराए की", r"rent|tenant|sharecrop|lease|बटाई|किराए|किराये|ठेके"),
          ("own", "Own land", "अपनी ज़मीन", r"own|mine|my land|अपनी|मेरी|है"))
YESNO = _c(("unsure", "Not sure", "पक्का नहीं", r"not sure|don.?t know|unsure|maybe|पता नहीं|पक्का नहीं|शायद"),
           ("no", "No", "नहीं", r"^\W*(no|nope|nahi|nahin)\b|\bnot\b|नहीं|नही"),
           ("yes", "Yes", "हाँ", r"\b(yes|yeah|yep|yup|haan|ha|ji|sure|bpl|poor)\b|हाँ|हां|जी|गरीब|बीपीएल|है"))


def pick(table, text: str):
    for v, _en, _hi, rx in table:
        if rx.search(text):
            return v
    return None


def parse_choice(table):
    def f(text: str):
        v = pick(table, text)
        return v if v is not None else None
    return f


MONTHS = [("jan", "जनवरी"), ("feb", "फ़रवरी|फरवरी"), ("mar", "मार्च"), ("apr", "अप्रैल"), ("may", "मई"), ("jun", "जून"), ("jul", "जुलाई"),
          ("aug", "अगस्त"), ("sep", "सितंबर|सितम्बर"), ("oct", "अक्टूबर|अक्तूबर"), ("nov", "नवंबर|नवम्बर"), ("dec", "दिसंबर|दिसम्बर")]


def month_of(seg: str) -> int | None:
    low = seg.lower()
    for i, (en, hi) in enumerate(MONTHS, 1):
        if re.search(rf"\b{en}[a-z]*\b|{hi}", low):
            return i
    if re.search(r"kharif|खरीफ", low):
        return 10
    if re.search(r"\brabi\b|रबी", low):
        return 4
    if re.search(r"\bzaid\b|जायद", low):
        return 6
    return None


# ------------------------------------------------------------------------------- slot parsers
def p_money(text: str):
    f = figures(text)
    v = (f["money"] or f["bare"] or [None])[0]
    return v if v and v > 0 else None


def p_rate(text: str):
    low = text.lower()
    f = figures(text)
    if re.search(r"सैकड|hundred|saikda|sainkda|sekda|per 100|के सौ", low):
        n = (f["money"] or f["bare"] or f["pct"] or [None])[0] if not DEV.search(text) else (f["money"] or f["pct"] or f["bare"] or [None])[0]
        # in Hindi "सैकड़ा" is read as 100; the rate is the small number
        small = [x for x in (f["money"] + f["pct"] + f["bare"]) if 0 < x < 100]
        n = small[0] if small else None
        return {"rate": n, "unit": "per100_month"} if n else None
    if f["pct"]:
        yearly = re.search(r"year|annum|yearly|annual|साल|वार्षिक|सालाना", low)
        return {"rate": f["pct"][0], "unit": "pct_year" if yearly else "pct_month"}
    n = (f["bare"] or f["money"] or [None])[0]
    return {"rate": n, "unit": "per100_month"} if n and n < 100 else None


def p_months(text: str):
    f = figures(text)
    if f["months"]:
        return int(f["months"][0])
    if f["years"]:
        return int(f["years"][0] * 12)
    n = (f["bare"] or f["money"] or [None])[0]
    return int(n) if n and 0 < n <= 360 else None


def p_age(text: str):
    n = _first_number(text)
    return int(n) if n and 0 < n < 111 else None


def p_text(text: str):
    return text.strip() if len(text.strip()) >= 6 else None


ALIAS = {
    "pm_kisan": r"pm.?kisan|kisan samman|पीएम.?किसान|किसान सम्मान", "kcc": r"kisan credit|\bkcc\b|क्रेडिट कार्ड", "pmfby": r"fasal|crop insurance|फसल बीमा|फ़सल बीमा",
    "pmjjby": r"jeevan jyoti|life insurance|जीवन ज्योति|जीवन बीमा", "pmsby": r"suraksha bima|accident|सुरक्षा बीमा|दुर्घटना", "apy": r"atal pension|अटल पेंशन",
    "pmjay": r"ayushman|health (cover|insurance)|आयुष्मान|इलाज|स्वास्थ्य बीमा", "nrega": r"nrega|mgnrega|job card|100 days|मनरेगा|जॉब कार्ड", "eshram": r"e.?shram|ई.?श्रम",
    "pmsym": r"maandhan|shram yogi|मानधन|श्रम योगी", "pmay_g": r"awas|house|आवास|मकान", "ujjwala": r"ujjwala|\bgas\b|उज्ज्वला|गैस", "oap": r"\bpension|old.?age|widow|पेंशन|विधवा|वृद्ध",
    "ssy": r"sukanya|daughter|सुकन्या|बेटी", "scholar": r"scholar|छात्रवृत्ति|वजीफ", "mudra": r"mudra|business loan|मुद्रा", "vishwakarma": r"vishwakarma|विश्वकर्मा",
    "svanidhi": r"svanidhi|swanidhi|स्वनिधि", "jandhan": r"jan ?dhan|जन ?धन", "shg_nrlm": r"self.?help|\bshg\b|lakhpati|समूह|लखपति",
}
HAVE = {
    "aadhaar": r"aadhaa?r|आधार", "bank": r"bank|account|passbook|खाता|पासबुक|बैंक", "ration": r"ration|राशन", "land": r"land|khatauni|khasra|7.?12|patta|ज़मीन|जमीन|खतौनी|खसरा|पट्टा",
    "job_card": r"job ?card|जॉब ?कार्ड", "caste": r"caste|जाति", "income": r"income cert|आय प्रमाण|आय का", "photo": r"photo|फोटो|फ़ोटो", "age_proof": r"age proof|birth|school cert|आयु|जन्म",
    "disability": r"udid|disab|दिव्यांग", "shg": r"\bshg\b|self.?help|समूह", "birth_cert": r"daughter.{0,15}birth|बेटी.{0,15}जन्म", "trade_proof": r"trade|vendor cert|shop|दुकान",
    "aadhaar_mobile": r"aadhaa?r.{0,25}(mobile|phone|number)|mobile.{0,25}aadhaa?r|आधार.{0,20}(मोबाइल|फ़ोन|नंबर)",
    "bank_aadhaar": r"(linked|seeded|link|जुड़ा|लिंक).{0,25}(aadhaa?r|आधार)|(aadhaa?r|आधार).{0,25}(linked|seeded|जुड़ा|लिंक)",
    "name_match": r"name.{0,20}(same|match)|नाम.{0,20}(एक|सही|मेल)", "account_active": r"active|चालू",
}


def p_schemes(text: str):
    if re.search(r"\b(all|everything|every)\b|सब|सभी|सारी", text, re.I):
        return [s["id"] for s in rural.SCHEMES]
    ids = [k for k, rx in ALIAS.items() if re.search(rx, text, re.I)]
    return ids or None


def p_have(text: str):
    if SKIP.match(text) or re.search(r"nothing|none of|कुछ नहीं|कोई नहीं", text, re.I):
        return []
    if re.search(r"\b(all|everything)\b|सब कुछ|सभी|सारे", text, re.I):
        return list(rural.DOCS)
    out = [k for k, rx in HAVE.items() if re.search(rx, text, re.I)]
    if "bank_aadhaar" in out and "bank" not in out:
        out.append("bank")
    return out if out else None


def p_income(text: str):
    """'120000 in October and 60000 in April', 'अक्टूबर में 1.2 लाख और अप्रैल में 60 हज़ार', 'kharif 1 lakh'."""
    segs = [s for s in re.split(r"\s*(?:,|;|\band\b|\bthen\b|और|तथा|फिर)\s*", text) if s.strip()]
    rows = []
    for s in segs:
        amt = _first_number(s)
        m = month_of(s)
        if amt and amt >= 100 and m:
            rows.append({"month": m, "amount": amt, "label": ""})
    return rows or None


def p_one_offs(text: str):
    if SKIP.match(text) or re.search(r"nothing|none|कुछ नहीं|कोई नहीं|no (big|other)", text, re.I):
        return []
    return p_income(text)


def p_cost(text: str):
    return p_money(text)


def p_years(text: str):
    f = figures(text)
    n = (f["years"] or f["bare"] or f["money"] or [None])[0]
    if f["months"] and not f["years"]:
        n = f["months"][0] / 12
    return int(round(n)) if n and 0 < n <= 60 else None


def p_pct(text: str):
    f = figures(text)
    n = (f["pct"] or f["bare"] or [None])[0]
    return n if n is not None and 0 <= n <= 20 else None


MODE = _c(("monthly", "Every month (SIP)", "हर महीने (SIP)", r"month|sip|every|monthly|हर महीने|महीने|एसआईपी|मासिक"),
          ("lump", "Once, in one go", "एक बार में", r"once|one.?time|lump|single|one go|एक बार|इकट्ठा|एकमुश्त"))


# ------------------------------------------------------------------------------- tool definitions
def slot(name, en, hi, ex_en, ex_hi, parse, choices=None, optional=False):
    return dict(name=name, en=en, hi=hi, ex_en=ex_en, ex_hi=ex_hi, parse=parse, choices=choices, optional=optional)


TOOLS: dict[str, dict[str, Any]] = {
    "policy": dict(title=("Is my policy good?", "क्या मेरी पॉलिसी अच्छी है?"), kind="policy_check", slots=[
        slot("premium", "How much premium do you pay each year?", "आप साल में कितना प्रीमियम भरते हैं?", "For example: 50000", "जैसे: 50000", p_money),
        slot("pay_years", "For how many years do you pay it?", "कितने साल तक भरते हैं?", "For example: 10", "जैसे: 10", p_years),
        slot("term_years", "After how many years does the policy end and pay you?", "कितने साल बाद पॉलिसी पूरी होकर पैसा मिलता है?", "For example: 20", "जैसे: 20", p_years),
        slot("maturity", "How much will you get back at the end, in total?", "अंत में कुल कितना वापस मिलेगा?", "For example: 10 lakh", "जैसे: 10 लाख", p_money),
        slot("cover", "How much life cover (sum assured) does it give? Say skip if you do not know.", "जीवन कवर (बीमित राशि) कितना है? पता न हो तो 'छोड़ो' कहिए।", "For example: 5 lakh", "जैसे: 5 लाख", p_money, optional=True)]),
    "loan": dict(title=("Moneylender check", "साहूकार का हिसाब"), kind="moneylender", slots=[
        slot("principal", "How much money did you borrow?", "आपने कितनी रक़म उधार ली?", "For example: 50000, or 1 lakh", "जैसे: 50000, या 1 लाख", p_money),
        slot("rate", "What interest does the lender charge?", "साहूकार कितना ब्याज लेता है?", "For example: 5 rupees per hundred a month, or 24% a year", "जैसे: 5 रुपये सैकड़ा महीना, या 24% साल", p_rate),
        slot("months", "For how many months?", "कितने महीने के लिए?", "For example: 10, or 2 years", "जैसे: 10, या 2 साल", p_months)]),
    "scheme": dict(title=("Is this offer real?", "क्या ऑफ़र असली है?"), kind="scheme_check", slots=[
        slot("text", "Tell me what they promised you, in your own words.", "उन्होंने आपसे क्या वादा किया, अपने शब्दों में बताइए।",
             "For example: pay 10000 now and get 20000 in 6 months", "जैसे: अभी 10000 दो और 6 महीने में 20000 पाओ", p_text)]),
    "schemes": dict(title=("My government schemes", "मेरी सरकारी योजनाएँ"), kind="entitlements", slots=[
        slot("age", "How old is the person who will apply?", "आवेदन करने वाले की उम्र कितनी है?", "A number, for example 35", "एक संख्या, जैसे 35", p_age),
        slot("gender", "Is it a man or a woman?", "पुरुष है या महिला?", "Tap one", "एक चुनिए", parse_choice(GENDER), GENDER),
        slot("work", "What work do they do?", "वे क्या काम करते हैं?", "Tap one, or say it", "एक चुनिए या बोलिए", parse_choice(WORK), WORK),
        slot("land", "Do they have farm land?", "क्या खेती की ज़मीन है?", "Tap one", "एक चुनिए", parse_choice(LAND), LAND),
        slot("poor", "Is the household poor, with a BPL or ration card?", "क्या परिवार ग़रीब है, बीपीएल या राशन कार्ड वाला?", "Tap one", "एक चुनिए", parse_choice(YESNO), YESNO),
        slot("bank", "Do they have a bank account?", "क्या बैंक खाता है?", "Tap one", "एक चुनिए", lambda t: (lambda v: None if v is None else v == "yes")(pick(YESNO, t)),
             [c for c in YESNO if c[0] != "unsure"])]),
    "docs": dict(title=("Are my papers ready?", "क्या काग़ज़ तैयार हैं?"), kind="docs_ready", slots=[
        slot("schemes", "Which schemes do you want to apply for?", "आप किन योजनाओं के लिए आवेदन करना चाहते हैं?", "For example: PM-Kisan, Ayushman, pension, or say all",
             "जैसे: पीएम-किसान, आयुष्मान, पेंशन, या कहिए सभी", p_schemes),
        slot("have", "Which papers do you already have?", "कौन-कौन से काग़ज़ आपके पास हैं?", "For example: Aadhaar, bank passbook, ration card. Say nothing if none.",
             "जैसे: आधार, बैंक पासबुक, राशन कार्ड। कोई नहीं हो तो 'कुछ नहीं' कहिए।", p_have)]),
    "income": dict(title=("Plan my year", "मेरा साल"), kind="income_plan", slots=[
        slot("income", "When does your money come in, and how much?", "आपका पैसा कब और कितना आता है?", "For example: 120000 in October and 60000 in April",
             "जैसे: अक्टूबर में 1.2 लाख और अप्रैल में 60 हज़ार", p_income),
        slot("cost", "How much do you spend in a normal month?", "एक सामान्य महीने में कितना ख़र्च होता है?", "For example: 8000", "जैसे: 8000", p_cost),
        slot("out", "Any big one-time costs? Say the month and amount, or say none.", "कोई बड़ा एकमुश्त ख़र्च? महीना और रक़म बताइए, या 'कोई नहीं' कहिए।",
             "For example: 20000 in June for seed", "जैसे: जून में 20000 बीज के लिए", p_one_offs, optional=True)]),
}
TOOLS.update({
    "fee": dict(title=("Fee calculator", "फ़ीस कैलकुलेटर"), kind="fee_drag", route="/practice", partial_nav=False, slots=[
        slot("mode", "Do you invest once, or every month?", "आप एक बार निवेश करते हैं, या हर महीने?", "Tap one", "एक चुनिए", parse_choice(MODE), MODE),
        slot("amount", "How much do you invest?", "आप कितना निवेश करते हैं?", "For example: 10000, or 5 lakh", "जैसे: 10000, या 5 लाख", p_money),
        slot("years", "For how many years?", "कितने साल के लिए?", "For example: 20", "जैसे: 20", p_years),
        slot("fee", "What yearly fee does the fund charge, in percent?", "फ़ंड सालाना कितने प्रतिशत फ़ीस लेता है?", "For example: 2. Say skip if you do not know.", "जैसे: 2। पता न हो तो 'छोड़ो' कहिए।", p_pct, optional=True)]),
    "emergency": dict(title=("Emergency meter", "इमरजेंसी मीटर"), kind="emergency", route="/practice", partial_nav=False, slots=[
        slot("cash", "How much cash savings do you have?", "आपके पास कितनी नक़द बचत है?", "For example: 3 lakh", "जैसे: 3 लाख", p_money),
        slot("exp", "How much do you spend in a month?", "आप महीने में कितना ख़र्च करते हैं?", "For example: 40000", "जैसे: 40000", p_money)]),
    "goal": dict(title=("Goal chart", "लक्ष्य चार्ट"), kind="goal", route="/learn", partial_nav=False, slots=[
        slot("target", "How much money do you want to reach?", "आप कितनी रक़म तक पहुँचना चाहते हैं?", "For example: 50 lakh, or 1 crore", "जैसे: 50 लाख, या 1 करोड़", p_money),
        slot("monthly", "How much can you put in each month?", "आप हर महीने कितना डाल सकते हैं?", "For example: 10000", "जैसे: 10000", p_money),
        slot("years", "In how many years?", "कितने साल में?", "For example: 15", "जैसे: 15", p_years)]),
})
KIND_TO_TOOL = {v["kind"]: k for k, v in TOOLS.items()}
RURAL = {"loan", "scheme", "schemes", "docs", "income", "policy"}
HANDLER_TOOLS = {"fee", "emergency", "goal"}              # answered by an existing assistant handler
CTX: contextvars.ContextVar = contextvars.ContextVar("guide_ctx", default=None)   # a caller (WhatsApp/SMS) can pin its own context
ctx_factory: Callable[[str], Any] | None = None           # set by the app: lang -> assistant.Ctx
SENTENCE = {
    "fee": lambda p, lang: "What does a {fee}% fee cost on {amt} {when} over {years} years?".format(
        fee=f"{p['fee']:g}" if p.get("fee") is not None else "2", amt=f"{int(p['amount'])}", years=int(p["years"]),
        when="a month" if p.get("mode") == "monthly" else "invested once"),
    "emergency": lambda p, lang: f"How long will {int(p['cash'])} last if I spend {int(p['exp'])} a month?",
    "goal": lambda p, lang: f"Will {int(p['monthly'])} a month reach {int(p['target'])} in {int(p['years'])} years?",
}

PAGES = [
    ("home", "/", ("Home", "होम"), r"\bhome\b|dashboard|होम", ["How am I doing?", "What can you do?"]),
    ("portfolio", "/portfolio", ("Portfolio", "पोर्टफोलियो"), r"portfolio|holdings|पोर्टफोलियो", ["How am I doing?", "Am I diversified?"]),
    ("protect", "/protect", ("Protect", "सुरक्षा"), r"\bprotect\b|safety|scam (page|help|tools?)|सुरक्षा", ["I got a suspicious call", "I already lost money in a scam"]),
    ("rural", "/rural", ("Rural", "ग्रामीण"), r"\brural\b|village|farmer tools?|ग्रामीण|गाँव|गांव", ["Check my moneylender interest", "Which government schemes can I get?"]),
    ("learn", "/learn", ("Learn", "सीखें"), r"\blearn\b|glossary|सीख", ["What is an expense ratio?", "What if the market falls 20%?"]),
    ("practice", "/practice", ("Practice", "अभ्यास"), r"\bpractice\b|अभ्यास", ["What does a 2% fee cost over 20 years?", "Which funds overlap the most?"]),
    ("govern", "/govern", ("Govern", "नियम"), r"\bgovern\b|risk firewall|rebalanc|नियम", ["Can I buy HDFC Bank?", "Is my ledger intact?"]),
    ("research", "/research", ("Research", "शोध"), r"\bresearch\b|stock analysis|शोध", ["Analyse TCS", "Which stock will double?"]),
    ("assistant", "/assistant", ("Assistant", "सहायक"), r"\bassistant\b|\bchat\b|सहायक", ["What can you do?"]),
]
TOOL_NAV = [("policy", r"(insurance|policy) (checker|check)|policy good|बीमा (जाँच|पॉलिसी जाँच)"), ("loan", r"moneylender|money lender|sahukar|loan checker|interest checker|साहूकार"),
            ("scheme", r"(offer|scheme|scam|fraud) (checker|check|tool)|offer real|ऑफ़र|ऑफर"),
            ("schemes", r"(government|sarkari|govt) schemes?|scheme finder|सरकारी योजना"),
            ("docs", r"(documents?|papers?) (check|ready|checklist)|काग़ज़|कागज"),
            ("fee", r"fee (calculator|slider|drag|checker)|expense ratio calculator|फ़ीस कैलकुलेटर|फीस कैलकुलेटर"),
            ("emergency", r"emergency (meter|calculator|fund (meter|calculator))|इमरजेंसी मीटर"),
            ("goal", r"goal (chart|planner|calculator)|लक्ष्य चार्ट"),
            ("income", r"(income|harvest|year|season) (planner|plan)|plan my (year|season|harvest)|मेरा साल|आमदनी की योजना")]
NAV_EN = re.compile(r"^\s*(please\s+)?(take me to|go to|open|show me|navigate to|switch to|bring up|let'?s (go to|open)|start|launch|guide me (to|through))\b", re.I)
NAV_HI = re.compile(r"(खोलो|खोलिए|खोलें|ले चलो|ले चलिए|दिखाओ|दिखाइए|दिखाएँ|जाओ|जाइए|पर चलो|पर चलिए|शुरू करो|शुरू कीजिए)")


# ------------------------------------------------------------------------------- the conversation
def _ask(spec: dict, lang: str) -> dict[str, Any]:
    t = _t(lang)
    return {"slot": spec["name"], "question": t(spec["en"], spec["hi"]), "example": t(spec["ex_en"], spec["ex_hi"]), "optional": spec["optional"],
            "choices": [{"text": en, "label": hi if lang == "hi" else en} for _v, en, hi, _rx in spec["choices"]] if spec["choices"] else None}


def _route(tool: str) -> str:
    return TOOLS[tool].get("route", "/rural")


def _query(tool: str, params: dict[str, Any], run: bool) -> dict[str, str]:
    import json
    q = {"tool": tool}
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, list) and all(isinstance(x, str) for x in v):
            q[k] = ",".join(v)
        else:
            q[k] = json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict, bool)) else str(v)
    if run:
        q["run"] = "1"
    return q


def _next_slot(st: dict[str, Any]) -> dict | None:
    for sp in TOOLS[st["tool"]]["slots"]:
        if sp["name"] not in st["params"] and sp["name"] not in st.setdefault("skipped", []):
            return sp
    return None


def _prefill(tool: str, st: dict[str, Any], text: str) -> None:
    """Take whatever the opening sentence already told us."""
    p = st["params"]
    if tool == "loan":
        from backend import assistant
        rate, unit, principal, months = assistant._loan_args(text)
        if rate:
            p["rate"], p["unit"] = rate, unit
        if principal:
            p["principal"] = principal
        if months:
            p["months"] = months
    elif tool in HANDLER_TOOLS:
        from backend import assistant
        roles = tools.money_roles(text)
        q = tools.quantities(text)
        yrs = int(q["years"][0]["v"]) if q["years"] else None
        if tool == "fee":
            pf = assistant._parse_fee(text)
            if roles["monthly"] is not None:
                p["mode"], p["amount"] = "monthly", roles["monthly"]
            elif roles["lump"] is not None:
                p["mode"], p["amount"] = "lump", roles["lump"]
            if pf["years"]:
                p["years"] = pf["years"]
            if pf["fees"]:
                p["fee"] = max(pf["fees"])
        elif tool == "emergency":
            if roles["monthly"] is not None and roles["lump"] is not None:
                p["exp"], p["cash"] = roles["monthly"], roles["lump"]
            elif roles["monthly"] is not None:
                p["exp"] = roles["monthly"]
        else:
            if roles["monthly"] is not None:
                p["monthly"] = roles["monthly"]
            if yrs:
                p["years"] = yrs
            big = [m["v"] for m in q["money"] if m["v"] != roles["monthly"]]
            if big:
                p["target"] = max(big)
    elif tool == "policy":
        from backend import assistant
        a = assistant._policy_args(text)
        for k in ("premium", "pay_years", "term_years", "maturity", "cover"):
            if k in a:
                p[k] = a[k]
    elif tool == "scheme":
        if len(text.strip()) > 25 and re.search(r"\d|scheme|offer|double|chit|गारंटी|दोगुना|योजना", text, re.I):
            p["text"] = text.strip()
    elif tool == "schemes":
        m = re.search(r"(\d{2})\s*(?:years?|yrs?|साल|वर्ष)", text, re.I)
        if m:
            p["age"] = int(m.group(1))
        for name, table in (("gender", GENDER), ("work", WORK), ("land", LAND)):
            v = pick(table, text)
            if v and (name != "land" or re.search(r"land|ज़मीन|जमीन|खेत", text, re.I)) and (name != "gender" or re.search(r"\b(male|female|man|woman|i am a (man|woman))\b|पुरुष|महिला", text, re.I)):
                p[name] = v
    elif tool == "docs":
        ids = [k for k, rx in ALIAS.items() if re.search(rx, text, re.I)]
        if ids and len(ids) < len(ALIAS):
            p["schemes"] = ids
    elif tool == "income":
        rows = p_income(text)
        if rows:
            p["income"] = rows


def _finish(cid: str, st: dict[str, Any], lang: str) -> dict[str, Any]:
    """Every needed answer is in: run the tool and describe what the page will show."""
    t = _t(lang)
    tool, p = st["tool"], st["params"]
    say, params = "", dict(p)
    if tool == "loan":
        r = rural.loan_cost(p["principal"], p["rate"], p.get("unit", "per100_month"), p["months"], "interest_only", lang)
        money = tools.inr_hi if lang == "hi" else tools.inr
        say = (f"{r['headline']} " + t(f"On {money(p['principal'])} for {p['months']} months you pay {money(r['interest'])} interest, {money(r['total'])} in all. ",
                                        f"{money(p['principal'])} पर {p['months']} महीने में {money(r['interest'])} ब्याज लगेगा, कुल {money(r['total'])}। ") + r["verdict"])
    elif tool == "policy":
        r = rural.policy_check(p["premium"], p["pay_years"], p["term_years"], p["maturity"], p.get("cover"), None, "", lang)
        say = f"{r['headline']} {r['verdict']}"
    elif tool == "scheme":
        r = rural.scheme_check(p["text"], lang=lang)
        say = f"{r['verdict']} " + (r["flags"][0]["text"] if r["flags"] else "")
    elif tool == "schemes":
        prof = {"age": p.get("age"), "gender": p.get("gender", "any"), "work": p.get("work", "other"), "land": p.get("land", "none"),
                "poor": p.get("poor", "unsure"), "bank": p.get("bank", True), "lpg": True}
        r = rural.entitlements(prof, lang)
        LAST_SCHEMES[cid] = [s["id"] for s in r["schemes"] if s["status"] == "likely"]
        names = ", ".join(s["name"] for s in r["schemes"][:4])
        say = t(f"You may qualify for {r['count']} schemes, including {names}. I have listed where to apply and what to carry.",
                f"आप {r['count']} योजनाओं के हक़दार हो सकते हैं, जैसे {names}। कहाँ आवेदन करना है और क्या ले जाना है, मैंने सूची में दिखा दिया है।")
    elif tool == "docs":
        r = rural.readiness(p["schemes"], p.get("have", []), lang)
        say = r["summary"]
        params = {"schemes": list(p["schemes"]), "have": list(p.get("have", []))}
    elif tool == "income":
        r = rural.income_plan(p["income"], p["cost"], p.get("out") or [], 0, 36, lang)
        say = f"{r['headline']} {r['tips'][0] if r['tips'] else ''}"
        params = {"income": p["income"], "cost": p["cost"], "out": p.get("out") or []}
    elif tool in HANDLER_TOOLS:
        from backend import assistant
        ctx = CTX.get() or (ctx_factory(lang) if ctx_factory else None)
        sentence = SENTENCE[tool](p, lang)
        a = assistant.HANDLERS[TOOLS[tool]["kind"]](sentence, ctx) if ctx else None
        say = (a.headline + (" " + a.bullets[0] if a and a.bullets else "")) if a else ""
        vis = (a.visual or {}).get("params", {}) if a else {}
        params = vis or {k: v for k, v in p.items()}
        STATE.pop(cid, None)
        nxt = {"fee": ["How long will 3 lakh last if I spend 40000 a month?", "Will 10000 a month reach 50 lakh in 15 years?"],
               "emergency": ["What does a 2% fee cost over 20 years?", "Will 10000 a month reach 50 lakh in 15 years?"],
               "goal": ["What does a 2% fee cost over 20 years?", "How long will 3 lakh last if I spend 40000 a month?"]}[tool]
        return {"tool": tool, "route": _route(tool), "label": t(*TOOLS[tool]["title"]), "navigate": True, "done": True, "ask": None,
                "params": _query(tool, params, True), "say": say, "next": nxt, "step": None}
    STATE.pop(cid, None)
    nxt = {"policy": ["Check my moneylender interest", "Which government schemes can I get?"],
           "loan": ["Which government schemes can I get?", "Plan my money around the harvest"],
           "scheme": ["Check my moneylender interest", "I already lost money in a scam"],
           "schemes": ["Are my papers ready?", "Check my moneylender interest"],
           "docs": ["Which government schemes can I get?", "Check my moneylender interest"],
           "income": ["Check my moneylender interest", "Which government schemes can I get?"]}[tool]
    return {"tool": tool, "route": _route(tool), "label": t(*TOOLS[tool]["title"]), "navigate": True, "done": True, "ask": None,
            "params": _query(tool, params, True), "say": say, "next": nxt, "step": None}


def _payload(cid: str, st: dict[str, Any], lang: str, navigate: bool) -> dict[str, Any]:
    t = _t(lang)
    spec = _next_slot(st)
    if spec is None:
        return _finish(cid, st, lang)
    slots = TOOLS[st["tool"]]["slots"]
    st["awaiting"] = spec["name"]
    return {"tool": st["tool"], "route": _route(st["tool"]), "label": t(*TOOLS[st["tool"]]["title"]), "navigate": navigate, "done": False,
            "ask": _ask(spec, lang), "params": _query(st["tool"], st["params"], False), "say": None,
            "step": [slots.index(spec) + 1, len(slots)]}


def begin(tool: str, text: str, lang: str, cid: str) -> dict[str, Any]:
    st = {"tool": tool, "params": {}, "awaiting": None, "tries": 0, "lang": lang, "skipped": []}
    if tool == "docs" and LAST_SCHEMES.get(cid):
        st["params"]["schemes"] = list(LAST_SCHEMES[cid])
    _prefill(tool, st, text)
    STATE[cid] = st
    return _payload(cid, st, lang, navigate=True)


def forget(cid: str) -> None:
    """Drop everything remembered about one conversation (shared-device "next person")."""
    STATE.pop(cid, None)
    LAST_SCHEMES.pop(cid, None)


def active(cid: str) -> bool:
    return bool(STATE.get(cid, {}).get("awaiting"))


def fill(cid: str, text: str, lang: str) -> dict[str, Any] | None:
    """Use `text` as the answer to the open question. None means: not an answer, route it normally."""
    st = STATE.get(cid)
    if not st or not st.get("awaiting"):
        return None
    t = _t(lang)
    if CANCEL.match(text):
        STATE.pop(cid, None)
        return {"cancelled": True, "say": t("Okay, I have stopped. Ask me anything when you are ready.", "ठीक है, मैंने रोक दिया। जब चाहें कुछ भी पूछिए।"), "done": True, "ask": None, "navigate": False, "route": None, "tool": st["tool"], "params": {}}
    spec = next(s for s in TOOLS[st["tool"]]["slots"] if s["name"] == st["awaiting"])
    if spec["optional"] and SKIP.match(text):
        st["skipped"].append(spec["name"])
        st["tries"] = 0
        return _payload(cid, st, lang, navigate=True)
    val = spec["parse"](text)
    if val is None or (val == [] and spec["name"] not in ("have", "out")):
        # Not an answer. A different clear question gets answered instead of being trapped here.
        from backend import assistant
        if st["tries"] >= 1 and assistant.rule_intent(text):
            STATE.pop(cid, None)
            return None
        st["tries"] += 1
        a = _ask(spec, lang)
        a["question"] = t("I did not catch that. ", "मैं समझ नहीं पाया। ") + a["question"]
        return {"tool": st["tool"], "route": _route(st["tool"]), "label": t(*TOOLS[st["tool"]]["title"]), "navigate": False, "done": False, "ask": a,
                "params": _query(st["tool"], st["params"], False), "say": None, "step": None, "retry": True}
    if spec["name"] == "rate" and isinstance(val, dict):
        st["params"]["rate"], st["params"]["unit"] = val["rate"], val["unit"]
    elif spec["name"] == "bank":
        st["params"]["bank"] = bool(val)
    else:
        st["params"][spec["name"]] = val
    st["tries"] = 0
    return _payload(cid, st, lang, navigate=TOOLS[st["tool"]].get("partial_nav", True))


# ------------------------------------------------------------------------------- opening a page
def navigate(text: str, lang: str, cid: str) -> dict[str, Any] | None:
    """'open the protect page', 'take me to the moneylender check', 'सुरक्षा पेज खोलिए'."""
    s = text.strip()
    if len(s.split()) > 6:
        return None
    if not (NAV_EN.search(s) or NAV_HI.search(s)):
        return None
    for tool, rx in TOOL_NAV:
        if re.search(rx, s, re.I):
            return begin(tool, "", lang, cid)
    t = _t(lang)
    for _id, route, title, rx, ideas in PAGES:
        if re.search(rx, s, re.I):
            STATE.pop(cid, None)
            return {"tool": None, "route": route, "label": t(*title), "navigate": True, "done": True, "ask": None, "params": {},
                    "say": t(f"Opening {title[0]}. You can ask me from here.", f"{title[1]} खोल रहा हूँ। आप यहीं से मुझसे पूछ सकते हैं।"), "next": ideas, "step": None}
    return None


def to_answer(g: dict[str, Any], lang: str) -> Answer:
    """The chat/voice answer that carries the payload. The front end follows `data.guide`."""
    t = _t(lang)
    if g.get("ask"):
        a = g["ask"]
        head = a["question"]
        bullets = [a["example"]] if a.get("example") else []
        if g.get("step"):
            bullets.append(t(f"Step {g['step'][0]} of {g['step'][1]}. Say \"cancel\" to stop.", f"चरण {g['step'][0]}/{g['step'][1]}। रोकने के लिए \"रद्द\" कहिए।"))
        chips = a.get("choices") or []
        ans = Answer(headline=head, bullets=bullets, kind="guide", follow_ups=[c["text"] for c in chips],
                     follow_ups_hi=[c["label"] for c in chips] if lang == "hi" else [])
    else:
        nxt = g.get("next") or []
        ans = Answer(headline=g.get("say") or "", kind="guide", follow_ups=list(nxt))
        if g.get("label") and g.get("route"):
            ans.bullets = [t(f"I opened {g['label']} so you can see it.", f"मैंने {g['label']} खोल दिया है ताकि आप देख सकें।")]
    ans.lang = lang
    ans.speech = ans.headline
    ans.data = {"guide": g, "intent": "guide"}
    return ans


def intercept(text: str, lang: str, cid: str) -> Answer | None:
    """Called first for every typed or spoken line."""
    if active(cid):
        if (NAV_EN.search(text) or NAV_HI.search(text)) and (g := navigate(text, lang, cid)) is not None:
            return to_answer(g, lang)                       # "open X" while a question is open: go there instead
        g = fill(cid, text, lang)
        if g is not None:
            return to_answer(g, lang)
    g = navigate(text, lang, cid)
    return to_answer(g, lang) if g else None


def done_from_answer(tool: str, answer: Answer, lang: str) -> dict[str, Any]:
    """The handler already had every figure: open its page with those figures and the result showing."""
    t = _t(lang)
    vis = answer.visual or {}
    return {"tool": tool, "route": "/" + vis.get("page", "").lstrip("/") if vis.get("page") else _route(tool), "label": t(*TOOLS[tool]["title"]),
            "navigate": True, "done": True, "ask": None, "params": _query(tool, vis.get("params", {}), True), "say": answer.headline, "next": [], "step": None}
