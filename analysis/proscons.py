"""Plain-language pros and cons for one company: what looks good, what to watch, what we could not check.

No buy or sell signal, no price target, no prediction. Every line is a measured fact about the company, put next to
something it can be judged against (its sector peers, its own past, its own earlier year) and explained in a sentence
a non-expert can follow.

How much to trust each line is part of the answer, so every line carries:
  basis        which kinds of data it rests on (company numbers, financial statements, prices, peers, news, ownership)
  confidence   "solid" (two or more independent kinds of data, fresh, enough comparisons), "light" (one kind, or
               somewhat old, or few comparisons) or "weak" (very old, or a single thin input)
and the page shows how old each kind of data is and how many of the possible checks could be run at all. A missing
number is listed under "could not check"; it is never read as good or bad.
"""
from __future__ import annotations

import math
import statistics
from datetime import datetime, timezone
from typing import Any

from core import universe

FIN = {"FINANCIALS"}


def _t(lang: str):
    return (lambda en, hi: hi if lang == "hi" else en)


def _median(xs: list[float]) -> float | None:
    return statistics.median(xs) if xs else None


def _money(x: float, cur: str) -> str:
    if cur == "₹":
        if x >= 1e12:
            return f"₹{x / 1e12:.1f} lakh crore"
        if x >= 1e7:
            return f"₹{x / 1e7:,.0f} crore"
        return f"₹{x:,.0f}"
    return f"${x / 1e9:,.1f} billion" if x >= 1e9 else f"${x:,.0f}"


