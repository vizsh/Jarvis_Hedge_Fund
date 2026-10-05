# Testing

```bash
python -m pytest tests/ -q       # 532 tests, ~70 s
```

## What is tested

Newer areas (added since the table below was written):

| File | What it protects |
|---|---|
| `test_understand.py` | whole-question routing: app questions and their tours, companies (analysis and comparison), general money concepts, the scam scripts, Hindi answers, the portfolio-move answer |
| `test_setup.py` | five baskets name only real features; the pitch basket has every feature; the rural baskets are free; a saved setup round-trips |
| `test_protect_govern.py` (extended) | tip checker: calm tips are never certified safe; fixed periodic returns and requests for money or login are decisive; the panel gives reasons and steps |
| `test_messaging.py` | WhatsApp answers and the menu fallback; buy and portfolio-advice answers stay in the app |

Older table (counts were correct when written; the total is now 532):


| File | Tests | What it protects |
|---|---|---|
| `test_assistant.py` | 48 | routing accuracy on blind sets; **numbers equal the calculators**; Hindi headlines keep every number; chips route to real intents; per-request language; flows and glossary have complete Hindi; LLM-stage behaviour (stubbed) |
| `test_router.py` | 39 | intent parsing for trade commands vs questions |
| `test_guidance.py` | 37 | actions queue, flows, palette, drill-downs, watchlist |
| `test_usability.py` | 32 | portfolios, parser, profiles, X-ray, stress, explainer |
| `test_agents.py` | 18 | research desks, citation gate, conviction, groupthink |
| `test_risk_engine.py` | 17 | firewall limits and the closed-form remedy |
| `test_backend.py` | 23 | HTTP / WebSocket pipeline |
| `test_protect_govern.py` | 13 | tip scanner, tax shield, ledger chain and triggers, firewall check |
| `test_hindi.py` | 12 | exact Hindi rules, number preservation, drill-down and scanner coverage, company names untouched |
| `test_voice.py` | 12 | STT grammar repair, confidence floors |
| `test_calibration.py` | 11 | Brier / hit-rate scoring |
| `test_snapshot.py`, `test_pit.py`, `test_mixed_calendar.py` | 22 | point-in-time safety, no lookahead |
| `test_hindi_input.py` | 23 | Hindi numbers read exactly, units told apart, routing accuracy on tune / blind / blind2 / real-transcript sets with zero confident-wrong answers, nothing invented, model fallback is closed-list and confidence-gated, end-to-end Hindi answers |
| `test_stocks.py` | 15 | type-ahead search, typo tolerance, unknown company is looked up (not turned into TCS), on-demand fetch registers only if prices arrived |
| `test_recovery.py` | 11 | every situation has a complete plan in both languages; first steps are the urgent ones; drafts contain only what the person gave and mark gaps; the situation is read from a sentence; the chatbot returns the plan |
| `test_practice.py` | 5 | scam classifier (English and Hindi, incl. transcriber misspellings and codes spoken as words), overlap symmetry |
| `test_demos.py` | 4 | ledger tamper detection, goal fan ordering |
| `test_replay.py` | 5 | recorded replay fidelity |

## Principles

- **Exact tests for exact things.** Fee drag is checked against the closed form `P (1+r)^n`; overlap against a hand computation; emergency months against `cash / burn`.
- **A tool answer must equal its calculator.** The test calls both and compares (e.g. goal probability in the headline equals `goal.fan(...)`).
- **A translator cannot change a number.** Hindi tests compare figures between English and Hindi text.
- **Wrong is worse than asking.** Routing tests count *confidently wrong* answers and require zero on every blind set.
- **No test depends on Ollama.** The model stage is stubbed; offline behaviour (asking) is what is tested.
- **The test session shares the app database,** so fixtures snapshot and restore saved funds.

## Routing evaluation sets

| File | Role |
|---|---|
| `tests/chat_eval_data.py` | rule-regression suite (tuned against; may overlap training examples) |
| `tests/chat_eval_blind.py` | second set, written after tuning on the first |
| `tests/chat_eval_blind3.py`, `chat_eval_blind4.py` | later sets; the **first-run** result before any tuning is the honest estimate |

Procedure for honest numbers: write new sentences, run once and record the score, only then add rules, and keep the set as regression cover. Results are in [ASSISTANT.md](ASSISTANT.md#6-measured-accuracy).

A separate check that the blind set does not appear in `intent_data.py` (the training examples) runs as a test.

## Scripts (not part of pytest)

| Script | Purpose |
|---|---|
| `python tools/dry_run.py` | 28 invariants through the scripted demo (double-fire, 9,999 shares, expired remedy, command during replay...) |
| `python tools/backfill_calibration.py` | scores the research desks against realised forward returns |
| `python tools/demo_risk.py`, `demo_timemachine.py`, `demo_agents.py`, `demo_backend.py` | narrated demonstrations |
| `python tools/record_demo.py` | capture a golden take for replay |

## What is not tested (and why)

- Voice **quality** and Hindi recognition on real human voices (tests use synthesized speech; a person must listen).
- Browser microphone capture (blocked in automated browser panes).
- Live data feeds (the snapshot is frozen on purpose).
