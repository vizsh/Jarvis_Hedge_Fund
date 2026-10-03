"""Local speech-to-text with faster-whisper.

Push-to-talk, transcribed on release -- not streaming. Streaming partials look good in a
video but cost real complexity (VAD, chunk stitching, partial-vs-final state), and for
one-line commands the whole utterance is under three seconds anyway. Batch-on-release is
simpler, more accurate, and keeps the failure mode obvious.

Nothing leaves the machine. That matters for the pitch: the browser Web Speech API is
free and easy but ships your audio to Google, which would quietly break the on-prem
claim this whole project rests on.

Two things make a small model punch above its weight here:

1.  `initial_prompt` primes the decoder with our actual vocabulary. Whisper is heavily
    biased toward its language model, and without priming it reliably turns "MPHASIS"
    into "em phasis" and "NSE" into "and see".

2.  `snap_to_grammar` repairs what is left. The command grammar is tiny and known, so a
    transcript only has to be close -- we can pull it onto the nearest valid ticker or
    verb instead of hoping the decoder nailed it.
"""
from __future__ import annotations

import difflib
import io
import os
import re
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

# Domain vocabulary. Whisper weights this heavily, so it is the cheapest accuracy win
# available and costs nothing at runtime.
INITIAL_PROMPT = (
    "Commands for an investment terminal. Vocabulary: JARVIS, analyse, investigate, "
    "rewind, buy, sell, shares, execute, portfolio, sector cap, policy, "
    "TCS, Infosys, Wipro, HCL Tech, Tech Mahindra, Mphasis, Persistent Systems, "
    "HDFC Bank, ICICI Bank, ITC, Hindustan Unilever, NSE, NAV."
)

# small.en over base.en. base is measurably worse on Indian-accented English, which is
# the accent this is actually used in, and a command misheard is a command lost. It
# costs ~1s more per utterance and ~460MB on disk; accuracy is worth both.
# Override with JARVIS_STT_MODEL if a machine cannot spare the time.
MODEL_SIZE = os.environ.get("JARVIS_STT_MODEL", "small.en")
FALLBACK_MODEL = "base.en"
DEVICE = "auto"
COMPUTE = "int8"            # int8 runs fine on CPU and keeps the GPU free for the LLM.


@dataclass
class Transcript:
    text: str
    raw: str
    confidence: float
    duration_ms: int
    model: str
    repaired: bool = False


@lru_cache(maxsize=1)
def _model():
    """Loaded once, lazily. The first call downloads weights, so warm_up() exists.

    Falls back to the smaller model if the preferred one cannot be fetched -- an
    offline machine should still have working speech, just less accurate speech.
    """
    from faster_whisper import WhisperModel
    device = DEVICE
    if device == "auto":
        try:
            import torch  # noqa: PLC0415
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:  # noqa: BLE001
            device = "cpu"
    compute = "float16" if device == "cuda" else COMPUTE
    try:
        return WhisperModel(MODEL_SIZE, device=device, compute_type=compute)
    except Exception:  # noqa: BLE001
        return WhisperModel(FALLBACK_MODEL, device=device, compute_type=compute)


def available() -> bool:
    try:
        import faster_whisper  # noqa: F401, PLC0415
        return True
    except Exception:  # noqa: BLE001
        return False


def warm_up() -> float:
    """Load weights before the demo. First load can take 30s+ on a cold cache and it
    would otherwise land on the first thing the audience watches you say."""
    t0 = time.perf_counter()
    try:
        _model()
    except Exception:  # noqa: BLE001
        return -1.0
    return time.perf_counter() - t0


# --- grammar repair ----------------------------------------------------------------
VERB_FORMS = {
    "analyse": ["analyse", "analyze", "analysis", "and allies", "a nice"],
    "investigate": ["investigate", "investigator"],
    "rewind": ["rewind", "re wind", "we wind", "rewound"],
    "buy": ["buy", "by", "bye"],
    "sell": ["sell", "cell"],
    "execute": ["execute", "execute it", "exec you"],
    "portfolio": ["portfolio", "port folio"],
}

TICKER_FORMS = {
    "TCS": ["tcs", "t c s", "tics", "ticks", "tee cee ess", "the cs"],
    "Infosys": ["infosys", "info sys", "infoses", "in for cis"],
    "Wipro": ["wipro", "we pro", "why pro"],
    "HCL Tech": ["hcl tech", "h c l tech", "hcl"],
    "Tech Mahindra": ["tech mahindra", "tech mahendra"],
    "Mphasis": ["mphasis", "em phasis", "emphasis", "m phasis"],
    "Persistent": ["persistent", "persistant", "per sistent", "persistent systems"],
    "HDFC Bank": ["hdfc bank", "h d f c bank", "hdfc"],
    "ICICI Bank": ["icici bank", "i c i c i bank", "icici", "i see i see i"],
    "ITC": ["itc", "i t c", "it see"],
    "Hindustan Unilever": ["hindustan unilever", "hul"],
}


