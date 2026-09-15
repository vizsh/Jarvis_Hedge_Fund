# JARVIS // ALPHA OS

A **glass-box governance layer** for AI investment decisions. Not an alpha engine.

Published 2026 work is consistent: LLM trading agents do not beat buy-and-hold
out-of-sample, and their backtests are contaminated because the model has already read
the outcomes. So this project does not compete on returns. It competes on the thing you
can actually prove on stage — every number traceable to a source document, every
rejection explained by deterministic code, every decision replayable at a point in time.

> We deliberately run a small local model. If our governance layer only works with a
> frontier model, it isn't a governance layer.

**Paper trading only. No broker execution. Research and decision-support, not investment advice.**

## Quick start

```bash
pip install -r requirements.txt
python tools/ingest.py          # build the frozen snapshot (~5 min, GDELT is the slow part)
python -m pytest tests/ -q      # 32 tests
python tools/demo_risk.py       # the firewall, on real prices
python tools/demo_timemachine.py  # rewind to Feb 2020 and watch Covid arrive
python tools/demo_agents.py --clock 2020-03-23   # four desks, at the Covid bottom

python -m uvicorn backend.app:app --port 8000    # terminal 1 — backend
npm run dev --prefix frontend                    # terminal 2 — HUD at :5173
python tools/demo_backend.py                     # optional: script it from the CLI
```

Hotkeys: `T` presenter mode · `→` next step (fires its command) · `←` back (does not
fire) · `⏎` re-run current step · `R` play the recorded take · `E` stop it ·
`1`-`6` pin a phase · `B` cold boot · `/` type · hold `SPACE` to speak.

## The three pillars

| Pillar | Mechanism | Where |
|---|---|---|
| **Time Machine** | agents read only through a store that filters `published_at <= sim_clock`, so lookahead is impossible by construction | `core/pit.py` |
| **Glass box** | every claim must cite evidence ids; uncited AND fabricated citations are dropped in code before the risk engine sees them | `agents/desks.py`, `agents/evidence.py` |
| **Risk Firewall** | deterministic, LLM-free, and solves in closed form for the largest compliant trade | `risk/engine.py` |

## Layout

```
core/     events.py (FROZEN wire contract) · signal.py · db.py · pit.py
risk/     policy.py · portfolio.py · engine.py · seed.py
ingest/   base.py (PIT safety tiers) · sources.py (7 adapters)
agents/   evidence.py · desks.py · orchestrator.py · llm.py · schema.py · persist.py
backend/  app.py (FastAPI + WS) · pipeline.py · session.py · intents.py · bus.py
frontend/ three/Orb.tsx + orbShaders.ts (the morph) · three/layout.ts · components/ · lib/
tools/    ingest.py · demo_risk.py · demo_timemachine.py · demo_agents.py · demo_backend.py
tests/    60 passing
config/   policy.yaml (versioned limits) · universe.yaml (tickers, macro series)
```

## The snapshot

25,346 prices · 14,721 signals · 552 documents, across 14 tickers, 2019-06 to date.
Seven sources, all free, no API keys, no paid tier.

Every source declares its **point-in-time safety tier**, because pretending they are
equal would quietly reintroduce the lookahead we built the store to prevent:

| Tier | Sources | Meaning |
|---|---|---|
| `exact` | yfinance prices, SEC EDGAR, Google News, GDELT | real publication dates — replay is trustworthy |
| `approximated` | yfinance quarterly, FRED | statutory lag applied (SEBI LODR +45d) — directionally honest |
| `snapshot_only` | yfinance ratios | no history — stamped at ingest, vanishes on rewind by design |

That last tier is the one that catches people out. A rewound dashboard showing a
current P/E is not a time machine, it is a bug with good lighting.

## Status

