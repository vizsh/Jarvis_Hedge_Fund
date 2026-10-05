"""Understanding what was actually asked, before any tool is picked.

The older router matched single words ("scam" -> the scam answer, "fee" -> the fee answer), so a question ABOUT a
feature or a stock got a canned reply about one keyword in it. This layer reads the whole sentence first and
decides what kind of request it is:

  * a question about the app itself ("how do I use the fee slider", "help me understand this feature")
        -> a structured explanation plus a guided tour the page plays on screen
  * a request to analyse or compare companies ("analyse TCS", "compare Reliance and HDFC Bank")
        -> the company's facts, good points and watch-outs, with a price chart
  * a general money question ("SIP or lump sum", "what happens when the market falls")
        -> a checked, hand-written explanation from backend/knowledge.py

Everything else still goes to the calculator tools in backend/assistant.py. A model is only ever used to PICK from a
closed list when the rules are unsure; it never writes an answer or a figure.
"""
from __future__ import annotations

import contextvars
import re
from datetime import datetime, timezone
from typing import Any

from backend import charts, knowledge, tours
from backend.explain import Answer
from core import universe

# the page the person is looking at ("this feature" means this page's tool)
REQ_ROUTE: contextvars.ContextVar[str] = contextvars.ContextVar("req_route", default="")

_I = re.I


def _t(lang: str):
    return (lambda en, hi: hi if lang == "hi" else en)


# =================================================================== feature questions
_HOWTO = re.compile(
    r"\bhow (do|does|can|should|to|would) (i |we |you |one )?[\w\- ]{0,40}?\b(use|work|works|operate|read|understand|start|open|try|run|see|check|set up)\b"
    r"|\bhow (is|are) (the |this |that |a |an )?[\w\- ]{2,40}(used|calculated|worked out|made)\b"
    r"|\b(explain|walk me through|walk through|guide me|take me through|show me (how|around|the|what|a|this)|help me (understand|use|learn|with|get)|teach me|tutorial|demo|give me (a |an )?(tour|overview|walkthrough|demo)|tour of|overview of|step by step|visually)\b"
    r"|\bwhat (does|do|is) (the |this |that |a )?[\w\- ]{2,35}(do|for|feature|tool|page|screen|section|tab)\b"
    r"|\bwhat can (i|you|this)\b.{0,30}\b(do|use|see)\b|\bwhat (are )?(the )?features\b|\bhow does (this|jarvis|the app|the prototype)\b|\bwhere (is|do i find|can i find|can i see)\b"
    r"|\bwhat('?s| is) this\b|\bhelp me understand\b", _I)
_UI_WORD = re.compile(r"\b(assistant|chatbot|chat|feature|features|tool|tools|page|pages|screen|section|tab|slider|button|checker|meter|simulator|panel|desk|coach|scanner|kiosk|prototype|app|application|product|project|platform|demo|tour|walk ?through|menu|orb|mic|toggle|card|chart|graph|dashboard)\b", _I)
_SELF = re.compile(r"\b(this|the current|the open|current|here)\b.{0,12}\b(feature|page|screen|tool|section|tab|part|thing)\b|\bwhat am i (looking at|seeing)\b|\bexplain (this|what i see|what you see)\b|\bhelp me understand (this|it|what)\b$", _I)
_GENERIC_TOURS = {"portfolio", "assistant", "research", "protect", "practice", "govern", "rural", "whatsapp", "learn", "settings", "overview"}
# a personal money question is never a question about the app, however it is worded
_PERSONAL_NUMBERS = re.compile(r"\d")


def tour_for_route(route: str) -> dict[str, Any] | None:
    """The tour for whatever page (and tool) is open."""
    r = (route or "").lstrip("#") or "/"
    path, _, q = r.partition("?")
    tool = dict(p.split("=", 1) for p in q.split("&") if "=" in p).get("tool")
    if tool:
        for t in tours.TOURS:
            if t["route"] == f"{path}?tool={tool}":
                return t
    page = {"/": "overview", "/portfolio": "portfolio", "/protect": "protect", "/rural": "rural", "/whatsapp": "whatsapp", "/learn": "learn",
            "/practice": "practice", "/govern": "govern", "/research": "research", "/assistant": "assistant"}.get(path)
    return tours.BY_ID.get(page or "overview")


