import { useState } from "react";

import "../styles-chat.css";
import "../styles-summary.css";
import "../styles-assistant.css";

import { answerText, type AnswerData, type ReadItem } from "../lib/chat";
import { useLang } from "../lib/lang";
import { go } from "../lib/router";
import { send } from "../lib/socket";
import { speak, stop as stopSpeech } from "../lib/speak";
import { startTour } from "../lib/tour";
import { EmergencyMeter, FeeDrag, WeeklyDigest } from "../pages/PracticeMore";
import { GoalFan, PanicSim } from "../pages/Demos";
import { ScamCall } from "../pages/Practice";
import { RecoveryCoach } from "../pages/Recovery";
import { CompareChart, PriceChart } from "./charts/PriceChart";
import { Icon } from "./Icon";

/** What sort of answer this is, in words, so a glance tells you whether it is a calculation, a company read, an explanation or a warning. */
const KIND: Record<string, [string, string, string]> = {
  scam_help: ["Scam safety", "ठगी से सुरक्षा", "risk"], scam_recovery: ["Scam recovery", "ठगी के बाद", "risk"], tip_scan: ["Tip check", "टिप जाँच", "risk"],
  upi_check: ["UPI safety", "UPI सुरक्षा", "risk"], scheme_check: ["Offer check", "ऑफ़र जाँच", "risk"],
  stock_analysis: ["Company research", "कंपनी शोध", "stock"], stock_compare: ["Compare companies", "कंपनियों की तुलना", "stock"], stock_unknown: ["Company research", "कंपनी शोध", "stock"],
  feature_help: ["How it works", "यह कैसे काम करता है", "guide"], concept: ["Explained", "समझाया गया", "learn"], define: ["Meaning", "मतलब", "learn"],
  fee_drag: ["Fees", "फ़ीस", "calc"], emergency: ["Emergency cash", "इमरजेंसी पैसा", "calc"], goal: ["Goal check", "लक्ष्य जाँच", "calc"], panic: ["Crash replay", "गिरावट रिप्ले", "calc"],
  fund_overlap: ["Funds", "फ़ंड", "calc"], fund_list: ["Funds", "फ़ंड", "calc"], fund_info: ["Funds", "फ़ंड", "calc"], fund_vs_direct: ["Funds", "फ़ंड", "calc"],
  xray: ["Your portfolio", "आपका पोर्टफ़ोलियो", "own"], why: ["Your portfolio", "आपका पोर्टफ़ोलियो", "own"], fix: ["Your portfolio", "आपका पोर्टफ़ोलियो", "own"], stress: ["Stress test", "तनाव परीक्षण", "own"],
  diversification: ["Your portfolio", "आपका पोर्टफ़ोलियो", "own"], correlation: ["Your portfolio", "आपका पोर्टफ़ोलियो", "own"], portfolio_move: ["What moved", "क्या चला", "own"], should_buy: ["Fit with your portfolio", "आपके पोर्टफ़ोलियो में फ़िट", "own"],
  digest: ["Weekly digest", "साप्ताहिक सार", "own"], predict: ["Predictions", "भविष्यवाणी", "risk"], help: ["About me", "मेरे बारे में", "guide"], clarify: ["Need one more detail", "एक और जानकारी चाहिए", "guide"],
  moneylender: ["Loan cost", "क़र्ज़ की लागत", "calc"], credit_score: ["Credit score", "क्रेडिट स्कोर", "learn"], policy_check: ["Policy check", "पॉलिसी जाँच", "calc"],
};
const STEP_KINDS = new Set(["scam_help", "scam_recovery", "feature_help"]);
const CONF: Record<string, [string, string]> = { solid: ["Solid basis", "पक्का आधार"], light: ["Light basis", "हल्का आधार"], weak: ["Weak basis", "कमज़ोर आधार"] };

function ReadList({ items, hi, empty }: { items: ReadItem[]; hi: boolean; empty: string }) {
  const [all, setAll] = useState(false);
  if (!items.length) return <p className="ac-none">{empty}</p>;
  const shown = all ? items : items.slice(0, 3);
  return (
    <>
      <ul className="ac-read">
        {shown.map((x) => (
          <li key={x.title}>
            <div className="ac-read-top">{x.tag && <i className="sum-tag">{x.tag}</i>}{x.confidence && <i className={`sum-conf ${x.confidence}`} title={x.basis}>{CONF[x.confidence][hi ? 1 : 0]}</i>}</div>
            <b>{x.title}</b><span>{x.why}</span>
          </li>))}
      </ul>
      {items.length > 3 && <button className="ac-more" onClick={() => setAll(!all)}>{all ? (hi ? "कम दिखाइए" : "Show fewer") : (hi ? `सभी ${items.length} दिखाइए` : `Show all ${items.length}`)}</button>}
    </>
  );
}

