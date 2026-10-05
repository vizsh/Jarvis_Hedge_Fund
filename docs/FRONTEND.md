# Frontend

React 18 + Vite + TypeScript, with Three.js (`@react-three/fiber`, `drei`, `postprocessing`) for the orb and `lightweight-charts` for price charts. State is `zustand`. There is no router library: a tiny hash router is enough.

`npm run build` writes `frontend/dist`, which FastAPI serves at `/` (so the app is one process on port 8000). `npm run dev` serves with hot reload on `:5173` and proxies API routes to `:8000`; **every backend route must be listed in `vite.config.ts`**, or the dev server answers with the SPA index and the feature silently never works.

## Pages (`src/pages`, hash routes in `lib/router.ts`)

| Route | Component | Contents |
|---|---|---|
| `#/` | `Home` (Pages.tsx) | the three pillars and entry points |
| `#/portfolio` | `Portfolio` | X-ray, history, profiles, builder |
| `#/protect` | `Protect.tsx` | `TipScanner`, `TaxShield`, `PanicSim` (Demos), `WatchlistPanel` |
| `#/learn` | `Learn` (Pages.tsx) | `GoalFan`, `AskPanel`, glossary, `StressPanel`, "every number is a door" |
| `#/practice` | `Practice.tsx` + `PracticeMore.tsx` | `OverlapChecker`, `FeeDrag`, `EmergencyMeter`, `WeeklyDigest`, `ScamCall` |
| `#/govern` | `Govern.tsx` | `Firewall`, `RebalanceSim`, `Ledger`, `TamperDemo` |
| `#/research` | `Research` | desks, conviction, claims, calibration, sources, time machine |
| `#/assistant` | `Assistant` | orb, `ChatThread`, `JobsLauncher`, `CommandBar` |

`#/practice?a=largecap_a&b=bluechip_b` style **query parameters** pre-fill a tool (read with `hashParams()`); the chatbot's "Open the ... visual" buttons use this.

## Components worth knowing

| Component | Role |
|---|---|
| `AnswerCard` | renders any assistant answer: headline, fact chips, table, bullets, action, "how it was worked out", tool buttons, follow-up chips; hosts the **inline visuals** (`FeeDrag`, `EmergencyMeter`, `GoalFan`, `PanicSim`, `WeeklyDigest`, `ScamCall`, each with a `compact` mode) |
| `ChatThread` | the conversation panel, the Voice + text switch, starter chips |
| `CommandBar`, `VoiceBar`, `VoiceInput` (`MicButton`, `OrbMic`) | typing, transport controls, microphone |
| `Dock` / `TopNav` (`Nav.tsx`) | the always-present assistant dock, language switch, voice picker |
| `Flow` | the guided-job runner |
| `DrillDown` (`Num`) | the "every number is a door" modal |
| `Orb.tsx` + `orbShaders.ts` | 26,000-particle orb that morphs into the provenance graph |

## State (`src/lib`)

| Module | Holds |
|---|---|
| `store.ts` | what the backend believes: fund, clock, phase, desks, speech line, transcript |
| `chat.ts` | the chat messages and the **voice-replies** preference |
| `lang.ts` | `useLang` (`en`/`hi`), per-language voice choice, `CLIENT_ID`; announces the language to the server on load |
| `i18n.ts` | `useT()` -> `{hi, t(en, hi), d(text)}`; error and job translations |
| `speak.ts` | the speech engine (one `<audio>`, queue, prefetch, latches, `speechGeneration()`, `voiceReplies`) |
| `voice.ts`, `bargein.ts` | microphone controller (idle / starting / listening / processing); optional talk-over interrupt |
| `socket.ts` | WebSocket + `send(text, shown?)`, `startMic/stopMic(raw?)`, event filtering by `cid` and language |
| `guide.ts` | flow runner, palette, drill-down and report overlay state |
| `ui.ts`, `router.ts`, `types.ts` | small UI flags, the hash router, shared types |

