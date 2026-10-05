"""Builds JARVIS_Product_Brief.docx (python-docx). Run tools/brief_figures.py first."""
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "docx_assets" / "brief"
GOLD, INK, MUTE = RGBColor(0xB8, 0x76, 0x0A), RGBColor(0x1D, 0x1B, 0x16), RGBColor(0x6B, 0x67, 0x5C)

d = Document()
sec = d.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.1)
sec.top_margin, sec.bottom_margin = Cm(2.0), Cm(1.9)

st = d.styles["Normal"]
st.font.name, st.font.size = "Calibri", Pt(10.5)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
st.paragraph_format.space_after, st.paragraph_format.line_spacing = Pt(5), 1.12
for name, size, col in (("Heading 1", 20, GOLD), ("Heading 2", 14, INK), ("Heading 3", 11.5, GOLD)):
    h = d.styles[name]
    h.font.name, h.font.size, h.font.bold, h.font.color.rgb = "Cambria", Pt(size), True, col
    h.element.rPr.rFonts.set(qn("w:eastAsia"), "Cambria")
    h.paragraph_format.space_before, h.paragraph_format.space_after, h.paragraph_format.keep_with_next = Pt(14 if name != "Heading 3" else 8), Pt(5), True


def shade(cell, hexcol):
    tcPr = cell._tc.get_or_add_tcPr()
    s = OxmlElement("w:shd"); s.set(qn("w:val"), "clear"); s.set(qn("w:color"), "auto"); s.set(qn("w:fill"), hexcol); tcPr.append(s)


def borders(table, color="D8D0BC"):
    tbl = table._tbl
    pr = tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{e}"); el.set(qn("w:val"), "single"); el.set(qn("w:sz"), "4"); el.set(qn("w:color"), color); b.append(el)
    pr.append(b)


def P(text="", bold=False, italic=False, size=None, color=None, align=None, after=None, style=None):
    p = d.add_paragraph(style=style)
    if text:
        r = p.add_run(text); r.bold, r.italic = bold, italic
        if size: r.font.size = Pt(size)
        if color: r.font.color.rgb = color
    if align: p.alignment = align
    if after is not None: p.paragraph_format.space_after = Pt(after)
    return p


def rich(text, style=None):
    """**bold** segments inside a paragraph."""
    p = d.add_paragraph(style=style)
    for i, seg in enumerate(text.split("**")):
        if seg:
            r = p.add_run(seg); r.bold = i % 2 == 1
    return p


def H(t, l=1):
    h = d.add_heading(t, level=l)
    if l == 1 and t not in ("Contents", "1. The idea in one page") and not t.startswith(("10.", "13.", "14.", "Appendix A")) and not t.startswith("Appendix B") and not t.startswith("Appendix C") and not t.startswith("Appendix D"):
        h.paragraph_format.page_break_before = True
    return h


def B(items):
    for t in items:
        p = rich(t, "List Bullet"); p.paragraph_format.space_after = Pt(2)


def T(rows, widths, head=True, size=9, zebra=True):
    t = d.add_table(rows=len(rows), cols=len(rows[0]))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    borders(t)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j); c.width = Cm(widths[j])
            c.paragraphs[0].paragraph_format.space_after = Pt(1)
            for k, seg in enumerate(str(val).split("**")):
                if seg:
                    r = c.paragraphs[0].add_run(seg); r.font.size = Pt(size); r.bold = (head and i == 0) or k % 2 == 1
                    if head and i == 0: r.font.color.rgb = RGBColor(255, 255, 255)
            if head and i == 0: shade(c, "2A2C31")
            elif zebra and i % 2 == 0: shade(c, "FAF6EA")
    d.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def callout(title, text, fill="FFF4D8"):
    t = d.add_table(rows=1, cols=1); t.alignment = WD_TABLE_ALIGNMENT.CENTER; borders(t, "E0C47A")
    c = t.cell(0, 0); shade(c, fill); c.width = Cm(16.6)
    p = c.paragraphs[0]; r = p.add_run(title + "  "); r.bold = True; r.font.color.rgb = GOLD
    for i, seg in enumerate(text.split("**")):
        if seg:
            r = p.add_run(seg); r.bold = i % 2 == 1
    d.add_paragraph().paragraph_format.space_after = Pt(2)


_fig = [0]


def F(name, caption, w=16.2):
    import re
    _fig[0] += 1
    caption = f"Figure {_fig[0]}. " + re.sub(r"^Figure\s*\d*\.?\s*", "", caption)
    p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.keep_with_next = True; p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(str(FIG / name), width=Cm(w))
    c = P(caption, italic=True, size=8.8, color=MUTE, align=WD_ALIGN_PARAGRAPH.CENTER, after=8)


def pagebreak():
    d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# footer page numbers
fp = sec.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = fp.add_run("Jarvis, money plainly  |  Product brief  |  page "); r.font.size = Pt(8.5); r.font.color.rgb = MUTE
for tag, txt in (("begin", None), (None, "PAGE"), ("end", None)):
    rr = fp.add_run(); rr.font.size = Pt(8.5)
    if tag:
        e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), tag); rr._r.append(e)
    else:
        e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = txt; rr._r.append(e)

# =============================================================================================== cover
for _ in range(5): P()
P("JARVIS", bold=True, size=44, color=GOLD, after=0)
P("money, plainly", italic=True, size=22, color=INK, after=14)
P("A free, local, bilingual financial-protection platform for India, built first for the people the financial system serves least.", size=13, color=MUTE, after=26)
T([["What it is", "A guard, a guide and a calculator for everyday money: it checks scams and loan costs, finds government benefits, explains investing, researches a stock in plain words and keeps an honest record."],
   ["Who it is for", "75% of the effort: underprivileged and rural families.  20%: retail and middle-class investors.  5%: affluent users and advisers."],
   ["Where it stands", "A working prototype: web app, WhatsApp/SMS simulator, Hindi voice, offline pack, 25 guided tours, 520 automated tests."],
   ["Document", "Product, users, technology, business and roadmap in one brief. Prepared for the Drishti AI hackathon review."]], [3.2, 13.4], head=False, size=10)
pagebreak()

# =============================================================================================== contents
H("Contents")
T([["1", "The idea in one page"], ["2", "The problem we are solving, and for whom"], ["3", "Who uses it: the 75 / 20 / 5 design"], ["4", "How the platform works"],
   ["5", "Features for the underprivileged majority"], ["6", "Features for retail and middle-class users"], ["7", "Features for affluent users and advisers"],
   ["8", "Shared foundations: understanding, tours, charts, trust"], ["9", "Five flagship features in depth"], ["10", "A day in the life: three users, one platform"], ["11", "Complete feature catalogue"], ["12", "Technical deep dive"],
   ["13", "Where the prototype stands today"], ["14", "How we are different"], ["15", "Taking it to market: the business"], ["16", "Risks, compliance and ethics"],
   ["17", "Roadmap, measures of success and what we added"], ["A", "Demo script, FAQ, glossary and sources"]], [1.2, 15.4], head=False, size=10.5)
