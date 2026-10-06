"""Tools for rural and low-income households: five things that cost real money when missing.

  A1 loan_cost      what a moneylender's "rate" really is per year, and what switching would save
  A2 scheme_check   red-flag check of a "double your money" / chit / app offer
  B1 entitlements   which government schemes a household probably qualifies for
  B2 readiness      which documents are missing for the schemes picked, and the one thing to fix first
  C1 income_plan    month-by-month plan for lumpy income (harvest, season, daily wage)

Same rules as the rest of the app: every number is computed here, never by a model; text is written
once by hand in English and Hindi; nothing is invented. Scheme facts change, so each carries the
official place to confirm and the data carries a `CHECKED` date; the screen says to confirm there.
"""
from __future__ import annotations

import math
import re
from typing import Any

CHECKED = "2026-10"       # when the scheme list below was last reviewed
MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTHS_HI = ["जन", "फ़र", "मार्च", "अप्रै", "मई", "जून", "जुला", "अग", "सित", "अक्टू", "नव", "दिस"]


def _tr(lang: str):
    return (lambda en, hi: hi if lang == "hi" else en)


def _inr(x: float, lang: str = "en") -> str:
    x = float(x)
    sign = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1e7:
        v, u = x / 1e7, "करोड़ रुपये" if lang == "hi" else "crore"
        return f"{sign}{v:.2f} {u}" if lang == "hi" else f"{sign}₹{v:.2f} {u}"
    if x >= 1e5:
        v = x / 1e5
        return f"{sign}{v:.2f} लाख रुपये" if lang == "hi" else f"{sign}₹{v:.2f} lakh"
    return f"{sign}₹{x:,.0f}"


# =============================================================================== A1 loans
LEGAL_NOTE = {
    "en": "Ask whether the lender is licensed under your state's Money Lenders Act, and ask for a written record of every payment. Threats or harassment to collect a debt are not allowed; you can complain to the police.",
    "hi": "पूछिए कि साहूकार आपके राज्य के साहूकारी क़ानून में लाइसेंस वाला है या नहीं, और हर भुगतान की लिखित रसीद माँगिए। वसूली के लिए धमकी या परेशान करना मना है; आप पुलिस में शिकायत कर सकते हैं।",
}
# Alternatives: (id, English, Hindi, typical yearly rate %, note). Rates are typical ranges to ask
# about, not offers; the screen says so.
ALTERNATIVES = [
    ("kcc", "Kisan Credit Card (farmers, up to ₹3 lakh)", "किसान क्रेडिट कार्ड (किसानों के लिए, ₹3 लाख तक)", 4.0,
     "about 7% a year, and about 4% if repaid on time under the interest-help scheme; ask your bank"),
    ("shg", "Self-help group / bank-linked SHG loan", "स्वयं सहायता समूह / बैंक से जुड़ा SHG ऋण", 12.0,
     "usually 12-24% a year, decided by the group"),
    ("bank", "Bank or co-operative loan", "बैंक या सहकारी समिति का ऋण", 12.0,
     "usually 9-15% a year"),
]


def loan_cost(principal: float, rate: float, unit: str = "per100_month", months: int = 12,
              mode: str = "interest_only", lang: str = "en") -> dict[str, Any]:
    """`unit`: per100_month ("₹5 per ₹100 per month", same as 5% a month), pct_month, pct_year,
    rs_per_month (rupees of interest each month on the whole loan).
    `mode`: interest_only (interest paid every month, principal at the end), bullet_simple (all at the
    end, interest not added on), bullet_compound (interest added to the loan each month, the dreaded
    "byaj pe byaj")."""
    t = _tr(lang)
    principal, months = max(0.0, float(principal)), max(1, int(months))
    if unit == "pct_year":
        m = (float(rate) / 100) / 12
    elif unit == "rs_per_month":
        m = float(rate) / principal if principal else 0.0
    else:                                    # per100_month and pct_month are the same number
        m = float(rate) / 100
    simple_year = m * 12 * 100
    eff_year = ((1 + m) ** 12 - 1) * 100 if mode == "bullet_compound" else simple_year
    if mode == "bullet_compound":
        total = principal * (1 + m) ** months
    else:
        total = principal * (1 + m * months)
    interest = total - principal
    double_months = (math.log(2) / math.log(1 + m)) if (mode == "bullet_compound" and m > 0) else (1 / m if m > 0 else None)
    alts = []
    for aid, en, hi, yr, note in ALTERNATIVES:
        cost = principal * (yr / 100) * (months / 12)
        alts.append({"id": aid, "name": hi if lang == "hi" else en, "yearly_pct": yr, "interest": round(cost),
                     "saves": round(max(0.0, interest - cost)), "note": note})
    band = "red" if eff_year >= 36 else "amber" if eff_year >= 18 else "green"
    verdict = {
        "red": t("This is very expensive. Borrowing at this rate usually leaves the family poorer even if the money is repaid on time.",
                 "यह बहुत महँगा है। इस दर पर समय से चुकाने के बाद भी परिवार अक्सर पहले से ग़रीब रह जाता है।"),
        "amber": t("This is expensive. A bank, co-operative or group loan is likely cheaper.", "यह महँगा है। बैंक, सहकारी समिति या समूह का ऋण शायद सस्ता पड़ेगा।"),
        "green": t("This is within the normal range for a loan.", "यह ऋण की सामान्य दर के अंदर है।"),
    }[band]
    head = t(f"{rate:g} {'rupees per 100 a month' if unit == 'per100_month' else '% a month' if unit == 'pct_month' else '% a year' if unit == 'pct_year' else 'rupees a month'} is {eff_year:.0f}% a year.",
             f"{rate:g} {'रुपये सैकड़ा महीना' if unit == 'per100_month' else '% महीना' if unit == 'pct_month' else '% साल' if unit == 'pct_year' else 'रुपये महीना'} यानी साल का {eff_year:.0f}%।")
    return {"principal": principal, "months": months, "monthly_pct": round(m * 100, 3), "yearly_pct": round(eff_year, 1),
            "interest": round(interest), "total": round(total), "mode": mode,
            "double_months": None if double_months is None else round(double_months, 1),
            "band": band, "headline": head, "verdict": verdict, "alternatives": alts, "legal": LEGAL_NOTE[lang],
            "interest_share": round(interest / principal * 100, 1) if principal else 0.0}


# =============================================================================== A2 schemes (offers)
# Each flag: id -> (weight, English, Hindi, regex over lower-cased text incl. Devanagari)
FLAGS: dict[str, tuple[int, str, str, str]] = {
    "guaranteed": (25, "Promises guaranteed or fixed high returns. No real investment can guarantee profit.",
                   "पक्के या तय ऊँचे मुनाफ़े का वादा। कोई असली निवेश मुनाफ़े की गारंटी नहीं दे सकता।",
                   r"guarantee|assured|fixed return|sure.?shot|100 ?%|risk.?free|no risk|without risk|गारंटी|पक्का मुनाफ़|पक्का मुनाफा|तय मुनाफ|बिना जोखिम|जोखिम नहीं"),
    "double": (30, "Says your money will double or multiply quickly.",
               "कहता है कि पैसा जल्दी दोगुना या कई गुना हो जाएगा।",
               r"double|doubl|triple|\b[2-9] ?x\b|दोगुना|दुगना|दुगुना|तिगुना|डबल|कई गुना"),
    "recruit": (30, "Pays you for bringing in other people (a chain). That is how pyramid schemes work.",
                "दूसरों को जोड़ने पर कमीशन (चेन)। पिरामिड योजनाएँ इसी तरह चलती हैं।",
                r"refer|recruit|add (\d+ )?(members|people|friends)|bring (\d+ |your |more )?(friends|members|people|relatives)|join (your )?(friends|family)|downline|chain|network marketing|member.?ship|जोड़|रेफ़र|रेफर|सदस्य बनाइ|चेन|नेटवर्क"),
    "joining_fee": (15, "Asks for a joining, registration or 'release' fee first.",
                    "पहले जॉइनिंग, रजिस्ट्रेशन या 'रिलीज़' फ़ीस माँगता है।",
                    r"joining fee|registration fee|processing fee|release fee|pay first|advance|deposit first|जॉइनिंग|रजिस्ट्रेशन फ़ीस|रजिस्ट्रेशन फीस|पहले पैसे|एडवांस|अग्रिम"),
    "daily_return": (25, "Promises a return every day or week. Real returns do not arrive like a salary.",
                     "रोज़ या हर हफ़्ते कमाई का वादा। असली निवेश वेतन की तरह नहीं मिलता।",
                     r"daily (return|income|profit)|per day|every day|weekly (return|income|profit)|रोज़ाना|रोजाना|हर रोज़|हर रोज|हर दिन|प्रतिदिन|हर हफ्ते|हर हफ़्ते"),
    "pressure": (15, "Pressure to decide now ('last chance', 'only today', 'few seats left').",
                 "अभी फ़ैसला करने का दबाव ('आख़िरी मौक़ा', 'सिर्फ़ आज', 'कुछ ही सीटें')।",
                 r"last chance|only today|today only|limited (seats|offer|slots|period)|hurry|expires|now or never|आखिरी मौका|आख़िरी मौक़ा|सिर्फ आज|सिर्फ़ आज|जल्दी करें|सीमित"),
    "secret": (15, "Asks you to keep it secret or not to check with family or the bank.",
               "इसे गुप्त रखने या परिवार/बैंक से न पूछने को कहता है।",
               r"keep (it )?secret|don.?t tell|do not tell|confidential|किसी को मत बता|गुप्त|राज़ रख|राज रख"),
    "personal_account": (20, "Asks you to pay cash or into a personal account or UPI ID, not a registered company.",
                         "नक़द या किसी व्यक्ति के खाते/UPI में पैसा माँगता है, पंजीकृत कंपनी में नहीं।",
                         r"cash only|personal account|send (to|on) (my )?(phone ?pe|gpay|paytm|upi)|pay (me )?on (phone ?pe|gpay|paytm)|नक़द में|नकद में|मेरे खाते|मेरे नंबर पर|फोन ?पे|गूगल ?पे"),
    "prize": (30, "Says you won a prize, lottery or gift and must pay to claim it.",
              "कहता है कि आपने इनाम या लॉटरी जीती है और लेने के लिए पैसे देने होंगे।",
              r"lottery|you have won|you won|prize|lucky draw|gift|लॉटरी|इनाम|जीत लिया|लकी ड्रॉ|ईनाम"),
    "app_trading": (15, "An app or group promises trading profits (crypto, forex, 'VIP' tips). Fake apps show fake profits and block withdrawals.",
                    "ऐप या ग्रुप ट्रेडिंग मुनाफ़े का वादा करता है (क्रिप्टो, फ़ॉरेक्स, 'VIP' टिप्स)। नक़ली ऐप नक़ली मुनाफ़ा दिखाते हैं और पैसा निकालने नहीं देते।",
                    r"crypto|bitcoin|forex|trading app|vip (group|tips)|telegram|usdt|क्रिप्टो|बिटकॉइन|फॉरेक्स|फ़ॉरेक्स|टेलीग्राम|ट्रेडिंग ऐप"),
    "no_paper": (10, "No written agreement or registration is mentioned.",
                 "किसी लिखित क़रार या पंजीकरण का ज़िक्र नहीं।",
                 r"no (paper|document|agreement)|without (paper|document|agreement)|verbal|कोई कागज़|कोई कागज|बिना कागज़|बिना कागज|मौखिक"),
    "land_gold": (10, "Promises a plot, gold or goods in return for a monthly instalment: check who actually holds them.",
                  "मासिक किस्त के बदले प्लॉट, सोना या सामान का वादा: जाँचिए कि वह असल में किसके पास है।",
                  r"plot|gold coin|gold scheme|chit|committee|kameti|किश्त|प्लॉट|सोने|चिट फंड|चिट फ़ंड|कमेटी|कमिटी"),
}
VERIFY = [
    ("SEBI: sebi.gov.in → Intermediaries (is the adviser or platform registered?)", "SEBI: sebi.gov.in → Intermediaries (क्या सलाहकार/प्लेटफ़ॉर्म पंजीकृत है?)"),
    ("RBI: sachet.rbi.org.in (is it allowed to take deposits? report illegal deposit schemes)", "RBI: sachet.rbi.org.in (क्या जमा लेने की अनुमति है? ग़ैरक़ानूनी योजना की शिकायत करें)"),
    ("Company: mca.gov.in (is the company real and when was it formed?)", "कंपनी: mca.gov.in (क्या कंपनी असली है और कब बनी?)"),
    ("Cyber fraud: call 1930 or cybercrime.gov.in; otherwise your local police station", "साइबर ठगी: 1930 पर फ़ोन करें या cybercrime.gov.in; नहीं तो अपना थाना"),
]
SAFE_BENCHMARK = 7.0   # yearly % of a bank fixed deposit: the benchmark a promise is compared with
SAFE_YEARLY = [("Bank fixed deposit", "बैंक एफ़डी", 7.0), ("Post Office savings schemes", "डाकघर की बचत योजनाएँ", 7.5)]


def implied_return(put: float, get: float, months: float) -> float | None:
    """Yearly % return implied by 'pay `put`, receive `get` after `months`'."""
    if put <= 0 or months <= 0 or get <= 0:
        return None
    return ((get / put) ** (12 / months) - 1) * 100