## Styling

Plain CSS files per area, no CSS-in-JS: `styles.css` (base HUD), `styles-pages.css` (page layouts, assistant stage), `styles-practice.css` (fund ribbons, fee/emergency visuals, scam phone), `styles-chat.css` (chat and answer cards), `styles-desk.css`, `styles-portfolio.css`, `styles-guide.css`. Class names are scoped by feature; legacy collisions were resolved by renaming (`split -> sim`, `verdict -> vbanner`).

## Writing a bilingual component

```tsx
import { useT } from "../lib/i18n";

function Example({ data }: { data: any }) {
  const { hi, t, d } = useT();
  return (
    <section className="card">
      <h2>{t("Fee drag", "फ़ीस का असर")}</h2>           {/* fixed text */}
      <p>{d(data.explanation)}</p>                      {/* backend English -> Hindi via /translate */}
      <button>{hi ? "भेजें" : "Send"}</button>
    </section>
  );
}
```

Rule: send **English questions** to the router even when showing a Hindi label (`send(question, shownLabel)`), and never transliterate company names.

## Accessibility and responsiveness

Designed for 1440x900; rails narrow below 1360, low-value stats drop below 1180, the left rail folds at 1040, and everything stacks with the orb on top at 820. The chat panel becomes a full-width block on narrow screens. Interactive charts have `aria-label`s; the Stop control is always visible while speaking. The paper-only disclosure never disappears at any size.

## Design system (the "Jarvis, money plainly" theme)
`frontend/src/styles-theme.css` is the single design layer, loaded after everything else. World: a private-bank ledger at night. Warm graphite surfaces, ivory text, **one marigold accent** used only for what the person can act on; green and coral are reserved for meaning (good / bad), indigo for a secondary data series. Display type is **Fraunces** (soft serif) for headings and big figures; UI type is **Instrument Sans** with tabular numerals; Noto Sans Devanagari covers Hindi. No scanlines, no grid, no glow, no uppercase labels. Icons are a drawn set (`components/Icon.tsx`, one 1.6 stroke), not emoji.

Charts (all interactive, keyboard-reachable, reduced-motion safe):
- `components/Chart.tsx`: portfolio value vs benchmark (TradingView lightweight-charts, themed), with 1M/3M/6M/1Y range chips and a live crosshair readout.
- `components/charts/FanChart.tsx`: goal range-of-outcomes (bad / typical / good paths, goal line, hover or arrow-key readout, animated reveal).
- `components/charts/AllocationMap.tsx`: squarified treemap by sector then company; a sector over the person's own cap is outlined in coral.

## Light and dark themes
`lib/theme.ts` + the sun/moon button in the top bar. The choice follows the operating system until you press the button, then is remembered (`jarvis.theme`); an inline script in `index.html` sets it before first paint so there is no flash. Both themes are token sets in `styles-theme.css` (`[data-theme="dark"]` / `[data-theme="light"]`); translucent whites in older CSS are now `rgb(var(--wash) / a)` so they flip to translucent ink in light mode. The canvas chart re-reads its colours on the `jarvis:theme` event. The 3D assistant stage and the WhatsApp phone mock are designed dark and stay dark in both.

## The analyst arena (Research page)
`components/research/Arena.tsx` draws what the backend actually does when a company is analysed, driven only by real events, in the order they happened: dated **evidence** (grouped prices / company numbers / headlines / filings) is shared with **three analyst desks that reason at once** (pulses travel along the lines while a desk is thinking); each **claim** that survives the citation gate flies to its side of the **committee balance** (supports / cautions), a claim without a valid citation is shown being **dropped**; then the **Red Team** (waiting until the analysts finish) reads their conclusions and argues the opposite side; the balance tilts with the weight of what survived and the **plain summary** node lights up. A five-step strip, live counters (evidence shared, claims kept, dropped, analyst agreement, evidence quality) and a feed of the latest claims accompany it; hovering a claim lights the evidence it cites.