P("Figures quoted about India are public, rounded and indicative. Check them against the latest official release before using them outside this brief.", italic=True, size=9, color=MUTE)

# =============================================================================================== 1 idea
H("1. The idea in one page")
callout("Main idea", "**Put a trustworthy money adviser, a scam shield and a government-benefits finder in the hands of people who have never had one, in their own language, on the phone they already own, at no cost to them.** Everything else in the platform is an add-on that extends the same engine to people with more money and more complex needs.")
H("Abstract", 2)
rich("Most Indians make money decisions alone. A farmer decides whether a moneylender's '5 rupees per hundred' is fair. A daily-wage family decides whether an agent's policy is worth paying for. A first-time investor decides whether a Telegram tip is real. They do it with no adviser, little time and in a language the financial industry rarely speaks. The cost is large and invisible: interest rates that are really 60% a year, savings lost to fraud, benefits never claimed.")
rich("Jarvis is one platform that answers those questions plainly. It reads a question the way a person asks it (typed or spoken, Hindi or English), picks the right tool, works the answer out with deterministic code and shows it as a clear card with the figures, the steps and, where useful, a chart. For people who cannot or do not want to use an app, the same tools run as a WhatsApp or SMS conversation. For people with savings, the same engine explains funds, fees, tax and risk, researches a company and enforces their own risk limits.")
rich("The design rule is **accuracy over fluency**: no figure is ever produced by a language model; every number comes from a calculator or from dated public data, and the screen says how old that data is and how much each point can be trusted. Nothing says buy or sell. The decision stays with the person.")
H("The three promises", 2)
T([["Promise", "What it means in practice"], ["Protect", "Spot a scam, a bad loan or a missed benefit before it costs money; and tell a person exactly what to do in the first hour if it already has."],
   ["Explain", "Answer the real question asked, in plain words, with the working shown, in the person's language, spoken or written."],
   ["Stay honest", "Free, local and private by design; no hidden numbers; a record of every decision that cannot be quietly edited."]], [3.3, 13.3])
F("audience.png", "Figure 1. The design weighting. The 75/20/5 split is how effort and features are prioritised, not a measured customer count.", 12.5)

# =============================================================================================== 2 problem
H("2. The problem we are solving, and for whom")
rich("India has built world-class payment rails (UPI) and a huge base of bank accounts, but understanding has not kept pace. Surveys of financial literacy have repeatedly found only about a quarter of adults able to answer basic questions on interest, inflation and risk (the 2019 national survey put it near 27%). Meanwhile digital fraud has grown with digital payments, and a national cyber-fraud helpline (1930) exists because the volume is high. The result is a gap between access and safe use.")
F("problems.png", "Figure 2. Seven problems people actually live with, and the part of the platform that answers each.")
H("Problems in more detail", 2)
T([["Problem", "Who suffers", "Why it persists", "Our answer"],
   ["Moneylender interest is quoted per month, per hundred", "Farmers, daily-wage workers, small traders", "No one converts it to a yearly figure; '5 per hundred' sounds small (it is 60% a year)", "Moneylender check: yearly cost, rupees paid, comparison with a bank loan"],
   ["Scams by call, SMS, group chat", "Everyone, but loss hurts most when savings are small", "Urgency and secrecy; no one to ask; same reply for every scam from most tools", "Nine scam scripts, rehearsal, recovery coach, UPI and offer checks"],
   ["Government benefits unclaimed or stuck", "Rural and urban poor, pensioners, students", "Eligibility is scattered; Aadhaar-bank seeding errors; no tracing tool", "Schemes finder, papers checklist, 'why no money?' payment tracer"],
   ["Irregular income", "Farm families, casual labour", "Budget tools assume a monthly salary", "Plan-my-year, sell-or-hold, daily saving, SHG ledger"],
   ["Language and access", "Hindi-first, low-literacy, feature-phone users", "Fintech is English, app-based, data-hungry", "Hindi voice, WhatsApp/SMS, offline pack, shared-device kiosk"],
   ["Investing without understanding", "First-time and middle-class investors", "Fees, overlap, tax and risk are hidden; influencers fill the gap", "Fee drag, overlap, tax shield, plain research summary, concept answers"],
   ["No enforceable discipline", "Serious investors, family offices, advisers", "Limits live in spreadsheets and can be overridden or edited", "Risk firewall, hash-chained audit record, attribution"]], [3.6, 3.4, 4.7, 4.9], size=8.4)

H("The size of the gap", 2)
T([["Indicator (rounded, public)", "What it says", "Why it matters here"],
   ["About 1.4 billion people, roughly two-thirds in rural areas", "Most Indians live where branches, advisers and English are scarce", "A rural-first design reaches the largest group"],
   ["Over 50 crore Jan Dhan accounts; UPI runs well over 15 billion payments a month", "Access and digital payments are widespread", "Safe use, not access, is the gap"],
   ["Financial literacy near 27% of adults (2019 national survey)", "Most adults cannot answer basic interest, inflation and risk questions", "Plain explanation is the unmet need"],
   ["About 9-10 crore women in roughly 90 lakh self-help groups", "Trusted local savings networks already exist", "Natural distribution channel and a ledger need"],
   ["Around 5 lakh Common Service Centres", "Village-level digital service points", "Shared-device and kiosk deployment"],
   ["Demat accounts well above 15 crore", "A fast-growing first-time investor base", "The 20% needs fee, risk and tip-checking help"]], [5.6, 5.6, 5.4], size=8.4)
P("Indicative figures from public releases (government, regulators, payment and depository bodies). Verify against the latest release before external use.", italic=True, size=8.5, color=MUTE)

# =============================================================================================== 3 users
H("3. Who uses it: the 75 / 20 / 5 design")
rich("The platform is organised around three groups. The percentages describe where design and engineering effort is directed. They are a deliberate bias toward the underprivileged majority, because that is where a free, honest tool changes the most outcomes per rupee.")
T([["Group", "Who", "Typical need", "How they meet the platform", "Main features"],
   ["**75%** Underprivileged and rural", "Farm and wage families, SHG women, pensioners, first-time borrowers, migrant workers", "Is this loan fair? Is this a scam? What am I owed? Why has my money not come?", "WhatsApp or SMS, Hindi voice, shared phone or CSC kiosk, offline", "Twelve rural tools, scam shield, WhatsApp menu, voice, offline pack"],
   ["**20%** Retail and middle class", "Salaried families, small investors, gig workers, students", "Am I paying too much in fees? Is my money spread? Is this stock or fund sensible? What tax will I pay?", "Web app on phone or laptop; assistant; research page", "Portfolio X-ray, fee drag, overlap, tax shield, research desk, concept answers"],
   ["**5%** Affluent and advisers", "Active investors, family offices, small advisers", "Keep concentration within limits; prove what was decided and when; see where returns came from", "Govern page, reports, audit trail", "Risk firewall, audit chain, attribution, time machine, multiple portfolios"]], [2.6, 3.2, 3.8, 3.4, 3.6], size=8.4)
