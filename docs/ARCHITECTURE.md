# Architecture

JARVIS is one FastAPI process plus a static React build. Everything (data, models, voices) runs on the user's machine.

## 1. System view

```mermaid
flowchart TB
    subgraph Client["Browser tab"]
        Pages["Pages (hash router)"]
        Stores["zustand stores: store, chat, lang, ui, voice, guide, bargein"]
        Speak["speak.ts: one audio element, generation counter"]
        Sock["socket.ts: WebSocket + HTTP helpers"]
        Pages --> Stores --> Sock
        Stores --> Speak
    end

    subgraph Server["FastAPI (backend/app.py)"]
        HTTP["HTTP routes"]
        WS["/ws WebSocket"]
        Dispatch["dispatch(): command or question"]
        Assist["assistant.py"]
        Explain["explain.py (original explainer)"]
        Calc["analysis/*.py calculators"]
        Verna["vernacular.py + Hindi rule tables"]
        Bus["bus.py event bus"]
        Pipe["pipeline.py (desks, execution)"]
        TTS["tts.py"]
        STT["voice/stt.py"]
    end

    DB[("SQLite data/snapshot.db")]
    Ollama["Ollama (optional)"]

    Sock <--> WS
    Sock --> HTTP
    HTTP --> Dispatch --> Assist
    Assist --> Explain
    Assist --> Calc --> DB
    Assist -. "intent pick only" .-> Ollama
    Assist --> Verna
    Dispatch --> Bus --> WS
    Pipe --> Bus
    Pipe -. "research desks" .-> Ollama
    Speak -- "POST /tts" --> TTS
    Sock -- "POST /stt" --> STT
```

## 2. The three layers of the backend

| Layer | Files | Rule |
|---|---|---|
| **Truth** (numbers) | `analysis/*.py`, `risk/engine.py`, `backend/practice.py`, `backend/ledger.py`, `backend/digest.py` | Pure, deterministic, tested. No model is imported here. |
| **Meaning** (what was asked) | `backend/assistant.py`, `backend/explain.py`, `backend/intents.py`, `backend/router.py` | Rules first. A model may only choose among known intents. |
| **Words** (how it is said) | `backend/vernacular.py`, `hindi_rules.py`, `hindi_page_rules.py`, `glossary_hi.py`, `flows_hi.py`, `practice_hi.py` | Templates with numbers placed by code, English or Hindi. |

This separation is what lets the product be both friendly and verifiable.

## 3. Life of a question

```mermaid
sequenceDiagram
    participant U as User (tab A, Hindi)
    participant W as socket.ts
    participant S as app.py dispatch()
    participant A as assistant.aanswer()
    participant C as calculator
    participant V as vernacular
    U->>W: types "what does a 2% fee cost over 20 years?"
    W->>S: WS command {text, lang: "hi", cid: "ab12"}
    S->>S: set request language (contextvar)
    S->>A: _assist(text)
    A->>A: detect intent by rules (fee_drag)
    A->>C: tools.fee_drag(100000, 0, 20, 12, 2, 0.2)
    C-->>A: numbers
    A-->>S: Answer written in Hindi from templates
    S->>V: localize_answer (already Hindi: skip translator)
    S-->>W: SPEECH event {text, lang, answer, cid: "ab12"}
    W->>W: drop if cid is another tab, or lang differs from this screen
    W->>U: answer card in chat + (optional) spoken
```

Key points:

- **Per-screen language.** `LANG` on the server is only a fallback for announcements nobody asked for. Each request carries its own `lang` (a `contextvars.ContextVar` read by `_lang()`), so an English tab and a Hindi tab never override each other.
- **Own replies only.** Replies carry the asking tab's `cid`. `socket.ts` ignores events for other tabs, and ignores untagged announcements whose `lang` differs from the screen's language.
- **Stateless-ish.** Conversation memory (`explain.Conversation`) holds only the last subject, the last answer kind and the last tool question (for "explain that simpler").

## 4. Event bus and the frozen contract

`core/events.py` defines the **frozen** WebSocket contract (`PROTOCOL_VERSION = 1`): never remove or retype a field, only add optional ones. Event types cover boot, clock, transcript, intent, desk/claim/verdict, proposal, risk decision, execution, telemetry, speech and errors. `backend/bus.py` fans events out to every connected socket; speech payloads pass through `speech_filter` (`_speech_filter` in `app.py`) so announcements are language-consistent.

Replays (`recorder.py`) store the event stream **and** state snapshots, so a recorded demo is faithful even offline.

## 5. Data and state

| Store | Where | Contents |
|---|---|---|
| Snapshot | `data/snapshot.db` (SQLite, WAL) | prices, signals, documents, claims, decisions (see [DATA](DATA.md)) |
| Paper ledger | table `paper_ledger` | hash-chained, append-only (SQLite triggers refuse UPDATE/DELETE) |
| Lots | `lots` | the cost basis you typed (never guessed) |
| Portfolios | `portfolios` | saved and preset portfolios |
| Watches | `watches` | standing "tell me if" rules |
| Saved funds | `my_funds` | funds the user says they own |
| Session | memory (`backend/session.py`) | active portfolio, prices at the simulation clock, policy |

The **point-in-time store** (`core/pit.py`) is the only thing calculators read through: it filters on `published_at <= sim_clock`, so no number can see the future.

## 6. Voice path

```mermaid
flowchart LR
    Mic["Mic (MediaRecorder + timer VAD)"] -->|"POST /stt"| Whisper["faster-whisper (local)"]
    Whisper -->|"text (+ Hindi to English for commands)"| Dispatch
    Dispatch --> Answer
    Answer -->|"text per chunk"| Tts["POST /tts (Kokoro/Piper) -> WAV"]
    Tts --> Audio["one <audio> element"]
    Stop["Stop"] -->|"pause + clear queue + abort fetches + bump generation"| Audio
```

Details in [VOICE.md](VOICE.md).

## 7. Frontend structure

```mermaid
flowchart TD
    main["main.tsx"] --> App["App.tsx: shell + hash router"]
    App --> TopNav
    App --> Page["Page by route"]
    App --> Dock["Dock (mic + Stop)"]
    Page --> Home & Portfolio & Protect & Learn & Practice & Govern & Research & Assistant
    Assistant --> Orb["3D Orb"] & ChatThread & Jobs["JobsLauncher"] & CommandBar
    ChatThread --> AnswerCard --> Inline["Inline visuals: FeeDrag, EmergencyMeter, GoalFan, PanicSim, WeeklyDigest, ScamCall"]
```

Details in [FRONTEND.md](FRONTEND.md).

## 8. Runtime model

- One process: `uvicorn backend.app:app`. Startup loads the snapshot, warms the TTS engines in a thread and warms the language model.
- Background work uses `_spawn()` (tracked asyncio tasks); blocking work (TTS, Whisper) runs in threads.
- The built frontend (`frontend/dist`) is served by FastAPI; in development Vite serves it on :5173.

## 9. Invariants worth protecting

1. `risk/` never imports an LLM.
2. Calculators are pure and shared: the page slider and the chatbot call the **same** function, so they cannot disagree (tested).
3. A translator may never change a number (`numbers_preserved` guard).
4. `core/events.py` is frozen.
5. Raw audio and portfolios never leave the machine.