- [x] **H0–1** frozen event contract, SQLite schema, `Signal`, `PointInTimeStore`
- [x] **H1–3** ingestion to frozen snapshot — 7 sources, 40k rows, PIT safety tiers
- [x] **H3–4** risk firewall with closed-form remedies + 32 tests
- [x] **H4–5.5** four desks, citation gate, conviction + groupthink scoring
- [x] **H5.5–6.5** FastAPI + WebSocket, intent router, full demo script end to end
- [x] **H6.5–10** orb, morph, HUD — 26k-particle core, bloom, provenance constellation
- [x] **H10–12.5** command centre panels + Time Machine scrubber
- [x] **H12.5–14** faster-whisper STT (local) + TTS + grammar repair
- [x] **H14–15** offline replay, presenter mode, scripted run order
- [x] **dry run** 28/28 invariants green, incl. out-of-order and panic cases
- [x] **calibration** desks scored against realised forward returns

See [SPEC.md](SPEC.md) for the full build plan.

## Design rules

1. The risk engine never imports an LLM. Ever.
2. Agents never touch raw tables — only `PointInTimeStore`.
3. Explanations are templates over measured numbers, never generated prose.
4. `core/events.py` is frozen: add optional fields, never retype or remove one.
5. Intents resolve by regex first; the model is a fallback, never in the scripted path.
6. Nothing executes without an explicit `execute` command, and approvals are re-gated
   against the book at execution time.
7. Trading costs are charged from day one — omitting them is how backtests inflate.


## What the gate catches, and what it does not

The citation gate rejects two things mechanically: claims with **no** citations, and
claims citing evidence ids that **do not exist** in the pack. The second is the
dangerous one, because a fabricated citation looks rigorous on screen.

It does not catch a **wrong inference from real evidence**. In testing, the Fundamental
desk cited revenue and net income and concluded the stock was "overvalued on P/E" -- but
there was no P/E in the pack at that clock. Valid citations, invalid reasoning. Mitigate
that with narrow desk briefs and computed indicators, and be honest that it is a
residual risk rather than a solved problem.

## A result worth showing

Rewound to **23 March 2020** -- the actual bottom of the Covid crash -- all four desks
returned maximally bearish, agreement 1.00, and the Red Team found no counter-case.
The system flagged `GROUPTHINK - LOW INFORMATION` and **halved** conviction rather than
confirming it.

That is the thesis in one screen. Four correlated agents agreeing told us nothing, on
the single best buying day of the decade. A system that grows more confident as its
correlated components agree fails hardest exactly when it is most certain.


## The morph

The orb and the provenance graph are the **same 26,000 particles**. A `uMorph` uniform
slides each one from its home on the shell to its seat in the graph, staggered by a
per-particle seed so the shell peels apart in waves and arcs rather than sliding.

A crossfade between two components reads as two components. A morph reads as one
machine changing its mind — and that difference is most of the effect.

The graph layout is deterministic radial (ticker → desks → claims → evidence), not
force-directed. A force sim on strictly levelled data mostly produces an expensive
hairball that settles differently every run, which is the last thing you want when you
are narrating it on stage.


## Voice

Push-to-talk, not streaming. Hold `SPACE`, speak, release — the browser records the
utterance, posts it to `/stt`, and **faster-whisper transcribes it on this machine**.

That last part is the point. The browser's Web Speech API is free and trivial to wire
up, but it uploads audio to Google, which would quietly break the on-prem claim the
whole project rests on. Synthesis stays local too — `SpeechSynthesis` reads the OS's
installed voices and renders on-device.

Two things make a 75MB model good enough:

- **`initial_prompt`** primes the decoder with our actual vocabulary. Unprimed, Whisper
  reliably turns "Mphasis" into "emphasis" and "NSE" into "and see".
- **`snap_to_grammar`** repairs the rest. The command grammar is tiny and known, so a
  transcript only has to be *close* — it gets pulled onto the nearest valid ticker or
  verb. The case that matters most is `buy`/`by`: pure homophones, and getting it wrong
  turns a trade command into nothing.

Below 0.45 confidence the transcript is shown but **not dispatched**. A misheard "sell"
is not a recoverable mistake.

Measured: 850–1400ms per command on CPU int8, transcript through to dispatched intent.


## Demo insurance

```bash
python tools/record_demo.py                                   # capture a golden take
curl -X POST "http://localhost:8000/replay/start?name=demo"   # or press R in the HUD
```

