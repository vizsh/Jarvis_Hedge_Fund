import { useEffect, useMemo, useRef, useState } from "react";

import "../styles-recovery.css";
import { useT } from "../lib/i18n";
import { useLang } from "../lib/lang";
import { allowSpeech, speak } from "../lib/speak";

type Step = { id: string; n: number; title: string; detail: string; mins: number };
type Plan = { type: string; label: string; steps: Step[] };

const WHEN: [string, string, number][] = [
  ["Just now", "अभी-अभी", 0], ["About an hour ago", "लगभग एक घंटा पहले", 60],
  ["Earlier today", "आज पहले", 360], ["A few days ago", "कुछ दिन पहले", 4000],
];

const key = (type: string) => `jarvis.recovery.${type}`;
const load = (type: string): string[] => { try { return JSON.parse(localStorage.getItem(key(type)) || "[]"); } catch { return []; } };
const save = (type: string, done: string[]) => { try { localStorage.setItem(key(type), JSON.stringify(done)); } catch { /* storage blocked */ } };

function whenLabel(mins: number, hi: boolean): string {
  if (mins <= 0) return hi ? "अभी" : "now";
  if (mins < 60) return hi ? `${mins} मिनट में` : `within ${mins} min`;
  if (mins === 60) return hi ? "1 घंटे में" : "within 1 hour";
  if (mins <= 1440) return hi ? "24 घंटे में" : "within 24 hours";
  if (mins <= 4320) return hi ? "3 कामकाजी दिनों में" : "within 3 working days";
  return hi ? "अगले 30 दिन" : "next 30 days";
}

