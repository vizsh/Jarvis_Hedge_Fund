# Technical overview: stack, engines, agents and flows

Read with [ARCHITECTURE.md](ARCHITECTURE.md) (diagrams and invariants) and [CONTEXT.md](CONTEXT.md) (what each feature is for).
This page answers three things: which technology is used where and why, which component makes which decision, and how each feature flows.

## 1. Technology stack and why

| Layer | Technology | Where | Why it was chosen |
|---|---|---|---|
| Backend API | FastAPI, uvicorn (one process) | `backend/app.py` (about 110 routes, `/ws` WebSocket) | Typed request models, async, WebSocket for live answers, one process to run on a laptop |
| Storage | SQLite (WAL) | `data/snapshot.db`, paper ledger, setup, lots, watches | No server to install; one file a demo can carry |
| Point-in-time data | `core/pit.py` | every calculator reads through it | Filters on `published_at <= sim clock`, so no figure can see the future |
| Calculators | Pure Python, standard library (`analysis/*.py`, `backend/rural.py`) | the numbers | Deterministic and testable; the rural file also runs in the browser through Pyodide |
| Frontend | React, TypeScript, Vite, zustand stores, hash routing | `frontend/src` | Fast builds; hash routes work from a static build and an offline pack |
| Live charts | recharts, optional TradingView tab, Yahoo Finance when online | `backend/charts.py`, `components/charts` | Charts for the user; the saved snapshot is used when offline |
| Speech in | faster-whisper (local), MediaRecorder with a timer for voice activity | `voice/stt.py`, `POST /stt` | Hindi and English on the machine; no audio leaves it |
| Speech out | Kokoro or Piper (local) | `backend/tts.py`, `POST /tts` | Spoken answers without a cloud voice service |
| Local language model | Ollama, `llama3.1:8b` (optional) | `agents/llm.py` | Used only to pick among closed options and to write research desk notes; not required |
| Offline | Service worker, Pyodide running the rural calculator file | `frontend`, `/offline` | Basic phones on poor networks; the rural calculators keep working |
| Messaging | WhatsApp and SMS simulator; Twilio webhook (`/twilio/webhook`) | `backend/messaging.py`, `pages/WhatsApp.tsx` | Same answers as the web; real delivery needs a provider account |
| Tests | pytest (532 tests); TypeScript check and Vite build | `tests/`, `docs/TESTING.md` | Guards numbers, wording rules and the frozen event contract |

## 2. Who decides what

The backend has three layers. Each has its own rule (ARCHITECTURE.md section 2):

| Layer | Components | Rule |
|---|---|---|
| **Truth** (numbers) | `analysis/*.py`, `risk/engine.py`, `backend/practice.py`, `backend/ledger.py`, `backend/digest.py`, `backend/rural.py` | Pure and deterministic. No model is imported here. |
| **Meaning** (what was asked) | `backend/understand.py`, `backend/assistant.py`, `backend/intents.py`, `backend/router.py`, `backend/guide.py` | Rules first; a model may only pick one known intent |
| **Words** (how it is said) | `backend/vernacular.py`, `hindi_rules.py`, `hindi_page_rules.py`, `glossary_hi.py`, `flows_hi.py`, `practice_hi.py`, `knowledge.py`, `scams.py` | Hand-written templates; numbers are placed by code, never by a translator |

A translation cannot change a number: a `numbers_preserved` guard rejects any translation that changes a figure.

## 3. The agents and engines, one by one

Nothing in the prototype acts on its own in the world. "Agents" here means the small deciders below. Each is either fixed code or a checker over a closed list.

### 3.1 Question understanding (`backend/understand.py`)
- Reads the whole sentence and separates four kinds of request, in this order: a question about the app (guided tour), a company (research or comparison), a general money question (checked explanation), or a personal number question (calculator). Tip messages go to the tip checker; messages about a loss go to the recovery coach.
- Only if none fits does the older rule router run (`backend/assistant.py`), then the optional local model.
- Decision made: which handler owns the question. Output: a handler name, never an answer.

### 3.2 Rule router and intents (`backend/assistant.py`, `backend/intents.py`, `backend/router.py`)
- Regular expressions with word boundaries for each intent (moneylender, fee drag, tax, scam and so on). Tests guard the wording.
- Decision made: which calculator to call, with inputs parsed from the text.

