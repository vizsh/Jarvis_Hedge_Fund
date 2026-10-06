# JARVIS // money, plainly: master context

This is the single document to read before answering any question about the project, its problem, its users, its features, its
numbers, or its status. Every other doc goes deeper on one area; this one says what the whole thing is and why.

Last updated: 6 October 2026 (commit `470d22a` and later).

---

## 1. What it is, in one paragraph

JARVIS is a free, local, bilingual (English and Hindi) prototype that helps ordinary Indian people protect their money, understand
it, and keep it honest. It runs on one machine: a FastAPI backend, a React front end, a SQLite snapshot of prices and company data,
and optional local models for speech and intent. It never uses a language model to produce a number. Every figure comes from code
you can read, or from dated public data, and every answer shows how it was worked out.

It is a prototype, not a product. It is paper trading only (no broker, no real money), and nothing is charged.

## 2. The problem it addresses

**The problem in one sentence:** ordinary households, especially rural and first-time savers, lose money through three channels
(scams, expensive informal credit, and fees or tips they cannot check). A plain-language check at the moment of decision can catch
most of these early. Each loss also weakens the lender or bank that serves the household, so the problem reaches institutions too.

| Loss channel | What it looks like | Figure we can cite | Source and status |
|---|---|---|---|
| **Digital fraud** | Panic transfers, OTP and remote-app scams, fake KYC and impersonation calls | About ₹22,845 crore lost in 2024, against about ₹7,465 crore in 2023; about 19 lakh financial-fraud complaints on NCRP in 2024 | I4C figures as reported in a 2025 industry summary. Quote the official I4C release before a pitch. |
| **Informal credit** | A moneylender quotes ₹2 to ₹5 per ₹100 a month | Arithmetic, not a survey: 5% a month is 60% a year on simple interest, and more with compounding. A formal Kisan Credit Card costs about 7% a year, or about 4% with prompt-repayment interest relief (`backend/rural.py`) | The arithmetic is exact. The informal-rate range comes from older SIDBI and NSS-based summaries (dated, re-check before quoting). |
| **Fees and unverified tips** | A fund fee quietly takes a large share of long-run growth; tips with no time frame or source | Shown in the app with the user's own inputs (a 2% fee on a 20-year horizon is an illustration, not a national statistic) | Calculation, not a survey. |

**Why it matters to lenders and banks.** A household that pays 60% a year on an informal loan has little left to repay a formal loan
or to keep a savings account funded. That raises default risk on co-operative bank and microfinance loans, and it moves borrowers
back to informal lenders once formal lenders tighten. The prototype does not measure these effects. A pilot with a partner bank
would have to.

**Context figures, with the caveat attached.**
- Financial literacy: 27% of Indian adults overall and 24% in rural areas (NCFE 2019 survey).
- Households in the securities market: about 9.5% overall, about 6% rural (SEBI Investor Survey 2025; verify on sebi.gov.in).
- Rural share of GDP: about 46% of net domestic product (NITI Aayog / CSO estimates).
- Rural share of deposits: strictly rural bank branches hold about 10 to 11% of scheduled bank deposits; rural plus semi-urban
  branches hold about 28 to 30% (RBI Basic Statistical Returns). Always say which of the two you mean.

**Figures we do not use until a source is found** (they appeared in an outside draft without a source): bank fraud of ₹48,000 crore
in FY 2025–26; "₹5,000–8,000 crore recovered through 1930"; co-operative bank NPA of 35–38% and ₹7,500 crore of stressed rural
assets; "trillions" of unclaimed benefits; and "25–30% of deposits" without the rural / semi-urban qualifier.

## 3. Who it is for: the reform (scope by audience)

The product has ten features. Not every audience needs all of them, so the setup screen (`/setup`) asks who the prototype is for
and starts from one of five baskets. The person can then switch features on or off. **Every feature works the same in every basket.**
A basket only decides what the menu shows by default.