def _norm(x: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", x.lower()).strip()


def feature_tour(text: str) -> dict[str, Any] | None:
    """The guided tour a question is asking for, or None when it is not about the app."""
    for t in tours.TOURS:
        if _norm(t["example"]["en"]) == _norm(text):
            return t
    if not _HOWTO.search(text):
        return None
    t = tours.match(text)
    if t is not None:
        if t["id"] in _GENERIC_TOURS and not (_UI_WORD.search(text) or re.search(r"\b(walk me through|guide me|take me through|tour|show me around)\b", text, _I)):
            return None
        return t
    if _SELF.search(text):
        return tour_for_route(REQ_ROUTE.get())
    if re.search(r"\b(this|the) (app|prototype|product|project|platform|demo|system)\b|\b(all|every|each|the)\b.{0,12}\bfeatures?\b|\bwhat can (i|you|this)\b.{0,25}\b(do|use)\b|\bgive me (a |an )?(tour|overview|walkthrough)\b|\bshow me around\b|\bwhat (are )?the features\b", text, _I):
        return tours.BY_ID["overview"]
    return None


def h_feature(t: dict[str, Any], ctx) -> Answer:
    L = ctx.lang
    tt = _t(L)
    lg = "hi" if L == "hi" else "en"
    steps = t["steps"]
    a = Answer(headline=t["what"][lg], bullets=list(t["how"][lg]),
               action=tt("Starting the guided tour now: I will open each part on screen and read it out. Press Esc or Stop any time, and use Next or Back to go at your own pace.",
                         "निर्देशित सैर अभी शुरू कर रहा हूँ: मैं हर हिस्सा स्क्रीन पर खोलकर पढ़ूँगा। कभी भी Esc या रोकिए दबाइए, और अपनी गति से चलने के लिए आगे या पीछे दबाइए।"),
               facts=[{"label": tt("Steps in the tour", "सैर के चरण"), "value": str(len(steps)), "tone": ""},
                      {"label": tt("Opens on", "यहाँ खुलता है"), "value": t["route"].split("?")[0].strip("/").title() or tt("Home", "होम"), "tone": ""}],
               table={"columns": [tt("Step", "चरण"), tt("What you will see", "आप क्या देखेंगे")],
                      "rows": [[f"{i + 1}. {s['title'][lg]}", _first_sentence(s["body"][lg])] for i, s in enumerate(steps)]},
               visual={"page": t["route"].split("?")[0].strip("/") or "", "label": tt("Open this page", "यह पेज खोलिए"), "params": {}})
    a.kind = "feature_help"
    a.lang = L
    a.data = {"intent": "feature_help", "tour": t["id"], "tour_title": t["title"][lg], "routed_by": "understand"}
    a.speech = (t["title"][lg] + ". " + _first_sentence(t["what"][lg]) + " " + tt("Watch the screen: I will walk you through it.", "स्क्रीन देखिए: मैं आपको इसमें घुमाऊँगा।")).strip()
    others = [x for x in tours.TOURS if x["id"] != t["id"] and (x["route"].split("?")[0] == t["route"].split("?")[0] or t["id"] == "overview")][:3]
    a.follow_ups = [x["example"]["en"] for x in others] or [tours.BY_ID["overview"]["example"]["en"]]
    if L == "hi":
        a.follow_ups_hi = [x["example"]["hi"] for x in others] or [tours.BY_ID["overview"]["example"]["hi"]]
    if ctx.convo is not None:
        ctx.convo.remember(a)
    return a


def _first_sentence(s: str) -> str:
    m = re.match(r"(.+?[.।!?])(\s|$)", s)
    return (m.group(1) if m else s).strip()


# =================================================================== stocks
_ANALYSE = re.compile(
    r"\b(analy[sz]\w*|explain|describe|understand|break ?down|what(\'s| is| are)|research|review|study|examine|look (at|into|up)|check( out)?|deep dive|tell me (about|more about)|what (do you think|about|can you tell me)|thoughts on|opinion on|take on|"
    r"how (is|are|'s|has|have|did|was)|how('s| is) [\w .&-]{2,30} (doing|performing|looking)|(is|are) [\w .&-]{2,30} (a )?(good|bad|decent|solid|safe|risky|strong|weak|healthy|overvalued|expensive|cheap)|"
    r"chart|graph|price (history|trend|chart|of)|share price|stock price|trend|performance|fundamentals?|technicals?|financials?|valuation|pros and cons|outlook|snapshot|profile|overview|summary of|about)\b", _I)
_FIT = re.compile(r"\b(tell me|let me know|advise me|help me decide|suggest)\b.{0,30}\b(if|whether)\b.{0,25}\b(buy|invest in|purchase|get|add)\b|\bwhether (to|i should) (buy|add|invest)\b|\b(should|shall|can|could|may|would) (i|we)\b.{0,15}\b(buy|add|get|sell|invest|pick|take|trim|exit|top up|hold|keep)\b|\bis it (ok|okay|safe|worth|wise|fine)\b.{0,15}\b(to )?(buy|add|invest|sell)\b|\bworth (buying|adding|investing)\b", _I)
_EXPLICIT = re.compile(r"\b(analy[sz]\w*|research|deep dive|tell me about|pros and cons|price history)\b", _I)
_CHART_WORDS = re.compile(r"\b(chart|graph|price (history|trend|chart)|candles?|plot|show me the price)\b", _I)
_COMPARE = re.compile(r"\b(compare|comparison|versus|vs\.?|against|better than|or|and)\b", _I)
_COMPARE_STRONG = re.compile(r"\b(compare|comparison|versus|vs\.?|which is better|difference between|better than|head to head)\b|\bwhich (stock |share |company |one )?(is |looks |seems |would be )?(better|safer|cheaper|stronger|riskier|more (risky|stable))\b|\b(better|safer|cheaper|stronger|riskier)\b.{0,12}\b(or)\b", _I)


def _tickers_in(text: str) -> list[str]:
    """Every company named in a sentence, in order of appearance, without repeats."""
    from backend import intents
    low = text.lower()
    found: list[tuple[int, str]] = []
    cands: list[tuple[str, str]] = list(((a, tk) for a, tk in intents.ALIASES.items()))
    for tk in universe.tickers():
        cands.append((universe.name(tk).lower(), tk))
        cands.append((tk.replace(".NS", "").lower(), tk))
    for tk, e in universe.extras().items():
        cands.append((e["name"].lower(), tk))
        cands.append((tk.replace(".NS", "").lower(), tk))
    taken: list[tuple[int, int]] = []
    for label, tk in sorted(cands, key=lambda kv: -len(kv[0])):
        if len(label) < 3:
            continue
        for m in re.finditer(rf"(?<![a-z0-9]){re.escape(label)}(?![a-z0-9])", low):
            if any(s < m.end() and m.start() < e for s, e in taken):
                continue
            taken.append((m.start(), m.end()))
            found.append((m.start(), tk))
    out: list[str] = []
    for _, tk in sorted(found):
        if tk not in out:
            out.append(tk)
    return out


def _today_pit(ctx):
    from core.pit import PointInTimeStore
    return PointInTimeStore(ctx.conn, datetime.now(timezone.utc))


def stock_intent(text: str) -> tuple[str, list[str]] | None:
    """('analysis' | 'compare', tickers) when the sentence asks about companies themselves rather than the portfolio."""
    tk = _tickers_in(text)
    if not tk:
        return None
    if len(tk) >= 2 and _COMPARE_STRONG.search(text) and not _FIT.search(text):
        return "compare", tk[:3]
    if len(tk) >= 2 and _COMPARE.search(text) and _ANALYSE.search(text) and not _FIT.search(text):
        return "compare", tk[:3]
    if _FIT.search(text) and not _CHART_WORDS.search(text) and not _EXPLICIT.search(text):
        return None                                    # "should I add X": the portfolio-fit answer owns this
    if _ANALYSE.search(text) or _CHART_WORDS.search(text):
        return "analysis", tk[:1]
    return None


def _fmt_money(x: float, cur: str) -> str:
    if cur == "₹":
        if x >= 1e12:
            return f"₹{x / 1e12:.1f} lakh crore"
        if x >= 1e7:
            return f"₹{x / 1e7:,.0f} crore"
        return f"₹{x:,.0f}"
    return f"${x / 1e9:,.1f} billion" if x >= 1e9 else f"${x:,.0f}"


def _sig(pit, ticker: str, kind: str) -> float | None:
    s = pit.latest(ticker, kind)
    return s.value_num if s is not None and s.value_num is not None else None


def h_stock(ticker: str, ctx, text: str = "") -> Answer:
    from analysis import proscons
    L = ctx.lang
    tt = _t(L)
    name = universe.name(ticker)
    cur = charts.currency(ticker)
    pit = _today_pit(ctx)
    price = ctx.prices.get(ticker) or pit.last_close(ticker) or 0.0
    holding = None
    try:
        nav = ctx.portfolio.nav(ctx.prices) or 0.0
        if nav:
            holding = {"weight": ctx.portfolio.positions.get(ticker, 0) * price / nav,
                       "sector_weight": ctx.portfolio.sector_value(universe.sector(ticker), ctx.prices, universe.sectors()) / nav,
                       "sector_limit": ctx.policy.limits.max_sector_pct}
    except Exception:  # noqa: BLE001
        holding = None
    pc = proscons.pros_cons(pit, ticker, L, holding)
    ch = charts.price_chart(pit, ticker)
    f = pc["facts"]
    sec = universe.sector_label(universe.sector(ticker))

    parts: list[str] = []
    if ch:
        d = ch["change_pct"]
        parts.append(tt(f"Over the past year its share price {'rose' if d >= 0 else 'fell'} {abs(d):.0f}%, to {cur}{ch['last']:,.2f}.",
                        f"पिछले एक साल में इसका भाव {abs(d):.0f}% {'बढ़ा' if d >= 0 else 'गिरा'}, और अब {cur}{ch['last']:,.2f} है।"))
    if f.get("pe") and f.get("pe_peers"):
        parts.append(tt(f"You pay about {cur}{f['pe']:.0f} for each {cur}1 of yearly profit, against about {cur}{f['pe_peers']:.0f} for similar {sec.lower()} companies.",
                        f"सालाना मुनाफ़े के हर {cur}1 के लिए लगभग {cur}{f['pe']:.0f} देने पड़ते हैं, जबकि समान {sec} कंपनियों में लगभग {cur}{f['pe_peers']:.0f}।"))
    n_p, n_c = len(pc["pros"]), len(pc["cons"])
    if not (pc["pros"] or pc["cons"]):
        head = tt(f"{name}: I do not hold enough data on this company to describe it yet.", f"{name}: इस कंपनी पर अभी इतना डेटा नहीं कि इसका वर्णन कर सकूँ।")
    else:
        head = f"{name}: " + " ".join(parts) if parts else f"{name}: " + tt(f"{n_p} good points and {n_c} things to watch.", f"{n_p} अच्छी बातें और {n_c} ध्यान देने की बातें।")

    facts = []
    if ch:
        facts.append({"label": tt("Price now", "अभी का भाव"), "value": f"{cur}{ch['last']:,.2f}", "tone": ""})
        facts.append({"label": tt("1-year change", "1 साल में बदलाव"), "value": f"{ch['change_pct']:+.0f}%", "tone": "good" if ch["change_pct"] >= 0 else "bad"})
    if f.get("pe"):
        facts.append({"label": tt("Price vs profit (P/E)", "भाव बनाम मुनाफ़ा (P/E)"), "value": f"{f['pe']:.1f}" + (f" · {tt('peers', 'साथी')} {f['pe_peers']:.1f}" if f.get("pe_peers") else ""), "tone": ""})
    if f.get("roe") is not None:
        facts.append({"label": tt("Return on shareholders' money", "शेयरधारकों के पैसे पर कमाई"), "value": f"{f['roe'] * 100:.0f}%", "tone": ""})
    if f.get("market_cap"):
        facts.append({"label": tt("Market value", "बाज़ार मूल्य"), "value": _fmt_money(f["market_cap"], cur), "tone": ""})
    if f.get("worst_fall") is not None:
        facts.append({"label": tt("Worst fall in the year", "साल की सबसे बड़ी गिरावट"), "value": f"{f['worst_fall']:.0f}%", "tone": "warn" if f["worst_fall"] < -20 else ""})

    sections = [{"kind": "good", "title": tt("Good points", "अच्छी बातें"), "items": pc["pros"][:5]},
                {"kind": "watch", "title": tt("Things to watch", "ध्यान देने की बातें"), "items": pc["cons"][:5]}]
    rows = [[r["metric"], r["value"], f"{r['rank']} / {r['of']}"] for r in pc["ranks"]]
    note = [tt("This describes the company from data we hold; it is not a recommendation to buy or sell.",
               "यह हमारे पास के डेटा से कंपनी का वर्णन है; ख़रीदने या बेचने की सलाह नहीं।")]
    if pc["for_you"]:
        note.append(pc["for_you"][0])
    a = Answer(headline=head, bullets=[x["title"] for x in pc["pros"][:2]] + [x["title"] for x in pc["cons"][:2]], action=" ".join(note), facts=facts,
               table={"columns": [tt("Measure", "पैमाना"), tt("This company", "यह कंपनी"), tt("Rank among peers", "साथियों में स्थान")], "rows": rows} if rows else None,
               detail=tt(f"Prices come from Yahoo Finance when this machine is online and from the saved snapshot otherwise (this chart used the {ch['source'] if ch else 'saved'} data). Company numbers come from public statements, compared with {len([t for t in universe.tickers() if universe.sector(t) == universe.sector(ticker)]) - 1} similar companies in the same industry. Each point shows how much data it rests on.",
                         f"भाव इंटरनेट चालू होने पर Yahoo Finance से और नहीं तो सहेजे डेटा से आते हैं। कंपनी के आँकड़े सार्वजनिक बही-खातों से हैं, और एक ही उद्योग की समान कंपनियों से तुलना की गई है। हर बात बताती है कि वह कितने डेटा पर टिकी है।"),
               visual={"page": "research", "label": tt("Open the full research page", "पूरा शोध पेज खोलिए"), "params": {"ticker": ticker}})
    a.kind = "stock_analysis"
    a.lang = L
    a.subject = ticker
    a.data = {"intent": "stock_analysis", "routed_by": "understand", "ticker": ticker, "chart": ch, "sections": sections, "coverage": pc["coverage"],
              "freshness": pc["freshness"], "investigate": f"Investigate {name}"}
    a.speech = head if len(head) < 260 else head[:257] + "…"
    peers = [t for t in universe.tickers() if t != ticker and universe.sector(t) == universe.sector(ticker) and charts.currency(t) == charts.currency(ticker)][:1]
    qs = ([(f"Compare {name} and {universe.name(peers[0])}", f"{name} और {universe.name(peers[0])} की तुलना कीजिए")] if peers else []) + \
         [(f"Should I add {name} to my portfolio?", f"क्या {name} को अपने पोर्टफ़ोलियो में जोड़ना ठीक रहेगा?"),
          ("Show me how the research page works", "शोध पेज कैसे काम करता है दिखाइए")]
    a.follow_ups = [q for q, _ in qs]
    if L == "hi":
        a.follow_ups_hi = [h for _, h in qs]
    if ctx.convo is not None:
        ctx.convo.remember(a)
    return a


def h_compare(tickers: list[str], ctx) -> Answer:
    from analysis import proscons
    L = ctx.lang
    tt = _t(L)
    pit = _today_pit(ctx)
    pcs = {tk: proscons.pros_cons(pit, tk, L) for tk in tickers}
    names = [universe.name(tk) for tk in tickers]
    ch = charts.compare_chart(pit, tickers)

    def v(tk, k):
        return _sig(pit, tk, k)

    def cell(x, fmt):
        return "–" if x is None else fmt.format(x)
    metrics = [
        (tt("Price vs profit (P/E), lower is cheaper", "भाव बनाम मुनाफ़ा (P/E), कम = सस्ता"), lambda tk: pcs[tk]["facts"]["pe"], "{:.1f}", False),
        (tt("Return on shareholders' money", "शेयरधारकों के पैसे पर कमाई"), lambda tk: pcs[tk]["facts"]["roe"], "{:.0%}", True),
        (tt("Profit margin", "मुनाफ़ा मार्जिन"), lambda tk: pcs[tk]["facts"]["margin"], "{:.0%}", True),
        (tt("Sales growth (latest quarter)", "बिक्री की बढ़त (ताज़ा तिमाही)"), lambda tk: v(tk, "rev_growth"), "{:.0%}", True),
        (tt("Debt vs own capital (non-banks), lower is safer", "क़र्ज़ बनाम अपनी पूँजी (बैंक छोड़कर), कम = सुरक्षित"), lambda tk: v(tk, "debt_to_equity") if universe.sector(tk) != "FINANCIALS" else None, "{:.0f}%", False),
        (tt("Price change over the year", "साल में भाव का बदलाव"), lambda tk: (pcs[tk]["facts"]["year_return"] / 100) if pcs[tk]["facts"]["year_return"] is not None else None, "{:+.0%}", True),
        (tt("Worst fall in the year", "साल की सबसे बड़ी गिरावट"), lambda tk: (pcs[tk]["facts"]["worst_fall"] / 100) if pcs[tk]["facts"]["worst_fall"] is not None else None, "{:.0%}", True),
    ]
    rows, leads = [], {tk: [] for tk in tickers}
    for label, get, fmt, higher in metrics:
        vals = {tk: get(tk) for tk in tickers}
        rows.append([label] + [cell(vals[tk], fmt) for tk in tickers])
        have = {tk: x for tk, x in vals.items() if x is not None}
        if len(have) >= 2:
            best = max(have, key=have.get) if higher else min(have, key=have.get)
            spread = abs(max(have.values()) - min(have.values()))
            if spread > 1e-9:
                leads[best].append(label.split(",")[0].split(" (")[0].lower())
    mcaps = {tk: pcs[tk]["facts"]["market_cap"] for tk in tickers}
    rows.append([tt("Market value", "बाज़ार मूल्य")] + [(_fmt_money(mcaps[tk], charts.currency(tk)) if mcaps[tk] else "–") for tk in tickers])
    bullets = []
    for tk, nm in zip(tickers, names):
        if leads[tk]:
            bullets.append(tt(f"{nm} is ahead on: {', '.join(leads[tk][:4])}.", f"{nm} इन में आगे है: {', '.join(leads[tk][:4])}।"))
    bullets.append(tt("Ahead on a measure is not the same as the better company: a lower price can mean a weaker business, and a faster-growing one usually costs more.",
                      "किसी पैमाने पर आगे होना बेहतर कंपनी होना नहीं है: कम भाव कमज़ोर कारोबार भी बता सकता है, और तेज़ बढ़त वाली आम तौर पर महँगी होती है।"))
    sectors = {universe.sector(tk) for tk in tickers}
    if len(sectors) > 1:
        bullets.append(tt("These are in different industries, so measures like P/E and margin are not directly comparable.", "ये अलग उद्योगों में हैं, इसलिए P/E और मार्जिन जैसे पैमाने सीधे तुलनीय नहीं हैं।"))
    head = tt(f"{' vs '.join(names)}: side by side on the same measures, and on one chart with every line starting at 100.",
              f"{' बनाम '.join(names)}: एक ही पैमानों पर आमने-सामने, और एक चार्ट पर जहाँ हर रेखा 100 से शुरू होती है।")
    a = Answer(headline=head, bullets=bullets, action=tt("This compares facts; it does not say which to buy.", "यह तथ्यों की तुलना है; यह नहीं कहती कि कौन सी ख़रीदें।"),
               table={"columns": [tt("Measure", "पैमाना")] + names, "rows": rows},
               detail=tt("Each number is from the company's saved statements and the past year of prices; blank (–) means no figure was saved. Banks are left out of the debt comparison because debt means something different for a lender.",
                         "हर संख्या कंपनी के सहेजे बही-खातों और पिछले साल के भावों से है; ख़ाली (–) का मतलब कोई आँकड़ा सहेजा नहीं। क़र्ज़ की तुलना में बैंक छोड़े गए हैं क्योंकि ऋणदाता के लिए क़र्ज़ का मतलब अलग है।"),
               visual={"page": "research", "label": tt(f"Open {names[0]} in Research", f"शोध में {names[0]} खोलिए"), "params": {"ticker": tickers[0]}})
    a.kind = "stock_compare"
    a.lang = L
    a.data = {"intent": "stock_compare", "routed_by": "understand", "tickers": tickers, "chart": ch}
    a.speech = head
    qs = [(f"Analyse {names[0]}", f"{names[0]} का विश्लेषण कीजिए"), (f"Analyse {names[1]}", f"{names[1]} का विश्लेषण कीजिए")]
    a.follow_ups = [q for q, _ in qs]
    if L == "hi":
        a.follow_ups_hi = [h for _, h in qs]
    if ctx.convo is not None:
        ctx.convo.remember(a)
    return a


def h_unknown_company(phrase: str, ctx) -> Answer:
    from analysis import stocksearch
    tt = _t(ctx.lang)
    try:
        hits = stocksearch.search(phrase, limit=4)
    except Exception:  # noqa: BLE001
        hits = []
    bullets = [f"{h['name']} ({h['symbol']})" + (tt(" · already loaded", " · पहले से लोड") if h.get("covered") else tt(" · can be fetched", " · लाया जा सकता है")) for h in hits[:4]]
    a = Answer(headline=tt(f"I do not have “{phrase}” loaded yet, so I will not guess about it.", f"“{phrase}” अभी लोड नहीं है, इसलिए मैं अंदाज़े से नहीं बताऊँगा।"),
               bullets=bullets or [tt("No close match found in the list of listed companies.", "सूचीबद्ध कंपनियों में कोई क़रीबी मेल नहीं मिला।")],
               action=tt("Open the Research page, search the company there, and it is fetched live with its prices and statements.", "शोध पेज खोलिए, वहाँ कंपनी खोजिए, और उसके भाव और बही-खाते सीधे लाए जाएँगे।"),
               visual={"page": "research", "label": tt("Search on the Research page", "शोध पेज पर खोजिए"), "params": {}})
    a.kind = "stock_unknown"
    a.lang = ctx.lang
    a.data = {"intent": "stock_unknown", "routed_by": "understand"}
    a.follow_ups = ["Analyse TCS", "Compare Infosys and Wipro"]
    if ctx.lang == "hi":
        a.follow_ups_hi = ["TCS का विश्लेषण कीजिए", "Infosys और Wipro की तुलना कीजिए"]
    return a


# =================================================================== concepts
_TFIDF = None


def _index():
    global _TFIDF
    if _TFIDF is None:
        from sklearn.feature_extraction.text import TfidfVectorizer
        docs, ids = [], []
        for c in knowledge.CONCEPTS:
            for q in c["q"]:
                docs.append(q)
                ids.append(c["id"])
        v = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True, stop_words="english")
        X = v.fit_transform(docs)
        _TFIDF = (v, X, ids)
    return _TFIDF


