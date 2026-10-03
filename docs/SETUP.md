# Setup

Tested on Windows 11 with Python 3.11 and Node 22; nothing is Windows-specific.

## 1. Prerequisites

| Need | Why | Notes |
|---|---|---|
| Python 3.11 | backend | `pip install -r requirements.txt` |
| Node 18+ | build the UI | |
| [Ollama](https://ollama.com) | research desks and the assistant's *optional* intent picker | `ollama pull llama3.1:8b` (and `phi3:mini` for the router) |
| ~2 GB disk | models and data | Kokoro (~380 MB), Whisper `small.en` / `small`, snapshot |
| A microphone | voice input | browsers allow it on `localhost` |

The app works without Ollama (the research desks and the model fallback are unavailable; everything else works).

## 2. Install and build

```bash
pip install -r requirements.txt

python tools/ingest.py            # builds data/snapshot.db (~5 min; GDELT is the slow part)
python tools/get_voice.py         # downloads Piper voices and the Kokoro model files

cd frontend
npm install
npm run build                     # writes frontend/dist
cd ..
```

`requirements.txt` includes `kokoro-onnx`, `soundfile` and `piper-tts` for voices and `faster-whisper` for speech recognition. Whisper models download themselves on first use.

## 3. Run

```bash
python -m uvicorn backend.app:app --port 8000
```

Open <http://localhost:8000>. Startup takes ~40 s while the engines warm up (the first request after that is fast). Check `GET /health`.

Hot-reload UI development:

```bash
npm run dev --prefix frontend     # http://localhost:5173, proxies API routes to :8000
```

Every new backend route must be added to the proxy list in `frontend/vite.config.ts`.

## 4. Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `JARVIS_VOICE_EN` | `kokoro:bm_george` | default English voice (`kokoro:<id>` or a Piper model name) |
| `JARVIS_VOICE_HI` | `kokoro:hm_psi` | default Hindi voice |
| `JARVIS_STT_MODEL` | `small.en` | Whisper model for English speech |

## 5. First five minutes

1. Pick **EN** or **हिन्दी** (top right).
2. **Portfolio** page: load the example or paste your broker export.
3. **Assistant** page: try *"Which funds overlap the most?"*, *"What does a 2% fee cost over 20 years?"*, *"How long will 3 lakh last if I spend 40000 a month?"*, *"Someone asked for my OTP"*.
4. Press **Try it here** under an answer to play with the inline visual.
5. **Practice** page: rehearse the scam call (try *Speak*; allow the microphone).
6. Toggle **Voice + text / Text only**; press **Stop** at any time.

## 6. Tests

```bash
python -m pytest tests/ -q
```

See [TESTING.md](TESTING.md).

## 7. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| No sound | The voice may be on "Text only" (chat header) or silenced ("VOICE OFF" top right); also check `/tts/status` shows voices available |
| Voice missing | Run `python tools/get_voice.py`; confirm `models/kokoro/` has `kokoro-v1.0.onnx` and `voices-v1.0.bin` |
| Microphone does nothing | Allow it in the address bar; embedded browser panes may block it; use a normal browser at `http://localhost:8000` |
| Hindi shows when English is chosen | Hard-refresh (Ctrl+Shift+R) to load the current build; language is per screen |
| Features "do nothing" in dev mode | The route is missing from the proxy list in `vite.config.ts` |
| Port busy | `netstat -ano | findstr :8000` then stop the process, or use another `--port` |
| Slow first answer | Models warm up on the first call; later calls are fast |
| Research desks time out | Start Ollama and pull `llama3.1:8b` |
| `data/snapshot.db` missing | Run `python tools/ingest.py` |

## 8. Git hygiene

`models/`, `*.wav`, `*.log`, `data/*.db*` and `node_modules` are git-ignored; the snapshot and model files are rebuilt by the tools above.