`record_demo.py` runs the whole script against the live backend and writes
`data/recordings/demo.jsonl`. Pressing **R** replays it with the original timing (long
pauses capped at 3s, because a 15s desk wait is dead air on stage).

A recording captures **state snapshots alongside the event stream**. Events alone are
not enough: the panels also fetch `/state`, so a replay would answer from a live session
that knows nothing about the take and the HUD would show 2026 numbers under a 2020
clock. Replayed clock changes are also mirrored onto the live session, so `/prices`
follows and the session is left where the recording ended.

**What replay removes:** the model, the mic, the network, the GPU. **What it still
needs:** `data/snapshot.db`, for the price chart — a local file that is already required
for the app to start. The real failure modes on the day are Ollama and the venue, not a
missing file.

Replay raises a visible amber **REPLAY** banner and flags `/health`. A fallback you
cannot distinguish from the live system is a lie waiting to be found, and "yes, that is
a recording — here is the live one" is a fine answer to have ready.

## Presenter mode

Press **T**. The narration for each step is shown in large type with the command that
sits behind it; `→` advances *and* fires the command, so your hands leave the keyboard
between beats and you are never typing while talking. `←` steps back without firing,
because you are usually re-saying a line, not re-running a trade.

The running order lives in `config/script.yaml` — edit the words there, not in the code.


## Calibration — the number we did not want

```bash
python tools/backfill_calibration.py     # ~4 min, 18 investigations across 6 regimes
```

Each investigation runs at a past clock, so the forward return needed to grade the call
is already in the snapshot. Result over 108 directional claims:

| Desk | N | Hit rate | Brier | Bear share |
|---|---|---|---|---|
| Red Team | 35 | 60.0% | 0.301 | 17% |
| Quant | 31 | 45.2% | 0.428 | 71% |
| Narrative | 25 | 36.0% | 0.446 | 96% |
| Fundamental | 23 | 34.8% | 0.391 | 74% |

**No desk beats a coin flip.** A Brier of 0.25 is what you score by always saying 50/50;
everything above it is worse than useless.

This is the single most useful result in the project, and it is exactly what the 2026
literature predicts. It is also the argument for the whole design: the governance layer
is not decoration wrapped around a good model, it is load-bearing, because **the model
has no edge**. That is why the firewall is deterministic code that no LLM output can
reach.

Honesty note carried in the API response and on screen: point-in-time control stops the
desks *seeing* the future in their inputs. It does nothing about the base model having
read 2020 during training. Treat these as an **upper bound** on skill.

## Dry run

```bash
python tools/dry_run.py       # 28 invariants, ~3 min
```

Walks the script, then does what a nervous presenter does: approve with nothing staged,
order 9999 shares, ask for a ticker outside the universe, double-fire a key, accept a
remedy that has expired, command during a replay.


## The Red Team, and what measuring it changed

Calibration caught a design error. The Red Team originally ran **in parallel with the
analysts and blind to them**, and produced bear claims 74% of the time — so whenever
the analysts were also bearish (17 of 18 backfill runs), the "dissent" agreed with the
consensus and the groupthink detector had nothing to catch. A dissenter that cannot see
what it is dissenting from is not a dissenter; it is a fourth analyst with a dramatic
name.

It now runs **second**, is shown the analysts' actual claims, and is told which stance
to oppose. Claims that side with the consensus anyway are dropped and counted as
`conceded` — a high count being the honest signal that no counter-case exists. Wall
clock is unchanged at ~14s, because Ollama serialises the calls either way.

Measured effect, same 18 backfill runs, same scoring:

| | v1 blind | v2 two-pass |
|---|---|---|
| Red Team bear share | 74% | **17%** |
| Red Team hit rate | 55.3% | **60.0%** |
| Red Team Brier | 0.334 | **0.301** |
| Overall bear share | 75% | 60% |