Backend support: `agents/orchestrator.run_desks(on_event=...)` reports `analysts_start`, each `desk_done` the moment that desk finishes, and `red_start`; `pipeline.do_investigate` turns them into `agent.state` (including `waiting`), `claim`, `claim.rejected` and the new `consensus` event as they happen instead of after all desks have finished.

## Govern page
A permanent "Your limits, right now" header draws the three rules the firewall enforces (largest single stock, largest industry, cash floor) as bars with the limit marked, then a segmented control switches between Check a trade, Rebalance, Audit record and Tamper test, so the page is no longer one 5,000 px scroll.

## Practice and Protect: tool decks
Both pages open with a row of selectable tool cards (`components/ToolDeck.tsx`) and show one tool at a time beneath it, instead of every tool stacked in a long scroll. Protect leads with the urgent one ("I think I was scammed"), tinted coral. A deep link such as `#/practice?tool=fee` or `#/protect?type=upi_card` opens the right tool, which is how the guide lands on them.

## Research summary: technical readings
Besides fundamentals, the plain summary now reads the price history the way a technician would, and explains each reading in a sentence without turning it into a signal: price against its 50- and 200-day averages, a momentum reading (RSI) for a fast run-up or drop, one-year performance against similar companies (separates "the sector moved" from "this company moved"), unusually heavy trading, and distance from the year's high and low. Price-based readings are capped at three, because they move together and would otherwise count one fact several times.

## Research summary: what it reads and how it is trusted
`analysis/proscons.py` turns measured facts into plain pros and cons (no buy/sell signal). Beyond price and chart it reads
growth, cash conversion and free cash flow, debt, interest cover, liquidity, dividend and payout, Piotroski and Altman scores
(skipped for banks), the company's own past P/E range and growth-adjusted P/E, a peer rank table, and ownership (insider and
institutional share; a trend appears once two snapshots at least three weeks apart exist; pledging is declared missing).
Every line carries `confidence` (solid/light/weak from independent data kinds, sample size and age) and `basis`; the page
also shows how old each data kind is and how many checks had data. The extra data comes from `ingest/enrich.py`
(`python -m tools.enrich` for the whole universe; `ingest.ondemand.add_stock` runs it for new stocks). The endpoint reads at
the real clock, not the simulation clock, because enrichment is stamped when it is fetched.

## The assistant: understanding, answers, and guided tours
`backend/understand.py` reads the whole sentence before any keyword rule: it separates (1) questions about the app, (2) requests to
analyse or compare companies, (3) general money questions, then falls back to the calculator tools. A local model, when used at all, only
PICKS from a closed list; it never writes an answer or a figure.
- **Feature questions** ("how do I use the fee slider", "help me understand this feature") return a structured answer and start a guided
  tour. `backend/tours.py` (+ `tours_parts.py`) is the single source of the steps in English and Hindi; `lib/tour.ts` and
  `components/TourOverlay.tsx` play them: open the page, press the tab, spotlight each part, read the caption aloud. "This feature" means the page
  that is open (the client sends its route). `GET /tours`, `GET /tours/{id}?lang=`.
- **Companies**: `analyse X` / `compare X and Y` answer in chat with facts, good points and watch-outs (each with a confidence mark), peer ranks
  and a chart (`backend/charts.py`: live from Yahoo Finance when online, saved snapshot otherwise, labelled with its date), plus an optional
  TradingView embed. The Research page's search sends `investigate X`, which still starts the analyst desks.
- **Knowledge**: `backend/knowledge.py` holds checked, hand-written explanations (EN/HI) for common money questions; `backend/scams.py` holds one
  script per scam type (bank OTP, digital arrest, courier, remote app, task job, loan app, prize, SIM/utility, investment group).
- Layout: a question and its answer are one block; the answer card shows its kind, the short answer, figures, chart/table, steps, a caution, tools and follow-ups.