H("Three people, three journeys", 2)
T([["", "Sunita, 38 (rural, SHG member)", "Rakesh, 29 (salaried, first investor)", "Meera, 54 (affluent investor)"],
   ["Starting point", "Borrowed Rs 50,000 from a local lender at 5 rupees per hundred a month; has a basic smartphone with WhatsApp", "Saving Rs 8,000 a month; follows a Telegram group promising 20% returns", "Holds 14 stocks and four funds; wants discipline and a record for her adviser"],
   ["What she or he does", "Sends 'sahukar 5 rupaye sainkda' by voice note", "Pastes the tip into the tip checker, then asks 'SIP or lump sum?'", "Sets limits in Govern, checks a trade, reads attribution"],
   ["What the platform does", "Replies: 60% a year, Rs 30,000 interest; offers the schemes finder and papers checklist", "Flags guaranteed-return and urgency tactics; explains SIP vs lump sum with a table; opens fee drag", "Blocks a trade that breaches her 35% industry limit and writes it to the audit chain"],
   ["Outcome", "Knows the true cost; finds a scheme she qualified for; later keeps the group ledger", "Avoids the group; starts an index-fund SIP", "Decisions she can defend and prove"]], [2.6, 4.7, 4.7, 4.6], size=8.4)

# =============================================================================================== 4 how it works
H("4. How the platform works")
rich("A person asks. The platform reads the whole sentence, decides what kind of request it is, runs the right tool or opens the right checked explanation, and shows the result as a structured card. The figure below follows one question from start to finish.")
F("journey.png", "Figure 3. The journey of a question. The same path serves the web app, the voice orb and the WhatsApp/SMS channel.")
H("The five kinds of request", 2)
T([["Kind", "Example", "What happens"], ["About the app", "'How do I use the fee slider?'", "A structured answer plus a guided tour: the page opens, each part lights up, the caption is read aloud"],
   ["A company", "'Analyse TCS', 'compare Reliance and HDFC Bank'", "Facts, good points and watch-outs with confidence marks, peer ranks and a live or saved chart"],
   ["General money", "'SIP or lump sum?', 'How are mutual funds taxed?'", "A checked, hand-written explanation in English or Hindi, with a table and a next step"],
   ["Your numbers", "'What does a 2% fee cost over 20 years?'", "A deterministic calculator; the card shows the result and the working"],
   ["Scam or rural money", "'Someone from the bank asked for my OTP'", "The script that matches what was described, or the rural tool with its inputs"]], [3.0, 5.4, 8.2], size=8.8)
H("Why the answers can be trusted", 2)
F("trust.png", "Figure 4. The trust pipeline. A language model never sits between the data and the number.", 15.5)
B(["**Deterministic numbers.** Interest, fees, goals, tax and ratios are computed in code that is unit-tested (520 tests).",
   "**Dated data.** Every price and statement carries the date it was fetched; the Research page shows how old each kind of data is and how many checks had data at all.",
   "**Confidence on every point.** Each good point or watch-out is marked solid, light or weak depending on how many independent kinds of data it rests on, its sample size and its age.",
   "**Honest gaps.** Missing data appears under 'what we could not check' (for example promoter share pledging), never guessed.",
   "**No advice.** The platform describes; it does not say buy, sell or hold."])
F("whatsapp.png", "Figure 5. The same tool over WhatsApp. A person sends a sentence or a voice note and gets the same answer as the web app.", 14.5)

# =============================================================================================== 5 majority
H("5. Features for the underprivileged majority")
rich("This is the heart of the platform. Every feature here is designed for a person with limited time, limited data, limited English and no adviser. All of it runs offline or on a basic connection and is available in Hindi.")
H("Rural money tools (twelve)", 2)
T([["Tool", "Use case", "What it gives", "Who it helps"],
   ["Moneylender check", "A local lender charges '5 rupees per hundred'", "True yearly rate, rupees paid, comparison with a bank loan", "Borrowers in debt traps"],
   ["Credit score guide", "Loan rejected, or no credit history", "What a score is, why a loan fails, how to build one", "First-time borrowers"],
   ["Is this offer real?", "Double-your-money, chit fund, pay-and-earn", "Red-flag check with reasons", "Anyone approached by an agent"],
   ["UPI safety", "Collect request, QR to 'receive' money, refund call", "Which tricks apply and what to do", "New UPI users"],
   ["Is my policy good?", "Agent-sold endowment or bonus-refund plan", "Real yearly return versus term plus saving", "Insurance buyers"],
   ["My government schemes", "Which benefits might I qualify for?", "Short list with reasons", "Poor households"],
   ["Are my papers ready?", "Documents for a scheme or loan", "Checklist, Aadhaar-bank seeding hints", "Applicants"],
   ["Why no money?", "Pension or subsidy has not arrived", "Likely causes in order, and the fix", "DBT beneficiaries"],
   ["Plan my year", "Income arrives at harvest", "Month-by-month plan around lean months", "Farm families"],
   ["Sell or hold?", "Wait for a better mandi price?", "Break-even price after storage cost and interest", "Farmers"],
   ["Daily saving", "Rs 20 a day for a daughter's wedding", "What small daily savings become, with the working", "Low-income savers"],
   ["Group ledger", "SHG savings, loans, fines, repayments", "Interest, who owes what, meeting report, member statements", "SHG women and federations"]], [3.2, 4.4, 5.2, 3.8], size=8.4)
H("Scam protection (nine scripts)", 2)
rich("Scams are not one thing, so the answer is not one thing. The platform recognises nine scripts and answers each with what the caller says, what is actually true and the first steps for that scam. After a loss, a recovery coach orders the first hour: freeze, call 1930, report on cybercrime.gov.in, and what not to do (never pay again to 'recover' money).")
T([["Script", "The tell", "First step"], ["Bank OTP / KYC", "Asks for OTP, PIN or CVV; deadline of minutes", "Hang up; call the number on your card"],
   ["Digital arrest", "Police or CBI on video call; keep it secret; move money", "Hang up; tell family; report on 1930"],
   ["Courier parcel", "Parcel with drugs; customs fee; press 1", "Do not press or pay; check the courier site"],
   ["Remote app", "Install AnyDesk or a support app", "Uninstall; change passwords from another device"],
   ["Task job", "Earn per like or task, then pay to unlock", "Stop paying; keep receipts; report"],
   ["Loan app threats", "Fee first, contacts and photos access, morphed pictures", "Uninstall, revoke permissions, report"],
   ["Prize / lottery", "Pay a fee to release a prize", "Ignore, block, report if paid"],
   ["SIM / electricity", "Disconnection tonight unless you call", "Check the bill on the provider's own app"],
   ["Investment group", "Guaranteed returns, VIP group, app shows fake profit", "Stop sending money; check SEBI registration"]], [3.4, 7.2, 6.0], size=8.6)
