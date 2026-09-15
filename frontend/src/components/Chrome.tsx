import { useEffect, useRef, useState } from "react";

import { useStore, type Phase } from "../lib/store";
import { micError, send, startMic, stopMic } from "../lib/socket";
import * as socket from "../lib/socket";
import { VoiceBar } from "./VoiceBar";
import { onVoice } from "../lib/speak";
import { useGuide } from "../lib/guide";
import { Waveform } from "./Waveform";


const PHASES: Phase[] = ["boot", "core", "graph", "terminal", "simulate", "execute"];

/* ------------------------------------------------------------------ top bar */
export function TopBar({ onOpenBuilder }: { onOpenBuilder?: () => void }) {
  const connected = useStore((s) => s.connected);
  const t = useStore((s) => s.telemetry);
  const fund = useStore((s) => s.fund);
  const phase = useStore((s) => s.phase);
  const setPhase = useStore((s) => s.setPhase);

  return (
    <div className="topbar">
      <div className="brand">JARVIS<span> // </span>ALPHA OS</div>

      <button className="btn portfolio-btn" onClick={onOpenBuilder}
              title="Load, build or paste a portfolio">
        {fund?.portfolio_name ?? "Portfolio"} ▾
      </button>

      <div className="stat">
        <div className={`dot ${connected ? "live" : "dead"}`} />
        <span className="k">{connected ? "link" : "offline"}</span>
      </div>

      <div className="stat optional">
        <span className="k">model</span>
        <span className="v">{t?.model ?? fund?.model ?? "—"}</span>
      </div>

      <div className="stat">
        <span className="k">state</span>
        <span className="v hot">{(t?.orb ?? "idle").toUpperCase()}</span>
      </div>

      <ForceStop />

      <div className="spacer" />

      {/* The two most honest numbers in the product, so they live at eye level. */}
      <div className="stat">
        <span className="k">citations dropped</span>
        <span className={`v ${(t?.claims_rejected ?? 0) > 0 ? "hot" : ""}`}>
          {t?.claims_rejected ?? 0}
        </span>
      </div>
      <div className="stat">
        <span className="k">violations blocked</span>
        <span className={`v ${(t?.violations_blocked ?? 0) > 0 ? "bad" : ""}`}>
          {t?.violations_blocked ?? 0}
        </span>
      </div>
      {/* Never marked optional: the paper-only disclosure stays visible at every size. */}
      <div className="stat">
        <span className="k">broker</span>
        <span className="v hot">PAPER</span>
      </div>

      <div className="phase-pips">
        {PHASES.map((p, i) => (
          <div
            key={p}
            className={`pip ${phase === p ? "on" : ""}`}
            title={`${i + 1} · ${p}`}
            onClick={() => setPhase(p, true)}
          />
        ))}
      </div>
    </div>
  );
}

/** Force stop: one control, always at the top, that ends the voice and keeps it ended.
 *
 *  The bar at the bottom already has a Stop, and it was not enough — that one sets the
 *  SOFT latch, which the next question or the next guided-flow step lifts automatically.
 *  So the voice always came back within seconds and the control read as broken.
 *
 *  This one sets the hard latch: nothing the program does on its own can start it
 *  talking again. It is deliberately the only bright-red thing in the top bar, it never
 *  collapses at small widths, and Escape reaches it from anywhere. */
function ForceStop() {
  const [silenced, setSilenced] = useState(socket.voiceSilenced());

  useEffect(() => {
    // Mirror the engine rather than trusting this component's copy: the latch can also
    // be set from the keyboard or by another control.
    const off = onVoice(() => setSilenced(socket.voiceSilenced()));

    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      // Escape already closes the palette, a drill-down, the report and the flow
      // runner. Silencing on the same key would mean closing a dialog left the voice
      // permanently off with no visible cause, so Escape only reaches the voice when
      // there is nothing to dismiss.
      const g = useGuide.getState();
      if (g.palette || g.drill || g.report || g.flow) return;
      socket.forceStopVoice();
      setSilenced(true);
    };
    window.addEventListener("keydown", onKey);
    return () => { off(); window.removeEventListener("keydown", onKey); };
  }, []);

  const toggle = () => {
    if (silenced) socket.resumeVoice();
    else socket.forceStopVoice();
    setSilenced(!silenced);
  };

  return (
    <button className={`force-stop ${silenced ? "off" : ""}`} onClick={toggle}
            title={silenced
              ? "Voice is silenced. Click to let it speak again."
              : "Stop the voice and keep it stopped (Esc)"}>
      <span className="fs-icon" />
      {silenced ? "VOICE OFF" : "STOP VOICE"}
    </button>
  );
}

/* ------------------------------------------------------------------ command */
const SUGGESTIONS = [
  "analyse TCS",
  "buy 30 shares of Persistent",
  "what if we relax the sector cap to 40%",
  "rewind to 2020-03-23",
  "execute",
  "show me the portfolio",
];