| Basket | Starting features | Demo monthly price | Why |
|---|---|---|---|
| **Full prototype (for pitching)** | All ten | Free in the demo | One place to show every feature to a funder or partner |
| **Banks and co-operative banks** | Assistant, Rural tools, WhatsApp & SMS, Scam protection, Learn, Govern & audit | ₹499 | Fewer fraud losses for customers, credit-cost explanations, WhatsApp outreach, compliance limits with an audit record |
| **Farmers and rural families** | Assistant, Rural tools, WhatsApp & SMS, Scam protection, Learn | Free | Moneylender cost, schemes, papers, harvest plan, scam safety, on a basic phone |
| **Self-help groups and NGOs** | Assistant, Rural tools, WhatsApp & SMS, Scam protection, Learn | Free | Group ledger and meeting reports, daily saving plans, scam awareness, shared-device use |
| **Middle-class retail investors** | Assistant, Portfolio X-ray, Research desk, Practice tools, Scam protection, Learn | ₹597 | Portfolio health, fund overlap and fees, company research, tax timing |

Monetisation model (demo only): the rural and self-help features are always free; paid features are Portfolio X-ray (₹199/month),
Research desk (₹299), Practice tools (₹99) and Govern & audit (₹499). Checkout is a dummy; nothing is charged. The prices are there to
show how the model would work in a pitch. Persistence is one saved setup per install, not per user (see section 11).

## 4. The ten features

Home is always on. The other nine (plus home makes ten) are below. Routes are hash routes (`#/route`).

| Feature (route) | Tier | What it does | Who it is for | Status |
|---|---|---|---|---|
| **Assistant** (`#/assistant`) | Free | Types or speaks a question in English or Hindi. Every reply is a card: kind, short answer, figures, a chart or table where useful, steps, a caution, tools and follow-ups. A guided tour can walk you through any feature on screen. | Everyone | Working. Understanding layer reads the whole sentence before any keyword rule (`backend/understand.py`). |
| **Rural tools** (`#/rural`) | Free | Twelve tools: moneylender check, credit score, is this offer real, UPI safety, policy check, government schemes, papers checklist, "why no money?", plan my year, sell or hold, daily saving, group ledger. Works offline once the pack is saved. | Farmers, daily-wage families, SHGs | Working. Layout reworked for readability; original rules kept. |
| **WhatsApp & SMS** (`#/whatsapp`) | Free | The same answers as the assistant on a phone chat: numbered menu, one question at a time, voice notes, Hindi. A simulator in the browser behaves like the real channel. | Basic-phone users | Working as a simulator. Real delivery needs a Twilio account (see MESSAGING.md). |
| **Scam protection** (`#/protect`) | Free | Scam scripts for nine kinds of scam, a tip checker with specialist reasoning, a recovery coach for the first hour after a loss, a tax shield, a panic-sell replay, standing "tell me if" rules. | Everyone; families of older people | Working. |
| **Learn** (`#/learn`) | Free | Plain explanations (32 checked topics in English and Hindi), a goal range from the portfolio's own history, "every number is a door" drill-downs, a glossary. | First-time savers and investors | Working. |
| **Portfolio X-ray** (`#/portfolio`) | Paid | Health grade, spread, allocation map, what-to-do list, and a chart of your money against the index. | Retail investors | Working on sample portfolios. |
| **Research desk** (`#/research`) | Paid | Search any listed stock. A plain-words summary: good points, watch-outs, peer ranks, confidence on every line, how current the data is. Three analyst desks (Fundamental, Quant, Narrative) and a red-team sceptic study the company. Time machine. | Retail investors | Working. Summary reads growth, cash, valuation, ownership and price behaviour. |
| **Practice tools** (`#/practice`) | Paid | Fund overlap checker, fee-drag slider, emergency-fund meter, weekly spoken digest, scam-call rehearsal. | Retail investors, anyone learning | Working. |
| **Govern & audit** (`#/govern`) | Paid | Risk firewall that checks any trade against per-stock, per-industry and cash limits; rebalance simulator; tamper-evident audit record (hash-chained on this machine, not anchored outside it); tamper test. | Banks, advisers, family offices | Working on the paper-trading portfolio. |