/** The first-hour plan after a scam: what happened -> ordered steps with a clock -> ready-to-send drafts. */
export function RecoveryCoach({ init, compact = false }: { init?: Record<string, string | number>; compact?: boolean }) {
  const { hi, t } = useT();
  const lang = useLang((s) => s.lang);
  const [types, setTypes] = useState<{ id: string; label: string }[]>([]);
  const [kind, setKind] = useState<string | null>((init?.type as string) || null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [offset, setOffset] = useState(0);                      // minutes already gone when they started
  const [t0] = useState(() => Date.now());
  const [now, setNow] = useState(Date.now());
  const [done, setDone] = useState<string[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const [form, setForm] = useState({ amount: init?.amount ? String(init.amount) : "", when: "", txn_id: "", fraud_contact: "", bank: "", name: "" });
  const [drafts, setDrafts] = useState<{ script: string; portal: string; letter: string } | null>(null);
  const [copied, setCopied] = useState("");
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => { fetch(`/recovery/types?lang=${lang}`).then((r) => r.json()).then((x) => setTypes(x.types)).catch(() => {}); }, [lang]);
  useEffect(() => {
    if (!kind) return;
    fetch(`/recovery/plan?type=${kind}&lang=${lang}`).then((r) => r.json()).then(setPlan).catch(() => {});
    setDone(load(kind));
  }, [kind, lang]);
  useEffect(() => { const i = window.setInterval(() => setNow(Date.now()), 15000); return () => window.clearInterval(i); }, []);
  useEffect(() => {
    if (!kind) return;
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      fetch("/recovery/draft", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: kind, lang, amount: form.amount ? Number(form.amount) : null, when: form.when,
                               txn_id: form.txn_id, fraud_contact: form.fraud_contact, bank: form.bank, name: form.name }) })
        .then((r) => r.json()).then(setDrafts).catch(() => {});
    }, 250);
    return () => window.clearTimeout(timer.current);
  }, [kind, lang, form]);

  const elapsed = offset + Math.floor((now - t0) / 60000);        // minutes since the scam
  const left = Math.max(0, 60 - elapsed);
  const toggle = (id: string) => {
    if (!kind) return;
    const next = done.includes(id) ? done.filter((x) => x !== id) : [...done, id];
    setDone(next); save(kind, next);
  };
  const copy = async (which: string, text: string) => {
    try { await navigator.clipboard.writeText(text); setCopied(which); setTimeout(() => setCopied(""), 1500); } catch { /* clipboard blocked */ }
  };
  const progress = useMemo(() => (plan ? Math.round((done.filter((d) => plan.steps.some((s) => s.id === d)).length / plan.steps.length) * 100) : 0), [done, plan]);
  const reset = () => { if (kind) save(kind, []); setDone([]); };

  return (
    <section className={compact ? "fd-inline" : "card wide rcv"}>
      {!compact && <h2>{t("Scam recovery coach", "ठगी के बाद का कोच")}</h2>}
      {!compact && <p className="muted">{t("If you think you have been scammed: do these things in this order. The first hour matters most, and none of this is your fault.",
        "अगर आपको लगता है कि आप ठगी का शिकार हुए: ये काम इसी क्रम में कीजिए। पहला घंटा सबसे अहम है, और इसमें आपकी कोई ग़लती नहीं है।")}</p>}

      {!kind && (
        <div className="rcv-pick">
          <div className="rcv-q">{t("What happened?", "क्या हुआ?")}</div>
          {types.map((x) => <button key={x.id} className="rcv-type" onClick={() => setKind(x.id)}>{x.label}</button>)}
        </div>)}

      {kind && plan && (
        <>
          <div className="rcv-top">
            <div className={`rcv-clock ${left === 0 ? "late" : ""}`}>
              <span className="rcv-clock-n">{left > 0 ? `${left}` : "0"}</span>
              <span className="rcv-clock-l">{left > 0 ? t("min left in the first hour", "मिनट बचे पहले घंटे में") : t("first hour passed: still do every step", "पहला घंटा बीत गया: फिर भी हर क़दम कीजिए")}</span>
            </div>
            <div className="rcv-side">
              <div className="small muted">{t("When did it happen?", "यह कब हुआ?")}</div>
              <div className="chips">
                {WHEN.map(([en, h, m]) => (
                  <button key={en} className={`abtn ${offset === m ? "primary" : ""}`} onClick={() => setOffset(m)}>{hi ? h : en}</button>))}
              </div>
              <div className="rcv-bar" aria-label={`${progress}%`}><div style={{ width: `${progress}%` }} /></div>
              <div className="tiny muted">{t(`${progress}% of steps done`, `${progress}% क़दम पूरे`)} · <button className="linklike" onClick={() => setKind(null)}>{t("change situation", "स्थिति बदलिए")}</button> · <button className="linklike" onClick={reset}>{t("reset", "रीसेट")}</button></div>
            </div>
          </div>

          <div className="rcv-call">
            <a className="btn go" href="tel:1930">☎ {t("Call 1930", "1930 पर फ़ोन करें")}</a>
            <a className="btn ghost" href="https://cybercrime.gov.in" target="_blank" rel="noreferrer">cybercrime.gov.in ↗</a>
            <span className="tiny muted">{t("Use your bank's number from your card or its website, not one the caller gave.", "बैंक का नंबर कार्ड या उसकी वेबसाइट से लीजिए, ठग के दिए नंबर से नहीं।")}</span>
          </div>

          <ol className="rcv-steps">
            {plan.steps.map((s) => {
              const isDone = done.includes(s.id);
              const urgent = !isDone && s.mins > 0 && elapsed < s.mins && s.mins <= 60;
              return (
                <li key={s.id} className={`rcv-step ${isDone ? "done" : ""} ${urgent ? "urgent" : ""}`}>
                  <label className="rcv-check">
                    <input type="checkbox" checked={isDone} onChange={() => toggle(s.id)} />
                    <span className="rcv-n">{s.n}</span>
                  </label>
                  <div className="rcv-body">
                    <button className="rcv-title" onClick={() => setOpen(open === s.id ? null : s.id)} aria-expanded={open === s.id}>
                      {s.title}
                      <span className={`rcv-due ${urgent ? "hot" : ""}`}>{whenLabel(s.mins, hi)}</span>
                    </button>
                    {(open === s.id || urgent) && (
                      <div className="rcv-detail">
                        <p>{s.detail}</p>
                        <button className="abtn" onClick={() => { allowSpeech(); speak(`${s.title}. ${s.detail}`, lang, true); }}>🔊 {t("Read aloud", "सुनें")}</button>
                      </div>)}
                  </div>
                </li>);
            })}
          </ol>

          <details className="rcv-drafts" open={!compact}>
            <summary>{t("Ready-to-send drafts (fill in what you know)", "भेजने लायक़ मसौदे (जो पता है वह भरिए)")}</summary>
            <div className="rcv-form">
              {([["amount", "Amount lost (₹)", "खोई रक़म (₹)"], ["when", "Date and time", "तारीख़ और समय"], ["txn_id", "Transaction ID / UTR", "ट्रांज़ैक्शन आईडी / UTR"],
                 ["fraud_contact", "Fraudster's phone / UPI ID / account", "ठग का फ़ोन / UPI आईडी / खाता"], ["bank", "Your bank", "आपका बैंक"], ["name", "Your name", "आपका नाम"]] as [string, string, string][]).map(([k, en, h]) => (
                <input key={k} className="field" placeholder={hi ? h : en} value={(form as any)[k]} inputMode={k === "amount" ? "numeric" : undefined}
                       onChange={(e) => setForm({ ...form, [k]: e.target.value })} />))}
            </div>
            {drafts && (
              <div className="rcv-texts">
                {([["script", "30-second phone script for the helpline or bank", "हेल्पलाइन या बैंक के लिए 30 सेकंड की बात"],
                   ["portal", "Text for cybercrime.gov.in", "cybercrime.gov.in के लिए पाठ"],
                   ["letter", "Letter to your bank", "बैंक को पत्र"]] as [keyof typeof drafts, string, string][]).map(([k, en, h]) => (
                  <div className="rcv-text" key={k}>
                    <div className="rcv-text-head"><b>{hi ? h : en}</b>
                      <button className="abtn" onClick={() => copy(k, drafts[k])}>{copied === k ? t("Copied ✓", "कॉपी हुआ ✓") : t("Copy", "कॉपी")}</button></div>
                    <pre>{drafts[k]}</pre>
                  </div>))}
                <p className="tiny muted">{t("Nothing is sent from here: copy these into your phone call, the portal or an email. Gaps in [brackets] are things you have not filled in.",
                  "यहाँ से कुछ नहीं भेजा जाता: इन्हें फ़ोन कॉल, पोर्टल या ईमेल में कॉपी कीजिए। [कोष्ठक] की ख़ाली जगहें वे हैं जो आपने नहीं भरीं।")}</p>
              </div>)}
          </details>
        </>)}
    </section>
  );
}
