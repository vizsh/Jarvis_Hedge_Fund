import { useEffect, useRef } from "react";

import { useChat } from "../lib/chat";
import { useLang } from "../lib/lang";
import { send } from "../lib/socket";
import { AnswerCard } from "./AnswerCard";

// [what is asked (the router understands English), what is shown in Hindi mode]
const STARTERS: [string, string][] = [
  ["Which of my mutual funds overlap?", "मेरे कौन से म्यूचुअल फ़ंड आपस में मिलते हैं?"],
  ["What does a 2% fee cost over 20 years?", "2% फ़ीस बीस साल में कितनी पड़ती है?"],
  ["How long will 3 lakh last if I spend 40000 a month?", "3 लाख रुपये 40000 महीने के ख़र्च पर कितना चलेंगे?"],
  ["Will 10000 a month reach 50 lakh in 15 years?", "10000 महीने की SIP से 15 साल में 50 लाख बनेंगे?"],
  ["Someone asked for my OTP on a call", "किसी ने फ़ोन पर मेरा OTP माँगा"],
  ["Give me my weekly digest", "मेरा साप्ताहिक सार सुनाइए"],
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

  const submit = (q: string, shown?: string) => { const v = q.trim(); if (v) send(v, shown); };

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
              {STARTERS.map(([q, h]) => <button key={q} className="achip" onClick={() => submit(q, hi ? h : undefined)}>{hi ? h : q}</button>)}
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
