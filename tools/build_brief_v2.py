"""Builds JARVIS_Product_Brief_v2.docx: the revised product brief, with real competitor comparisons, a deeper technical section,
the WhatsApp companion build, the audience-led scope, and the current screens.

Run: python -m tools.brief_v2_figures   (diagrams)
     python -m tools.build_brief_v2     (document)
"""
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "docx_assets" / "brief_v2"
GOLD, INK, MUTE = RGBColor(0xB8, 0x76, 0x0A), RGBColor(0x1D, 0x1B, 0x16), RGBColor(0x6B, 0x67, 0x5C)
CONTENT_W = 16.6

d = Document()
sec = d.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.2)
sec.top_margin, sec.bottom_margin = Cm(2.0), Cm(2.0)

st = d.styles["Normal"]
st.font.name, st.font.size = "Calibri", Pt(10.5)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
st.paragraph_format.space_after, st.paragraph_format.line_spacing = Pt(6), 1.15
for name, size, col in (("Heading 1", 19, GOLD), ("Heading 2", 13.5, INK), ("Heading 3", 11.5, GOLD)):
    h = d.styles[name]
    h.font.name, h.font.size, h.font.bold, h.font.color.rgb = "Cambria", Pt(size), True, col
    h.element.rPr.rFonts.set(qn("w:eastAsia"), "Cambria")
    h.paragraph_format.space_before = Pt(16 if name == "Heading 1" else 10)
    h.paragraph_format.space_after, h.paragraph_format.keep_with_next = Pt(6), True


def shade(cell, hexcol):
    tcPr = cell._tc.get_or_add_tcPr()
    s = OxmlElement("w:shd"); s.set(qn("w:val"), "clear"); s.set(qn("w:color"), "auto"); s.set(qn("w:fill"), hexcol); tcPr.append(s)


def borders(table, color="D8D0BC"):
    pr = table._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{e}"); el.set(qn("w:val"), "single"); el.set(qn("w:sz"), "4"); el.set(qn("w:color"), color); b.append(el)
    pr.append(b)


def cell_margins(table, top=50, bottom=50, left=80, right=80):
    pr = table._tbl.tblPr
    m = OxmlElement("w:tblCellMar")
    for k, v in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        el = OxmlElement(f"w:{k}"); el.set(qn("w:w"), str(v)); el.set(qn("w:type"), "dxa"); m.append(el)
    pr.append(m)


def fixed_layout(table):
    pr = table._tbl.tblPr
    lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); pr.append(lay)


def P(text="", bold=False, italic=False, size=None, color=None, align=None, after=None):
    p = d.add_paragraph()
    if text:
        r = p.add_run(text); r.bold, r.italic = bold, italic
        if size: r.font.size = Pt(size)
        if color: r.font.color.rgb = color
    if align is not None: p.alignment = align
    if after is not None: p.paragraph_format.space_after = Pt(after)
    return p


def rich(text, style=None):
    p = d.add_paragraph(style=style)
    for i, seg in enumerate(text.split("**")):
        if seg:
            r = p.add_run(seg); r.bold = i % 2 == 1
    return p


def H(t, l=1):
    h = d.add_heading(t, level=l)
    if l == 1 and not t.startswith(("Contents", "1. ")):
        h.paragraph_format.page_break_before = True
    return h


def B(items):
    for t in items:
        p = rich(t, "List Bullet"); p.paragraph_format.space_after = Pt(3)


def T(rows, widths, head=True, size=8.8, zebra=True):
    assert abs(sum(widths) - CONTENT_W) < 0.2, sum(widths)
    t = d.add_table(rows=len(rows), cols=len(rows[0]))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    fixed_layout(t); borders(t); cell_margins(t)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j); c.width = Cm(widths[j])
            p = c.paragraphs[0]; p.paragraph_format.space_after = Pt(0); p.paragraph_format.line_spacing = 1.05
            for k, seg in enumerate(str(val).split("**")):
                if seg:
                    r = p.add_run(seg); r.font.size = Pt(size); r.bold = (head and i == 0) or k % 2 == 1
                    if head and i == 0: r.font.color.rgb = RGBColor(255, 255, 255)
            if head and i == 0: shade(c, "2A2C31")
            elif zebra and i % 2 == 0: shade(c, "FAF6EA")
    if head:
        trPr = t.rows[0]._tr.get_or_add_trPr(); h = OxmlElement("w:tblHeader"); h.set(qn("w:val"), "true"); trPr.append(h)
    d.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def callout(title, text, fill="FFF4D8", edge="E0C47A"):
    t = d.add_table(rows=1, cols=1); t.alignment = WD_TABLE_ALIGNMENT.CENTER; borders(t, edge); fixed_layout(t); cell_margins(t, 110, 110, 150, 150)
    c = t.cell(0, 0); shade(c, fill); c.width = Cm(CONTENT_W)
    p = c.paragraphs[0]; p.paragraph_format.space_after = Pt(0)
    r = p.add_run(title + "  "); r.bold = True; r.font.color.rgb = GOLD
    for i, seg in enumerate(text.split("**")):
        if seg:
            r = p.add_run(seg); r.bold = i % 2 == 1
    d.add_paragraph().paragraph_format.space_after = Pt(2)


_fig = [0]


def F(name, caption, w=15.5):
    import re
    _fig[0] += 1
    p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True; p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(str(FIG / name), width=Cm(w))
    P(f"Figure {_fig[0]}. " + re.sub(r"^Figure\s*\d*\.?\s*", "", caption), italic=True, size=8.6, color=MUTE, align=WD_ALIGN_PARAGRAPH.CENTER, after=10)


def pagebreak():
    d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# footer with page numbers
