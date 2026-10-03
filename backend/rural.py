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
        from analysis import tools
        q = tools.quantities(text)
        money = [x["v"] for x in q["money"] if x["v"] >= 100]
        mo = q["months"][0]["v"] if q["months"] else (q["years"][0]["v"] * 12 if q["years"] else None)
        if len(money) >= 2 and mo and money[1] > money[0]:
            put, get, months = money[0], money[1], mo
    hits = [(fid, w, en, hi) for fid, (w, en, hi, rx) in FLAGS.items() if re.search(rx, low)]
    score = sum(w for _, w, _, _ in hits)
    ret = implied_return(put, get, months) if (put and get and months) else None
    rflags = []
    if ret is not None:
        if ret >= 30:
            score += 40
            rflags.append(t(f"The promise works out to {ret:,.0f}% a year. Bank deposits pay about 7%; nothing safe pays this.",
                            f"यह वादा साल के {ret:,.0f}% के बराबर है। बैंक जमा लगभग 7% देते हैं; कोई सुरक्षित चीज़ इतना नहीं देती।"))
        elif ret >= 15:
            score += 20
            rflags.append(t(f"The promise works out to {ret:,.0f}% a year, much more than safe options (about 7%). High returns carry high risk of loss.",
                            f"यह वादा साल के {ret:,.0f}% के बराबर है, सुरक्षित विकल्पों (लगभग 7%) से बहुत ज़्यादा। ऊँचे मुनाफ़े में नुक़सान का ख़तरा भी ऊँचा होता है।"))
    score = min(100, score)
    level = "red" if score >= 60 else "amber" if score >= 30 else "green"
    verdict = {
        "red": t("Very likely a scam. Do not pay anything.", "बहुत संभव है कि यह ठगी है। कुछ भी पैसा मत दीजिए।"),
        "amber": t("High risk. Check it properly before paying anything.", "ज़्यादा जोखिम है। कोई पैसा देने से पहले ठीक से जाँचिए।"),
        "green": t("No common red flag found in what you wrote. That is not proof it is safe: still verify it.", "आपके लिखे में कोई आम चेतावनी नहीं मिली। इसका मतलब यह नहीं कि यह सुरक्षित है: फिर भी जाँचिए।"),
    }[level]
    return {"score": score, "level": level, "verdict": verdict, "implied_yearly_pct": None if ret is None else round(ret, 1),
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
