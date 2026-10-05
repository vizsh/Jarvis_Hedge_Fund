import { useEffect, useRef, useState } from "react";

import { useChat, type ChatMessage } from "../lib/chat";
import { useLang } from "../lib/lang";
import { send } from "../lib/socket";
import { AnswerCard } from "./AnswerCard";
import { Icon } from "./Icon";

// [what is asked (the router understands English), what is shown in Hindi mode]
const GROUPS: { icon: string; en: string; hi: string; qs: [string, string][] }[] = [
  { icon: "research", en: "Research a company", hi: "कंपनी का शोध", qs: [["Analyse TCS", "TCS का विश्लेषण कीजिए"], ["Compare Reliance and HDFC Bank", "Reliance और HDFC Bank की तुलना कीजिए"], ["How is Infosys doing?", "Infosys कैसा चल रहा है?"]] },
  { icon: "protect", en: "Protect me", hi: "मुझे बचाइए", qs: [["Someone from the bank asked for my OTP on a call", "बैंक से किसी ने फ़ोन पर मेरा OTP माँगा"], ["A Telegram group promises guaranteed 20% returns", "टेलीग्राम ग्रुप 20% पक्के रिटर्न का वादा करता है"], ["My father lost 50000 on a fake trading app", "मेरे पिता ने नक़ली ट्रेडिंग ऐप में 50000 खो दिए"]] },
  { icon: "learn", en: "Understand money", hi: "पैसा समझिए", qs: [["Should I invest through SIP or lump sum?", "SIP से निवेश करूँ या एकमुश्त?"], ["How are mutual funds taxed?", "म्यूचुअल फ़ंड पर कर कैसे लगता है?"], ["What should I do when the market falls?", "बाज़ार गिरे तो मुझे क्या करना चाहिए?"]] },
  { icon: "portfolio", en: "Your own numbers", hi: "आपके अपने आँकड़े", qs: [["Why did my portfolio fall?", "मेरा पोर्टफ़ोलियो क्यों गिरा?"], ["What does a 2% fee cost over 20 years?", "2% फ़ीस बीस साल में कितनी पड़ती है?"], ["How long will 3 lakh last if I spend 40000 a month?", "3 लाख रुपये 40000 महीने के ख़र्च पर कितना चलेंगे?"]] },
  { icon: "assistant", en: "Learn this app", hi: "यह ऐप सीखिए", qs: [["How does this prototype work?", "यह प्रोटोटाइप कैसे काम करता है?"], ["Walk me through the audit record", "ऑडिट रिकॉर्ड घुमाकर समझाइए"], ["Help me understand the fee slider", "फ़ीस स्लाइडर समझने में मदद कीजिए"]] },
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
      <Icon name={voice ? "speaker" : "close"} size={14} />
      <span>{voice ? (hi ? "आवाज़ + टेक्स्ट" : "Voice + text") : (hi ? "सिर्फ़ टेक्स्ट" : "Text only")}</span>
    </button>
  );
}

interface Turn { q?: ChatMessage; a?: ChatMessage }
function turns(ms: ChatMessage[]): Turn[] {
  const out: Turn[] = [];
  for (const m of ms) {
    if (m.who === "you") out.push({ q: m });
    else if (out.length && out[out.length - 1].q && !out[out.length - 1].a) out[out.length - 1].a = m;
    else out.push({ a: m });
  }
  return out;
}

const ago = (t: number, hi: boolean) => new Date(t).toLocaleTimeString(hi ? "hi-IN" : "en-IN", { hour: "numeric", minute: "2-digit" });

/** The conversation: each question sits above its own answer in one block, so it is always clear what an answer is an answer to. */
export function ChatThread() {
  const messages = useChat((s) => s.messages);
  const pending = useChat((s) => s.pending);
  const clear = useChat((s) => s.clear);
  const hi = useLang((s) => s.lang) === "hi";
  const end = useRef<HTMLDivElement>(null);
  const [, bump] = useState(0);

  useEffect(() => { end.current?.scrollIntoView({ block: "end", behavior: "smooth" }); }, [messages.length, pending]);
  useEffect(() => {
    if (!pending) return;
    const id = window.setTimeout(() => bump((n) => n + 1), 45000);
    return () => window.clearTimeout(id);
  }, [pending]);
  const waiting = pending > 0 && Date.now() - pending < 45000;

  const submit = (q: string, shown?: string) => { const v = q.trim(); if (v) send(v, shown); };
  const list = turns(messages);

  return (
    <section className="as-chat" aria-label="Conversation" data-tour="chat">
      <div className="as-head">
        <div className="as-title"><h2>{hi ? "जार्विस से पूछिए" : "Ask Jarvis"}</h2><span>{hi ? "हर आँकड़ा कैलकुलेटर से, अंदाज़े से नहीं" : "Every figure from a calculator, never a guess"}</span></div>
        <VoiceToggle />
        {messages.length > 0 && <button className="as-clear" onClick={clear}>{hi ? "साफ़ करें" : "Clear"}</button>}
      </div>

      <div className="as-thread">
        {list.length === 0 && (
          <div className="as-empty">
            <h3>{hi ? "आज आप क्या जानना चाहते हैं?" : "What would you like to know today?"}</h3>
            <p>{hi ? "अपने शब्दों में पूछिए: मैं सवाल को पूरा समझकर जवाब देता हूँ, किसी एक शब्द पर नहीं। नीचे के हर सवाल पर पूरा जवाब तैयार है।" : "Ask in your own words. I read the whole question, not one keyword in it. Every example below has a complete answer behind it."}</p>
            <div className="as-groups">
              {GROUPS.map((g) => (
                <div className="as-group" key={g.en}>
                  <h4><Icon name={g.icon} size={15} /> {hi ? g.hi : g.en}</h4>
                  {g.qs.map(([q, h]) => <button key={q} onClick={() => submit(q, hi ? h : undefined)}>{hi ? h : q}</button>)}
                </div>))}
            </div>
          </div>)}

        {list.map((t, i) => (
          <div className="turn" key={t.q?.id ?? t.a?.id ?? i}>
            {t.q && <div className="turn-q"><span className="turn-label">{hi ? "आपने पूछा" : "You asked"} · {ago(t.q.at, hi)}</span><p>{t.q.text}</p></div>}
            {t.a && (t.a.answer
              ? <AnswerCard a={t.a.answer} onAsk={submit} />
              : <div className="turn-plain">{t.a.text}</div>)}
          </div>))}

        {waiting && (
          <div className="turn-wait" role="status" aria-live="polite">
            <span /><span /><span />
            <em>{hi ? "आपका सवाल समझ रहा हूँ…" : "Reading your question…"}</em>
          </div>)}
        <div ref={end} />
      </div>
    </section>
  );
}