**Grouped by the loss each one addresses.** The features are not reduced or moved; this is how they are explained.

| Loss channel | Features that address it |
|---|---|
| **Fraud shield** | Scam protection (scripts, rehearsal, tip checker, recovery coach); the Assistant's scam answers; the Learn topics on fraud |
| **Credit cost** | Rural tools (moneylender check, KCC and SHG comparison, credit score guide, schemes, papers); the Assistant's loan answers |
| **Investing protection** | Portfolio X-ray (fees, overlap, concentration); Research desk (plain company summary, confidence on every line); Practice tools (fee drag, overlap, fund checks) |
| **Reach and trust** | Assistant (English and Hindi, voice); WhatsApp and SMS (simulator today); Learn (checked topics, glossary); Govern and audit (limits and a tamper-evident record for advisers and banks) |

Not yet in the app: showing these groups on the home tiles, the setup screen and each feature page. That is the next UI step.

Other things a user sees: the **Home** menu (tiles for the features they chose), the **My setup** button (change the basket and
features at any time), the **Set up** page (`#/setup`), and the **locked-feature** page that appears when a feature is not in the
current setup (add it in one tap).

## 5. How the parts work

**Answering a question (assistant and WhatsApp use the same path).**
1. The text is read as a whole (`backend/understand.py`). Four kinds of request are separated first: a question about the app (guided
   tour), a company (analysis or comparison, with a chart), a general money question (checked explanation), or a personal number
   question (calculator). Tip messages go to the tip checker, and messages about a loss go to the recovery coach.
2. Only if none of those fit does the older rule router run (`backend/assistant.py`), then the optional local model.
3. The local model, when installed, may only **pick** one item from a closed list. It never writes an answer or a figure.
4. Answers are built from hand-written, checked text (English and Hindi) and from calculators. Numbers are placed by code.

**The tip checker (`analysis/tipminds.py`).** A panel of eight specialists reads what a tip is suggesting and tests it:
feasibility (a first-passage price model from the stock's own volatility; a fixed periodic return; a guarantee), fundamentals (the
implied P/E at the target against peers and history), technicals, market structure (liquidity, listing), source and incentive (who gains
if you act), SEBI rules, wording (one low-weight witness), and consequence (what it could cost). Two answers come out separately: the
chance it is a scam, and how much real backing the idea has. The output is an action: ignore and report, ignore, verify first,
research it yourself, or information only. Sample tips and their results are in `docs/TIP_TEST_SAMPLES.md`.

**Company research (`analysis/proscons.py`, `ingest/enrich.py`).** The company's own numbers (growth, cash conversion, debt, interest
cover, Piotroski and Altman scores, dividends, ownership, its past P/E range) and its price behaviour (trend, momentum, volume, range,
relative strength) are turned into good points and watch-outs. Each line carries a basis and a confidence mark: solid, light or weak. The
page shows how old each kind of data is and how many checks had data at all. Banks skip debt-type measures, and the page says why.

**Charts (`backend/charts.py`).** Live closes from Yahoo Finance when online, otherwise the saved snapshot; the source and the date of
the last close are always shown. A TradingView tab is an optional live chart.

**Offline (`frontend` service worker, Pyodide).** The rural calculators are pure standard-library Python so they can run in the browser.
The offline pack caches the app shell and those calculators.

**Setup (`backend/setup.py`, `frontend/src/pages/Setup.tsx`).** Ten features with free or paid tiers and demo prices; five baskets; the
saved choice is one row in SQLite (`app_setup`). The menu, the home tiles and the route gate all read the saved list. A feature that is
not in the list opens the locked page instead of its screen.

**Privacy.** Speech-to-text (faster-whisper) and text-to-speech (Piper, Kokoro) run on the machine. The portfolio, saved funds, rules and
audit record stay in the local database. The only outbound requests are for public market data and, if enabled, the messaging provider.
A shared-device (kiosk) mode clears the previous person's answers.

