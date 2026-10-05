# JARVIS // ALPHA OS — 1-Day Solo Build Spec

**Positioning:** Not an alpha engine. A **glass-box governance OS** for AI investment
decisions — provenance, point-in-time replay, deterministic risk containment.

**Thesis line for the demo:** *"We deliberately run a small local model. If our
governance layer only works with a frontier model, it isn't a governance layer."*

**Constraints:** solo dev, ~16h, 100% free/open-source, local Ollama, offline-capable.

---

> This is the original hackathon plan. The current, complete description is [docs/CONTEXT.md](docs/CONTEXT.md).

## Non-negotiables

1. **Frozen snapshot.** Zero live API calls during the demo. One ingestion run → SQLite.
2. **Point-in-time.** Agents never touch raw tables. All reads go through
   `PointInTimeStore` which enforces `published_at <= sim_clock`. Lookahead is
   structurally impossible, not promised.
3. **Citations or death.** An agent claim with zero `source_ids` is dropped in code
   before it reaches the risk engine. This is the anti-hallucination mechanism.
4. **Risk engine is pure Python.** No LLM anywhere near it. Deterministic, unit-tested,
   returns remedial deltas not just rejections.
5. **Text input works from hour 6 and is never removed.** Voice is additive.

---

## Stack (all free)

| Layer | Choice | Cut from blueprint |
|---|---|---|
| Orchestration | `asyncio.gather()` + 40-line orchestrator | ~~LangGraph~~ |
| Vector search | SQLite + numpy cosine, `nomic-embed-text` via Ollama | ~~Qdrant~~ |
| DB | SQLite | ~~PostgreSQL~~ |
| Frontend | Vite + React + @react-three/fiber | ~~Next.js~~ |
| LLM | Ollama: `llama3.1:8b` (analyst desks) + `phi3:mini` (intent router) + `nomic-embed-text` | ~~paid API~~ |
| STT | faster-whisper, local, WebSocket audio | — |
| TTS | Piper or Kokoro, local streaming | — |
| Charts | lightweight-charts | — |

## Data sources (6, all free, no card)

| # | Source | Role | Market |
|---|---|---|---|
| 1 | yfinance | OHLC, fundamentals, options chain | NSE `.NS` + US |
| 2 | nsepython / jugaad-data | corporate announcements, delivery %, bulk deals, RBI macro | **India deep** |
| 3 | SEC EDGAR `companyfacts` (no key) | authoritative fundamentals | US shallow |
| 4 | GDELT DOC 2.0 | global news tone, good Indian coverage | both |
| 5 | Google News RSS | per-ticker headlines, no key | both |
| 6 | FRED | rates, CPI, yield curve | macro |

**`Signal` primitive** — every source normalizes to this. It is what makes multi-source
tractable AND auto-populates the provenance graph:

```
Signal(value, as_of, published_at, source_uri, source_type, confidence, latency_class)
```

## Agents — 4 prompts, ONE code path

Fundamental · Quant · Narrative · **Red Team** (must argue the strongest case against).

- Strict JSON out, Pydantic validation, retry on parse failure.
- Every claim carries `source_ids[]`. Uncited → dropped.
- Run in parallel via `asyncio.gather`.
- **Conviction = f(agreement, evidence quality, disagreement resolution).**
  Unanimity from correlated LLM agents is a bug → flag `GROUPTHINK — LOW INFORMATION`.

## Risk firewall

Declarative policy spec (YAML/Pydantic), versioned. Limits: position ≤5%, sector ≤30%,
cash ≥10%, drawdown trigger 5%.

On breach: emit machine-readable violation **plus the remedial delta** — solve for max
allowable shares ("reduce to 62 shares to hold sector at 29.8%").

## UI

- **Phase 0 — cold boot.** Terminal spew, subsystem checks, sources coming online. 10s,
  trivially cheap, sets the tone harder than anything else.
- **Orb → graph must be a real morph.** Shared `BufferGeometry`, animated positions.
  A crossfade reads as two components; a morph reads as one machine thinking.
  This is the money shot — budget 3 uninterrupted hours.
- **Audio-reactive** via Web Audio FFT → shader uniforms. States: idle / listening /
  thinking / speaking / alert.
- **Telemetry rail** always on: agent states, source latencies, tick counts. Numbers that
  never stop moving are what say "real system".
- **Scrubber is permanent furniture** — keeps the Time Machine visible in every phase.
- Palette `#020105`, corner brackets, 1px rules, monospace, cyan/violet/amber, restrained
  bloom. Restraint is what separates "Iron Man" from "gamer RGB".

## Reduced / faked (be honest about it on screen)

- Calibration memory → backfilled once, panel labeled `BACKFILLED`.
- Policy simulator → one canned what-if (sector cap 30→35%), precomputed.
- US depth (13F, Form 4, full-text EDGAR) → cut.

## Hour plan (solo)

```
H0–1     DONE - event contract, schema, Signal, PIT store, risk engine, 24 tests
H1–3     Ingestion → frozen snapshot                   (run it, walk away, keep coding)
H3–4     DONE - closed-form remedies, policy simulator, 32 tests
H4–5.5   DONE - 4 desks, citation gate, conviction/groupthink, 14s wall clock
H5.5–6.5 DONE - FastAPI + WS, intent router, demo script runs end to end
H6.5–10  DONE - orb, real BufferGeometry morph, bloom, HUD
H10–11.5 DONE - risk card, verdict meters, claims, chart, positions
H11.5–12.5 DONE - scrubber + era marks
H12.5–14 DONE - faster-whisper local STT, grammar repair, on-device TTS
H14–15   Demo script, hotkeys 1–5, reset button, offline replay
H15–16   Buffer (you will need all of it)
```

**Solo rules:** Freeze the WebSocket event contract in hour 1 and build the frontend
against mock events immediately — you are demoable from hour 4 and every later step just
swaps a mock for something real. Never sit and watch a download or an ingest run.

## Demo script (3 min)

1. Cold boot. Sources come online.
2. *"JARVIS, analyse TCS."* Orb morphs to provenance graph, 4 desks deliberate,
   Red Team dissents, conviction score lands.
3. Click a graph node → the actual sentence from the source highlights. **Glass box.**
4. Propose the trade → firewall **blocks** it, shows the exact remedial delta.
5. *"JARVIS, rewind to 20 February 2020."* Everything rewinds. Agents re-deliberate
   knowing nothing of what's coming. **No competing repo can do this.**
6. Close on the counter: claims rejected for missing citation, violations blocked.

## Framing

Paper trading only. No broker execution. Research and decision-support tool,
not investment advice. Keep this line in the product and the deck — it is what makes
the risk-firewall story coherent rather than reckless.


## Usability pass (post-plan)

- 56-ticker universe (NIFTY 50 + benchmark), 103k price rows
- Bring-your-own-portfolio: presets, stock picker, broker paste-parser
- Policy profiles: retail / balanced / fund — same engine, reachable limits
- Portfolio X-ray: bounded score formula, capped findings, effective holdings
- Stress tests: 4 historical windows + 4 labelled what-ifs
- Plain-language `/ask`: computed numbers, templated words, glossed jargon
- Simple / expert mode split
- 133 tests, dry run 28/28