H("Reaching people without an app", 2)
B(["**WhatsApp and SMS.** A numbered menu of fourteen options, one question at a time, text or voice note, Hindi or English. The simulator in the app is the exact conversation a real number would have; connecting a real number is a Twilio webhook.",
   "**Hindi voice.** Speech is turned into text on the same machine, shown back as 'I heard...' so a mishearing is fixed before it is answered, and answers can be read aloud.",
   "**Offline pack.** The app and the Python calculators are saved in the browser (Pyodide), so a village with no signal still has every tool.",
   "**Kiosk mode.** On a shared phone or a Common Service Centre screen, one tap wipes the previous person's answers before the next person starts.",
   "**Guided tours.** Every feature can be walked through on screen with a spoken caption, so someone who cannot read well can still learn the tool by watching it."])

H("The WhatsApp / SMS menu", 2)
T([["No.", "Option", "No.", "Option"], ["1", "Check a moneylender's interest", "8", "Will my savings reach my goal?"], ["2", "Is an offer or scheme real?", "9", "Credit score: why was my loan rejected?"],
   ["3", "Government schemes I can get", "10", "Save a little every day for a goal"], ["4", "Are my papers ready?", "11", "Sell my crop now or wait?"],
   ["5", "Plan my money around harvest", "12", "Why has my government payment not come?"], ["6", "What does a fund fee cost?", "13", "Is this UPI request or QR safe?"],
   ["7", "How long will my savings last?", "14", "Is my insurance policy a good deal?"]], [1.2, 7.1, 1.2, 7.1], size=8.8)
P("Also: CANCEL stops a task, MENU shows the list, and sending the Hindi or English word switches language. Each reply asks one thing at a time and ends with the next step.", italic=True, size=9, color=MUTE)

# =============================================================================================== 6 retail
H("6. Features for retail and middle-class users")
rich("People with some savings meet a different problem: too many products, hidden costs and loud advice. The platform gives them clarity, not tips.")
T([["Feature", "Use case", "How it works", "Benefit"],
   ["Portfolio X-ray", "'Am I in good shape?'", "Grade out of 100 against limits for the investor type; spread, biggest industry, worst fall, market sensitivity; every number clickable to its working", "A plain verdict and where to look next"],
   ["Allocation map and chart", "See where the money sits", "Treemap by industry and company; 'what this basket would have done' versus the index", "Spot concentration in seconds"],
   ["Fee drag", "What does a 2% fee cost?", "Lump sum, SIP, years, return and two fees; chart of cheap fund, your fund and no fee", "Makes a small number visible"],
   ["Fund overlap", "Do my funds hold the same stocks?", "Pick two funds; shared holdings light up; overlap percentage", "Avoids paying twice"],
   ["Emergency meter", "How many months would I last?", "Cash, spending, continuing income; ring against a six-month target", "A concrete safety number"],
   ["Tax shield", "What does selling today cost in tax?", "Per holding: days held, gain, tax now, days to the one-year mark", "Better timing, never guessed cost"],
   ["Panic-sell replay", "What if I had sold in the crash?", "Real crash prices applied to the person's holdings", "Behaviour change"],
   ["Research desk", "Is this company sound?", "Four analysts and a sceptic study it; claims must cite evidence; plain-words summary", "Fundamentals, not just price"],
   ["Weekly digest", "One-minute update", "Spoken summary built from the person's data", "Habit without effort"],
   ["Concept answers", "SIP vs lump sum, tax, gold, EMI...", "32 checked explanations in English and Hindi with tables", "Learning in context"]], [3.0, 3.6, 6.3, 3.7], size=8.3)
H("The plain-words research summary", 2)
rich("The Research page is where the platform goes beyond price and chart. For any listed company it reads growth, cash conversion and free cash flow, debt and interest cover, liquidity, dividends, two standard financial-health scores, the company's own past valuation range, growth-adjusted valuation, peer rank on five measures, and ownership. It also reads trend, momentum, volume and relative strength, capped so one price fact is not counted four times. Each line carries a basis and a confidence mark, and the page shows how current each kind of data is.")
F("ui_stock.jpg", "Figure 6. A company answer in the chat: key figures, a live chart, good points and watch-outs with confidence marks.", 15.2)

# =============================================================================================== 7 affluent
H("7. Features for affluent users and advisers")
rich("The smallest group, the 5%, is served by the same engine, with the parts that matter most to people who manage larger or more complex portfolios.")
T([["Feature", "What it does", "Why it matters"],
   ["Risk firewall", "Checks any trade against per-stock, per-industry and cash limits using plain arithmetic; offers the largest compliant size", "No analyst, model or button can talk it into a bad order"],
   ["Hash-chained audit record", "Every decision, approved or blocked, is written to a chain where each row carries a fingerprint of the previous one", "A quiet edit breaks the chain and is caught; useful for advisers and family offices"],
   ["Tamper test", "Edits one old entry in a copy and shows the chain pointing to it", "Proves the record to a sceptical reader"],
   ["Rebalance simulator", "Builds the smallest set of trades that restores limits; 'only sell' option", "Fixes a breach with minimum turnover"],
   ["Attribution", "Splits a move into per-holding and per-sector contributions and allocation versus selection effect", "Answers 'where did the return come from?'"],
   ["Time machine", "Rewinds the clock so analysts only see what was known on that day", "Tests whether an analysis would have helped, without hindsight"],
   ["Multiple portfolios and reports", "Preset or pasted portfolios; printable report", "Family and client views"],
   ["Calibration", "Scores each analyst desk against realised returns (hit rate, Brier score)", "Shows which desks are worse than a coin flip"]], [3.6, 7.2, 5.8], size=8.5)
F("ui_tour.jpg", "Figure 7. A guided tour on the Govern page: the spotlight shows the part being explained and the caption is read aloud.", 14.5)

