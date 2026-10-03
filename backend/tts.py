"""Local neural text-to-speech with two engines.

Kokoro is the primary voice: far more natural than Piper (real intonation, and it has Hindi
voices trained on Hindi speech rather than a robotic phoneme reader). It runs at roughly
0.45x real time on this CPU, so the browser asks for the first sentence on its own to start
quickly and the rest as one piece for natural flow.

Piper is the fallback and the fast option: ~0.08x real time but flatter. A voice id is
"<engine>:<name>"; a bare name means Piper (the original ids keep working).

Why server-side audio at all: the browser's speechSynthesis could not be interrupted
reliably. Here the browser plays a plain WAV through an element it controls (see speak.ts).
"""
from __future__ import annotations

import io
import os
import threading
import wave
from collections import OrderedDict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent / "models"
PIPER_DIR = ROOT / "piper"
KOKORO_DIR = ROOT / "kokoro"
KOKORO_MODEL = KOKORO_DIR / "kokoro-v1.0.onnx"
KOKORO_VOICES = KOKORO_DIR / "voices-v1.0.bin"

# What the UI offers. id -> (label, language, kokoro lang code)
KOKORO_CHOICES = {
    "kokoro:bm_george": ("George · British male", "en", "en-gb"),
    "kokoro:bm_daniel": ("Daniel · British male", "en", "en-gb"),
    "kokoro:am_michael": ("Michael · American male", "en", "en-us"),
    "kokoro:bf_emma": ("Emma · British female", "en", "en-gb"),
    "kokoro:af_heart": ("Heart · American female", "en", "en-us"),
    "kokoro:hm_psi": ("Psi · Hindi male", "hi", "hi"),
    "kokoro:hm_omega": ("Omega · Hindi male", "hi", "hi"),
    "kokoro:hf_alpha": ("Alpha · Hindi female", "hi", "hi"),
    "kokoro:hf_beta": ("Beta · Hindi female", "hi", "hi"),
}
DEFAULTS = {"en": os.environ.get("JARVIS_VOICE_EN", "kokoro:bm_george"),
            "hi": os.environ.get("JARVIS_VOICE_HI", "kokoro:hm_psi")}
# A touch faster than the model's default, which sounds slow and deliberate. Hindi stays
# closer to natural because its voices are already brisk.
SPEED = {"en": 1.12, "hi": 1.04}

_piper: dict[str, Any] = {}
_kokoro: Any = None
_lock = threading.Lock()
_cache: "OrderedDict[tuple, bytes]" = OrderedDict()
_CACHE_MAX = 300


def _kokoro_ok() -> bool:
    try:
        import kokoro_onnx  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return KOKORO_MODEL.exists() and KOKORO_VOICES.exists()


def _piper_ok(name: str) -> bool:
    try:
        import piper  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return (PIPER_DIR / f"{name}.onnx").exists()


def _split(voice: str) -> tuple[str, str]:
    return tuple(voice.split(":", 1)) if ":" in voice else ("piper", voice)   # type: ignore[return-value]


def _fallback(lang: str) -> str:
    return "hi_IN-pratham-medium" if lang == "hi" else "en_GB-alan-medium"


def resolve(voice: str | None, lang: str = "en") -> str | None:
    """The voice that will actually be used: the one asked for, else the language default,
    else the Piper fallback, else None (nothing installed)."""
    for cand in (voice, DEFAULTS.get(lang), _fallback(lang)):
        if not cand:
            continue
        engine, name = _split(cand)
        if engine == "kokoro" and _kokoro_ok():
            return cand
        if engine == "piper" and _piper_ok(name):
            return name
    return None


def available(voice: str | None = None, lang: str = "en") -> bool:
    return resolve(voice, lang) is not None


def catalogue() -> list[dict[str, str]]:
    out = []
    if _kokoro_ok():
        out += [{"id": k, "label": v[0], "lang": v[1], "engine": "kokoro"}
                for k, v in KOKORO_CHOICES.items()]
    if PIPER_DIR.exists():
        for p in sorted(PIPER_DIR.glob("*.onnx")):
            out.append({"id": p.stem, "label": f"{p.stem} (fast, flatter)",
                        "lang": "hi" if p.stem.startswith("hi") else "en", "engine": "piper"})
    return out


def _get_kokoro():
    global _kokoro
    if _kokoro is None:
        import onnxruntime as ort
        from kokoro_onnx import Kokoro
        so = ort.SessionOptions()
        so.intra_op_num_threads = 8
        sess = ort.InferenceSession(str(KOKORO_MODEL), sess_options=so,
                                    providers=["CPUExecutionProvider"])
        _kokoro = Kokoro.from_session(sess, str(KOKORO_VOICES))
    return _kokoro


def _wav(samples, rate: int) -> bytes:
    import numpy as np
    pcm = (np.clip(samples, -1, 1) * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def synthesize(text: str, voice: str | None = None, lang: str = "en") -> bytes:
    chosen = resolve(voice, lang)
    if chosen is None:
        raise RuntimeError("no voice installed")
    speed = SPEED.get(lang, 1.0)
    key = (chosen, text, speed)
    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
        engine, name = _split(chosen)
        if engine == "kokoro":
            code = KOKORO_CHOICES.get(chosen, ("", lang, "en-gb" if lang == "en" else "hi"))[2]
            samples, rate = _get_kokoro().create(text, voice=name, speed=speed, lang=code)
            data = _wav(samples, rate)
        else:
            from piper import PiperVoice
            if name not in _piper:
                _piper[name] = PiperVoice.load(str(PIPER_DIR / f"{name}.onnx"))
            buf = io.BytesIO()
            with wave.open(buf, "wb") as w:
                _piper[name].synthesize_wav(text, w)
            data = buf.getvalue()
        _cache[key] = data
        if len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)
        return data


def warm_up() -> None:
    """Load both engines now. The first Kokoro call costs several seconds, and it would
    otherwise land on the first thing anybody says."""
    for lang in ("en", "hi"):
        try:
            synthesize("ठीक है।" if lang == "hi" else "Ready.", None, lang)
        except Exception:  # noqa: BLE001
            pass
