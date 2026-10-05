"""Plain-language pros and cons for one company: what looks good, what to watch, what we could not check.

No buy or sell signal, no price target, no prediction. Every line is a measured fact about the company, put
next to something it can be judged against (its sector peers, its own past year) and explained in a sentence a
non-expert can follow. Whatever the numbers do not cover is said out loud under "could not check", so a missing
number is never mistaken for a good or a bad one.
"""
from __future__ import annotations

import math
import statistics
from typing import Any

from core import universe


def _t(lang: str):
    return (lambda en, hi: hi if lang == "hi" else en)


def _median(xs: list[float]) -> float | None:
    return statistics.median(xs) if xs else None


def _val(pit, tk: str, kind: str) -> float | None:
    s = pit.latest(tk, kind)
    return s.value_num if s is not None and s.value_num is not None else None


def _money(x: float, cur: str) -> str:
    if cur == "₹":
        if x >= 1e12:
            return f"₹{x / 1e12:.1f} lakh crore"
        if x >= 1e7:
            return f"₹{x / 1e7:,.0f} crore"
        return f"₹{x:,.0f}"
    return f"${x / 1e9:,.1f} billion" if x >= 1e9 else f"${x:,.0f}"


def pros_cons(pit, ticker: str, lang: str = "en", holding: dict[str, float] | None = None) -> dict[str, Any]:
    """`holding` (optional): {"weight": share of the portfolio in this stock, "sector_weight": share in its sector,
    "sector_limit": the person's own cap} so the summary can say how it sits with what they already own."""
    t = _t(lang)
    name, sector = universe.name(ticker), universe.sector(ticker)
    sec_label = universe.sector_label(sector)
    cur = "₹" if ticker.upper().endswith((".NS", ".BO")) else "$"
    pros: list[dict[str, Any]] = []
    cons: list[dict[str, Any]] = []
    gaps: list[str] = []

    def add(bucket, w, title_en, title_hi, why_en, why_hi):
        bucket.append({"w": w, "title": t(title_en, title_hi), "why": t(why_en, why_hi)})

    # ---- the business, against sector peers -------------------------------------------------------
    peers = [x for x in universe.tickers() if x != ticker and universe.sector(x) == sector]

    def vs(kind: str) -> tuple[float | None, float | None]:
        return _val(pit, ticker, kind), _median([v for v in (_val(pit, p, kind) for p in peers) if v is not None])

    pe, pe_m = vs("pe_ratio")
    roe, roe_m = vs("roe")
    mar, mar_m = vs("profit_margin")
    mcap = _val(pit, ticker, "market_cap")
    pb = _val(pit, ticker, "pb_ratio")

    if pe and pe_m:
        if pe < pe_m * 0.9:
            add(pros, 3, "Priced lower than similar companies", "समान कंपनियों से सस्ते भाव पर",
                f"You pay about ₹{pe:.0f} for each ₹1 of yearly profit. Similar {sec_label.lower()} companies are about ₹{pe_m:.0f}. Cheaper is not automatically better, but you pay less for the same profit.",
                f"हर ₹1 के सालाना मुनाफ़े के लिए लगभग ₹{pe:.0f} देने पड़ते हैं। {sec_label} की समान कंपनियों में यह लगभग ₹{pe_m:.0f} है। सस्ता होना अपने आप बेहतर नहीं, पर उतने ही मुनाफ़े के लिए कम देना पड़ता है।")
        elif pe > pe_m * 1.15:
            add(cons, 3, "Priced higher than similar companies", "समान कंपनियों से महँगे भाव पर",
                f"You pay about ₹{pe:.0f} for each ₹1 of yearly profit, against about ₹{pe_m:.0f} for similar companies. The market expects more from it, so there is less room for disappointment.",
                f"हर ₹1 के सालाना मुनाफ़े के लिए लगभग ₹{pe:.0f} देने पड़ते हैं, जबकि समान कंपनियों में लगभग ₹{pe_m:.0f}। बाज़ार को इससे ज़्यादा उम्मीद है, इसलिए निराशा की गुंजाइश कम है।")
    elif pe is None:
        gaps.append(t("Its price compared with its profit (P/E): no figure saved.", "भाव बनाम मुनाफ़ा (P/E): कोई आँकड़ा सहेजा नहीं।"))

    if roe is not None:
        if roe >= 0.15 or (roe_m and roe > roe_m * 1.1):
            add(pros, 3, "Earns a good return on shareholders' money", "शेयरधारकों के पैसे पर अच्छी कमाई",
                f"It earns about {roe * 100:.0f} paise a year on every ₹1 shareholders have put in" + (f" (similar companies: about {roe_m * 100:.0f})." if roe_m else "."),
                f"शेयरधारकों के हर ₹1 पर यह साल में लगभग {roe * 100:.0f} पैसे कमाती है" + (f" (समान कंपनियाँ: लगभग {roe_m * 100:.0f})।" if roe_m else "।"))
        elif roe < 0.10 or (roe_m and roe < roe_m * 0.8):
            add(cons, 3, "Earns a modest return on shareholders' money", "शेयरधारकों के पैसे पर कमाई कम",
                f"It earns about {roe * 100:.0f} paise a year on every ₹1 shareholders have put in" + (f", below similar companies (about {roe_m * 100:.0f})." if roe_m else "."),
                f"शेयरधारकों के हर ₹1 पर यह साल में लगभग {roe * 100:.0f} पैसे कमाती है" + (f", जो समान कंपनियों (लगभग {roe_m * 100:.0f}) से कम है।" if roe_m else "।"))
    else:
        gaps.append(t("Return on shareholders' money (ROE): no figure saved.", "शेयरधारकों के पैसे पर कमाई (ROE): कोई आँकड़ा सहेजा नहीं।"))

    if mar is not None:
        if mar_m and mar > mar_m * 1.1:
            add(pros, 2, "Keeps more profit from each rupee of sales", "बिक्री के हर रुपये में से ज़्यादा मुनाफ़ा",
                f"About {mar * 100:.0f} paise of every ₹1 of sales is left as profit; similar companies keep about {mar_m * 100:.0f}.",
                f"बिक्री के हर ₹1 में से लगभग {mar * 100:.0f} पैसे मुनाफ़ा बचता है; समान कंपनियों में लगभग {mar_m * 100:.0f}।")
        elif mar_m and mar < mar_m * 0.8:
            add(cons, 2, "Keeps less profit from each rupee of sales", "बिक्री के हर रुपये में से कम मुनाफ़ा",
                f"About {mar * 100:.0f} paise of every ₹1 of sales is left as profit; similar companies keep about {mar_m * 100:.0f}.",
                f"बिक्री के हर ₹1 में से लगभग {mar * 100:.0f} पैसे मुनाफ़ा बचता है; समान कंपनियों में लगभग {mar_m * 100:.0f}।")
    else:
        gaps.append(t("Profit margin: no figure saved.", "मुनाफ़ा मार्जिन: कोई आँकड़ा सहेजा नहीं।"))

    if mcap:
        if (cur == "₹" and mcap >= 1e12) or (cur == "$" and mcap >= 1e11):
            add(pros, 1, "A very large, well-established company", "बहुत बड़ी, जमी हुई कंपनी",
                f"Its market value is about {_money(mcap, cur)}. Very large companies tend to swing less than small ones, though they can still fall.",
                f"इसका बाज़ार मूल्य लगभग {_money(mcap, cur)} है। बहुत बड़ी कंपनियाँ आम तौर पर छोटी से कम झूलती हैं, पर गिर वे भी सकती हैं।")
        elif (cur == "₹" and mcap < 2e11) or (cur == "$" and mcap < 2e9):
            add(cons, 1, "A smaller company", "अपेक्षाकृत छोटी कंपनी",
                f"Its market value is about {_money(mcap, cur)}. Smaller companies usually have bigger price swings and are harder to sell in a hurry.",
                f"इसका बाज़ार मूल्य लगभग {_money(mcap, cur)} है। छोटी कंपनियों में भाव ज़्यादा झूलता है और जल्दी बेचना कठिन हो सकता है।")

    # ---- how the price itself has behaved --------------------------------------------------------
    px = [r["close"] for r in pit.prices(ticker, 250) if r.get("close")]
    ret = dd = vol = off_high = None
    if len(px) >= 60:
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
        if ret > 0.10:
            add(pros, 2, "The price has risen over the past year", "पिछले साल भाव बढ़ा है",
                f"The share price is up about {ret * 100:.0f}% over {span}. A past rise says nothing about what comes next.",
                f"{span} में शेयर का भाव लगभग {ret * 100:.0f}% बढ़ा है। पिछली बढ़त से आगे का कुछ पता नहीं चलता।")
        elif ret < -0.10:
            add(cons, 2, "The price has fallen over the past year", "पिछले साल भाव गिरा है",
                f"The share price is down about {abs(ret) * 100:.0f}% over {span}. It may be cheaper now, or the market may see a problem: the numbers alone do not say which.",
                f"{span} में शेयर का भाव लगभग {abs(ret) * 100:.0f}% गिरा है। हो सकता है अब सस्ता हो, या बाज़ार को कोई दिक़्क़त दिख रही हो: सिर्फ़ आँकड़ों से पता नहीं चलता।")
        if dd < -0.25:
            add(cons, 2, "It has had a big fall from its peak", "अपने ऊँचे भाव से बड़ी गिरावट आई है",
                f"At its worst point in this period the price was {abs(dd) * 100:.0f}% below its earlier high. If you own it, expect rough patches.",
                f"इस अवधि में सबसे बुरे समय भाव अपने पिछले ऊँचे भाव से {abs(dd) * 100:.0f}% नीचे था। रखेंगे तो उतार-चढ़ाव के दौर झेलने पड़ सकते हैं।")
        elif dd > -0.12:
            add(pros, 1, "Its price has been fairly steady", "इसका भाव काफ़ी स्थिर रहा है",
                f"Even at its worst point the price was only {abs(dd) * 100:.0f}% below its earlier high.", f"सबसे बुरे समय भी भाव अपने पिछले ऊँचे भाव से सिर्फ़ {abs(dd) * 100:.0f}% नीचे था।")
        if vol is not None and vol > 0.35:
            add(cons, 1, "The price swings a lot", "भाव बहुत झूलता है",
                f"Day to day the price moves a lot (about {vol * 100:.0f}% a year on a standard measure). That is harder to sit through.",
                f"दिन-ब-दिन भाव काफ़ी हिलता है (एक मानक पैमाने पर साल का लगभग {vol * 100:.0f}%)। इसे झेलना कठिन हो सकता है।")
    else:
        gaps.append(t("The past year of prices: not enough history saved.", "पिछले साल के भाव: पर्याप्त इतिहास सहेजा नहीं।"))

    # ---- the news ---------------------------------------------------------------------------------
    tones = [s.value_num for s in pit.signals(ticker, kind="news_tone", limit=30) if s.value_num is not None]
    if len(tones) >= 5:
        avg = sum(tones) / len(tones)
        if avg > 0.3:
            add(pros, 1, "Recent news has been mostly positive", "हाल की ख़बरें ज़्यादातर सकारात्मक रहीं",
                "Headlines over the past weeks lean positive. News tone changes quickly and is only a rough guide.", "पिछले हफ़्तों की सुर्ख़ियाँ सकारात्मक झुकाव की हैं। ख़बरों का रुख़ जल्दी बदलता है और यह सिर्फ़ मोटा संकेत है।")
        elif avg < -0.3:
            add(cons, 1, "Recent news has been mostly negative", "हाल की ख़बरें ज़्यादातर नकारात्मक रहीं",
                "Headlines over the past weeks lean negative. News tone changes quickly and is only a rough guide.", "पिछले हफ़्तों की सुर्ख़ियाँ नकारात्मक झुकाव की हैं। ख़बरों का रुख़ जल्दी बदलता है और यह सिर्फ़ मोटा संकेत है।")
    else:
        gaps.append(t("Recent news tone: too few headlines saved.", "हाल की ख़बरों का रुख़: बहुत कम सुर्ख़ियाँ सहेजी हैं।"))

    gaps.append(t("Not covered here: future earnings, debt levels, the quality of management, and anything that happened after the data was saved.",
                  "यहाँ शामिल नहीं: आगे की कमाई, क़र्ज़ का स्तर, प्रबंधन की गुणवत्ता, और डेटा सहेजे जाने के बाद की कोई भी बात।"))

    # ---- how it sits with what the person already owns --------------------------------------------
    for_you: list[str] = []
    if holding:
        w, sw, lim = holding.get("weight", 0.0), holding.get("sector_weight", 0.0), holding.get("sector_limit")
        for_you.append(t(f"You already own it: {w * 100:.1f}% of your money. " if w else "You do not hold it today. ",
                         f"आपके पास यह पहले से है: आपके पैसे का {w * 100:.1f}%। " if w else "आज आपके पास यह नहीं है। ") +
                       t(f"{sec_label} is {sw * 100:.1f}% of your money" + (f", against your own {lim * 100:.0f}% limit." if lim else "."),
                         f"{sec_label} आपके पैसे का {sw * 100:.1f}% है" + (f", जबकि आपकी अपनी सीमा {lim * 100:.0f}% है।" if lim else "।")))
        if lim and sw >= lim:
            for_you.append(t("Adding more would push that sector further past your own limit.", "और जोड़ने पर वह सेक्टर आपकी अपनी सीमा से और ऊपर चला जाएगा।"))

    pros.sort(key=lambda x: -x["w"])
    cons.sort(key=lambda x: -x["w"])
    about = t(f"{name} is in the {sec_label} sector" + (f", with a market value of about {_money(mcap, cur)}." if mcap else "."),
              f"{name} {sec_label} सेक्टर की कंपनी है" + (f", जिसका बाज़ार मूल्य लगभग {_money(mcap, cur)} है।" if mcap else "।"))
    strip = lambda xs: [{"title": x["title"], "why": x["why"]} for x in xs]      # noqa: E731
    return {"ticker": ticker, "name": name, "about": about, "pros": strip(pros), "cons": strip(cons), "gaps": gaps, "for_you": for_you,
            "counts": {"pros": len(pros), "cons": len(cons)},
            "facts": {"pe": pe, "pe_peers": pe_m, "roe": roe, "roe_peers": roe_m, "margin": mar, "margin_peers": mar_m, "market_cap": mcap, "pb": pb,
                      "year_return": None if ret is None else round(ret * 100, 1), "worst_fall": None if dd is None else round(dd * 100, 1),
                      "volatility": None if vol is None else round(vol * 100, 1)},
            "how_to_read": [t("Good points are things that look healthy in the numbers we hold. Watch-outs are things that could hurt or that you should understand before you decide.",
                              "अच्छी बातें वे हैं जो हमारे पास के आँकड़ों में स्वस्थ दिखती हैं। ध्यान देने की बातें वे हैं जो नुक़सान कर सकती हैं या जिन्हें फ़ैसले से पहले समझना चाहिए।"),
                            t("Neither list is a prediction. This page does not say buy, sell or hold: that decision is yours.",
                              "कोई भी सूची भविष्यवाणी नहीं है। यह पेज ख़रीदने, बेचने या रोकने को नहीं कहता: फ़ैसला आपका है।")],
            "lang": lang}