def concept_candidates(text: str) -> list[tuple[str, float]]:
    """Concept ids ranked by fit: keyword patterns first, then similarity to the example questions."""
    kw = dict(knowledge.keyword_hits(text))
    best: dict[str, float] = dict(kw)
    try:
        from sklearn.preprocessing import normalize
        v, X, ids = _index()
        sims = (normalize(X) @ normalize(v.transform([text])).T).toarray().ravel()
        for s, cid in zip(sims, ids):
            if cid not in kw and s > best.get(cid, 0.0):
                best[cid] = float(s)
    except Exception:  # noqa: BLE001
        pass
    return sorted(best.items(), key=lambda kv: -kv[1])


def h_concept(cid: str, ctx, simple: bool = False) -> Answer:
    c = knowledge.BY_ID[cid]
    L = ctx.lang
    lg = "hi" if L == "hi" else "en"
    tt = _t(L)
    tbl = None
    if c["table"]:
        tbl = {"columns": c["table"]["columns"][lg], "rows": c["table"]["rows"][lg]}
    a = Answer(headline=c["head"][lg], bullets=list(c["points"][lg]), action=c["watch"][lg], table=tbl)
    if simple:
        a.bullets, a.table = a.bullets[:2], None
        a.level = "simple"
    if c["example"]:
        a.detail = c["example"][lg]
    a.kind = "concept"
    a.lang = L
    a.data = {"intent": "concept", "concept": cid, "category": c["cat"], "routed_by": "understand"}
    if c["tool"]:
        page, label_en, label_hi, params = c["tool"]
        a.visual = {"page": page, "label": label_hi if L == "hi" else label_en, "params": params}
    if c["tour"]:
        a.data["tour"] = c["tour"]
        a.data["tour_title"] = tours.BY_ID[c["tour"]]["title"][lg]
        a.data["tour_manual"] = True                    # offered as a button, not started by itself
    a.speech = _first_sentence(c["head"][lg])
    a.follow_ups = [q for q, _ in c["follow"]]
    if L == "hi":
        a.follow_ups_hi = [h for _, h in c["follow"]]
    if ctx.convo is not None:
        ctx.convo.remember(a)
    return a