export function CommandBar() {
  const [text, setText] = useState("");
  const [micOn, setMicOn] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [micMsg, setMicMsg] = useState<string | null>(null);
  const speech = useStore((s) => s.speech);
  const transcript = useStore((s) => s.transcript);
  const input = useRef<HTMLInputElement>(null);
  // React state cannot guard this. `startMic()` is async, so between keydown and the
  // moment `micOn` flips there is a 100-500ms window (longer on the permission
  // prompt) where a keyup sees micOn === false and silently drops the release --
  // the recorder then runs forever and the next keydown is blocked by the stale
  // guard. These refs hold the truth synchronously.
  const wantMic = useRef(false);      // is the key/button held RIGHT NOW
  const micBusy = useRef(false);      // a start or stop is in flight

  const submit = (value: string) => {
    const v = value.trim();
    if (!v) return;
    send(v);
    setText("");
  };

  const beginMic = async () => {
    if (wantMic.current || micBusy.current) return;   // key repeat, or already going
    wantMic.current = true;
    micBusy.current = true;
    let ok = false;
    try {
      ok = await startMic();
    } finally {
      // Always clear the guard. Leaving it latched is how the microphone ends up
      // permanently dead with no visible reason.
      micBusy.current = false;
    }
    if (!ok) {
      wantMic.current = false;
      setMicOn(false);
      setMicMsg(socket.micError);
      return;
    }
    setMicMsg(null);
    // Released while we were still asking for the microphone: honour the release
    // now rather than leaving a recorder running that nothing will ever stop.
    if (!wantMic.current) { void endMic(); return; }
    setMicOn(true);
  };

  const endMic = async () => {
    if (!wantMic.current && !micOn) {
      // Released before start finished; startMic's own guard handles the teardown.
      if (!micBusy.current) { await stopMic(); }
      return;
    }
    wantMic.current = false;
    if (micBusy.current) return;      // start still running; it will call us back
    setMicOn(false);
    setThinking(true);
    // Recording stops here and the utterance goes to faster-whisper on the backend,
    // which transcribes AND dispatches. We only surface what it heard.
    const result = await stopMic();
    setThinking(false);
    if (result?.transcript) setText(result.transcript);
    setMicMsg(result && !result.ok ? socket.micError : null);
  };

  // Push-to-talk on the spacebar, as long as you are not typing into the box.
  useEffect(() => {
    const typing = () => document.activeElement === input.current
      || (document.activeElement as HTMLElement)?.tagName === "TEXTAREA";
    const down = (e: KeyboardEvent) => {
      if (e.code === "Space" && !typing()) {
        e.preventDefault();
        if (e.repeat) return;          // holding a key fires keydown repeatedly
        void beginMic();
      }
      if (e.key === "/" && !typing()) {
        e.preventDefault();
        input.current?.focus();
      }
    };
    const up = (e: KeyboardEvent) => {
      if (e.code === "Space" && !typing()) { e.preventDefault(); void endMic(); }
    };
    // Losing focus mid-hold (alt-tab) never delivers the keyup, which would strand
    // the recorder open.
    const blur = () => { if (wantMic.current) void endMic(); };

    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    window.addEventListener("blur", blur);
    return () => {
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
      window.removeEventListener("blur", blur);
    };
  });

  return (
    <div className="command">
      <div className="jarvis-line">
        <span className="tag">JARVIS</span>
        <span>
          {micOn ? "Listening…"
            : thinking ? "Transcribing locally…"
            : speech || "Standing by. Hold SPACE to speak, or press / to type."}
        </span>
      </div>
      <Waveform active={micOn} />
      {micMsg && <div className="mic-error">{micMsg}</div>}
      {!micMsg && transcript && (
        <div className="heard">
          heard: &ldquo;{transcript}&rdquo;
        </div>
      )}

      <div className="cmdrow">
        <input
          ref={input}
          value={micOn && transcript ? transcript : text}
          placeholder="analyse TCS · buy 30 Persistent · rewind to 2020-03-23"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") submit(text); }}
        />
        <button className={`btn mic ${micOn ? "on" : ""}`}
                title="Hold to speak — transcribed locally by faster-whisper"
                onMouseDown={() => beginMic()}
                onMouseUp={() => endMic()}
                onMouseLeave={() => { if (wantMic.current) void endMic(); }}>
          {micOn ? "● REC" : thinking ? "…" : "HOLD"}
        </button>
        <button className="btn go" onClick={() => submit(text)}>Send</button>
      </div>

      <div className="cmd-foot">
        <div className="marks">
          {SUGGESTIONS.map((s) => (
            <div className="mark" key={s} onClick={() => submit(s)}>{s}</div>
          ))}
        </div>
        <VoiceBar />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ scrubber */
const STOPS = [
  { date: "2020-02-20", label: "PRE-CRASH" },
  { date: "2020-03-23", label: "COVID BOTTOM" },
  { date: "2020-06-30", label: "RECOVERY" },
  { date: "2023-01-10", label: "2023" },
  { date: "2026-09-14", label: "TODAY" },
];

export function Scrubber() {
  const simClock = useStore((s) => s.simClock);
  const fund = useStore((s) => s.fund);
  const day = simClock ? simClock.slice(0, 10) : "—";

  const t0 = new Date("2019-06-01").getTime();
  const t1 = new Date("2026-09-14").getTime();
  const now = simClock ? new Date(day).getTime() : t1;
  const position = Math.round(((now - t0) / (t1 - t0)) * 1000);

  return (
    <div className="scrubber">
      <div className="head">
        <span>Simulation clock · point-in-time guard ARMED</span>
        <span>{fund ? `${(fund.visible.prices + fund.visible.signals).toLocaleString()} rows visible` : ""}</span>
      </div>
      <div className="clock">{day}</div>
      <input
        type="range" min={0} max={1000} value={Number.isFinite(position) ? position : 1000}
        onChange={(e) => {
          const ms = t0 + (Number(e.target.value) / 1000) * (t1 - t0);
          send(`rewind to ${new Date(ms).toISOString().slice(0, 10)}`);
        }}
      />
      <div className="marks">
        {STOPS.map((s) => (
          <div className="mark" key={s.date} onClick={() => send(`rewind to ${s.date}`)}>
            {s.label}
          </div>
        ))}
      </div>
    </div>
  );
}