**And the caveat that matters more than the improvement:** swinging from 74% bear to
83% bull is still one-sided, just in the other direction. A desk that is always long in
a market that mostly rises will score ~60% without reasoning at all, so the Red Team's
better numbers are probably structural rather than analytical. The `one_sided` threshold
was widened to 0.80/0.20 specifically so the system flags this on itself — it now marks
both the Narrative desk (96% bear) and the Red Team (17% bear) as carrying no
information.

The v1 claims are kept in `claims_v1_blind_redteam` so the comparison stays reproducible.

## Responsive

Designed for 1440x900. Below that: rails narrow (1360), low-value top-bar stats drop
(1180), the left diagnostics rail folds away (1040), then everything stacks with the orb
on top (820). A separate short-screen rule handles 1366x768 laptops, declared **before**
the width rules — equal specificity means last-wins, and the stacked layout has to be
able to override it. The paper-only disclosure never drops at any size.


# ============================================================================
# The usability pass — who this is actually for
# ============================================================================

The governance engine was sound and the product was a **diorama**: one hardcoded fund,
fourteen tickers, and no way for anyone to put their own money in. Everything below
follows from fixing that.

## Three users, in order of how underserved they are

1. **The retail investor who does not know they are concentrated.** ₹5–50 lakh across a
   handful of stocks, mostly IT and banks because that is what everyone owns. Has never
   computed their sector exposure. The question they actually have is *"is my money too
   bunched up, and what happens if technology has a bad quarter?"*
2. **The learner.** The Time Machine is a teaching instrument — here is what you would
   have done at the Covid bottom, and here is why the system distrusted it.
3. **The boutique analyst** — the original target, and the least underserved.

## What changed

**Data.** 14 tickers → **56**: the NIFTY 50 across 11 sectors, mid-cap IT names, and the
NIFTY index itself as a benchmark. 103,000 price rows. A real Indian retail portfolio is
now mostly drawn from what we cover. (`LTIM` 404s on Yahoo and `TATAMOTORS` is gone
post-demerger — `LTTS`/`TATAELXSI` and `TMPV` carry the history.)

**Bring your own portfolio.** Three ways in, because different people arrive differently:
load a preset, search and pick stocks, or **paste straight from your broker**. The parser
takes name or symbol, any separator, skips headers, and **returns what it could not read
instead of dropping it** — a holding that vanished quietly is worse than one that failed
loudly.

**Policy profiles.** Pointing institutional limits (5% per stock) at a real retail
portfolio produced thirteen red findings and a grade E. That is an alarm, not a
diagnosis: a ten-stock portfolio *cannot* satisfy a 5% cap, so the advice was unreachable
by construction. Same engine, three profiles — retail / serious / boutique. The same
portfolio now reads **94A / 83B / 51D**, and every score states which yardstick it used.

**Portfolio X-ray.** A grade, a published score formula, and at most five findings
ranked by severity. `Effective holdings` (1/HHI) is the one that lands: *"you own 10
stocks but it behaves like 6"*.

**Stress tests.** Four real historical windows replayed against your actual share counts
at the prices that really occurred, plus four labelled what-ifs. The UI tags them **REAL**
vs **WHAT-IF** and never blurs the two.

**Plain-language Q&A.** `/ask` answers in sentences a non-expert can act on.

## How the chatbot stays simple AND accurate

One rule: **the model never produces a number.** Every figure is computed in Python from
the snapshot; the templates only decide how to say it. Simplicity here is a writing
problem, not a modelling one — which is why the answers can drop the jargon without
going vague.

The writing rules, applied deliberately:
- Lead with the answer, not the method.
- One idea per sentence, none over ~20 words.
- Money in lakh and crore, never `1.2e6`.
- Jargon gets glossed **every** time, not once.
- Say what it means for the person, not what the metric is called.
- Every answer carries `detail` for the expert view, so simplifying never costs the number.

Real output:

> **Q: what should I sell?**
> Selling about ₹48,418 across 1 holding would bring you inside every limit.
> — Sell 22 TCS — about ₹48,418 — to get under the technology limit.
> ⇒ That money goes to cash. You do not have to buy anything with it today.