# =================================================================== the decision
_OVERRIDABLE = {"define", "fee_drag", "goal", "emergency", "fund_overlap", "diversification", "correlation", "predict", "stress", "why", "fix", "xray",
                "simplify", "help", "chitchat", "should_buy", "fund_list", "fund_info", "fund_vs_direct", "clarify", "credit_score",
                "policy_check", "moneylender", "digest", "ledger", "hold_sell", "income_plan", "saving_goal", "scheme_check", "entitlements", "docs_ready", "out_of_scope"}
_CALC = {"fee_drag", "goal", "emergency", "fund_overlap", "moneylender", "hold_sell", "saving_goal", "policy_check", "credit_score", "stress", "panic"}
_STRICT_KEEP = {"tip_scan", "scam_recovery", "scam_help", "upi_check", "dbt_trace", "my_funds_add", "my_funds_remove", "my_funds_show", "shg_ledger"}


def _concept_wins(text: str, intent: str, how: str) -> str | None:
    """The concept to answer with, when the question is general knowledge rather than a calculation on the person's own numbers."""
    cands = concept_candidates(text)
    if not cands:
        return None
    cid, score = cands[0]
    kw = dict(knowledge.keyword_hits(text))
    has_num = bool(_PERSONAL_NUMBERS.search(text))
    if intent in _STRICT_KEEP:
        return None
    from backend import assistant
    if assistant.find_funds(text) and intent.startswith(("fund_", "my_funds")):
        return None                                   # named sample funds belong to the fund tools
    if cid in kw and (intent in _OVERRIDABLE or how in ("none", "legacy")) and not (has_num and intent in _CALC):
        return cid
    return None


