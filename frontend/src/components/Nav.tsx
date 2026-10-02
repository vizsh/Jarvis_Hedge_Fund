import { useEffect, useState } from "react";

import { go, ROUTES, useRoute } from "../lib/router";
import { interrupt, onVoice } from "../lib/speak";
import { useStore } from "../lib/store";
import { useUI } from "../lib/ui";
import { useBargeIn } from "../lib/bargein";
import { useVoice } from "../lib/voice";
import { ForceStop } from "./Chrome";
import { MicIcon } from "./VoiceInput";

export function TopNav() {
  const route = useRoute();
  const connected = useStore((s) => s.connected);
  const fund = useStore((s) => s.fund);
  const setBuilder = useUI((s) => s.setBuilder);
  return (
    <header className="topnav">
      <a className="brand-mini" href="#/"><b>JARVIS</b><span>//</span>ALPHA OS</a>
      <nav className="navlinks" aria-label="Pages">
        {ROUTES.map((r) => (
          <a key={r.path} href={"#" + r.path} className={route === r.path ? "on" : ""}>{r.label}</a>
        ))}
      </nav>
      <div className="nav-right">
        <button className="btn sm ghost" onClick={() => setBuilder(true)}
                title="Load, build or paste a portfolio">
          {fund?.portfolio_name ?? "Portfolio"} ▾
        </button>
        <span className={`dot ${connected ? "live" : "dead"}`} title={connected ? "Connected" : "Offline"} />
        <ForceStop />
      </div>
    </header>
  );
}

/** The assistant, available on every page: a mic, what it is doing, and -- the part that
 *  matters -- a Stop button that is there the whole time it is speaking. */
export function Dock() {
  const route = useRoute();
  const status = useVoice((s) => s.status);
  const speakingMic = useVoice((s) => s.speaking);
  const heard = useVoice((s) => s.heard);
  const error = useVoice((s) => s.error);
  const toggle = useVoice((s) => s.toggle);
  const speech = useStore((s) => s.speech);
  const barge = useBargeIn();
  const [talking, setTalking] = useState(false);
  useEffect(() => onVoice((st) => setTalking(st === "speaking")), []);

  if (route === "/assistant") {
    return talking ? (
      <button className="stop-float" onClick={interrupt}>■ STOP — enough</button>
    ) : null;
  }

  const line =
    status === "starting" ? "Allow the microphone if asked…"
    : status === "listening" ? (speakingMic ? "Hearing you… pause when done" : "Listening — speak now")
    : status === "processing" ? "Transcribing locally…"
    : talking ? "Speaking…"
    : error ? error
    : heard ? `You said: “${heard}”`
    : "Ask anything. Tap the mic and speak.";

  return (
    <div className={`dock ${status} ${talking ? "talking" : ""}`}>
      <button className="dock-mic" onClick={toggle} disabled={status === "processing"}
              aria-label={status === "listening" ? "Stop listening and send" : "Speak to JARVIS"}>
        <MicIcon size={20} />
      </button>
      <div className="dock-body">
        <div className="dock-line">{line}</div>
        {!talking && speech && status === "idle" && !error && (
          <div className="dock-sub">{speech.length > 140 ? speech.slice(0, 138) + "…" : speech}</div>
        )}
        <label className="dock-toggle" title="Interrupt by talking over it. Works best with headphones.">
          <input type="checkbox" checked={barge.on} onChange={(e) => barge.set(e.target.checked)} />
          talk over me to interrupt <i>(headphones)</i>
        </label>
      </div>
      {talking && <button className="dock-stop" onClick={interrupt}>■ Stop</button>}
      <a className="dock-open" href="#/assistant">Open assistant</a>
    </div>
  );
}