# =============================================================================================== 8 shared
H("8. Shared foundations")
H("Understanding the whole question", 2)
rich("Earlier assistants matched a keyword: any message with 'scam' got the same scam reply. The understanding layer reads the whole sentence first. It separates questions about the app, requests about companies, general money questions and personal calculations, and only then picks the tool. A local model, if used, can only choose from a fixed list; it writes nothing.")
H("Guided tours", 2)
rich("Twenty-five tours cover every area. Ask 'help me understand this feature' and the platform opens the page you are on, presses the tab, spotlights each part in turn and reads the caption in your language, with Back, Next, Auto and Esc controls. The tour is the same content as the text answer, so what is shown and what is said never disagree.")
F("ui_compare.jpg", "Figure 8. Comparing two companies on one chart, every line rebased to 100 on the same start date.", 14.5)
H("Charts from online sources", 2)
rich("Company charts are fetched live from Yahoo Finance when the machine is online and read from the saved snapshot when it is not, labelled either way with the source and the date of the last close. A TradingView tab offers a fully interactive live chart. The 50- and 200-day averages, range buttons and a hover read-out are built in.")
H("Language, theme and accessibility", 2)
B(["English and Hindi throughout, written by hand (no machine translation of answers or tours).", "Light and dark themes; layouts work at phone width with no sideways scrolling.", "Voice in and out, with an always-visible stop; captions for every spoken line.", "Question and answer shown as one block so it is always clear what an answer answers, whether the question was typed or spoken."])
F("ui_mobile.jpg", "Figure 9. The assistant on a phone in the light theme: example questions grouped by need, message box docked at the bottom.", 6.2)

# =============================================================================================== 9 deep dives
H("9. Five flagship features in depth")
H("9.1 The moneylender check: making a hidden cost visible", 2)
rich("'Five rupees per hundred' is how most informal credit is quoted. It sounds small, so the real cost goes unquestioned. The tool turns it into the yearly rate, the rupees paid and the comparison with a bank loan, in Hindi or English, by text or voice note.")
F("lender.png", "Figure 6. The same loan quoted per month and per year. A 5-rupee rate costs 60% a year; on Rs 50,000 that is Rs 30,000 of interest (simple interest, before compounding).", 13.8)
T([["Step", "What the person does", "What the platform shows"], ["1", "Types or says: 'sahukar 5 rupaye sainkda, 50,000'", "Understands the rate, the amount and the months from the sentence, in Hindi or English"],
   ["2", "Confirms the numbers", "Asks only for what is missing, one question at a time"], ["3", "Reads the result", "60% a year; Rs 30,000 a year; what a 12% bank loan would cost instead"],
   ["4", "Optional", "Opens the schemes finder and papers checklist to look for cheaper credit"]], [1.6, 6.2, 8.8], size=8.8)
H("9.2 Scam recovery: the first hour", 2)
rich("When money has already gone, speed decides whether a bank can freeze it. The coach asks what happened and orders the steps by time. Every answer includes 'none of this is your fault' and warns against the second scam: paying a 'recovery agent'.")
F("recovery.png", "Figure 7. The recovery timeline the coach follows.", 14.2)
H("9.3 The plain-words research summary", 2)
rich("A company is judged on more than its price. The summary reads fundamentals, valuation in context, ownership and the chart, and then shows how much to trust each line.")
T([["Layer", "Examples of what is read", "How it appears"],
   ["Growth", "Sales and profit growth, three-year sales growth", "Good point or watch-out with the figure and its age"],
   ["Cash and safety", "Cash conversion, free cash flow, debt, interest cover, liquidity, distress and quality scores", "Banks skip debt-type measures and the page says why"],
   ["Valuation in context", "Price against profit versus peers and versus the company's own past range; growth-adjusted valuation", "Peer rank bars, with the number of peers"],
   ["Ownership", "Insider and institutional share; trend once two snapshots exist; pledging flagged as not available", "Honest 'could not check' list"],
   ["Price behaviour", "Trend against 50- and 200-day averages, momentum, volume, distance from the year's range", "Capped at three so one price fact is not counted several times"],
   ["Trust", "Basis, sample size, data age, number of checks that had data", "Solid / light / weak mark on every line"]], [3.2, 7.0, 6.4], size=8.4)
H("9.4 The risk firewall and the audit chain", 2)
rich("Limits are only useful if they cannot be argued with. The firewall checks every trade against per-stock, per-industry and cash limits with plain arithmetic, and writes every decision to a chain in which each row carries the fingerprint of the previous one.")
F("chain.png", "Figure 8. A hash-chained record. Changing any past entry breaks every fingerprint after it.", 14.2)
H("9.5 Guided tours: learning a feature by watching it", 2)
rich("A tour is a list of steps: open this page, press this tab, spotlight this part, say this. The same list drives the text answer, so the words on screen and the words spoken never disagree. A ghost pointer shows how a button is pressed, which matters for people who learn by seeing. Tours exist for the whole app, each page, and each tool, and 'this feature' always means the page that is open.")
F("ui_tour.jpg", "Figure 9. A tour step on the Govern page.", 14.0)

# =============================================================================================== 10 day in life
H("10. A day in the life: three users, one platform")
T([["Time", "Sunita (rural, 75%)", "Rakesh (salaried, 20%)", "Meera (affluent, 5%)"],
   ["Morning", "Gets an SMS-style prompt on WhatsApp; asks by voice note whether her pension instalment is delayed", "Reads his weekly digest on the way to work", "Opens the Govern page: limits are green except one industry"],
   ["Midday", "Learns the Aadhaar-bank seeding step is missing; follows the papers checklist at the village centre", "Sees a tip in a group; pastes it into the tip checker", "Checks a proposed trade; the firewall blocks it and offers a smaller size"],
   ["Evening", "SHG meeting: updates the group ledger; prints member statements", "Asks 'SIP or lump sum?' and opens fee drag", "Reads attribution: technology cost 1.4 points last quarter"],
   ["Night", "Rehearses the 'bank KYC' scam call with her daughter", "Compares two funds for overlap", "Exports the audit record for her adviser"]], [1.8, 5.0, 4.9, 4.9], size=8.4)
rich("The same engine serves all three. What changes is the channel, the language, the depth and who pays.")

H("Who benefits, and how", 2)
T([["Stakeholder", "How they benefit", "What they see"],
   ["Underprivileged families", "Pay less interest, avoid fraud, claim benefits, plan lumpy income", "True cost of a loan, a scam refused, a scheme found, a payment traced"],
   ["Women's self-help groups", "Honest group accounts, member statements, meeting reports", "A ledger that works offline and in Hindi"],
   ["Retail and middle-class investors", "Lower fees, less duplication, better tax timing, fewer tip-driven mistakes", "Fee drag, overlap, tax shield, plain research with confidence marks"],
   ["Affluent investors and advisers", "Enforced limits and a provable record", "Firewall verdicts, audit chain, attribution"],
   ["Banks, co-operatives, MFIs", "Fewer fraud losses and complaints; better outreach to first-time customers", "A white-label shield and a messaging channel"],
   ["Government missions and NGOs", "Higher scheme uptake and measurable literacy outcomes", "An impact dashboard from the pilot onward"],
   ["Society", "Less money lost to fraud and predatory credit; more trusted advice", "Stronger household balance sheets"]], [4.0, 6.8, 5.8], size=8.5)
