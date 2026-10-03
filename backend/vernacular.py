"""Hindi explainer: plain-language answers in everyday spoken Hindi.

The same rule as the English explainer applies, and matters more here: the language model
may only REWORD. Every figure in an answer is computed in Python; a translation that
changes, drops or invents a number is rejected and the English answer is shown instead.
That check is mechanical (compare the numbers on both sides), so a fluent-sounding Hindi
sentence with a wrong amount can never reach a user who cannot easily spot it.

Translation runs on the local llama3.1:8b through Ollama -- free, offline, and the same
model the rest of the product already depends on.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

from agents.llm import ANALYST_MODEL, chat_json

LANGS = {"en": "English", "hi": "हिन्दी"}

_CACHE: dict[tuple[str, str], str] = {}
_CACHE_MAX = 600

# Digits, with Indian/Western grouping and decimals: 1,83,000  10.5  94
_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")

SYSTEM = (
    "You translate short investment explanations from English into simple, everyday spoken "
    "Hindi (Devanagari script), the way a patient friend would explain money to someone "
    "with no finance background. Rules: keep EVERY number, percentage and ₹ amount exactly "
    "as written, using Western digits (0-9); keep company names and tickers in English "
    "letters; use common words (e.g. 'शेयर', 'पोर्टफोलियो', 'जोखिम', 'लाख'); never add, "
    "remove or soften any fact; do not explain or comment."
)


def _numbers(text: str) -> Counter:
    return Counter(n.replace(",", "") for n in _NUM.findall(text))


def numbers_preserved(source: str, translated: str) -> bool:
    """Every figure in the source must appear, unchanged, in the translation -- and a
    fraction like "94 out of 100" must still read as 94 of 100, not 100 of 94. That exact
    swap happened in the first trial and a plain count of the digits cannot see it."""
    want, got = _numbers(source), _numbers(translated)
    if not all(got[n] >= c for n, c in want.items()):
        return False
    for a, b in re.findall(r"(\d+) out of (\d+)", source):
        if not re.search(rf"{b}\s*में\s*से\s*{a}\b", translated):
            return False
    return True


def looks_hindi(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    deva = len(_DEVANAGARI.findall(text))
    # A real Hindi sentence can be mostly company names ("सबसे ज़्यादा असर: ICICI Bank, ..."),
    # so a ratio alone is too strict; a handful of Devanagari letters is enough.
    return bool(letters) and (deva >= 8 or deva / len(letters) > 0.4)


async def _one(texts: list[str]) -> list[str] | None:
    schema = {"type": "object",
              "properties": {"hindi": {"type": "array", "items": {"type": "string"}}},
              "required": ["hindi"]}
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))
    prompt = (f"Translate each numbered English line into simple spoken Hindi. Return a JSON "
              f"object with a 'hindi' array containing exactly {len(texts)} strings, in order.\n\n"
              f"{numbered}")
    try:
        out = await chat_json(prompt, schema, model=ANALYST_MODEL, system=SYSTEM,
                              temperature=0.1, max_tokens=140 * len(texts) + 60, attempts=2)
    except Exception:  # noqa: BLE001
        return None
    hi = out.get("hindi")
    if not isinstance(hi, list) or len(hi) != len(texts):
        return None
    return [str(h).strip() for h in hi]


async def translate_many(texts: list[str], lang: str = "hi") -> list[str]:
    """Translate several lines in one model call. Any line that fails the number check, or
    does not come back as Hindi, is returned in ENGLISH -- never as a wrong Hindi line."""
    if lang != "hi" or not texts:
        return list(texts)
    # Whole-sentence exact rules first: this covers almost everything the explainer says.
    from backend.hindi_rules import exact
    result: list[str | None] = []
    for t in texts:
        if (hit := _CACHE.get((lang, t))) is not None:
            result.append(hit)
            continue
        sents = [x for x in re.split(r"(?<=[.!?])\s+", t.strip()) if x]
        done = [exact(x) for x in sents]
        if sents and all(d is not None for d in done):
            hi = " ".join(done)                      # type: ignore[arg-type]
            _CACHE[(lang, t)] = hi
            result.append(hi)
        else:
            result.append(None)
    missing = [i for i, r in enumerate(result) if r is None and texts[i].strip()]
    if missing:
        batch = [texts[i] for i in missing]
        got = await _one(batch)
        if got is None:                       # one retry, one line at a time
            got = []
            for t in batch:
                one = await _one([t])
                got.append(one[0] if one else "")
        for i, hi in zip(missing, got):
            src = texts[i]
            if hi and looks_hindi(hi) and numbers_preserved(src, hi):
                result[i] = hi
                _CACHE[(lang, src)] = hi
                if len(_CACHE) > _CACHE_MAX:
                    _CACHE.pop(next(iter(_CACHE)))
    return [r if r is not None else texts[i] for i, r in enumerate(result)]


def _brief_hi(headline: str, bullets: list[str], max_words: int = 30) -> str:
    """Short spoken version of an already-Hindi answer: whole sentences, no trailing
    qualification, and one supporting fact only when the headline is very short."""
    def cut(text: str, limit: int) -> str:
        text = (text or "").split(" — ")[0].strip()
        out: list[str] = []
        n = 0
        for sent in re.split(r"(?<=[।.!?])\s+", text):
            w = len(sent.split())
            if out and n + w > limit:
                break
            out.append(sent)
            n += w
            if n >= limit * 0.6:
                break
        return " ".join(out)
    first = cut(headline, max_words)
    if len(first.split()) < 14 and bullets:
        first = (first + " " + cut(bullets[0], 22)).strip()
    return first


async def localize_answer(answer: Any, lang: str) -> dict[str, Any]:
    """The answer dict, with its text fields in `lang`, plus the short spoken line.

    Returns {"answer": dict, "spoken": str, "full": str, "translated": bool}.
    """
    from backend.explain import _brief
    d = answer.as_dict()
    spoken_en, full_en = answer.spoken(), answer.spoken_full()
    if lang != "hi":
        return {"answer": d, "spoken": spoken_en, "full": full_en, "translated": False}
    if getattr(answer, "lang", "en") == "hi":
        # Written in Hindi by the tool that produced it (numbers computed in Python): no
        # second pass through a translator that could only make it worse.
        spoken = answer.speech or _brief_hi(answer.headline, list(answer.bullets))
        full = " ".join(p for p in [answer.headline, *answer.bullets, answer.action] if p)
        return {"answer": d, "spoken": spoken, "full": full, "translated": True}

    # Fixed order: speech line first (what is heard), then what is shown.
    bullets = list(answer.bullets[:3])
    follow = list(answer.follow_ups[:3])
    lines = [answer.headline, *bullets, *(([answer.action]) if answer.action else []), *follow]
    out = await translate_many(lines, "hi")
    it = iter(out)
    head_hi = next(it)
    bullets_hi = [next(it) for _ in bullets]
    action_hi = next(it) if answer.action else None
    follow_hi = [next(it) for _ in follow]

    # The spoken line is cut from the SAME Hindi that is shown, never translated separately:
    # translating the clipped English brief gave a second, different (and clumsier) Hindi.
    spoken_hi = _brief_hi(head_hi, bullets_hi)
    translated = looks_hindi(head_hi)
    # follow_ups stays English: it is what actually gets asked when a chip is tapped, and
    # the router only understands English. follow_ups_hi is the label shown on the chip.
    d.update(headline=head_hi, bullets=bullets_hi + list(answer.bullets[3:]),
             action=action_hi, follow_ups_hi=follow_hi, lang="hi" if translated else "en")
    full_hi = " ".join(p for p in [head_hi, *bullets_hi, action_hi] if p)
    return {"answer": d, "spoken": spoken_hi, "full": full_hi, "translated": translated}


# ------------------------------------------------------------------ Hindi -> English input
_CANON = [
    "How am I doing?", "Why is my risk high?", "Am I diversified?", "What should I sell?",
    "What happened in Covid?", "What if I do nothing?", "What moves together?",
    "What should I buy to spread out?", "What is my worst case?", "What if the market drops 20%?",
    "What if technology falls 30%?", "Tell me more", "Reset",
]
_KNOWN: dict[str, str] | None = None


def _known() -> dict[str, str]:
    """Hindi form -> English question, built from the same rule table that writes Hindi."""
    global _KNOWN
    if _KNOWN is None:
        from backend.hindi_rules import exact
        _KNOWN = {}
        for en in _CANON:
            hi = exact(en)
            if hi:
                _KNOWN[_norm(hi)] = en
    return _KNOWN


def _norm(t: str) -> str:
    return re.sub(r"[\s?।.,!]+", " ", t).strip().lower()


async def to_english(hindi: str) -> str:
    """Recover the English meaning of a spoken Hindi question or command.

    Known questions are matched against the Hindi we ourselves produce (fuzzy, so small
    transcription slips do not matter). Anything else goes to the local model, whose output
    only has to be a question for the router -- a trade still needs an explicit confirmation
    and still passes the risk firewall.
    """
    import difflib
    h = _norm(hindi)
    best, score = None, 0.0
    for known, en in _known().items():
        r = difflib.SequenceMatcher(None, h, known).ratio()
        if r > score:
            best, score = en, r
    if best and score >= 0.72:
        return best
    schema = {"type": "object", "properties": {"english": {"type": "string"}}, "required": ["english"]}
    try:
        out = await chat_json(
            f"Translate this spoken Hindi request about an investment portfolio into a short, "
            f"plain English sentence. Keep every number and company name. Hindi: {hindi}",
            schema, model=ANALYST_MODEL, temperature=0.0, max_tokens=60, attempts=2)
        english = str(out.get("english", "")).strip() or hindi
    except Exception:  # noqa: BLE001
        return hindi
    # A figure the speaker said must survive into the English (the first trial dropped
    # "20%" from "if the market falls 20%"). Anything missing is appended, which is enough
    # for the explainer to pick it up.
    have = _numbers(english)
    for tok in re.findall(r"\d[\d,]*(?:\.\d+)?\s?%?", hindi):
        digits = tok.replace(",", "").strip().rstrip("%").strip()
        if not have[digits]:
            english += " " + tok.strip()
            have[digits] += 1
    return english