### 3.3 Optional local model (`agents/llm.py`)
- Ollama, `llama3.1:8b`, runs only if installed. It is used in two places: picking one intent from a closed list, and writing the research desk notes.
- If Ollama is missing, every answer still comes from rules, and the page says so.

### 3.4 Tip panel: eight specialists (`analysis/tipminds.py`)
Each specialist reads the same tip and returns a verdict with a weight. These are fixed functions, not models talking to each other:
1. **Feasibility**: first-passage model, P(touch) = 2 × (1 − Φ(ln(target/price) / (σ√(days/365)))), with σ from the stock's own volatility. A fixed periodic return or a guarantee is flagged here.
2. **Fundamentals**: implied P/E at the target against the company's own history and peers.
3. **Technicals**: trend and range from the price series.
4. **Market structure**: liquidity and listing status.
5. **Source and incentive**: who gains if you act.
6. **SEBI rules**: registration and disclosure checks.
7. **Wording**: one witness among eight, with low weight (`analysis/scanner.py`).
8. **Consequence**: what acting could cost.

Two outputs are kept apart: the chance it is a scam, and how much real backing the idea has. The action is one of: ignore and report, ignore, verify first, research it yourself, or information only. Examples are in `docs/TIP_TEST_SAMPLES.md`.

### 3.5 Research desks (`agents/desks.py`, `agents/orchestrator.py`, `agents/evidence.py`, `agents/persist.py`)
- Three analyst desks: **Fundamental** (fundamental and macro evidence), **Quant** (quant evidence), **Narrative** (narrative and macro evidence). Each desk gets an evidence pack built from the point-in-time store.
- A **red team** (a forced sceptic) argues against the consensus.
- `fuse()` combines the desk reports. `apply_citation_gate()` drops any claim without a citation, and each drop is counted (`CLAIM_REJECTED`).
- Desks run concurrently (`run_desks`). The provenance graph shows which evidence each claim came from.

### 3.6 Company research summary (`analysis/proscons.py`, `ingest/enrich.py`)
- Rule-based. Each good point or watch-out is a fixed test on the company's numbers and price behaviour, with a basis and a confidence mark (solid, light or weak).
- Missing data is reported under "could not check", never filled in.

### 3.7 Risk engine (`risk/engine.py`, `risk/policy.py`, `risk/portfolio.py`)
- `RiskEngine.evaluate()` checks a proposed trade against the policy: largest single stock, largest industry, cash floor, and others.
- Returns a `RiskDecision` with violations, remedies (for example `max_allowable_shares`, the largest number of shares that passes) and a summary.
- Hard rule: `risk/` never imports an LLM.

### 3.8 Scam scripts and recovery coach (`backend/scams.py`, `backend/recovery.py`)
- Nine scam scripts matched by phrase patterns. The rehearsal simulator (`backend/practice.py`) answers with fixed scripted lines.
- Recovery coach: picks a checklist by situation (UPI, shared OTP, remote app, investment, digital arrest, link clicked), sorts the steps by the first-hour clock, and writes the drafts (phone script, cybercrime text, letter to the bank) from templates with blanks in [brackets]. Nothing is sent from the app.

### 3.9 Govern and audit (`backend/ledger.py`)
- Paper trades are appended to a hash-chained table; SQLite triggers refuse UPDATE and DELETE. Each entry stores a SHA-256 of its data plus the previous entry's hash.
- The tamper test edits a copy of a record and shows the chain breaking at that entry.
- Limit: the chain is tamper-evident on this machine. Whoever rewrites the whole chain can recompute every hash unless the latest hash is anchored outside the machine. Anchoring is not built.

### 3.10 Setup and route gate (`backend/setup.py`, `frontend/src/lib/setup.ts`, `App.tsx`)
- Decides which features the menu shows, from the saved basket and feature list (one row in `app_setup`).
- A route whose feature is not in the list renders the locked page instead of its screen.

## 4. Flows, feature by feature