fp = sec.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = fp.add_run("Jarvis, money plainly  |  Product brief v2  |  page "); r.font.size = Pt(8.2); r.font.color.rgb = MUTE
for tag, txt in (("begin", None), (None, "PAGE"), ("end", None)):
    rr = fp.add_run(); rr.font.size = Pt(8.2)
    if tag:
        e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), tag); rr._r.append(e)
    else:
        e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = txt; rr._r.append(e)

# ============================================================================================ cover
for _ in range(4): P()
P("JARVIS", bold=True, size=44, color=GOLD, after=0)
P("money, plainly", italic=True, size=22, color=INK, after=16)
P("A free, local, bilingual money guide and scam shield, built around the people who need it most and organised so each audience gets only what it needs.", size=13, color=MUTE, after=28)
T([["What it is", "A guard, guide and calculator for everyday money: scam protection, loan costs, government benefits, investing explained, company research, and an honest record of decisions."],
   ["Who it is for", "Five starting baskets: banks and co-operative banks, farmers and rural families, self-help groups and NGOs, middle-class retail investors, and a full prototype for pitching."],
   ["What changed", "The problem direction is now audience-led scope. The companion WhatsApp build, the tip panel, the setup and the competitor comparison are new in this version."],
   ["Status of this brief", "Describes the prototype as it is in the repository today, plus one separate build (the companion WhatsApp assistant) that lives on another device."]],
  [3.4, 13.2], head=False, size=9.6)
pagebreak()

# ============================================================================================ contents
H("Contents")
T([["1", "The idea in one page"], ["2", "The problem, and the change of direction"], ["3", "The problem in numbers"],
   ["4", "Who it is for: five baskets and the full prototype"], ["5", "The ten features and their use cases"], ["6", "How it works, step by step"],
   ["7", "Technology in depth"], ["8", "Competitors and how we compare, feature by feature"], ["9", "Business: who pays, why, and how we reach them"],
   ["10", "Risks, compliance and ethics"], ["A", "Demo script, questions reviewers ask, glossary and sources"]], [1.4, 15.2], head=False, size=10)

# ============================================================================================ 1
H("1. The idea in one page")
callout("Main idea", "**Give people who have never had a trustworthy money adviser a free guard against scams and a plain explanation of what things really cost, in their own language. Then offer the same engine, in the right form, to banks, co-operatives, groups and investors who need it for their own customers.**")
H("Abstract", 2)
rich("Most Indian households decide money matters alone: a farmer weighs a moneylender's '5 rupees per hundred' with no way to convert it, a pensioner waits for a payment with no one to trace it, a first-time investor follows a tip group, a family is rushed by a fake police call. The cost is large and mostly invisible: credit at 60% a year quoted as a small monthly figure, savings lost in minutes, benefits never claimed, fees that take a third of twenty years of growth.")
rich("JARVIS answers those questions plainly. A person types or speaks a question in Hindi or English. The product reads the whole sentence, chooses the right tool or checked explanation, and shows the answer with its working: the yearly figure, the rupees, the steps, and how much each point can be trusted. The numbers come from code and dated public data, never from a language model. Nothing says buy, sell or hold.")
rich("The product is one codebase with ten features. A short setup asks who the prototype is for and starts from one of five baskets, so a bank sees the customer protection and compliance tools, a farmer sees the rural tools and scam protection, and an investor sees the portfolio and research tools. Anyone can add or remove features at any time. Rural and self-help features are always free.")
H("The three promises", 2)
T([["Promise", "What it means in practice"],
   ["Protect", "Spot a scam, a predatory loan or a missed benefit before it costs money; and say exactly what to do in the first hour if it already has."],
   ["Explain", "Answer the question that was asked, in plain words, with the arithmetic shown, in the person's language, by text or voice."],
   ["Stay honest", "Local and private by design; no invented figures; every decision recorded so it cannot be quietly changed."]], [3.2, 13.4])

# ============================================================================================ 2
H("2. The problem, and the change of direction")
H("The problem statement in plain terms", 2)
rich("People in India, especially rural households, low-income families and first-time savers, lose money they can least afford to lose because they do not have clear, trusted, affordable information about money at the moment they decide. The three losses that happen most are fraud, expensive credit that is not understood, and investing without support. The product's job is to make those losses visible and preventable without charging the people who suffer them.")
callout("Note on the direction", "**What changed.** An earlier version of this brief organised the work around a broad weighting of users. That weighting was only an illustration of how to think about segments and is removed. The direction now is **audience-led scope**: each audience gets the features that solve its own problem, the full prototype shows all of them together for a funder or partner, and the rural and self-help features stay free for the people the problem is about.", fill="E9F3EC", edge="9CC7AE")
H("Why the scope had to change", 2)
B(["One product with ten features is hard to explain to a bank, a farmer and an investor at the same time. Each hears about the features that are not for them.",
   "Each audience pays for different things. A bank pays to protect its customers; an investor pays for analysis; a rural household should not pay at all.",
   "Each audience uses the product differently. A farmer uses voice or WhatsApp on a basic phone; a bank's team uses a web dashboard and a compliance record; an investor reads a research summary on a laptop."])

