import { useEffect, useRef } from "react";

import { useChat } from "../lib/chat";
import { useLang } from "../lib/lang";
import { send } from "../lib/socket";
import { AnswerCard } from "./AnswerCard";

const STARTERS = [
  "Which of my mutual funds overlap?",
  "What does a 2% fee cost over 20 years?",
  "How long will 3 lakh last if I spend 40000 a month?",
  "Will 10000 a month reach 50 lakh in 15 years?",
  "Someone asked for my OTP on a call",
  "Give me my weekly digest",
];

/** Switch between hearing the answer and only reading it. The text is always shown. */
export function VoiceToggle() {
  const voice = useChat((s) => s.voice);
  const setVoice = useChat((s) => s.setVoice);
  const hi = useLang((s) => s.lang) === "hi";
  return (
    <button className={`voicetoggle ${voice ? "on" : "off"}`} role="switch" aria-checked={voice}
            onClick={() => setVoice(!voice)}
            title={voice ? "Answers are spoken and shown. Click to read only." : "Answers are shown only. Click to hear them too."}>
      <span className="vt-ico" aria-hidden>{voice ? "🔊" : "🔇"}</span>
      <span>{voice ? (hi ? "आवाज़ + टेक्स्ट" : "Voice + text") : (hi ? "सिर्फ़ टेक्स्ट" : "Text only")}</span>
    </button>
  );
}

export function ChatThread() {
  const messages = useChat((s) => s.messages);
  const clear = useChat((s) => s.clear);
  const hi = useLang((s) => s.lang) === "hi";
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => { end.current?.scrollIntoView({ block: "end", behavior: "smooth" }); }, [messages.length]);

  const submit = (q: string) => { const v = q.trim(); if (v) send(v); };

  return (
    <aside className="chat" aria-label="Conversation">
      <div className="chat-head">
        <b>{hi ? "बातचीत" : "Conversation"}</b>
        <VoiceToggle />
        {messages.length > 0 && <button className="abtn" onClick={clear}>{hi ? "साफ़" : "Clear"}</button>}
      </div>

      <div className="chat-body">
        {messages.length === 0 && (
          <div className="chat-empty">
            <p>{hi ? "कुछ भी पूछिए। मैं हर आँकड़ा कैलकुलेटर से निकालता हूँ, अंदाज़े से नहीं।"
                   : "Ask anything about your money. Every figure comes from a calculator, not a guess."}</p>
            <div className="achips">
              {STARTERS.map((q) => <button key={q} className="achip" onClick={() => submit(q)}>{q}</button>)}
            </div>
          </div>)}

        {messages.map((m) => m.who === "you"
          ? <div key={m.id} className="bubble-you">{m.text}</div>
          : m.answer
            ? <AnswerCard key={m.id} a={m.answer} onAsk={submit} compact />
            : <div key={m.id} className="bubble-jarvis">{m.text}</div>)}
        <div ref={end} />
      </div>

    </aside>
  );
}