H("Why now", 2)
B(["Payments are digital but safe use lags, and fraud rises with every new user.", "WhatsApp and voice notes are already how many first-time smartphone users communicate.", "Local speech recognition and small local models are now good enough to run on one machine.", "Regulators and banks are under pressure to show financial-inclusion outcomes and reduce fraud."])

# =============================================================================================== 11 catalogue
H("11. Complete feature catalogue")
F("matrix.png", "Figure 10. Which feature matters to which group (core, good, some). The majority-first bias is visible in the top rows.", 14.8)
T([["Area", "Feature", "Use case", "Problem it solves", "Primary user"],
   ["Assistant", "Chat + voice orb", "Ask in words or speech", "Hard to find the right tool", "All"],
   ["Assistant", "Guided tours (25)", "Learn a feature by watching it", "Training cost, low literacy", "All"],
   ["Assistant", "Concept answers (32)", "General money questions", "No one to ask", "All"],
   ["Protect", "Scam scripts (9) + rehearsal", "Recognise and refuse a scam", "Fraud losses", "75%, 20%"],
   ["Protect", "Recovery coach", "First hour after a scam", "Panic, wrong steps", "All"],
   ["Protect", "Tip checker", "Verify a Telegram/WhatsApp tip", "Influencer fraud", "20%, 75%"],
   ["Protect", "Tax shield, panic replay, standing rules", "Timing, behaviour, alerts", "Avoidable tax, panic selling", "20%, 5%"],
   ["Rural", "Twelve tools", "Loans, schemes, papers, harvest", "Debt traps, missed benefits", "75%"],
   ["Messaging", "WhatsApp / SMS (14 options)", "Use without an app", "Access and language", "75%"],
   ["Portfolio", "X-ray, map, chart, actions", "Understand holdings", "Hidden concentration", "20%, 5%"],
   ["Research", "Desks + plain summary + charts", "Study a company", "Price-only thinking", "20%, 5%"],
   ["Practice", "Fee, overlap, emergency, digest", "Learn by doing", "Hidden costs", "20%"],
   ["Learn", "Goal fan, number doors, glossary", "Will I reach my goal?", "Opaque numbers", "20%"],
   ["Govern", "Firewall, rebalance, audit, tamper test", "Discipline and proof", "Overrides, edits", "5%"],
   ["Platform", "Offline pack, kiosk, language, theme", "Deploy anywhere", "Connectivity, shared devices", "75%"]], [2.2, 4.2, 3.9, 3.6, 2.7], size=8.2)

# =============================================================================================== 10 technical
H("12. Technical deep dive")
F("architecture.png", "Figure 11. Layers of the platform. Data flows up from the point-in-time store to the people at the top.", 14.2)
F("stack.png", "Figure 12. Technology stack. Everything is free and open source and runs on a single modest machine.", 15.0)
H("Key design decisions", 2)
T([["Decision", "Reason", "Consequence"],
   ["Deterministic calculators, not a model, for numbers", "A wrong rate or fee is worse than a slow answer", "Same question, same answer; every figure testable"],
   ["Local first: speech, voice, data and optional model on the machine", "Privacy, cost, no data needed once set up", "Works offline; no per-question cloud bill"],
   ["Point-in-time store: every read is filtered by a clock", "Prevents hindsight in research and in the time machine", "Credible backtests and honest 'what was known then'"],
   ["Hand-written bilingual text, closed-list model picking", "Prevents invented words and numbers; Hindi quality", "Content effort grows with coverage, so it is planned as content, not code"],
   ["Hash-chained ledger", "Tamper-evidence without a blockchain", "Cheap, auditable, explainable to non-experts"],
   ["Rules before models in routing", "Demo and production reliability", "A model failing never breaks the core path"]], [5.2, 5.6, 5.8], size=8.5)
F("pit.png", "Figure 13. The point-in-time guard. When the clock is moved back, later facts are hidden from the analysts.", 13.5)
H("Components", 2)
B(["**Ingestion** pulls free price, statement, ownership and headline data on demand or in batch; each row is stamped with when it was published and fetched.",
   "**Enrichment** derives growth, cash conversion, debt, interest cover, Piotroski and Altman scores, dividend and payout, ownership and a company's own past P/E range (banks skip debt-type scores because they mean something else for a lender).",
   "**Research desks** (four analysts and a sceptic) run on a local model; their claims must cite stored evidence or are rejected, and the page streams each desk's result as it finishes.",
   "**Messaging** (WhatsApp/SMS) shares the same assistant; sessions are per phone number; voice notes are transcribed locally.",
   "**Offline** uses a service worker and Pyodide so the Python rural calculators run in the browser.",
   "**Quality** is protected by 520 automated tests covering routing, Hindi, scam scripts, calculators, summaries and the audit chain."])

H("Content and language operations", 2)
rich("Because answers are hand-written, content is a product in its own right. The current library holds 32 general explanations, nine scam scripts and 25 tours, each in English and Hindi, grouped as below. Adding a language means writing, reviewing and testing the same set, not retraining a model.")
T([["Content set", "Count", "Covers"], ["General explanations", "32", "Investing basics, funds, tax, saving, loans, insurance, safety, how the app works"],
   ["Scam scripts", "9", "Bank OTP, digital arrest, courier, remote app, task job, loan app, prize, SIM or utility, investment group"],
   ["Guided tours", "25", "Whole app, every page, every tool in Practice, Protect, Govern, Rural, WhatsApp, Learn"],
   ["Rural tools", "12", "Loans, schemes, papers, harvest, saving, group ledger, UPI, policy"], ["Research checks", "25", "Growth, cash, safety, valuation, ownership, price behaviour, news"]], [4.0, 1.8, 10.8], size=8.8)
H("Deployment options", 2)
T([["Option", "Where it runs", "Best for", "Notes"],
   ["Single laptop or mini PC", "One machine runs everything, including voice and the optional model", "Pilots, demos, a Common Service Centre", "Lowest cost; fully private"],
   ["Edge box per partner", "A small server at a bank branch, NGO office or federation", "Partner-hosted deployments", "Data stays with the partner"],
   ["Cloud-hosted", "Standard container host", "Scale across states; WhatsApp at volume", "Needs consent and a data-protection review"],
   ["Offline browser pack", "Phone or tablet browser (service worker, Pyodide)", "No-signal villages", "Rural tools only; prices need a connection"]], [3.4, 4.8, 4.2, 4.2], size=8.4)
