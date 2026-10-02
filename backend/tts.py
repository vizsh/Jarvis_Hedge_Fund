"""Local neural text-to-speech (Piper). Replaces the browser's speechSynthesis.

Why this exists: speechSynthesis could not be interrupted reliably. Chrome keeps playing
queued utterances after cancel(), and OS voices vary wildly. Here the server returns a
plain WAV per sentence and the browser plays it through an <audio> element it fully
controls -- stopping is pausing that element and dropping the queue, which is instant and
deterministic. It also gives one consistent, much better voice. Nothing leaves the machine.
"""
from __future__ import annotations

import io
import os
import threading
import wave
from collections import OrderedDict
from pathlib import Path

VOICE_DIR = Path(__file__).resolve().parent.parent / "models" / "piper"
DEFAULT_VOICE = os.environ.get("JARVIS_VOICE", "en_GB-alan-medium")

_voices: dict[str, object] = {}
_lock = threading.Lock()
_cache: "OrderedDict[tuple[str, str], bytes]" = OrderedDict()
_CACHE_MAX = 300


def available(voice: str | None = None) -> bool:
    try:
        import piper  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return (VOICE_DIR / f"{voice or DEFAULT_VOICE}.onnx").exists()


def voices() -> list[str]:
    return sorted(p.stem for p in VOICE_DIR.glob("*.onnx")) if VOICE_DIR.exists() else []


def _load(name: str):
    from piper import PiperVoice
    if name not in _voices:
        _voices[name] = PiperVoice.load(str(VOICE_DIR / f"{name}.onnx"))
    return _voices[name]


def synthesize(text: str, voice: str | None = None) -> bytes:
    name = voice or DEFAULT_VOICE
    key = (name, text)
    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
        v = _load(name)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            v.synthesize_wav(text, w)
        data = buf.getvalue()
        _cache[key] = data
        if len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)
        return data


def warm_up() -> None:
    try:
        if available():
            synthesize("Ready.")
    except Exception:  # noqa: BLE001
        pass