/** One structured answer, laid out the same way every time: what kind it is, the short answer, the evidence (figures, chart, table),
 *  the steps, what to do next, how it was worked out, and tappable follow-ups. Used by the chat and by the Learn page. */
export function AnswerCard({ a, onAsk, compact = false }: {
  a: AnswerData; onAsk: (q: string, shown?: string) => void; compact?: boolean;
}) {
  const lang = useLang((s) => s.lang);
  const hi = lang === "hi";
  const [copied, setCopied] = useState(false);
  const [inline, setInline] = useState(false);
  const d = a.data ?? {};
  const canInline = ["fee_drag", "emergency", "goal", "panic", "digest", "scam_recovery"].includes(a.kind) && !!a.visual;
  const chips = a.follow_ups ?? [];
  const [kindEn, kindHi, tone] = KIND[a.kind] ?? ["Answer", "जवाब", "calc"];
  const steps = STEP_KINDS.has(a.kind);
  const long = a.headline.length > 150;

  const open = () => {
    if (!a.visual) return;
    const q = new URLSearchParams(Object.entries(a.visual.params ?? {}).map(([k, v]) => [k, String(v)])).toString();
    go(`/${a.visual.page}${q ? "?" + q : ""}`);
  };
  const copy = async () => {
    const text = [answerText(a), ...(a.table ? a.table.rows.map((r) => r.join(" | ")) : [])].join("\n");
    try { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch { /* clipboard blocked */ }
  };
  const runDesks = () => { if (d.investigate) { go("/research"); send(d.investigate, hi ? "विश्लेषक चलाइए" : "Run the analyst desks"); } };

  return (
    <article className={`ac ${tone} ${a.kind} ${compact ? "compact" : ""}`}>
      <header className="ac-top">
        <span className="ac-kind">{hi ? kindHi : kindEn}</span>
        {d.category && <span className="ac-cat">{d.category}</span>}
        {a.kind === "stock_analysis" && d.coverage && <span className="ac-cat">{hi ? `${d.coverage.of} में से ${d.coverage.ran} जाँचों के लिए डेटा` : `${d.coverage.ran} of ${d.coverage.of} checks had data`}</span>}
      </header>

      <p className={`ac-lead ${long ? "long" : ""}`}>{a.headline}</p>

      {!!a.facts?.length && (
        <div className="ac-facts">
          {a.facts.map((f, i) => (<div key={i} className={`ac-fact ${f.tone ?? ""}`}><b>{f.value}</b><span>{f.label}</span></div>))}
        </div>)}

      {d.chart && (d.chart.kind === "price" ? <PriceChart d={d.chart} /> : <CompareChart d={d.chart} />)}

      {!!d.sections?.length && (
        <div className="ac-cols">
          {d.sections.map((s) => (
            <section key={s.kind} className={`ac-col ${s.kind}`}>
              <h4>{s.kind === "good" ? "✓" : "⚠"} {s.title} <small>({s.items.length})</small></h4>
              <ReadList items={s.items} hi={hi} empty={s.kind === "good" ? (hi ? "हमारे पास के आँकड़ों में कुछ ख़ास अच्छा नहीं दिखता।" : "Nothing stands out as especially good in the numbers we hold.") : (hi ? "कोई चिंता की बात नहीं दिखती।" : "Nothing stands out as a concern in the numbers we hold.")} />
            </section>))}
        </div>)}

      {a.table && a.table.rows.length > 0 && (
        <div className="ac-table-wrap">
          <table className="ac-table">
            <thead><tr>{a.table.columns.map((c, i) => <th key={i}>{c}</th>)}</tr></thead>
            <tbody>{a.table.rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j} data-label={a.table!.columns[j]}>{c}</td>)}</tr>)}</tbody>
          </table>
        </div>)}

      {!!a.bullets?.length && !d.sections?.length && (
        steps
          ? <ol className="ac-steps">{a.bullets.map((b, i) => <li key={i}><span>{b.replace(/^\d+\.\s*/, "")}</span></li>)}</ol>
          : <ul className="ac-points">{a.bullets.map((b, i) => <li key={i}>{b}</li>)}</ul>)}
      {!!a.bullets?.length && !!d.sections?.length && a.kind === "stock_compare" && <ul className="ac-points">{a.bullets.map((b, i) => <li key={i}>{b}</li>)}</ul>}

      {a.action && <div className="ac-note"><Icon name="warn" size={15} /><span>{a.action}</span></div>}

      {canInline && inline && (a.kind === "fee_drag" ? <FeeDrag init={a.visual!.params} compact />
        : a.kind === "emergency" ? <EmergencyMeter init={a.visual!.params} compact />
        : a.kind === "scam_recovery" ? <RecoveryCoach init={a.visual!.params} compact />
        : a.kind === "digest" ? <WeeklyDigest compact autoPlay />
        : a.kind === "panic" ? <PanicSim init={a.visual!.params} compact />
        : <GoalFan init={a.visual!.params} compact />)}
      {a.kind === "scam_help" && a.visual && inline && <ScamCall init={a.visual.params} compact />}

      {a.detail && (
        <details className="ac-detail">
          <summary>{a.kind === "concept" && d.concept ? (hi ? "एक उदाहरण" : "A worked example") : (hi ? "यह कैसे निकाला गया" : "How this was worked out")}</summary>
          <p>{a.detail}</p>
        </details>)}

      <footer className="ac-tools">
        {d.tour && (
          <button className="ac-btn primary" onClick={() => startTour(d.tour!)}><Icon name="arrow" size={14} /> {d.tour_manual ? (hi ? "स्क्रीन पर दिखाइए" : "Show me on screen") : (hi ? "सैर दोबारा चलाइए" : "Replay the guided tour")}</button>)}
        {canInline && <button className="ac-btn primary" aria-expanded={inline} onClick={() => setInline((v) => !v)}>
          {inline ? (hi ? "बंद करें ▴" : "Hide it ▴") : a.kind === "scam_recovery" ? (hi ? "यहीं कोच खोलें" : "Open the coach here") : a.kind === "digest" ? (hi ? "यहीं सुनिए" : "Play it here") : (hi ? "यहीं आज़माइए ▾" : "Try it here ▾")}</button>}
        {a.kind === "scam_help" && a.visual && <button className="ac-btn primary" aria-expanded={inline} onClick={() => setInline((v) => !v)}>{inline ? (hi ? "बंद करें ▴" : "Hide it ▴") : (hi ? "यहीं अभ्यास करें" : "Rehearse it here")}</button>}
        {a.kind === "stock_analysis" && d.investigate && <button className="ac-btn primary" onClick={runDesks}>{hi ? "विश्लेषक डेस्क चलाइए" : "Run the analyst desks"}</button>}
        {a.visual && !d.tour && <button className={`ac-btn ${canInline || a.kind === "stock_analysis" ? "" : "primary"}`} onClick={open}>{canInline ? (hi ? "पूरे पेज पर खोलें" : "Open full page") : a.visual.label} <Icon name="arrow" size={13} /></button>}
        <span className="ac-spacer" />
        <button className="ac-btn ghost" onClick={() => speak(answerText(a), a.lang === "hi" ? "hi" : "en", true)} title={hi ? "ज़ोर से पढ़ें" : "Read this aloud"}><Icon name="speaker" size={14} /> {hi ? "सुनें" : "Listen"}</button>
        <button className="ac-btn ghost" onClick={() => stopSpeech()} aria-label={hi ? "आवाज़ रोकें" : "Stop the voice"}>■</button>
        <button className="ac-btn ghost" onClick={copy}>{copied ? (hi ? "कॉपी हुआ ✓" : "Copied ✓") : (hi ? "कॉपी" : "Copy")}</button>
      </footer>

      {chips.length > 0 && (
        <div className="ac-chips" aria-label={hi ? "आगे पूछिए" : "Ask next"}>
          {chips.map((q, i) => (<button key={q} className="ac-chip" onClick={() => onAsk(q, (hi && a.follow_ups_hi?.[i]) || undefined)}>{(hi && a.follow_ups_hi?.[i]) || q}</button>))}
        </div>)}
    </article>
  );
}