**A. Asking a question (assistant and WhatsApp share it)**
```
text or voice -> /stt (Whisper, local) -> socket command {text, lang, cid}
  -> dispatch() in app.py -> understand.py (what kind of question?)
      - app question   -> tours.py (guided tour)
      - company        -> proscons.py / charts.py (point-in-time data)
      - tip message    -> tipminds.py (eight specialists)
      - loss message   -> recovery.py (first-hour checklist)
      - money question -> assistant.py rules -> calculator (analysis/*.py) -> knowledge.py or templates
  -> optional local model: may pick one intent only
  -> answer card (text, figures, chart, caution) -> SPEECH event tagged with cid
  -> browser ignores events for other tabs -> shown; optionally spoken via /tts
```

**B. Moneylender cost (`#/rural`)**
```
"5 rupees per hundred a month on 50,000" -> assistant.py rule (moneylender)
  -> rural.loan_cost(): 5% a month -> 60% a year (simple; compounding if asked)
  -> interest = 50,000 x 0.60 = 30,000 a year
  -> alternatives (rural.py ALTERNATIVES): KCC about 7% (about 4% with prompt repayment), SHG 12-24%
  -> comparison card in English or Hindi; no model writes the figures
```
Guided flows (`backend/guide.py`) ask one question at a time and release the flow after a second miss or a long sentence.

**C. Scam protection (`#/protect`)**
```
Scam scripts:   text -> scams.py phrase patterns -> matched script + warning signs
Tip checker:    text -> understand.py (tip) -> tipminds.py -> 8 verdicts -> action + evidence
Recovery coach: situation + time since loss -> recovery.py checklist (sorted by the first-hour clock)
                -> drafts from templates (phone script, cybercrime text, bank letter)
Rehearsal:      practice.py scripted caller -> user reply -> scored by fixed rules
```

**D. Research desk (`#/research`, paid)**
```
ticker -> ingest (point-in-time store; live fetch only if missing) -> evidence pack
  -> proscons.py plain summary (rule-based, with confidence marks)
  -> optional: 3 analyst desks + red team (agents/desks.py), run concurrently, with the local model
  -> fuse() -> citation gate drops uncited claims -> provenance graph
  -> page shows data age and how many checks had data
```

**E. Portfolio X-ray and practice (`#/portfolio`, `#/practice`, paid)**
```
holdings -> analysis/xray.py (grade, spread, overlap via HHI, allocation)
         -> analysis/tax.py, analysis/tools.py (fee drag: end-of-month contributions, monthly compounding)
         -> slider and chatbot call the same function, so they cannot disagree (tested)
```

**F. Govern and audit (`#/govern`, paid)**
```
proposed trade -> risk/engine.py evaluate(policy) -> RiskDecision (violations, remedies)
  -> if allowed: ledger.py appends a hash-chained entry (SQLite triggers block edits)
  -> audit page verifies the chain; the tamper test shows where it breaks
```

**G. Offline (rural pack)**
```
service worker caches the app shell -> rural calculators run in Pyodide from the same Python file
  -> same results as the server (tested)
```

**H. Setup and locked features**
```
first visit -> /setup (basket + switches) -> POST /setup -> app_setup row
menu, home tiles and route gate all read the saved list
locked route -> locked page -> "Add it" -> save -> open the feature
```

## 5. Frontend structure
`main.tsx` -> `App.tsx` (shell, hash router, route gate, locked page) -> pages by route. Stores (zustand): `store`, `chat`, `lang`, `ui`, `voice`, `guide`, `bargein`, `setup`, `tour`, `theme`. Styles: `styles-theme.css` (tokens for light and dark), then per-area files; `styles-rural.css` loads last for the village layer.

## 6. The frozen contract and invariants
1. `risk/` never imports an LLM.
2. Calculators are pure and shared: the page slider and the chatbot call the same function.
3. A translation may never change a number.
4. `core/events.py` is frozen (`PROTOCOL_VERSION = 1`): fields may be added, never removed or retyped.
5. Raw audio and portfolios never leave the machine. The only outbound calls are public market data and, if enabled, the messaging provider.

## 7. Known limits, stated plainly
- The local model is optional and was not installed in the last checks.
- WhatsApp is a simulator; real delivery needs a Twilio account.
- Hindi speech recognition has not been tested with rural speakers.
- Live prices and company data cover the 53-company universe well; other companies are fetched on demand and only partly covered.
- Setup is saved once per install, not per user; payments are dummy.
- The audit chain is tamper-evident, not tamper-proof (section 3.9).
