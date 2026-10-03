"""Download the local neural voice (Piper, British male) used for spoken answers.

    python tools/get_voice.py

The model is ~63 MB and is git-ignored. Without it the app still works: it falls back to
the browser's built-in voice, but that one cannot be interrupted as reliably.
"""
import urllib.request
from pathlib import Path

ROOT = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
VOICES = {  # name -> path under the voices repo
    "en_GB-alan-medium": "en/en_GB/alan/medium",          # English answers
    "hi_IN-pratham-medium": "hi/hi_IN/pratham/medium",    # Hindi answers
}
dest = Path(__file__).resolve().parent.parent / "models" / "piper"
dest.mkdir(parents=True, exist_ok=True)
for name, sub in VOICES.items():
    for ext in (".onnx", ".onnx.json"):
        target = dest / f"{name}{ext}"
        if not target.exists():
            print("downloading", target.name)
            urllib.request.urlretrieve(f"{ROOT}/{sub}/{name}{ext}", target)
    print("voice ready:", name)
print("Hindi speech INPUT uses Whisper 'small' (multilingual); it downloads itself on first use.")

# Kokoro: the primary, more natural voice (English + Hindi). ~380 MB, one-time download.
KOKORO = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
kdest = dest.parent / "kokoro"
kdest.mkdir(parents=True, exist_ok=True)
for fn in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
    if not (kdest / fn).exists():
        print("downloading", fn)
        urllib.request.urlretrieve(f"{KOKORO}/{fn}", kdest / fn)
    print("kokoro ready:", fn)
