import { useEffect, useRef, useState } from "react";

import { hiError, useT } from "../lib/i18n";
import { send } from "../lib/socket";
import { useStore } from "../lib/store";
import { installVoiceKeys, useVoice } from "../lib/voice";
import { HeardDraft } from "./Chrome";
import { Icon } from "./Icon";
import { MicIcon } from "./VoiceInput";
import { VoiceBar } from "./VoiceBar";
import { Waveform } from "./Waveform";

/** The message box: one rounded field with the microphone and send inside it, the voice state in plain words underneath,
 *  and the voice controls (stop, quiet for, pace) tucked behind one button instead of lined up beside every message. */
export function Composer() {
  const { hi, t } = useT();
  const [text, setText] = useState("");
  const [opts, setOpts] = useState(false);
  const [, tick] = useState(0);
  const box = useRef<HTMLTextAreaElement>(null);
  const speech = useStore((s) => s.speech);
  const status = useVoice((s) => s.status);
  const hearing = useVoice((s) => s.speaking);
  const heard = useVoice((s) => s.heard);
  const heardAt = useVoice((s) => s.heardAt);
  const error = useVoice((s) => s.error);
  const clearError = useVoice((s) => s.clearError);
  const toggle = useVoice((s) => s.toggle);

  const submit = () => { const v = text.trim(); if (!v) return; send(v); setText(""); };

  useEffect(() => {
    const typing = () => document.activeElement === box.current || (document.activeElement as HTMLElement)?.tagName === "TEXTAREA";
    const off = installVoiceKeys(typing);
    const slash = (e: KeyboardEvent) => { if (e.key === "/" && !typing() && !(document.activeElement as HTMLElement)?.matches?.("input,select")) { e.preventDefault(); box.current?.focus(); } };
    window.addEventListener("keydown", slash);
    return () => { off(); window.removeEventListener("keydown", slash); };
  }, []);

  useEffect(() => {
    if (!heardAt) return;
    const id = window.setTimeout(() => tick((n) => n + 1), 9000);
    return () => window.clearTimeout(id);
  }, [heardAt]);

  // grow with the text, up to five lines
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 128) + "px";
  }, [text]);

  const recently = !!heard && Date.now() - heardAt < 9000;
  const line =
    status === "starting" ? t("Allow the microphone if your browser asks…", "ब्राउज़र पूछे तो माइक की अनुमति दीजिए…")
    : status === "listening" ? (hearing ? t("Hearing you… pause when you are done.", "सुन रहा हूँ… बोल चुकें तो रुकिए।") : t("Listening. Speak now.", "सुन रहा हूँ। अब बोलिए।"))
    : status === "processing" ? t("Turning your voice into text on this machine…", "आपकी आवाज़ को इसी मशीन पर लिख रहा हूँ…")
    : error ? (hiError(error, hi) ?? "")
    : recently ? `${t("I heard", "मैंने सुना")}: “${heard}”`
    : null;

  return (
    <div className={`cmp ${status}`} data-tour="composer">
      <HeardDraft />
      {line && <div className={`cmp-line ${error && status === "idle" ? "bad" : ""}`} role="status" onClick={error ? clearError : undefined}>
        {status === "listening" && <Waveform active />}
        <span>{line}</span>
      </div>}
      <div className="cmp-row">
        <textarea
          id="command-input" ref={box} rows={1} value={text} onChange={(e) => setText(e.target.value)}
          placeholder={t("Ask anything: “analyse TCS”, “is this call a scam?”, “how does the fee slider work?”", "कुछ भी पूछिए: “TCS का विश्लेषण”, “क्या यह कॉल ठगी है?”, “फ़ीस स्लाइडर कैसे काम करता है?”")}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
          aria-label={t("Ask Jarvis", "जार्विस से पूछिए")}
        />
        <button className={`cmp-mic ${status}`} id="mic-button" onClick={toggle} disabled={status === "processing"} aria-pressed={status === "listening"}
                aria-label={status === "listening" ? t("Stop listening and send", "सुनना बंद करके भेजें") : t("Speak your question", "बोलकर पूछिए")}
                title={t("Tap to speak. Pause, or tap again, to send. Esc cancels.", "बोलने के लिए दबाइए। रुकिए, या भेजने को फिर दबाइए। Esc रद्द करता है।")}>
          <MicIcon size={18} />
        </button>
        <button className="cmp-send" onClick={submit} disabled={!text.trim()} aria-label={t("Send", "भेजें")}><Icon name="arrow" size={18} /></button>
      </div>
      <div className="cmp-foot">
        <span className="cmp-hint">{speech && status === "idle" && !recently && !error ? "" : ""}{t("Enter to send · Shift+Enter for a new line · / to jump here", "भेजने को Enter · नई पंक्ति को Shift+Enter · यहाँ आने को /")}</span>
        <button className={`cmp-opt ${opts ? "on" : ""}`} onClick={() => setOpts(!opts)} aria-expanded={opts}>{t("Voice options", "आवाज़ के विकल्प")} {opts ? "▴" : "▾"}</button>
      </div>
      {opts && <div className="cmp-opts"><VoiceBar /></div>}
    </div>
  );
}