# ============================================================================================ 3
H("3. The problem in numbers")
rich("The figures below are the ones used to justify the work. Each has a source; the notes say where a figure is an older summary that should be checked before it is quoted.")
T([["Problem", "Number", "What it means here", "Source"],
   ["Low financial literacy", "27% of adults; 24% rural; over 80% of women not literate on basic questions (2019)", "Most people decide alone, so plain explanation is the unmet need", "NCFE Financial Literacy and Inclusion Survey 2019"],
   ["Cyber and financial fraud", "About ₹22,845 crore lost in 2024, up 206% from ₹7,465 crore; about 19 lakh complaints on the national portal", "Scams are the largest direct loss that can be prevented in advance", "I4C figures as reported in a 2025 industry summary; quote the official release"],
   ["Money recovered when reported quickly", "About ₹5,489 crore saved across 17.8 lakh complaints in 2024 through the 1930 system", "The first hour decides recovery", "Same reporting as above"],
   ["Informal credit at high rates", "Typical informal rates of 24–40% a year, up to about 150%; formal bank loans typically 6–20%", "A monthly quote hides a yearly cost of 60% or more", "NSS-based summaries and a SIDBI study on informal lending (2019); older figures, verify before quoting"],
   ["Few households invest", "About 9.5% of households participate; rural about 6%, urban about 15%", "Many want to start but lack support and trust", "SEBI Investor Survey 2025 (verify on sebi.gov.in)"],
   ["Hidden fees", "A 2% yearly fee takes about a third of 20 years of growth in the app's own example", "Small percentages compound into large losses", "Arithmetic in the product; not a survey"]],
  [3.2, 4.9, 4.4, 4.1], size=8.2)
P("Sources: NCFE (ncfe.org.in), I4C and 1930 reporting (summarised by an industry report), SIDBI study on informal sector lending (sidbi.in), SEBI Investor Survey 2025 (sebi.gov.in). Verify the original releases before a public quote.", italic=True, size=8.4, color=MUTE)

# ============================================================================================ 4
H("4. Who it is for: five baskets and the full prototype")
rich("The setup screen (`#/setup`) asks who the prototype is for and starts from one basket. The person can then switch features on or off. Every feature works the same in every basket; a basket decides only what the menu shows by default. A feature outside the basket opens a page explaining it, with one tap to add it.")
F("setup_flow.png", "The setup in four steps. Nothing is charged; the price is a demo estimate for the pitch.", 15.2)
F("shot_setup.jpg", "The current setup screen: a numbered form, switch rows, and a live menu preview with the demo price.", 13.4)
T([["Basket", "Who it is for", "What it starts with", "Demo price", "Why it exists"],
   ["**Full prototype (for pitching)**", "Funders, partners, judges", "All ten features", "Free in the demo", "One place to show every feature"],
   ["**Banks and co-operative banks**", "Bank teams protecting customers", "Assistant, rural tools, WhatsApp and SMS, scam protection, learn, govern and audit", "₹499 per month", "Fewer fraud losses, credit-cost explanations, customer outreach, compliance record"],
   ["**Farmers and rural families**", "Households on a basic phone", "Assistant, rural tools, WhatsApp and SMS, scam protection, learn", "Free", "Moneylender cost, schemes, papers, harvest plan, scam safety"],
   ["**Self-help groups and NGOs**", "Women's groups, field staff", "Assistant, rural tools, WhatsApp and SMS, scam protection, learn", "Free", "Group ledger, meeting reports, saving plans, shared-device use"],
   ["**Middle-class retail investors**", "Salaried savers and investors", "Assistant, portfolio X-ray, research desk, practice tools, scam protection, learn", "₹597 per month", "Portfolio health, overlap and fees, company research, tax timing"]],
  [3.5, 3.1, 4.5, 2.4, 3.1], size=8.0)
F("basket_matrix.png", "Which features each basket includes, and the demo price. Rural and self-help baskets carry no charge.", 13.8)
F("prices.png", "Demo monthly price of each basket. Dummy prices for the pitch; no payment is taken in the prototype.", 13.2)

# ============================================================================================ 5
H("5. The ten features and their use cases")
rich("Home is always on. The other nine are below, with the basket that most needs each one and the use case it serves.")
T([["Feature", "Use case", "Who needs it", "Tier"],
   ["**Assistant** (`#/assistant`)", "Ask anything in words or voice; answers come as cards with figures, charts, steps and follow-ups; guided tours of any feature", "Everyone", "Free"],
   ["**Rural tools** (`#/rural`)", "Moneylender cost in a yearly rate; credit-score guide; is this offer real; UPI safety; policy check; schemes; papers; why no money; plan my year; sell or hold; daily saving; group ledger", "Farmers, daily-wage families, self-help groups, banks' rural teams", "Free"],
   ["**WhatsApp and SMS** (`#/whatsapp`)", "The same answers in a phone chat: numbered menu, one question at a time, voice notes, Hindi; a simulator in the app", "Basic-phone users, field staff", "Free"],
   ["**Scam protection** (`#/protect`)", "Nine scam scripts; the tip checker with eight specialists; the recovery coach for the first hour; tax shield; panic-sell replay; standing rules", "Everyone; families of older people; banks", "Free"],
   ["**Learn** (`#/learn`)", "Plain explanations on 32 topics; a goal range from the portfolio's own history; drill-downs that show where each number comes from; glossary", "First-time savers and investors", "Free"],
   ["**Portfolio X-ray** (`#/portfolio`)", "Health grade; spread; allocation map; what-to-do list; the portfolio against the index", "Retail investors", "Paid ₹199 / month"],
   ["**Research desk** (`#/research`)", "Search any listed stock; plain summary with good points and watch-outs, each marked by confidence; peer ranks; analyst desks; time machine", "Retail investors", "Paid ₹299 / month"],
   ["**Practice tools** (`#/practice`)", "Fund overlap; fee drag; emergency-fund meter; weekly spoken digest; scam-call rehearsal", "Retail investors, learners", "Paid ₹99 / month"],
   ["**Govern and audit** (`#/govern`)", "Risk firewall that checks trades against limits; rebalance simulator; hash-chained audit record; tamper test", "Banks, advisers, family offices", "Paid ₹499 / month"]],
  [3.9, 7.4, 3.6, 1.7], size=8.1)
