# API reference

Base URL `http://localhost:8000`. JSON unless noted. Interactive OpenAPI docs are served by FastAPI at `/docs`.

**Language and tab.** Endpoints that produce words accept an optional `lang` (`"en"` or `"hi"`) and, where a reply is also broadcast, `cid` (the asking tab). See [LANGUAGE.md](LANGUAGE.md#3-per-screen-language-and-why-it-matters).

## Assistant and questions

| Method | Path | Purpose |
|---|---|---|
| POST | `/ask` | `{question, level?, lang?, cid?}` -> an answer dict (`headline, bullets, action, detail, facts, table, visual, follow_ups, follow_ups_hi, lang, kind`). `level`: `normal` / `simple` / `maths`. |
| POST | `/command` | `{text, lang?, cid?}` - the single entry for anything typed or spoken: decides *command vs question* once. |
| WS | `/ws` | server -> client events (frozen contract); client -> server `{type: "command", text, lang, cid}`, `boot`, `transcript`. |
| POST | `/stt?lang=&raw=&cid=` | audio body -> transcript. `raw=true` returns only the transcript (no dispatch, no translation). |
| POST | `/tts` | `{text, voice?, lang}` -> `audio/wav` (204 if no voice is installed). |
| GET | `/tts/status` | availability, default voices, the voice catalogue. |
| GET / POST | `/language` | last language a screen set (fallback only) / set it. |
| POST | `/translate` | `{lines: [...]}` -> `{hindi: [...]}` for backend-written sentences (exact rules, guarded model, else unchanged). |
| GET | `/glossary?lang=` | terms and definitions. |
| GET | `/palette?q=` | command-palette search over every capability. |

## Practice and protection tools

| Method | Path | Purpose |
|---|---|---|
| GET | `/funds` | the sample funds (id, name, kind, fee, top holdings). |
| GET | `/funds/overlap?a=&b=` | overlap %, shared stocks, wasted fee per ₹1 lakh, share of your own holdings inside each fund. |
| GET / POST | `/myfunds` | saved funds; POST `{fund_id, on}`. |
| GET | `/feedrag?principal=&monthly=&years=&gross=&fee=&low=` | fee-drag series and totals. |
| GET | `/emergency?cash=&expenses=&invest=&income=&haircut=` | months of cover, shortfall, month series. |
| GET | `/goal?monthly=&years=&target=&haircut=` | percentile bands and the chance of reaching the target. |
| GET | `/panic?key=covid\|rate_shock_2022\|adani_2023` | portfolio value series through a crash. |
| GET | `/digest?lang=` | weekly digest sections and spoken text. |
| GET | `/scamcall/scenarios?lang=` | the three scenarios. |
| POST | `/scamcall/step` | `{scenario, node, reply, pressure, lang}` -> next caller line / win / loss with feedback. |
| POST | `/scan` | `{text}` -> tip scan: score, verdict, flags, claims, companies. |
| GET | `/tax/shield` | per-holding tax if sold today vs waiting. |
| GET / POST | `/lots` | cost basis lots you entered. |

## Portfolio and analysis

| Method | Path | Purpose |
|---|---|---|
| GET | `/state`, `/policy`, `/health` | session state, active limits, liveness (also flags a replay). |
| GET | `/profiles` · POST `/profiles/{key}` | limit profiles (`retail`, `balanced`, `fund`) / switch. |
| GET | `/universe` | searchable catalogue with prices. |
| GET / POST | `/portfolios` · POST `/portfolios/{id}/activate` · DELETE `/portfolios/{id}` · POST `/portfolios/parse` | saved portfolios; paste a broker export (rejects are returned). |
| GET | `/xray?lang=` | grade, score, effective holdings, findings. |
| GET | `/stress` | four real windows + four what-ifs. |
| GET | `/correlation` | which holdings are the same bet. |
| GET | `/rebalance` · POST `/rebalance/apply` | minimal-trade plan / book it to the paper ledger (re-gated). |
| GET | `/attribution` | Brinson-style allocation vs selection. |
| GET | `/history` | daily basket value vs the benchmark. |
| GET | `/screen/{kind}` | factor screens. |
| GET | `/drilldown/{metric}?key=` | components, formula, why it matters, provenance. |
| GET | `/report` | the one-page printable report. |
| GET | `/actions` | ranked "what to do next". |
| GET | `/flows?lang=` · `/flows/{id}?lang=` | guided jobs (localized). |
| GET / POST / DELETE | `/watch`, `/watch/metrics`, `/watch/{id}` | standing "tell me if" rules. |
| GET | `/prices/{ticker}`, `/evidence/{ticker}` | point-in-time prices; evidence pack for the provenance graph. |

## Governance

| Method | Path | Purpose |
|---|---|---|
| POST | `/firewall/check` | `{ticker, side, shares}` -> approved / violations / largest compliant size. Does not touch the book. |
| GET | `/sandbox` · POST `/sandbox/stage` · `/sandbox/from-rebalance` · `/sandbox/discard` · `/sandbox/commit` | staging layer: preview before/after, then commit through the firewall. |
| GET | `/ledger` | entries and chain verification. |
| POST | `/ledger/tamper` | in-memory simulated edit (`rehash` optional); nothing is written. |
| POST | `/ledger/tamper/real` | attempts a real UPDATE inside a savepoint that is always rolled back; the append-only trigger blocks it. |
| POST | `/ledger/demo-seed` | adds sample `DEMO` entries if the ledger is short. |
| GET | `/calibration` | per-desk hit rate and Brier score. |

## Demo and recording

`GET /script`, `GET /recordings`, `POST /record/start|stop`, `POST /replay/start|stop`, `POST /boot`. See [GOVERNANCE_ENGINE.md](GOVERNANCE_ENGINE.md#demo-insurance).

## Example

```bash
curl -s -X POST localhost:8000/ask -H 'Content-Type: application/json' \
  -d '{"question":"what does a 2% fee cost over 20 years","lang":"en"}'
```

```json
{
  "headline": "A 2% fee costs you about ₹2.58 lakh over 20 years, compared with a 0.2% fund.",
  "kind": "fee_drag",
  "facts": [{"label": "At 2%", "value": "₹6.73 lakh", "tone": "bad"}, "..."],
  "visual": {"page": "practice", "label": "Open the fee slider", "params": {"fee": 2, "low": 0.2, "years": 20}},
  "follow_ups": ["Which funds overlap the most?", "..."]
}
```