> **Q: what happened in Covid?**
> In the covid crash, you would lose about ₹2.92 lakh.
> — That is 29% of your money — ₹10.00 lakh becomes ₹7.08 lakh. The NIFTY 50 moved −37%,
> so you would have done better than the market by 8%.
> ⇒ Those are the real prices from that window.

Note what it does *not* do: no advice to buy, no prediction, no confidence it has not
earned. Historical answers say they are real; what-ifs say they are what-ifs.

## Two modes, one product

**My portfolio** — X-ray, profile, ask, stress, positions. For the private investor.
**Under the hood** — agent desks, conviction, citation gate, calibration, execution log.
For the analyst, and for judges who want to see the machinery.

## New surfaces

```
GET  /universe          searchable catalogue with live prices
GET  /portfolios        saved + preset portfolios
POST /portfolios        create from picked holdings
POST /portfolios/parse  read a pasted broker export
GET  /profiles          limit profiles          POST /profiles/{key} switch
GET  /xray              health score + findings
GET  /stress            historical + hypothetical scenarios
POST /ask               plain-language Q&A
GET  /glossary          every term, glossed
```


# ============================================================================
# Replacing the fund's work, not just its chatbot
# ============================================================================

A fund's workflow is: **screen → research → construct → risk-check → execute →
rebalance → attribute → report → review.** We already automated research (the desks),
risk-check (the firewall) and review (calibration). The chatbot is a surface over those,
not the product.

The unautomated majority was **screening, construction, rebalancing and attribution** —
and all four are *deterministic arithmetic*, which is exactly why they can be automated
honestly when return prediction cannot.

| Fund role | Replaced by | Deterministic? |
|---|---|---|
| Screening analyst | `analysis/factors.py` — factor ranking + 4 screens | yes |
| Risk analyst | correlation engine, X-ray, stress | yes |
| Portfolio manager | `analysis/rebalance.py` — minimal-trade optimiser | yes |
| Performance analyst | `analysis/attribution.py` — Brinson decomposition | yes |
| Research desks | 4 LLM desks + citation gate | no — and gated because of it |
| Compliance | risk firewall + audit trail | yes |
| Post-trade review | calibration record | yes |

## The rebalancer

Greedy and ordered, because "minimal" needs a definition: trim position breaches, trim
sector breaches largest-first, restore the cash floor, then **deploy the surplus into
the lowest-correlation candidates** rather than a sector quota. Every leg is re-checked
by the firewall before it is returned — a plan the firewall would refuse is not a plan.

Real output on the over-concentrated preset:

| | retail | fund |
|---|---|---|
| trades | 5 | 20 |
| effective holdings | 10.8 → 11.5 | 10.8 → **23.6** |
| compliant after | yes | yes |

The retail plan is two lines: *sell 22 TCS, buy 315 ONGC — correlation **−0.01** to your
book.* That is a portfolio manager's decision, computed.

## The correlation engine

The finding that lands hardest in a demo: this portfolio holds four IT names at
**0.70–0.78** correlation to each other. "You own ten stocks" is a count. "Three pairs
move together above 0.7, so 26% of your money is one bet" changes what you do next.

## Voice, rebuilt

The old version handed a whole paragraph to the browser as one utterance — which is why
it read like a machine rather than someone explaining. It now queues **sentences** with
a pause between them scaled to length. The pause is where comprehension happens.

Controls, because being talked at with no off switch is the actual complaint:

- **■ Stop** — instant, mid-sentence. Each sentence is its own utterance, so there is no
  "wait for the paragraph to finish".
- **Quiet for ▾** — 1 / 5 / 15 / 60 minutes, with a live countdown, persisted across
  reload. A span rather than a toggle, because a presenter wants silence for the next
  stretch, not a switch to remember.
- **Pace** — 0.7x to 1.5x, applied to the remainder immediately rather than the next answer.
- A per-sentence progress bar, so "muted" is never an unexplained dead state.

## Three modes

**My money** (X-ray, ask, stress) · **Fund desk** (correlation, attribution, rebalance,
screener) · **Machinery** (desks, conviction, citation gate, calibration).