F("shot_rural.jpg", "The Rural tools: a moneylender cost in yearly terms, the rupees paid, and what a bank or group loan would cost instead.", 13.6)
F("shot_whatsapp.jpg", "The WhatsApp and SMS channel: the same answer as the web app, in a phone chat with numbered options and voice notes.", 9.6)

# ============================================================================================ 6
H("6. How it works, step by step")
H("Answering a question", 2)
rich("A question takes the same path whether it is typed in the app, spoken, or sent by WhatsApp:")
F("journey.png", "The path of one question. Step 3 is the decision point; the five paths are the only ways an answer is produced.", 15.4)
B(["**Read the whole sentence.** The understanding layer decides what kind of request it is: a question about the app, a company, a money concept, a personal number, or a scam, tip or loss. It reads meaning, not single keywords.",
   "**Choose the tool.** Calculators compute the figures; checked text explains the concept; the company analysis reads stored data; the scam scripts and recovery steps are written for each situation.",
   "**Show the working.** Every answer has the figures, the steps, a caution, and a 'how this was worked out' line.",
   "**Optional model, closed list.** A local language model, if installed, may only pick one item from a fixed list. It never writes an answer or a figure."])
H("Testing a tip", 2)
rich("A tip is not judged by its tone. It is read into a fixed form and then examined by eight specialists, each working from its own evidence. Two answers come out separately: how likely it is a scam, and how much real backing the idea has.")
F("tip_panel.png", "How a tip is tested: a fixed reading, eight specialists, two separate answers, then one of five actions.", 15.2)
F("shot_tip_panel.jpg", "A real result on a sample tip: the specialists' findings, with the reasons for each.", 13.4)
F("shot_tip_claims.jpg", "The same tip's claims, tested against stored company data, with the source and date of each figure.", 13.4)
H("Trust in the answers", 2)
F("trust.png", "Every answer passes through these steps. No step lets a language model produce a number.", 15.2)

# ============================================================================================ 7
H("7. Technology in depth")
rich("This section is for technical reviewers. It describes what is built, how the parts connect, and the limits of each part.")
H("7.1 Architecture", 2)
F("architecture.png", "The layers of the prototype. Data flows up from the point-in-time store to the people at the top.", 15.0)
T([["Layer", "What is in it", "Where it lives"],
   ["Front end", "React and TypeScript, built with Vite; one stylesheet per area; SVG and canvas charts; a 3D voice orb; a service worker for offline use", "frontend/src"],
   ["API", "FastAPI with about 110 routes; a WebSocket stream for live events; endpoints for the assistant, setup, tip scan, research summary, tours and messaging", "backend/app.py"],
   ["Understanding", "A rule-based reader of the whole sentence; closed-list pick by an optional local model; checked explanations (32), scam scripts (9), guided tours (25)", "backend/understand.py, knowledge.py, scams.py, tours.py"],
   ["Analysis", "Calculators (fees, emergency, goals, tax, panic, overlap, stress); the tip panel; the company summary; portfolio attribution", "analysis/"],
   ["Data", "A SQLite snapshot with a date on every row; a point-in-time store that refuses reads from the future; enrichment for growth, cash, ownership, valuation", "core/, ingest/"],
   ["Channels", "Web app; WhatsApp and SMS simulator; the companion WhatsApp build on a separate device (section 7.5)", "backend/messaging.py"],
   ["Setup", "Ten features, free and paid tiers with demo prices, five baskets, one saved choice per install", "backend/setup.py"]],
  [2.7, 9.6, 4.3], size=8.2)
H("7.2 How the answer pipeline is built", 2)
rich("The assistant reads each question in this order, and stops at the first clear match: a tip or a loss goes to the tip checker or recovery coach; a question about the app goes to a tour; a company goes to the company card; a general concept goes to the checked text; a figure goes to a calculator. Only if none of these match does the older rule router run, and only then the optional local model, whose answer must be one item from a fixed list.")
H("7.3 The tip panel: the mathematics behind the feasibility check", 2)
rich("Feasibility asks whether the promised move could happen at all. The stock's own volatility gives the chance of reaching a price level within a time window, using the reflection principle for a driftless price path:")
P("P(touch) = 2 × (1 − Φ( ln(target / price) / (σ × √(days / 365)) ))", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=6)
rich("where σ is the stock's annualised volatility from its own closing prices, and Φ is the standard normal distribution. For a stock with 30% volatility, a target 45% above the price within one month has a chance of about 1% in this model; the output states the number, not a verdict. A fixed periodic return is converted to an annual rate and compared with bank deposit rates and long-run equity returns. Each specialist reports a stance (for, against, neutral or cannot tell) and the reasoning. The synthesis combines independent signals as one minus the product of their complements, so several weak signals add up without any single one deciding the result.")
H("7.4 Company research", 2)
rich("The company summary reads about twenty-five checks: growth, cash conversion and free cash flow, debt and interest cover, liquidity, distress and quality scores (not for banks, where those measures mean something else), dividends and payout, ownership, the company's own past valuation range, growth-adjusted valuation, peer ranks on five measures, and price behaviour. Each check has a basis (which kinds of data), an age, and a confidence mark. The page lists the checks that had no data under 'could not check'.")
H("7.5 WhatsApp: the simulator in the app, and the companion build", 2)
rich("There are two WhatsApp channels, and they should not be confused.")
B(["**In the repository: the simulator.** The WhatsApp page in the app behaves like the real channel. It sends each message to the same messaging handler that a real number would use. It is complete for testing the conversation, the menus, voice notes and answers; it does not connect to WhatsApp.",
   "**Built separately: the companion assistant.** A second build, on another device, uses an unofficial client library (Baileys or whatsapp-web.js) to run a WhatsApp session on a companion phone or computer, so that the assistant answers from the real WhatsApp account. It sends questions to the same backend answer path. It is not in this repository and this brief does not describe its code in detail."])