## 6. Honesty rules (the product's non-negotiables)

1. **No model writes a number.** Figures come from calculators and dated data.
2. **No buy, sell or hold.** Answers describe, compare and explain. The decision stays with the person. Tests check the wording.
3. **Show the working.** Every answer has a "how this was worked out" line or the detail behind it.
4. **Say what is not known.** Missing data goes under "could not check", never guessed.
5. **Age is visible.** Every data kind shows its date; old data is labelled.
6. **Paper only.** No broker connection and no real money in any feature.
7. **Dummy money.** Prices in the setup are for the pitch; nothing is charged.

## 7. Architecture and where things live

```
backend/
  app.py          FastAPI app: ~106 HTTP routes, WebSocket event stream, /ask, /setup, /scan, /research/summary, /twilio/webhook
  assistant.py    rule router and calculator handlers; tip answer; scam answers
  understand.py   whole-question understanding: app tours, companies, concepts, portfolio moves
  knowledge.py    32 checked general explanations (EN + HI)
  scams.py        nine scam scripts
  tours.py        guided tours (25); tours_parts.py holds the step-by-step detail
  charts.py       price series and comparison series
  messaging.py    WhatsApp/SMS handling: menus, voice notes, answer rendering
  guide.py        multi-question guided flows (e.g. moneylender check asks one thing at a time)
  rural.py        rural calculators (standard library only)
  setup.py        features, baskets, prices, saved setup
analysis/
  tipminds.py     tip panel of eight specialists
  scanner.py      text-pattern tactics and claim tests (one witness among eight)
  proscons.py     plain research summary for one company
  attribution.py  what moved the portfolio (Brinson-style)
  tax.py, shield.py, panic.py, stress.py, goal.py, xray.py, tools.py, stocksearch.py ...
core/             point-in-time store (pit.py), database (db.py), universe (universe.py)
ingest/           data adapters; enrich.py (growth, cash, ownership); ondemand.py (add a stock)
agents/           research desks, orchestrator, local model client (llm.py)
risk/             risk firewall and sandbox
frontend/src/
  pages/          Home (Pages.tsx), Setup, Rural, WhatsApp, Protect, Practice, Govern, Learn, AssistantPage ...
  components/     Nav, Composer, ChatThread, AnswerCard, TourOverlay, charts/PriceChart, ResearchSummary ...
  lib/            setup.ts (setup store), tour.ts, chat.ts, socket.ts, speak.ts, router.ts, theme.ts, lang.ts
  styles-*.css    one stylesheet per area; styles-rural.css loads after the theme (village-first layer)
tests/            35 test files, 532 tests (run: python -m pytest tests -q)
tools/            figure and document generators, sample runners (tip_samples, wa_check, wa_batch, brief_figures, build_brief)
docs/             this file and the topic docs
data/             snapshot.db (prices, signals, ledger) -- not committed in full
```

Data flow in one line: public data is ingested into `snapshot.db` with a date on each row; the backend reads it through a
point-in-time store that refuses to see the future; calculators and checked text turn it into answers; the front end and the
WhatsApp channel render the same answer.

## 8. How to run it, test it, and commit it