H("Security and privacy measures", 2)
B(["Processing of speech, calculators and the optional model happens on the machine; nothing is sent to an outside service to answer a question.", "A shared-device mode wipes the previous person's answers and results before the next person starts.", "Stored data is limited to what a tool needs; portfolios and ledgers stay on the device unless the person exports them.", "The audit record is tamper-evident; backups are exported by the person, not uploaded.", "Outbound requests are limited to fetching public market data and, if enabled, the messaging provider."])
H("Performance and scale", 2)
rich("Answers from calculators and stored explanations return in well under a second. A company card adds the time to fetch a live chart, capped at a few seconds and cached for ten minutes, with automatic fall-back to the saved snapshot. The research desks, which use a local model, take about half a minute and stream each desk's result as it finishes. Scaling to many users is a hosting question rather than a design change, because the core is stateless apart from per-user sessions.")

# =============================================================================================== 11 prototype status
H("13. Where the prototype stands today")
F("maturity.png", "Figure 14. Readiness by area, as judged by the team. Green is demonstrable, amber is partial, red is planned.", 14.2)
T([["Working now", "Partly done", "Not yet"],
   ["Twelve rural tools in Hindi and English; offline pack; WhatsApp simulator; nine scam scripts and the recovery coach; assistant understanding; 25 tours; research summary with confidence; firewall and audit chain",
    "Voice recognition in Hindi (works, accuracy varies by accent and microphone); live data for the 53-company universe plus on-demand additions; fund holdings are illustrative samples",
    "Real WhatsApp/SMS number in production; more Indian languages; USSD/IVR for feature phones; promoter pledging data; large-scale hosting; user research with real beneficiaries"]], [5.6, 5.5, 5.5], size=8.8)
callout("Be clear about limits", "Trading is **paper only**. The sample funds' holdings are illustrative. The price snapshot can be weeks old unless refreshed (the page says so). Answers are education and description, not regulated advice.", "FDEDEB")

# =============================================================================================== 12 differentiation
H("14. How we are different")
F("position.png", "Figure 15. Positioning. Most tools serve wealthy investors or are passive content; this platform serves the masses and does the task.", 11.8)
T([["", "Broker and trading apps", "Bank apps", "Finance influencers", "Literacy NGOs and portals", "**This platform**"],
   ["Primary user", "Active traders", "Own customers", "Followers", "Learners", "**Underprivileged first, then retail, then affluent**"],
   ["Language / channel", "English app", "App and branch", "Video, chat groups", "Web, workshops", "**Hindi voice, WhatsApp, SMS, offline**"],
   ["Numbers come from", "Feeds", "Core systems", "Opinion", "Static examples", "**Deterministic code + dated data**"],
   ["Scam help", "Banner warnings", "Generic alerts", "Often the source", "Awareness posters", "**Script-specific answers, rehearsal, recovery coach**"],
   ["Advice stance", "Encourage trading", "Sell bank products", "Tips", "Education", "**Describe only; no buy/sell**"],
   ["Cost to the user", "Brokerage and fees", "Free, with product push", "Free or paid courses", "Free", "**Free; funded by partners**"],
   ["Works offline", "No", "Limited", "No", "No", "**Yes**"]], [2.6, 2.6, 2.4, 2.5, 2.6, 3.9], size=8.0)
H("Our defensible edges", 2)
B(["**Mass-first design.** The hardest users set the standard: voice, Hindi, offline, shared device.", "**Task completion, not content.** It computes the loan cost and traces the missing payment.", "**Trust architecture.** No invented numbers, visible data age, confidence marks, tamper-evident record.", "**Cost structure.** Free and local means serving a village costs almost nothing per user.", "**One engine, three audiences.** Rural, retail and affluent features share the same core, so each group improves the others."])

# =============================================================================================== 13 business
H("15. Taking it to market: the business")
rich("The users who benefit most cannot pay, and should not have to. The business therefore sells to the institutions that profit from those users being safer and better served, and sells premium features to the small group that can pay.")
F("business.png", "Figure 16. The business model. Users on the left use it free; institutions on the right pay.")
T([["Revenue stream", "Customer", "What they buy", "Why they pay"],
   ["Institutional licence", "Banks, co-operative banks, MFIs, business correspondents", "White-label scam shield and loan-fairness tools for their customers; WhatsApp channel", "Lower fraud losses, fewer complaints, financial-inclusion targets"],
   ["Programme contracts", "NGOs, CSR funds, state rural-livelihood missions, SHG federations", "Deployment in a region with local-language content and impact reporting", "Measurable outcomes: scams avoided, benefits claimed"],
   ["Channel partnerships", "Common Service Centres, post offices, agri co-operatives", "Kiosk mode and training", "New service for footfall"],
   ["Premium subscriptions", "Retail and affluent users", "Research summaries, alerts, reports, multi-portfolio", "Time saved, discipline, proof"],
   ["API and data", "Fintechs, advisers", "Scam scripts, calculators, summaries as an API", "Build faster, stay compliant"]], [3.2, 4.6, 4.9, 3.9], size=8.4)
F("partners.png", "Figure. Partner ecosystem: who delivers, who funds, who regulates the advice.", 13.5)
F("economics.png", "Figure 17. Illustrative economics. Assumptions, not forecasts: the mass segment is funded by partners, the premium segment by users.", 13.5)
H("Go-to-market", 2)
T([["Phase", "Action", "Proof we need"],
   ["1. Pilot (0-6 months)", "Two or three partners: an SHG federation, a co-operative bank, an NGO; a real WhatsApp number; 2,000 users", "Weekly active use, scams avoided, benefits found, comprehension in user tests"],
   ["2. Expand (6-18 months)", "More states and languages; voice-first and IVR; bank and CSC channels", "Cost per active user, partner renewals, fraud-loss reduction"],
   ["3. Platform (18-36 months)", "API, white-label, regional models, impact dashboard for funders", "Revenue per partner, retention, third-party integrations"]], [3.6, 7.2, 5.8], size=8.6)
H("An illustrative impact model", 2)
T([["Per 10,000 active rural users in a year (assumptions)", "Illustrative result"],
   ["Borrowers who learn the true yearly cost of a loan", "About 2,500"], ["Households that find at least one scheme they qualified for", "About 1,500"],
   ["Scam attempts recognised and refused", "About 4,000"], ["Households that complete a savings plan with the daily-saving tool", "About 1,000"],
   ["Typical annual cost to serve (messaging, support, content amortised)", "Low single-digit rupees per user per month"]], [11.0, 5.6], size=8.8)
P("These are planning assumptions for pilot design, not results. The pilot exists to replace them with measured numbers.", italic=True, size=8.8, color=MUTE)
H("Costs and sustainability", 2)
B(["**Low marginal cost.** Local software and free data sources; the main variable cost is WhatsApp/SMS delivery, passed through to partners.", "**Content is the real cost.** Hand-written Hindi and regional text, kept accurate as rules change (tax, scheme rates). Budget for editors and a review process.", "**Support and training** for partner staff, which is also a revenue line."])