F("companion.png", "The companion build: the user's WhatsApp, a companion session on a second device, and the Jarvis answer path. Built separately; not part of this repository.", 14.4)
callout("Important limit on the companion build", "**Unofficial libraries are not an official WhatsApp API.** They depend on how WhatsApp's app works and can break when it changes; their use may conflict with WhatsApp's terms and can lead to the account being restricted. Before any public launch, use the official WhatsApp Business Platform through a licensed provider, or keep the companion for private testing only.", fill="FBE9E7", edge="E7A89E")
H("7.6 Security, privacy and offline use", 2)
B(["Speech-to-text and text-to-speech run on the machine. The portfolio, saved funds, rules and audit record stay in the local database.",
   "Outbound requests are for public market data and, when enabled, the messaging provider.",
   "A shared-device mode clears the previous person's answers before the next person starts.",
   "The audit record is hash-chained: each entry carries the fingerprint of the one before it, so a quiet edit breaks the chain and the break is shown.",
   "The offline pack saves the app shell and the rural calculators (written in standard Python so they run in the browser through Pyodide), so the rural tools work with no signal."])
H("7.7 Testing and quality", 2)
rich("The automated suite has 532 tests across 35 files. They cover routing across several thousand phrasings, numbers that must equal the calculators, Hindi text that keeps every figure, the point-in-time store (no look-ahead), the tip panel, the setup and its prices, the WhatsApp answers, and the audit chain. A separate set of sample runs (tip samples, WhatsApp batches) is kept in the repository so results can be re-checked by anyone.")
H("7.8 Limits we know about", 2)
B(["Voice recognition in Hindi works but has not been tested with rural speakers across accents and phones.",
   "Live data covers the 53-company universe; other companies are fetched on demand and only partly covered.",
   "Practice-tool fund holdings are illustrative samples, not live factsheets.",
   "The setup is saved once per install. Accounts and per-user storage are not built.",
   "Payments are dummy; there is no checkout.",
   "The companion WhatsApp build is not in this repository and has not been reviewed for terms-of-service or security."])
F("stack.png", "Technology stack. Everything in the repository is free and open source and runs on one modest machine.", 15.2)
F("pit.png", "The point-in-time guard: when the clock is set back, later facts are hidden from the analysts.", 14.2)
F("chain.png", "The audit chain: changing one past entry breaks every fingerprint after it, and the break is shown.", 14.6)

# ============================================================================================ 8 competitors
H("8. Competitors and how we compare, feature by feature")
rich("The comparison is by feature group, because no single competitor covers the whole product. Each table names real platforms that compete with one part of JARVIS. Descriptions are from public sources as checked in this revision; features of commercial products change, so confirm them before any sales conversation.")
H("8.1 Scam protection", 2)
T([["", "JARVIS scam protection", "Truecaller (Scam Checker, Scamfeed, Family Protection)", "Bank apps and the 1930 helpline"],
   ["What it is", "Scripts, rehearsal, tip checker, recovery coach in one free tool", "Caller identification and spam blocking, plus a Scam Checker for numbers, links and messages, and a community report feed", "Bank app alerts; a phone line for reporting fraud"],
   ["Who it reaches", "Anyone, including a basic phone through WhatsApp or SMS; no app install", "Smartphone users who install the app; India is its largest market", "The bank's own customers; the helpline for anyone who has lost money"],
   ["Identifies a caller", "No. It does not read numbers", "Yes; a large spam and caller database", "No"],
   ["Explains the specific script and what is true", "Yes: nine scripts, each with what the caller says against what is true", "Warnings and reports; less explanation of the script", "Generic alerts"],
   ["Practice before a real call", "Yes: scam-call rehearsal", "No", "No"],
   ["First-hour recovery steps", "Yes, ordered by time, with the helpline", "Reporting features, not a step-by-step coach", "Helpline call; the bank's own process"],
   ["Family protection", "Planned as a family view, not built", "Yes: a family admin gets alerts and can end a call on a member's behalf", "No"],
   ["Price to the user", "Free", "Free core features; some features may be paid (confirm)", "Free"]],
  [3.0, 4.6, 5.0, 4.0], size=7.9)
rich("**How we differ.** Truecaller is strongest at stopping the call before it arrives. JARVIS is strongest at what happens after the call: explaining the script, practising the reply, and ordering the first hour when money has gone. The two are complementary: a user can run Truecaller and JARVIS together, and a bank could promote JARVIS alongside its own alerts.")
H("8.2 Investing education and the first investment", 2)
T([["", "JARVIS Learn and Practice", "Zerodha Varsity", "Groww (learning inside a trading app)", "Fi Money (conversational money app)"],
   ["Format", "Plain explanations on 32 topics; drill-downs tied to the user's own numbers; a glossary; tours", "Free courses: 17 modules, hundreds of chapters, quizzes, a Hindi library and a certificate", "Short snippets and a content hub inside the app", "Friendly insights on spending, savings and diversification inside an account"],
   ["Ties to the user's own money", "Yes: fee drag, overlap, the portfolio's own goal range", "No: general courses", "Partly: definitions next to the user's data", "Yes: inside an account"],
   ["Works without an investing account", "Yes", "Yes (courses are free)", "No: built for its trading app", "No: built for its money app"],
   ["Languages", "Hindi and English, written by hand", "English with a Hindi library", "English and some Hindi", "English"],
   ["Commercial link", "None: no product sold", "Zerodha is a broker", "Groww is a broker and fund platform", "Fi is a money account"]],
  [2.8, 4.1, 3.6, 3.3, 2.8], size=7.9)
