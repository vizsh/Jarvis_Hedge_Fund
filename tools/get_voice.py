"""Download the local neural voice (Piper, British male) used for spoken answers.

    python tools/get_voice.py

The model is ~63 MB and is git-ignored. Without it the app still works: it falls back to
the browser's built-in voice, but that one cannot be interrupted as reliably.
"""
import urllib.request
from pathlib import Path

NAME = "en_GB-alan-medium"
BASE = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/{NAME}"
dest = Path(__file__).resolve().parent.parent / "models" / "piper"
dest.mkdir(parents=True, exist_ok=True)
for ext in (".onnx", ".onnx.json"):
    target = dest / f"{NAME}{ext}"
    if not target.exists():
        print("downloading", target.name)
        urllib.request.urlretrieve(BASE + ext, target)
print("voice ready:", dest / f"{NAME}.onnx")