# =============================================================================================== 14 risk
H("16. Risks, compliance and ethics")
T([["Risk", "Why it matters", "How we handle it"],
   ["Looking like regulated advice", "In India, paid investment advice needs SEBI registration", "Describe, never recommend; no buy/sell; clear disclaimers; confidence marks; partner with registered advisers for premium advice"],
   ["Wrong or outdated rules (tax, scheme rates)", "A wrong figure harms trust", "Dated rules, 'as of' wording, tell the user to confirm, editorial review cycle"],
   ["Data privacy", "Personal finance data is sensitive; India's Digital Personal Data Protection Act 2023 applies", "Local-first processing, no raw data leaves the device by default, kiosk wipe, consent for any cloud channel"],
   ["Scam-script misuse", "A scam explanation could be read as a how-to", "Frame from the victim's side, no operational detail, include protective steps"],
   ["Language errors", "A bad translation can mislead", "Hand-written bilingual text, native-speaker review before each new language"],
   ["Over-reliance", "People may treat the tool as a guarantee", "Plain limits stated; decisions stay with the person"],
   ["Connectivity and device limits", "Rural networks are uneven", "Offline pack, SMS fallback, low-bandwidth design"],
   ["Platform dependence", "WhatsApp or provider policy changes", "Channel-agnostic core; SMS and IVR alternatives"]], [3.8, 5.0, 7.8], size=8.5)
H("Ethical principles", 2)
B(["Serve the person, not the product: nothing is sold through the tool.", "Say what is not known. A gap is shown, not hidden.", "Never shame a victim: 'none of this is your fault' is part of every recovery answer.", "Keep a record a person can inspect."])

# =============================================================================================== 15 roadmap
H("17. Roadmap, measures of success and what we added")
F("roadmap.png", "Figure 18. Roadmap from prototype to platform.")
H("Measures of success", 2)
T([["Group", "Measure", "Why it matters"],
   ["75% underprivileged", "Scams avoided or reported within the first hour; borrowers who learn their true yearly rate; benefits claimed; weekly use over WhatsApp", "Direct financial outcomes"],
   ["20% retail", "Fees saved after fee-drag use; funds de-duplicated; share of questions answered without clarification", "Behaviour change and answer quality"],
   ["5% affluent", "Breaches blocked; audit entries verified; adviser adoption", "Trust and retention"],
   ["Platform", "Cost per active user; answer coverage by language; partner renewals", "Sustainability"]], [3.4, 8.6, 4.6], size=8.6)
H("What we added beyond the original brief", 2)
rich("Reviewing the idea end to end, several things a funder or partner will ask for were missing, and are now part of the plan:")
B(["**A regulatory position** (describe, never advise) and a path to SEBI-registered partners for advice.", "**An impact measurement framework**, so CSR funders and missions can see outcomes.", "**A content operation**: editors, review cycles and native-speaker checks for each language.", "**A channel strategy beyond WhatsApp**: SMS now, USSD and IVR for feature phones, and a Common Service Centre model.", "**A user-research plan** with real beneficiaries before scale: comprehension, trust, voice accuracy by accent.", "**A security and privacy plan** aligned to the Digital Personal Data Protection Act 2023.", "**An honest limits section** (paper trading, sample fund data, snapshot age) so claims stay credible."])

# =============================================================================================== appendix
H("Appendix A. Demo script (six minutes)")
T([["Minute", "Do this", "Say this"],
   ["0-1", "Open Home, then Assistant; ask 'How does this prototype work?'", "A guided tour starts: the platform explains itself, visually and aloud"],
   ["1-2", "Rural: moneylender, 5 rupees per hundred, Rs 50,000", "Sixty per cent a year; this is what the 75% gets, free, in Hindi"],
   ["2-3", "Assistant: 'Someone from the bank asked for my OTP'", "A script-specific answer, not a generic warning; open the rehearsal"],
   ["3-4", "WhatsApp page: send 'hi' and a sentence in Hindi", "No app, no data plan needed; same tools"],
   ["4-5", "Assistant: 'Analyse TCS', then 'Compare Reliance and HDFC Bank'", "Facts, chart, confidence marks; never buy or sell"],
   ["5-6", "Govern: check a trade that breaks the limit; Tamper test", "Rules no AI can override; a record that catches edits"]], [1.6, 7.6, 7.4], size=8.8)
H("Appendix B. Questions reviewers ask")
T([["Question", "Short answer"],
   ["Is this financial advice?", "No. It describes and explains, never says buy, sell or hold, and shows how much to trust each point."],
   ["How do you avoid wrong numbers?", "No language model produces a number. Calculators and dated data do, and 520 tests check them."],
   ["Who pays if users are poor?", "Institutions that gain from fewer frauds and more inclusion: banks, co-operatives, NGOs, CSR funds, state missions."],
   ["Does it work without internet?", "Yes, for the rural tools: the calculators run in the browser from a saved pack. Fresh prices need a connection."],
   ["Why Hindi first?", "It is the largest language among the underserved group. The content model lets more languages be added with review by native speakers."],
   ["What is real and what is a mock?", "The tools, the assistant, the research summary and the audit chain are real. WhatsApp is simulated until a number is connected; trading is paper only."],
   ["What if a scam script is misused?", "Answers are written from the victim's side, with protective steps and no operational detail."],
   ["What is next?", "A pilot with two or three partners and a real WhatsApp number, then more languages and voice-first access."]], [5.2, 11.4], size=8.8)
H("Appendix C. Glossary")
T([["Term", "Meaning"], ["SHG", "Self-help group: a small group, usually of women, that saves and lends together"], ["DBT", "Direct benefit transfer of subsidies and pensions to bank accounts"], ["UPI", "Unified Payments Interface, India's instant payment system"],
   ["SIP", "Systematic investment plan: a fixed monthly investment into a fund"], ["Point-in-time store", "A data store where every read is filtered by a clock so the future is hidden"], ["Hash chain", "Each record carries a fingerprint of the one before it, so an edit is detectable"],
   ["Confidence mark", "Solid, light or weak: how much data a point rests on"], ["CSC", "Common Service Centre: village-level digital service points"], ["IVR / USSD", "Voice-menu and short-code phone services that work on basic phones"]], [3.6, 13.0], size=9)
H("Appendix D. Sources and notes")
B(["Product facts come from the prototype itself (code and tests at the time of writing).", "India context: RBI, NPCI, SEBI, Ministry of Rural Development (DAY-NRLM), NCFE financial-literacy survey 2019, MeitY (CSC). Figures are rounded and should be refreshed before external use.", "Business figures are illustrative assumptions to be replaced by pilot data."])

out = ROOT / "JARVIS_Product_Brief.docx"
d.save(out)
words = sum(len(p.text.split()) for p in d.paragraphs) + sum(len(c.text.split()) for t in d.tables for r in t.rows for c in r.cells)
print("saved", out, "words ~", words)