rich("**How we differ.** Varsity and Groww teach investing in general, and then send the learner to their own products. JARVIS explains the learner's own numbers, has no product to sell, and works in Hindi on WhatsApp. It is weaker on depth: a learner who wants a full course should use Varsity.")
H("8.3 Fund and portfolio tools", 2)
rich("Portfolio trackers and broker dashboards (for example Groww, Zerodha's console and ET Money) show holdings and returns. In this revision we did not benchmark their fund-overlap or fee-drag features, so no feature-by-feature claim is made here. The honest position is: JARVIS shows overlap and the rupee cost of a fee over time, and explains tax timing; check the current features of each commercial tool before saying more.")
H("8.4 Farmer information and rural money", 2)
T([["", "JARVIS rural tools", "Kisan Suvidha (government app)"],
   ["What it gives", "Money decisions: loan cost in yearly terms, schemes and papers, why a payment is late, plan a year of irregular income, sell or hold, group ledger", "Farming information: weather for today and the next five days, mandi prices, plant protection, agro advisories, dealer contacts, soil health, access to the Kisan Call Centre"],
   ["Languages", "Hindi and English, by text or voice; WhatsApp and SMS", "Nine languages (per the source)"],
   ["Reach", "Basic phones through WhatsApp and SMS; offline pack", "Over 10.6 lakh downloads (per the source); an app"],
   ["Relationship", "Complementary: we explain what a loan or scheme costs and do not duplicate weather or prices", "Complementary: a link from JARVIS to its prices and advisories would be a natural partnership"]],
  [3.0, 6.8, 6.8], size=8.0)
rich("**How we differ.** Kisan Suvidha tells a farmer what the weather and the market are doing. JARVIS tells the same farmer what the loan really costs and which benefit they are owed. A farmer needs both; the two should link, not compete.")
H("8.5 Group ledgers", 2)
T([["", "JARVIS group ledger", "Khatabook", "DigiKhata"],
   ["Built for", "Self-help groups: savings, internal loans, fines, interest, member statements, meeting reports", "Small businesses: credit and debit with customers and suppliers", "Small businesses (the company is based in Pakistan, so it is not a direct comparison in India)"],
   ["Reach (per public sources)", "Prototype", "About 50 million downloads, about 10 million monthly active users, 13 languages, about 3,000 cities", "Not applicable in India"],
   ["Offline use", "Yes: saved on the device, export a backup", "Mostly app-based", "Not applicable"]],
  [3.4, 5.0, 4.8, 3.4], size=8.0)
rich("**How we differ.** Khatabook is a general business ledger with a large base; it does not model a self-help group's savings, internal loans and fines, or the meeting report. JARVIS's ledger is built for that group, works offline, and writes the report. We do not claim the larger reach.")
H("8.6 WhatsApp chatbots for banks and enterprises", 2)
T([["", "JARVIS on WhatsApp", "Gupshup", "Yellow.ai", "Haptik (Jio)", "Kaleyra (Tata Communications)"],
   ["What it is", "A finance product: calculators, checked answers, scam scripts", "A WhatsApp Business messaging platform; you build the bot", "An enterprise conversational platform; you build the bot", "A conversational AI platform for enterprises", "Enterprise messaging (CPaaS) for regulated industries"],
   ["Built-in finance content and calculators", "Yes", "No: you supply it", "No: you supply it", "No: you supply it", "No"],
   ["Hindi and Indian languages", "Hindi and English, hand-written", "Supported by the platform", "14 Indian languages (per the source)", "Supported", "Supported"],
   ["Known bank users (per public sources)", "None yet", "Enterprise customers", "HDFC Bank and Reliance named as users", "JioMart and others named", "Banks named among regulated clients"],
   ["Role for a bank", "The finance content and scam shield on top of their platform", "The messaging rails", "The bot platform", "The bot platform", "The messaging rails"]],
  [2.7, 3.2, 2.7, 2.8, 2.7, 2.5], size=7.5)
rich("**How we differ.** These platforms compete for the channel. JARVIS is not a messaging platform and should not try to be one. A bank or NGO that already uses one of them can add JARVIS's finance content, calculators and scam scripts as a module. The sale is to the content and the outcome, not to the pipes.")
H("8.7 Moneylender and informal credit checks", 2)
rich("We did not find a direct consumer competitor in this revision. The closest products are loan calculators on bank and lender websites, which compute an EMI for a stated rate but do not convert a monthly moneylender rate to a yearly figure, compare it with informal and formal alternatives, or explain the cost in Hindi on a basic phone. This should be checked with a fuller search before the pitch.")
H("8.8 Summary: where we sit", 2)
T([["Category", "Direct competitors", "Our position", "Stance"],
   ["Scam protection", "Truecaller; bank alerts; helplines", "After-the-call protection, rehearsal and recovery; works on a basic phone", "Complementary; can be combined"],
   ["Investing education", "Zerodha Varsity; Groww; Fi Money", "Explains the user's own numbers, no product sold, Hindi on WhatsApp", "Competitive for the first-time investor; weaker on depth"],
   ["Fund and portfolio tools", "Broker and portfolio apps", "Overlap and fee cost in rupees; tax timing; governance record", "To be benchmarked before claiming an edge"],
   ["Farmer information", "Kisan Suvidha", "Money decisions for the farmer, not weather or prices", "Complementary; link, do not compete"],
   ["Group ledgers", "Khatabook (business ledger)", "Self-help-group records and meeting reports, offline", "Different segment"],
   ["WhatsApp channel for banks", "Gupshup; Yellow.ai; Haptik; Kaleyra", "Finance content and scam shield, delivered on their rails", "Partner, not a rival platform"],
   ["Moneylender cost", "Loan calculators (no informal conversion)", "Yearly rate, comparison and Hindi explanation", "Little direct competition found; verify"]],
  [3.2, 4.4, 5.8, 3.2], size=8.0)