def _utc(d) -> datetime:
    if isinstance(d, str):
        d = datetime.fromisoformat(d.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def pros_cons(pit, ticker: str, lang: str = "en", holding: dict[str, float] | None = None) -> dict[str, Any]:
    """`holding` (optional): {"weight", "sector_weight", "sector_limit"} so the summary can say how the company sits
    with what the person already owns."""
    t = _t(lang)
    name, sector = universe.name(ticker), universe.sector(ticker)
    sec_label = universe.sector_label(sector)
    is_fin = sector in FIN
    cur = "₹" if ticker.upper().endswith((".NS", ".BO")) else "$"
    clock = _utc(pit.clock_iso)
    pros: list[dict[str, Any]] = []
    cons: list[dict[str, Any]] = []
    gaps: list[str] = []
    ran: set[str] = set()                       # checks that had the data to run
    want: set[str] = set()                      # checks that apply to this company at all

    def age_of(when) -> int | None:
        return None if when is None else max(0, (clock - _utc(when)).days)

    def sig(tk: str, kind: str):
        s = pit.latest(tk, kind)
        return (s.value_num, s.as_of) if s is not None and s.value_num is not None else (None, None)

    def val(tk: str, kind: str) -> float | None:
        return sig(tk, kind)[0]

    def conf(types: set[str], age: int | None, n: int | None) -> str:
        if age is not None and age > 120:
            return "weak"
        score = len(types) - (1 if (n is not None and n < 3) else 0) - (1 if (age is not None and age > 45) else 0)
        return "solid" if score >= 2 else "light" if score == 1 else "weak"

    def add(bucket, w, title_en, title_hi, why_en, why_hi, types=("company numbers",), age=None, n=None, n_label=""):
        ty = set(types)
        bucket.append({"w": w, "title": t(title_en, title_hi), "why": t(why_en, why_hi), "k": title_en, "conf": conf(ty, age, n),
                       "basis": ", ".join(sorted(ty)) + (f" ({n} {n_label})" if n is not None and n_label else "") + (f"; {age} days old" if age is not None else "")})

    peers = [x for x in universe.tickers() if x != ticker and universe.sector(x) == sector]

    def vs(kind: str):
        v, when = sig(ticker, kind)
        pv = [x for x in (val(p, kind) for p in peers) if x is not None]
        return v, _median(pv), len(pv), age_of(when)

    # ================================================================= the business, against peers
    pe, pe_m, pe_n, pe_age = vs("pe_ratio")
    roe, roe_m, roe_n, roe_age = vs("roe")
    mar, mar_m, mar_n, mar_age = vs("profit_margin")
    mcap, mcap_when = sig(ticker, "market_cap")

    want |= {"pe", "roe", "margin"}
    if pe and pe_m:
        ran.add("pe")
        if pe < pe_m * 0.9:
            add(pros, 3, "Priced lower than similar companies", "समान कंपनियों से सस्ते भाव पर",
                f"You pay about ₹{pe:.0f} for each ₹1 of yearly profit. Similar {sec_label.lower()} companies are about ₹{pe_m:.0f}. Cheaper is not automatically better, but you pay less for the same profit.",
                f"हर ₹1 के सालाना मुनाफ़े के लिए लगभग ₹{pe:.0f} देने पड़ते हैं। {sec_label} की समान कंपनियों में यह लगभग ₹{pe_m:.0f} है। सस्ता होना अपने आप बेहतर नहीं, पर उतने ही मुनाफ़े के लिए कम देना पड़ता है।",
                ("company numbers", "peers"), pe_age, pe_n, "peers")
        elif pe > pe_m * 1.15:
            add(cons, 3, "Priced higher than similar companies", "समान कंपनियों से महँगे भाव पर",
                f"You pay about ₹{pe:.0f} for each ₹1 of yearly profit, against about ₹{pe_m:.0f} for similar companies. The market expects more from it, so there is less room for disappointment.",
                f"हर ₹1 के सालाना मुनाफ़े के लिए लगभग ₹{pe:.0f} देने पड़ते हैं, जबकि समान कंपनियों में लगभग ₹{pe_m:.0f}। बाज़ार को इससे ज़्यादा उम्मीद है, इसलिए निराशा की गुंजाइश कम है।",
                ("company numbers", "peers"), pe_age, pe_n, "peers")
    elif pe is None:
        gaps.append(t("Its price compared with its profit (P/E): no figure saved.", "भाव बनाम मुनाफ़ा (P/E): कोई आँकड़ा सहेजा नहीं।"))

    if roe is not None:
        ran.add("roe")
        pk = ("company numbers", "peers") if roe_m else ("company numbers",)
        if roe >= 0.15 or (roe_m and roe > roe_m * 1.1):
            add(pros, 3, "Earns a good return on shareholders' money", "शेयरधारकों के पैसे पर अच्छी कमाई",
                f"It earns about {roe * 100:.0f} paise a year on every ₹1 shareholders have put in" + (f" (similar companies: about {roe_m * 100:.0f})." if roe_m else "."),
                f"शेयरधारकों के हर ₹1 पर यह साल में लगभग {roe * 100:.0f} पैसे कमाती है" + (f" (समान कंपनियाँ: लगभग {roe_m * 100:.0f})।" if roe_m else "।"),
                pk, roe_age, roe_n if roe_m else None, "peers")
        elif roe < 0.10 or (roe_m and roe < roe_m * 0.8):
            add(cons, 3, "Earns a modest return on shareholders' money", "शेयरधारकों के पैसे पर कमाई कम",
                f"It earns about {roe * 100:.0f} paise a year on every ₹1 shareholders have put in" + (f", below similar companies (about {roe_m * 100:.0f})." if roe_m else "."),
                f"शेयरधारकों के हर ₹1 पर यह साल में लगभग {roe * 100:.0f} पैसे कमाती है" + (f", जो समान कंपनियों (लगभग {roe_m * 100:.0f}) से कम है।" if roe_m else "।"),
                pk, roe_age, roe_n if roe_m else None, "peers")
    else:
        gaps.append(t("Return on shareholders' money (ROE): no figure saved.", "शेयरधारकों के पैसे पर कमाई (ROE): कोई आँकड़ा सहेजा नहीं।"))

    if mar is not None:
        ran.add("margin")
        if mar_m and mar > mar_m * 1.1:
            add(pros, 2, "Keeps more profit from each rupee of sales", "बिक्री के हर रुपये में से ज़्यादा मुनाफ़ा",
                f"About {mar * 100:.0f} paise of every ₹1 of sales is left as profit; similar companies keep about {mar_m * 100:.0f}.",
                f"बिक्री के हर ₹1 में से लगभग {mar * 100:.0f} पैसे मुनाफ़ा बचता है; समान कंपनियों में लगभग {mar_m * 100:.0f}।", ("company numbers", "peers"), mar_age, mar_n, "peers")
        elif mar_m and mar < mar_m * 0.8:
            add(cons, 2, "Keeps less profit from each rupee of sales", "बिक्री के हर रुपये में से कम मुनाफ़ा",
                f"About {mar * 100:.0f} paise of every ₹1 of sales is left as profit; similar companies keep about {mar_m * 100:.0f}.",
                f"बिक्री के हर ₹1 में से लगभग {mar * 100:.0f} पैसे मुनाफ़ा बचता है; समान कंपनियों में लगभग {mar_m * 100:.0f}।", ("company numbers", "peers"), mar_age, mar_n, "peers")
    else:
        gaps.append(t("Profit margin: no figure saved.", "मुनाफ़ा मार्जिन: कोई आँकड़ा सहेजा नहीं।"))

    want.add("size")
    if mcap:
        ran.add("size")
        ag = age_of(mcap_when)
        if (cur == "₹" and mcap >= 1e12) or (cur == "$" and mcap >= 1e11):
            add(pros, 1, "A very large, well-established company", "बहुत बड़ी, जमी हुई कंपनी",
                f"Its market value is about {_money(mcap, cur)}. Very large companies tend to swing less than small ones, though they can still fall.",
                f"इसका बाज़ार मूल्य लगभग {_money(mcap, cur)} है। बहुत बड़ी कंपनियाँ आम तौर पर छोटी से कम झूलती हैं, पर गिर वे भी सकती हैं।", ("company numbers",), ag)
        elif (cur == "₹" and mcap < 2e11) or (cur == "$" and mcap < 2e9):
            add(cons, 1, "A smaller company", "अपेक्षाकृत छोटी कंपनी",
                f"Its market value is about {_money(mcap, cur)}. Smaller companies usually have bigger price swings and are harder to sell in a hurry.",
                f"इसका बाज़ार मूल्य लगभग {_money(mcap, cur)} है। छोटी कंपनियों में भाव ज़्यादा झूलता है और जल्दी बेचना कठिन हो सकता है।", ("company numbers",), ag)

    # ================================================================= A: growth, cash, safety, income, quality
    rg, rg_w = sig(ticker, "rev_growth")
    eg, eg_w = sig(ticker, "earn_growth")
    cagr, cagr_w = sig(ticker, "rev_cagr_3y")
    want |= {"growth_sales", "growth_profit", "growth_3y"}
    if rg is not None:
        ran.add("growth_sales")
        if rg >= 0.12:
            add(pros, 2, "Sales are growing fast", "बिक्री तेज़ी से बढ़ रही है",
                f"Sales in the latest quarter were {rg * 100:.0f}% higher than a year earlier. Growth is what lets a company earn more over time.",
                f"ताज़ा तिमाही की बिक्री एक साल पहले से {rg * 100:.0f}% ज़्यादा रही। बढ़त ही कंपनी को समय के साथ ज़्यादा कमाने देती है।", ("financial statements",), age_of(rg_w))
        elif rg <= 0:
            add(cons, 2, "Sales are shrinking", "बिक्री घट रही है",
                f"Sales in the latest quarter were {abs(rg) * 100:.0f}% lower than a year earlier. One quarter can be a blip; a run of them is a trend.",
                f"ताज़ा तिमाही की बिक्री एक साल पहले से {abs(rg) * 100:.0f}% कम रही। एक तिमाही अपवाद हो सकती है; लगातार कई हों तो रुझान है।", ("financial statements",), age_of(rg_w))
    else:
        gaps.append(t("Sales growth: no figure saved.", "बिक्री की बढ़त: कोई आँकड़ा सहेजा नहीं।"))
    if eg is not None:
        ran.add("growth_profit")
        if eg >= 0.15:
            add(pros, 2, "Profits are growing", "मुनाफ़ा बढ़ रहा है",
                f"Profit in the latest quarter was {eg * 100:.0f}% higher than a year earlier.", f"ताज़ा तिमाही का मुनाफ़ा एक साल पहले से {eg * 100:.0f}% ज़्यादा रहा।", ("financial statements",), age_of(eg_w))
        elif eg <= -0.05:
            add(cons, 2, "Profits are shrinking", "मुनाफ़ा घट रहा है",
                f"Profit in the latest quarter was {abs(eg) * 100:.0f}% lower than a year earlier.", f"ताज़ा तिमाही का मुनाफ़ा एक साल पहले से {abs(eg) * 100:.0f}% कम रहा।", ("financial statements",), age_of(eg_w))
    if cagr is not None:
        ran.add("growth_3y")
        if cagr >= 0.12:
            add(pros, 1, "Consistent growth over three years", "तीन साल से लगातार बढ़त",
                f"Yearly sales grew about {cagr * 100:.0f}% a year, on average, over the last three fiscal years.", f"पिछले तीन वित्त वर्षों में सालाना बिक्री औसतन लगभग {cagr * 100:.0f}% प्रति वर्ष बढ़ी।", ("financial statements",), age_of(cagr_w))
        elif cagr <= 0.02:
            add(cons, 1, "Little growth over three years", "तीन साल में बहुत कम बढ़त",
                f"Yearly sales grew only about {cagr * 100:.0f}% a year, on average, over the last three fiscal years.", f"पिछले तीन वित्त वर्षों में सालाना बिक्री औसतन केवल लगभग {cagr * 100:.0f}% प्रति वर्ष बढ़ी।", ("financial statements",), age_of(cagr_w))

    if is_fin:
        gaps.append(t("Debt, short-term liquidity, cash-flow conversion and distress scores are left out for banks and lenders: they do not mean the same thing for a company whose business is lending.",
                      "क़र्ज़, अल्पकालिक तरलता, नक़दी-रूपांतरण और संकट-स्कोर बैंकों और ऋणदाताओं के लिए छोड़े गए हैं: जिस कंपनी का कारोबार ही उधार देना है उसके लिए इनका मतलब वही नहीं होता।"))
    else:
        want |= {"cash_conv", "fcf", "debt", "cover", "liquidity", "altman", "piotroski"}
        o2n, o2n_w = sig(ticker, "ocf_to_ni")
        if o2n is not None:
            ran.add("cash_conv")
            if o2n >= 0.9:
                add(pros, 3, "Its profit turns into real cash", "इसका मुनाफ़ा असली नक़दी बनता है",
                    f"For each ₹1 of reported profit it brought in about ₹{o2n:.2f} of cash from operations in its last fiscal year. Profit that arrives as cash is harder to fake and easier to spend or pay out.",
                    f"पिछले वित्त वर्ष में बताए गए हर ₹1 मुनाफ़े पर इसने कारोबार से लगभग ₹{o2n:.2f} नक़द कमाया। जो मुनाफ़ा नक़द आता है उसे दिखावटी बनाना कठिन है और ख़र्च या बाँटना आसान।",
                    ("financial statements",), age_of(o2n_w))
            elif o2n < 0.6:
                add(cons, 3, "Its profit is not turning into cash", "इसका मुनाफ़ा नक़दी नहीं बन रहा",
                    f"For each ₹1 of reported profit it brought in only about ₹{o2n:.2f} of cash from operations in its last fiscal year. That can mean customers pay late or profit is being counted before it is collected.",
                    f"पिछले वित्त वर्ष में बताए गए हर ₹1 मुनाफ़े पर इसने कारोबार से केवल लगभग ₹{o2n:.2f} नक़द कमाया। इसका मतलब ग्राहक देर से चुका रहे हैं, या मुनाफ़ा वसूली से पहले गिना जा रहा है।",
                    ("financial statements",), age_of(o2n_w))
        fcf, fcf_w = sig(ticker, "fcf")
        if fcf is not None:
            ran.add("fcf")
            if fcf < 0:
                add(cons, 2, "It spends more cash than it brings in", "यह कमाई से ज़्यादा नक़द ख़र्च कर रही है",
                    "After paying for its investments, its free cash flow is negative. It must borrow, issue new shares or run down savings to keep going. That is normal in a fast-growing business and a warning in a slow one.",
                    "निवेश का ख़र्च चुकाने के बाद इसका फ़्री कैश फ़्लो ऋणात्मक है। चलते रहने के लिए इसे उधार लेना, शेयर बेचना या बचत घटानी पड़ेगी। तेज़ी से बढ़ते कारोबार में यह सामान्य है, धीमे कारोबार में चेतावनी।",
                    ("financial statements",), age_of(fcf_w))
            elif mcap and fcf / mcap >= 0.03:
                add(pros, 2, "It generates spare cash after investing", "निवेश के बाद भी इसके पास फ़ालतू नक़द बचता है",
                    f"After its investments it has about {fcf / mcap * 100:.1f}% of its market value left over each year as free cash. That money can pay dividends, cut debt or fund growth.",
                    f"निवेश के बाद हर साल इसके बाज़ार मूल्य का लगभग {fcf / mcap * 100:.1f}% फ़्री कैश बचता है। उस पैसे से लाभांश, क़र्ज़ घटाना या बढ़त का ख़र्च हो सकता है।",
                    ("financial statements", "company numbers"), age_of(fcf_w))
        de, de_w = sig(ticker, "debt_to_equity")
        if de is not None:
            ran.add("debt")
            if de < 30:
                add(pros, 2, "Little debt compared with its own capital", "अपनी पूँजी की तुलना में कम क़र्ज़",
                    f"Its borrowings are about {de:.0f}% of what shareholders own in it. Low debt means a bad year is easier to survive.",
                    f"इसका क़र्ज़ शेयरधारकों की अपनी हिस्सेदारी का लगभग {de:.0f}% है। कम क़र्ज़ का मतलब है कि बुरा साल झेलना आसान।", ("financial statements",), age_of(de_w))
            elif de > 150:
                add(cons, 3, "Heavy debt compared with its own capital", "अपनी पूँजी की तुलना में भारी क़र्ज़",
                    f"Its borrowings are about {de:.0f}% of what shareholders own in it. High debt magnifies both good years and bad ones, and interest has to be paid either way.",
                    f"इसका क़र्ज़ शेयरधारकों की अपनी हिस्सेदारी का लगभग {de:.0f}% है। भारी क़र्ज़ अच्छे और बुरे दोनों सालों को बड़ा कर देता है, और ब्याज हर हाल में चुकाना पड़ता है।", ("financial statements",), age_of(de_w))
        ic, ic_w = sig(ticker, "interest_cover")
        if ic is not None:
            ran.add("cover")
            if ic >= 8:
                add(pros, 2, "Earns many times its interest bill", "अपने ब्याज के बिल से कई गुना कमाती है",
                    f"Its operating profit is about {ic:.0f} times its yearly interest cost, so lenders are very well covered.", f"इसका परिचालन मुनाफ़ा सालाना ब्याज के लगभग {ic:.0f} गुना है, यानी ऋणदाता बहुत सुरक्षित हैं।", ("financial statements",), age_of(ic_w))
            elif ic < 3:
                add(cons, 3, "Earnings only just cover the interest", "कमाई ब्याज को बस पूरा करती है",
                    f"Its operating profit is only about {ic:.1f} times its yearly interest cost. A dip in earnings could make the interest hard to pay.",
                    f"इसका परिचालन मुनाफ़ा सालाना ब्याज का केवल लगभग {ic:.1f} गुना है। कमाई गिरी तो ब्याज चुकाना कठिन हो सकता है।", ("financial statements",), age_of(ic_w))
        cr, cr_w = sig(ticker, "current_ratio")
        if cr is not None:
            ran.add("liquidity")
            if cr < 1:
                add(cons, 1, "Short-term bills exceed short-term assets", "छोटी अवधि के बिल छोटी अवधि की संपत्ति से ज़्यादा",
                    f"For each ₹1 it must pay within a year it holds about ₹{cr:.2f} of assets that turn to cash within a year. That is tight unless its customers pay very quickly.",
                    f"एक साल में चुकाने वाले हर ₹1 के सामने इसके पास एक साल में नक़द बनने वाली लगभग ₹{cr:.2f} की संपत्ति है। जब तक ग्राहक बहुत जल्दी न चुकाएँ, यह तंग है।", ("financial statements",), age_of(cr_w))
        z, z_w = sig(ticker, "altman_z")
        if z is not None:
            ran.add("altman")
            if z < 1.8:
                add(cons, 3, "A standard distress score is in the warning zone", "एक मानक संकट-स्कोर चेतावनी वाले क्षेत्र में है",
                    f"The Altman Z-score, which blends profit, debt and assets into one number, is {z:.1f}; below 1.8 is usually read as financial strain. It is a screen, not a verdict.",
                    f"ऑल्टमैन Z-स्कोर, जो मुनाफ़े, क़र्ज़ और संपत्ति को एक संख्या में मिलाता है, {z:.1f} है; 1.8 से नीचे को आम तौर पर आर्थिक दबाव माना जाता है। यह छन्नी है, फ़ैसला नहीं।", ("financial statements", "company numbers"), age_of(z_w))
            elif z > 3:
                add(pros, 2, "A standard distress score reads safe", "एक मानक संकट-स्कोर सुरक्षित पढ़ता है",
                    f"The Altman Z-score, which blends profit, debt and assets into one number, is {z:.1f}; above 3 is usually read as financially sound.",
                    f"ऑल्टमैन Z-स्कोर, जो मुनाफ़े, क़र्ज़ और संपत्ति को एक संख्या में मिलाता है, {z:.1f} है; 3 से ऊपर को आम तौर पर आर्थिक रूप से मज़बूत माना जाता है।", ("financial statements", "company numbers"), age_of(z_w))
        pf_s = pit.latest(ticker, "piotroski_f")
        if pf_s is not None and pf_s.value_num is not None:
            pf, pf_w = pf_s.value_num, pf_s.as_of
            ran.add("piotroski")
            try:
                tests = int((pf_s.value_text or "").split(" of ")[1].split()[0])
            except (IndexError, ValueError):
                tests = 9
            if pf >= max(6, tests - 2):
                add(pros, 2, "Healthy on a standard financial checklist", "मानक वित्तीय चेकलिस्ट पर स्वस्थ",
                    f"It passed {int(pf)} of {tests} standard checks (Piotroski score) on whether profit, cash, debt and efficiency improved over the last year.",
                    f"पिछले साल मुनाफ़ा, नक़दी, क़र्ज़ और कार्यकुशलता सुधरी या नहीं, इसकी {tests} मानक जाँचों (पियोत्रोस्की स्कोर) में से यह {int(pf)} में पास हुई।", ("financial statements",), age_of(pf_w), tests, "tests")
            elif pf <= 3:
                add(cons, 2, "Weak on a standard financial checklist", "मानक वित्तीय चेकलिस्ट पर कमज़ोर",
                    f"It passed only {int(pf)} of {tests} standard checks (Piotroski score) on whether profit, cash, debt and efficiency improved over the last year.",
                    f"पिछले साल मुनाफ़ा, नक़दी, क़र्ज़ और कार्यकुशलता सुधरी या नहीं, इसकी {tests} मानक जाँचों (पियोत्रोस्की स्कोर) में से यह केवल {int(pf)} में पास हुई।", ("financial statements",), age_of(pf_w), tests, "tests")
        if not ({"cash_conv", "debt", "cover"} & ran):
            gaps.append(t("Debt, cash flow and financial-health scores: no statements saved for this company yet.", "क़र्ज़, नक़दी-प्रवाह और वित्तीय-स्वास्थ्य स्कोर: इस कंपनी के बही-खाते अभी सहेजे नहीं हैं।"))

    dy, dy_w = sig(ticker, "div_yield")
    po, po_w = sig(ticker, "payout")
    want.add("dividend")
    if dy is not None:
        ran.add("dividend")
        if dy >= 0.015 and (po is None or po <= 0.75):
            add(pros, 1, "Pays a regular dividend it can afford", "नियमित लाभांश देती है जो वह वहन कर सकती है",
                f"The dividend is about {dy * 100:.1f}% of the share price a year" + (f", and it pays out about {po * 100:.0f}% of its profit, which leaves room to keep paying." if po is not None else "."),
                f"लाभांश शेयर के भाव का लगभग {dy * 100:.1f}% सालाना है" + (f", और यह अपने मुनाफ़े का लगभग {po * 100:.0f}% बाँटती है, जिससे आगे भी देते रहने की गुंजाइश है।" if po is not None else "।"),
                ("company numbers",), age_of(dy_w))
    if po is not None and po > 1.0:
        add(cons, 2, "Paying out more than it earns", "कमाई से ज़्यादा बाँट रही है",
            f"Its payout is about {po * 100:.0f}% of its profit, so the dividend is being funded from savings or borrowing. That cannot continue forever.",
            f"इसका भुगतान मुनाफ़े का लगभग {po * 100:.0f}% है, यानी लाभांश बचत या उधार से दिया जा रहा है। यह हमेशा नहीं चल सकता।", ("company numbers",), age_of(po_w))

    # ================================================================= B: valuation in context
    hm_s = pit.latest(ticker, "pe_hist_median")
    hmed, hm_w = (hm_s.value_num, hm_s.as_of) if hm_s is not None else (None, None)
    hlow, hhigh = val(ticker, "pe_hist_low"), val(ticker, "pe_hist_high")
    try:
        hn = int((hm_s.value_text or "0").split()[0]) if hm_s is not None else 0
    except ValueError:
        hn = 0
    want |= {"pe_own", "peg"}
    if pe and hmed and hn >= 3 and hlow is not None and hhigh is not None:
        ran.add("pe_own")
        r = pe / hmed
        rng = f"(between ₹{hlow:.0f} and ₹{hhigh:.0f})"
        if r <= 0.85:
            add(pros, 3, "Priced below its own usual level", "अपने सामान्य स्तर से सस्ते भाव पर",
                f"Today you pay about ₹{pe:.0f} for each ₹1 of yearly profit. At the end of its last {hn} financial years the figure was typically ₹{hmed:.0f} {rng}. It is cheaper than it usually is. That can mean a bargain or that the business has weakened.",
                f"आज हर ₹1 के सालाना मुनाफ़े के लिए लगभग ₹{pe:.0f} देने पड़ते हैं। पिछले {hn} वित्त वर्षों के अंत में यह सामान्यतः ₹{hmed:.0f} था (₹{hlow:.0f} से ₹{hhigh:.0f} के बीच)। यह अपने सामान्य से सस्ती है। इसका मतलब सौदा भी हो सकता है, या कारोबार कमज़ोर हुआ हो।",
                ("company numbers", "prices"), age_of(hm_w), hn, "year-ends")
        elif r >= 1.2:
            add(cons, 3, "Priced above its own usual level", "अपने सामान्य स्तर से महँगे भाव पर",
                f"Today you pay about ₹{pe:.0f} for each ₹1 of yearly profit. At the end of its last {hn} financial years the figure was typically ₹{hmed:.0f} {rng}. It is dearer than it usually is, so the market is expecting better than before.",
                f"आज हर ₹1 के सालाना मुनाफ़े के लिए लगभग ₹{pe:.0f} देने पड़ते हैं। पिछले {hn} वित्त वर्षों के अंत में यह सामान्यतः ₹{hmed:.0f} था (₹{hlow:.0f} से ₹{hhigh:.0f} के बीच)। यह अपने सामान्य से महँगी है, यानी बाज़ार को पहले से बेहतर की उम्मीद है।",
                ("company numbers", "prices"), age_of(hm_w), hn, "year-ends")
    elif pe is not None:
        gaps.append(t("Its price against its own past range: not enough years of earnings saved.", "अपने पुराने दायरे से भाव की तुलना: कमाई के पर्याप्त साल सहेजे नहीं हैं।"))
    if pe and eg and eg > 0.05:
        ran.add("peg")
        peg = pe / (eg * 100)
        if peg < 1:
            add(pros, 2, "You pay little for its growth", "इसकी बढ़त के लिए कम देना पड़ता है",
                f"The price-to-profit figure ({pe:.0f}) is only {peg:.1f} times its recent profit growth rate ({eg * 100:.0f}%). Under 1 is generally read as paying little for growth, provided the growth lasts.",
                f"भाव-बनाम-मुनाफ़ा ({pe:.0f}) हाल की मुनाफ़ा-बढ़त दर ({eg * 100:.0f}%) का केवल {peg:.1f} गुना है। 1 से कम को आम तौर पर बढ़त के लिए कम देना माना जाता है, बशर्ते बढ़त टिके।",
                ("company numbers", "financial statements"), age_of(eg_w))
        elif peg > 2.5:
            add(cons, 2, "You pay a lot for its growth", "इसकी बढ़त के लिए बहुत देना पड़ता है",
                f"The price-to-profit figure ({pe:.0f}) is {peg:.1f} times its recent profit growth rate ({eg * 100:.0f}%). Above 2.5 means the price already assumes the growth continues or speeds up.",
                f"भाव-बनाम-मुनाफ़ा ({pe:.0f}) हाल की मुनाफ़ा-बढ़त दर ({eg * 100:.0f}%) का {peg:.1f} गुना है। 2.5 से ऊपर का मतलब है कि भाव पहले से मानकर चल रहा है कि बढ़त जारी रहेगी या तेज़ होगी।",
                ("company numbers", "financial statements"), age_of(eg_w))

    # how it ranks among similar companies, on several measures at once
    ranks = []
    for kind, label_en, label_hi, higher, fmt in (
            ("pe_ratio", "Price vs profit (lower is cheaper)", "भाव बनाम मुनाफ़ा (कम = सस्ता)", False, "{:.1f}"),
            ("roe", "Return on shareholders' money", "शेयरधारकों के पैसे पर कमाई", True, "{:.0%}"),
            ("profit_margin", "Profit margin", "मुनाफ़ा मार्जिन", True, "{:.0%}"),
            ("rev_growth", "Sales growth", "बिक्री की बढ़त", True, "{:.0%}"),
            ("debt_to_equity", "Debt vs capital (lower is safer)", "क़र्ज़ बनाम पूँजी (कम = सुरक्षित)", False, "{:.0f}%")):
        if is_fin and kind == "debt_to_equity":
            continue
        mine = val(ticker, kind)
        pv = [x for x in (val(p, kind) for p in peers) if x is not None]
        if mine is None or len(pv) < 3:
            continue
        better = sum(1 for x in pv if (x > mine if higher else x < mine))
        ranks.append({"metric": t(label_en, label_hi), "value": fmt.format(mine), "rank": better + 1, "of": len(pv) + 1})
    want.add("ranks")
    if ranks:
        ran.add("ranks")

    # ================================================================= C: who owns it
    want.add("ownership")
    ins, ins_w = sig(ticker, "holding_insiders")
    inst, inst_w = sig(ticker, "holding_institutions")
    if ins is not None:
        ran.add("ownership")
        if ins >= 0.5:
            add(pros, 2, "Its founders or promoters own a large stake", "संस्थापकों या प्रवर्तकों के पास बड़ी हिस्सेदारी है",
                f"Insiders (promoters and management) own about {ins * 100:.0f}% of the company. They win or lose alongside shareholders. A large controlling stake also means outside shareholders have little say.",
                f"भीतरी लोगों (प्रवर्तक और प्रबंधन) के पास कंपनी का लगभग {ins * 100:.0f}% है। वे शेयरधारकों के साथ ही जीतते या हारते हैं। बड़ी नियंत्रक हिस्सेदारी का यह भी मतलब है कि बाहरी शेयरधारकों की सुनवाई कम है।",
                ("ownership",), age_of(ins_w))
        elif ins < 0.10:
            add(cons, 1, "No controlling owner with a big stake", "बड़ी हिस्सेदारी वाला कोई नियंत्रक मालिक नहीं",
                f"Insiders own only about {ins * 100:.0f}%. That can mean professional management with nobody firmly in charge, and control can change hands more easily.",
                f"भीतरी लोगों के पास केवल लगभग {ins * 100:.0f}% है। इसका मतलब पेशेवर प्रबंधन हो सकता है जिसके ऊपर कोई मज़बूत मालिक नहीं, और नियंत्रण आसानी से बदल सकता है।", ("ownership",), age_of(ins_w))
        # a trend exists only once there are two snapshots at least three weeks apart
        snaps = [s for s in pit.signals(ticker, kind="holding_insiders", limit=12) if s.value_num is not None]
        if len(snaps) >= 2 and (_utc(snaps[0].as_of) - _utc(snaps[-1].as_of)).days >= 21:
            d = (snaps[0].value_num - snaps[-1].value_num) * 100
            d0, d1 = _utc(snaps[-1].as_of).date(), _utc(snaps[0].as_of).date()
            if d <= -1.5:
                add(cons, 3, "Promoters have reduced their stake", "प्रवर्तकों ने अपनी हिस्सेदारी घटाई है",
                    f"Insider ownership fell by about {abs(d):.1f} percentage points between our snapshots of {d0} and {d1}. Insiders selling is worth understanding, though there are many innocent reasons.",
                    f"हमारे {d0} और {d1} के स्नैपशॉट के बीच भीतरी हिस्सेदारी लगभग {abs(d):.1f} प्रतिशत अंक घटी। भीतरी लोगों का बेचना समझने लायक़ है, हालाँकि कई मासूम कारण हो सकते हैं।",
                    ("ownership",), age_of(snaps[0].as_of), len(snaps), "snapshots")
            elif d >= 1.5:
                add(pros, 2, "Promoters have raised their stake", "प्रवर्तकों ने अपनी हिस्सेदारी बढ़ाई है",
                    f"Insider ownership rose by about {d:.1f} percentage points between our snapshots of {d0} and {d1}. Insiders buying with their own money is a vote of confidence, not a guarantee.",
                    f"हमारे {d0} और {d1} के स्नैपशॉट के बीच भीतरी हिस्सेदारी लगभग {d:.1f} प्रतिशत अंक बढ़ी। भीतरी लोगों का अपने पैसे से ख़रीदना भरोसे का संकेत है, गारंटी नहीं।",
                    ("ownership",), age_of(snaps[0].as_of), len(snaps), "snapshots")
        else:
            gaps.append(t("Whether promoters are buying or selling: we have only one snapshot so far. The trend appears once the data has been refreshed a few weeks apart.",
                          "प्रवर्तक ख़रीद रहे हैं या बेच रहे हैं: अब तक हमारे पास एक ही स्नैपशॉट है। कुछ हफ़्तों के अंतर पर डेटा ताज़ा होने पर रुझान दिखेगा।"))
    else:
        gaps.append(t("Who owns the company (promoters, institutions): no figure saved.", "कंपनी का मालिक कौन (प्रवर्तक, संस्थाएँ): कोई आँकड़ा सहेजा नहीं।"))
    if inst is not None:
        if inst >= 0.35:
            add(pros, 1, "Large funds own a big part of it", "बड़े फ़ंडों के पास इसका बड़ा हिस्सा है",
                f"Institutions (mutual funds, insurers, foreign investors) own about {inst * 100:.0f}%. They research companies closely, though if they all leave at once the price can fall fast.",
                f"संस्थाओं (म्यूचुअल फ़ंड, बीमा कंपनियाँ, विदेशी निवेशक) के पास लगभग {inst * 100:.0f}% है। वे कंपनियों को बारीकी से परखते हैं, पर साथ बेचें तो भाव तेज़ी से गिर सकता है।", ("ownership",), age_of(inst_w))
        elif inst < 0.05:
            add(cons, 1, "Few big funds own it", "बहुत कम बड़े फ़ंड इसे रखते हैं",
                f"Institutions own only about {inst * 100:.0f}%. That means less professional scrutiny and, often, less trading in the shares.",
                f"संस्थाओं के पास केवल लगभग {inst * 100:.0f}% है। इसका मतलब पेशेवर जाँच कम और अक्सर शेयरों का कारोबार भी कम।", ("ownership",), age_of(inst_w))
    gaps.append(t("Promoter share pledging (shares put up as security for loans, a known risk in India) is not in our free data yet.",
                  "प्रवर्तकों की शेयर गिरवी (क़र्ज़ की ज़मानत में रखे शेयर, भारत में एक जाना-पहचाना जोखिम) अभी हमारे मुफ़्त डेटा में नहीं है।"))

    # ================================================================= the chart, read like a technician but never turned into a signal
    rows = [r for r in pit.prices(ticker, 250) if r.get("close")]
    px = [r["close"] for r in rows]
    ret = dd = vol = off_high = None
    want |= {"trend", "range", "momentum", "relative", "volume"}
    if len(px) >= 60:
        p_age = age_of(rows[-1]["date"])
        ret = px[-1] / px[0] - 1
        peak, dd = px[0], 0.0
        for p in px:
            peak = max(peak, p)
            dd = min(dd, p / peak - 1)
        rets = [math.log(b / a) for a, b in zip(px, px[1:]) if a > 0 and b > 0]
        vol = statistics.pstdev(rets) * math.sqrt(252) if len(rets) > 20 else None
        off_high = px[-1] / max(px) - 1
        months = max(2, round(len(px) / 21))
        span = t(f"the last {months} months", f"पिछले {months} महीनों")
        ran.add("range")
        if ret > 0.10:
            add(pros, 2, "The price has risen over the past year", "पिछले साल भाव बढ़ा है",
                f"The share price is up about {ret * 100:.0f}% over {span}. A past rise says nothing about what comes next.", f"{span} में शेयर का भाव लगभग {ret * 100:.0f}% बढ़ा है। पिछली बढ़त से आगे का कुछ पता नहीं चलता।", ("prices",), p_age, len(px), "days")
        elif ret < -0.10:
            add(cons, 2, "The price has fallen over the past year", "पिछले साल भाव गिरा है",
                f"The share price is down about {abs(ret) * 100:.0f}% over {span}. It may be cheaper now, or the market may see a problem: the numbers alone do not say which.",
                f"{span} में शेयर का भाव लगभग {abs(ret) * 100:.0f}% गिरा है। हो सकता है अब सस्ता हो, या बाज़ार को कोई दिक़्क़त दिख रही हो: सिर्फ़ आँकड़ों से पता नहीं चलता।", ("prices",), p_age, len(px), "days")
        if dd < -0.25:
            add(cons, 2, "It has had a big fall from its peak", "अपने ऊँचे भाव से बड़ी गिरावट आई है",
                f"At its worst point in this period the price was {abs(dd) * 100:.0f}% below its earlier high. If you own it, expect rough patches.",
                f"इस अवधि में सबसे बुरे समय भाव अपने पिछले ऊँचे भाव से {abs(dd) * 100:.0f}% नीचे था। रखेंगे तो उतार-चढ़ाव के दौर झेलने पड़ सकते हैं।", ("prices",), p_age, len(px), "days")
        elif dd > -0.12:
            add(pros, 1, "Its price has been fairly steady", "इसका भाव काफ़ी स्थिर रहा है",
                f"Even at its worst point the price was only {abs(dd) * 100:.0f}% below its earlier high.", f"सबसे बुरे समय भी भाव अपने पिछले ऊँचे भाव से सिर्फ़ {abs(dd) * 100:.0f}% नीचे था।", ("prices",), p_age, len(px), "days")
        if vol is not None and vol > 0.35:
            add(cons, 1, "The price swings a lot", "भाव बहुत झूलता है",
                f"Day to day the price moves a lot (about {vol * 100:.0f}% a year on a standard measure). That is harder to sit through.",
                f"दिन-ब-दिन भाव काफ़ी हिलता है (एक मानक पैमाने पर साल का लगभग {vol * 100:.0f}%)। इसे झेलना कठिन हो सकता है।", ("prices",), p_age, len(px), "days")
        if len(px) >= 200:
            last = px[-1]
            ma200, ma50 = sum(px[-200:]) / 200, sum(px[-50:]) / 50
            ran.add("trend")
            if last > ma200 and ma50 > ma200:
                add(pros, 2, "Trading above its long-term averages", "अपने लंबी अवधि के औसत से ऊपर चल रहा है",
                    f"The price (₹{last:,.0f}) is above both its 50-day average (₹{ma50:,.0f}) and its 200-day average (₹{ma200:,.0f}). That is what a steady uptrend looks like; it describes the past, not the future.",
                    f"भाव (₹{last:,.0f}) अपने 50-दिन (₹{ma50:,.0f}) और 200-दिन (₹{ma200:,.0f}) दोनों औसत से ऊपर है। स्थिर बढ़त ऐसी दिखती है; यह बीते कल की बात है, आने वाले कल की नहीं।", ("prices",), p_age, len(px), "days")
            elif last < ma200 and ma50 < ma200:
                add(cons, 2, "Trading below its long-term averages", "अपने लंबी अवधि के औसत से नीचे चल रहा है",
                    f"The price (₹{last:,.0f}) is below both its 50-day average (₹{ma50:,.0f}) and its 200-day average (₹{ma200:,.0f}). That is what a downtrend looks like. Trends can turn, so treat it as a description, not a verdict.",
                    f"भाव (₹{last:,.0f}) अपने 50-दिन (₹{ma50:,.0f}) और 200-दिन (₹{ma200:,.0f}) दोनों औसत से नीचे है। गिरावट का रुझान ऐसा दिखता है। रुझान पलट सकते हैं, इसलिए इसे वर्णन समझिए, फ़ैसला नहीं।", ("prices",), p_age, len(px), "days")
        if len(px) >= 30:
            ran.add("momentum")
            gains = [max(0.0, b - a) for a, b in zip(px[-15:], px[-14:])]
            losses = [max(0.0, a - b) for a, b in zip(px[-15:], px[-14:])]
            ag, al = sum(gains) / 14, sum(losses) / 14
            rsi = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
            if rsi >= 70:
                add(cons, 1, "It has run up fast recently", "हाल में तेज़ी से चढ़ा है",
                    f"Over the last two weeks it rose far more days than it fell (a standard momentum reading, RSI, is {rsi:.0f}; above 70 is usually called stretched). Fast rises are sometimes followed by a pause.",
                    f"पिछले दो हफ़्तों में यह गिरने से कहीं ज़्यादा दिन चढ़ा (मानक गति-पैमाना RSI {rsi:.0f} है; 70 से ऊपर को आम तौर पर खिंचा हुआ कहते हैं)। तेज़ चढ़ाव के बाद कभी-कभी ठहराव आता है।", ("prices",), p_age, len(px), "days")
            elif rsi <= 30:
                add(cons, 1, "It has dropped fast recently", "हाल में तेज़ी से गिरा है",
                    f"Over the last two weeks it fell far more days than it rose (momentum reading RSI is {rsi:.0f}; below 30 is usually called oversold). Sharp drops sometimes bounce, and sometimes keep going.",
                    f"पिछले दो हफ़्तों में यह चढ़ने से कहीं ज़्यादा दिन गिरा (गति-पैमाना RSI {rsi:.0f} है; 30 से नीचे को आम तौर पर ज़्यादा बिका हुआ कहते हैं)। तेज़ गिरावट के बाद कभी उछाल आता है, कभी गिरावट जारी रहती है।", ("prices",), p_age, len(px), "days")
        if len(px) >= 120:
            def yr(tk):
                q = [r["close"] for r in pit.prices(tk, 250) if r.get("close")]
                return (q[-1] / q[0] - 1) if len(q) >= 120 else None
            peer_rets = [v for v in (yr(x) for x in peers[:12]) if v is not None]
            if len(peer_rets) >= 3:
                ran.add("relative")
                pm = _median(peer_rets)
                diff = (ret - pm) * 100
                if diff >= 8:
                    add(pros, 2, "It has done better than similar companies", "समान कंपनियों से बेहतर रहा है",
                        f"Over the same period its price moved {ret * 100:+.0f}%, against about {pm * 100:+.0f}% for similar {sec_label.lower()} companies. Doing better than the group means the move is not just the whole sector rising.",
                        f"इसी अवधि में इसका भाव {ret * 100:+.0f}% चला, जबकि समान {sec_label} कंपनियों में लगभग {pm * 100:+.0f}%। समूह से बेहतर होने का मतलब है कि यह सिर्फ़ पूरे सेक्टर के चढ़ने से नहीं हुआ।", ("prices", "peers"), p_age, len(peer_rets), "peers")
                elif diff <= -8:
                    add(cons, 2, "It has lagged similar companies", "समान कंपनियों से पीछे रहा है",
                        f"Over the same period its price moved {ret * 100:+.0f}%, against about {pm * 100:+.0f}% for similar {sec_label.lower()} companies. Lagging the group suggests the weakness is about this company, not just the sector.",
                        f"इसी अवधि में इसका भाव {ret * 100:+.0f}% चला, जबकि समान {sec_label} कंपनियों में लगभग {pm * 100:+.0f}%। समूह से पीछे रहने का मतलब है कि कमज़ोरी इसी कंपनी की है, सिर्फ़ सेक्टर की नहीं।", ("prices", "peers"), p_age, len(peer_rets), "peers")
        vols = [r.get("volume") or 0 for r in rows]
        if len(vols) >= 120 and sum(vols[-120:-20]) > 0:
            ran.add("volume")
            ratio = (sum(vols[-20:]) / 20) / (sum(vols[-120:-20]) / 100)
            if ratio >= 1.6:
                add(cons, 1, "Unusually heavy trading lately", "हाल में असामान्य रूप से भारी कारोबार",
                    f"Shares changed hands about {ratio:.1f} times as often as usual over the last month. That usually means news or a change of mind among big holders: worth finding out why before you decide.",
                    f"पिछले महीने शेयर सामान्य से लगभग {ratio:.1f} गुना बार हाथ बदले। इसका मतलब आम तौर पर कोई ख़बर या बड़े धारकों का मन बदलना होता है: फ़ैसले से पहले कारण जानना ठीक रहेगा।", ("prices",), p_age, len(px), "days")
        if len(px) >= 120:
            lo = min(px)
            if px[-1] <= lo * 1.05:
                add(cons, 1, "Close to its lowest price of the year", "साल के सबसे निचले भाव के क़रीब",
                    f"It is within about 5% of the lowest level of the past year (₹{lo:,.0f}). A low price is not a bargain by itself; check why it is low.",
                    f"यह पिछले साल के सबसे निचले स्तर (₹{lo:,.0f}) के लगभग 5% के भीतर है। नीचा भाव अपने आप सौदा नहीं होता; देखिए कि नीचा क्यों है।", ("prices",), p_age, len(px), "days")
            elif off_high >= -0.03:
                add(pros, 1, "Close to its highest price of the year", "साल के सबसे ऊँचे भाव के क़रीब",
                    "It is within about 3% of its highest level of the past year, so the market has recently been willing to pay this much. It also means little cushion if sentiment turns.",
                    "यह पिछले साल के सबसे ऊँचे स्तर के लगभग 3% के भीतर है, यानी बाज़ार हाल में इतना देने को तैयार रहा है। साथ ही रुख़ पलटे तो गुंजाइश कम है।", ("prices",), p_age, len(px), "days")
    else:
        gaps.append(t("The past year of prices: not enough history saved.", "पिछले साल के भाव: पर्याप्त इतिहास सहेजा नहीं।"))

    # ================================================================= the news
    want.add("news")
    tones = [s.value_num for s in pit.signals(ticker, kind="news_tone", limit=30) if s.value_num is not None]
    if len(tones) >= 5:
        ran.add("news")
        avg = sum(tones) / len(tones)
        last_tone = pit.latest(ticker, "news_tone")
        n_age = age_of(last_tone.as_of) if last_tone else None
        if avg > 0.3:
            add(pros, 1, "Recent news has been mostly positive", "हाल की ख़बरें ज़्यादातर सकारात्मक रहीं",
                "Headlines over the past weeks lean positive. News tone changes quickly and is only a rough guide.", "पिछले हफ़्तों की सुर्ख़ियाँ सकारात्मक झुकाव की हैं। ख़बरों का रुख़ जल्दी बदलता है और यह सिर्फ़ मोटा संकेत है।", ("news",), n_age, len(tones), "readings")
        elif avg < -0.3:
            add(cons, 1, "Recent news has been mostly negative", "हाल की ख़बरें ज़्यादातर नकारात्मक रहीं",
                "Headlines over the past weeks lean negative. News tone changes quickly and is only a rough guide.", "पिछले हफ़्तों की सुर्ख़ियाँ नकारात्मक झुकाव की हैं। ख़बरों का रुख़ जल्दी बदलता है और यह सिर्फ़ मोटा संकेत है।", ("news",), n_age, len(tones), "readings")
    else:
        gaps.append(t("Recent news tone: too few headlines saved.", "हाल की ख़बरों का रुख़: बहुत कम सुर्ख़ियाँ सहेजी हैं।"))

    gaps.append(t("Not covered here: future earnings forecasts, management quality, and anything that happened after the data was saved.",
                  "यहाँ शामिल नहीं: आगे की कमाई के अनुमान, प्रबंधन की गुणवत्ता, और डेटा सहेजे जाने के बाद की कोई भी बात।"))

    # ================================================================= how it sits with what the person already owns
    for_you: list[str] = []
    if holding:
        w, sw, lim = holding.get("weight", 0.0), holding.get("sector_weight", 0.0), holding.get("sector_limit")
        for_you.append(t(f"You already own it: {w * 100:.1f}% of your money. " if w else "You do not own it today. ",
                         f"आपके पास यह पहले से है: आपके पैसे का {w * 100:.1f}%। " if w else "आज आपके पास यह नहीं है। ") +
                       t(f"{sec_label} is {sw * 100:.1f}% of your money" + (f", against your own {lim * 100:.0f}% limit." if lim else "."),
                         f"{sec_label} आपके पैसे का {sw * 100:.1f}% है" + (f", जबकि आपकी अपनी सीमा {lim * 100:.0f}% है।" if lim else "।")))
        if lim and sw >= lim:
            for_you.append(t("Adding more would push that sector further past your own limit.", "और जोड़ने पर वह सेक्टर आपकी अपनी सीमा से और ऊपर चला जाएगा।"))

    # ================================================================= how old is each kind of data
    def fresh(label_en, label_hi, when):
        return {"label": t(label_en, label_hi), "date": _utc(when).date().isoformat() if when else None, "age_days": age_of(when)}
    last_price = rows[-1]["date"] if rows else None
    stm = [s.as_of for k in ("rev_growth", "ocf_to_ni", "earn_growth") for s in [pit.latest(ticker, k)] if s is not None]
    doc = pit.news(ticker, limit=1)
    news_when = doc[0]["published_at"] if doc else None
    freshness = [fresh("Prices", "भाव", last_price), fresh("Company numbers", "कंपनी के आँकड़े", mcap_when),
                 fresh("Financial statements", "बही-खाते", max(stm, key=_utc) if stm else None),
                 fresh("Ownership", "स्वामित्व", ins_w), fresh("Headlines", "सुर्ख़ियाँ", news_when)]

    pros.sort(key=lambda x: -x["w"])
    cons.sort(key=lambda x: -x["w"])
    about = t(f"{name} is in the {sec_label} sector" + (f", with a market value of about {_money(mcap, cur)}." if mcap else "."),
              f"{name} {sec_label} सेक्टर की कंपनी है" + (f", जिसका बाज़ार मूल्य लगभग {_money(mcap, cur)} है।" if mcap else "।"))

    def tag(k: str) -> str:
        low = k.lower()
        if "news" in low:
            return t("News", "ख़बरें")
        if any(w in low for w in ("price has", "big fall", "swings", "fairly steady", "averages", "run up", "dropped", "lagged", "done better", "trading lately", "lowest", "highest")):
            return t("Price and trend", "भाव और रुझान")
        if any(w in low for w in ("promoter", "founders", "controlling owner", "funds own", "big funds")):
            return t("Who owns it", "मालिक कौन")
        if any(w in low for w in ("large", "smaller")):
            return t("Size", "आकार")
        if any(w in low for w in ("own usual", "pay little", "pay a lot")):
            return t("Valuation in context", "भाव का संदर्भ")
        if any(w in low for w in ("cash", "debt", "interest", "bills", "distress", "checklist", "dividend", "paying out")):
            return t("Cash and safety", "नक़दी और सुरक्षा")
        if "each rupee of sales" in low:
            return t("The business", "कारोबार")
        if any(w in low for w in ("sales", "profits are", "three years")):
            return t("Growth", "बढ़त")
        return t("The business", "कारोबार")

    price_tag = t("Price and trend", "भाव और रुझान")

    def strip(xs):
        """Price-based readings move together (a falling price is also below its averages and behind its peers), so
        more than three of them would count one fact several times. The strongest three are kept."""
        out, n = [], 0
        for x in xs:
            tg = tag(x["k"])
            if tg == price_tag:
                n += 1
                if n > 3:
                    continue
            if len(out) >= 8:
                break
            out.append({"title": x["title"], "why": x["why"], "tag": tg, "confidence": x["conf"], "basis": x["basis"]})
        return out

    pros_out, cons_out = strip(pros), strip(cons)
    return {"ticker": ticker, "name": name, "about": about, "pros": pros_out, "cons": cons_out, "gaps": gaps, "for_you": for_you, "ranks": ranks,
            "freshness": freshness, "coverage": {"ran": len(ran), "of": len(want)},
            "counts": {"pros": len(pros_out), "cons": len(cons_out)},
            "facts": {"pe": pe, "pe_peers": pe_m, "roe": roe, "roe_peers": roe_m, "margin": mar, "margin_peers": mar_m, "market_cap": mcap, "pb": val(ticker, "pb_ratio"),
                      "year_return": None if ret is None else round(ret * 100, 1), "worst_fall": None if dd is None else round(dd * 100, 1),
                      "volatility": None if vol is None else round(vol * 100, 1)},
            "how_to_read": [t("Good points are things that look healthy in the numbers we hold. Watch-outs are things that could hurt or that you should understand before you decide. A 'light' or 'weak' basis means the point rests on little data or old data: weigh it less.",
                              "अच्छी बातें वे हैं जो हमारे पास के आँकड़ों में स्वस्थ दिखती हैं। ध्यान देने की बातें वे हैं जो नुक़सान कर सकती हैं या जिन्हें फ़ैसले से पहले समझना चाहिए। 'हल्का' या 'कमज़ोर' आधार का मतलब है कि बात कम या पुराने डेटा पर टिकी है: उसे कम तौलिए।"),
                            t("Neither list is a prediction. This page does not say buy, sell or hold: that decision is yours.",
                              "कोई भी सूची भविष्यवाणी नहीं है। यह पेज ख़रीदने, बेचने या रोकने को नहीं कहता: फ़ैसला आपका है।")],
            "lang": lang}