def override(text: str, intent: str, how: str, ctx) -> Answer | None:
    """Called by the assistant after the older rules have named an intent: returns a better-fitting answer, or None to keep it."""
    # 1. the app itself
    t = feature_tour(text)
    if t is not None and not _PERSONAL_NUMBERS.search(re.sub(r"\b(2020|2022|2023)\b", "", text)):
        return h_feature(t, ctx)
    # 2. companies
    si = stock_intent(text)
    if si is not None:
        kind, tks = si
        return h_compare(tks, ctx) if kind == "compare" else h_stock(tks[0], ctx, text)
    from backend import intents
    if _ANALYSE_TARGET.search(text) and not intents.resolve_ticker(text) and intent in ("clarify", "should_buy", "simplify", "define"):
        phrase = intents.target_phrase(text)
        if phrase and not knowledge.keyword_hits(text):
            return h_unknown_company(phrase, ctx)
    # 2b. a scam the older rules did not name (a job that charges you, a threatening loan app, a fake prize...)
    if intent in ("clarify", "scheme_check", "define", "predict", "simplify", "out_of_scope") and not _HOWTO.search(text):
        from backend import assistant, scams
        sc = scams.pick(text)
        if sc["id"] in ("task_job", "loan_app", "prize", "courier", "sim_utility", "remote_app", "digital_arrest"):
            return assistant.h_scam_help(text, ctx)
    # 3. general knowledge
    cid = _concept_wins(text, intent, how)
    if cid is not None and not (intent == "should_buy" and intents.resolve_ticker(text)):
        return h_concept(cid, ctx, simple=bool(_SIMPLE.search(text)))
    # 4. what moved the person's own portfolio
    if _MOVE.search(text) and intent in ("clarify", "why", "stress", "xray", "simplify", "define"):
        return h_move(text, ctx)
    return None


