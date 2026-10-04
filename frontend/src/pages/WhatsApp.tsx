import { useEffect, useMemo, useRef, useState } from "react";

import "../styles-whatsapp.css";
import { Page } from "./Page";
import { useT } from "../lib/i18n";
import { go } from "../lib/router";
import { pstore } from "../lib/pstore";

type Msg = { id: number; who: "me" | "bot"; text: string; at: number; voice?: number; read?: boolean };
type Channel = "whatsapp:" | "";

const time = (t: number) => new Date(t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
const newNumber = () => "+9198" + String(Math.floor(Math.random() * 1e8)).padStart(8, "0");
let uid = 1;

/** Pull the tappable numbered options out of a bot message ("1. Woman" -> button that sends "1"). */
function split(text: string): { body: string; options: { n: string; label: string }[]; link: string | null } {
  const lines = text.split("\n");
  const options: { n: string; label: string }[] = [];
  const keep: string[] = [];
  let link: string | null = null;
  for (const l of lines) {
    const m = l.match(/^\s*(\d{1,2})\.\s+(.+)$/);
    if (m) { options.push({ n: m[1], label: m[2] }); continue; }
    const u = l.match(/🔗\s*(https?:\/\/\S+)/);
    if (u) { link = u[1]; continue; }
    keep.push(l);
  }
  return { body: keep.join("\n").replace(/\n{3,}/g, "\n\n").trim(), options, link };
}

function Bubble({ m, onPick, last }: { m: Msg; onPick: (n: string, label: string) => void; last: boolean }) {
  const { t } = useT();
  const parts = useMemo(() => (m.who === "bot" ? split(m.text) : null), [m]);
  const html = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/\*([^*\n]+)\*/g, "<b>$1</b>");
  const open = (url: string) => { try { const u = new URL(url); go(u.hash.replace(/^#/, "") || "/"); } catch { /* not a link */ } };
  return (
    <div className={`wa-row ${m.who}`}>
      <div className="wa-bubble">
        {m.voice !== undefined
          ? <span className="wa-voice">🎙 <i /><i /><i /><i /><i /> {Math.max(1, Math.round(m.voice))}s</span>
          : <span dangerouslySetInnerHTML={{ __html: html(parts ? parts.body : m.text) }} />}
        <span className="wa-meta">{time(m.at)}{m.who === "me" && <b className={m.read ? "read" : ""}> ✓✓</b>}</span>
      </div>
      {parts && parts.options.length > 0 && last && (
        <div className="wa-opts">{parts.options.map((o) => <button key={o.n} onClick={() => onPick(o.n, o.label)}>{o.n}. {o.label}</button>)}</div>
      )}
      {parts?.link && last && <button className="wa-open" onClick={() => open(parts.link!)}>↗ {t("Open this in the app", "ऐप में खोलें")}</button>}
    </div>
  );
}

export default function WhatsApp() {
  const { t, hi } = useT();
  const [channel, setChannel] = useState<Channel>("whatsapp:");
  const [number, setNumber] = useState<string>(() => pstore.get("sim.", "number", "") || newNumber());
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [typing, setTyping] = useState(false);
  const [rec, setRec] = useState<number | null>(null);          // seconds recorded so far, null = not recording
  const log = useRef<HTMLDivElement>(null);
  const recorder = useRef<{ mr: MediaRecorder; chunks: Blob[]; t0: number; timer: number } | null>(null);
  useEffect(() => pstore.set("sim.", "number", number), [number]);
  useEffect(() => { log.current?.scrollTo({ top: log.current.scrollHeight, behavior: "smooth" }); }, [msgs, typing]);

  const sender = channel + number;
  const base = location.origin;

  const deliver = async (texts: string[]) => {
    for (const x of texts) {
      setTyping(true);
      await new Promise((r) => setTimeout(r, Math.min(1400, 350 + x.length * 4)));
      setTyping(false);
      setMsgs((m) => [...m, { id: uid++, who: "bot", text: x, at: Date.now() }]);
    }
  };
  const markRead = () => setMsgs((m) => m.map((x) => (x.who === "me" ? { ...x, read: true } : x)));

  const send = async (body: string, shown?: string) => {
    if (!body.trim()) return;
    setMsgs((m) => [...m, { id: uid++, who: "me", text: shown ?? body, at: Date.now() }]);
    setText("");
    try {
      const r = await fetch(`/twilio/webhook?format=json&base=${encodeURIComponent(base)}`, {
        method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ From: sender, Body: body, MessageSid: "SIM" + Date.now() }),
      });
      markRead();
      await deliver((await r.json()).messages);
    } catch { markRead(); await deliver([t("I could not reach the server. Is the backend running?", "सर्वर तक नहीं पहुँच सका। क्या बैकएंड चल रहा है?")]); }
  };

  const startRec = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      const chunks: Blob[] = [];
      mr.ondataavailable = (e) => chunks.push(e.data);
      const t0 = Date.now();
      const timer = window.setInterval(() => setRec((Date.now() - t0) / 1000), 200);
      mr.start();
      recorder.current = { mr, chunks, t0, timer };
      setRec(0);
    } catch { void deliver([t("I could not use the microphone. Allow it in the browser, or type instead.", "माइक नहीं चल सका। ब्राउज़र में अनुमति दीजिए, या लिखकर भेजिए।")]); }
  };
  const stopRec = async (cancel = false) => {
    const r = recorder.current; if (!r) return;
    recorder.current = null; window.clearInterval(r.timer); setRec(null);
    const blob: Blob = await new Promise((res) => { r.mr.onstop = () => res(new Blob(r.chunks, { type: r.mr.mimeType })); r.mr.stop(); });
    r.mr.stream.getTracks().forEach((x) => x.stop());
    if (cancel) return;
    const secs = (Date.now() - r.t0) / 1000;
    setMsgs((m) => [...m, { id: uid++, who: "me", text: "", voice: secs, at: Date.now() }]);
    try {
      const res = await fetch(`/messaging/sim/voice?sender=${encodeURIComponent(sender)}&base=${encodeURIComponent(base)}`, { method: "POST", headers: { "Content-Type": blob.type || "audio/webm" }, body: blob });
      markRead();
      await deliver((await res.json()).messages);
    } catch { markRead(); await deliver([t("Could not send the voice note.", "वॉइस नोट नहीं भेज सका।")]); }
  };

  const reset = () => { setMsgs([]); setNumber(newNumber()); setTyping(false); void deliver([hi ? "'hi' लिखकर शुरू कीजिए। नंबर 1 से 9 भी चलते हैं।" : "Send 'hi' to start. Numbers 1 to 9 work too."]); };
  useEffect(() => { void deliver([hi ? "'hi' लिखकर शुरू कीजिए। नंबर 1 से 9 भी चलते हैं।" : "Send 'hi' to start. Numbers 1 to 9 work too."]); }, []); // eslint-disable-line

  const lastBot = [...msgs].reverse().find((m) => m.who === "bot")?.id;
  return (
    <Page title="WhatsApp" lead={t("The same tools on a phone chat: a numbered menu, one question at a time, voice notes, Hindi. This is the exact conversation a real WhatsApp or SMS number would have.",
      "फ़ोन की चैट पर वही औज़ार: नंबर वाला मेनू, एक बार में एक सवाल, वॉइस नोट, हिंदी। असली WhatsApp या SMS नंबर पर बिल्कुल यही बातचीत होगी।")}>
      <div className="wa-layout">
        <div className="wa-phone" role="region" aria-label="WhatsApp chat simulator">
          <header className="wa-head">
            <div className="wa-av">J</div>
            <div className="wa-title"><b>JARVIS</b><small>{typing ? t("typing…", "लिख रहा है…") : rec !== null ? t("recording…", "रिकॉर्ड हो रहा है…") : t("online", "ऑनलाइन")}</small></div>
            <select value={channel} onChange={(e) => { setChannel(e.target.value as Channel); }} aria-label="channel">
              <option value="whatsapp:">WhatsApp</option><option value="">SMS</option>
            </select>
            <button className="wa-icon" onClick={reset} title={t("New chat with a new number", "नए नंबर से नई चैट")} aria-label="new chat">↺</button>
          </header>
          <div className="wa-log" ref={log} aria-live="polite">
            {msgs.map((m) => <Bubble key={m.id} m={m} last={m.id === lastBot} onPick={(n, label) => void send(n, `${n}. ${label}`)} />)}
            {typing && <div className="wa-row bot"><div className="wa-bubble wa-typing"><i /><i /><i /></div></div>}
          </div>
          <div className="wa-quick">
            <button onClick={() => void send("menu")}>{t("Menu", "मेनू")}</button>
            <button onClick={() => void send(hi ? "English" : "हिंदी")}>{hi ? "English" : "हिंदी"}</button>
            <button onClick={() => void send("cancel")}>{t("Cancel", "रद्द")}</button>
          </div>
          <form className="wa-form" onSubmit={(e) => { e.preventDefault(); void send(text); }}>
            {rec === null ? (<>
              <input value={text} onChange={(e) => setText(e.target.value)} placeholder={t("Type a message", "संदेश लिखिए")} aria-label="message" />
              {text.trim() ? <button className="wa-go" aria-label="send">➤</button>
                : <button type="button" className="wa-go" aria-label="record a voice note" onClick={() => void startRec()}>🎙</button>}
            </>) : (<>
              <div className="wa-recbar"><span className="dot" /> {rec.toFixed(0)}s {t("Recording… tap ➤ to send", "रिकॉर्डिंग… भेजने के लिए ➤ दबाइए")}</div>
              <button type="button" className="wa-icon" onClick={() => void stopRec(true)} aria-label="cancel recording">🗑</button>
              <button type="button" className="wa-go" onClick={() => void stopRec()} aria-label="send voice note">➤</button>
            </>)}
          </form>
        </div>

        <aside className="wa-side">
          <h2>{t("Try these", "ये आज़माइए")}</h2>
          <ul>
            {[["hi", "hi"], ["1", t("1 · Check a moneylender", "1 · साहूकार का ब्याज")], ["3", t("3 · Government schemes", "3 · सरकारी योजनाएँ")],
              ["my sahukar charges 5 rupees per hundred a month on 50000 for 10 months", t("A full sentence", "पूरा वाक्य")],
              ["साहूकार पाँच रुपये सैकड़ा महीने पर पचास हज़ार रुपये दस महीने के लिए", t("In Hindi", "हिंदी में")],
              ["pay 10000 and get 20000 in 6 months, is this scheme genuine", t("Is this offer real?", "क्या यह ऑफ़र असली है?")],
              ["what is an expense ratio", t("A money word", "पैसे का कोई शब्द")]].map(([q, label]) =>
              <li key={q}><button onClick={() => void send(q, q)}>{label}</button></li>)}
          </ul>
          <p className="wa-note">{t("Tap an option under a reply instead of typing the number. Use 🎙 to send a voice note: it is transcribed on this machine and shown back as “I heard…” first.",
            "टाइप करने की जगह जवाब के नीचे का विकल्प दबाइए। 🎙 से वॉइस नोट भेजिए: वह इसी मशीन पर लिखा जाता है और पहले “मैंने सुना…” दिखता है।")}</p>
          <p className="wa-note">{t("To connect a real number, see docs/MESSAGING.md (Twilio webhook: /twilio/webhook).", "असली नंबर जोड़ने के लिए docs/MESSAGING.md देखिए (Twilio वेबहुक: /twilio/webhook)।")}</p>
        </aside>
      </div>
    </Page>
  );
}