- Run the backend: `python -m uvicorn backend.app:app --port 8000` (from the repo root). Open http://localhost:8000.
- Build the front end after changes: `cd frontend && npm run build` (the backend serves the built files).
- Test: `python -m pytest tests -q` (532 tests, about 70 seconds).
- Try a WhatsApp conversation from the command line: `python -m tools.wa_check` or `python -m tools.wa_batch` (30 everyday questions).
- Regenerate the tip samples: `python -m tools.tip_samples`.
- Commit and push after each verified change, to `master` (the project's working rule).

## 9. Sources for the numbers

- NCFE Financial Literacy and Inclusion Survey 2019 (27% overall; 24% rural; women over 80% not literate):
  https://ncfe.org.in/wp-content/uploads/2023/12/ExecSumm_.pdf
- I4C and 1930 helpline figures for 2024 as reported in a 2025 industry summary (₹22,845 crore; 1,918,865 NCRP complaints):
  https://www.quickheal.co.in/documents/media/2025/cyber-frauds-cost-india-digital-terminal-july2025.pdf
  Other reports give different totals for different years (for example ₹177 crore for FY24 in a Business Standard piece). Quote the
  official I4C release, not a summary.
- Informal lending practices (SIDBI study, 2019): https://www.sidbi.in/uploads/coca_reports/2019-03-29-165105-t9yg7-Study-on-Informal-Sector-Lending-Practices-in-India-Final-Report.pdf
- SEBI Investor Survey 2025 (about 9.5% of households participate; rural about 6%; urban about 15%). Verify on sebi.gov.in before quoting.
- The 2003 NSS informal-credit share and the moneylender rate ranges are older summaries. Re-check the original reports before quoting.

## 10. Status, gaps and decisions

**Working now:** all ten features above; setup with five baskets and locked-feature prompts; tip checker with eight specialists; company
research with confidence marks; WhatsApp simulator with 30 everyday questions answered (`tools/wa_batch.py`); Hindi voice and text on the
assistant; offline pack for the rural tools; 532 passing tests.

**Known gaps (be honest about these on any slide):**
- The audit chain is tamper-evident, not tamper-proof. Someone who rewrites the whole chain can recompute every hash unless the latest hash is anchored somewhere outside the machine. Anchoring is not built.
- WhatsApp is a simulator. A real number needs a Twilio account and the webhook (`docs/MESSAGING.md`).
- The setup is saved once per install, not per user. A real product needs accounts.
- Payments are dummy. No checkout, no invoices.
- Voice recognition in Hindi works but accuracy varies with accent and microphone; it has not been tested with rural speakers yet.
- Live data covers the 53-company universe; other companies are fetched on demand and only partly covered.
- Fund holdings in the practice tools are illustrative samples, not live factsheets.
- The assistant's understanding was tested on about 500 automated cases and sample phrasings, not on real user recordings.
- Mobile layouts were checked for the assistant, not for every page.
- The local language model is optional and was not installed during the last checks; rule-based answers work without it.

**Decisions and why:**
- Numbers only from code: a wrong figure costs more trust than a slow answer.
- Hand-written Hindi and English text: a machine translation can change a number or a meaning.
- Local first: privacy, no per-question cost, works offline.
- One codebase, ten features, baskets for audiences: showing every feature to every person would confuse the people who need it most.
- Free for rural and self-help features: they are the people the problem statement is about; paid features fund the research and governance tools.

## 11. Next steps (in order)

1. Record the official problem-statement text in section 2.
2. Test the rural tools and WhatsApp flow with three to five real users, in Hindi, on a basic phone.
3. Decide per-user accounts and where the setup lives.
4. Connect a real WhatsApp number through Twilio for a pilot.
5. Measure the pilot outcomes listed in `docs/PITCH_RURAL.md` (true yearly rate learned, scams refused, schemes found).

## 12. Quick answers

- **What is the core idea?** Put a trustworthy money guide in the hands of people who have never had one, in their own language, free.
- **Who is the primary user?** Rural and low-income households; then retail investors; then affluent users and advisers.
- **Why not use a chatbot model for everything?** Because a model can invent a number. Here the model only picks which checked answer fits.
- **Is it investment advice?** No. It describes and explains and never says buy, sell or hold.
- **How is it different from a broker or bank app?** It serves the people those apps don't reach, works in Hindi and on WhatsApp, and
  refuses to sell anything.
- **How does it make money?** Demo model: paid features for banks and retail investors; rural and self-help features free; institutions
  pay for fewer frauds and better reach (see `docs/PITCH_RURAL.md` and `JARVIS_Product_Brief.docx`).
- **How many tests?** 532, run with `python -m pytest tests -q`.