def _repair(text: str, forms: dict[str, list[str]]) -> tuple[str, bool]:
    """Replace the longest matching variant with its canonical form.

    Identity matches are NOT skipped: a transcript saying "wipro" already resolves
    correctly, but the operator sees the transcript on screen and "Wipro" reads as a
    system that knows what it heard. `changed` ignores pure case differences so a
    cosmetic fix is not reported as a repair.
    """
    out = text
    for canonical, variants in forms.items():
        for variant in sorted(variants, key=len, reverse=True):
            pattern = re.compile(rf"\b{re.escape(variant)}\b", re.I)
            if pattern.search(out):
                out = pattern.sub(canonical, out, count=1)
                break
    return out, out.lower() != text.lower()


def snap_to_grammar(text: str) -> tuple[str, bool]:
    """Pull a near-miss transcript onto the known command vocabulary.

    Whisper mangles tickers far more often than ordinary words, because they are not
    words. "Mphasis" comes back as "emphasis" almost every time.
    """
    repaired = False
    text, a = _repair(text, TICKER_FORMS)
    text, b = _repair(text, VERB_FORMS)
    repaired = a or b

    # Spoken dates: "twenty three march twenty twenty" -> leave to the intent parser,
    # but normalise the common "march twenty third" ordinal noise first.
    text = re.sub(r"\b(\d{1,2})(?:st|nd|rd|th)\b", r"\1", text, flags=re.I)

    # A multi-word repair can leave a trailing duplicate: "i see i see i bank" expands
    # to "ICICI Bank" and the spoken "bank" survives alongside it. Collapse repeats.
    words = text.split()
    deduped = [w for i, w in enumerate(words)
               if i == 0 or w.lower() != words[i - 1].lower()]
    if len(deduped) != len(words):
        text, repaired = " ".join(deduped), True

    # If the first word is still not a known verb but is close to one, snap it. This
    # catches the long tail without a dictionary entry for every mishearing.
    words = text.split()
    if words:
        head = words[0].lower().strip(",.")
        if head not in VERB_FORMS:
            match = difflib.get_close_matches(head, list(VERB_FORMS), n=1, cutoff=0.74)
            if match:
                words[0] = match[0]
                text = " ".join(words)
                repaired = True
    return text.strip(), repaired


# --- transcription ------------------------------------------------------------------
HI_MODEL = os.environ.get("JARVIS_STT_HI_MODEL", "large-v3-turbo")
HI_FALLBACK = "small"

# A Hindi prompt that is ordinary spoken Hindi with the product's words and numbers written as
# WORDS. Whisper continues in the style of its prompt, so this nudges it to say "तीन लाख" rather
# than guess a digit string (it once wrote "3,000,000" for तीन लाख, a tenfold error).
HI_PROMPT = ("मेरा पोर्टफोलियो कैसा चल रहा है। तीन लाख रुपये हैं और चालीस हज़ार रुपये महीने का खर्च है। "
             "दस हज़ार की एसआईपी, म्यूचुअल फंड, ओटीपी, केवाईसी, एक्सपेंस रेशियो, दो प्रतिशत फीस, बीस साल।")
HI_HOTWORDS = "ओटीपी म्यूचुअल फंड एसआईपी पोर्टफोलियो फीस प्रतिशत लाख हज़ार करोड़ केवाईसी ठगी निफ्टी"


def _cuda_ready() -> bool:
    """CUDA for Whisper needs cuBLAS/cuDNN. They ship as pip packages (nvidia-cublas-cu12,
    nvidia-cudnn-cu12); put their folders on the DLL search path, then check it really loads."""
    try:
        import ctypes
        import glob
        import site

        import ctranslate2
        if ctranslate2.get_cuda_device_count() < 1:
            return False
        for sp in site.getsitepackages():
            for d in glob.glob(os.path.join(sp, "nvidia", "*", "bin")):
                os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
                if hasattr(os, "add_dll_directory"):
                    os.add_dll_directory(d)
        ctypes.CDLL("cublas64_12.dll")
        return True
    except Exception:  # noqa: BLE001
        return False