# ============================================================================================ 9 business
H("9. Business: who pays, why, and how we reach them")
rich("The free core is the reason people trust the product. The business is built on the institutions that gain when their customers are safer and better informed, and on premium tools for investors. Rural users are not the source of revenue; they are the reason the product exists.")
F("business.png", "Who pays for what. Users on the left use the product; institutions on the right pay for a licence, a programme or outcome reports.", 15.2)
H("9.1 Revenue streams", 2)
T([["Stream", "Who pays", "What they buy", "How it is priced (proposal)", "Why they pay"],
   ["Institution licence", "Banks and co-operative banks", "Finance content, scam shield and loan-cost tools for their customers, on their channels; compliance record", "Annual licence per institution, with a per-active-user cap; demo basket is ₹499/month", "Fewer fraud complaints and losses; customer education; a record for auditors"],
   ["Programme contract", "NGOs, state rural missions, federations", "Deployment in a region with local-language content, training and outcome reporting", "Project fee plus a per-group or per-district rate", "Measured reach and outcomes for their funders"],
   ["Outcome reports", "CSR funds and funders", "Impact dashboard: scams refused, true rates learned, schemes claimed", "Subscription to reporting, tied to a programme", "Evidence for spending decisions"],
   ["Premium subscription", "Retail investors", "Portfolio X-ray, research desk, practice tools; demo basket ₹597/month", "Monthly per feature (₹99 to ₹299) or per basket", "Time saved and better decisions"],
   ["Adviser seats and API", "Registered advisers, fintechs", "Governance and audit tools; the calculators and scam scripts as an API", "Seat price and API calls", "Faster product build; a compliance record"]],
  [2.7, 3.0, 4.4, 3.8, 2.7], size=7.9)
F("partners.png", "The partner ecosystem: who delivers, who funds, and who must stay involved in the advice.", 14.2)
H("9.2 Why the model works", 2)
B(["**The free core is cheap to serve.** Local software and free public data. The main variable cost is messaging, which can be passed to the programme or the institution.",
   "**Institutions already pay for fraud.** A bank that cuts scam losses or complaints has a measurable return; a licence is easier to justify than a consumer subscription.",
   "**One engine, several products.** The same calculators and checked content serve the bank, the NGO and the investor, which lowers the cost of each new customer type.",
   "**Trust is the moat.** No figure is invented, every answer shows its working, and nothing is sold. That is hard to copy quickly and matters most to regulated buyers."])
H("9.3 How we reach each buyer", 2)
T([["Buyer", "Entry point", "What they need to see", "Typical first step"],
   ["Co-operative banks and small finance banks", "Customer-protection or financial-inclusion team", "Fraud-loss data, a pilot with their own customers, compliance record", "Pilot in one branch area for eight weeks"],
   ["Large banks", "Digital channels and fraud-risk teams", "Integration with their WhatsApp or app, data-protection review, a proven pilot", "Sandbox with a limited customer group"],
   ["State rural missions and NGOs", "Livelihood and financial-literacy programmes", "Local-language content, field training, outcome measures", "A district pilot with a field partner"],
   ["Self-help group federations", "Federation leaders", "Ledger that works offline, meeting reports, trust in the tool", "A pilot with a few groups"],
   ["Investors and advisers", "Direct, through the website and partner webinars", "A research summary that is honest about gaps; the audit record", "Free trial of one paid feature"],
   ["Funders and CSR", "Impact teams", "A dashboard of outcomes and a clear pilot plan", "Funded pilot with reporting"]],
  [3.7, 4.1, 5.1, 3.7], size=7.9)
H("9.4 Going to market: a sequence", 2)
B(["**Pilot (first eight weeks).** One district or one federation, a real WhatsApp channel through a licensed provider, weekly sessions, and three measures: true yearly rate learned, scams refused, schemes found.",
   "**Proof (months three to six).** Publish the pilot's numbers. Convert the pilot into a paid programme with the NGO or a co-operative bank.",
   "**Institutions (months six to eighteen).** Offer the licence to two or three banks, with the compliance record and the scam shield as the core.",
   "**Scale (after eighteen months).** Add languages and voice-first access, and a partner API for advisers and fintechs."])
H("9.5 Unit economics: what we can say now", 2)
rich("We do not yet have revenue or margin figures we would defend in front of a buyer, because the pilot has not run. No figures are shown here for that reason. What can be said is the structure: the free core costs little to serve per user; the institutional and programme revenue pays for the content, support and messaging; the premium tier pays for the research and governance tools. The pilot (section 9.4) is designed to produce the real numbers: cost per active user, fraud losses avoided, and partner renewals.")
H("9.6 Risks to the business", 2)
T([["Risk", "Why it matters", "Mitigation"],
   ["Slow public-sector procurement", "Programme and missions take long to approve", "Start with NGOs and co-operatives; keep the pilot small and cheap"],
   ["Platform dependence on WhatsApp", "Unofficial channels can break or lose accounts", "Use the official platform through a licensed provider for any public launch"],
   ["Regulatory limits on advice", "Paid investment advice needs SEBI registration", "Describe and explain only; partner with registered advisers for premium advice"],
   ["Competitors with a bigger reach", "Truecaller and the bank apps already have users", "Complement rather than compete; offer the content to them as a module"],
   ["Content upkeep", "Tax rules, scheme rates and scam patterns change", "An editorial process with dated rules and native-speaker review"]],
  [3.6, 6.2, 6.8], size=8.2)

