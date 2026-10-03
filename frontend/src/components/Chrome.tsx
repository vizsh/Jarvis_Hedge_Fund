import { useEffect, useRef, useState } from "react";

import { useStore, type Phase } from "../lib/store";
import { send } from "../lib/socket";
import * as socket from "../lib/socket";
import { VoiceBar } from "./VoiceBar";
import { interrupt, isSpeaking, onVoice } from "../lib/speak";
import { useGuide } from "../lib/guide";
import { Waveform } from "./Waveform";
import { MicButton } from "./VoiceInput";
import { installVoiceKeys, useVoice } from "../lib/voice";


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
export function ForceStop() {
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
      // Same for the microphone: Esc while it is open means "cancel the recording",
      // not "silence JARVIS". The voice controller swallows the key first in a real
      // keypress, but listener order is not something to lean on.
      const mic = useVoice.getState().status;
      if (mic === "listening" || mic === "starting" || mic === "processing") return;
      // Esc while JARVIS is talking = "that's enough": stop it NOW, no latch. (The
      // STOP VOICE button is the one that keeps it quiet afterwards.)
      if (isSpeaking()) { interrupt(); return; }
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
  "Which of my mutual funds overlap?",
  "What does a 2% fee cost over 20 years?",
  "How long will 3 lakh last if I spend 40000 a month?",
  "Give me my weekly digest",
  "analyse TCS",
  "buy 30 shares of Persistent",
];

export function CommandBar() {
  const [text, setText] = useState("");
  const [, tick] = useState(0);
  const speech = useStore((s) => s.speech);
  const transcript = useStore((s) => s.transcript);
  const status = useVoice((s) => s.status);
  const speaking = useVoice((s) => s.speaking);
  const heard = useVoice((s) => s.heard);
  const heardAt = useVoice((s) => s.heardAt);
  const error = useVoice((s) => s.error);
  const clearError = useVoice((s) => s.clearError);
  const input = useRef<HTMLInputElement>(null);

  const submit = (value: string) => {
    const v = value.trim();
    if (!v) return;
    send(v);
    setText("");
  };

  // SPACE and Escape for the microphone, and "/" to jump to the text box. The microphone
  // logic itself lives in lib/voice.ts so the orb, this panel and the keyboard are all
  // driving one state machine rather than three half-copies of it.
  useEffect(() => {
    const typing = () => document.activeElement === input.current
      || (document.activeElement as HTMLElement)?.tagName === "TEXTAREA";
    const off = installVoiceKeys(typing);
    const slash = (e: KeyboardEvent) => {
      if (e.key === "/" && !typing()) { e.preventDefault(); input.current?.focus(); }
    };
    window.addEventListener("keydown", slash);
    return () => { off(); window.removeEventListener("keydown", slash); };
  }, []);

  // Let the "I heard" card age out.
  useEffect(() => {
    if (!heardAt) return;
    const id = window.setTimeout(() => tick((n) => n + 1), 12000);
    return () => window.clearTimeout(id);
  }, [heardAt]);

  const shownHeard = (transcript || heard);
  const recentlyHeard = !!shownHeard && Date.now() - heardAt < 12000;

  const status_line =
    status === "starting" ? "Allow the microphone if your browser asks…"
    : status === "listening"
      ? (speaking ? "Hearing you… pause when you are done." : "Listening — speak now.")
    : status === "processing" ? "Transcribing locally…"
    : speech || "Standing by. Tap the mic or click the orb to speak, or press / to type.";

  return (
    <div className={`command ${status}`}>
      <div className="jarvis-line">
        <span className="tag">JARVIS</span>
        <span>{status_line}</span>
      </div>
      <Waveform active={status === "listening"} />
      {error && status === "idle" && (
        <div className="mic-error" onClick={clearError}>{error}</div>
      )}
      {!error && recentlyHeard && status !== "listening" && (
        <div className="heard-card">
          <span className="heard-label">I heard</span>
          <span className="heard-text">&ldquo;{shownHeard}&rdquo;</span>
        </div>
      )}

      <div className="cmdrow">
        <input
          id="command-input"
          ref={input}
          value={text}
          placeholder="Ask about funds, fees, savings, goals or scams — or: analyse TCS"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") submit(text); }}
        />
        <MicButton />
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
