# JARVIS: monetisation, running costs and data sources

Status: working analysis, written from the code and `docs/DATA.md`. Cost figures are **estimates with the assumption stated beside each one**. Before any pitch or budget, get current vendor price lists and written legal advice. Nothing here is a quote.

---

## 1. Monetisation: who pays, for what, and why

### 1.1 The short answer

An individual rural user should not be charged for the core protection, and the product is built that way. The money comes from institutions that carry the loss when a household is defrauded or defaults, and from a small number of paid tools for people who can afford them. Charging individuals is possible for the investor tools only, and it has to be justified by what those tools do.

### 1.2 Payers and what each one buys

| Payer | What they buy | Why they would pay | Realistic price shape |
|---|---|---|---|
| **Co-operative and rural banks** | White-label WhatsApp and SMS assistant for customers; fraud-recovery coach; credit-cost explainer; Govern and audit for staff | Fewer fraud complaints, fewer customers lost to informal lenders, a compliance trail | Annual licence per bank or per customer band, plus a set-up fee. The demo shows ₹499 a month. Treat that as a placeholder until a bank has signed. |
| **Regional rural banks and small finance banks** | Same as above, with the credit-cost tools tied to their own KCC and SHG products | Priority-sector targets; lower default risk on rural loans | Enterprise licence, usually negotiated per branch count |
| **State missions and NGOs** (livelihood, women's SHG and financial-inclusion programmes) | Field kit: offline pack, group ledger, scheme finder, training in Hindi and regional languages | Programme outcomes they must report; cheaper than field staff time | Project contract per district or per year |
| **CSR funds** | Outcome reporting: scams stopped, debt avoided (only as counts that the product actually records) | Spend obligations and impact reporting | Subscription for a reporting dashboard |
| **Retail investors** (middle class, urban and semi-urban) | Portfolio X-ray, fund overlap and fee drag, research desk, practice tools | Clear value on their own money; willing to pay a small monthly fee | Per-feature subscription (the demo uses ₹99 to ₹499 a month) |
| **Individuals who are scammed** | Recovery coach | Urgent need, but a one-off need: a poor subscription fit | Do not charge at the moment of loss. Keep it free. |

### 1.3 Why an institution pays, in plain terms

- **Banks.** A fraud loss on one customer account is a complaint, a reimbursement decision and a reputation cost. A guided first-hour recovery and a documented process reduce that. Credit-cost explanations help borrowers move from informal lenders to KCC or SHG loans, which is a better-quality book. The honest caveat: the product does not yet show a measured reduction in losses. A pilot must produce that number before a bank will sign a multi-year contract.
- **State missions and NGOs.** They are judged on reach and outcomes. An offline tool that serves a village without a smartphone is a field-staff multiplier.
- **CSR funds.** They need reportable outcomes. The reporting has to count real events from the product, not estimates.

### 1.4 Why an individual can be charged, and when it is not justified

- **Can charge:** the retail investor tools. They analyse the person's own holdings, fees and company research, and they are paid in the same way a budgeting or research app is paid.
- **Should not charge:** the rural and scam-protection features. The people who most need them have the least money, and a paywall on fraud protection makes the fraud problem worse. The product's own rule is that rural and self-help features stay free.
- **Legal limit on research:** the research desk summarises company data and gives a confidence mark, but it does not recommend buying or selling. Charging for stock research or investment advice can require SEBI Research Analyst or Investment Adviser registration. Get written advice on this before taking money for the research desk or the tip checker. Until then, the paid tier should be a tool-subscription framing, not an advice framing.
- **Legal limit on lending:** the moneylender and KCC comparison is information. If the product ever brokers a loan or takes a fee from a lender, RBI digital-lending rules apply. Do not add that without a licence plan.

### 1.5 The advantage, honestly

What the product has:
1. **Deterministic numbers.** Every figure comes from code, and the same function serves the page and the chatbot. Most AI-based finance tools cannot make that claim.
2. **Local first.** Speech, models and personal data stay on the machine. This matters for banks with data rules and for the DPDP Act 2023.
3. **Hindi and English as first-class text,** written by hand, not machine-translated, with a check that a translation never changes a number.
4. **Recovery workflow.** The first-hour checklist, drafts and helpline routing are a specific product, not a generic FAQ.
5. **Audit trail.** The hash-chained record is useful for advisers and banks, with the limit that it is tamper-evident, not anchored.

What it does not have yet (be honest in any pitch):
- No real customer data, no pilot, no measured outcome.
- Distribution. A bank channel or a state programme gives reach; the app alone does not.
- Moat is thin on features. Competitors (Truecaller, bank SMS alerts, Groww and Zerodha education, Khatabook for ledgers, Gupshup and Yellow.ai as bot platforms) can copy individual features. The defensible asset would be the institutional integrations and the verified Hindi content, not the code.
- Data licensing (section 3) is an unresolved commercial risk.

### 1.6 Pricing structure proposed for a pilot (to validate, not to publish)

| Tier | Who | Indicative structure | What must be true first |
|---|---|---|---|
| Free core | Everyone | Rural tools, scam protection, learn, WhatsApp | Nothing; keep it free |
| Institution licence | Banks, RRBs, SFBs | Annual licence per branch or customer band, plus set-up fee | A pilot showing fewer complaints or lower credit-cost exposure |
| Programme contract | State missions, NGOs | Per district per year, plus training | A signed MoU and a reporting template |
| CSR reporting | CSR funds | Annual reporting subscription | Counts that the product really records |
| Investor subscription | Urban retail | Per feature, monthly or yearly | Paying users in a test; SEBI advice opinion for research |

### 1.7 Revenue sanity check

Revenue depends on signed institutions, not on user counts. Ten rural users paying nothing are worth nothing directly; one bank contract is worth more than a thousand free users. Plan the first year around 2 to 3 paid pilots with clear outcome measures, not around a user target.

---

## 2. Costs of running the app

### 2.1 What runs where

| Part | Where it runs today | Cost driver |
|---|---|---|
| FastAPI backend, SQLite, React build | Developer laptop | Electricity only |
| Speech-to-text (faster-whisper) | Local CPU or GPU | Hardware; slow on CPU for long audio |
| Text-to-speech (Kokoro or Piper) | Local | Hardware only |
| Optional local model (Ollama, llama3.1:8b) | Local | Hardware; needs roughly 8 GB of RAM or VRAM |
| Market data (yfinance, SEC EDGAR, Google News RSS, GDELT, FRED, NSE via nsepython and jugaad-data) | Fetched at build time, plus on-demand for extra tickers | Free to call; **licence is the real cost** (section 3) |
| WhatsApp and SMS | Simulator today; Twilio webhook for real | Per-message fees from Twilio and from WhatsApp (Meta) |

### 2.2 Running cost by feature

Marginal cost per use is near zero for everything computed locally. The external costs are messaging, data licences and hosting.

| Feature | Runs on | External cost per use | Fixed cost it adds | Note |
|---|---|---|---|---|
| Assistant (text and voice) | Local backend; local Whisper and TTS | None | Hosting (below) | Voice needs a machine with enough CPU or GPU |
| Rural tools (moneylender, schemes, papers, harvest, ledger) | Local, offline-capable | None | None | Offline pack runs in the browser |
| Is this offer real? | Local | None | None | Rule-based |
| WhatsApp and SMS | Backend plus Twilio | Twilio fee plus WhatsApp conversation fee per message or session (India rates vary by message type; **check the current rate card**) | Twilio account, number, approved templates | Largest per-user cost if used at scale |
| Scam protection (scripts, tip checker, recovery coach) | Local | None | None | Tip checker needs price history, which needs data licence (section 3) |
| Learn | Local | None | None | Static checked content |
| Portfolio X-ray | Local | Price data for the user's holdings | Data licence | Works on sample portfolios without a licence |
| Research desk | Local; optional local model for desk notes | Data for the chosen stock; news feed | Data licence; LLM hardware if desks are on | Most data-heavy feature |
| Practice tools (fund overlap, fee drag, scam-call rehearsal) | Local | None | Fund factsheets when real funds are added | Current funds are illustrative samples, not real |
| Govern and audit | Local SQLite | None | None | Single-machine audit trail |

### 2.3 Hosting (estimates)

Assumptions: one small server, backend and built frontend together, SQLite on disk, no GPU.

| Option | Indicative monthly cost | What it can carry |
|---|---|---|
| Developer laptop | ₹0 | Demos only; not reachable from outside |
| Small Indian or European VPS (2 vCPU, 4 GB RAM, 50 GB disk) | roughly ₹800 to ₹2,000 | Web app for a pilot; text assistant; no heavy voice |
| Same VPS plus a GPU instance for speech | roughly ₹15,000 to ₹60,000 or more | Voice at useful speed; price depends heavily on provider |
| Managed database and object storage (if moving off SQLite) | roughly ₹1,000 to ₹5,000 | Multi-user accounts |
| Domain and TLS | roughly ₹1,000 a year | Required for WhatsApp webhooks |

These are planning ranges. Confirm with providers.

### 2.4 Implementation costs as a project (estimates)

Assumes a small team in India. Monthly team cost is the biggest line. Ranges are planning figures, not offers.

| Phase | Work | Team (example) | Indicative cost |
|---|---|---|---|
| 0. Validation (6 to 8 weeks) | Pilot agreement with one bank or NGO; outcome metric agreed; Hindi review by field staff; legal opinion on research and advice | 1 product lead, 1 field or language lead, part-time lawyer | Lawyer fees plus 2 people's time; largest unknown is legal |
| 1. Hardening (6 to 8 weeks) | Accounts and login instead of one saved setup; per-user data; backups; monitoring; security review; Twilio production account and approved templates | 2 engineers, 1 designer part-time | Engineer time plus Twilio and template approval fees |
| 2. Data licensing (ongoing, start early) | Licensed Indian market data; NSE data terms; Google News and GDELT terms review | Business owner | Licence fees vary widely; obtain quotes |
| 3. Pilot operations (3 to 6 months) | Field support, Hindi content updates, scheme-data upkeep (schemes change), monitoring | 1 field coordinator, 1 engineer part-time | Team cost plus hosting |
| 4. Scale-up | Multi-region hosting, managed database, support desk, compliance reporting | Grows with contracts | Funded by pilot revenue |

Cost categories not yet priced: data licences, legal and SEBI opinion, security audit, insurance, and translation review.

### 2.5 Total cost in one sentence

Running the prototype costs almost nothing. Running it as a service for a pilot costs a small server plus a small team plus data licences and legal work. The data licence and legal work are unknown until quotes come back, and they can be the largest line.

---

## 3. Every data set in the prototype, and where it comes from

Status key: **Live-ingested** = pulled by `tools/ingest.py` into `data/snapshot.db`. **Static** = written into the code by hand. **Illustrative** = a sample, labelled as one in the app.

### 3.1 Market data (snapshot)

| Data | Source | Adapter | Status | Use | Point-in-time tier |
|---|---|---|---|---|---|
| Daily prices (OHLCV), 57 symbols, 2019 to 2026 | Yahoo Finance via yfinance (NSE `.NS` and some US tickers) | `ingest/sources.py` | Live-ingested, frozen snapshot | Charts, tip checker volatility, research, X-ray | exact |
| Fundamentals (ratios, growth, cash, debt) | yfinance | same | Live-ingested | Company research, tip fundamentals | snapshot_only for current ratios; approximated for quarterly (45-day lag) |
| US company facts | SEC EDGAR company facts | `ingest/sources.py` | Live-ingested | US names in the universe | exact |
| Company news | Google News RSS | same | Live-ingested | Research desk evidence | exact |
| Global news events | GDELT | same | Live-ingested | Research desk evidence | exact |
| Macro series | FRED (US), and RBI and NSE series via jugaad-data | same | Live-ingested | Context in research and learn | approximated |
| NSE announcements, delivery %, bulk deals | nsepython | same | Live-ingested | Research evidence | exact |
| Universe list (tickers, sectors, names, benchmark) | `config/universe.yaml` (hand-written) | config | Static | Sector maps and screens | n/a |
| Extra stocks the user searches | yfinance on demand, NSE listing CSV | `analysis/stocksearch.py` (`archives.nseindia.com/content/equities/EQUITY_L.csv`) | Live, on demand, kept separate | Research on any listed stock | as above |

Known data gaps from `docs/DATA.md`: some tickers return 404 on Yahoo; a demerged company's history must be mapped to its successor; prices are a snapshot, not live.

**Licence warning.** yfinance scrapes Yahoo Finance, whose terms restrict commercial use. NSE data is also governed by its own terms. A paid product needs a licensed data feed. This is the first thing to fix before any charge.

### 3.2 Government schemes (rural tools)

Source: each scheme's official portal, as listed in `backend/rural.py`. The text (benefit, eligibility, documents) is **static, hand-written**, and must be checked against the portal before each pilot. Schemes change with budgets.

| Scheme id | Scheme | Portal named in the code | What the app uses it for |
|---|---|---|---|
| pm_kisan | PM-KISAN income support | pmkisan.gov.in | Payment-status and papers checklist |
| kcc | Kisan Credit Card | pmkisan.gov.in (KCC) or your bank | Credit-cost comparison, eligibility and documents |
| pmfby | PM Fasal Bima Yojana (crop insurance) | pmfby.gov.in | Claim and policy checks |
| pmjjby | PM Jeevan Jyoti Bima Yojana | jansuraksha.gov.in | Insurance check |
| pmsby | PM Suraksha Bima Yojana | jansuraksha.gov.in | Insurance check |
| apy | Atal Pension Yojana | npscra.nsdl.co.in or your bank | Pension planning and the saving example |
| pmjay | Ayushman Bharat PM-JAY | pmjay.gov.in; helpline 14555 | Health scheme check |
| nrega | MGNREGA | nrega.nic.in | Work and payment checks |
| eshram | e-Shram registration | eshram.gov.in | Registration checklist |
| pmsym | PM Shram Yogi Maan-dhan | maandhan.in | Pension scheme check |
| pmay_g | PM Awas Yojana (Gramin) | pmayg.nic.in | Housing scheme check |
| ujjwala | PM Ujjwala Yojana | pmuy.gov.in | LPG scheme check |
| oap | Old-age and social pensions (NSAP) | nsap.nic.in or state portal | Pension check |
| ssy | Sukanya Samriddhi Yojana | indiapost.gov.in or any bank | Savings-scheme rate and tax explanation |
| scholar | National scholarships | scholarships.gov.in | Education scheme check |
| mudra | PM MUDRA loans | mudra.org.in or your bank | Small-business loan check |
| vishwakarma | PM Vishwakarma | pmvishwakarma.gov.in | Artisan scheme check |
| svanidhi | PM SVANidhi | pmsvanidhi.mohua.gov.in | Street-vendor loan check |
| jandhan | PM Jan Dhan Yojana | pmjdy.gov.in | Bank account and zero-balance rules |
| shg_nrlm | SHG and NRLM (DAY-NRLM) | aajeevika.gov.in | SHG bank-linkage explanation |

Rates quoted in the rural tools, such as KCC at about 7% a year (about 4% with prompt-repayment relief), are **static**, from the scheme terms as summarised in the code. Verify with the bank or scheme text before quoting.

### 3.3 Interest and return reference rates

| Constant | Value | Source as stated in code | Used in |
|---|---|---|---|
| Bank deposit benchmark | about 7% a year | Stated in `analysis/tipminds.py` (`RISK_FREE = 0.07`) and in the offer checker (`SAFE_BENCHMARK = 7.0`). A rough round figure, not a live rate. | Tip panel scale; offer checker |
| Long-run equity return | about 12% a year | `analysis/tipminds.py` (`EQUITY_LONG_RUN`), labelled "only for scale" | Tip panel scale |
| Best sustained professional record | about 25% a year | `analysis/tipminds.py` (`ELITE_SUSTAINED`) | Tip panel scale |
| Informal lending | 2 to 5 rupees per 100 a month | Commonly reported range; the code converts monthly to yearly (×12) | Moneylender check |
| Fixed-deposit and post-office rates | Bank FD about 7%; post-office schemes about 7.5% | `backend/rural.py` (`SAFE_YEARLY`) | Comparisons. **Static: update each quarter from RBI and India Post published rates.** |

### 3.4 Tax rules (calculators)

| Rule | Value | Source as stated in code | File |
|---|---|---|---|
| Short-term capital gains (listed equity) | 20% | Section 111A | `analysis/tax.py` |
| Long-term capital gains (listed equity) | 12.5% | Section 112A | `analysis/tax.py` |
| LTCG exemption | ₹1,25,000 a financial year | Section 112A | `analysis/tax.py` |
| Long-term holding period | 365 days | Listed equity | `analysis/tax.py` |

Tax rules change with budgets. Verify against the current Income Tax Act text and the latest Finance Act each year. The rates above are the rates the code uses as of the last update.

### 3.5 Scam, helpline and regulator references

| Item | Source | Status |
|---|---|---|
| National cyber-fraud helpline 1930 | Government of India cyber-crime helpline | Static reference in `backend/recovery.py`, `backend/assistant.py`, `backend/rural.py` |
| cybercrime.gov.in (National Cyber Crime Reporting Portal) | MHA | Static |
| Nine scam scripts; scripted rehearsal callers; red-flag patterns | Written for this project from publicly reported scam types | Static, hand-written. Review regularly; scam types change |
| SEBI SCORES grievance portal, sebi.gov.in intermediary check | SEBI | Static reference |
| RBI Sachet portal (illegal deposit schemes) | RBI | Static reference |
| MCA company check (mca.gov.in) | Ministry of Corporate Affairs | Static reference |

### 3.6 Financial literacy and market-participation figures (context, not calculations)

| Figure | Source as cited in `docs/CONTEXT.md` section 9 | Status |
|---|---|---|
| 27% of adults financially literate; 24% rural | NCFE Financial Literacy and Inclusion Survey 2019 | Cited, dated |
| Cyber-fraud losses about ₹22,845 crore in 2024; about 19 lakh NCRP financial-fraud complaints | I4C figures as reported in a 2025 industry summary | Cited as reported; quote the official I4C release before a pitch |
| Informal lending practices | SIDBI study on informal sector lending, 2019 | Dated; re-check before quoting |
| About 9.5% of households in the market; rural about 6% | SEBI Investor Survey 2025 | Verify on sebi.gov.in before quoting |

### 3.7 Sample and illustrative data (not real)

| Data | Where | What it is |
|---|---|---|
| Eight sample mutual funds with holdings and fees | `backend/practice.py` (`FUNDS`) | Rounded, typical of their type; **not real factsheets**. The app says so. Replace with AMC portfolio disclosures before any real use. |
| Sample portfolios for X-ray and practice | `config/policies.yaml`, `risk/seed.py`, `backend/practice.py` | Illustrative |
| Scam-call scenarios (`kyc`, `police`, `invest`) | `backend/practice.py`, `backend/practice_hi.py` | Scripted for training |
| Tip-test samples | `docs/TIP_TEST_SAMPLES.md` (generated by `tools/tip_samples.py`) | Synthetic test inputs |
| Setup prices (₹199, ₹299, ₹99, ₹499, ₹597 baskets) | `backend/setup.py` | **Dummy** for the pitch; nothing is charged |

### 3.8 User data (stays on the machine)

| Data | Where it lives | Leaves the machine? |
|---|---|---|
| Typed and spoken questions | Process memory; audio is not stored | No |
| Portfolio, cost basis (lots), saved funds, watches | SQLite tables `lots`, `portfolios`, `my_funds`, `watches` | No |
| Paper-trade audit record | SQLite `paper_ledger` (hash-chained) | No |
| Setup choice | SQLite `app_setup` | No |
| Public market data requests | Yahoo, SEC, Google News, GDELT, FRED, NSE | Only the ticker or series requested |
| WhatsApp messages (when live) | Twilio and Meta | Yes, through the provider; needs a privacy notice |

---

## 4. Open items before any charge or pilot

1. **Data licence:** replace or license the Yahoo and NSE-scraped data for any paid use.
2. **Legal opinion:** SEBI registration needed for the research desk or tip checker if paid; RBI rules if any lender is involved; DPDP Act 2023 duties for personal data and consent.
3. **Schemes and rates:** re-check every scheme portal, FD rate and tax rule before each pilot; add a "last checked" date to each.
4. **Funds:** replace the eight sample funds with AMC disclosures before showing real fund data.
5. **Outcome data:** agree with the pilot partner what will be measured (scams reported in first hour, credit-cost conversations, complaints) and build the counter into the product.
6. **Prices:** get written rate cards from Twilio, the hosting provider and any data vendor; replace every estimate in section 2.
