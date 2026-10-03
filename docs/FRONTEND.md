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