def scheme_check(text: str = "", put: float | None = None, get: float | None = None,
                 months: float | None = None, lang: str = "en") -> dict[str, Any]:
    t = _tr(lang)
    low = (text or "").lower()
    if put is None and get is None and months is None and text:
        # "pay 10000, get 20000 in 6 months" written in words: read the figures from the sentence
        try:
            from analysis import tools          # not available inside the offline (in-browser) copy
            q = tools.quantities(text)
            money = [x["v"] for x in q["money"] if x["v"] >= 100]
            mo = q["months"][0]["v"] if q["months"] else (q["years"][0]["v"] * 12 if q["years"] else None)
        except ImportError:
            nums = [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*(?:\.\d+)?", text)]
            money = [x for x in nums if x >= 100]
            m = re.search(r"(\d+(?:\.\d+)?)\s*(months?|years?|महीने|साल)", text, re.I)
            mo = (float(m.group(1)) * (12 if re.match(r"y|सा", m.group(2), re.I) else 1)) if m else None
        if len(money) >= 2 and mo and money[1] > money[0]:
            put, get, months = money[0], money[1], mo
    hits = [(fid, w, en, hi) for fid, (w, en, hi, rx) in FLAGS.items() if re.search(rx, low)]
    ret = implied_return(put, get, months) if (put and get and months) else None
    # Each signal is a probability-like weight p (0 to 1). They combine as 1 - prod(1 - p), so a second
    # warning adds less than the first and the score cannot jump on one word. Return signal is smooth:
    # 0 at the safe benchmark (7% a year), rising on a log scale to 60 points at 100% a year.
    parts = [(fid, w, hi if lang == "hi" else en) for fid, w, en, hi in hits]
    rflags = []
    if ret is not None and ret > SAFE_BENCHMARK:
        pts = min(60.0, 50.0 * math.log(ret / SAFE_BENCHMARK) / math.log(100.0 / SAFE_BENCHMARK))
        if pts >= 1:
            parts.append(("returns", round(pts), t(f"The promise works out to {ret:,.0f}% a year against about {SAFE_BENCHMARK:g}% from a bank deposit.",
                                                   f"यह वादा साल के {ret:,.0f}% के बराबर है, जबकि बैंक जमा लगभग {SAFE_BENCHMARK:g}% देती है।")))
            rflags.append(parts[-1][2])
    keep = 1.0
    for _fid, w, _txt in parts:
        keep *= 1 - min(w, 100) / 100
    score = int(round(100 * (1 - keep)))
    breakdown = [{"id": fid, "points": int(round(w)), "text": txt} for fid, w, txt in parts]
    score = min(100, score)
    level = "red" if score >= 60 else "amber" if score >= 30 else "green"
    verdict = {
        "red": t("Very likely a scam. Do not pay anything.", "बहुत संभव है कि यह ठगी है। कुछ भी पैसा मत दीजिए।"),
        "amber": t("High risk. Check it properly before paying anything.", "ज़्यादा जोखिम है। कोई पैसा देने से पहले ठीक से जाँचिए।"),
        "green": t("No common red flag found in what you wrote. That is not proof it is safe: still verify it.", "आपके लिखे में कोई आम चेतावनी नहीं मिली। इसका मतलब यह नहीं कि यह सुरक्षित है: फिर भी जाँचिए।"),
    }[level]
    return {"score": score, "level": level, "verdict": verdict, "implied_yearly_pct": None if ret is None else round(ret, 1),
            "breakdown": breakdown,
            "flags": [{"id": f, "text": hi if lang == "hi" else en, "weight": w} for f, w, en, hi in hits] + [{"id": "returns", "text": s, "weight": 0} for s in rflags],
            "compare": [{"name": hi if lang == "hi" else en, "yearly_pct": r} for en, hi, r in SAFE_YEARLY],
            "verify": [hi if lang == "hi" else en for en, hi in VERIFY],
            "rule": t("A promise of high, fixed or quick returns is the one thing every scam has in common. Never pay to receive money.",
                      "ऊँचे, तय या जल्दी मुनाफ़े का वादा हर ठगी में एक जैसा होता है। पैसे पाने के लिए कभी पैसे मत दीजिए।")}


# =============================================================================== B1/B2 entitlements
# doc ids -> (English, Hindi, how to get it if missing)
DOCS: dict[str, tuple[str, str, str, str]] = {
    "aadhaar": ("Aadhaar card", "आधार कार्ड", "Apply or correct at an Aadhaar centre (uidai.gov.in).", "आधार केंद्र पर बनवाइए या सुधरवाइए (uidai.gov.in)।"),
    "aadhaar_mobile": ("Mobile number linked to Aadhaar", "आधार से जुड़ा मोबाइल नंबर", "Visit an Aadhaar centre and update the mobile number; OTPs depend on it.", "आधार केंद्र जाकर मोबाइल नंबर अपडेट करवाइए; OTP इसी पर आते हैं।"),
    "bank": ("Bank account (in your own name)", "बैंक खाता (अपने नाम से)", "Open a Jan Dhan account at any bank branch: zero balance, needs only Aadhaar.", "किसी भी बैंक शाखा में जन धन खाता खुलवाइए: शून्य बैलेंस, सिर्फ़ आधार चाहिए।"),
    "bank_aadhaar": ("Bank account linked (seeded) with Aadhaar for benefit transfers", "आधार से जुड़ा (सीडेड) बैंक खाता", "Ask the bank to link Aadhaar for DBT and give you a written acknowledgement. Check status on myaadhaar.uidai.gov.in → Bank Seeding Status.", "बैंक से DBT के लिए आधार जुड़वाइए और लिखित पावती लीजिए। स्थिति myaadhaar.uidai.gov.in → Bank Seeding Status पर देखिए।"),
    "name_match": ("Same spelling of your name on Aadhaar, bank and other papers", "आधार, बैंक और बाक़ी काग़ज़ों में नाम की एक जैसी वर्तनी", "Correct the one that differs (usually the bank passbook) before applying; mismatches are the commonest reason payments fail.", "जो अलग है उसे (अक्सर बैंक पासबुक) आवेदन से पहले सुधरवाइए; नाम का मेल न होना भुगतान रुकने का सबसे आम कारण है।"),
    "account_active": ("Bank account is active (not dormant)", "बैंक खाता चालू है (निष्क्रिय नहीं)", "Make a small deposit or withdrawal; ask the bank to reactivate a dormant account.", "थोड़ी रक़म जमा/निकालिए; निष्क्रिय खाता बैंक से दोबारा चालू करवाइए।"),
    "land": ("Land record (khasra / khatauni / 7-12 / patta)", "ज़मीन का रिकॉर्ड (खसरा / खतौनी / 7-12 / पट्टा)", "Get a copy from the tehsil / revenue office or your state's land-record website.", "तहसील/राजस्व कार्यालय या राज्य की भूलेख वेबसाइट से प्रति लीजिए।"),
    "ration": ("Ration card", "राशन कार्ड", "Apply at the food and civil supplies office or through your panchayat / CSC.", "खाद्य एवं नागरिक आपूर्ति कार्यालय, पंचायत या CSC से आवेदन कीजिए।"),
    "job_card": ("MGNREGA job card", "मनरेगा जॉब कार्ड", "Apply at the gram panchayat; it must be issued within 15 days.", "ग्राम पंचायत में आवेदन कीजिए; 15 दिन में बनना चाहिए।"),
    "caste": ("Caste certificate (SC / ST / OBC)", "जाति प्रमाणपत्र (SC / ST / OBC)", "Apply at the tehsil / e-district portal.", "तहसील या ई-डिस्ट्रिक्ट पोर्टल पर आवेदन कीजिए।"),
    "income": ("Income certificate", "आय प्रमाणपत्र", "Apply at the tehsil / e-district portal.", "तहसील या ई-डिस्ट्रिक्ट पोर्टल पर आवेदन कीजिए।"),
    "age_proof": ("Age proof (Aadhaar / school certificate / birth certificate)", "आयु प्रमाण (आधार / स्कूल प्रमाणपत्र / जन्म प्रमाणपत्र)", "Aadhaar usually works; otherwise the school or municipal office.", "आमतौर पर आधार चलता है; नहीं तो स्कूल या नगर निकाय।"),
    "disability": ("Disability certificate / UDID card", "दिव्यांगता प्रमाणपत्र / UDID कार्ड", "Apply at the district hospital / swavlambancard.gov.in.", "ज़िला अस्पताल या swavlambancard.gov.in पर आवेदन कीजिए।"),
    "birth_cert": ("Girl child's birth certificate", "बेटी का जन्म प्रमाणपत्र", "Apply at the panchayat / municipal registrar.", "पंचायत या नगर निकाय के पंजीयक से लीजिए।"),
    "photo": ("Passport-size photographs", "पासपोर्ट साइज़ फ़ोटो", "Any photo studio.", "किसी भी फ़ोटो स्टूडियो में।"),
    "trade_proof": ("Proof of your trade or business (vendor certificate / shop slip / skill)", "पेशे/दुकान का प्रमाण (वेंडर प्रमाणपत्र / दुकान की पर्ची / हुनर)", "A letter from the local body, a bill, or a word from your panchayat can be accepted.", "स्थानीय निकाय का पत्र, बिल या पंचायत का प्रमाण चल सकता है।"),
    "shg": ("Membership of a self-help group", "स्वयं सहायता समूह की सदस्यता", "Ask your block's NRLM / 'Aajeevika' office or the nearest group.", "अपने ब्लॉक के NRLM / आजीविका कार्यालय या नज़दीकी समूह से पूछिए।"),
}
CORE = ("aadhaar", "bank", "bank_aadhaar", "name_match", "account_active", "aadhaar_mobile")   # block many schemes

# id: dict(en, hi, gives_en, gives_hi, cash_per_year, docs, where_en, where_hi, link, rule)
# `rule(p) -> 'likely' | 'maybe' | None` with `why`.
SCHEMES: list[dict[str, Any]] = [
    dict(id="pm_kisan", en="PM-KISAN", hi="पीएम-किसान",
         gives_en="₹6,000 a year in three instalments, straight to your bank account.", gives_hi="साल में ₹6,000, तीन किस्तों में, सीधे बैंक खाते में।",
         cash=6000, docs=["aadhaar", "bank_aadhaar", "land", "name_match"], link="pmkisan.gov.in",
         where_en="Common Service Centre, or your agriculture / patwari office", where_hi="कॉमन सर्विस सेंटर, या कृषि/पटवारी कार्यालय",
         need="owns_land", not_for="taxpayer", gist_en="owns cultivable land and does not pay income tax", gist_hi="खेती की ज़मीन अपने नाम है और आयकर नहीं देते"),
    dict(id="kcc", en="Kisan Credit Card", hi="किसान क्रेडिट कार्ड",
         gives_en="Farm loan up to ₹3 lakh at about 7% a year (about 4% if repaid on time), instead of a moneylender or arhtiya at 36% or more.", gives_hi="₹3 लाख तक का खेती का ऋण लगभग 7% साल पर (समय से चुकाने पर लगभग 4%), साहूकार या आढ़तिये के 36% या ज़्यादा के बदले।",
         cash=0, docs=["aadhaar", "bank", "land", "photo"], link="pmkisan.gov.in (KCC) / your bank",
         where_en="Your bank branch or co-operative society", where_hi="आपकी बैंक शाखा या सहकारी समिति",
         need="farms", gist_en="farms land (own or rented) or keeps animals or fish", gist_hi="खेती (अपनी या बटाई) या पशुपालन/मछली पालन करते हैं"),
    dict(id="pmfby", en="PM Fasal Bima Yojana (crop insurance)", hi="पीएम फ़सल बीमा योजना",
         gives_en="Insurance if the crop is lost to flood, drought, hail or pests. You pay only 2% (kharif), 1.5% (rabi) of the sum insured.", gives_hi="बाढ़, सूखा, ओले या कीट से फ़सल बर्बाद होने पर बीमा। आप बीमित रक़म का सिर्फ़ 2% (ख़रीफ़), 1.5% (रबी) देते हैं।",
         cash=0, docs=["aadhaar", "bank", "land"], link="pmfby.gov.in",
         where_en="Your bank, CSC or the crop-insurance portal; apply before the cut-off date each season", where_hi="बैंक, CSC या फ़सल बीमा पोर्टल; हर मौसम में अंतिम तिथि से पहले",
         need="farms", gist_en="grows crops", gist_hi="फ़सल उगाते हैं"),
    dict(id="pmjjby", en="PM Jeevan Jyoti Bima (life insurance)", hi="पीएम जीवन ज्योति बीमा",
         gives_en="₹2 lakh to your family if you die, for about ₹436 a year, taken from your account.", gives_hi="मृत्यु पर परिवार को ₹2 लाख, लगभग ₹436 सालाना में, आपके खाते से कटकर।",
         cash=0, docs=["aadhaar", "bank", "account_active"], link="jansuraksha.gov.in",
         where_en="Your bank branch", where_hi="आपकी बैंक शाखा", age=(18, 50), need="bank",
         gist_en="aged 18-50 with a bank account", gist_hi="18-50 साल के और बैंक खाता है"),
    dict(id="pmsby", en="PM Suraksha Bima (accident insurance)", hi="पीएम सुरक्षा बीमा",
         gives_en="₹2 lakh for accidental death or full disability, for ₹20 a year.", gives_hi="दुर्घटना में मृत्यु या पूरी विकलांगता पर ₹2 लाख, सिर्फ़ ₹20 सालाना में।",
         cash=0, docs=["aadhaar", "bank", "account_active"], link="jansuraksha.gov.in",
         where_en="Your bank branch", where_hi="आपकी बैंक शाखा", age=(18, 70), need="bank",
         gist_en="aged 18-70 with a bank account", gist_hi="18-70 साल के और बैंक खाता है"),
    dict(id="apy", en="Atal Pension Yojana", hi="अटल पेंशन योजना",
         gives_en="A fixed monthly pension of ₹1,000-₹5,000 from age 60; you save a small amount each month (about ₹42-₹210 if you start at 18).", gives_hi="60 साल के बाद ₹1,000-₹5,000 की तय मासिक पेंशन; आप हर महीने थोड़ा जमा करते हैं (18 साल में शुरू करें तो लगभग ₹42-₹210)।",
         cash=0, docs=["aadhaar", "bank", "account_active", "aadhaar_mobile"], link="npscra.nsdl.co.in / your bank",
         where_en="Your bank branch", where_hi="आपकी बैंक शाखा", age=(18, 40), need="bank", not_for="taxpayer",
         gist_en="aged 18-40, with a bank account, not an income-tax payer", gist_hi="18-40 साल के, बैंक खाता, आयकर दाता नहीं"),
    dict(id="pmjay", en="Ayushman Bharat PM-JAY (health cover)", hi="आयुष्मान भारत पीएम-जय (स्वास्थ्य बीमा)",
         gives_en="Free hospital treatment up to ₹5 lakh per family per year at listed hospitals. Everyone aged 70+ can enrol regardless of income.", gives_hi="सूचीबद्ध अस्पतालों में परिवार को साल में ₹5 लाख तक मुफ़्त इलाज। 70 साल से ऊपर के सभी लोग आय की परवाह किए बिना जुड़ सकते हैं।",
         cash=0, docs=["aadhaar", "ration"], link="pmjay.gov.in / call 14555",
         where_en="Ayushman Mitra at a government hospital, CSC, or call 14555 to check your name", where_hi="सरकारी अस्पताल में आयुष्मान मित्र, CSC, या अपना नाम जाँचने के लिए 14555",
         need="poor_or_senior", gist_en="a poor household (kutcha house, no adult earner, landless labour, SC/ST, etc.) or aged 70+", gist_hi="ग़रीब परिवार (कच्चा मकान, कोई कमाने वाला नहीं, भूमिहीन मज़दूर, SC/ST आदि) या 70+ उम्र"),
    dict(id="nrega", en="MGNREGA (100 days of work)", hi="मनरेगा (100 दिन का काम)",
         gives_en="Up to 100 days of paid work a year near home. If work is not given within 15 days of asking, you are owed an allowance.", gives_hi="घर के पास साल में 100 दिन तक मज़दूरी वाला काम। माँगने के 15 दिन में काम न मिले तो भत्ता मिलता है।",
         cash=0, docs=["aadhaar", "bank_aadhaar", "photo", "job_card"], link="nrega.nic.in",
         where_en="Gram panchayat (ask for a job card, and give a written demand for work)", where_hi="ग्राम पंचायत (जॉब कार्ड माँगिए और काम के लिए लिखित माँग दीजिए)",
         need="rural_adult", gist_en="an adult living in a rural area willing to do manual work", gist_hi="गाँव में रहने वाले वयस्क जो शारीरिक काम करने को तैयार हैं"),
    dict(id="eshram", en="e-Shram card (unorganised workers)", hi="ई-श्रम कार्ड (असंगठित मज़दूर)",
         gives_en="Free registration with ₹2 lakh accident insurance and a base for other worker schemes.", gives_hi="मुफ़्त पंजीकरण, ₹2 लाख का दुर्घटना बीमा और अन्य श्रमिक योजनाओं का आधार।",
         cash=0, docs=["aadhaar", "bank", "aadhaar_mobile"], link="eshram.gov.in",
         where_en="Any CSC, post office, or eshram.gov.in (free)", where_hi="कोई भी CSC, डाकघर, या eshram.gov.in (मुफ़्त)", age=(16, 59), need="worker", not_for="taxpayer",
         gist_en="aged 16-59 and works as a labourer, farm hand, vendor or artisan, not in EPFO/ESIC", gist_hi="16-59 साल के मज़दूर, खेत मज़दूर, फेरीवाले या कारीगर, EPFO/ESIC में नहीं"),
    dict(id="pmsym", en="PM Shram Yogi Maandhan (pension for workers)", hi="पीएम श्रम योगी मानधन (मज़दूरों की पेंशन)",
         gives_en="₹3,000 a month pension from age 60; the government adds an equal amount to what you pay.", gives_hi="60 साल के बाद ₹3,000 मासिक पेंशन; आप जितना देते हैं सरकार उतना ही जोड़ती है।",
         cash=0, docs=["aadhaar", "bank", "account_active", "aadhaar_mobile"], link="maandhan.in",
         where_en="Any CSC", where_hi="कोई भी CSC", age=(18, 40), need="worker", not_for="taxpayer",
         gist_en="aged 18-40, unorganised worker earning up to ₹15,000 a month", gist_hi="18-40 साल के असंगठित मज़दूर, ₹15,000 महीने तक कमाई"),
    dict(id="pmay_g", en="PM Awas Yojana (Gramin): house", hi="पीएम आवास योजना (ग्रामीण): मकान",
         gives_en="Help of about ₹1.2 lakh (₹1.3 lakh in hilly areas) to build a pucca house, plus toilet and MGNREGA wages.", gives_hi="पक्का मकान बनाने के लिए लगभग ₹1.2 लाख (पहाड़ी इलाक़ों में ₹1.3 लाख) की मदद, साथ में शौचालय और मनरेगा मज़दूरी।",
         cash=0, docs=["aadhaar", "bank_aadhaar", "job_card", "ration"], link="pmayg.nic.in",
         where_en="Gram panchayat / block office (the list is made from a household survey)", where_hi="ग्राम पंचायत / ब्लॉक कार्यालय (सूची घरेलू सर्वे से बनती है)",
         need="kutcha", gist_en="lives in a kutcha or one-room house and has no pucca house", gist_hi="कच्चे या एक कमरे के मकान में रहते हैं, पक्का मकान नहीं"),
    dict(id="ujjwala", en="PM Ujjwala (free LPG connection)", hi="पीएम उज्ज्वला (मुफ़्त गैस कनेक्शन)",
         gives_en="A free LPG connection in the woman's name, so no more cooking over a smoky fire.", gives_hi="महिला के नाम मुफ़्त एलपीजी कनेक्शन, ताकि धुएँ वाले चूल्हे से छुटकारा मिले।",
         cash=0, docs=["aadhaar", "bank", "ration", "photo"], link="pmuy.gov.in",
         where_en="Nearest LPG distributor", where_hi="नज़दीकी गैस एजेंसी", need="poor_woman",
         gist_en="a woman (18+) in a poor household without an LPG connection", gist_hi="ग़रीब परिवार की महिला (18+) जिसके पास गैस कनेक्शन नहीं"),
    dict(id="oap", en="Old-age / widow / disability pension (NSAP)", hi="वृद्धावस्था / विधवा / दिव्यांग पेंशन (NSAP)",
         gives_en="A monthly pension (central share ₹200-₹500, states add more), paid into your account.", gives_hi="मासिक पेंशन (केंद्र का हिस्सा ₹200-₹500, राज्य और जोड़ते हैं), सीधे खाते में।",
         cash=0, docs=["aadhaar", "bank_aadhaar", "age_proof", "ration", "income"], link="nsap.nic.in / your state social-welfare portal",
         where_en="Gram panchayat / block or social-welfare office", where_hi="ग्राम पंचायत / ब्लॉक या समाज कल्याण कार्यालय", need="pension",
         gist_en="a poor household member who is 60+, or a widow (40+), or has a disability of 80% or more", gist_hi="ग़रीब परिवार का 60+ सदस्य, या विधवा (40+), या 80% या ज़्यादा दिव्यांगता"),
    dict(id="ssy", en="Sukanya Samriddhi (savings for a daughter)", hi="सुकन्या समृद्धि (बेटी की बचत)",
         gives_en="A government-backed savings account for a girl under 10, from ₹250 a year, with a good interest rate set by the government (about 8%).", gives_hi="10 साल से छोटी बेटी के लिए सरकार-समर्थित बचत खाता, साल के ₹250 से, सरकार की तय अच्छी ब्याज दर (लगभग 8%) पर।",
         cash=0, docs=["aadhaar", "birth_cert", "photo"], link="indiapost.gov.in / any bank",
         where_en="Post office or authorised bank", where_hi="डाकघर या अधिकृत बैंक", need="daughter",
         gist_en="has a daughter under 10", gist_hi="10 साल से छोटी बेटी है"),
    dict(id="scholar", en="Scholarships for SC / ST / OBC / minority students", hi="SC / ST / OBC / अल्पसंख्यक छात्रवृत्ति",
         gives_en="Fees and a yearly allowance for school and college; amounts and income limits depend on the state and course.", gives_hi="स्कूल-कॉलेज की फ़ीस और सालाना भत्ता; रक़म और आय सीमा राज्य और पाठ्यक्रम पर निर्भर।",
         cash=0, docs=["aadhaar", "bank_aadhaar", "caste", "income", "photo"], link="scholarships.gov.in",
         where_en="National Scholarship Portal (scholarships.gov.in) through the school or a CSC", where_hi="राष्ट्रीय छात्रवृत्ति पोर्टल (scholarships.gov.in), स्कूल या CSC से",
         need="student_category", gist_en="has a child studying and the family is SC, ST, OBC or minority with a modest income", gist_hi="बच्चा पढ़ रहा है और परिवार SC, ST, OBC या अल्पसंख्यक है, सीमित आय"),
    dict(id="mudra", en="PM Mudra loan (small business)", hi="पीएम मुद्रा ऋण (छोटा कारोबार)",
         gives_en="Loan up to ₹10 lakh for a small non-farm business; no collateral up to ₹10 lakh. Start with 'Shishu' (up to ₹50,000).", gives_hi="छोटे ग़ैर-कृषि कारोबार के लिए ₹10 लाख तक का ऋण; बिना गिरवी। 'शिशु' (₹50,000 तक) से शुरू करें।",
         cash=0, docs=["aadhaar", "bank", "trade_proof", "photo"], link="mudra.org.in / your bank",
         where_en="Any bank, small-finance bank or microfinance institution", where_hi="कोई भी बैंक, स्मॉल फ़ाइनेंस बैंक या माइक्रोफ़ाइनेंस संस्था", need="business",
         gist_en="runs or wants to start a small shop, workshop, dairy-product or service business", gist_hi="छोटी दुकान, वर्कशॉप, दूध-उत्पाद या सेवा का कारोबार चलाते हैं या शुरू करना चाहते हैं"),
    dict(id="vishwakarma", en="PM Vishwakarma (artisans)", hi="पीएम विश्वकर्मा (कारीगर)",
         gives_en="Skill training with a daily stipend, a ₹15,000 toolkit grant and a loan up to ₹3 lakh at 5%.", gives_hi="रोज़ाना भत्ते के साथ प्रशिक्षण, ₹15,000 औज़ार सहायता और 5% पर ₹3 लाख तक ऋण।",
         cash=0, docs=["aadhaar", "bank", "aadhaar_mobile", "trade_proof"], link="pmvishwakarma.gov.in",
         where_en="CSC or the PM Vishwakarma portal", where_hi="CSC या पीएम विश्वकर्मा पोर्टल", age=(18, 120), need="artisan",
         gist_en="an artisan or craftsperson in a traditional trade (carpenter, potter, blacksmith, weaver, tailor, cobbler, barber...)", gist_hi="पारंपरिक पेशे का कारीगर (बढ़ई, कुम्हार, लोहार, बुनकर, दर्ज़ी, मोची, नाई...)"),
    dict(id="svanidhi", en="PM SVANidhi (street vendors)", hi="पीएम स्वनिधि (रेहड़ी-पटरी वाले)",
         gives_en="Working-capital loan from ₹10,000, repeated and larger when repaid, with a small interest subsidy.", gives_hi="₹10,000 से शुरू कार्यशील पूँजी ऋण, समय से चुकाने पर दोबारा और बड़ा, ब्याज में छोटी छूट के साथ।",
         cash=0, docs=["aadhaar", "bank", "trade_proof"], link="pmsvanidhi.mohua.gov.in",
         where_en="Municipal office, a bank or a CSC", where_hi="नगर निकाय कार्यालय, बैंक या CSC", need="vendor",
         gist_en="sells goods or services on the street or from a cart", gist_hi="सड़क पर या ठेले से सामान/सेवा बेचते हैं"),
    dict(id="jandhan", en="Jan Dhan account", hi="जन धन खाता",
         gives_en="A zero-balance bank account with a RuPay card (₹2 lakh accident cover) and the door to every payment scheme above.", gives_hi="शून्य बैलेंस वाला बैंक खाता, RuPay कार्ड (₹2 लाख दुर्घटना बीमा) और ऊपर की हर भुगतान योजना का रास्ता।",
         cash=0, docs=["aadhaar", "photo"], link="pmjdy.gov.in",
         where_en="Any bank branch or banking correspondent", where_hi="कोई भी बैंक शाखा या बैंक मित्र", need="no_bank",
         gist_en="does not have a bank account", gist_hi="बैंक खाता नहीं है"),
    dict(id="shg_nrlm", en="Self-help group (DAY-NRLM / Lakhpati Didi)", hi="स्वयं सहायता समूह (DAY-NRLM / लखपति दीदी)",
         gives_en="Cheap group loans, a revolving fund and training. Group loans are the best replacement for a moneylender.", gives_hi="सस्ते समूह ऋण, रिवॉल्विंग फ़ंड और प्रशिक्षण। साहूकार का सबसे अच्छा विकल्प समूह ऋण है।",
         cash=0, docs=["aadhaar", "bank", "shg"], link="aajeevika.gov.in",
         where_en="Block NRLM / Aajeevika office, or ask the nearest group", where_hi="ब्लॉक NRLM / आजीविका कार्यालय, या नज़दीकी समूह से पूछिए", need="woman_not_shg",
         gist_en="a woman in a rural household not yet in a self-help group", gist_hi="ग्रामीण परिवार की महिला जो अभी किसी समूह में नहीं"),
]
SCHEME_BY_ID = {s["id"]: s for s in SCHEMES}


def _profile(p: dict[str, Any]) -> dict[str, Any]:
    return {"age": int(p.get("age") or 0), "gender": p.get("gender") or "any",
            "land": p.get("land") or "none", "work": p.get("work") or "other",
            "bank": bool(p.get("bank", True)), "taxpayer": bool(p.get("taxpayer", False)),
            "poor": p.get("poor") or "unsure", "category": p.get("category") or "general",
            "daughter": bool(p.get("daughter", False)), "kutcha": bool(p.get("kutcha", False)),
            "disability": bool(p.get("disability", False)), "widow": bool(p.get("widow", False)),
            "student": bool(p.get("student", False)), "shg": bool(p.get("shg", False)),
            "rural": bool(p.get("rural", True)), "lpg": bool(p.get("lpg", True))}


def _check(s: dict[str, Any], p: dict[str, Any]) -> str | None:
    """'likely' | 'maybe' | None for one household."""
    age, lo_hi = p["age"], s.get("age")
    if lo_hi and age and not (lo_hi[0] <= age <= lo_hi[1]):
        return None
    if s.get("not_for") == "taxpayer" and p["taxpayer"]:
        return None
    need = s["need"]
    poor = p["poor"] in ("yes", "unsure")
    worker = p["work"] in ("labour", "farm_labour", "vendor", "artisan", "farmer", "other_worker")
    if need == "owns_land":
        return "likely" if p["land"] == "own" else None
    if need == "farms":
        return "likely" if (p["land"] in ("own", "tenant") or p["work"] == "farmer") else None
    if need == "bank":
        return "likely" if p["bank"] else None
    if need == "no_bank":
        return "likely" if not p["bank"] else None
    if need == "poor_or_senior":
        if age >= 70:
            return "likely"
        return "likely" if (p["poor"] == "yes" or p["kutcha"] or p["land"] == "none" and p["work"] in ("farm_labour", "labour")) else ("maybe" if p["poor"] == "unsure" else None)
    if need == "rural_adult":
        return "likely" if (p["rural"] and (age == 0 or age >= 18)) else None
    if need == "worker":
        return "likely" if worker else None
    if need == "kutcha":
        return "likely" if p["kutcha"] else None
    if need == "poor_woman":
        return ("likely" if p["poor"] == "yes" else "maybe") if (p["gender"] == "female" and not p["lpg"]) else None
    if need == "pension":
        if (age >= 60 and poor) or (p["widow"] and age >= 40 and poor) or (p["disability"] and poor):
            return "likely" if p["poor"] == "yes" else "maybe"
        return None
    if need == "daughter":
        return "likely" if p["daughter"] else None
    if need == "student_category":
        return ("likely" if p["category"] in ("sc", "st", "obc", "minority") else None) if p["student"] else None
    if need == "business":
        return "likely" if p["work"] in ("business", "vendor", "artisan") else "maybe" if p["work"] == "other" else None
    if need == "artisan":
        return "likely" if p["work"] == "artisan" else None
    if need == "vendor":
        return "likely" if p["work"] == "vendor" else None
    if need == "woman_not_shg":
        return "likely" if (p["gender"] == "female" and p["rural"] and not p["shg"]) else None
    return None


def entitlements(profile: dict[str, Any], lang: str = "en") -> dict[str, Any]:
    t = _tr(lang)
    p = _profile(profile)
    out = []
    for s in SCHEMES:
        status = _check(s, p)
        if status:
            out.append({"id": s["id"], "name": s["hi"] if lang == "hi" else s["en"], "status": status,
                        "gives": s["gives_hi"] if lang == "hi" else s["gives_en"],
                        "who": s["gist_hi"] if lang == "hi" else s["gist_en"],
                        "where": s["where_hi"] if lang == "hi" else s["where_en"], "link": s["link"],
                        "cash_per_year": s["cash"], "docs": [DOCS[d][1 if lang == "hi" else 0] for d in s["docs"]],
                        "doc_ids": s["docs"]})
    out.sort(key=lambda x: (x["status"] != "likely", -x["cash_per_year"]))
    cash = sum(x["cash_per_year"] for x in out if x["status"] == "likely")
    return {"schemes": out, "count": len(out), "cash_per_year": cash, "checked": CHECKED,
            "note": t("This is a guide to what to ask about, not a decision. Rules and amounts change and states add their own: confirm at the place shown before you rely on it. Nobody may charge you a fee to apply.",
                      "यह पूछने की सूची है, फ़ैसला नहीं। नियम और रक़म बदलती रहती हैं और राज्य अपनी योजनाएँ जोड़ते हैं: भरोसा करने से पहले दिखाई जगह पर पक्का कीजिए। आवेदन के लिए किसी को पैसे देने की ज़रूरत नहीं।")}


def readiness(scheme_ids: list[str], have: list[str], lang: str = "en") -> dict[str, Any]:
    """Which documents each chosen scheme still needs, and the single fix that unblocks the most."""
    t = _tr(lang)
    have_s = set(have)
    chosen = [SCHEME_BY_ID[i] for i in scheme_ids if i in SCHEME_BY_ID]
    per, blockers = [], {}
    for s in chosen:
        miss = [d for d in s["docs"] if d not in have_s]
        for d in miss:
            blockers[d] = blockers.get(d, 0) + 1
        per.append({"id": s["id"], "name": s["hi"] if lang == "hi" else s["en"], "ready": not miss,
                    "have": len(s["docs"]) - len(miss), "total": len(s["docs"]),
                    "missing": [d for d in miss]})
    # Order of attack: the thing blocking most schemes first; core identity/bank ones win ties.
    prio = list(DOCS)
    order = sorted(blockers, key=lambda d: (-blockers[d], 0 if d in CORE else 1, prio.index(d)))
    docs = {d: {"id": d, "name": DOCS[d][1 if lang == "hi" else 0], "how": DOCS[d][3 if lang == "hi" else 2],
                "blocks": blockers[d]} for d in blockers}
    steps = []
    for n, d in enumerate(order, 1):
        steps.append({"n": n, **docs[d]})
    for e in per:
        e["missing"] = [docs[d]["name"] for d in e["missing"]]
    first = steps[0] if steps else None
    summary = (t("You have everything for the schemes you picked. Go to the place shown for each.", "आपने जो योजनाएँ चुनीं उनके सारे काग़ज़ आपके पास हैं। हर योजना के लिए दिखाई जगह जाइए।")
               if not steps else
               t(f"Fix this first: {first['name']}. It is holding up {first['blocks']} of your {len(chosen)} schemes.", f"सबसे पहले यह ठीक कीजिए: {first['name']}। यह आपकी {len(chosen)} में से {first['blocks']} योजनाओं को रोक रहा है।"))
    return {"schemes": per, "steps": steps, "summary": summary,
            "tip": t("Most payments fail for three simple reasons: Aadhaar not linked to the bank account, a name spelled differently in two places, or a dormant account. Fix those before you apply.",
                     "ज़्यादातर भुगतान तीन सीधी वजहों से रुकते हैं: आधार बैंक खाते से जुड़ा नहीं, दो जगह नाम की वर्तनी अलग, या खाता निष्क्रिय। आवेदन से पहले इन्हें ठीक कीजिए।"),
            "all_docs": [{"id": k, "name": v[1 if lang == "hi" else 0]} for k, v in DOCS.items()]}


# =============================================================================== C1 lumpy income
def income_plan(income: list[dict[str, Any]], monthly_cost: float, one_offs: list[dict[str, Any]] | None = None,
                savings: float = 0.0, borrow_rate_yearly: float = 36.0, lang: str = "en") -> dict[str, Any]:
    """`income`: [{month 1-12, amount, label}]; `one_offs`: money out in a month (seed, fees, wedding)."""
    t = _tr(lang)
    names = MONTHS_HI if lang == "hi" else MONTHS_EN
    inc = [0.0] * 12
    out = [float(monthly_cost)] * 12
    for e in income or []:
        m = int(e.get("month", 1)) - 1
        if 0 <= m < 12:
            inc[m] += max(0.0, float(e.get("amount", 0)))
    for e in one_offs or []:
        m = int(e.get("month", 1)) - 1
        if 0 <= m < 12:
            out[m] += max(0.0, float(e.get("amount", 0)))
    total_in, total_out = sum(inc), sum(out)
    net = total_in - total_out

    # Without a plan: you spend as you go, starting from `savings`.
    bal, series, short_months, peak_short = float(savings), [], [], 0.0
    for m in range(12):
        bal += inc[m] - out[m]
        series.append(round(bal))
        if bal < 0:
            short_months.append(m)
            peak_short = max(peak_short, -bal)
    # Steady-state buffer so a repeating year never goes below zero: the worst cumulative dip.
    cum, lo = 0.0, 0.0
    start = int(min(range(12), key=lambda m: -inc[m])) if any(inc) else 0           # begin just after the biggest income
    for k in range(12):
        m = (start + k) % 12
        cum += inc[m] - out[m]
        lo = min(lo, cum)
    buffer_needed = max(0.0, -lo) if net >= 0 else None
    # Borrowing cost if the gap is covered by credit instead of a buffer.
    gap_months = len(short_months)
    borrow_cost = peak_short * (borrow_rate_yearly / 100) * (max(1, gap_months) / 12) if peak_short else 0.0

    # Per-income rule: how much of each lump to keep aside for the months until the next one.
    plan = []
    income_months = [m for m in range(12) if inc[m] > 0]
    for m in income_months:
        nxt = next(((m + k) % 12 for k in range(1, 13) if inc[(m + k) % 12] > 0), m)
        span = ((nxt - m) % 12) or 12
        need = sum(out[(m + k) % 12] for k in range(0, span))          # cover this month through the month before the next income
        keep = min(inc[m], need)
        plan.append({"month": names[m], "amount": round(inc[m]), "months_until_next": span, "spend_now": round(max(0.0, inc[m] - keep)),
                     "keep_aside": round(keep),
                     "text": t(f"From the {_inr(inc[m])} you get in {names[m]}, you will need {_inr(need)} to cover the {span} months until your next income. Keep {_inr(keep)} aside{' and you may use the rest' if inc[m] > keep else ''}.",
                               f"{names[m]} में मिलने वाले {_inr(inc[m], 'hi')} में से अगली आमदनी तक के {span} महीनों के लिए {_inr(need, 'hi')} चाहिए। {_inr(keep, 'hi')} अलग रखिए{' और बाक़ी इस्तेमाल कर सकते हैं' if inc[m] > keep else ''}।")})
    draw = total_in / 12
    emergency = out_avg = total_out / 12
    emergency_target = out_avg * 6                                 # irregular income needs a longer cushion than a salaried 3
    if net < 0:
        head = t(f"Your income does not cover your costs: you fall short by about {_inr(-net)} a year ({_inr(-net / 12)} a month).",
                 f"आपकी आमदनी ख़र्च पूरा नहीं करती: साल में लगभग {_inr(-net, 'hi')} ({_inr(-net / 12, 'hi')} महीना) कम पड़ता है।")
        band = "red"
    elif short_months:
        lean = ", ".join(names[m] for m in short_months)
        head = t(f"You earn enough over the year, but run out of money in {gap_months} months ({lean}). Saving from the good months fixes this.",
                 f"साल भर में कमाई काफ़ी है, पर {gap_months} महीनों ({lean}) में पैसा ख़त्म हो जाता है। अच्छे महीनों से बचत रखने पर यह ठीक हो जाता है।")
        band = "amber"
    else:
        head = t("Your income covers your costs in every month with the savings you have.", "आपके पास की बचत से हर महीने आमदनी ख़र्च पूरा कर देती है।")
        band = "green"
    tips = []
    if peak_short:
        tips.append(t(f"Until your next income you are short by up to {_inr(peak_short)}. Cover it from the cheapest source first (savings, a group or bank loan, Kisan Credit Card), not a moneylender. After that, the keep-aside rule below stops it happening again.",
                      f"अगली आमदनी तक आपको {_inr(peak_short, 'hi')} तक की कमी पड़ेगी। इसे सबसे सस्ते साधन से पूरा कीजिए (बचत, समूह या बैंक ऋण, किसान क्रेडिट कार्ड), साहूकार से नहीं। उसके बाद नीचे का 'अलग रखने' का नियम इसे दोबारा होने से रोकेगा।"))
    if borrow_cost:
        tips.append(t(f"Covering that gap with a moneylender at {borrow_rate_yearly:.0f}% a year would cost about {_inr(borrow_cost)}. The same money saved would cost nothing.",
                      f"वह कमी साहूकार से {borrow_rate_yearly:.0f}% साल पर पूरी करने में लगभग {_inr(borrow_cost, 'hi')} ब्याज लगेगा। यही रक़म बचत में हो तो कोई ब्याज नहीं।"))
    tips.append(t(f"Aim for an emergency fund of about {_inr(emergency_target)} (six months of costs), because income that comes in lumps is less certain than a salary.",
                  f"लगभग {_inr(emergency_target, 'hi')} का इमरजेंसी फ़ंड रखिए (छह महीने का ख़र्च), क्योंकि एकमुश्त आने वाली आमदनी वेतन से कम पक्की होती है।"))
    if net >= 0:
        tips.append(t(f"Think of yourself as paying yourself {_inr(min(draw, total_in / 12))} a month from the money kept aside, like a salary.",
                      f"ख़ुद को हर महीने {_inr(min(draw, total_in / 12), 'hi')} 'वेतन' की तरह दीजिए, अलग रखे पैसे से।"))
    return {"headline": head, "band": band, "income_year": round(total_in), "cost_year": round(total_out), "net_year": round(net),
            "months": [{"m": names[m], "income": round(inc[m]), "cost": round(out[m]), "balance": series[m]} for m in range(12)],
            "short_months": [names[m] for m in short_months], "peak_shortfall": round(peak_short),
            "buffer_needed": round(peak_short),
            "borrow_cost": round(borrow_cost), "emergency_target": round(emergency_target),
            "plan": plan, "tips": tips,
            "note": t("Add every large cost you know is coming (seed and fertiliser, school fees, a wedding, festivals) under 'one-off costs' so the plan can see it.",
                      "जो बड़े ख़र्च आने वाले हैं (बीज-खाद, स्कूल फ़ीस, शादी, त्योहार) उन्हें 'एकमुश्त ख़र्च' में जोड़िए ताकि योजना उन्हें देख सके।")}


# =============================================================================== A3 insurance policy check
INS_FLAGS: dict[str, tuple[int, str, str, str]] = {
    "sold_as_fd": (30, "Described like a fixed deposit or savings account. An insurance policy is not one, and early exit usually costs you.",
                   "फ़िक्स्ड डिपॉज़िट या बचत खाते की तरह बताई गई। बीमा पॉलिसी वह नहीं है, और बीच में छोड़ने पर आम तौर पर नुक़सान होता है।",
                   r"like (an? )?(fd|fixed deposit|savings)|better than (an? )?(fd|fixed deposit|bank)|fd (jaisa|se behtar)|एफ़?डी जैसा|एफ़?डी से (बेहतर|ज़्यादा)|बैंक से ज़्यादा"),
    "bank_sold": (15, "Sold by a bank or post-office staff member as a 'scheme' or 'investment'. Staff earn commission on insurance; the bank does not guarantee it.",
                  "बैंक या डाकघर के कर्मचारी ने 'योजना' या 'निवेश' कहकर बेची। बीमा पर उन्हें कमीशन मिलता है; बैंक इसकी गारंटी नहीं देता।",
                  r"bank (manager|staff|officer|person) (told|said|sold|suggested)|sold (me )?(at|in|by) (the )?bank|बैंक (वाले|मैनेजर|कर्मचारी)|बैंक में (बेची|बताया|कहा)"),
    "guaranteed_high": (25, "Promises guaranteed or very high returns.", "गारंटी या बहुत ऊँचे रिटर्न का वादा।",
                        r"guarantee|assured return|fixed return|double|दोगुना|गारंटी|पक्का (रिटर्न|मुनाफ़ा|मुनाफा)"),
    "pay_few_get_many": (15, "Pay for a few years and get a large sum or income for life: check the exact figures in writing.",
                         "कुछ साल भरें और बड़ी रक़म या उम्र भर आमदनी: सही आँकड़े लिखित में माँगिए।",
                         r"pay (only )?\d+ years? (and )?get|limited pay|कुछ साल (भरो|भरें)|सिर्फ़? \d+ साल"),
    "pressure": (15, "Pressure to sign today ('offer ends', 'last day', 'bonus lapses').", "आज ही दस्तख़त करने का दबाव ('ऑफ़र ख़त्म', 'आख़िरी दिन', 'बोनस ख़त्म')।",
                 r"last day|offer ends|limited offer|only today|today only|hurry|आखिरी दिन|आख़िरी दिन|ऑफर खत्म|सिर्फ़? आज"),
    "refund_scam": (45, "A caller says an old policy has a bonus or refund waiting and asks you to pay a fee or tax to release it. That is a scam: real insurers never ask for money to pay you.",
                    "कोई फ़ोन पर कहता है कि पुरानी पॉलिसी का बोनस या रिफ़ंड रुका है और छुड़ाने को फ़ीस या टैक्स माँगता है। यह ठगी है: असली बीमा कंपनी पैसे देने के लिए पैसे नहीं माँगती।",
                    r"(bonus|refund|maturity|claim|lapsed?).{0,50}(pay|fee|gst|tax|charges|processing).{0,40}(release|unlock|get|receive|transfer)|(pay|fee|gst|tax).{0,50}(bonus|refund|maturity).{0,30}(release|unlock)|बोनस.{0,40}(फ़ीस|फीस|टैक्स|चार्ज)|रिफ़ंड.{0,40}(फ़ीस|फीस|टैक्स)"),
    "cheque_to_agent": (40, "Asked to pay by cash, or by cheque or UPI to a person instead of the insurance company.",
                        "नक़द में, या बीमा कंपनी की जगह किसी व्यक्ति को चेक/UPI से भुगतान करने को कहा।",
                        r"cash only|pay cash|in cash|cheque (in|to) (my|the agent|his|her) name|pay (me|the agent) (directly|personally)|personal (account|upi)|नक़द में|नकद में|एजेंट के (नाम|खाते)|मेरे खाते में"),
    "market_hidden": (15, "Market-linked (ULIP) but sold with fixed-sounding promises. Ask for the charges table in writing.",
                      "बाज़ार से जुड़ी (यूलिप) पर तय रिटर्न जैसे वादे के साथ बेची। ख़र्चों की तालिका लिखित में माँगिए।",
                      r"ulip|unit.?linked|market.?linked|यूलिप"),
}
INS_VERIFY = [
    ("IRDAI Bima Bharosa (complaints and checking an insurer or agent): bimabharosa.irdai.gov.in", "IRDAI बीमा भरोसा (शिकायत और बीमा कंपनी/एजेंट की जाँच): bimabharosa.irdai.gov.in"),
    ("Call the insurer's own number printed on the policy, never a number the caller gives; ask for the surrender-value table in writing.", "पॉलिसी पर छपे बीमा कंपनी के अपने नंबर पर फ़ोन कीजिए, फ़ोन करने वाले के दिए नंबर पर नहीं; सरेंडर वैल्यू की तालिका लिखित में माँगिए।"),
    ("Unresolved after the insurer's reply: Insurance Ombudsman (cioins.co.in).", "बीमा कंपनी के जवाब से संतुष्ट न हों तो: बीमा लोकपाल (cioins.co.in)।"),
]
FREE_LOOK = {"en": "A new policy can usually be returned within the free-look period (about 15 to 30 days from receipt; check your document) for a refund of the premium minus small charges. Use it if you feel misled.",
             "hi": "नई पॉलिसी आम तौर पर 'फ़्री-लुक' अवधि (मिलने से लगभग 15 से 30 दिन; अपने काग़ज़ में देखिए) में लौटाई जा सकती है, थोड़ी कटौती के साथ प्रीमियम वापस। भ्रमित महसूस करें तो इसका इस्तेमाल कीजिए।"}
SAFE_RATE = 7.1          # a plain PPF-like rate, used only as a comparison; the screen says so


def irr_pct(premium: float, pay_years: int, term_years: int, maturity: float) -> float | None:
    """Yearly return of paying `premium` at the start of each of `pay_years` years and receiving `maturity`
    at the end of `term_years`."""
    if premium <= 0 or pay_years < 1 or term_years < pay_years or maturity <= 0:
        return None

    def f(r: float) -> float:
        return sum(premium / (1 + r) ** t for t in range(pay_years)) - maturity / (1 + r) ** term_years
    lo, hi = -0.9, 2.0
    if f(lo) * f(hi) > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return round(((lo + hi) / 2) * 100, 2)


def _fv_deposits(amount: float, years: int, term: int, rate_pct: float) -> float:
    r = rate_pct / 100
    return sum(amount * (1 + r) ** (term - t) for t in range(years))


def policy_check(premium: float, pay_years: int, term_years: int, maturity: float, sum_assured: float | None = None,
                 term_quote: float | None = None, text: str = "", lang: str = "en") -> dict[str, Any]:
    t = _tr(lang)
    pay_years, term_years = int(pay_years), int(term_years)
    paid = premium * pay_years
    irr = irr_pct(premium, pay_years, term_years, maturity)
    alt_fv = _fv_deposits(premium, pay_years, term_years, SAFE_RATE)
    real_today = maturity / (1.06 ** term_years) if term_years else maturity
    ratio = (sum_assured / premium) if (sum_assured and premium) else None
    band = "red" if (irr is None or irr < 4) else "amber" if irr < 6.5 else "green"
    if irr is None:
        head = t("These figures do not add up to a return. Check the maturity amount and the years.", "इन आँकड़ों से रिटर्न नहीं निकलता। मैच्योरिटी रक़म और साल दोबारा देखिए।")
    else:
        head = t(f"You pay {_inr(paid)} and get {_inr(maturity)} back after {term_years} years. That is about {irr:.1f}% a year.",
                 f"आप {_inr(paid, 'hi')} भरते हैं और {term_years} साल बाद {_inr(maturity, 'hi')} पाते हैं। यह साल का लगभग {irr:.1f}% है।")
    verdict = {"red": t("This is a poor saving product. A bank or post-office deposit would very likely give you more, with no early-exit penalty.", "यह बचत के हिसाब से कमज़ोर है। बैंक या डाकघर की जमा से आपको लगभग निश्चित ही ज़्यादा मिलता, बिना बीच में छोड़ने के नुक़सान के।"),
               "amber": t("This returns less than safe deposits (about 7%). It may still be worth it only if you value the life cover.", "यह सुरक्षित जमा (लगभग 7%) से कम देती है। जीवन कवर को आप क़ीमती मानें तभी ठीक है।"),
               "green": t("The return is in line with safe deposits. Check the cover and the exit terms.", "रिटर्न सुरक्षित जमा के बराबर है। कवर और बीच में छोड़ने की शर्तें जाँचिए।")}[band]
    more = alt_fv > maturity
    bullets = [t(f"The same {_inr(premium)} a year for {pay_years} years in a safe deposit at about {SAFE_RATE}% would grow to about {_inr(alt_fv)} by year {term_years}: {_inr(abs(alt_fv - maturity))} {'more' if more else 'less'} than the policy.",
                 f"यही {_inr(premium, 'hi')} साल के, {pay_years} साल तक, लगभग {SAFE_RATE}% की सुरक्षित जमा में रखें तो {term_years} साल में लगभग {_inr(alt_fv, 'hi')} होते: पॉलिसी से {_inr(abs(alt_fv - maturity), 'hi')} {'ज़्यादा' if more else 'कम'}।"),
               t(f"In today's money (at 6% a year price rise) the {_inr(maturity)} is worth about {_inr(real_today)}.", f"आज के पैसे में (6% सालाना महँगाई मानें तो) {_inr(maturity, 'hi')} की क़ीमत लगभग {_inr(real_today, 'hi')} है।")]
    if ratio is not None:
        low = ratio < 30
        bullets.append(t(f"Life cover is {_inr(sum_assured)}, about {ratio:.0f} times one year's premium. " + ("That is low: a pure term plan gives many times more cover per rupee." if low else "That is a reasonable cover for the premium."),
                         f"जीवन कवर {_inr(sum_assured, 'hi')} है, यानी एक साल के प्रीमियम का लगभग {ratio:.0f} गुना। " + ("यह कम है: शुद्ध टर्म प्लान में प्रति रुपया कई गुना ज़्यादा कवर मिलता है।" if low else "प्रीमियम के हिसाब से यह ठीक कवर है।")))
    split = None
    if term_quote and sum_assured and 0 < term_quote < premium:
        invest = premium - term_quote
        fv = _fv_deposits(invest, pay_years, term_years, SAFE_RATE)
        split = {"term_quote": term_quote, "invest": invest, "fv": round(fv), "cover": sum_assured}
        bullets.append(t(f"Option: buy a pure term plan for {_inr(sum_assured)} at {_inr(term_quote)} a year and put the other {_inr(invest)} a year in a safe deposit: about {_inr(fv)} by year {term_years}, plus the same cover.",
                         f"विकल्प: {_inr(sum_assured, 'hi')} का शुद्ध टर्म प्लान {_inr(term_quote, 'hi')} साल में लें और बाक़ी {_inr(invest, 'hi')} साल की सुरक्षित जमा में रखें: {term_years} साल में लगभग {_inr(fv, 'hi')}, साथ में वही कवर।"))
    low_t = (text or "").lower()
    hits = [(fid, en, hi) for fid, (w, en, hi, rx) in INS_FLAGS.items() if re.search(rx, low_t)]
    score = sum(INS_FLAGS[f][0] for f, _e, _h in hits)
    scam = any(f == "refund_scam" for f, _e, _h in hits)
    if scam:
        head = t("This sounds like a refund scam, not a policy question. Do not pay anything.", "यह पॉलिसी का सवाल नहीं, रिफ़ंड ठगी जैसा लगता है। कुछ भी पैसा मत दीजिए।")
        band = "red"
    advice = [t("Do not stop paying in a panic: leaving early can cost you. First ask the insurer for the surrender-value table in writing, then decide.", "घबराकर प्रीमियम बंद मत कीजिए: बीच में छोड़ना महँगा पड़ सकता है। पहले बीमा कंपनी से सरेंडर वैल्यू की तालिका लिखित में माँगिए, फिर तय कीजिए।"),
              FREE_LOOK[lang]]
    return {"irr_pct": irr, "total_paid": round(paid), "maturity": round(maturity), "gain": round(maturity - paid), "alt_safe_fv": round(alt_fv),
            "alt_gap": round(alt_fv - maturity), "real_today": round(real_today), "cover_ratio": None if ratio is None else round(ratio, 1),
            "band": band, "headline": head, "verdict": verdict, "bullets": bullets, "split": split, "scam": scam,
            "flags": [{"id": f, "text": hi if lang == "hi" else en} for f, en, hi in hits], "flag_score": min(100, score),
            "advice": advice, "verify": [hi if lang == "hi" else en for en, hi in INS_VERIFY],
            "note": t(f"The safe-deposit comparison uses about {SAFE_RATE}% for illustration; today's rates differ. A policy also gives life cover, which a deposit does not, so weigh both.",
                      f"सुरक्षित जमा की तुलना उदाहरण के लिए लगभग {SAFE_RATE}% से है; आज की दरें अलग हो सकती हैं। पॉलिसी जीवन कवर भी देती है जो जमा नहीं देती, इसलिए दोनों तौलिए।")}


# =============================================================================== A4 UPI safety coach
# The few rules that explain almost every UPI fraud. Everything below is a case of one of these.
UPI_RULES = [
    ("Your UPI PIN is only for SENDING money. You never type it to receive money.", "UPI पिन सिर्फ़ पैसा भेजने के लिए है। पैसा पाने के लिए इसे कभी नहीं डालना पड़ता।"),
    ("A \"collect request\" or a QR code you scan means YOU pay. If someone says you will receive money by approving or scanning, it is a lie.", "\"कलेक्ट रिक्वेस्ट\" मंज़ूर करने या QR स्कैन करने का मतलब है कि पैसा आप भेज रहे हैं। कोई कहे कि इससे पैसा आएगा, तो वह झूठ है।"),
    ("No bank, company or officer needs your PIN, OTP, card number or CVV. Nobody. Not for a refund, KYC or prize.", "किसी बैंक, कंपनी या अधिकारी को आपका पिन, OTP, कार्ड नंबर या CVV नहीं चाहिए। किसी को नहीं। रिफ़ंड, KYC या इनाम के लिए भी नहीं।"),
    ("A real refund or credit arrives by itself. You never have to \"verify\" or \"activate\" it by paying or clicking.", "असली रिफ़ंड या जमा अपने आप आता है। उसे \"वेरिफ़ाई\" या \"चालू\" करने के लिए पैसे भेजने या लिंक दबाने की ज़रूरत नहीं।"),
    ("Never install a screen-sharing app (AnyDesk, TeamViewer, QuickSupport) because someone on the phone asked.", "फ़ोन पर किसी के कहने से कभी स्क्रीन-शेयरिंग ऐप (AnyDesk, TeamViewer, QuickSupport) न डालें।"),
    ("Find customer care only inside your own UPI app or on the bank's printed card/passbook, never by searching or from a message.", "कस्टमर केयर का नंबर सिर्फ़ अपने UPI ऐप के अंदर या बैंक के छपे कार्ड/पासबुक से लें, सर्च या मैसेज से नहीं।"),
]
UPI_RECOVER = {"en": "If you already paid, entered your PIN or shared a code: call 1930 now and tell your bank, then follow the scam recovery steps (the first hour matters).",
               "hi": "अगर आप पैसा भेज चुके, पिन डाल चुके या कोड बता चुके: अभी 1930 पर फ़ोन कीजिए और बैंक को बताइए, फिर ठगी-के-बाद के क़दम अपनाइए (पहला घंटा सबसे अहम है)।"}

# id, regex (English + Hindi), level, title, why, steps
UPI_CASES: list[dict[str, Any]] = [
    dict(id="receive_pin", level="red", rx=r"(receive|get|credit|refund).{0,40}(enter|put|type|give|share).{0,25}pin|(enter|put|type|give|share).{0,25}(pin).{0,40}(receive|get|credit|refund|money|payment)|(receive|get|credit|refund|incoming).{0,40}(need|have|must|should|asked).{0,25}(pin)|pin.{0,30}(to receive|to get)|पैसा (पाने|लेने|लेने के लिए|आने).{0,25}पिन|पिन.{0,30}(डालना|डालो|डालें|बताना).{0,30}(पैसा|रिफ़ंड|रिफंड|पाने)",
         en=("Stop. You never enter a PIN to receive money.", "रुकिए। पैसा पाने के लिए पिन कभी नहीं डालना पड़ता।"),
         why=("Entering a PIN always approves a payment OUT of your account. Fraudsters make it look like money is coming in.", "पिन डालने का मतलब हमेशा आपके खाते से पैसा जाना है। ठग इसे ऐसे दिखाते हैं जैसे पैसा आ रहा हो।"),
         do=[("Do not enter the PIN. Close the screen.", "पिन मत डालिए। स्क्रीन बंद कीजिए।"), ("Check your balance in the app: money that is really coming in just appears.", "ऐप में बैलेंस देखिए: असली आने वाला पैसा अपने आप दिख जाता है।")]),
    dict(id="collect", level="red", rx=r"collect request|payment request|request (money )?(from|on) (phonepe|gpay|google pay|paytm|upi)|approve (the |a )?(request|collect)|accept (the |a )?(request|collect)|कलेक्ट|रिक्वेस्ट (मंज़ूर|मंजूर|एक्सेप्ट|accept)",
         en=("This is a collect request: approving it sends YOUR money out.", "यह कलेक्ट रिक्वेस्ट है: मंज़ूर करने पर आपका पैसा जाएगा।"),
         why=("A collect request asks you to pay. Scammers say it will send you a refund or prize.", "कलेक्ट रिक्वेस्ट आपसे पैसा माँगता है। ठग कहते हैं कि इससे रिफ़ंड या इनाम आएगा।"),
         do=[("Decline it. Look at the amount and the name: it will say you are paying.", "इसे अस्वीकार कीजिए। रक़म और नाम देखिए: उसमें आपके पैसे देने की बात होगी।"), ("Do not continue the chat or call with that person.", "उस व्यक्ति से बातचीत आगे मत बढ़ाइए।")]),
    dict(id="qr_receive", level="red", rx=r"(scan|qr).{0,40}(receive|get|credit|refund|money|payment|sell|buyer)|(buyer|customer|olx|quikr|facebook marketplace).{0,40}(qr|scan)|qr code.{0,30}(sent|send|share)|क्यूआर|क्यू आर|qr.{0,20}स्कैन|स्कैन.{0,30}(पैसा|पैसे)",
         en=("Scanning a QR code sends money. It never receives it.", "QR स्कैन करने से पैसा जाता है, आता नहीं।"),
         why=("On sites like OLX a fake \"buyer\" sends a QR to \"pay you\". When you scan and enter your PIN, you pay them.", "OLX जैसी जगह नक़ली \"ख़रीदार\" \"आपको पैसे देने\" को QR भेजता है। आप स्कैन करके पिन डालते हैं तो पैसा आप देते हैं।"),
         do=[("Do not scan. To be paid, give your UPI ID or show your own QR.", "स्कैन मत कीजिए। पैसे लेने के लिए अपनी UPI आईडी दीजिए या अपना QR दिखाइए।"), ("Ask the buyer to pay you by sending to your ID, and wait for the credit message.", "ख़रीदार से कहिए आपकी आईडी पर भेजे, और जमा होने का संदेश आने तक रुकिए।")]),
    dict(id="mistaken_transfer", level="amber", rx=r"(sent|transferred|credited|received).{0,30}(by mistake|wrongly|wrong number|wrong account|galti)|(by mistake|wrongly|galti).{0,40}(send|sent|return|back|refund)|please (return|send back)|गलती से.{0,40}(भेज|आ गए|आया|लौटा|वापस)|वापस (कर दो|कीजिए|भेज)",
         en=("A \"mistaken\" transfer is a known trick. Do not return it to them yourself.", "\"गलती से\" भेजा पैसा एक जानी-पहचानी चाल है। उसे ख़ुद वापस न भेजिए।"),
         why=("The money can come from a stolen account or card; returning it from your account leaves you with the loss, or the first payment is reversed later.", "वह पैसा चोरी के खाते या कार्ड से आया हो सकता है; आप अपनी तरफ़ से लौटाएँगे तो नुक़सान आपका होगा, या पहला भुगतान बाद में पलट जाएगा।"),
         do=[("Tell your bank and let it handle the return. Do not send money to the person.", "बैंक को बताइए और वापसी उसी से करवाइए। उस व्यक्ति को पैसा मत भेजिए।"), ("Do not share your PIN, OTP or any link they send.", "उनका भेजा कोई पिन, OTP या लिंक मत इस्तेमाल कीजिए।")]),
    dict(id="remote_app", level="red", rx=r"anydesk|teamviewer|quick ?support|screen ?shar|remote (access|control|app)|rustdesk|एनीडेस्क|टीमव्यूअर|स्क्रीन शेयर|रिमोट",
         en=("Do not install it. This gives the caller full control of your phone and bank apps.", "इसे मत डालिए। इससे कॉल करने वाले को आपके फ़ोन और बैंक ऐप पर पूरा क़ाबू मिल जाता है।"),
         why=("With a screen-sharing app the fraudster sees your PIN and OTPs and moves money themselves.", "स्क्रीन-शेयरिंग ऐप से ठग आपका पिन और OTP देखकर ख़ुद पैसा भेज देता है।"),
         do=[("Cut the call. If the app is already installed, switch on airplane mode and uninstall it.", "कॉल काटिए। ऐप डल चुका हो तो एयरप्लेन मोड चालू करके उसे हटा दीजिए।"), ("Call your bank on the number printed on your card.", "कार्ड पर छपे नंबर पर बैंक को फ़ोन कीजिए।")]),
    dict(id="customer_care", level="red", rx=r"(customer care|helpline|support number|toll.?free).{0,40}(google|search|found|online|website|number)|(google|search|searched|online).{0,40}(customer care|helpline|support|refund)|कस्टमर केयर.{0,30}(गूगल|सर्च|नंबर)|गूगल पर.{0,30}(नंबर|कस्टमर)",
         en=("A number from a web search or message is often a fraudster's.", "वेब सर्च या मैसेज से मिला नंबर अक्सर ठग का होता है।"),
         why=("Fake care numbers are placed in search results. They ask for your PIN, a \"small payment\" or an app.", "नक़ली कस्टमर केयर नंबर सर्च में डाले जाते हैं। वे पिन, \"थोड़ा भुगतान\" या ऐप माँगते हैं।"),
         do=[("Hang up. Use the Help section inside your own UPI app, or the number on your card or passbook.", "फ़ोन रख दीजिए। अपने UPI ऐप का Help भाग या कार्ड/पासबुक पर छपा नंबर इस्तेमाल कीजिए।"), ("Never pay a \"verification\" amount.", "\"वेरिफ़िकेशन\" के नाम पर कभी पैसा मत भेजिए।")]),
    dict(id="refund_link", level="red", rx=r"refund.{0,40}(link|click|form|website|verify|activate|pay)|(click|open|tap).{0,30}link|cashback.{0,30}(link|claim|click)|link.{0,30}(refund|cashback|claim|kyc|update)|लिंक.{0,40}(रिफ़ंड|रिफंड|कैशबैक|केवाईसी|खोल|दबा)|रिफ़ंड.{0,40}लिंक",
         en=("Do not tap the link. Real refunds never need a link or a form.", "लिंक मत दबाइए। असली रिफ़ंड के लिए लिंक या फ़ॉर्म नहीं चाहिए।"),
         why=("The link opens a copy of a bank or UPI page that steals your card, PIN or OTP.", "लिंक बैंक या UPI जैसा नक़ली पेज खोलता है जो आपका कार्ड, पिन या OTP चुरा लेता है।"),
         do=[("Delete the message. Open your bank or UPI app yourself and check there.", "संदेश मिटा दीजिए। अपना बैंक या UPI ऐप ख़ुद खोलकर वहीं देखिए।"), ("Report the number to 1930 or cybercrime.gov.in.", "नंबर की शिकायत 1930 या cybercrime.gov.in पर कीजिए।")]),
    dict(id="kyc", level="red", rx=r"kyc|account (will be )?(blocked|suspended|closed|frozen)|sim (will be )?(blocked|deactivated)|electricity.{0,30}(cut|disconnect)|bill.{0,30}(disconnect|cut)|केवाईसी|खाता.{0,20}(बंद|ब्लॉक)|बिजली.{0,25}(कट|बंद)|सिम.{0,20}(बंद|ब्लॉक)",
         en=("A threat to block or cut something unless you act now is a scam pattern.", "\"अभी नहीं किया तो बंद\" वाली धमकी ठगी का तरीक़ा है।"),
         why=("Banks and utilities do not threaten by SMS or call, and do not collect PINs or ask for \"small payments\" to avoid cut-offs.", "बैंक और बिजली विभाग SMS या कॉल पर धमकी नहीं देते, न पिन माँगते हैं, न कटने से बचाने को \"थोड़ा भुगतान\"।"),
         do=[("Do not call the number in the message. Visit the branch or use the official app or website.", "संदेश वाले नंबर पर फ़ोन मत कीजिए। शाखा जाइए या आधिकारिक ऐप/वेबसाइट देखिए।")]),
    dict(id="small_test", level="red", rx=r"(ask|want|demand)s?.{0,20}small (payment|amount).{0,30}(verify|activate|confirm|unlock)|(send|pay|transfer).{0,15}(re\.? ?1|rs\.? ?1|₹ ?1|one rupee|1 rupee|₹ ?10|10 rupees|small amount|test payment).{0,40}(verify|activate|confirm|test|unlock)|(verify|activate|unlock).{0,40}(small|₹ ?1\b|one rupee|1 rupee)|एक रुपये?.{0,30}(भेज|वेरिफ़|वेरिफ)|थोड़ा पैसा.{0,30}(वेरिफ़|वेरिफ|चालू)",
         en=("A \"small verification payment\" is the first step of a bigger theft.", "\"वेरिफ़िकेशन के लिए थोड़ा भुगतान\" बड़ी चोरी का पहला क़दम है।"),
         why=("It tests that you will obey, or sends you to a fake page where the real amount is taken.", "इससे ठग परखता है कि आप कहना मानेंगे, या नक़ली पेज पर ले जाकर असली रक़म निकालता है।"),
         do=[("Do not send anything. No real service verifies you by taking money.", "कुछ मत भेजिए। कोई असली सेवा पैसा लेकर वेरिफ़ाई नहीं करती।")]),
    dict(id="prize", level="red", rx=r"lottery|prize|lucky draw|you (have )?won|won a|gift voucher|scratch card|cashback offer|लॉटरी|इनाम|लकी ड्रॉ|स्क्रैच",
         en=("You do not win prizes you never entered, and prizes never need payment.", "जिस इनाम में आपने हिस्सा नहीं लिया वह आपको नहीं मिलता, और इनाम के लिए पैसा नहीं देना पड़ता।"),
         why=("Fraudsters send a \"claim\" request or ask for a fee or your PIN.", "ठग \"क्लेम\" रिक्वेस्ट भेजते हैं या फ़ीस या पिन माँगते हैं।"),
         do=[("Ignore and block. Never pay to receive.", "नज़रअंदाज़ कीजिए और ब्लॉक कीजिए। पाने के लिए कभी भुगतान मत कीजिए।")]),
    dict(id="apk", level="red", rx=r"\.apk|apk file|install (this|the) (app|file)|download (this|the) (app|file)|app from (a )?(link|whatsapp|message)|एपीके|ऐप डाउनलोड|फ़ाइल डाउनलोड",
         en=("Never install an app from a message or link.", "मैसेज या लिंक से आया ऐप कभी न डालें।"),
         why=("Fake bank, KYC, PM-scheme and traffic-challan apps read your SMS and steal OTPs.", "नक़ली बैंक, KYC, सरकारी योजना और चालान ऐप आपके SMS पढ़कर OTP चुरा लेते हैं।"),
         do=[("Install apps only from the Play Store or App Store, from the real company.", "ऐप सिर्फ़ प्ले स्टोर/ऐप स्टोर से, असली कंपनी का डालिए।"), ("If installed already: uninstall, switch on airplane mode, call your bank.", "डल चुका हो तो हटाइए, एयरप्लेन मोड चालू कीजिए, बैंक को फ़ोन कीजिए।")]),
    dict(id="otp_pin", level="red", rx=r"(share|give|tell|send|read out).{0,25}(otp|pin|cvv|password)|(asked|wants?|needs?).{0,25}(my )?(otp|pin|cvv)|(otp|पिन|ओटीपी|सीवीवी).{0,25}(माँग|मांग|बता|बताओ|बताइए|पूछ)",
         en=("Never share your PIN, OTP or CVV with anyone.", "अपना पिन, OTP या CVV किसी को न बताएँ।"),
         why=("Anyone who asks for them, whatever they say they are, is stealing.", "जो भी माँगे, चाहे कुछ भी बताए, वह चोरी कर रहा है।"),
         do=[("Cut the call or stop replying. Call your bank on the number on your card.", "कॉल काटिए या जवाब देना बंद कीजिए। कार्ड के नंबर पर बैंक को फ़ोन कीजिए।")]),
]
UPI_MENU = [  # tappable situations (also the guide's choices)
    ("They say I will receive money if I enter my PIN", "कहते हैं पिन डालने से पैसा आएगा"),
    ("I got a collect or payment request", "मुझे कलेक्ट/पेमेंट रिक्वेस्ट आई"),
    ("A buyer sent a QR code to pay me", "ख़रीदार ने पैसे देने को QR भेजा"),
    ("Someone sent money by mistake and wants it back", "किसी ने गलती से पैसा भेजकर वापस माँगा"),
    ("They want me to install AnyDesk or a screen app", "AnyDesk या स्क्रीन ऐप डालने को कह रहे हैं"),
    ("I found a customer care number on Google", "गूगल पर कस्टमर केयर नंबर मिला"),
    ("A link for a refund, KYC or cashback", "रिफ़ंड, KYC या कैशबैक का लिंक"),
    ("They ask for a small payment to verify", "वेरिफ़ाई के लिए थोड़ा भुगतान माँगते हैं"),
]


def upi_check(text: str, lang: str = "en") -> dict[str, Any]:
    t = _tr(lang)
    low = (text or "").lower()
    case = next((c for c in UPI_CASES if re.search(c["rx"], low)), None)
    rules = [hi if lang == "hi" else en for en, hi in UPI_RULES]
    recover = UPI_RECOVER[lang]
    if case:
        i = 1 if lang == "hi" else 0
        return {"matched": case["id"], "level": case["level"], "headline": case["en"][i], "why": case["why"][i],
                "do": [d[i] for d in case["do"]], "rules": rules, "recover": recover,
                "verdict": (t("Very likely a scam. Do not pay or share anything.", "बहुत संभव है कि यह ठगी है। कुछ भी पैसा या जानकारी मत दीजिए।") if case["level"] == "red"
                            else t("A known trick. Be careful and do not send money yourself.", "एक जानी-पहचानी चाल है। सावधान रहिए और ख़ुद पैसा मत भेजिए।"))}
    return {"matched": None, "level": "amber",
            "headline": t("I could not match this to a known trick, so use the rules below.", "यह किसी जानी-पहचानी चाल से नहीं मिला, इसलिए नीचे के नियम अपनाइए।"),
            "why": t("Almost every UPI fraud asks you for one of: your PIN, an OTP, a scan, an approval, a click, an app, or a payment before you get anything.",
                     "लगभग हर UPI ठगी में इनमें से कुछ माँगा जाता है: पिन, OTP, स्कैन, मंज़ूरी, क्लिक, ऐप, या कुछ मिलने से पहले भुगतान।"),
            "do": [t("If any of those is being asked, stop. Describe it to me in a few words, or choose a situation.", "इनमें से कुछ भी माँगा जा रहा हो तो रुकिए। मुझे थोड़े शब्दों में बताइए, या कोई स्थिति चुनिए।")],
            "rules": rules, "recover": recover,
            "verdict": t("Not matched. If you are asked for a PIN, OTP, scan or click, treat it as a scam.", "मेल नहीं मिला। पिन, OTP, स्कैन या क्लिक माँगा जाए तो उसे ठगी मानिए।")}


# drills: a scenario, three choices, which is right and why
UPI_DRILLS: list[dict[str, Any]] = [
    dict(id="d1", s=("You sell a table on OLX. The buyer says: \"I'll pay by QR. Scan the code I sent and enter your PIN to receive.\"", "आप OLX पर मेज़ बेच रहे हैं। ख़रीदार कहता है: \"मैं QR से पैसे दे रहा हूँ। मेरा भेजा कोड स्कैन करके पैसा पाने के लिए पिन डालिए।\""),
         o=[("Scan it and enter the PIN", "स्कैन करके पिन डालूँ", 0), ("Refuse; give my UPI ID and wait for the credit message", "मना करूँ; अपनी UPI आईडी दूँ और जमा होने का संदेश देखूँ", 1), ("Scan it but not enter the PIN", "स्कैन करूँ पर पिन न डालूँ", 0)],
         why=("Scanning and the PIN both mean YOU pay. To be paid, only your UPI ID or your own QR is needed.", "स्कैन और पिन दोनों का मतलब आप पैसा दे रहे हैं। पैसे पाने के लिए सिर्फ़ आपकी UPI आईडी या आपका अपना QR चाहिए।")),
    dict(id="d2", s=("A caller says your electricity will be cut tonight unless you pay ₹10 to \"update\" your bill, and sends a link.", "कॉल आती है कि आज रात बिजली कट जाएगी जब तक आप बिल \"अपडेट\" करने को ₹10 न दें, और एक लिंक भेजते हैं।"),
         o=[("Pay ₹10, it is small", "₹10 ही तो हैं, भेज दूँ", 0), ("Ignore the link; check the bill in the official app or at the office", "लिंक छोड़ दूँ; आधिकारिक ऐप या दफ़्तर में बिल देखूँ", 1), ("Call the number back to argue", "उसी नंबर पर फ़ोन करके बहस करूँ", 0)],
         why=("The small amount is a hook: the link is a fake page. Utilities do not threaten by phone.", "छोटी रक़म चारा है: लिंक नक़ली पेज है। बिजली विभाग फ़ोन पर धमकाता नहीं।")),
    dict(id="d3", s=("Your phone shows \"Collect request from Customer Care ₹4,999 — Approve to get your refund\".", "आपके फ़ोन पर आता है \"कस्टमर केयर से ₹4,999 की कलेक्ट रिक्वेस्ट — रिफ़ंड पाने के लिए मंज़ूर करें\"।"),
         o=[("Approve, it says refund", "मंज़ूर करूँ, रिफ़ंड लिखा है", 0), ("Decline; a refund never needs approval", "अस्वीकार करूँ; रिफ़ंड में मंज़ूरी नहीं लगती", 1), ("Approve but with a smaller amount", "कम रक़म करके मंज़ूर करूँ", 0)],
         why=("A collect request takes money out. A refund just appears in your account.", "कलेक्ट रिक्वेस्ट से पैसा निकलता है। रिफ़ंड अपने आप खाते में आ जाता है।")),
    dict(id="d4", s=("A stranger sends you ₹5,000 and phones: \"Sorry, wrong number. Please send it back to me right now.\"", "कोई अनजान आपको ₹5,000 भेजकर फ़ोन करता है: \"माफ़ कीजिए, गलत नंबर पर गया। अभी वापस भेज दीजिए।\""),
         o=[("Return it quickly to be helpful", "मदद के लिए जल्दी लौटा दूँ", 0), ("Do not return it; tell my bank and let it reverse properly", "ख़ुद न लौटाऊँ; बैंक को बताऊँ ताकि वही ठीक से वापस करे", 1), ("Return half", "आधा लौटा दूँ", 0)],
         why=("The money may be from a stolen account. If you send yours, you lose it. The bank can reverse it safely.", "पैसा चोरी के खाते से हो सकता है। आप अपना भेजेंगे तो आपका जाएगा। बैंक सुरक्षित तरीक़े से वापस कर सकता है।")),
    dict(id="d5", s=("You searched Google for your bank's customer care. The number answers and asks you to install a \"support app\".", "आपने बैंक का कस्टमर केयर गूगल पर खोजा। नंबर पर कोई उठाकर \"सपोर्ट ऐप\" डालने को कहता है।"),
         o=[("Install it, they are helping", "डाल दूँ, वे मदद कर रहे हैं", 0), ("Hang up; use the number on my card or the app's Help", "फ़ोन रख दूँ; कार्ड का नंबर या ऐप का Help इस्तेमाल करूँ", 1), ("Install but do not log in", "डालूँ पर लॉग-इन न करूँ", 0)],
         why=("Search results can hold fake numbers; a screen app gives them control. Even installing is too much.", "सर्च में नक़ली नंबर हो सकते हैं; स्क्रीन ऐप से उन्हें क़ाबू मिलता है। डालना भी ठीक नहीं।")),
    dict(id="d6", s=("An SMS: \"Your account is blocked. Update KYC at this link today.\"", "SMS: \"आपका खाता ब्लॉक है। आज ही इस लिंक पर KYC अपडेट कीजिए।\""),
         o=[("Open the link and fill in details", "लिंक खोलकर जानकारी भरूँ", 0), ("Do not open; visit the branch or official app", "न खोलूँ; शाखा जाऊँ या आधिकारिक ऐप देखूँ", 1), ("Forward it to friends to warn them, after opening it", "पहले खोलकर देखूँ, फिर दोस्तों को भेजूँ", 0)],
         why=("Real KYC never comes with a threat and a link. Even opening an unknown link can be risky.", "असली KYC धमकी और लिंक के साथ नहीं आता। अनजान लिंक खोलना भी जोखिम है।")),
    dict(id="d7", s=("A friend you know messages: \"I'm stuck, urgent, can you send ₹3,000? New number.\"", "जान-पहचान वाला संदेश भेजता है: \"फँस गया हूँ, ज़रूरी है, ₹3,000 भेज दो? नया नंबर है।\""),
         o=[("Send it, he is a friend", "भेज दूँ, दोस्त है", 0), ("Call him on his old number first", "पहले उसके पुराने नंबर पर फ़ोन करूँ", 1), ("Ask him to send a selfie", "सेल्फ़ी माँग लूँ", 0)],
         why=("Hacked or copied accounts message everyone. A call on the old number settles it; a photo can be copied too.", "हैक या नक़ली अकाउंट सबको संदेश भेजते हैं। पुराने नंबर पर फ़ोन से बात साफ़ हो जाती है; फ़ोटो भी कॉपी हो सकती है।")),
    dict(id="d8", s=("You are told you won ₹25,000 in a scratch card and must pay ₹499 \"processing fee\" first.", "बताया जाता है कि आपने स्क्रैच कार्ड में ₹25,000 जीते हैं और पहले ₹499 \"प्रोसेसिंग फ़ीस\" देनी होगी।"),
         o=[("Pay ₹499, it is worth it", "₹499 दे दूँ, फ़ायदा है", 0), ("Ignore and block", "नज़रअंदाज़ करके ब्लॉक करूँ", 1), ("Pay half now, half later", "आधा अभी, आधा बाद में", 0)],
         why=("You cannot win what you never entered, and real prizes never ask for a fee.", "जिसमें हिस्सा नहीं लिया वह जीता नहीं जाता, और असली इनाम फ़ीस नहीं माँगता।")),
]


def upi_drills(lang: str = "en") -> dict[str, Any]:
    i = 1 if lang == "hi" else 0
    return {"drills": [{"id": d["id"], "scenario": d["s"][i], "why": d["why"][i],
                        "options": [{"text": o[i], "right": bool(o[2])} for o in d["o"]]} for d in UPI_DRILLS],
            "menu": [{"text": en, "label": hi if lang == "hi" else en} for en, hi in UPI_MENU],
            "rules": [hi if lang == "hi" else en for en, hi in UPI_RULES], "recover": UPI_RECOVER[lang]}


# =============================================================================== B3 DBT / subsidy tracer
# Why a government payment (DBT: direct benefit transfer) did not arrive. Money moves through a short
# chain: you are registered -> your record is approved -> your Aadhaar is linked to ONE bank account in
# NPCI's mapper -> the name and account details match -> the account is active -> the bank credits it.
# Almost every "it never came" is a break at one of those links. This ranks the likely breaks from
# what the person tells us and gives the exact fix for each. Scores are likelihood weights, not
# probabilities, and the screen says so.
DBT_SCHEMES = {  # id: (English, Hindi, needs_ekyc, where to check status)
    "pm_kisan": ("PM-KISAN", "पीएम-किसान", True, "pmkisan.gov.in → Know Your Status; helpline 155261 or 1800-115-526"),
    "pension": ("Pension (old-age, widow, disability)", "पेंशन (वृद्धावस्था, विधवा, दिव्यांग)", True, "your state social-welfare portal or the block / panchayat office"),
    "scholarship": ("Scholarship", "छात्रवृत्ति", True, "scholarships.gov.in → Check Status"),
    "lpg": ("LPG subsidy", "गैस सब्सिडी", False, "your gas distributor or the LPG company's app (PAHAL)"),
    "mgnrega": ("MGNREGA wages", "मनरेगा मज़दूरी", False, "nrega.nic.in → your panchayat's muster roll and payment status"),
    "ration": ("Ration / food subsidy", "राशन / खाद्य सब्सिडी", False, "your state food department portal or the ration shop"),
    "other": ("Another scheme", "कोई और योजना", False, "the scheme's own website or the block / panchayat office"),
}
DBT_STATUS = [("not_applied", "I never applied or I am not sure I am registered", "आवेदन नहीं किया या पता नहीं कि पंजीकृत हूँ"),
              ("pending", "It says pending or under process", "पेंडिंग या प्रक्रिया में दिखा रहा है"),
              ("rejected", "It says rejected or failed", "रिजेक्ट या फ़ेल दिखा रहा है"),
              ("approved", "It says approved or paid, but nothing came", "मंज़ूर या भुगतान दिखा रहा है, पर पैसा नहीं आया"),
              ("other_account", "It says paid, but to an account I do not know", "भुगतान दिखा रहा है, पर किसी अनजान खाते में"),
              ("no_status", "I cannot see any status", "कोई स्टेटस नहीं दिख रहा")]
DBT_YNU = ("yes", "no", "unsure")
DBT_USED = [("recent", "I used the account in the last few months", "पिछले कुछ महीनों में खाता चलाया"),
            ("old", "Not used for over a year", "एक साल से ज़्यादा से नहीं चलाया"),
            ("never", "Never used since opening", "खुलने के बाद कभी नहीं चलाया")]
FEE_SCAM = r"fee|commission|charge|bribe|pay (him|her|them|someone)|इनाम|फीस|फ़ीस|कमीशन|रिश्वत|पैसे माँग"


def _cause(cid: str, score: int, en: str, hi: str, why_en: str, why_hi: str, steps_en: list[str], steps_hi: list[str]) -> dict[str, Any]:
    return {"id": cid, "score": score, "en": en, "hi": hi, "why_en": why_en, "why_hi": why_hi, "steps_en": steps_en, "steps_hi": steps_hi}


def dbt_trace(scheme: str = "other", status: str = "no_status", linked: str = "unsure", name_same: str = "unsure",
              merged: str = "unsure", last_used: str = "recent", aadhaar_mobile: str = "unsure", text: str = "",
              lang: str = "en") -> dict[str, Any]:
    t = _tr(lang)
    sch = DBT_SCHEMES.get(scheme, DBT_SCHEMES["other"])
    needs_ekyc = sch[2]
    causes: list[dict[str, Any]] = []

    def add(*a):
        causes.append(_cause(*a))

    if status == "not_applied":
        add("not_registered", 95, "You may not be registered, or the application was never completed",
            "आप पंजीकृत नहीं हो सकते, या आवेदन पूरा नहीं हुआ",
            "A payment cannot be sent to a record that does not exist.", "जो रिकॉर्ड है ही नहीं उस पर भुगतान नहीं भेजा जा सकता।",
            [f"Check or apply: {sch[3]}", "Ask the panchayat / block office or a Common Service Centre to look up your name with your Aadhaar number.", "Apply yourself or at a CSC. Nobody may charge a fee to register you."],
            [f"जाँचिए या आवेदन कीजिए: {sch[3]}", "पंचायत / ब्लॉक कार्यालय या कॉमन सर्विस सेंटर से अपने आधार नंबर से नाम खोजवाइए।", "आवेदन ख़ुद या CSC पर कीजिए। पंजीकरण के लिए किसी को फ़ीस देने की ज़रूरत नहीं।"])
    if status == "other_account":
        add("wrong_account", 92, "The money went to a different bank account linked to your Aadhaar",
            "पैसा आपके आधार से जुड़े किसी दूसरे बैंक खाते में गया",
            "DBT goes to the account most recently linked to your Aadhaar in NPCI's mapper, which may be an old or other account (for example a new Jan Dhan or a bank you tried once).",
            "DBT आपके आधार से सबसे हाल में जुड़े खाते में जाता है (NPCI मैपर में), जो कोई पुराना या दूसरा खाता हो सकता है (जैसे नया जन धन या एक बार खोला गया बैंक)।",
            ["Ask the bank where the credit went and for the account number's last 4 digits.", "Get the right account made the active one: fill the Aadhaar-seeding form for the account you want, at that bank branch.", "Keep the written acknowledgement. Next payments go to the newest linked account."],
            ["बैंक से पूछिए कि पैसा कहाँ गया और खाते के आख़िरी 4 अंक क्या हैं।", "जो खाता चाहिए उसी बैंक शाखा में आधार-सीडिंग फ़ॉर्म भरकर उसे चालू खाता बनवाइए।", "लिखित पावती रखिए। आगे का भुगतान सबसे नए जुड़े खाते में जाएगा।"])
    if status == "rejected":
        add("rejected", 85, "The record was rejected, usually for a data error", "रिकॉर्ड रिजेक्ट हुआ है, आम तौर पर डेटा की गलती से",
            "Common reasons: name or account number does not match, wrong IFSC, Aadhaar not verified, or the account is closed.", "आम वजहें: नाम या खाता नंबर नहीं मिलता, गलत IFSC, आधार सत्यापित नहीं, या खाता बंद।",
            [f"Open the status page and read the exact reason: {sch[3]}", "Correct that item (usually at the bank or the block office), then ask for the record to be re-submitted.", "Ask for the correction in writing and keep the receipt."],
            [f"स्टेटस पेज खोलकर सही वजह पढ़िए: {sch[3]}", "वही चीज़ ठीक कराइए (अक्सर बैंक या ब्लॉक कार्यालय में), फिर रिकॉर्ड दोबारा भिजवाने को कहिए।", "सुधार लिखित में माँगिए और रसीद रखिए।"])
    if status == "pending":
        add("pending", 60, "It is still waiting for approval, or for a step on your side", "यह अभी मंज़ूरी का, या आपकी तरफ़ के किसी चरण का इंतज़ार कर रहा है",
            "Records wait at the block or state level, and some need an e-KYC, land or bank check from you before moving on.", "रिकॉर्ड ब्लॉक या राज्य स्तर पर रुकते हैं, और कुछ को आगे बढ़ने से पहले आपका e-KYC, ज़मीन या बैंक सत्यापन चाहिए।",
            [f"Read the status page for a pending item: {sch[3]}", "Ask the block / panchayat office who the record is pending with, and by when.", "If it is an e-KYC or similar step, complete it at a CSC (free or a small government-set fee)."],
            [f"स्टेटस पेज पर लंबित चरण देखिए: {sch[3]}", "ब्लॉक / पंचायत कार्यालय से पूछिए कि रिकॉर्ड किसके पास रुका है और कब तक चलेगा।", "e-KYC जैसा कोई चरण हो तो CSC पर पूरा कीजिए (मुफ़्त या सरकार की तय छोटी फ़ीस)।"])
    if status == "approved":
        add("credit_failed", 55, "Approved, but the bank did not credit it", "मंज़ूर हो गया, पर बैंक ने जमा नहीं किया",
            "The state sent it but the bank returned it: wrong or changed IFSC, closed or frozen account, or Aadhaar not linked.", "राज्य ने भेजा पर बैंक ने लौटा दिया: गलत या बदला हुआ IFSC, बंद या फ़्रीज़ खाता, या आधार नहीं जुड़ा।",
            ["Ask the bank in writing: was a credit received against my Aadhaar, and if returned, what was the reason code.", "Fix that reason (see the items below), then ask the scheme office to re-send."],
            ["बैंक से लिखित में पूछिए: मेरे आधार पर क्रेडिट आया था क्या, और लौटा तो कारण कोड क्या था।", "वह कारण ठीक कीजिए (नीचे की बातें देखिए), फिर योजना कार्यालय से दोबारा भिजवाने को कहिए।"])
    if linked == "no":
        add("not_seeded", 90, "Your Aadhaar is not linked to the bank account for benefit transfers", "आपका आधार लाभ हस्तांतरण के लिए बैंक खाते से जुड़ा नहीं है",
            "Without this link the payment has nowhere to go. Having an Aadhaar and a bank account separately is not enough.", "इस जुड़ाव के बिना भुगतान जाएगा कहाँ? आधार और बैंक खाता अलग-अलग होना काफ़ी नहीं।",
            ["Check: myaadhaar.uidai.gov.in → Bank Seeding Status (login with Aadhaar and OTP).", "If not linked: fill the Aadhaar-seeding form at your bank branch and get a stamped copy.", "Wait about a week, then ask the scheme office to re-send."],
            ["जाँचिए: myaadhaar.uidai.gov.in → Bank Seeding Status (आधार और OTP से लॉग-इन)।", "जुड़ा न हो तो बैंक शाखा में आधार-सीडिंग फ़ॉर्म भरिए और मुहर लगी प्रति लीजिए।", "लगभग एक हफ़्ते बाद योजना कार्यालय से दोबारा भिजवाने को कहिए।"])
    elif linked == "unsure":
        add("not_seeded", 55, "Check whether your Aadhaar is really linked to this bank account", "जाँचिए कि आपका आधार सच में इस बैंक खाते से जुड़ा है",
            "Many people think it is linked because the bank has their Aadhaar, but benefit-transfer linking is a separate step.", "कई लोग मानते हैं कि जुड़ा है क्योंकि बैंक के पास आधार है, पर लाभ हस्तांतरण का जुड़ाव अलग चरण है।",
            ["Check: myaadhaar.uidai.gov.in → Bank Seeding Status.", "Or ask the bank: is my Aadhaar seeded for DBT with the NPCI mapper?"],
            ["जाँचिए: myaadhaar.uidai.gov.in → Bank Seeding Status।", "या बैंक से पूछिए: क्या मेरा आधार NPCI मैपर में DBT के लिए सीडेड है?"])
    if name_same == "no":
        add("name_mismatch", 85, "Your name is spelled differently on Aadhaar, the bank and the scheme", "आधार, बैंक और योजना में आपके नाम की वर्तनी अलग है",
            "The match is checked by computer. Initials, a missing surname or a spelling difference makes it fail.", "मिलान कंप्यूटर करता है। इनिशियल, छूटा हुआ सरनेम या वर्तनी का फ़र्क़ इसे फ़ेल कर देता है।",
            ["Compare the three exactly: Aadhaar, bank passbook, scheme record.", "Correct the one that is different. The bank passbook is usually the quickest: take Aadhaar to the branch.", "Then ask the scheme office to update its record to match."],
            ["तीनों को अक्षर-अक्षर मिलाइए: आधार, बैंक पासबुक, योजना का रिकॉर्ड।", "जो अलग है उसे ठीक कराइए। बैंक पासबुक अक्सर सबसे जल्दी होती है: आधार लेकर शाखा जाइए।", "फिर योजना कार्यालय से अपना रिकॉर्ड भी वैसा ही कराइए।"])
    elif name_same == "unsure":
        add("name_mismatch", 40, "Check that your name matches exactly in all three places", "तीनों जगह नाम का हूबहू मिलना जाँचिए",
            "A small spelling difference is a very common reason for silent failure.", "वर्तनी का छोटा फ़र्क़ चुपचाप फ़ेल होने की बहुत आम वजह है।",
            ["Lay the Aadhaar, passbook and any scheme slip side by side and compare each letter."], ["आधार, पासबुक और योजना की पर्ची साथ रखकर हर अक्षर मिलाइए।"])
    if last_used in ("old", "never"):
        add("dormant", 70 if last_used == "old" else 60, "The account may be inactive (dormant) or have pending KYC", "खाता निष्क्रिय (डॉर्मेंट) हो सकता है या उसका KYC लंबित हो सकता है",
            "Banks stop credits to accounts with no customer-made transaction for a long time (often 1 to 2 years) until KYC is refreshed.", "लंबे समय (अक्सर 1 से 2 साल) तक ग्राहक का कोई लेन-देन न हो तो बैंक KYC नया होने तक जमा रोक देते हैं।",
            ["Go to the branch with Aadhaar and ask to reactivate the account and update KYC.", "Make a small deposit or withdrawal to show it is in use.", "Ask the scheme office to re-send once it is active."],
            ["आधार लेकर शाखा जाइए और खाता दोबारा चालू कराने और KYC अपडेट करने को कहिए।", "थोड़ी रक़म जमा या निकालकर खाते को चालू दिखाइए।", "चालू होने के बाद योजना कार्यालय से दोबारा भिजवाने को कहिए।"])
    if merged == "yes":
        add("merged_bank", 65, "Your bank merged or changed its codes, so the old IFSC may be dead", "आपके बैंक का विलय हुआ या कोड बदले, इसलिए पुराना IFSC बेकार हो सकता है",
            "After bank mergers many branches got new IFSC and account details. A scheme record with the old ones fails.", "बैंक विलय के बाद कई शाखाओं के IFSC और खाता विवरण बदल गए। पुराने विवरण वाला रिकॉर्ड फ़ेल हो जाता है।",
            ["Read the IFSC printed on your latest passbook or cheque.", "Ask the scheme office to update the bank details in your record to the current IFSC."],
            ["अपनी ताज़ा पासबुक या चेक पर छपा IFSC देखिए।", "योजना कार्यालय से अपने रिकॉर्ड में बैंक विवरण नए IFSC से अपडेट करवाइए।"])
    elif merged == "unsure":
        add("merged_bank", 20, "If your bank has merged with another, update the IFSC in your record", "आपका बैंक किसी में मिला हो तो अपने रिकॉर्ड में IFSC अपडेट कराइए",
            "Merged banks changed many IFSC codes.", "विलय वाले बैंकों के कई IFSC बदले।", ["Compare the IFSC on your passbook with the one in your scheme record."], ["पासबुक का IFSC और योजना के रिकॉर्ड का IFSC मिलाइए।"])
    if aadhaar_mobile in ("no", "unsure"):
        add("mobile", 50 if (aadhaar_mobile == "no" and needs_ekyc) else 25, "Your Aadhaar may not have a working mobile number", "आपके आधार में चालू मोबाइल नंबर न हो सकता है",
            "e-KYC and many checks send an OTP to the number on your Aadhaar. Without it they cannot be completed.", "e-KYC और कई जाँचों में आधार वाले नंबर पर OTP आता है। उसके बिना वे पूरे नहीं होते।",
            ["Update the mobile number at an Aadhaar centre (a small fee applies).", "Then redo the e-KYC / verification step."], ["आधार केंद्र पर मोबाइल नंबर अपडेट कराइए (छोटी फ़ीस लगती है)।", "फिर e-KYC / सत्यापन दोबारा कीजिए।"])
    if needs_ekyc and status in ("pending", "approved", "no_status") and aadhaar_mobile != "no":
        add("ekyc", 45, "An e-KYC or verification step may be pending", "e-KYC या सत्यापन का कोई चरण लंबित हो सकता है",
            "Some schemes stop paying until e-KYC (OTP or fingerprint) is done.", "कुछ योजनाएँ e-KYC (OTP या फ़िंगरप्रिंट) होने तक भुगतान रोक देती हैं।", [f"Check on the scheme site and finish e-KYC at a CSC: {sch[3]}"], [f"योजना की साइट देखिए और CSC पर e-KYC पूरा कीजिए: {sch[3]}"])
    add("timing", 20, "Payments are released in batches, so it may simply not be your turn yet", "भुगतान बैचों में जारी होते हैं, हो सकता है अभी आपकी बारी न आई हो",
        "Even a correct record can wait a few weeks inside a payment period.", "सही रिकॉर्ड भी भुगतान अवधि में कुछ हफ़्ते रुक सकता है।", ["Check the status page for the date of the last release.", "Check your passbook and SMS, not only the app: it may already be there."],
        ["स्टेटस पेज पर पिछली रिलीज़ की तारीख़ देखिए।", "सिर्फ़ ऐप नहीं, पासबुक और SMS भी देखिए: पैसा आ चुका हो सकता है।"])
    causes.sort(key=lambda c: -c["score"])
    i = 1 if lang == "hi" else 0
    scam = bool(re.search(FEE_SCAM, (text or "").lower()))
    out = [{"id": c["id"], "score": c["score"], "title": c["hi" if i else "en"], "why": c["why_hi" if i else "why_en"], "steps": c["steps_hi" if i else "steps_en"]} for c in causes[:5]]
    first = out[0]
    head = t(f"Most likely: {first['title']}.", f"सबसे संभावित: {first['title']}।")
    return {"scheme": sch[1] if i else sch[0], "check_at": sch[3], "headline": head, "causes": out, "top": first["id"],
            "scam": scam,
            "scam_note": t("If anyone asks you for a fee, commission or gift to release or speed up a government payment, that is a fraud or a bribe. Real DBT never needs it. Report it to 1930 or the district officer.",
                           "कोई सरकारी भुगतान जारी या तेज़ करने के बदले फ़ीस, कमीशन या तोहफ़ा माँगे तो वह ठगी या रिश्वत है। असली DBT में इसकी ज़रूरत नहीं। 1930 या ज़िला अधिकारी को बताइए।"),
            "complain": [t("Scheme grievance portal: pgportal.gov.in (CPGRAMS), free. Keep the registration number.", "शिकायत पोर्टल: pgportal.gov.in (CPGRAMS), मुफ़्त। पंजीकरण संख्या रखिए।"),
                         t("Also tell the block development office / gram panchayat and your bank branch manager, in writing.", "ब्लॉक विकास कार्यालय / ग्राम पंचायत और बैंक शाखा प्रबंधक को भी लिखित में बताइए।")],
            "note": t("Scores are rough likelihood weights from the answers you gave, not probabilities. Rules and portals change: confirm on the official site.", "स्कोर आपके जवाबों से बने मोटे संभावना-भार हैं, संभावनाएँ नहीं। नियम और पोर्टल बदलते हैं: आधिकारिक साइट पर पक्का कीजिए।")}


def dbt_letter(scheme: str = "other", name: str = "", village: str = "", block: str = "", bank: str = "", top: str = "", lang: str = "en") -> dict[str, str]:
    """A short written complaint the person can hand in or send. Their own details are dropped into blanks."""
    sch = DBT_SCHEMES.get(scheme, DBT_SCHEMES["other"])
    nm, vl, bk, bn = name or "________", village or "________", block or "________", bank or "________"
    if lang == "hi":
        body = (f"सेवा में,\nखंड विकास अधिकारी / संबंधित कार्यालय, {bk}\n\nविषय: {sch[1]} का भुगतान प्राप्त न होने की शिकायत\n\n"
                f"महोदय,\nमैं {nm}, ग्राम {vl}, {sch[1]} का लाभार्थी हूँ। मुझे अपना भुगतान प्राप्त नहीं हुआ है। मेरा बैंक खाता {bn} में है और आधार से जुड़ा है। "
                f"कृपया मेरे रिकॉर्ड की स्थिति बताएँ, कमी (यदि कोई हो) का कारण लिखित में दें, और उसे ठीक कर भुगतान जारी करवाएँ।\n\n"
                f"मेरे पास आधार, बैंक पासबुक और पंजीकरण की रसीद है। मैं किसी प्रकार का शुल्क नहीं दूँगा/दूँगी।\n\nभवदीय,\n{nm}\nदिनांक: ________   मोबाइल: ________")
        bank_letter = (f"सेवा में,\nशाखा प्रबंधक, {bn}\n\nविषय: DBT क्रेडिट की जानकारी और आधार सीडिंग की पुष्टि\n\n"
                       f"महोदय,\nमैं {nm}, इस शाखा का खाताधारक हूँ। कृपया लिखित में बताएँ: (1) क्या मेरा आधार NPCI मैपर में इस खाते से DBT के लिए जुड़ा है; "
                       f"(2) क्या {sch[1]} के नाम पर कोई क्रेडिट आया या लौटाया गया, और लौटाया तो कारण कोड क्या है; (3) क्या खाता चालू है और KYC पूरा है।\n\nभवदीय,\n{nm}\nदिनांक: ________")
    else:
        body = (f"To,\nThe Block Development Officer / concerned office, {bk}\n\nSubject: Complaint of non-receipt of {sch[0]} payment\n\n"
                f"Sir/Madam,\nI am {nm} of village {vl}, a beneficiary of {sch[0]}. I have not received my payment. My bank account is with {bn} and is linked with my Aadhaar. "
                f"Please tell me the status of my record, give me in writing the reason for any problem, and have it corrected and the payment released.\n\n"
                f"I hold my Aadhaar, bank passbook and registration receipt. I will not pay any fee.\n\nYours faithfully,\n{nm}\nDate: ________   Mobile: ________")
        bank_letter = (f"To,\nThe Branch Manager, {bn}\n\nSubject: Request for DBT credit details and Aadhaar-seeding confirmation\n\n"
                       f"Sir/Madam,\nI am {nm}, an account holder at this branch. Please confirm in writing: (1) whether my Aadhaar is linked to this account for DBT in the NPCI mapper; "
                       f"(2) whether any credit for {sch[0]} was received or returned, and if returned, the reason code; (3) whether the account is active with KYC complete.\n\nYours faithfully,\n{nm}\nDate: ________")
    return {"office": body, "bank": bank_letter}


def dbt_full(scheme: str = "other", status: str = "no_status", linked: str = "unsure", name_same: str = "unsure", merged: str = "unsure",
             last_used: str = "recent", aadhaar_mobile: str = "unsure", text: str = "", name: str = "", village: str = "", block: str = "",
             bank: str = "", lang: str = "en") -> dict[str, Any]:
    out = dbt_trace(scheme, status, linked, name_same, merged, last_used, aadhaar_mobile, text, lang)
    out["letters"] = dbt_letter(scheme, name, village, block, bank, out["top"], lang)
    return out


# =============================================================================== C3 sell now or hold the crop?
# The honest version of "mandi price timing". Nobody can predict next season's price, and this does not
# try. It answers the two questions a farmer can actually settle: (1) how much higher must the price
# be later just to break even once storage, shrinkage, handling and the cost of money are counted, and
# (2) in the farmer's OWN past prices (pasted in), how often did the price rise that much between these
# two months? Prices are never supplied by the app.
MONTH_NAMES = {m: i for i, names in enumerate(
    [("jan", "january"), ("feb", "february"), ("mar", "march"), ("apr", "april"), ("may",), ("jun", "june"), ("jul", "july"),
     ("aug", "august"), ("sep", "sept", "september"), ("oct", "october"), ("nov", "november"), ("dec", "december")], 1) for m in names}


def parse_prices(text: str) -> list[tuple[int, int, float]]:
    """(year, month, price) from lines like '2023-10 2100', '2023-10-14, 2,150', 'Oct 2023: 2100', '10/2023 2100'."""
    out: list[tuple[int, int, float]] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        y = m = None
        mt = re.search(r"\b(20\d\d)[-/.](\d{1,2})(?:[-/.]\d{1,2})?\b", line)
        rest = line
        if mt and 1 <= int(mt.group(2)) <= 12:
            y, m = int(mt.group(1)), int(mt.group(2))
            rest = line.replace(mt.group(0), " ", 1)
        else:
            mt = re.search(r"\b([A-Za-z]{3,9})\.?[ ,\-]*(20\d\d)\b", line)
            if mt and mt.group(1).lower() in MONTH_NAMES:
                y, m = int(mt.group(2)), MONTH_NAMES[mt.group(1).lower()]
                rest = line.replace(mt.group(0), " ", 1)
            else:
                mt = re.search(r"\b(\d{1,2})[/\-](20\d\d)\b", line)
                if mt and 1 <= int(mt.group(1)) <= 12:
                    y, m = int(mt.group(2)), int(mt.group(1))
                    rest = line.replace(mt.group(0), " ", 1)
        if y is None:
            continue
        nums = re.findall(r"\d[\d,]*(?:\.\d+)?", rest)
        if nums:
            p = float(nums[-1].replace(",", ""))
            if p > 0:
                out.append((y, m, p))
    return out


def _median(xs: list[float]) -> float:
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def hold_or_sell(qty: float, price_now: float, months: int, price_later: float | None = None, storage_per_q_month: float = 0.0,
                 shrink_pct_month: float = 0.0, handling_per_q: float = 0.0, rate_pct_year: float = 7.0, history_text: str = "",
                 from_month: int | None = None, lang: str = "en") -> dict[str, Any]:
    t = _tr(lang)
    qty, months = max(0.0, float(qty)), max(1, int(months))
    price_now = float(price_now)
    keep = (1 - shrink_pct_month / 100) ** months                       # share of the crop left after shrinkage
    sell_now = qty * price_now
    now_future = sell_now * (1 + rate_pct_year / 100 * months / 12)       # the cash, put to work, after the same months
    cost = qty * storage_per_q_month * months + qty * handling_per_q
    breakeven = (now_future + cost) / (qty * keep) if qty and keep else None
    rise_needed = ((breakeven / price_now) - 1) * 100 if breakeven else None
    hold_value = (qty * keep * float(price_later) - cost) if price_later else None
    gain = (hold_value - now_future) if hold_value is not None else None

    hist = parse_prices(history_text)
    m0 = int(from_month) if from_month else None
    years: list[dict[str, Any]] = []
    season: list[dict[str, Any]] = []
    hit = None
    if hist:
        by: dict[tuple[int, int], list[float]] = {}
        for y, m, p in hist:
            by.setdefault((y, m), []).append(p)
        avg = {k: sum(v) / len(v) for k, v in by.items()}
        mo_vals: dict[int, list[float]] = {}
        for (y, m), p in avg.items():
            mo_vals.setdefault(m, []).append(p)
        allavg = sum(avg.values()) / len(avg)
        season = [{"month": m, "avg": round(sum(v) / len(v)), "index": round(sum(v) / len(v) / allavg * 100), "years": len(v)} for m, v in sorted(mo_vals.items())]
        if m0:
            m1 = (m0 - 1 + months) % 12 + 1
            carry = (m0 - 1 + months) // 12
            for y in sorted({k[0] for k in avg}):
                a, b = avg.get((y, m0)), avg.get((y + carry, m1))
                if a and b:
                    years.append({"year": y, "from": round(a), "to": round(b), "rise_pct": round((b / a - 1) * 100, 1)})
            if years and rise_needed is not None:
                hit = {"n": len(years), "enough": sum(1 for y in years if y["rise_pct"] >= rise_needed),
                       "median_rise": round(_median([y["rise_pct"] for y in years]), 1),
                       "worst": min(y["rise_pct"] for y in years), "best": max(y["rise_pct"] for y in years)}

    # The verdict never rests on a guess alone: it needs the expected price to clear the break-even, and, if the
    # farmer's own history was given, for that to have happened in most of those years.
    if price_later is None and hit is None:
        band = "amber"
        head = t(f"To come out ahead by waiting {months} months, the price must reach about ₹{breakeven:,.0f} a quintal: {rise_needed:.1f}% higher than today's ₹{price_now:,.0f}.",
                 f"{months} महीने रुकने पर फ़ायदे में रहने के लिए भाव लगभग ₹{breakeven:,.0f} प्रति क्विंटल होना चाहिए: आज के ₹{price_now:,.0f} से {rise_needed:.1f}% ऊँचा।")
        verdict = t("Compare that with what mandi prices usually do in your area (the last few years), then decide.", "इसकी तुलना अपने इलाक़े में मंडी के भाव की आम चाल (पिछले कुछ साल) से कीजिए, फिर तय कीजिए।")
    else:
        enough = hit["enough"] / hit["n"] if hit else None
        good_guess = gain is not None and gain > 0
        if gain is not None and gain <= 0 and (enough is None or enough < 0.5):
            band = "red"
        elif (gain is None or gain > 0) and (enough is None or enough >= 0.7):
            band = "green"
        else:
            band = "amber"
        head = t((f"If the price reaches ₹{price_later:,.0f}, holding {'gains' if (gain or 0) > 0 else 'loses'} about ₹{abs(gain):,.0f} after all costs. " if gain is not None else "")
                 + (f"In your own history it rose by enough in {hit['enough']} of {hit['n']} years." if hit else ""),
                 (f"भाव ₹{price_later:,.0f} तक पहुँचे तो रुकने से सारे ख़र्च के बाद लगभग ₹{abs(gain):,.0f} {'फ़ायदा' if (gain or 0) > 0 else 'नुक़सान'} होगा। " if gain is not None else "")
                 + (f"आपके अपने इतिहास में {hit['n']} में से {hit['enough']} साल भाव इतना बढ़ा।" if hit else ""))
        verdict = {"green": t("Holding looks worth it on your own numbers. Prices can still fall: hold only what you can afford to wait on.", "आपके अपने आँकड़ों से रुकना फ़ायदे का लगता है। भाव गिर भी सकता है: उतना ही रोकिए जिसका इंतज़ार झेल सकें।"),
                   "amber": t("It is not clear-cut. If you need cash soon, or owe money at high interest, selling now is the safer choice.", "साफ़ नहीं है। जल्दी नक़द चाहिए, या महँगा क़र्ज़ है, तो अभी बेचना ज़्यादा सुरक्षित है।"),
                   "red": t("Waiting loses money on these numbers. Selling now is better.", "इन आँकड़ों पर रुकने से घाटा है। अभी बेचना बेहतर है।")}[band]
    cash = t("Costs counted: storage, shrinkage, handling and what the money would earn or save.", "गिने गए ख़र्च: भंडारण, छीजन, ढुलाई, और पैसे से मिलने वाली कमाई या बचत।")
    return {"band": band, "headline": head, "verdict": verdict, "sell_now": round(sell_now), "sell_now_future": round(now_future),
            "breakeven_price": None if breakeven is None else round(breakeven, 1), "rise_needed_pct": None if rise_needed is None else round(rise_needed, 1),
            "hold_value": None if hold_value is None else round(hold_value), "gain": None if gain is None else round(gain), "holding_costs": round(cost),
            "crop_left_pct": round(keep * 100, 1), "years": years, "history": hit, "season": season, "n_history": len(hist), "cash_note": cash,
            "warn": t("Prices can move either way and no one can promise a rise. This uses your numbers and your own past prices, never a forecast.", "भाव किसी भी तरफ़ जा सकता है और बढ़ने का वादा कोई नहीं कर सकता। यह आपके आँकड़ों और आपके अपने पुराने भावों से बना है, कोई पूर्वानुमान नहीं।"),
            "tip": t("If you must borrow against the crop at a moneylender's rate, waiting almost never pays: check the rate in the Moneylender tool. A bank or Kisan Credit Card loan, or a warehouse-receipt loan, costs far less.", "फ़सल के बदले साहूकार की दर पर क़र्ज़ लेना पड़े तो रुकना लगभग कभी फ़ायदे का नहीं: दर साहूकार वाले औज़ार में जाँचिए। बैंक या किसान क्रेडिट कार्ड, या गोदाम-रसीद पर क़र्ज़ कहीं सस्ता है।")}


# =============================================================================== E1 daily-wage saving helper
# "Rs 10 a day" thinking, made real. Two questions, same arithmetic: (a) I want X rupees in N months for a
# goal (a daughter's marriage, a roof, a cow): how much a day? (b) I can put aside Y a day: what does it
# become in N months, and how long to reach X? Compared across: cash kept at home (no growth, and it leaks),
# and a recurring deposit (RD, interest compounded quarterly as post-office RDs do). The rate is an
# illustration the screen labels as such; rates change.
SAVE_GOALS = {  # id: (English, Hindi)
    "daughter": ("Daughter's marriage or education", "बेटी की शादी या पढ़ाई"), "son": ("Son's education", "बेटे की पढ़ाई"),
    "house": ("House or roof repair", "मकान या छत की मरम्मत"), "medical": ("Medical emergency fund", "इलाज के लिए आपात निधि"),
    "animal": ("Cow, buffalo or goat", "गाय, भैंस या बकरी"), "tools": ("Tools, cart or a small shop", "औज़ार, ठेला या छोटी दुकान"),
    "festival": ("Festival or wedding in the family", "त्योहार या घर की शादी"), "oldage": ("Old age", "बुढ़ापा"), "other": ("Something else", "कुछ और"),
}
SAVE_PLACES = [  # (English, Hindi, rate shown as illustration, note_en, note_hi)
    ("Post Office Recurring Deposit (5 years)", "डाकघर आवर्ती जमा (5 साल)", 6.7, "From ₹100 a month; backed by the government; interest added every 3 months.", "₹100 महीने से; सरकार की गारंटी; ब्याज हर 3 महीने जुड़ता है।"),
    ("Bank recurring deposit", "बैंक की आवर्ती जमा", 6.5, "Any bank; some allow weekly or small amounts. Ask for the penalty if you miss a month.", "कोई भी बैंक; कुछ में छोटी रक़म चलती है। महीना चूकने पर जुर्माना पूछ लीजिए।"),
    ("Sukanya Samriddhi (only for a girl under 10)", "सुकन्या समृद्धि (सिर्फ़ 10 साल से छोटी बेटी के लिए)", 8.2, "From ₹250 a year; the best rate; money is locked until she is older.", "साल के ₹250 से; सबसे अच्छी दर; बेटी के बड़े होने तक पैसा बंद रहता है।"),
    ("Self-help group savings", "स्वयं सहायता समूह की बचत", 0.0, "Small weekly savings plus cheap group loans in an emergency. Rate depends on the group.", "छोटी साप्ताहिक बचत और ज़रूरत पर सस्ता समूह ऋण। दर समूह पर निर्भर।"),
]


def _rd_factor(months: int, rate_pct: float) -> float:
    """What Rs 1 deposited at the start of every month for `months` months is worth at the end, quarterly compounding."""
    q = 1 + rate_pct / 100 / 4
    return sum(q ** ((months - k) / 3) for k in range(months))      # deposit k has (months - k) months to grow


def rd_maturity(monthly: float, months: int, rate_pct: float) -> float:
    return monthly * _rd_factor(max(0, int(months)), rate_pct)


def months_to_reach(target: float, monthly: float, rate_pct: float, cap: int = 600) -> int | None:
    if monthly <= 0 or target <= 0:
        return None
    for n in range(1, cap + 1):
        if rd_maturity(monthly, n, rate_pct) >= target:
            return n
    return None


def daily_saving(goal: str = "other", target: float | None = None, months: int | None = None, daily: float | None = None,
                 daily_wage: float | None = None, days_per_month: int = 26, rate_pct: float = 6.7, inflation_pct: float = 6.0,
                 lang: str = "en") -> dict[str, Any]:
    t = _tr(lang)
    i = 1 if lang == "hi" else 0
    dpm = max(1, min(31, int(days_per_month)))
    out: dict[str, Any] = {"goal": SAVE_GOALS.get(goal, SAVE_GOALS["other"])[i], "rate": rate_pct, "days_per_month": dpm}
    money = (lambda v: _inr(v, lang))
    bullets: list[str] = []
    band = "green"
    head = ""

    if target and months:
        n = int(months)
        today_target = float(target)
        future_target = today_target * (1 + inflation_pct / 100) ** (n / 12)          # price rise: the same goal costs more later
        f = _rd_factor(n, rate_pct)
        need_rd = future_target / f
        need_cash = future_target / n
        per_day_rd, per_day_cash = need_rd / dpm, need_cash / dpm
        out.update({"mode": "plan", "target_today": round(today_target), "target_future": round(future_target), "months": n,
                    "need_monthly_rd": round(need_rd), "need_monthly_cash": round(need_cash), "per_day_rd": round(per_day_rd, 1), "per_day_cash": round(per_day_cash, 1),
                    "deposited_rd": round(need_rd * n), "interest_rd": round(future_target - need_rd * n), "per_week_rd": round(need_rd * 12 / 52)})
        head = t(f"{out['goal']}: if it costs {money(today_target)} today, in {n} months you will need about {money(future_target)} (prices rise). Put aside about ₹{per_day_rd:,.0f} a working day in a recurring deposit.",
                 f"{out['goal']}: आज इसका ख़र्च {money(today_target)} है तो {n} महीने बाद लगभग {money(future_target)} चाहिए (दाम बढ़ते हैं)। आवर्ती जमा में लगभग ₹{per_day_rd:,.0f} प्रति काम के दिन रखिए।")
        bullets.append(t(f"In a recurring deposit: ₹{need_rd:,.0f} a month ({money(need_rd * n)} put in, {money(future_target - need_rd * n)} added as interest). Kept as cash it would need ₹{need_cash:,.0f} a month, and cash at home leaks away.",
                         f"आवर्ती जमा में: ₹{need_rd:,.0f} महीना (कुल {money(need_rd * n)} जमा, {money(future_target - need_rd * n)} ब्याज से जुड़ेगा)। नक़द रखें तो ₹{need_cash:,.0f} महीना चाहिए, और घर का नक़द खर्च हो जाता है।"))
        if daily_wage:
            share = per_day_rd / daily_wage * 100
            out["wage_share_pct"] = round(share, 1)
            if share > 30:
                band = "red"
                longer = months_to_reach(future_target, 0.1 * daily_wage * dpm, rate_pct)
                bullets.append(t(f"That is {share:.0f}% of a day's wage: too much to keep up. Take longer: saving 10% of your wage (₹{0.1 * daily_wage:,.0f} a day) reaches the goal in about {longer} months." if longer else f"That is {share:.0f}% of a day's wage: too much to keep up.",
                                 f"यह एक दिन की मज़दूरी का {share:.0f}% है: निभाना मुश्किल। समय बढ़ाइए: मज़दूरी का 10% (₹{0.1 * daily_wage:,.0f} रोज़) बचाएँ तो लगभग {longer} महीने में लक्ष्य पूरा होगा।" if longer else f"यह एक दिन की मज़दूरी का {share:.0f}% है: निभाना मुश्किल।"))
            elif share > 15:
                band = "amber"
                bullets.append(t(f"That is {share:.0f}% of a day's wage: possible, but plan for weeks with no work.", f"यह एक दिन की मज़दूरी का {share:.0f}% है: हो सकता है, पर बिना काम वाले हफ़्तों की योजना रखिए।"))
            else:
                bullets.append(t(f"That is {share:.0f}% of a day's wage: realistic.", f"यह एक दिन की मज़दूरी का {share:.0f}% है: निभ सकता है।"))
        table = []
        for d in (10, 20, 50, 100):
            m = d * dpm
            table.append({"daily": d, "monthly": m, "after": round(rd_maturity(m, n, rate_pct)), "months_to_goal": months_to_reach(future_target, m, rate_pct)})
        out["table"] = table

    if daily and daily > 0:
        n = int(months) if months else 60
        m = daily * dpm
        mat = rd_maturity(m, n, rate_pct)
        out.setdefault("mode", "daily")
        out.update({"daily": daily, "monthly": round(m), "months": n, "matures": round(mat), "put_in": round(m * n), "interest": round(mat - m * n)})
        if not head:
            head = t(f"₹{daily:,.0f} a working day is ₹{m:,.0f} a month. In {n} months a recurring deposit makes it about {money(mat)}: {money(m * n)} of yours plus {money(mat - m * n)} interest.",
                     f"₹{daily:,.0f} रोज़ (काम के दिन) यानी ₹{m:,.0f} महीना। {n} महीने में आवर्ती जमा से लगभग {money(mat)}: आपके {money(m * n)} और {money(mat - m * n)} ब्याज।")
        else:
            bullets.append(t(f"At ₹{daily:,.0f} a day you would have about {money(mat)} in {n} months.", f"₹{daily:,.0f} रोज़ से {n} महीने में लगभग {money(mat)} होंगे।"))
        if target:
            reach = months_to_reach(float(target), m, rate_pct)
            out["months_to_target"] = reach
            if reach:
                bullets.append(t(f"At that rate you reach {money(float(target))} in about {reach} months ({reach / 12:.1f} years), before price rises.", f"इसी रफ़्तार से {money(float(target))} लगभग {reach} महीने ({reach / 12:.1f} साल) में पूरे होंगे, दाम बढ़ने से पहले के हिसाब से।"))
    if not head:
        head = t("Tell me a goal amount and when you want it, or how much you can put aside a day.", "लक्ष्य की रक़म और कब चाहिए, या रोज़ कितना बचा सकते हैं, यह बताइए।")
        band = "amber"
    places = [{"name": hi if lang == "hi" else en, "rate": r, "note": nh if lang == "hi" else ne} for en, hi, r, ne, nh in SAVE_PLACES]
    rules = [t("Pay yourself first: put the money aside on the day you are paid, not what is left at night.", "पहले ख़ुद को दीजिए: मज़दूरी मिलते ही बचत अलग कीजिए, रात को जो बचे वह नहीं।"),
             t("Build a small emergency pot first, about two weeks of wages, so a bad week does not break the savings.", "पहले एक छोटा आपात कोष बनाइए, लगभग दो हफ़्ते की मज़दूरी, ताकि बुरा हफ़्ता बचत न तोड़े।"),
             t("Never borrow from a moneylender for something you can save for: 5 rupees per hundred a month is 60% a year.", "जिसके लिए बचत हो सकती है उसके लिए साहूकार से कर्ज़ मत लीजिए: 5 रुपये सैकड़ा महीना यानी साल का 60%।"),
             t("Keep it where it is hard to spend and safe: a post-office or bank account in your own name, not a chit fund or a person.", "ऐसी जगह रखिए जहाँ ख़र्च करना कठिन और पैसा सुरक्षित हो: अपने नाम का डाकघर या बैंक खाता, चिट फंड या कोई व्यक्ति नहीं।")]
    out.update({"band": band, "headline": head, "bullets": bullets, "places": places, "rules": rules,
                "note": t(f"Rates shown ({rate_pct}%) and the 6% price rise are illustrations: deposit rates change. A deposit is safe but locked; if you stop early you may lose some interest.",
                          f"दिखाई गई दर ({rate_pct}%) और 6% दाम-वृद्धि उदाहरण हैं: जमा दरें बदलती हैं। जमा सुरक्षित है पर बँधी रहती है; बीच में तोड़ने पर कुछ ब्याज जा सकता है।")})
    return out


# =============================================================================== E2 self-help group ledger
# A self-help group's whole bookkeeping: monthly savings, internal loans, repayments, fines. Paper registers
# go wrong in the same few places (interest worked out by guess, a member who quietly stopped paying, a loan
# larger than the fund, a year-end share nobody can explain). This computes all of it from the plain list of
# entries, the same way every time, and writes the statements the group reads out at the meeting.
# The ledger itself is kept on the leader's device and sent only to be calculated; nothing is stored here.
import datetime as _dt


def _d(s: str) -> _dt.date | None:
    try:
        return _dt.date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def _fmt_rs(x: float) -> str:
    return f"₹{x:,.0f}"


def shg_summary(ledger: dict[str, Any], as_of: str | None = None, lang: str = "en") -> dict[str, Any]:
    """`ledger` = {"group": str, "rate": % per month on the loan balance, "loan_multiple": max loan as a multiple of savings,
    "members": [{"id","name"}], "entries": [{"date","member","type","amount","note"}]}; types: saving, withdraw, loan, repay, fine."""
    t = _tr(lang)
    rate = float(ledger.get("rate", 1.5))
    multiple = float(ledger.get("loan_multiple", 3))
    members = {m["id"]: m for m in ledger.get("members", [])}
    entries = []
    for e in ledger.get("entries", []):
        d = _d(e.get("date", ""))
        if d and e.get("member") in members and e.get("type") in ("saving", "withdraw", "loan", "repay", "fine") and float(e.get("amount", 0)) > 0:
            entries.append((d, e["member"], e["type"], float(e["amount"]), e.get("note", "")))
    entries.sort(key=lambda x: x[0])
    end = _d(as_of) if as_of else (entries[-1][0] if entries else _dt.date.today())
    end = end or _dt.date.today()
    entries = [e for e in entries if e[0] <= end]

    acct = {mid: dict(savings=0.0, loans=0.0, prin_paid=0.0, outstanding=0.0, int_accrued=0.0, int_paid=0.0, fines=0.0, last=None, last_repay=None,
                      first_loan=None, overpaid=0.0, saved_months=set()) for mid in members}
    for d, mid, typ, amt, _n in entries:
        a = acct[mid]
        if a["outstanding"] > 0 and a["last"]:                                   # interest runs on the balance since the last event
            a["int_accrued"] += a["outstanding"] * rate / 100 * (d - a["last"]).days / 30
        a["last"] = d
        if typ == "saving":
            a["savings"] += amt; a["saved_months"].add((d.year, d.month))
        elif typ == "withdraw":
            a["savings"] -= amt
        elif typ == "fine":
            a["fines"] += amt
        elif typ == "loan":
            a["loans"] += amt; a["outstanding"] += amt; a["first_loan"] = a["first_loan"] or d
            if a["last_repay"] is None:
                a["last_repay"] = d
        elif typ == "repay":
            due_int = a["int_accrued"] - a["int_paid"]
            to_int = min(amt, max(0.0, due_int))
            a["int_paid"] += to_int
            rest = amt - to_int
            to_prin = min(rest, a["outstanding"])
            a["prin_paid"] += to_prin; a["outstanding"] -= to_prin
            a["overpaid"] += rest - to_prin
            a["last_repay"] = d
    for a in acct.values():                                                      # accrue to the report date
        if a["outstanding"] > 0 and a["last"]:
            a["int_accrued"] += a["outstanding"] * rate / 100 * (end - a["last"]).days / 30
            a["last"] = end

    tot_sav = sum(a["savings"] for a in acct.values())
    tot_int = sum(a["int_paid"] for a in acct.values())
    tot_fine = sum(a["fines"] for a in acct.values())
    tot_out = sum(a["outstanding"] for a in acct.values())
    cash = tot_sav + tot_int + tot_fine - tot_out                                # money that should be in hand / bank
    # who has not saved in the last 3 months, when others have
    months_back = [((end.year * 12 + end.month - 1 - k) // 12, (end.year * 12 + end.month - 1 - k) % 12 + 1) for k in range(3)]
    active_months = {m for a in acct.values() for m in a["saved_months"]}
    rows, alerts = [], []
    for mid, m in members.items():
        a = acct[mid]
        missed = sum(1 for mo in months_back if mo in active_months and mo not in a["saved_months"])
        due_int = max(0.0, a["int_accrued"] - a["int_paid"])
        overdue = bool(a["outstanding"] > 0 and a["last_repay"] and (end - a["last_repay"]).days > 60)
        mult = (a["outstanding"] / a["savings"]) if a["savings"] > 0 else (None if a["outstanding"] == 0 else float("inf"))
        status = "overdue" if overdue else "missed" if missed >= 2 else "ok"
        share = (tot_int * a["savings"] / tot_sav) if tot_sav > 0 else 0.0
        rows.append({"id": mid, "name": m["name"], "savings": round(a["savings"]), "loans_taken": round(a["loans"]), "principal_repaid": round(a["prin_paid"]),
                     "outstanding": round(a["outstanding"]), "interest_due": round(due_int), "interest_paid": round(a["int_paid"]), "fines": round(a["fines"]),
                     "total_due": round(a["outstanding"] + due_int), "loan_multiple": None if mult is None else (None if mult == float("inf") else round(mult, 1)),
                     "missed_months": missed, "overdue": overdue, "status": status, "year_end_share": round(share), "overpaid": round(a["overpaid"])})
        if overdue:
            alerts.append(t(f"{m['name']} has not repaid for over 2 months and owes {_fmt_rs(a['outstanding'] + due_int)}.", f"{m['name']} ने 2 महीने से ज़्यादा से किस्त नहीं दी और {_fmt_rs(a['outstanding'] + due_int)} बाक़ी है।"))
        if missed >= 2:
            alerts.append(t(f"{m['name']} has missed saving in {missed} of the last 3 months.", f"{m['name']} ने पिछले 3 में से {missed} महीने बचत जमा नहीं की।"))
        if mult is not None and (mult == float("inf") or mult > multiple) and a["outstanding"] > 0:
            alerts.append(t(f"{m['name']}'s loan is more than {multiple:g} times their savings: the group is carrying the risk.", f"{m['name']} का ऋण उनकी बचत के {multiple:g} गुना से ज़्यादा है: जोखिम पूरा समूह उठा रहा है।"))
        if a["overpaid"] > 0:
            alerts.append(t(f"{m['name']} paid {_fmt_rs(a['overpaid'])} more than was due: treat it as savings or return it.", f"{m['name']} ने देय से {_fmt_rs(a['overpaid'])} ज़्यादा दिया: उसे बचत मानिए या लौटाइए।"))
    if cash < 0:
        alerts.insert(0, t(f"The books show the group has lent {_fmt_rs(-cash)} more than it has. Check every loan entry and the bank passbook.", f"हिसाब के अनुसार समूह ने अपने पास से {_fmt_rs(-cash)} ज़्यादा उधार दिया है। हर ऋण-प्रविष्टि और बैंक पासबुक जाँचिए।"))

    ym = (end.year, end.month)
    month = {"saving": 0.0, "withdraw": 0.0, "loan": 0.0, "repay": 0.0, "fine": 0.0}
    savers = set()
    for d, mid, typ, amt, _n in entries:
        if (d.year, d.month) == ym:
            month[typ] += amt
            if typ == "saving":
                savers.add(mid)
    mname = end.strftime("%B %Y")
    g = ledger.get("group") or t("Our group", "हमारा समूह")
    report = t(
        f"{g}: meeting report for {mname}\nSavings collected: {_fmt_rs(month['saving'])} from {len(savers)} of {len(members)} members\nLoans given: {_fmt_rs(month['loan'])}\nRepayments received: {_fmt_rs(month['repay'])}\nFines: {_fmt_rs(month['fine'])}\n"
        f"Group savings: {_fmt_rs(tot_sav)}   Loans outstanding: {_fmt_rs(tot_out)}\nCash that should be in hand / bank: {_fmt_rs(cash)}\nInterest earned so far: {_fmt_rs(tot_int)}",
        f"{g}: {mname} की बैठक की रिपोर्ट\nबचत जमा: {_fmt_rs(month['saving'])}, {len(members)} में से {len(savers)} सदस्यों से\nदिया गया ऋण: {_fmt_rs(month['loan'])}\nवापस मिली किस्तें: {_fmt_rs(month['repay'])}\nजुर्माना: {_fmt_rs(month['fine'])}\n"
        f"समूह की कुल बचत: {_fmt_rs(tot_sav)}   बाक़ी ऋण: {_fmt_rs(tot_out)}\nहाथ / बैंक में होना चाहिए: {_fmt_rs(cash)}\nअब तक कमाया ब्याज: {_fmt_rs(tot_int)}")
    stmts = {}
    for r in rows:
        stmts[r["id"]] = t(
            f"{g} — statement for {r['name']} (up to {end.isoformat()})\nSavings: {_fmt_rs(r['savings'])}\nLoans taken: {_fmt_rs(r['loans_taken'])}   Principal repaid: {_fmt_rs(r['principal_repaid'])}\n"
            f"Loan balance: {_fmt_rs(r['outstanding'])}   Interest due: {_fmt_rs(r['interest_due'])}   Total to pay: {_fmt_rs(r['total_due'])}\nInterest paid so far: {_fmt_rs(r['interest_paid'])}   Fines: {_fmt_rs(r['fines'])}",
            f"{g} — {r['name']} का विवरण ({end.isoformat()} तक)\nबचत: {_fmt_rs(r['savings'])}\nलिया ऋण: {_fmt_rs(r['loans_taken'])}   लौटाई मूल रक़म: {_fmt_rs(r['principal_repaid'])}\n"
            f"ऋण बाक़ी: {_fmt_rs(r['outstanding'])}   ब्याज देय: {_fmt_rs(r['interest_due'])}   कुल देना: {_fmt_rs(r['total_due'])}\nअब तक दिया ब्याज: {_fmt_rs(r['interest_paid'])}   जुर्माना: {_fmt_rs(r['fines'])}")
    return {"group": g, "as_of": end.isoformat(), "rate": rate, "loan_multiple": multiple, "members": rows, "alerts": alerts,
            "totals": {"members": len(members), "savings": round(tot_sav), "loans_out": round(tot_out), "interest_income": round(tot_int), "fines": round(tot_fine), "cash": round(cash),
                       "lent_total": round(sum(a["loans"] for a in acct.values()))},
            "month": {"name": mname, **{k: round(v) for k, v in month.items()}, "savers": len(savers)}, "report": report, "statements": stmts,
            "method": t(f"Interest is {rate:g}% a month on the loan balance, counted per day (30-day months). A repayment pays interest first, then the loan. The year-end share divides interest earned in proportion to savings.",
                        f"ब्याज ऋण-शेष पर {rate:g}% महीना है, दिन के हिसाब से (30 दिन का महीना)। किस्त पहले ब्याज में, फिर मूल में जाती है। वर्षांत का हिस्सा कमाए ब्याज को बचत के अनुपात में बाँटता है।")}


def shg_can_lend(ledger: dict[str, Any], member: str, amount: float, as_of: str | None = None, lang: str = "en") -> dict[str, Any]:
    """Should the group lend `amount` to `member` now? Three plain checks the group can read out."""
    t = _tr(lang)
    s = shg_summary(ledger, as_of, lang)
    row = next((r for r in s["members"] if r["id"] == member), None)
    if row is None:
        return {"ok": False, "checks": [], "headline": t("Unknown member.", "अज्ञात सदस्य।")}
    new_out = row["outstanding"] + amount
    limit = s["loan_multiple"] * max(row["savings"], 0)
    checks = [
        {"id": "cash", "ok": amount <= s["totals"]["cash"], "text": t(f"The group has {_fmt_rs(s['totals']['cash'])} in hand; the loan is {_fmt_rs(amount)}.", f"समूह के पास {_fmt_rs(s['totals']['cash'])} हैं; ऋण {_fmt_rs(amount)} है।")},
        {"id": "limit", "ok": new_out <= limit, "text": t(f"{row['name']}'s savings are {_fmt_rs(row['savings'])}; at {s['loan_multiple']:g} times that the most to owe is {_fmt_rs(limit)}, and the loan would take it to {_fmt_rs(new_out)}.",
                                                        f"{row['name']} की बचत {_fmt_rs(row['savings'])} है; उसके {s['loan_multiple']:g} गुना तक यानी अधिकतम {_fmt_rs(limit)} देय हो सकता है, और यह ऋण उसे {_fmt_rs(new_out)} पर ले जाएगा।")},
        {"id": "clean", "ok": not row["overdue"] and row["missed_months"] < 2, "text": t("Has no overdue loan and has been saving regularly." if not row["overdue"] and row["missed_months"] < 2 else "Has an overdue loan or missed savings: clear that first.",
                                                                                         "कोई बकाया किस्त नहीं और बचत नियमित है।" if not row["overdue"] and row["missed_months"] < 2 else "किस्त बकाया है या बचत छूटी है: पहले वह चुकता कीजिए।")},
    ]
    ok = all(c["ok"] for c in checks)
    return {"ok": ok, "checks": checks, "headline": t("Fine to lend on these checks. The group still decides.", "इन जाँचों पर ऋण देना ठीक है। फ़ैसला समूह का है।") if ok else
            t("Not yet: at least one check fails. The group still decides.", "अभी नहीं: कम से कम एक जाँच विफल है। फ़ैसला समूह का है।")}


# =============================================================================== E3 credit-score explainer
# For first-time borrowers. It does NOT fetch or guess a number: only the credit bureaus hold the score, and
# any figure made up here would be a lie. It explains what the score is made of, reads the person's own
# situation, names what is helping or hurting in plain words with the fix for each, shows what a good record
# is worth in rupees (EMI on the same loan at two rates), and drafts the letter to correct a wrong entry.
BUREAUS = [("TransUnion CIBIL", "cibil.com"), ("Experian", "experian.in"), ("Equifax", "equifax.co.in"), ("CRIF High Mark", "crifhighmark.com")]
CREDIT_FACTS = [
    ("A credit score (300 to 900) is a number a credit bureau works out from your repayment history. Lenders look at it before deciding a loan and its interest rate. About 750 and above is generally treated as good.",
     "क्रेडिट स्कोर (300 से 900) वह संख्या है जो क्रेडिट ब्यूरो आपके चुकाने के इतिहास से निकालता है। ऋण और ब्याज दर तय करने से पहले ऋणदाता इसे देखते हैं। लगभग 750 और ऊपर को आम तौर पर अच्छा माना जाता है।"),
    ("What matters most, in order: paying every instalment on time; how much of your card limit you use; how long you have had credit; how many times you recently applied for credit; and having a mix of loan types.",
     "सबसे ज़्यादा असर इन बातों का, क्रम से: हर किस्त समय पर देना; कार्ड की सीमा का कितना हिस्सा इस्तेमाल करना; कितने समय से ऋण का इतिहास है; हाल में कितनी बार ऋण के लिए आवेदन किया; और अलग-अलग तरह के ऋण।"),
    ("Having NO score is not a bad score. It means no one has reported anything about you yet. You build one by borrowing a small formal loan and repaying it on time.",
     "स्कोर न होना ख़राब स्कोर नहीं है। इसका मतलब है कि अब तक किसी ने आपके बारे में कुछ दर्ज नहीं किया। छोटा औपचारिक ऋण लेकर समय पर चुकाने से स्कोर बनता है।"),
    ("Repaying a moneylender or a chit fund builds NO score, because they do not report to the bureaus. Loans from banks, finance companies and microfinance institutions do.",
     "साहूकार या चिट फंड को चुकाने से कोई स्कोर नहीं बनता, क्योंकि वे ब्यूरो को रिपोर्ट नहीं करते। बैंक, फ़ाइनेंस कंपनी और माइक्रोफ़ाइनेंस संस्था के ऋण रिपोर्ट होते हैं।"),
]
CREDIT_SCAMS = [
    ("No company can remove a correct bad entry for a fee. \"Score repair\" and \"CIBIL fix\" offers are scams. Only wrong entries can be corrected, and that is free.",
     "कोई कंपनी फ़ीस लेकर सही नकारात्मक प्रविष्टि नहीं हटा सकती। \"स्कोर रिपेयर\" और \"सिबिल फ़िक्स\" के ऑफ़र ठगी हैं। सिर्फ़ गलत प्रविष्टि सुधरती है, और वह मुफ़्त है।"),
    ("An \"instant loan\" app that wants your contacts, photos or an upfront \"processing fee\" is a trap. Use banks and registered lenders.",
     "जो \"इंस्टैंट लोन\" ऐप आपके कॉन्टैक्ट, फ़ोटो या पहले से \"प्रोसेसिंग फ़ीस\" माँगे वह जाल है। बैंक और पंजीकृत ऋणदाता से ही लीजिए।"),
    ("If you sign as a guarantor or co-borrower, a missed payment lands on YOUR report too.",
     "आप गारंटर या सह-उधारकर्ता बनकर दस्तख़त करें तो किस्त चूकने पर वह आपकी रिपोर्ट में भी आती है।"),
]
START_PATH = [
    ("Open a bank account in your own name and keep it active (a Jan Dhan account is enough).", "अपने नाम का बैंक खाता खोलिए और चालू रखिए (जन धन खाता काफ़ी है)।"),
    ("Take one small formal loan or card you can easily afford, for example a Kisan Credit Card, a Mudra Shishu loan, a microfinance loan or a card secured against a fixed deposit.", "एक छोटा औपचारिक ऋण या कार्ड लीजिए जो आसानी से चुका सकें, जैसे किसान क्रेडिट कार्ड, मुद्रा शिशु ऋण, माइक्रोफ़ाइनेंस ऋण, या एफ़डी के बदले कार्ड।"),
    ("Pay every instalment on or before the date; set an auto-debit so it cannot be forgotten.", "हर किस्त तारीख़ पर या उससे पहले दीजिए; ऑटो-डेबिट लगाइए ताकि भूल न हो।"),
    ("After 6 months, ask a credit bureau for your free report and check that your loan appears and is correct.", "6 महीने बाद किसी क्रेडिट ब्यूरो से अपनी मुफ़्त रिपोर्ट माँगिए और देखिए कि आपका ऋण सही दिख रहा है।"),
    ("Do not apply to many lenders at once: each application leaves a mark.", "एक साथ कई ऋणदाताओं से आवेदन मत कीजिए: हर आवेदन का निशान रहता है।"),
]


def _emi(p: float, rate_pct: float, years: float) -> float:
    n = max(1, int(round(years * 12)))
    r = rate_pct / 100 / 12
    return p / n if r == 0 else p * r * (1 + r) ** n / ((1 + r) ** n - 1)


def emi_compare(amount: float, years: float, good_rate: float = 11.0, poor_rate: float = 16.0, lang: str = "en") -> dict[str, Any]:
    t = _tr(lang)
    n = max(1, int(round(years * 12)))
    eg, ep = _emi(amount, good_rate, years), _emi(amount, poor_rate, years)
    sg, sp = eg * n, ep * n
    return {"amount": round(amount), "years": years, "good_rate": good_rate, "poor_rate": poor_rate,
            "emi_good": round(eg), "emi_poor": round(ep), "total_good": round(sg), "total_poor": round(sp), "saved": round(sp - sg),
            "headline": t(f"On {_inr(amount)} over {years:g} years, {good_rate:g}% instead of {poor_rate:g}% saves about {_inr(sp - sg)} (₹{ep - eg:,.0f} less every month).",
                          f"{years:g} साल के {_inr(amount, 'hi')} पर {poor_rate:g}% की जगह {good_rate:g}% लगे तो लगभग {_inr(sp - sg, 'hi')} बचते हैं (हर महीने ₹{ep - eg:,.0f} कम)।")}


def credit_check(has_credit: str = "none", missed: str = "never", serious: str = "none", utilization: str = "na", enquiries: str = "0-1",
                 age: str = "na", informal_only: bool = False, lang: str = "en") -> dict[str, Any]:
    t = _tr(lang)
    i = 1 if lang == "hi" else 0
    reasons: list[dict[str, Any]] = []

    def add(weight: int, kind: str, en: str, hi: str, steps_en: list[str], steps_hi: list[str]):
        reasons.append({"w": weight, "kind": kind, "title": hi if i else en, "steps": steps_hi if i else steps_en})

    if has_credit == "none":
        extra_en = " Borrowing only from a moneylender or chit fund does not count: they are not reported." if informal_only else ""
        extra_hi = " सिर्फ़ साहूकार या चिट फंड से लेना गिना नहीं जाता: वे रिपोर्ट नहीं करते।" if informal_only else ""
        add(0, "neutral", "You probably have no credit score yet (no history)." + extra_en, "आपका शायद अभी कोई क्रेडिट स्कोर नहीं है (कोई इतिहास नहीं)।" + extra_hi,
            [s[0] for s in START_PATH], [s[1] for s in START_PATH])
        profile, band = "thin_file", "amber"
    else:
        r = 0
        if serious == "default":
            r += 6; add(6, "bad", "An unpaid (defaulted) loan is on your record.", "आपके रिकॉर्ड में न चुकाया गया (डिफ़ॉल्ट) ऋण है।",
                        ["Pay what is owed, then ask the lender in writing to mark the account closed and give a no-dues letter.", "It will still show for years, but a paid account is far better than an open default.", "Do not take new credit until it is closed."],
                        ["जो बाक़ी है चुकाइए, फिर ऋणदाता से लिखित में खाता बंद दर्ज करने और बकाया-नहीं का पत्र माँगिए।", "यह फिर भी कई साल दिखेगा, पर चुकाया खाता खुले डिफ़ॉल्ट से कहीं बेहतर है।", "खाता बंद होने तक नया ऋण मत लीजिए।"])
        elif serious in ("settled", "written_off"):
            r += 4; add(4, "bad", "A settled or written-off account is on your record.", "आपके रिकॉर्ड में निपटाया (सेटल) या बट्टे खाते (राइट-ऑफ़) वाला खाता है।",
                        ["It stays for years (commonly up to 7) and makes lenders cautious.", "If a balance remains, pay it and ask for the status to be updated to closed.", "From now, pay everything on time: new good history slowly outweighs the old."],
                        ["यह कई साल (आम तौर पर 7 तक) रहता है और ऋणदाताओं को सतर्क करता है।", "कुछ बाक़ी हो तो चुकाइए और स्थिति को बंद में बदलवाइए।", "आज से सब कुछ समय पर दीजिए: नया अच्छा इतिहास धीरे-धीरे पुराने पर भारी पड़ता है।"])
        if missed == "often":
            r += 3; add(5, "bad", "You have often paid late. This is the biggest thing lowering a score.", "आप अक्सर देर से चुकाते रहे हैं। स्कोर गिराने की यह सबसे बड़ी वजह है।",
                        ["Set an auto-debit for every instalment or keep the money aside on pay day.", "Pay all dues on time for the next 6 to 12 months: recent behaviour counts most.", "Ask the lender to move your due date to just after you are paid."],
                        ["हर किस्त का ऑटो-डेबिट लगाइए या मज़दूरी मिलते ही पैसा अलग रखिए।", "अगले 6 से 12 महीने सब समय पर दीजिए: हाल का व्यवहार सबसे ज़्यादा गिना जाता है।", "ऋणदाता से किस्त की तारीख़ मज़दूरी मिलने के ठीक बाद करवाइए।"])
        elif missed == "once":
            r += 1; add(2, "warn", "You paid late once or twice. It hurts for a while, then fades.", "आपने एक-दो बार देर की। कुछ समय असर रहता है, फिर घटता है।",
                        ["Pay on time from now on; the mark loses weight month by month."], ["अब से समय पर दीजिए; निशान का असर महीने-दर-महीने घटता है।"])
        if utilization == "high":
            r += 2; add(3, "bad", "You use most of your card or credit limit.", "आप अपने कार्ड या क्रेडिट सीमा का ज़्यादातर हिस्सा इस्तेमाल करते हैं।",
                        ["Keep use under about 30% of the limit.", "Pay part of the bill before the statement date, not only after it.", "Ask for a higher limit (do not spend more)."],
                        ["सीमा का लगभग 30% से कम इस्तेमाल कीजिए।", "बिल का हिस्सा स्टेटमेंट की तारीख़ से पहले चुकाइए, सिर्फ़ बाद में नहीं।", "सीमा बढ़ाने को कहिए (ज़्यादा ख़र्च मत कीजिए)।"])
        elif utilization == "mid":
            r += 1; add(1, "warn", "You use a fair part of your limit.", "आप सीमा का ठीक-ठाक हिस्सा इस्तेमाल करते हैं।", ["Try to bring it under 30%."], ["इसे 30% से नीचे लाने की कोशिश कीजिए।"])
        if enquiries == "4+":
            r += 2; add(3, "bad", "You have applied for credit many times recently.", "आपने हाल में कई बार ऋण के लिए आवेदन किया है।",
                        ["Stop applying for about 6 months: each application leaves a mark and many together look like desperation.", "Before applying, ask the lender whether they do a soft check."],
                        ["लगभग 6 महीने आवेदन बंद कीजिए: हर आवेदन का निशान रहता है और कई साथ मिलकर घबराहट जैसे दिखते हैं।", "आवेदन से पहले पूछिए कि क्या ऋणदाता सॉफ़्ट चेक करता है।"])
        elif enquiries == "2-3":
            r += 1; add(1, "warn", "You have applied a few times recently.", "आपने हाल में कुछ बार आवेदन किया है।", ["Space further applications out by a few months."], ["आगे के आवेदनों के बीच कुछ महीने का अंतर रखिए।"])
        if age == "<6m":
            r += 1; add(1, "warn", "Your credit history is very new.", "आपका क्रेडिट इतिहास बहुत नया है।", ["Time helps. Keep paying on time and keep the account open."], ["समय मदद करता है। समय पर देते रहिए और खाता खुला रखिए।"])
        if informal_only:
            add(1, "warn", "Most of your borrowing is from a moneylender or chit fund, which builds no score.", "आपका ज़्यादातर उधार साहूकार या चिट फंड का है, जिससे कोई स्कोर नहीं बनता।",
                ["Where you can, move to a bank, microfinance or group-linked loan: it is cheaper and it counts."], ["जहाँ हो सके बैंक, माइक्रोफ़ाइनेंस या समूह-जुड़े ऋण पर आइए: वह सस्ता है और गिना जाता है।"])
        if r >= 5:
            profile, band = "at_risk", "red"
        elif r >= 2:
            profile, band = "fair", "amber"
        else:
            profile, band = "healthy", "green"
            if not reasons:
                add(0, "good", "Nothing here looks harmful. Keep paying on time.", "यहाँ कुछ हानिकारक नहीं दिखता। समय पर देते रहिए।",
                    ["Keep your oldest account open.", "Check your free report once a year for wrong entries."], ["अपना सबसे पुराना खाता खुला रखिए।", "साल में एक बार मुफ़्त रिपोर्ट में गलत प्रविष्टि जाँचिए।"])
    reasons.sort(key=lambda x: -x["w"])
    head = {"thin_file": t("You probably have no score yet. That is fixable.", "आपका शायद अभी स्कोर नहीं है। यह ठीक हो सकता है।"),
            "at_risk": t("Your record is probably hurting you with lenders. There are clear steps.", "आपका रिकॉर्ड शायद ऋणदाताओं के सामने आपको नुक़सान पहुँचा रहा है। साफ़ क़दम हैं।"),
            "fair": t("Your record is probably fair and can improve.", "आपका रिकॉर्ड शायद ठीक-ठाक है और सुधर सकता है।"),
            "healthy": t("Your record looks healthy from what you told me.", "आपने जो बताया उससे आपका रिकॉर्ड स्वस्थ लगता है।")}[profile]
    return {"profile": profile, "band": band, "headline": head, "reasons": [{k: v for k, v in r.items() if k != "w"} for r in reasons],
            "facts": [hi if i else en for en, hi in CREDIT_FACTS], "scams": [hi if i else en for en, hi in CREDIT_SCAMS],
            "bureaus": [{"name": n, "site": s} for n, s in BUREAUS],
            "report_note": t("You can get a free full credit report from each bureau every year (an RBI rule). Ask for it yourself on the bureau's own website; never pay a middleman.",
                             "आप हर ब्यूरो से हर साल एक मुफ़्त पूरी क्रेडिट रिपोर्ट ले सकते हैं (RBI का नियम)। ब्यूरो की अपनी वेबसाइट से ख़ुद माँगिए; किसी बिचौलिये को पैसा मत दीजिए।"),
            "note": t("This reads your answers; it cannot know your actual score. Only the bureaus have that.", "यह आपके जवाब पढ़ता है; आपका असली स्कोर नहीं जान सकता। वह सिर्फ़ ब्यूरो के पास है।")}


def credit_dispute_letter(name: str = "", lender: str = "", wrong: str = "", lang: str = "en") -> dict[str, str]:
    nm, ln, wr = name or "________", lender or "________", wrong or "________"
    if lang == "hi":
        return {"lender": f"सेवा में,\nशिकायत निवारण अधिकारी, {ln}\n\nविषय: मेरी क्रेडिट रिपोर्ट में गलत प्रविष्टि सुधारने का अनुरोध\n\nमहोदय,\nमैं {nm} हूँ। मेरी क्रेडिट रिपोर्ट में यह प्रविष्टि गलत है: {wr}।\n"
                          f"कृपया इसकी जाँच कर क्रेडिट ब्यूरो को सुधार भेजिए और मुझे लिखित में सूचित कीजिए। मेरे पास भुगतान की रसीदें / पासबुक की प्रति है।\n\nभवदीय,\n{nm}\nदिनांक: ________   मोबाइल: ________",
                "bureau": f"सेवा में,\nक्रेडिट ब्यूरो (विवाद विभाग)\n\nविषय: मेरी रिपोर्ट में गलत जानकारी का विवाद\n\nमहोदय,\nमैं {nm} हूँ। मेरी रिपोर्ट में {ln} की यह प्रविष्टि गलत है: {wr}।\n"
                          f"कृपया ऋणदाता से जाँच कराकर 30 दिन में सुधार कीजिए। मैंने ऋणदाता को भी लिखित में बताया है।\n\nभवदीय,\n{nm}\nदिनांक: ________"}
    return {"lender": f"To,\nThe Grievance Officer, {ln}\n\nSubject: Request to correct a wrong entry on my credit report\n\nSir/Madam,\nI am {nm}. This entry on my credit report is wrong: {wr}.\n"
                      f"Please check it, send the correction to the credit bureau, and confirm to me in writing. I have my payment receipts / passbook copy.\n\nYours faithfully,\n{nm}\nDate: ________   Mobile: ________",
            "bureau": f"To,\nCredit Bureau (Dispute Resolution)\n\nSubject: Dispute of incorrect information on my report\n\nSir/Madam,\nI am {nm}. The entry from {ln} on my report is wrong: {wr}.\n"
                      f"Please verify it with the lender and correct it within 30 days. I have also told the lender in writing.\n\nYours faithfully,\n{nm}\nDate: ________"}


def credit_full(has_credit: str = "none", missed: str = "never", serious: str = "none", utilization: str = "na", enquiries: str = "0-1", age: str = "na",
                informal_only: bool = False, name: str = "", lender: str = "", wrong: str = "", amount: float = 100000, years: float = 3,
                good_rate: float = 11.0, poor_rate: float = 16.0, lang: str = "en") -> dict[str, Any]:
    out = credit_check(has_credit, missed, serious, utilization, enquiries, age, informal_only, lang)
    out["emi"] = emi_compare(amount, years, good_rate, poor_rate, lang)
    out["letters"] = credit_dispute_letter(name, lender, wrong, lang)
    return out
