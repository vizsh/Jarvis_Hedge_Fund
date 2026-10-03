import { useEffect, useState } from "react";

import { go, HI_LABEL, ROUTES, useRoute } from "../lib/router";
import { onVoice, stop as stopNow } from "../lib/speak";
import { useStore } from "../lib/store";
import { useUI } from "../lib/ui";
import { useBargeIn } from "../lib/bargein";
import { useVoice } from "../lib/voice";
import { setVoiceFor, useLang, voiceFor } from "../lib/lang";
import { speak } from "../lib/speak";
import { ForceStop } from "./Chrome";
import { MicIcon } from "./VoiceInput";
import { usePilot } from "../lib/pilot";
import { send } from "../lib/socket";

function VoicePicker() {
  const lang = useLang((s) => s.lang);
  const [voices, setVoices] = useState<{ id: string; label: string; lang: string }[]>([]);
  const [, bump] = useState(0);
  useEffect(() => { fetch("/tts/status").then((r) => r.json()).then((d) => setVoices(d.voices ?? [])).catch(() => {}); }, []);
  const mine = voices.filter((v) => v.lang === lang);
  if (mine.length < 2) return null;
  const chosen = voiceFor(lang) ?? mine[0].id;
  return (
    <select className="voicesel" aria-label="Voice" value={chosen} title="Choose the voice"
            onChange={(e) => {
              setVoiceFor(lang, e.target.value); bump((n) => n + 1);
              speak(lang === "hi" ? "नमस्ते, मैं जार्विस हूँ। आपकी मदद के लिए तैयार।" : "Hello, I'm JARVIS. Ready when you are.", lang);
            }}>
      {mine.map((v) => <option key={v.id} value={v.id}>{v.label}</option>)}
    </select>
  );
}

function LangSwitch() {
  const lang = useLang((s) => s.lang);
  const set = useLang((s) => s.set);
  return (
    <div className="langsw" role="group" aria-label="Answer language">
      <button className={lang === "en" ? "on" : ""} onClick={() => set("en")}>EN</button>
      <button className={lang === "hi" ? "on" : ""} onClick={() => set("hi")} title="उत्तर हिन्दी में">हिन्दी</button>
    </div>
  );
}

export function TopNav() {
  const route = useRoute();
  const lang = useLang((s) => s.lang);
  const connected = useStore((s) => s.connected);
  const fund = useStore((s) => s.fund);
  const setBuilder = useUI((s) => s.setBuilder);
  return (
    <header className="topnav">
      <a className="brand-mini" href="#/"><b>JARVIS</b><span>//</span>ALPHA OS</a>
      <nav className="navlinks" aria-label="Pages">
        {ROUTES.map((r) => (
          <a key={r.path} href={"#" + r.path} className={route === r.path ? "on" : ""}>{lang === "hi" ? HI_LABEL[r.label] ?? r.label : r.label}</a>
        ))}
      </nav>
      <div className="nav-right">
        <button className="btn sm ghost" onClick={() => setBuilder(true)}
                title="Load, build or paste a portfolio">
          {fund?.portfolio_name ?? "Portfolio"} ▾
        </button>
        <LangSwitch />
        <VoicePicker />
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
  const guide = usePilot((s) => s.guide);
  const [typed, setTyped] = useState("");
  const hi = useLang((s) => s.lang) === "hi";
  const [talking, setTalking] = useState(false);
  useEffect(() => onVoice((st) => setTalking(st === "speaking")), []);

  if (route === "/assistant") {
    return talking ? (
      <button className="stop-float" onClick={stopNow}>■ STOP — enough</button>
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
      {(guide?.ask || (guide?.done && guide.next?.length)) && (
        <div className="dock-guide">
          <div className="dock-guide-head">
            <span className="dock-logo" aria-hidden>J</span>
            <b>{guide.label ?? "JARVIS"}</b>
            {guide.step && <span className="dock-step">{guide.step[0]}/{guide.step[1]}</span>}
            <button className="dock-x" aria-label="cancel" onClick={() => (guide.ask ? send("cancel", hi ? "रद्द" : "cancel") : usePilot.getState().set(null))}>✕</button>
          </div>
          {guide.ask ? (<>
            <div className="dock-q">{guide.ask.question}</div>
            {guide.ask.example && <div className="dock-sub">{guide.ask.example}</div>}
            {guide.ask.choices && <div className="dock-chips">{guide.ask.choices.map((c) => <button key={c.text} onClick={() => send(c.text, c.label)}>{c.label}</button>)}</div>}
          </>) : (<>
            <div className="dock-sub">{hi ? "आगे क्या?" : "What next?"}</div>
            <div className="dock-chips">{guide.next!.map((q) => <button key={q} onClick={() => send(q)}>{q}</button>)}</div>
          </>)}
        </div>
      )}
      <button className="dock-mic" onClick={toggle} disabled={status === "processing"}
              aria-label={status === "listening" ? "Stop listening and send" : "Speak to JARVIS"}>
        <MicIcon size={20} />
      </button>
      <div className="dock-body">
        <div className="dock-line">{line}</div>
        {!talking && speech && status === "idle" && !error && (
          <div className="dock-sub">{speech.length > 140 ? speech.slice(0, 138) + "…" : speech}</div>
        )}
        <input className="dock-input" value={typed} onChange={(e) => setTyped(e.target.value)}
               placeholder={guide?.ask ? (hi ? "यहाँ जवाब लिखिए…" : "Type your answer…") : (hi ? "आगे पूछिए…" : "Ask next…")}
               onKeyDown={(e) => { if (e.key === "Enter" && typed.trim()) { send(typed.trim()); setTyped(""); } }} />
        <label className="dock-toggle" title="Interrupt by talking over it. Works best with headphones.">
          <input type="checkbox" checked={barge.on} onChange={(e) => barge.set(e.target.checked)} />
          talk over me to interrupt <i>(headphones)</i>
        </label>
      </div>
      {talking && <button className="dock-stop" onClick={stopNow}>■ Stop</button>}
      <a className="dock-open" href="#/assistant">Open assistant</a>
    </div>
  );
}
