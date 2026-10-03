# Data, configuration and constants

## 1. The frozen snapshot

`data/snapshot.db` (SQLite, WAL mode) is built once by `python tools/ingest.py` and read-only during the app. Why frozen: the unofficial NSE endpoints are flaky and live calls would make demos and tests non-reproducible. The point-in-time store also needs every row to carry the date it *became public*.

| Table | Rows (current build) | Contents |
|---|---|---|
| `prices` | ~102,900 | daily OHLCV for 57 symbols (NIFTY 50 across 11 sectors, mid-cap IT, the NIFTY index as benchmark, a few US names), 2019-06 to 2026-09 |
| `signals` | ~14,700 | fundamentals, ratios, macro series; each with `as_of`, `published_at`, `source`, safety tier |
| `documents`, `doc_chunks` | 552 | news and filings text, chunked for the research desks |
| `claims`, `decisions` | | research-desk output and verdicts (for calibration and replay) |
| `ledger` | | desk-decision audit trail |
| `paper_ledger` | grows | hash-chained paper trades (created at runtime) |
| `extra_universe` | grows | stocks the user searched for and fetched on demand (kept apart from the base universe so sector maps and screens do not silently change) |
| `lots`, `portfolios`, `watches`, `my_funds` | grow | your cost basis, saved portfolios, standing rules, saved funds |

## 2. Sources and point-in-time safety tiers

All free, no API keys. Seven adapters in `ingest/sources.py`: **yfinance** (NSE `.NS` and US prices, fundamentals), **SEC EDGAR** company facts, **Google News** RSS, **GDELT**, **FRED**, **nsepython** (announcements, delivery %, bulk deals), **jugaad-data** (NSE/RBI history and macro).

Each source declares how trustworthy its *publication dates* are, because pretending they are equal would quietly reintroduce lookahead:

| Tier | Sources | Meaning |
|---|---|---|
| `exact` | prices, SEC EDGAR, Google News, GDELT | real publication dates; replay is trustworthy |
| `approximated` | quarterly fundamentals, FRED | a statutory lag is applied (SEBI LODR +45 days) |
| `snapshot_only` | current ratios (e.g. P/E) | no history; stamped at ingest and **vanishes on rewind by design** |

`core/pit.py` (`PointInTimeStore`) is the only way calculators read data; it filters `published_at <= sim_clock`. Rewinding the clock hides later rows at the query, not in the app, so no calculation can see the future.

Known gaps: `LTIM` 404s on Yahoo; `TATAMOTORS` was demerged (`TMPV` carries the history); prices are a snapshot, not live.

## 3. Configuration files (`config/`)

| File | Purpose |
|---|---|
| `policies.yaml` | the three **profiles** and fixed governance flags |
| `policy.yaml` | the original single institutional policy (versioned) |
| `universe.yaml` | tickers, sectors, names, benchmark, macro series |
| `script.yaml` | the presenter's running order (edit words here, not in code) |

**Profiles** (same engine, different thresholds, so advice is *reachable*):

| Profile | Per stock | Per sector | Min cash | Max drawdown | Cost (bps) |
|---|---|---|---|---|---|
| Retail investor (default) | 15% | 35% | 5% | 20% | 30 |
| Serious private investor | 10% | 35% | 8% | 15% | 20 |
| Boutique fund | 5% | 30% | 10% | 5% | 15 |

Governance flags apply to every profile and are not tunable: `broker_execution: false`, `require_citations: true`, `require_human_approval: true`.

## 4. Constants used by calculators

| Constant | Value | Where |
|---|---|---|
| Short-term capital gains tax | 20% (Sec 111A) | `analysis/tax.py` |
| Long-term capital gains tax | 12.5% (Sec 112A) | `analysis/tax.py` |
| LTCG exemption | ₹1,25,000 per financial year | `analysis/tax.py` |
| Long-term threshold | 365 days | `analysis/tax.py` |
| Fee-drag default return | 12% before fees; cheap-fund fee 0.2% | `analysis/tools.py` |
| Emergency target | 6 months; investments haircut 20% | `analysis/tools.py` |
| Goal simulation | 2,000 paths, 21-day blocks of the portfolio's own returns | `analysis/goal.py` |

Rates change with budgets; update the constants and the tests together.

## 5. Sample mutual-fund data (illustrative)

`backend/practice.py::FUNDS` holds eight **sample** funds with rounded top holdings and fees typical of their type: Nifty 50 Index (0.20%), Large Cap A (1.60%), Bluechip B (1.70%), Flexi Cap C (1.55%), Technology (1.0%), Banking (1.1%), Healthcare (1.2%), Consumption (1.3%). They are **not real factsheets** and every answer says so. Replacing them with AMC portfolio disclosures is the top item on the [roadmap](ROADMAP.md). Overlap = sum over shared stocks of the smaller weight, as a share of the smaller fund.

## 6. Scam scenarios

`backend/practice.py` (English) and `backend/practice_hi.py` (Hindi) hold three scripted scenarios (`kyc`, `police`, `invest`) as nodes with: the caller's line, the red-flag codes it triggers, whether the next ask is dangerous (code, app, transfer), and three suggested replies. The scoring is deterministic keyword classification, so a rehearsal behaves the same every time and never says anything a real caller would not.
