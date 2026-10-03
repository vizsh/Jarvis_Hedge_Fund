# How the assistant decides, and how accurate it is

Order of decisions (`backend/assistant.py`):

1. **Precise rules** for each tool (fund overlap, fees, emergency cash, goals, panic-sell replay,
   weekly digest, scam help, tip scan, ledger, definitions, help). Trusted: never overruled.
2. **The original explainer's keyword rules** (risk, sell, stress test, diversification, ...).
3. **Local-LLM intent picker** (`aanswer`, Ollama llama3.1:8b): only when 1-2 found nothing, or
   when only a loose rule from 2 matched a long sentence. It picks ONE intent from a closed list
   with a confidence; below 0.75 it is ignored. It never writes an answer.
4. Otherwise the assistant **asks**, offering the three nearest things it can do (a TF-IDF
   similarity model trained on `backend/intent_data.py` suggests them).

Every figure is computed by `analysis/tools.py`, `backend/practice.py`, `analysis/goal.py`,
`analysis/panic.py` or `backend/digest.py`; English and Hindi text come from templates, so a
translator can never change a number.

## Measured (first run on sentences written after the rules were last tuned)

| Set | Rules only: right / asked / wrong | Rules + local model: right / wrong |
|---|---|---|
| 3rd blind set (43, longer, indirect) | 18 / 20 / 5 (before tuning on it) | 35 / 6 of 43 (81%) |
| 4th blind set (36, incl. 8 Hinglish) | 17 / 18 / 1 | 34 / 2 of 36 (94%) |

After each set was used to add rules, it scores 100% rules-only; that is regression coverage, not
generalisation. Only the first-run numbers above estimate real-world accuracy. `pytest` enforces
zero confident-wrong answers on every blind set, and the numbers shown to the user equal the
calculators (`tests/test_assistant.py`).
