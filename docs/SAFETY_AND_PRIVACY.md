# Safety, privacy and what it will not do

## Privacy: what stays on your machine

| Data | Where it goes |
|---|---|
| Your holdings, cost basis, saved funds, watch rules | local SQLite only |
| Your voice | recorded in the browser, posted to `localhost`, transcribed by local `faster-whisper`, **not stored** |
| Your questions | processed by local Python; only the *optional* intent-picker sends the question text to a **local** Ollama process |
| Speech output | rendered locally (Kokoro / Piper) |
| Market data | downloaded once at ingest from free public sources; nothing about you is sent |

There is no analytics, no account, no cloud API key. The browser's Web Speech API is deliberately **not** used, because it uploads audio to a third party.

## What it will not do

- **Predict prices or pick stocks.** It says so and offers a stress test or a tip check instead.
- **Give personalised investment or tax advice.** Calculators show arithmetic on stated assumptions; every projection is labelled "a projection, not a promise".
- **Trade real money.** Paper only; there is no broker integration.
- **Guess your cost basis.** Tax numbers appear only for lots you entered.
- **Let a model override a limit.** The risk firewall is arithmetic; `risk/` imports no LLM.
- **Present samples as facts.** Fund holdings are labelled illustrative.
- **Change a number when translating.** The Hindi guard rejects it ([LANGUAGE.md](LANGUAGE.md)).

## Honesty features (so you can trust the rest)

- **Glass box:** every figure has "how this was worked out", and the Learn page opens any number to its components, formula and source prices.
- **Point-in-time store:** calculations cannot see the future.
- **Hash-chained, append-only ledger:** editing history breaks the chain; the database also refuses edits and deletes ([FEATURES](FEATURES.md#audit-ledger-and-tamper-test)).
- **Calibration record:** the research desks are scored against realised returns and none beats a coin flip; the product shows this rather than hiding it.
- **Ask, do not guess:** unsure routing asks a question instead of answering a different one.
- **Stop always works:** one control cuts the voice and ends any inline briefing or call.

## Scam-safety principles baked into the content

1. **No bank, police officer or government office asks for your OTP, PIN or CVV.** An OTP exists only to approve money leaving *your* account.
2. **There is no "digital arrest".** Agencies do not arrest or take money over a call.
3. **There is no "safe account".** Any transfer requested over a call is the theft.
4. **Guaranteed high returns do not exist.** The promise is the bait.
5. **Urgency and secrecy are tactics.** "Do not tell your family" is the scammer's key move.
6. **Rule of three:** *Stop* (never act on a call), *hang up*, then *call the official number* (on your card or the bank's website) or **1930** (the national cyber-fraud helpline) / `cybercrime.gov.in`.
7. **After a scam, act in the first hour** (the recovery coach turns this into an ordered, situation-specific plan with a clock): report to 1930, ask your bank to block cards, UPI and net banking, remove any remote-access app, keep screenshots, and never pay anyone to "recover" money (that is a second scam).

These appear in the assistant's scam answers, the weekly digest tips, the rehearsal's end card and the tactic explanations.

## Known risks and mitigations

| Risk | Mitigation |
|---|---|
| A wrong number reaching a user | single shared calculators; exact-equality tests; translator guard |
| A confident wrong answer | closed-list model, confidence floor, ask-on-doubt, zero-confident-wrong tests |
| Over-trust in the research desks | calibration shown, groupthink flag halves conviction, desks never touch the firewall |
| Stale tax rates | constants isolated in `analysis/tax.py` with tests; label "not tax advice" |
| Sample data mistaken for real | explicit labels on every fund answer and visual |
| A microphone transcript misread as a trade | confidence floors; a misheard command is shown but not dispatched |
| Another tab/device receiving your answers | replies tagged with a per-tab id and dropped elsewhere |

Research and education prototype. Verify any figure before relying on it.