_SIMPLE = re.compile(r"\blike (i('?m| am) )?(5|five|10|ten|a (child|kid))\b|\beli5\b|\b(in )?(very )?simple (words|terms|language)\b|\bsimply\b", _I)
_MOVE = re.compile(r"\bwhy (did|has|is|was|are|were)\b.{0,15}\b(my )?(portfolio|money|investments?|holdings?|stocks?|shares)\b.{0,20}\b(fall|fell|drop\w*|down|lose|lost|go down|decline\w*|rise|rose|up|gain\w*|change\w*|move\w*)\b|\bwhat (made|caused|drove|is driving)\b.{0,25}\bmy (portfolio|investments?|money|returns?)\b|\bwhere did (my )?(money|gains?|losses?|returns?|profits?)\b.{0,15}\b(come from|go)\b|\bhow (did|has|have) my (portfolio|investments?|stocks?) (do|done|perform\w*|move\w*|fare\w*)\b|\bwhat (hurt|helped|dragged|pulled) my\b", _I)


_ANALYSE_TARGET = re.compile(r"\b(analy[sz]e|research|investigate|study|examine|review|look at|check out|deep dive (on|into))\b", _I)


def wants_card(text: str) -> bool:
    """True when this line should be answered as a card in the chat even though it looks like a command (analyse X)."""
    return stock_intent(text) is not None or feature_tour(text) is not None


