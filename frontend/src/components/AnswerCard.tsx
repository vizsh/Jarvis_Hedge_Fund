import { useState } from "react";

import "../styles-chat.css";

import { answerText, type AnswerData } from "../lib/chat";
import { useLang } from "../lib/lang";
import { go } from "../lib/router";
import { speak, stop as stopSpeech } from "../lib/speak";
import { EmergencyMeter, FeeDrag, WeeklyDigest } from "../pages/PracticeMore";
import { GoalFan, PanicSim } from "../pages/Demos";
import { ScamCall } from "../pages/Practice";
import { RecoveryCoach } from "../pages/Recovery";

/** One structured answer: headline, key figures, a table when there is one, the steps, what to
 *  do next, how it was worked out, and tappable follow-ups. Used by the chat thread and the
 *  Learn page so a question looks the same wherever it is asked. */
export function AnswerCard({ a, onAsk, compact = false }: {
  a: AnswerData; onAsk: (q: string, shown?: string) => void; compact?: boolean;
}) {
  const lang = useLang((s) => s.lang);
  const hi = lang === "hi";
  const [copied, setCopied] = useState(false);
  const [inline, setInline] = useState(false);
  // The fee answer can be played with right here, with the figures it was computed from.
  const canInline = ["fee_drag", "emergency", "goal", "panic", "digest", "scam_help", "scam_recovery"].includes(a.kind) && !!a.visual;
  const chips = a.follow_ups ?? [];

  const open = () => {
    if (!a.visual) return;
    const q = new URLSearchParams(Object.entries(a.visual.params ?? {}).map(([k, v]) => [k, String(v)])).toString();
    go(`/${a.visual.page}${q ? "?" + q : ""}`);
  };
  const copy = async () => {
    const text = [answerText(a), ...(a.table ? a.table.rows.map((r) => r.join(" | ")) : [])].join("\n");
    try { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch { /* clipboard blocked */ }
  };

  return (
    <div className={`acard ${a.kind} ${compact ? "compact" : ""}`}>
      <div className="acard-head">{a.headline}</div>

      {!!a.facts?.length && (
        <div className="afacts">
          {a.facts.map((f, i) => (
            <div key={i} className={`afact ${f.tone ?? ""}`}>
              <span className="afact-v">{f.value}</span>
              <span className="afact-l">{f.label}</span>
            </div>))}
        </div>)}

      {a.table && a.table.rows.length > 0 && (
        <div className="atable-wrap">
          <table className="atable">
            <thead><tr>{a.table.columns.map((c, i) => <th key={i}>{c}</th>)}</tr></thead>
            <tbody>{a.table.rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}>{c}</td>)}</tr>)}</tbody>
          </table>
        </div>)}

      {!!a.bullets?.length && (
        <ul className="abullets">{a.bullets.map((b, i) => <li key={i}>{b}</li>)}</ul>)}

      {a.action && <div className="aaction"><span aria-hidden>→</span> {a.action}</div>}

      {canInline && inline && (a.kind === "fee_drag" ? <FeeDrag init={a.visual!.params} compact />
        : a.kind === "emergency" ? <EmergencyMeter init={a.visual!.params} compact />
        : a.kind === "scam_recovery" ? <RecoveryCoach init={a.visual!.params} compact />
        : a.kind === "scam_help" ? <ScamCall init={a.visual!.params} compact />
        : a.kind === "digest" ? <WeeklyDigest compact autoPlay />
        : a.kind === "panic" ? <PanicSim init={a.visual!.params} compact />
        : <GoalFan init={a.visual!.params} compact />)}

      {a.detail && (
        <details className="adetail">
          <summary>{hi ? "यह कैसे निकाला गया" : "How this was worked out"}</summary>
          <p>{a.detail}</p>
        </details>)}

      <div className="atools">
        {canInline && <button className="abtn primary" aria-expanded={inline} onClick={() => setInline((v) => !v)}>
          {inline ? (hi ? "बंद करें ▴" : "Hide it ▴") : a.kind === "scam_recovery" ? (hi ? "🛟 यहीं कोच खोलें" : "🛟 Open the coach here") : a.kind === "scam_help" ? (hi ? "☎ यहीं अभ्यास करें" : "☎ Rehearse it here") : a.kind === "digest" ? (hi ? "▶ यहीं सुनिए" : "▶ Play it here") : (hi ? "यहीं आज़माइए ▾" : "Try it here ▾")}</button>}
        {a.visual && <button className={`abtn ${canInline ? "" : "primary"}`} onClick={open}>{canInline ? (hi ? "पूरे पेज पर खोलें ↗" : "Open full page ↗") : `${a.visual.label} ↗`}</button>}
        <button className="abtn" onClick={() => speak(answerText(a), a.lang === "hi" ? "hi" : "en", true)}
                title={hi ? "ज़ोर से पढ़ें" : "Read this aloud"}>🔊 {hi ? "सुनें" : "Read aloud"}</button>
        <button className="abtn" onClick={() => stopSpeech()} title={hi ? "आवाज़ रोकें" : "Stop the voice"}>■</button>
        <button className="abtn" onClick={copy}>{copied ? (hi ? "कॉपी हुआ ✓" : "Copied ✓") : (hi ? "कॉपी" : "Copy")}</button>
      </div>

      {chips.length > 0 && (
        <div className="achips">
          {chips.map((q, i) => (
            <button key={q} className="achip" onClick={() => onAsk(q, (hi && a.follow_ups_hi?.[i]) || undefined)}>{(hi && a.follow_ups_hi?.[i]) || q}</button>))}
        </div>)}
    </div>
  );
}