def _digit_token_ids(model) -> list[int]:
    """Token ids that are plain digits. Suppressing them forces numbers to be written as words,
    which the Hindi understanding code reads exactly."""
    try:
        vocab = model.hf_tokenizer.get_vocab()
    except Exception:  # noqa: BLE001
        return []
    return [i for tok, i in vocab.items() if re.fullmatch(r"[\u0120 ]*[0-9]+", tok)]


@lru_cache(maxsize=1)
def _model_multilingual():
    """The Hindi model. A bigger one than English needs: small mangles Hindi words ("पोर्टफोलियो" ->
    "पोट भूल्यो"); large-v3-turbo does not. On the GPU when cuBLAS is available (about a second
    per sentence), otherwise on the CPU (slower, same accuracy)."""
    from faster_whisper import WhisperModel
    device = "cuda" if _cuda_ready() else "cpu"
    compute = "float16" if device == "cuda" else COMPUTE
    for name in (HI_MODEL, HI_FALLBACK):
        try:
            m = WhisperModel(name, device=device, compute_type=compute)
            m._jarvis_name = f"{name} ({device})"
            m._jarvis_no_digits = _digit_token_ids(m)
            return m
        except Exception:  # noqa: BLE001
            if device == "cuda":                       # GPU libraries missing: same model on the CPU
                device, compute = "cpu", COMPUTE
                try:
                    m = WhisperModel(name, device=device, compute_type=compute)
                    m._jarvis_name = f"{name} ({device})"
                    m._jarvis_no_digits = _digit_token_ids(m)
                    return m
                except Exception:  # noqa: BLE001
                    pass
    raise RuntimeError("no Hindi speech model could be loaded")


def transcribe(audio: bytes, language: str = "en") -> Transcript:
    """Transcribe one push-to-talk utterance.

    `audio` is whatever the browser's MediaRecorder produced (webm/opus). faster-whisper
    decodes it through av/ffmpeg, so we hand over the bytes unchanged rather than
    converting to wav ourselves.
    """
    t0 = time.perf_counter()
    # Hindi is transcribed AS Hindi; backend/vernacular.to_english() then recovers the
    # English meaning so the router and every answer work unchanged. (Whisper's own
    # "translate" task was tried first and dropped key words: "why is my risk high" came
    # back as "why do I have a lot of problems".)
    hindi = language != "en"
    model = _model_multilingual() if hindi else _model()
    segments, info = model.transcribe(
        io.BytesIO(audio),
        language=language if hindi else "en",
        task="transcribe",
        # Beam search, not greedy. These utterances are short enough that the extra
        # cost is ~200ms, and greedy decoding was picking the wrong homophone often
        # enough to matter ("by" for "buy" is the whole ballgame here).
        beam_size=5,
        best_of=5,
        # Temperature fallback: if the first pass looks degenerate, retry hotter
        # rather than returning confident nonsense.
        temperature=[0.0, 0.2, 0.4],
        vad_filter=True,
        vad_parameters={
            "min_silence_duration_ms": 300,
            # Pad the detected speech. Without it the VAD clipped the first phoneme
            # when someone started talking the instant they pressed the key -- which
            # is exactly how push-to-talk gets used.
            "speech_pad_ms": 400,
        },
        initial_prompt=HI_PROMPT if hindi else INITIAL_PROMPT,
        **({"hotwords": HI_HOTWORDS, "suppress_tokens": [-1, *getattr(model, "_jarvis_no_digits", [])]} if hindi else {}),
        condition_on_previous_text=False,  # each command is independent
        # A held key with no speech should come back empty, not hallucinate a
        # sentence from the room tone.
        no_speech_threshold=0.6,
    )
    parts, logprobs = [], []
    for seg in segments:
        parts.append(seg.text)
        logprobs.append(seg.avg_logprob)

    raw = " ".join(p.strip() for p in parts).strip()
    text, repaired = snap_to_grammar(raw)

    # avg_logprob is roughly -0.1 (confident) to -1.0 (guessing); map to 0..1 so the
    # UI can show something meaningful without exposing a raw log probability.
    confidence = 0.0
    if logprobs:
        mean = sum(logprobs) / len(logprobs)
        confidence = max(0.0, min(1.0, 1.0 + mean))

    return Transcript(
        text=text, raw=raw, confidence=round(confidence, 3),
        duration_ms=int((time.perf_counter() - t0) * 1000),
        model=getattr(model, "_jarvis_name", "hindi") if hindi else MODEL_SIZE, repaired=repaired,
    )


def info() -> dict[str, Any]:
    return {"available": available(), "model": MODEL_SIZE, "loaded": _model.cache_info().currsize > 0,
            "hindi_model": HI_MODEL, "hindi_loaded": _model_multilingual.cache_info().currsize > 0}