# ============================================================================================ 10
H("10. Risks, compliance and ethics")
T([["Risk", "Why it matters", "How we handle it"],
   ["Looking like regulated advice", "In India, paid investment advice needs SEBI registration", "Describe, never recommend; no buy, sell or hold; confidence marks; registered partners for advice"],
   ["Wrong or outdated rules", "A wrong tax or scheme figure harms trust", "Dated rules with 'as of' wording; a review cycle; the user is told to confirm"],
   ["Personal data", "Financial data is sensitive; the Digital Personal Data Protection Act 2023 applies", "Local processing; no raw data leaves the device by default; consent for any cloud channel; shared-device wipe"],
   ["Scam scripts used as a how-to", "A script could be read as instructions for a scam", "Written from the victim's side with protective steps; no operational detail"],
   ["Translation errors", "A bad translation can change a meaning", "Hand-written bilingual text; native-speaker review before each new language"],
   ["Over-reliance", "People may treat the tool as a guarantee", "Stated limits on every answer; decisions stay with the person"],
   ["Connectivity", "Rural networks are uneven", "Offline pack; SMS fallback; low-bandwidth screens"],
   ["Channel terms", "Unofficial WhatsApp libraries may breach terms", "Companion build kept for private testing; official platform for public use"]],
  [3.6, 5.6, 7.4], size=8.2)
H("Ethical principles", 2)
B(["Serve the person, not the product: nothing is sold through the tool.", "Say what is not known. A gap is shown, not hidden.",
   "Never shame a victim: 'none of this is your fault' is part of every recovery answer.", "Keep a record a person can inspect."])

# ============================================================================================ appendix
H("Appendix A. Demo script (six minutes)")
T([["Minute", "Do this", "Say this"],
   ["0-1", "Open the setup; pick the farmers basket; start", "One app, five starting points; the farmer sees only what is theirs"],
   ["1-2", "Rural tools: moneylender, 5 rupees per hundred, Rs 50,000", "Sixty per cent a year, in rupees; free, in Hindi"],
   ["2-3", "Assistant: 'someone asked for my OTP on a call'", "A script-specific answer, and the reason it is a scam"],
   ["3-4", "WhatsApp page: send a sentence in Hindi", "The same answer on a basic phone; the companion is a separate build"],
   ["4-5", "Protect: tip checker, sample scam tip", "Eight specialists, two separate answers, and what to do"],
   ["5-6", "Setup: add Govern & audit; show the paid tier", "Banks pay for the compliance record; rural stays free"]],
  [1.6, 7.4, 7.6], size=8.4)
H("Appendix B. Questions reviewers ask")
T([["Question", "Short answer"],
   ["Is this financial advice?", "No. It describes and explains; it never says buy, sell or hold."],
   ["How do you avoid wrong numbers?", "No language model produces a number. Calculators and dated data do, and 532 tests check them."],
   ["Who pays if the users are poor?", "Institutions that gain from fewer frauds and better reach; the users pay nothing."],
   ["What about Truecaller and the banks?", "They stop the call. We help after the call: the script, the rehearsal and the first hour. We complement them."],
   ["Is the WhatsApp bot real?", "The simulator in the app is real and tested. The companion build is a separate build on another device, not in this repository, and it needs a review of channel terms."],
   ["What is not built yet?", "Accounts, real payments, a live WhatsApp number on the official platform, and tests with rural speakers."]],
  [5.2, 11.4], size=8.4)
H("Appendix C. Glossary")
T([["Term", "Meaning"], ["SHG", "Self-help group: a small, usually women's, group that saves and lends together"],
   ["DBT", "Direct benefit transfer of subsidies and pensions to bank accounts"], ["UPI", "The national instant payment system"],
   ["SIP", "Systematic investment plan: a fixed monthly investment into a fund"], ["Point-in-time store", "A data store where every read is filtered by a clock, so the future is hidden"],
   ["Hash chain", "Each record carries the fingerprint of the one before, so an edit is detectable"], ["Companion build", "The WhatsApp assistant on a second device, built separately"],
   ["CSC", "Common Service Centre: village-level digital service points"], ["1930", "The national cybercrime helpline"]],
  [3.6, 13.0], size=8.6)
H("Appendix D. Sources and notes")
B(["Product facts: the repository at the time of writing (code, tests, documentation in docs/CONTEXT.md).",
   "India context: NCFE Financial Literacy and Inclusion Survey 2019; I4C and 1930 reporting; SIDBI study on informal lending (2019); SEBI Investor Survey 2025; Digital Personal Data Protection Act 2023.",
   "Competitor descriptions: public pages and press coverage checked in this revision (Truecaller Scam Checker and Family Protection announcements; Zerodha Varsity app pages and support pages; Groww and Fi Money public descriptions; Kisan Suvidha government pages; Khatabook and DigiKhata public profiles; Gupshup, Yellow.ai, Haptik and Kaleyra public descriptions). Confirm current features before a sales meeting.",
   "Business figures are illustrations to be replaced by pilot data."])

out = ROOT / "JARVIS_Product_Brief_v2.docx"
d.save(out)
words = sum(len(p.text.split()) for p in d.paragraphs) + sum(len(c.text.split()) for t in d.tables for r in t.rows for c in r.cells)
print("saved", out, "words ~", words)