# the closed list a model may pick from when every rule was unsure
def concept_menu() -> dict[str, str]:
    return {c["id"]: (c["q"][0] if c["q"] else c["id"]) for c in knowledge.CONCEPTS}


async def llm_concept(text: str) -> tuple[str | None, float]:
    """When no rule fits, let the local model PICK the closest topic from the closed list (or none). It writes nothing."""
    from agents.llm import ANALYST_MODEL, chat_json
    menu = concept_menu()
    schema = {"type": "object", "properties": {"topic": {"type": "string", "enum": [*menu, "none"]}, "confidence": {"type": "number"}}, "required": ["topic", "confidence"]}
    nl = chr(10)
    listing = nl.join(f"- {k}: {v}" for k, v in menu.items())
    prompt = ("A user asked a money question. Pick the ONE topic below that best answers it, or none if no topic really answers it." + nl +
              "Topics (id: a sample question):" + nl + listing + nl + nl + "Question: " + text + nl + "Return the topic id and your confidence from 0 to 1.")
    try:
        out = await chat_json(prompt, schema, model=ANALYST_MODEL, temperature=0.0, max_tokens=40, attempts=1, timeout=8.0)
    except Exception:  # noqa: BLE001
        return None, 0.0
    t = out.get("topic")
    return (t if t in menu else None), float(out.get("confidence") or 0.0)


