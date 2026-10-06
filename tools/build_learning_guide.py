"""Builds JARVIS_Learning_Guide.docx: a learning document on the prototype, its data, competitors,
money and costs. Every figure is either from the repo (docs/*.md, code) or marked "verify".
Run: python tools/build_learning_guide.py
"""
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Cm

OUT = "C:/Jarvis_Hedge_Fund/JARVIS_Learning_Guide.docx"
GREEN = RGBColor(0x1F, 0x5C, 0x3E)
GREY = RGBColor(0x55, 0x55, 0x55)

doc = Document()
for s in doc.sections:
    s.left_margin = s.right_margin = Cm(2.2)
    s.top_margin = s.bottom_margin = Cm(2)

st = doc.styles["Normal"]
st.font.name = "Calibri"
st.font.size = Pt(10.5)
for name, size in [("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 11)]:
    h = doc.styles[name]
    h.font.name = "Calibri"
    h.font.size = Pt(size)
    h.font.color.rgb = GREEN


def shade(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def p(text, bold=False, italic=False, color=None, size=None):
    para = doc.add_paragraph()
    run = para.add_run(text)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = color
    if size:
        run.font.size = Pt(size)
    para.paragraph_format.space_after = Pt(6)
    return para


def bullets(items):
    for it in items:
        para = doc.add_paragraph(style="List Bullet")
        if isinstance(it, tuple):
            r = para.add_run(it[0])
            r.bold = True
            para.add_run(it[1])
        else:
            para.add_run(it)
        para.paragraph_format.space_after = Pt(2)


def table(header, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold = True
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        shade(c, "1F5C3E")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(v))
            r.font.size = Pt(9)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def note(text):
    para = doc.add_paragraph()
    r = para.add_run(text)
    r.italic = True
    r.font.size = Pt(9)
    r.font.color.rgb = GREY


# ----------------------------------------------------------------- title
t = doc.add_paragraph()
t.alignment = WD_ALIGN_PARAGRAPH.LEFT
r = t.add_run("JARVIS // money, plainly")
r.bold = True
r.font.size = Pt(24)
r.font.color.rgb = GREEN
p("Learning guide: the prototype, its data, its competitors, its money and its costs", size=13, color=GREY)
p("Written for the builder, to learn from. Sections 1 to 9 explain the product. Sections 10 to 13 are business: "
  "competitors, money, costs and risk. Figures come from the repository (docs/CONTEXT.md, docs/DATA.md, "
  "docs/ARCHITECTURE.md, docs/TECHNICAL_OVERVIEW.md, docs/BUSINESS_DATA_COSTS.md) or from public sources listed in section 14. "
  "Anything not checked is marked VERIFY.", italic=True, size=9.5)

# ----------------------------------------------------------------- 0 contents
doc.add_heading("Contents", level=2)
for line in ["1. The problem in plain terms", "2. What the prototype does: ten features", "3. How a question becomes an answer",
             "4. The engines and agents: who decides what", "5. Architecture and the technology stack",
             "6. The data: every data set, its source and its status", "7. Honesty rules and known limits",
             "8. Setup, baskets and the demo price", "9. Recent work and decisions (what changed and why)",
             "10. Competitor analysis", "11. Business model and how money would come in", "12. Costs: running and building",
             "13. Legal, regulatory and risk points", "14. Sources and what to verify next", "Glossary"]:
    p(line, size=10)

# ----------------------------------------------------------------- 1 problem
doc.add_heading("1. The problem in plain terms", level=1)
p("Ordinary households, especially rural families and first-time savers, lose money through three channels. "
  "Each one has a moment where a short, plain check would change the outcome. JARVIS is built around those moments.")
table(["Loss channel", "What it looks like", "Figure we can cite", "Status"],
      [["Digital fraud", "Panic transfers, OTP and remote-app scams, fake KYC and impersonation calls",
        "About ₹22,845 crore lost in 2024, against about ₹7,465 crore in 2023; about 19 lakh financial-fraud complaints on NCRP in 2024",
        "I4C figures as reported in a 2025 industry summary. VERIFY against the official I4C release."],
       ["Informal credit", "A moneylender quotes ₹2 to ₹5 per ₹100 a month",
        "5% a month is 60% a year on simple interest (arithmetic), more with compounding. Formal KCC about 7% a year, about 4% with prompt-repayment relief",
        "Arithmetic is exact. Informal-rate ranges come from older SIDBI and NSS-based summaries; VERIFY before quoting."],
       ["Fees and unverified tips", "Fund fees take a share of long-run growth; tips with no time frame or source",
        "A 2% fee on a 20-year horizon is shown with the user's own inputs (an illustration, not a national statistic)", "Calculation, not a survey."]],
      widths=[3, 4.5, 6, 4.5])
p("Context figures, with caveats:", bold=True)
bullets([
    "Financial literacy: 27% of adults, 24% in rural areas (NCFE 2019 survey).",
    "Households in the securities market: about 9.5%, rural about 6% (SEBI Investor Survey 2025). VERIFY on sebi.gov.in.",
    "Rural share of GDP: about 46% of net domestic product (NITI Aayog and CSO estimates).",
    "Rural share of deposits: strictly rural branches hold about 10 to 11% of scheduled bank deposits; rural plus semi-urban branches hold about 28 to 30% (RBI Basic Statistical Returns). Always say which of the two you mean.",
])
p("Figures we do not use until a source is found: bank fraud of ₹48,000 crore in FY 2025–26; ₹5,000 to ₹8,000 crore recovered through 1930; "
  "co-operative bank NPA of 35 to 38% and ₹7,500 crore of stressed rural assets; \"trillions\" of unclaimed benefits. "
  "They appeared in an outside draft without a source.", italic=True, size=9.5)
p("Why it reaches banks and lenders: a household paying 60% a year on an informal loan has little left to repay a formal loan. "
  "That raises default risk on co-operative and microfinance books, and pushes borrowers back to informal lenders when formal lenders tighten. "
  "The prototype does not measure this. A pilot with a partner bank would have to.")

# ----------------------------------------------------------------- 2 features
doc.add_heading("2. What the prototype does: ten features", level=1)
p("One codebase, ten features, grouped by the loss each one addresses. Home is always on. Routes are hash routes (#/route).")
table(["Loss channel", "Feature (route)", "Tier", "What it does", "Status"],
      [["Fraud shield", "Scam protection (#/protect)", "Free", "Nine scam scripts; tip checker with eight specialists; recovery coach for the first hour; tax shield; panic-sell replay; standing 'tell me if' rules", "Working"],
       ["Credit cost", "Rural tools (#/rural)", "Free", "Twelve tools: moneylender check, credit score guide, is this offer real, UPI safety, policy check, schemes, papers checklist, why no money, plan my year, sell or hold, daily saving, group ledger", "Working; offline once the pack is saved"],
       ["Investing protection", "Portfolio X-ray (#/portfolio)", "Paid", "Health grade, spread, allocation map, what-to-do list, money against the index", "Working on sample portfolios"],
       ["Investing protection", "Research desk (#/research)", "Paid", "Plain company summary with confidence marks; three analyst desks and a red team; time machine", "Working; data-licence dependent"],
       ["Investing protection", "Practice tools (#/practice)", "Paid", "Fund overlap checker, fee-drag slider, emergency-fund meter, weekly spoken digest, scam-call rehearsal", "Working; fund data is illustrative"],
       ["Reach and trust", "Assistant (#/assistant)", "Free", "Types or speaks a question in English or Hindi; every reply is a card with figures, a chart, steps and a caution; guided tours", "Working"],
       ["Reach and trust", "WhatsApp and SMS (#/whatsapp)", "Free", "The same answers on a phone chat: numbered menu, voice notes, Hindi", "Simulator; real delivery needs a Twilio account"],
       ["Reach and trust", "Learn (#/learn)", "Free", "32 checked explanations in English and Hindi; goal range from the portfolio's own history; glossary", "Working"],
       ["Reach and trust", "Govern and audit (#/govern)", "Paid", "Risk firewall for trades against per-stock, per-industry and cash limits; rebalance simulator; hash-chained audit record; tamper test", "Working on paper portfolio"],
       ["All", "Setup (#/setup)", "Free", "Choose a basket (five audiences) and switch features; locked-feature page for anything not in the setup", "Working; one saved setup per install"]],
      widths=[2.6, 3.4, 1.4, 6.6, 3])
p("Setup baskets (for pitching only): full prototype; banks and co-operative banks; farmers and rural families; self-help groups and NGOs; middle-class retail investors. "
  "Every feature works in every basket. A basket only sets the default menu.")

# ----------------------------------------------------------------- 3 flow
doc.add_heading("3. How a question becomes an answer", level=1)
p("Every typed or spoken question, from the assistant or WhatsApp, follows the same path. This is the most important flow to understand.")
bullets([
    ("Input. ", "Text, or speech sent to the local speech-to-text engine (faster-whisper). Each request carries its language and a tab identifier, so an English tab and a Hindi tab never mix."),
    ("Understanding. ", "backend/understand.py reads the whole sentence first and decides what kind of question it is: a question about the app (guided tour), a company (research or comparison), a general money question (checked explanation), a personal number question (calculator), a tip (tip checker), or a loss (recovery coach)."),
    ("Rules. ", "Only if none fits, the older rule router runs (backend/assistant.py, backend/intents.py). Regular expressions with word boundaries pick one intent."),
    ("Optional model. ", "If Ollama is installed, a local model may only pick one intent from a closed list. It never writes an answer or a figure."),
    ("Calculator. ", "The chosen handler calls a pure Python calculator (analysis/*.py or backend/rural.py). Numbers come from code and dated data only."),
    ("Words. ", "The answer is written from hand-written English or Hindi templates. A translation check rejects any change to a number."),
    ("Delivery. ", "The answer goes back as an event tagged with the tab identifier. Other tabs ignore it. It can be spoken with the local text-to-speech engine."),
])
p("Worked example: \"My moneylender asks 5 rupees per hundred a month on 50,000.\" The rule matches the moneylender intent. "
  "rural.loan_cost works out 5% a month, 60% a year on simple interest, and ₹30,000 of interest on ₹50,000 for a year. "
  "The comparison card puts this next to KCC at about 7% a year (about 4% with prompt repayment). No model writes any of those numbers.")

# ----------------------------------------------------------------- 4 engines and agents
doc.add_heading("4. The engines and agents: who decides what", level=1)
p("Nothing in the prototype acts on its own in the world. The word 'agent' is used for small deciders. Each is either fixed code or a checker over a closed list.")
table(["Component", "File", "Decision it makes", "How"],
      [["Question understanding", "backend/understand.py", "Which handler owns the question", "Ordered rules; tip and loss messages are routed away from general answers"],
       ["Rule router", "backend/assistant.py, intents.py, router.py", "Which calculator, with which inputs", "Regular expressions with word boundaries"],
       ["Optional local model", "agents/llm.py (Ollama, llama3.1:8b)", "Picks one intent from a closed list; writes desk notes", "Optional; answers still work without it"],
       ["Tip panel (eight specialists)", "analysis/tipminds.py, scanner.py", "Scam chance and backing, reported separately; then an action", "Fixed functions: feasibility (price model), fundamentals, technicals, market structure, source and incentive, SEBI rules, wording (one witness), consequence"],
       ["Research desks", "agents/desks.py, orchestrator.py, evidence.py", "Three analyst views (Fundamental, Quant, Narrative) and a red team", "Concurrent; uncited claims dropped by a citation gate"],
       ["Company summary", "analysis/proscons.py, ingest/enrich.py", "Good points and watch-outs with confidence", "Rule-based tests on the company's numbers; missing data reported, not filled in"],
       ["Risk engine", "risk/engine.py, policy.py", "Allowed or not for a trade; largest allowed size", "Limits per stock, industry and cash; never imports a model"],
       ["Scam and recovery", "backend/scams.py, recovery.py, practice.py", "Matched script; recovery checklist by situation and time", "Phrase patterns; first-hour clock; template drafts"],
       ["Offer checker", "backend/rural.py (scheme_check)", "Risk score for an offer", "Return signal on a log scale from the 7% benchmark; warning signs combined so that each adds less than the last; breakdown shown"],
       ["Audit ledger", "backend/ledger.py", "Records every paper trade", "Hash chain; SQLite triggers block edits"],
       ["Setup gate", "backend/setup.py, App.tsx", "Which features the menu shows", "Saved list; locked page for anything else"]],
      widths=[3.2, 4, 4.4, 5.4])
p("Three invariants protect the design: (1) risk/ never imports a language model; (2) calculators are pure and shared, so the page slider and the chatbot cannot disagree; "
  "(3) a translation may never change a number.", bold=True)

# ----------------------------------------------------------------- 5 architecture
doc.add_heading("5. Architecture and the technology stack", level=1)
table(["Layer", "Technology", "Where", "Why"],
      [["Backend API", "FastAPI, uvicorn, one process", "backend/app.py (about 110 routes, /ws WebSocket)", "Typed requests, async, live answers, runs on one laptop"],
       ["Storage", "SQLite (WAL)", "data/snapshot.db and runtime tables", "No server to install; one file to carry"],
       ["Point-in-time store", "core/pit.py", "All calculators read through it", "Filters on published_at <= simulated clock: no figure sees the future"],
       ["Calculators", "Pure Python, standard library", "analysis/*.py, backend/rural.py", "Deterministic, testable; rural file also runs in the browser through Pyodide"],
       ["Frontend", "React, TypeScript, Vite, zustand, hash routes", "frontend/src", "Fast builds; works from a static build and an offline pack"],
       ["Charts", "recharts; optional TradingView tab; Yahoo Finance when online", "backend/charts.py", "Snapshot used when offline; source and date shown"],
       ["Speech in", "faster-whisper (local)", "voice/stt.py, POST /stt", "No audio leaves the machine"],
       ["Speech out", "Kokoro or Piper (local)", "backend/tts.py, POST /tts", "Spoken answers without a cloud service"],
       ["Local model", "Ollama, llama3.1:8b (optional)", "agents/llm.py", "Picks intents and writes desk notes only"],
       ["Offline", "Service worker and Pyodide", "frontend and /offline", "Rural calculators work without a network"],
       ["Messaging", "Simulator; Twilio webhook", "backend/messaging.py, /twilio/webhook", "Same answers as the web; live needs a provider account"],
       ["Tests", "pytest (532 tests), TypeScript check, Vite build", "tests/, docs/TESTING.md", "Guard numbers, wording and the frozen event contract"]],
      widths=[2.8, 4.2, 4.6, 5])
p("Run it: one process serves the API, the built frontend and the landing page. The frontend development server (port 5173) forwards API routes to the backend (port 8000). "
  "Every backend route needs a proxy entry in frontend/vite.config.ts, or the dev server returns the page instead of data. This caused a real bug during the recent work.", size=10)
p("Frozen contract: core/events.py defines the WebSocket events (PROTOCOL_VERSION = 1). Fields may be added, never removed or retyped.", size=10)

# ----------------------------------------------------------------- 6 data
doc.add_heading("6. The data: every data set, its source and its status", level=1)
p("Status key: Live-ingested means pulled into data/snapshot.db by tools/ingest.py and then frozen. Static means written into the code by hand. "
  "Illustrative means a sample, labelled as one in the app.")
doc.add_heading("6.1 Market data", level=2)
table(["Data", "Source", "Status", "Used for", "Point-in-time tier"],
      [["Daily prices, 57 symbols, 2019 to 2026 (about 102,900 rows)", "Yahoo Finance via yfinance (NSE .NS and some US tickers)", "Live-ingested, frozen", "Charts, tip volatility, research, X-ray", "exact"],
       ["Fundamentals (ratios, growth, cash, debt; about 14,700 signal rows including macro)", "yfinance", "Live-ingested", "Company summary, tip fundamentals", "snapshot_only for current ratios; approximated for quarterly (45-day lag)"],
       ["US company facts", "SEC EDGAR company facts", "Live-ingested", "US names", "exact"],
       ["Company news and filings text (552 documents)", "Google News RSS", "Live-ingested", "Research desk evidence", "exact"],
       ["Global news events", "GDELT", "Live-ingested", "Research desk evidence", "exact"],
       ["Macro series", "FRED; RBI and NSE series via jugaad-data", "Live-ingested", "Context in research and learn", "approximated"],
       ["Announcements, delivery %, bulk deals", "nsepython", "Live-ingested", "Research evidence", "exact"],
       ["Universe (tickers, sectors, names, benchmark)", "config/universe.yaml", "Static", "Sector maps and screens", "n/a"],
       ["Extra stocks searched by the user", "yfinance on demand; NSE listing CSV (archives.nseindia.com)", "On demand, kept separate", "Research on any listed stock", "as above"]],
      widths=[4.4, 3.8, 2.6, 3.4, 2.6])
note("Known gaps (docs/DATA.md): some tickers return 404 on Yahoo; a demerged company's history must map to its successor; prices are a frozen snapshot, not live.")
doc.add_heading("6.2 Government schemes (rural tools)", level=2)
p("The rural tools cover 19 schemes, each with its official portal named in backend/rural.py: PM-KISAN (pmkisan.gov.in), Kisan Credit Card (pmkisan.gov.in or your bank), "
  "PM Fasal Bima Yojana (pmfby.gov.in), PMJJBY and PMSBY (jansuraksha.gov.in), Atal Pension Yojana (npscra.nsdl.co.in), Ayushman Bharat PM-JAY (pmjay.gov.in; helpline 14555), "
  "MGNREGA (nrega.nic.in), e-Shram (eshram.gov.in), PM-SYM (maandhan.in), PMAY-G (pmayg.nic.in), PM Ujjwala (pmuy.gov.in), NSAP pensions (nsap.nic.in), "
  "Sukanya Samriddhi (indiapost.gov.in), scholarships (scholarships.gov.in), PM MUDRA (mudra.org.in), PM Vishwakarma (pmvishwakarma.gov.in), PM SVANidhi (pmsvanidhi.mohua.gov.in), "
  "PM Jan Dhan (pmjdy.gov.in), and DAY-NRLM (aajeevika.gov.in).")
p("The benefit text, eligibility and document lists are static and hand-written. Schemes change with budgets. Check each portal before each pilot and record a last-checked date.")
doc.add_heading("6.3 Rates, tax and reference constants", level=2)
table(["Constant", "Value", "Where in code", "Status"],
      [["Bank deposit benchmark", "About 7% a year", "analysis/tipminds.py (RISK_FREE), rural.py (SAFE_BENCHMARK)", "Rough round figure; update from published RBI and bank rates"],
       ["Long-run equity return (scale only)", "About 12% a year", "analysis/tipminds.py (EQUITY_LONG_RUN)", "Used only for scale"],
       ["Best sustained professional record", "About 25% a year", "analysis/tipminds.py (ELITE_SUSTAINED)", "Used only for scale"],
       ["KCC interest", "About 7%; about 4% with prompt-repayment relief", "backend/rural.py (ALTERNATIVES)", "Static; VERIFY with the bank"],
       ["Post office schemes (comparison)", "About 7.5%", "backend/rural.py (SAFE_YEARLY)", "Static; update each quarter from India Post"],
       ["Short-term capital gains, listed equity", "20% (Section 111A)", "analysis/tax.py", "Verify against the current Act and Finance Act"],
       ["Long-term capital gains, listed equity", "12.5% (Section 112A)", "analysis/tax.py", "As above"],
       ["LTCG exemption", "₹1,25,000 a financial year", "analysis/tax.py", "As above"],
       ["Long-term holding period", "365 days", "analysis/tax.py", "As above"],
       ["Fee-drag default return", "12% before fees; cheap-fund fee 0.2%", "analysis/tools.py", "Illustrative defaults"],
       ["Emergency fund target", "6 months; investments haircut 20%", "analysis/tools.py", "Rule of thumb"]],
      widths=[4.2, 3.8, 4.6, 4.4])
doc.add_heading("6.4 Scam, helpline and regulator references", level=2)
table(["Item", "Source", "Where used"],
      [["National cyber-fraud helpline 1930", "Government of India", "Recovery coach, assistant, rural tools"],
       ["cybercrime.gov.in", "Ministry of Home Affairs (National Cyber Crime Reporting Portal)", "Recovery drafts and links"],
       ["Nine scam scripts; scripted rehearsal callers; red-flag patterns", "Written for this project from publicly reported scam types", "Scam protection; practice tools"],
       ["SEBI SCORES grievance portal; sebi.gov.in intermediary check", "SEBI", "Tip checker, learn"],
       ["RBI Sachet portal (illegal deposit schemes)", "RBI", "Offer checker"],
       ["MCA company check (mca.gov.in)", "Ministry of Corporate Affairs", "Offer checker, research"]],
      widths=[6.2, 6.2, 4.6])
doc.add_heading("6.5 Context figures (cited, not calculated)", level=2)
table(["Figure", "Source as cited", "Caveat"],
      [["27% adults financially literate; 24% rural; women over 80% not", "NCFE Financial Literacy and Inclusion Survey 2019", "Dated"],
       ["About ₹22,845 crore fraud losses in 2024; about 19 lakh NCRP complaints", "I4C figures as reported in a 2025 industry summary", "VERIFY the official release"],
       ["Informal lending practices", "SIDBI study on informal sector lending, 2019", "Dated; re-check"],
       ["About 9.5% of households in markets; rural about 6%", "SEBI Investor Survey 2025", "VERIFY on sebi.gov.in"],
       ["Rural about 46% of GDP; deposits about 10 to 11% strictly rural and 28 to 30% rural plus semi-urban", "NITI Aayog and CSO; RBI Basic Statistical Returns", "State which definition is used"]],
      widths=[6.4, 5.6, 4])
doc.add_heading("6.6 Sample and illustrative data (not real)", level=2)
table(["Data", "Where", "What it is"],
      [["Eight sample mutual funds with holdings and fees (Nifty 50 Index 0.20%; Large Cap A 1.60%; Bluechip B 1.70%; Flexi Cap C 1.55%; Technology 1.0%; Banking 1.1%; Healthcare 1.2%; Consumption 1.3%)", "backend/practice.py (FUNDS)", "Rounded and typical of their type. Not real factsheets. Replace with AMC disclosures before real use."],
       ["Sample portfolios", "config/policies.yaml, risk/seed.py, backend/practice.py", "Illustrative"],
       ["Scam-call scenarios (kyc, police, invest)", "backend/practice.py, practice_hi.py", "Scripted for training"],
       ["Tip-test samples", "docs/TIP_TEST_SAMPLES.md (from tools/tip_samples.py)", "Synthetic inputs"],
       ["Setup prices (₹99, ₹199, ₹299, ₹499, ₹597 baskets)", "backend/setup.py", "Dummy. Nothing is charged."]],
      widths=[6.6, 4.6, 5.6])
doc.add_heading("6.7 User data (stays on the machine)", level=2)
table(["Data", "Where it lives", "Leaves the machine?"],
      [["Typed and spoken questions", "Process memory; audio is not stored", "No"],
       ["Portfolio, cost basis (lots), saved funds, watches", "SQLite: lots, portfolios, my_funds, watches", "No"],
       ["Paper-trade audit record", "SQLite paper_ledger (hash-chained)", "No"],
       ["Setup choice", "SQLite app_setup", "No"],
       ["Public market data requests", "Yahoo, SEC, Google News, GDELT, FRED, NSE", "Only the ticker or series asked for"],
       ["WhatsApp messages (when live)", "Twilio and Meta", "Yes, through the provider; needs a privacy notice"]],
      widths=[6, 5.6, 5.2])

# ----------------------------------------------------------------- 7 honesty
doc.add_heading("7. Honesty rules and known limits", level=1)
doc.add_heading("7.1 Rules the product keeps", level=2)
bullets([
    "No model writes a number. Figures come from calculators and dated data.",
    "No buy, sell or hold advice. Answers describe, compare and explain. Tests check the wording.",
    "Show the working. Every answer has a 'how this was worked out' line.",
    "Say what is not known. Missing data goes under 'could not check', never guessed.",
    "Age is visible. Every data kind shows its date; old data is labelled.",
    "Paper only. No broker connection and no real money.",
    "Dummy money. Setup prices are for the pitch; nothing is charged.",
])
doc.add_heading("7.2 Known limits (say these on any slide)", level=2)
bullets([
    "WhatsApp is a simulator. Live delivery needs a Twilio account and approved templates.",
    "The setup is saved once per install, not per user. A real product needs accounts.",
    "Payments are dummy. There is no checkout or invoice.",
    "Hindi speech recognition works but accuracy varies with accent and microphone; it has not been tested with rural speakers.",
    "Live prices and company data cover the 53-company universe well; other companies are fetched on demand and only partly covered.",
    "Fund holdings are illustrative, not factsheets.",
    "The assistant's understanding was tested on about 500 automated cases and sample phrasings, not on real user recordings.",
    "Mobile layouts were checked for the assistant, not for every page.",
    "The local language model is optional and was not installed during the last checks.",
    "The audit chain is tamper-evident, not tamper-proof: someone who rewrites the whole chain can recompute the hashes unless the latest hash is anchored outside the machine. Anchoring is not built.",
    "The offer checker's warning signs are word patterns. They can miss new wording and can flag harmless words. It has no negation handling yet.",
])

# ----------------------------------------------------------------- 8 setup
doc.add_heading("8. Setup, baskets and the demo price", level=1)
p("The setup screen (#/setup) asks who the prototype is for and starts from one of five baskets. The user can then switch features on or off, and sees the menu and a demo monthly price change live. "
  "The saved choice is one row in SQLite (app_setup). The menu, the home tiles and the route gate all read it. A feature that is not in the list opens the locked page, which adds it in one tap.")
p("Since the last revision, the features on the setup screen and the home tiles are grouped by loss channel (Fraud shield, Credit cost, Investing protection, Reach and trust), "
  "using a group field in backend/setup.py. The groups explain the product; they do not change what a feature does.")

# ----------------------------------------------------------------- 9 recent work
doc.add_heading("9. Recent work and decisions (what changed and why)", level=1)
table(["Change", "Why", "Where"],
      [["Problem reframed around three loss channels; unsourced figures removed", "The product needed one clear problem statement, and a pitch must not rest on numbers without sources", "docs/CONTEXT.md section 2; README"],
       ["Features grouped by loss channel on setup and home", "Makes the scope and the problem visible in the app", "backend/setup.py; frontend setup and home pages"],
       ["Landing page integrated; Explore 5 Baskets opens setup; See how it works opens home", "Front door for the pitch, using the external landing repository", "landing/ (static build served at /landing/); backend and Vite dev-server redirect"],
       ["Dev server sends the root to the landing page and proxies /setup and /landing", "Opening the dev server skipped the landing page; /setup was missing from the proxy list", "frontend/vite.config.ts"],
       ["Recovery drafts readable on the light theme", "Dark-theme colours made the phone script, cybercrime text and bank letter nearly invisible", "frontend/src/styles-recovery.css"],
       ["Offer checker: smooth return score; diminishing flag combination; breakdown", "The score jumped in fixed steps and ignored how large a promise was", "backend/rural.py; Rural page"],
       ["Scam-call rehearsal: theme colours instead of dark-only colours", "Scenario cards, ringing screen and reply buttons were unreadable on the light theme", "frontend/src/styles-practice.css"],
       ["Technical overview and this guide", "Team learning and onboarding", "docs/TECHNICAL_OVERVIEW.md; docs/BUSINESS_DATA_COSTS.md"]],
      widths=[5.6, 6.4, 5])
p("Open UI issue: on narrow windows the floating assistant dock covers content at the bottom right, including the Answer button of the rehearsal and the recovery coach text. It is not fixed. The options are a collapsed dock, or moving it on narrow screens.", size=10)

# ----------------------------------------------------------------- 10 competitors
doc.add_heading("10. Competitor analysis", level=1)
p("Basis: the competitor research in the product brief v2 (public pages and press coverage checked in that revision), extended here. "
  "Competitors are grouped by the job they do for the user. A competitor is a substitute for the job, not just the same kind of app. "
  "Anything not checked in the repository is marked VERIFY.")

doc.add_heading("10.1 Scam protection", level=2)
table(["Player", "What it does", "Where JARVIS differs", "Threat or fit"],
      [["Truecaller (Scam Checker, Scamfeed, Family Protection)", "Blocks and labels calls and messages before they arrive; crowd-sourced caller data", "JARVIS works after the call: explains the script, lets the user rehearse a reply, and orders the first hour when money has gone", "Complement. JARVIS content could be a module for a caller-ID platform"],
       ["Bank SMS alerts and bank apps", "Transaction alerts; in-app card blocking; complaint forms", "Banks show what happened; JARVIS explains what to do and in what order", "Complement; a bank is also a buyer"],
       ["1930 helpline and cybercrime.gov.in", "Official reporting channel; freezes some money if reported fast", "JARVIS is a guide to using them well, in Hindi, with drafts", "Complement; JARVIS points to them"],
       ["Generic scam-awareness content (news, government campaigns)", "Awareness only; no action steps", "Interactive rehearsal and checklist", "Competes for attention; weaker on action"]],
      widths=[3.8, 4.4, 5.2, 3.6])

doc.add_heading("10.2 Investing education and portfolio tools", level=2)
table(["Player", "What it does", "Where JARVIS differs", "Threat or fit"],
      [["Zerodha Varsity", "Free investing course; part of a broker's business", "No product sold; explains the user's own numbers; Hindi on WhatsApp", "Strong on depth; weak on local language and personal numbers"],
       ["Groww (learning inside a trading and fund app)", "Learning content and a broker or fund platform", "Teaches in general, then sends the learner to its own products; JARVIS has no product to sell", "Large distribution; a direct competitor for the first-time investor"],
       ["Fi Money", "Money account with a conversational interface", "JARVIS explains; Fi executes with its own accounts", "Competitive for urban users; not for rural first-time savers"],
       ["ET Money, portfolio trackers, broker consoles", "Holdings and returns across funds", "Not benchmarked feature by feature in the brief. JARVIS adds fee drag in rupees and fund overlap, not a tracker", "VERIFY the feature overlap before any claim"],
       ["Scripbox and similar advisers", "Human or assisted fund advice for a fee", "JARVIS gives no advice; a registered adviser is the right channel for advice", "Different job; a possible partner for an adviser route"]],
      widths=[3.6, 4.2, 5.2, 4])

doc.add_heading("10.3 Rural credit and farmer information", level=2)
table(["Player", "What it does", "Where JARVIS differs", "Threat or fit"],
      [["Kisan Suvidha (government app)", "Weather, market prices, input information for farmers", "JARVIS tells the farmer what a loan really costs and which benefit they are owed", "Complement. The two should link, not compete"],
       ["Bank KCC and SHG loan desks", "Formal credit", "JARVIS compares the informal quote with the formal one, in rupees", "Partner and buyer"],
       ["Informal lenders", "Fast, unregulated cash at high rates", "JARVIS does not replace them; it makes the cost visible at the decision", "The problem itself, not a competitor"],
       ["Credit-score and loan-comparison websites", "Show formal loan options and scores", "JARVIS explains what a score is made of and does not invent one", "Different audience (formal borrowers)"]],
      widths=[3.8, 4.4, 5.2, 3.6])

doc.add_heading("10.4 Group ledgers and self-help groups", level=2)
table(["Player", "What it does", "Where JARVIS differs", "Threat or fit"],
      [["Khatabook", "General business ledger for small traders; large user base", "JARVIS models a self-help group's savings, internal loans, fines and the meeting report; works offline", "Different segment; a source of users for SHG features"],
       ["DigiKhata", "Digital ledger for small shops", "Same difference: a group, not a shop", "Different segment"],
       ["Paper registers and NGO spreadsheets", "The current default for most SHGs", "Digital report, offline, Hindi", "The real competitor: habit and cost of change"]],
      widths=[3.6, 4.6, 5.2, 3.6])

doc.add_heading("10.5 WhatsApp and conversational platforms", level=2)
table(["Player", "What it does", "Where JARVIS differs", "Threat or fit"],
      [["Gupshup, Yellow.ai, Haptik (Jio), Kaleyra (Tata Communications)", "Business messaging and chatbot platforms for banks and brands", "JARVIS is a content and calculation engine that plugs into these rails; it does not compete as a messaging platform", "Partner. They are the channel a bank buys"],
       ["Government WhatsApp services and chatbots", "Official service channels in some states", "VERIFY coverage before any claim", "Possible partner or competitor, depending on the state"]],
      widths=[4.4, 4.4, 5.4, 2.8])

doc.add_heading("10.6 What the competitor picture tells us", level=2)
bullets([
    "No competitor combines all four: after-the-call scam recovery, personal-number checks in Hindi, offline calculators, and an audit trail for institutions. That combination is the wedge, not any single feature.",
    "Most competitors are either channels (Truecaller, banks, WhatsApp platforms) or products to sell (brokers, fund platforms). JARVIS is neither, which is its strength for trust and its weakness for revenue.",
    "The biggest threat is not a product. It is distribution: a platform that adds a Hindi finance module to an existing app with millions of users.",
    "The defensible assets are institutional integrations, verified Hindi content, scheme data kept current, and outcome data from pilots. The code alone is easy to copy.",
    "Several competitor facts above are from the earlier brief and public pages. Feature-level claims need a fresh check before any sales conversation.",
])

# ----------------------------------------------------------------- 11 business
doc.add_heading("11. Business model and how money would come in", level=1)
doc.add_heading("11.1 Who pays and what they buy", level=2)
table(["Payer", "What they buy", "Why they would pay", "Price shape (to validate)"],
      [["Co-operative and rural banks", "White-label WhatsApp and SMS assistant; fraud-recovery coach; credit-cost explainer; Govern and audit for staff", "Fewer fraud complaints; fewer customers lost to informal lenders; compliance trail", "Annual licence per bank or customer band, plus set-up fee. The demo shows ₹499 a month; a placeholder until a bank signs"],
       ["Regional rural banks and small finance banks", "As above, with credit-cost tools tied to their own KCC and SHG products", "Priority-sector targets; lower default risk", "Enterprise licence, per branch count"],
       ["State missions and NGOs", "Field kit: offline pack, group ledger, scheme finder, training in Hindi and regional languages", "Programme outcomes they must report; cheaper than field staff time", "Contract per district per year"],
       ["CSR funds", "Outcome reporting from counts the product really records", "Spend obligations and impact reporting", "Reporting subscription"],
       ["Urban and semi-urban retail investors", "Portfolio X-ray, fund overlap and fee drag, research desk, practice tools", "Clear value on their own money", "Per-feature monthly or yearly subscription (demo shows ₹99 to ₹499)"],
       ["Individuals who have been scammed", "Recovery coach", "Urgent but one-off", "Do not charge at the moment of loss. Keep free"]],
      widths=[3.4, 4.6, 4.4, 4.2])

doc.add_heading("11.2 Why a bank would pay, in plain terms", level=2)
bullets([
    "A fraud on a customer account is a complaint, a reimbursement decision and a reputation cost. A guided first-hour process reduces that burden.",
    "A borrower who understands the cost of a moneylender loan can be moved to a KCC or SHG loan, which is a better-quality book for the bank.",
    "A documented advice trail and limit checks help compliance. The audit record must be described honestly: tamper-evident, not anchored.",
    "The honest caveat: the product does not yet show a measured reduction in losses. A pilot must produce that number before any multi-year contract.",
])

doc.add_heading("11.3 Why an individual can be charged, and when not", level=2)
bullets([
    "Can charge: the retail investor tools, which analyse the person's own holdings, fees and research. Comparable to a budgeting or research app.",
    "Should not charge: rural and scam-protection features. A paywall on fraud protection makes the fraud problem worse. The product's rule is that these stay free.",
    "Legal limit on research: the research desk summarises company data but does not recommend buying or selling. Charging for stock research or advice can require SEBI registration as a Research Analyst or Investment Adviser. Get a written opinion before charging for the research desk or tip checker. Until then, frame the paid tier as a tool subscription, not advice.",
    "Legal limit on lending: the credit-cost comparison is information. Brokering a loan or taking a fee from a lender brings in RBI digital-lending rules. Do not add that without a licence plan.",
])

doc.add_heading("11.4 The advantage, honestly", level=2)
table(["Advantage", "Why it matters", "Limit"],
      [["Deterministic numbers; one function serves the page and the chatbot", "Most AI finance tools cannot make this claim; trust is built on numbers that do not change", "Only as good as the data and the rules; they need upkeep"],
       ["Local-first: speech, models and personal data stay on the machine", "Banks have data rules; the DPDP Act 2023 raises the bar for personal data", "Cloud-based competitors can offer more compute"],
       ["Hindi and English written by hand, with a numbers check", "Machine translation can change a meaning or a figure; rural users need the right words", "Needs ongoing review by field staff"],
       ["First-hour recovery workflow with drafts and helpline routing", "A specific product for a specific urgent moment", "Scam types change; scripts need regular review"],
       ["Audit trail for advisers and banks", "Useful for compliance; a good story for institutions", "Tamper-evident, not anchored; not yet a certified control"],
       ["Free core for the people the problem is about", "Makes partnerships with NGOs and states easier; builds trust", "Does not pay for itself; institutions must pay"]],
      widths=[5.4, 6.2, 5.4])

doc.add_heading("11.5 Pricing structure for a pilot (to validate, not to publish)", level=2)
table(["Tier", "Who", "Structure", "What must be true first"],
      [["Free core", "Everyone", "Rural tools, scam protection, learn, WhatsApp", "Nothing; keep it free"],
       ["Institution licence", "Banks, RRBs, small finance banks", "Annual licence per branch or customer band, plus set-up fee", "A pilot showing fewer complaints or lower credit-cost exposure"],
       ["Programme contract", "State missions, NGOs", "Per district per year, with training", "A signed MoU and a reporting template"],
       ["CSR reporting", "CSR funds", "Annual reporting subscription", "Counts the product really records"],
       ["Investor subscription", "Urban retail", "Per feature, monthly or yearly", "Paying users in a test; a SEBI opinion on research"]],
      widths=[3.2, 3.6, 5.4, 4.8])

doc.add_heading("11.6 Revenue sanity check", level=2)
p("Revenue depends on signed institutions, not on user counts. A thousand free users bring no direct money; one bank contract can be worth far more. "
  "Plan the first year around two or three paid pilots with clear outcome measures, not a user target. The numbers in any model must come from signed terms, not from this guide.")

doc.add_heading("11.7 Go-to-market route", level=2)
bullets([
    "Step 1: an NGO or a co-operative bank as a pilot partner with an agreed outcome measure.",
    "Step 2: field work with the partner's staff, using the offline pack and the group ledger, in one district.",
    "Step 3: a bank or state mission signs a licence or programme contract using the pilot numbers.",
    "Step 4: a channel partnership with a WhatsApp business platform (section 10.5) to reach users at scale.",
    "Step 5: investor subscriptions for the urban segment, once the legal opinion is in hand.",
])

# ----------------------------------------------------------------- 12 costs
doc.add_heading("12. Costs: running and building", level=1)
p("Estimates with stated assumptions. Get written rate cards before any budget. Nothing here is a quote.", italic=True, size=9.5)
doc.add_heading("12.1 Running cost by feature", level=2)
table(["Feature", "Runs on", "External cost per use", "Fixed cost it adds", "Note"],
      [["Assistant (text and voice)", "Local backend; local Whisper and TTS", "None", "Hosting", "Voice needs CPU or GPU"],
       ["Rural tools", "Local, offline-capable", "None", "None", "Offline pack in the browser"],
       ["Is this offer real?", "Local", "None", "None", "Rule-based"],
       ["WhatsApp and SMS", "Backend plus Twilio", "Twilio fee plus WhatsApp conversation fee; VERIFY current rates", "Twilio account, number, approved templates", "Largest per-user cost at scale"],
       ["Scam protection", "Local", "None", "None", "Tip checker needs price history (data licence)"],
       ["Learn", "Local", "None", "None", "Static checked content"],
       ["Portfolio X-ray", "Local", "Price data for holdings", "Data licence", "Works on samples without a licence"],
       ["Research desk", "Local; optional model for desk notes", "Data for the stock; news feed", "Data licence; model hardware if desks are on", "Most data-heavy feature"],
       ["Practice tools", "Local", "None", "Factsheet data when real funds are added", "Current funds are samples"],
       ["Govern and audit", "Local SQLite", "None", "None", "Single-machine trail"]],
      widths=[3.3, 3.6, 3.9, 3.8, 2.6])
doc.add_heading("12.2 Hosting (planning ranges)", level=2)
table(["Option", "Indicative monthly cost", "Can carry"],
      [["Developer laptop", "₹0", "Demos only; not reachable from outside"],
       ["Small VPS (2 vCPU, 4 GB RAM, 50 GB disk)", "About ₹800 to ₹2,000", "Web app for a pilot; text assistant; no heavy voice"],
       ["Same VPS plus GPU instance for speech", "About ₹15,000 to ₹60,000 or more", "Voice at useful speed; price varies widely"],
       ["Managed database and storage (if moving off SQLite)", "About ₹1,000 to ₹5,000", "Multi-user accounts"],
       ["Domain and TLS certificate", "About ₹1,000 a year", "Required for WhatsApp webhooks"]],
      widths=[6, 4.6, 6.2])
doc.add_heading("12.3 Building it as a project (planning ranges)", level=2)
table(["Phase", "Work", "Team (example)", "Cost drivers"],
      [["0. Validation (6 to 8 weeks)", "Pilot agreement; outcome metric; Hindi review by field staff; legal opinion on research and advice", "Product lead; field or language lead; part-time lawyer", "Lawyer fees and staff time"],
       ["1. Hardening (6 to 8 weeks)", "Accounts and login; per-user data; backups; monitoring; security review; Twilio production account and template approval", "Two engineers; designer part-time", "Engineer time; Twilio and approval fees"],
       ["2. Data licensing (start early)", "Licensed Indian market data; NSE data terms; review of news-feed terms", "Business owner", "Licence fees, which vary; get quotes"],
       ["3. Pilot operations (3 to 6 months)", "Field support; Hindi content; scheme upkeep; monitoring", "Field coordinator; engineer part-time", "Team cost and hosting"],
       ["4. Scale-up", "Multi-region hosting; managed database; support desk; compliance reporting", "Grows with contracts", "Funded by pilot revenue"]],
      widths=[3.6, 6.2, 3.8, 3.2])
p("Cost lines not yet priced: data licences, legal and SEBI opinion, security audit, insurance, and translation review. The data licence and legal work are likely to be the largest.", size=10)
p("Bottom line: running the prototype costs almost nothing. Running it as a pilot service costs a small server, a small team, data licences and legal work.", bold=True)

# ----------------------------------------------------------------- 13 legal/risk
doc.add_heading("13. Legal, regulatory and risk points", level=1)
table(["Area", "Point", "Action"],
      [["Investment advice", "Research summaries and tip checking can be read as advice if charged for", "Written SEBI opinion before any charge; keep 'no buy, sell or hold' wording and tests"],
       ["Data licensing", "yfinance (Yahoo) and NSE-derived data have terms that restrict commercial use", "Licensed data feed before any paid use"],
       ["Personal data", "DPDP Act 2023: consent, purpose, security, rights, breach duties", "Privacy notice; consent flow; data-protection review"],
       ["Lending", "Credit-cost comparison is information; brokering a loan brings RBI digital-lending rules", "No lender brokerage without a licence plan"],
       ["Messaging", "WhatsApp business messaging is governed by the provider's terms and templates", "Approved templates; opt-in; provider compliance check"],
       ["Government schemes", "Scheme terms change; wrong information harms the user", "Scheme check before each pilot; last-checked date on each scheme"],
       ["Scam content", "Scam types change; a stale script gives false comfort", "Scheduled review; add a 'last reviewed' date"],
       ["Honesty of claims", "Figures from outside drafts can be wrong; the audit chain is not tamper-proof", "Use only sourced figures; state the audit-chain limit on any slide"],
       ["Accuracy of speech", "Hindi recognition varies by accent and microphone", "Test with real rural speakers before a pilot"],
       ["Product risk", "Free users bring no revenue; institutional sales are slow", "Pilot partner first; outcome measures agreed in writing"]],
      widths=[3.2, 7.2, 6.4])

# ----------------------------------------------------------------- 14 sources
doc.add_heading("14. Sources and what to verify next", level=1)
p("Repository documents used for this guide: docs/CONTEXT.md, docs/DATA.md, docs/ARCHITECTURE.md, docs/TECHNICAL_OVERVIEW.md, docs/BUSINESS_DATA_COSTS.md, docs/FEATURES.md, docs/RURAL.md, docs/MESSAGING.md, docs/VOICE.md, docs/SAFETY_AND_PRIVACY.md, docs/TESTING.md.", size=10)
p("Public sources cited in the product documents (verify before quoting):", bold=True)
bullets([
    "NCFE Financial Literacy and Inclusion Survey 2019 (ncfe.org.in).",
    "I4C and NCRP cyber-fraud figures; use the official I4C release, not a summary.",
    "SIDBI study on informal sector lending practices, 2019 (sidbi.in).",
    "SEBI Investor Survey 2025 (sebi.gov.in).",
    "RBI Basic Statistical Returns (rbi.org.in).",
    "NITI Aayog and Central Statistics Office estimates on rural GDP.",
    "Income Tax Act: Sections 111A and 112A, and the latest Finance Act (incometax.gov.in).",
    "Government scheme portals listed in section 6.2.",
    "DPDP Act 2023 (MeitY).",
])
p("Verify next, in this order:", bold=True)
bullets([
    "Data licence terms for yfinance, NSE data and the news feeds.",
    "Written SEBI opinion on the research desk and tip checker.",
    "Current Twilio and WhatsApp rate cards for India.",
    "Every scheme portal and rate in the rural tools, with a last-checked date.",
    "The official I4C figures and the SEBI survey numbers before any pitch.",
    "Replace the eight sample funds with AMC disclosures.",
])

# ----------------------------------------------------------------- glossary
doc.add_heading("Glossary", level=1)
table(["Term", "Meaning in this project"],
      [["APR", "Annual percentage rate. 5% a month is 60% a year on simple interest."],
       ["KCC", "Kisan Credit Card, a farm credit product from banks."],
       ["SHG", "Self-help group; a savings and credit group, often of women."],
       ["NCRP / 1930", "National Cyber Crime Reporting Portal and the national cyber-fraud helpline."],
       ["Golden hour / first hour", "The period after a fraudulent transfer in which reporting gives the best chance of freezing funds."],
       ["Point-in-time", "A data store that shows only what was public on a given date, so no figure sees the future."],
       ["First-passage probability", "The chance a price touches a level within a time, from its volatility (used in the tip panel)."],
       ["Fee drag", "The share of long-run growth a fund's annual fee takes away."],
       ["Hash chain", "Each audit entry stores a hash of the previous entry; changing one entry breaks the chain after it."],
       ["Tamper-evident", "Changes are detectable. Not the same as tamper-proof, which would need external anchoring."],
       ["Basket", "A starting setup for one audience in the prototype's setup screen."],
       ["DPDP Act 2023", "India's Digital Personal Data Protection Act."],
       ["Red team", "An analyst whose job is to argue against the consensus."],
       ["Offline pack", "The app shell and the rural calculators cached so they run without a network."]],
      widths=[4, 12.2])

doc.save(OUT)
print("saved", OUT)