def similar_concept(text: str, floor: float = 0.45) -> str | None:
    """Last resort once the rules and the intent model have both passed: a close paraphrase of a known question."""
    cands = concept_candidates(text)
    return cands[0][0] if cands and cands[0][1] >= floor else None


def h_move(text: str, ctx) -> Answer:
    """What moved the person's own basket over the last month and quarter, from the same attribution calculator the Portfolio page uses."""
    from analysis import attribution as attrib
    tt = _t(ctx.lang)
    win = "1m" if re.search(r"\b(month|30 days|this month)\b", text, _I) else "3m"
    a = attrib.analyse(ctx.pit, ctx.portfolio, ctx.prices, win)
    d = a.as_dict()
    words = {"1m": tt("the last month", "पिछले महीने"), "3m": tt("the last 3 months", "पिछले 3 महीनों"), "6m": tt("the last 6 months", "पिछले 6 महीनों")}
    cons = sorted(d["contributions"], key=lambda c: c["contribution"])
    hurt, help_ = [c for c in cons if c["contribution"] < 0][:3], [c for c in reversed(cons) if c["contribution"] > 0][:3]
    pr, br = d["portfolio_return"], d["benchmark_return"]
    rel = (pr - br) * 100
    head = tt(f"Over {words[win]} your basket moved {pr * 100:+.1f}%, {abs(rel):.1f} points {'ahead of' if rel >= 0 else 'behind'} the {d['benchmark_label']} ({br * 100:+.1f}%).",
              f"{words[win]} में आपकी टोकरी {pr * 100:+.1f}% चली, यानी {d['benchmark_label']} ({br * 100:+.1f}%) से {abs(rel):.1f} अंक {'आगे' if rel >= 0 else 'पीछे'}।")
    bullets = []
    if hurt:
        bullets.append(tt("Held it back most: ", "सबसे ज़्यादा नुक़सान: ") + ", ".join(f"{c['name']} ({c['ret'] * 100:+.0f}%)" for c in hurt))
    if help_:
        bullets.append(tt("Helped most: ", "सबसे ज़्यादा फ़ायदा: ") + ", ".join(f"{c['name']} ({c['ret'] * 100:+.0f}%)" for c in help_))
    sec = sorted(d["by_sector"], key=lambda s: s["contribution"])
    if sec and sec[0]["contribution"] < 0:
        bullets.append(tt(f"By industry, {sec[0]['sector_label']} cost the most ({sec[0]['contribution'] * 100:+.1f} points of the move).", f"उद्योग के हिसाब से {sec[0]['sector_label']} ने सबसे ज़्यादा नुक़सान किया (चाल में {sec[0]['contribution'] * 100:+.1f} अंक)।"))
    out = Answer(headline=head, bullets=bullets, action=d["caveat"],
                 table={"columns": [tt("Holding", "शेयर"), tt("Weight", "हिस्सा"), tt("Its move", "इसकी चाल"), tt("Effect on you", "आप पर असर")],
                        "rows": [[c["name"], f"{c['weight'] * 100:.1f}%", f"{c['ret'] * 100:+.1f}%", f"{c['contribution'] * 100:+.2f} " + tt("pts", "अंक")] for c in sorted(d["contributions"], key=lambda c: abs(c["contribution"]), reverse=True)[:8]]},
                 visual={"page": "portfolio", "label": tt("Open the Portfolio page", "पोर्टफ़ोलियो पेज खोलिए"), "params": {}})
    out.kind = "portfolio_move"
    out.lang = ctx.lang
    out.data = {"intent": "portfolio_move", "routed_by": "understand", "window": win}
    out.speech = head
    qs = [("What if the market drops 20%?", "बाज़ार 20% गिरे तो क्या होगा?"), ("Am I diversified?", "क्या मेरा पैसा अलग-अलग जगह बँटा है?")]
    out.follow_ups = [q for q, _ in qs]
    if ctx.lang == "hi":
        out.follow_ups_hi = [h for _, h in qs]
    return out
