import { useEffect, useMemo, useRef, useState } from "react";

import "../styles-rural.css";
import "../styles-kiosk.css";
import { Page } from "./Page";
import { hashParams } from "../lib/router";
import { useT } from "../lib/i18n";
import { useLang } from "../lib/lang";
import { speak } from "../lib/speak";
import { usePilot } from "../lib/pilot";
import { pstore } from "../lib/pstore";
import { ruralFetch } from "../lib/offline";
import { useKiosk } from "../lib/kiosk";
import { OfflineBar } from "../components/OfflineBar";

/** While the guide is still asking for something, the page shows what it has so far and holds the result back. */
function Waiting({ tool }: { tool: string }) {
  const g = usePilot((s) => s.guide);
  if (!g?.ask || g.tool !== tool) return null;
  return <div className="rural-wait">🎙 {g.ask.question}</div>;
}
const useWaiting = (tool: string) => { const g = usePilot((s) => s.guide); return !!g?.ask && g.tool === tool; };
const fromJSON = <T,>(v: string | undefined, d: T): T => { try { return v ? JSON.parse(v) : d; } catch { return d; } };

type Tool = "loan" | "scheme" | "schemes" | "docs" | "income" | "policy" | "upi" | "dbt" | "hold" | "saving" | "shg" | "credit";

const store = {
  get<T>(k: string, d: T): T { return pstore.get("rural.", k, d); },
  set(k: string, v: unknown) { pstore.set("rural.", k, v); },
};

function usePost<T>(url: string, body: unknown, enabled = true, delay = 250): T | null {
  const [out, setOut] = useState<T | null>(null);
  const key = JSON.stringify(body);
  useEffect(() => {
    if (!enabled) { setOut(null); return; }
    const id = window.setTimeout(() => {
      ruralFetch(url, JSON.parse(key)).then(setOut).catch(() => {});
    }, delay);
    return () => window.clearTimeout(id);
  }, [url, key, enabled, delay]);
  return out;
}

const inr = (v: number) => "₹" + Math.round(v).toLocaleString("en-IN");
const Say = ({ text }: { text: string }) => {
  const { t } = useT(); const lang = useLang((s) => s.lang);
  return <button className="btn ghost sm" onClick={() => speak(text, lang === "hi" ? "hi" : "en", true)}>🔊 {t("Read aloud", "सुनें")}</button>;
};

/* ------------------------------------------------------------------ A1 loan */
type Loan = { yearly_pct: number; interest: number; total: number; band: string; headline: string; verdict: string; legal: string;
  double_months: number | null; alternatives: { id: string; name: string; yearly_pct: number; interest: number; saves: number; note: string }[] };

function LoanTool({ init }: { init: Record<string, string> }) {
  const { t } = useT(); const lang = useLang((s) => s.lang);
  const guided = init.tool === "loan";
  const waiting = useWaiting("loan");
  const [f, setF] = useState(() => guided
    ? { principal: init.principal ? String(Number(init.principal)) : "", rate: init.rate ?? "", unit: init.unit ?? "per100_month", months: init.months ?? "", mode: "interest_only" }
    : store.get("loan", { principal: "50000", rate: "5", unit: "per100_month", months: "10", mode: "interest_only" }));
  useEffect(() => { if (!guided) store.set("loan", f); }, [f, guided]);
  const ok = !waiting && Number(f.principal) > 0 && Number(f.rate) > 0 && Number(f.months) > 0;
  const r = usePost<Loan>("/rural/loan", { principal: Number(f.principal), rate: Number(f.rate), unit: f.unit, months: Number(f.months), mode: f.mode, lang }, ok);
  const set = (k: string) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  return (
    <section className="card wide rural-card" data-date={new Date().toLocaleDateString()}>
      <h2>{t("What does the moneylender's interest really cost?", "साहूकार का ब्याज असल में कितना पड़ता है?")}</h2>
      <Waiting tool="loan" />
      <p className="muted">{t("Enter what you were told. I turn it into a yearly rate and rupees, and show what a bank or group would charge.", "जो आपको बताया गया वह भरिए। मैं उसे साल की दर और रुपयों में बदलूँगा, और बैंक या समूह की दर से तुलना दिखाऊँगा।")}</p>
      <div className="rural-form">
        <label>{t("Money borrowed (₹)", "उधार ली रक़म (₹)")}<input inputMode="numeric" value={f.principal} onChange={set("principal")} /></label>
        <label>{t("Interest told to you", "बताया गया ब्याज")}
          <span className="inline"><input inputMode="decimal" value={f.rate} onChange={set("rate")} />
            <select value={f.unit} onChange={set("unit")}>
              <option value="per100_month">{t("₹ per ₹100 a month (saikda)", "₹ सैकड़ा, महीना")}</option>
              <option value="pct_month">{t("% a month", "% महीना")}</option>
              <option value="pct_year">{t("% a year", "% साल")}</option>
              <option value="rs_per_month">{t("₹ a month on the whole loan", "₹ महीना, पूरे ऋण पर")}</option>
            </select></span></label>
        <label>{t("For how many months", "कितने महीने के लिए")}<input inputMode="numeric" value={f.months} onChange={set("months")} /></label>
        <label>{t("How it is paid", "भुगतान कैसे होता है")}
          <select value={f.mode} onChange={set("mode")}>
            <option value="interest_only">{t("Interest every month, loan back at the end", "हर महीने ब्याज, अंत में मूल")}</option>
            <option value="bullet_simple">{t("Everything at the end", "सब कुछ अंत में")}</option>
            <option value="bullet_compound">{t("Unpaid interest is added to the loan (byaj pe byaj)", "बिना चुकाया ब्याज मूल में जुड़ता है (ब्याज पर ब्याज)")}</option>
          </select></label>
      </div>
      {r && (<>
        <div className={`rural-big ${r.band}`}><span>{Math.round(r.yearly_pct)}%</span><small>{t("a year", "साल में")}</small></div>
        <p className="rural-head">{r.headline} {r.verdict}</p>
        <div className="rural-facts">
          <div><small>{t("Interest you pay", "आप ब्याज देंगे")}</small><b>{inr(r.interest)}</b></div>
          <div><small>{t("You repay in all", "कुल चुकाएँगे")}</small><b>{inr(r.total)}</b></div>
          {r.double_months && <div><small>{t("Debt doubles in about", "क़र्ज़ दोगुना लगभग")}</small><b>{Math.round(r.double_months)} {t("months", "महीने में")}</b></div>}
        </div>
        <table className="rural-table"><thead><tr><th>{t("Where from", "कहाँ से")}</th><th>{t("Per year", "साल में")}</th><th>{t("Interest", "ब्याज")}</th><th>{t("You save", "आपकी बचत")}</th></tr></thead>
          <tbody>
            <tr className="bad"><td>{t("This lender", "यह साहूकार")}</td><td>{Math.round(r.yearly_pct)}%</td><td>{inr(r.interest)}</td><td>–</td></tr>
            {r.alternatives.map((a) => <tr key={a.id}><td>{a.name}<small>{a.note}</small></td><td>~{a.yearly_pct}%</td><td>{inr(a.interest)}</td><td className="good">{inr(a.saves)}</td></tr>)}
          </tbody></table>
        <p className="rural-note">{r.legal}</p>
        <Say text={`${r.headline} ${r.verdict}`} />
      </>)}
    </section>
  );
}

/* ------------------------------------------------------------------ A2 offer checker */
type Offer = { score: number; level: string; verdict: string; rule: string; implied_yearly_pct: number | null;
  flags: { id: string; text: string }[]; verify: string[]; compare: { name: string; yearly_pct: number }[] };

function SchemeTool({ init }: { init: Record<string, string> }) {
  const { t } = useT(); const lang = useLang((s) => s.lang);
  const [text, setText] = useState(init.tool === "scheme" ? init.text ?? "" : "");
  const [n, setN] = useState({ put: "", get: "", months: "" });
  const [go, setGo] = useState(init.tool === "scheme" && !!init.text && !!init.run);
  const body = { text, put: n.put ? Number(n.put) : null, get: n.get ? Number(n.get) : null, months: n.months ? Number(n.months) : null, lang };
  const r = usePost<Offer>("/rural/scheme", body, go && (!!text.trim() || !!(n.put && n.get && n.months)), 0);
  const EX: [string, string, string][] = [
    ["Pay ₹10,000 now, get ₹20,000 in 6 months, guaranteed. Bring 3 friends and earn more. Only today!", "आज ही ₹10,000 लगाइए, 6 महीने में ₹20,000 पक्का। 3 दोस्तों को जोड़ें, और कमाएँ।", "A typical double-money offer"],
    ["Bank says our recurring deposit pays 6.8% a year, passbook and receipt provided.", "बैंक की आवर्ती जमा साल का 6.8% देती है, पासबुक और रसीद मिलेगी।", "An ordinary bank offer"],
  ];
  return (
    <section className="card wide rural-card" data-date={new Date().toLocaleDateString()}>
      <h2>{t("Is this scheme or offer real?", "क्या यह योजना या ऑफ़र असली है?")}</h2>
      <Waiting tool="scheme" />
      <p className="muted">{t("Write what they promised you, in your own words. I check it against the signs every fraud scheme shares.", "उन्होंने जो वादा किया वह अपने शब्दों में लिखिए। मैं उसे उन संकेतों से मिलाता हूँ जो हर ठगी योजना में एक जैसे होते हैं।")}</p>
      <textarea rows={4} value={text} onChange={(e) => { setText(e.target.value); setGo(false); }}
                placeholder={t("e.g. A man in our village says pay ₹10,000 and get ₹20,000 in 6 months...", "जैसे: गाँव में एक आदमी कहता है ₹10,000 दो और 6 महीने में ₹20,000 पाओ...")} />
      <div className="rural-form three">
        <label>{t("You pay (₹)", "आप देंगे (₹)")}<input inputMode="numeric" value={n.put} onChange={(e) => { setN({ ...n, put: e.target.value }); setGo(false); }} /></label>
        <label>{t("You get back (₹)", "आपको मिलेगा (₹)")}<input inputMode="numeric" value={n.get} onChange={(e) => { setN({ ...n, get: e.target.value }); setGo(false); }} /></label>
        <label>{t("After (months)", "कितने महीने बाद")}<input inputMode="numeric" value={n.months} onChange={(e) => { setN({ ...n, months: e.target.value }); setGo(false); }} /></label>
      </div>
      <div className="rural-actions">
        <button className="btn go" onClick={() => setGo(true)}>{t("Check it", "जाँचिए")}</button>
        {EX.map(([en, hi, lab]) => <button key={lab} className="btn ghost sm" onClick={() => { setText(lang === "hi" ? hi : en); setGo(true); }}>{t(lab, lab === "An ordinary bank offer" ? "एक सामान्य बैंक ऑफ़र" : "दोगुना पैसे वाला आम ऑफ़र")}</button>)}
      </div>
      {r && go && (<>
        <div className={`rural-big ${r.level}`}><span>{r.score}</span><small>/100 {t("risk", "जोखिम")}</small></div>
        <p className="rural-head">{r.verdict}</p>
        {r.implied_yearly_pct !== null && <p>{t(`What they promise works out to ${Math.round(r.implied_yearly_pct)}% a year.`, `उनका वादा साल के ${Math.round(r.implied_yearly_pct)}% के बराबर है।`)} {t("A bank deposit pays about 7%.", "बैंक जमा लगभग 7% देती है।")}</p>}
        {r.flags.length > 0 && <ul className="rural-flags">{r.flags.map((f) => <li key={f.id}>{f.text}</li>)}</ul>}
        <div className="rural-rule">{r.rule}</div>
        <h3>{t("Check it yourself", "ख़ुद जाँचिए")}</h3>
        <ul className="rural-links">{r.verify.map((v) => <li key={v}>{v}</li>)}</ul>
        <Say text={`${r.verdict} ${r.rule}`} />
      </>)}
    </section>
  );
}

/* ------------------------------------------------------------------ E3 credit score */
type Cred = { profile: string; band: string; headline: string; reasons: { kind: string; title: string; steps: string[] }[]; facts: string[]; scams: string[];
  bureaus: { name: string; site: string }[]; report_note: string; note: string;
  emi: { headline: string; emi_good: number; emi_poor: number; saved: number }; letters: { lender: string; bureau: string } };

function CreditTool({ init }: { init: Record<string, string> }) {
  const { t } = useT(); const lang = useLang((s) => s.lang);
  const guided = init.tool === "credit";
  const waiting = useWaiting("credit");
  const [f, setF] = useState(() => ({ has_credit: "none", missed: "never", serious: "none", utilization: "na", enquiries: "0-1", age: "na",
    ...(guided ? Object.fromEntries(["has_credit", "missed", "serious", "utilization", "enquiries", "age"].filter((k) => init[k]).map((k) => [k, init[k]])) : {}) }));
  const [loan, setLoan] = useState({ amount: "100000", years: "3", good: "11", poor: "16" });
  const [who, setWho] = useState({ name: "", lender: "", wrong: "" });
  const [copied, setCopied] = useState("");
  const [go, setGo] = useState(guided && !!init.run);
  const set = (k: string) => (e: { target: { value: string } }) => { setF({ ...f, [k]: e.target.value }); setGo(true); };
  const informal = f.has_credit === "informal";
  const r = usePost<Cred>("/rural/credit", { ...f, has_credit: informal ? "none" : f.has_credit, informal_only: informal, ...who, amount: Number(loan.amount) || 100000, years: Number(loan.years) || 3,
    good_rate: Number(loan.good) || 11, poor_rate: Number(loan.poor) || 16, lang }, go && !waiting, 200);
  const copy = async (k: string, s: string) => { try { await navigator.clipboard.writeText(s); setCopied(k); setTimeout(() => setCopied(""), 1500); } catch { /* clipboard blocked */ } };
  const opt = (rows: [string, string, string][]) => rows.map(([v, en, hi]) => <option key={v} value={v}>{t(en, hi)}</option>);
  return (
    <section className="card wide rural-card" data-date={new Date().toLocaleDateString()}>
      <h2>{t("Credit score: what it is and how to build one", "क्रेडिट स्कोर: यह क्या है और कैसे बनाएँ")}</h2>
      <Waiting tool="credit" />
      <p className="muted">{t("I cannot see your actual score (only the credit bureaus can). Tell me about your borrowing and I will say what is likely helping or hurting you, and exactly what to do.", "मैं आपका असली स्कोर नहीं देख सकता (वह सिर्फ़ क्रेडिट ब्यूरो के पास है)। अपने उधार के बारे में बताइए, मैं बताऊँगा क्या फ़ायदा या नुक़सान कर रहा है, और ठीक क्या करना है।")}</p>
      <div className="rural-form">
        <label>{t("Your borrowing so far", "अब तक का आपका उधार")}<select value={f.has_credit} onChange={set("has_credit")}>{opt([["none", "No loan or card", "कोई ऋण या कार्ड नहीं"], ["informal", "Only from a moneylender or chit fund", "सिर्फ़ साहूकार या चिट फंड से"], ["loan", "A bank or other formal loan", "बैंक या औपचारिक ऋण"], ["card", "A credit card", "क्रेडिट कार्ड"], ["both", "Both a loan and a card", "ऋण और कार्ड दोनों"]])}</select></label>
        {f.has_credit !== "none" && f.has_credit !== "informal" && (<>
          <label>{t("Late instalments", "देर से किस्त")}<select value={f.missed} onChange={set("missed")}>{opt([["never", "Never", "कभी नहीं"], ["once", "Once or twice", "एक-दो बार"], ["often", "Often", "अक्सर"]])}</select></label>
          <label>{t("Settled / written off / unpaid loan", "सेटल / राइट-ऑफ़ / न चुकाया ऋण")}<select value={f.serious} onChange={set("serious")}>{opt([["none", "None", "कोई नहीं"], ["settled", "Settled or written off", "सेटल या राइट-ऑफ़"], ["default", "Unpaid and still pending", "न चुकाया, अब भी बाक़ी"]])}</select></label>
          <label>{t("Share of card limit you use", "कार्ड सीमा का इस्तेमाल")}<select value={f.utilization} onChange={set("utilization")}>{opt([["na", "No card", "कार्ड नहीं"], ["low", "Under 30%", "30% से कम"], ["mid", "30% to 70%", "30% से 70%"], ["high", "Over 70%", "70% से ज़्यादा"]])}</select></label>
          <label>{t("Applications in the last 6 months", "पिछले 6 महीनों में आवेदन")}<select value={f.enquiries} onChange={set("enquiries")}>{opt([["0-1", "0 or 1", "0 या 1"], ["2-3", "2 or 3", "2 या 3"], ["4+", "4 or more", "4 या ज़्यादा"]])}</select></label>
          <label>{t("Oldest loan or card", "सबसे पुराना ऋण या कार्ड")}<select value={f.age} onChange={set("age")}>{opt([["<6m", "Under 6 months", "6 महीने से कम"], ["6m-2y", "6 months to 2 years", "6 महीने से 2 साल"], [">2y", "Over 2 years", "2 साल से ज़्यादा"]])}</select></label>
        </>)}
      </div>
      <div className="rural-actions"><button className="btn go" onClick={() => setGo(true)}>{t("Read my situation", "मेरी स्थिति पढ़िए")}</button></div>
      {r && go && (<>
        <div className={`rural-big ${r.band}`}><span style={{ fontSize: 24 }}>{r.headline}</span></div>
        {r.reasons.map((x, i) => (<div key={i} className={`rural-rule ${x.kind === "bad" ? "bad" : ""}`}><b>{x.title}</b><ul className="rural-flags good">{x.steps.map((s) => <li key={s}>{s}</li>)}</ul></div>))}
        <h3>{t("What a good record saves you", "अच्छा रिकॉर्ड कितना बचाता है")}</h3>
        <div className="rural-form three">
          <label>{t("Loan (₹)", "ऋण (₹)")}<input inputMode="numeric" value={loan.amount} onChange={(e) => setLoan({ ...loan, amount: e.target.value })} /></label>
          <label>{t("Years", "साल")}<input inputMode="decimal" value={loan.years} onChange={(e) => setLoan({ ...loan, years: e.target.value })} /></label>
          <label>{t("Rate with a good record (%)", "अच्छे रिकॉर्ड पर दर (%)")}<input inputMode="decimal" value={loan.good} onChange={(e) => setLoan({ ...loan, good: e.target.value })} /></label>
          <label>{t("Rate with a poor record (%)", "ख़राब रिकॉर्ड पर दर (%)")}<input inputMode="decimal" value={loan.poor} onChange={(e) => setLoan({ ...loan, poor: e.target.value })} /></label>
        </div>
        <p className="rural-head">{r.emi.headline} ({t("monthly instalment", "मासिक किस्त")} ₹{r.emi.emi_good.toLocaleString("en-IN")} {t("vs", "बनाम")} ₹{r.emi.emi_poor.toLocaleString("en-IN")})</p>
        <h3>{t("How a score works", "स्कोर कैसे काम करता है")}</h3>
        <ul className="rural-flags good">{r.facts.map((x) => <li key={x}>{x}</li>)}</ul>
        <h3>{t("Watch out for", "इनसे सावधान")}</h3>
        <ul className="rural-flags">{r.scams.map((x) => <li key={x}>{x}</li>)}</ul>
        <h3>{t("Your free report", "आपकी मुफ़्त रिपोर्ट")}</h3>
        <p className="rural-note">{r.report_note} {r.bureaus.map((b) => `${b.name} (${b.site})`).join(" · ")}</p>
        <details className="rural-letter"><summary>{t("Something on your report is wrong? Letters to fix it", "रिपोर्ट में कुछ गलत है? सुधार की चिट्ठियाँ")}</summary>
          <div className="rural-form three">
            <label>{t("Your name", "आपका नाम")}<input value={who.name} onChange={(e) => setWho({ ...who, name: e.target.value })} /></label>
            <label>{t("Lender", "ऋणदाता")}<input value={who.lender} onChange={(e) => setWho({ ...who, lender: e.target.value })} /></label>
            <label>{t("What is wrong", "क्या गलत है")}<input value={who.wrong} onChange={(e) => setWho({ ...who, wrong: e.target.value })} placeholder={t("e.g. shows overdue but I paid in May", "जैसे: बकाया दिखा रहा है पर मई में चुका दिया")} /></label>
          </div>
          {(["lender", "bureau"] as const).map((k) => (<div key={k}><pre>{r.letters[k]}</pre><button className="btn ghost sm" onClick={() => void copy(k, r.letters[k])}>{copied === k ? t("Copied ✓", "कॉपी हुआ ✓") : (k === "lender" ? t("Copy letter to the lender", "ऋणदाता की चिट्ठी कॉपी") : t("Copy letter to the bureau", "ब्यूरो की चिट्ठी कॉपी"))}</button></div>))}
        </details>
        <p className="rural-note">{r.note}</p>
        <Say text={r.headline} />
      </>)}
    </section>
  );
}

/* ------------------------------------------------------------------ E2 self-help group ledger */
type ShgMember = { id: string; name: string };
type ShgEntry = { date: string; member: string; type: string; amount: number; note?: string };
type ShgLedger = { group: string; rate: number; loan_multiple: number; members: ShgMember[]; entries: ShgEntry[] };
type ShgRow = { id: string; name: string; savings: number; loans_taken: number; outstanding: number; interest_due: number; interest_paid: number; fines: number; total_due: number;
  loan_multiple: number | null; missed_months: number; overdue: boolean; status: string; year_end_share: number };
type ShgSum = { group: string; as_of: string; members: ShgRow[]; alerts: string[]; report: string; statements: Record<string, string>; method: string;
  totals: { members: number; savings: number; loans_out: number; interest_income: number; fines: number; cash: number; lent_total: number } };
type Lend = { ok: boolean; headline: string; checks: { id: string; ok: boolean; text: string }[] };
const EMPTY_LEDGER: ShgLedger = { group: "", rate: 1.5, loan_multiple: 3, members: [], entries: [] };
const today = () => new Date().toISOString().slice(0, 10);
const TYPES: [string, string, string][] = [["saving", "Savings", "बचत"], ["loan", "Loan given", "ऋण दिया"], ["repay", "Repayment", "किस्त वापस"], ["fine", "Fine", "जुर्माना"], ["withdraw", "Savings withdrawn", "बचत निकाली"]];

function ShgTool() {
  const { t, hi } = useT(); const lang = useLang((s) => s.lang);
  const kiosk = useKiosk((s) => s.on);
  const [led, setLed] = useState<ShgLedger>(() => pstore.get("shg.", "ledger", EMPTY_LEDGER));
  // own namespace: turning shared-device mode on must never delete a group's books from the leader's device
  useEffect(() => pstore.set("shg.", "ledger", led), [led]);
  const [asOf, setAsOf] = useState(today());
  const [form, setForm] = useState({ date: today(), member: "", type: "saving", amount: "", note: "" });
  const [newName, setNewName] = useState("");
  const [all, setAll] = useState("");
  const [who, setWho] = useState("");
  const [lend, setLend] = useState({ member: "", amount: "" });
  const [copied, setCopied] = useState("");
  const s = usePost<ShgSum>("/rural/shg", { ledger: led, as_of: asOf, lang }, led.members.length > 0, 150);
  const lendRes = usePost<Lend>("/rural/shg/lend", { ledger: led, member: lend.member, amount: Number(lend.amount), as_of: asOf, lang }, !!lend.member && Number(lend.amount) > 0, 200);
  const memberId = form.member || led.members[0]?.id || "";
  const addMember = () => { const nm = newName.trim(); if (!nm) return; setLed({ ...led, members: [...led.members, { id: "m" + Date.now().toString(36) + led.members.length, name: nm }] }); setNewName(""); };
  const addEntry = () => { const a = Number(form.amount); if (!memberId || !(a > 0)) return; setLed({ ...led, entries: [...led.entries, { date: form.date, member: memberId, type: form.type, amount: a, note: form.note }] }); setForm({ ...form, amount: "", note: "" }); };
  const collectAll = () => { const a = Number(all); if (!(a > 0) || !led.members.length) return; setLed({ ...led, entries: [...led.entries, ...led.members.map((m) => ({ date: form.date, member: m.id, type: "saving", amount: a, note: "" }))] }); setAll(""); };
  const copy = async (k: string, text: string) => { try { await navigator.clipboard.writeText(text); setCopied(k); setTimeout(() => setCopied(""), 1500); } catch { /* clipboard blocked */ } };
  const download = (name: string, text: string, type: string) => { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([text], { type })); a.download = name; a.click(); URL.revokeObjectURL(a.href); };
  const csv = () => ["date,member,type,amount,note", ...led.entries.map((e) => [e.date, led.members.find((m) => m.id === e.member)?.name ?? e.member, e.type, e.amount, (e.note ?? "").replace(/,/g, " ")].join(","))].join("\n");
  const importFile = async (f: File | undefined) => { if (!f) return; try { const j = JSON.parse(await f.text()); if (Array.isArray(j.members) && Array.isArray(j.entries)) setLed({ ...EMPTY_LEDGER, ...j }); } catch { /* not a ledger file */ } };
  const nameOf = (id: string) => led.members.find((m) => m.id === id)?.name ?? id;
  const typeLabel = (k: string) => { const r = TYPES.find((x) => x[0] === k); return r ? (hi ? r[2] : r[1]) : k; };
  const rs = (v: number) => "₹" + Math.round(v).toLocaleString("en-IN");
  return (
    <section className="card wide rural-card" data-date={new Date().toLocaleDateString()}>
      <h2>{t("Self-help group ledger", "स्वयं सहायता समूह की बही")}</h2>
      <p className="muted">{t("Keep the group's savings, loans, repayments and fines. It works out the interest, who owes what, who has missed saving, and writes the meeting report and each member's statement.", "समूह की बचत, ऋण, किस्तें और जुर्माना रखिए। यह ब्याज, किस पर कितना बाक़ी है, किसने बचत छोड़ी, यह निकालता है और बैठक की रिपोर्ट व हर सदस्य का विवरण लिखता है।")}</p>
      <div className={`offline-bar ${kiosk ? "off" : ""}`}>{kiosk
        ? t("Shared-device mode: this ledger is NOT saved. Export a backup file before you press Next person.", "साझा-डिवाइस मोड: यह बही सहेजी नहीं जाती। अगला व्यक्ति दबाने से पहले बैकअप फ़ाइल निकालिए।")
        : t("Saved on this device only (not on any server). Export a backup file after every meeting.", "सिर्फ़ इसी डिवाइस पर सहेजी जाती है (किसी सर्वर पर नहीं)। हर बैठक के बाद बैकअप फ़ाइल निकालिए।")}</div>

      <details className="rural-letter" open={led.members.length === 0}><summary>{t("1. Group and members", "1. समूह और सदस्य")}</summary>
        <div className="rural-form three">
          <label>{t("Group name", "समूह का नाम")}<input value={led.group} onChange={(e) => setLed({ ...led, group: e.target.value })} /></label>
          <label>{t("Interest on loans (% a month)", "ऋण पर ब्याज (% महीना)")}<input inputMode="decimal" value={led.rate} onChange={(e) => setLed({ ...led, rate: Number(e.target.value) || 0 })} /></label>
          <label>{t("Loan up to (× savings)", "ऋण अधिकतम (× बचत)")}<input inputMode="decimal" value={led.loan_multiple} onChange={(e) => setLed({ ...led, loan_multiple: Number(e.target.value) || 0 })} /></label>
        </div>
        <div className="rural-row" style={{ gridTemplateColumns: "1fr auto" }}>
          <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder={t("Add a member's name", "सदस्य का नाम जोड़िए")} onKeyDown={(e) => { if (e.key === "Enter") addMember(); }} />
          <button className="btn go" onClick={addMember}>{t("Add", "जोड़ें")}</button>
        </div>
        <p className="rural-note">{led.members.map((m) => m.name).join(", ") || t("No members yet.", "अभी कोई सदस्य नहीं।")}</p>
      </details>

      {led.members.length > 0 && (<>
        <h3>{t("2. Enter a meeting", "2. बैठक की प्रविष्टि")}</h3>
        <div className="rural-form three">
          <label>{t("Date", "तारीख़")}<input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} /></label>
          <label>{t("Member", "सदस्य")}<select value={memberId} onChange={(e) => setForm({ ...form, member: e.target.value })}>{led.members.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}</select></label>
          <label>{t("What", "क्या")}<select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>{TYPES.map(([v, en, h]) => <option key={v} value={v}>{t(en, h)}</option>)}</select></label>
          <label>{t("Amount (₹)", "रक़म (₹)")}<input inputMode="numeric" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} onKeyDown={(e) => { if (e.key === "Enter") addEntry(); }} /></label>
          <label>{t("Note (optional)", "टिप्पणी (वैकल्पिक)")}<input value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} /></label>
        </div>
        <div className="rural-actions">
          <button className="btn go" onClick={addEntry}>{t("Add entry", "प्रविष्टि जोड़ें")}</button>
          <input style={{ width: 130 }} inputMode="numeric" value={all} onChange={(e) => setAll(e.target.value)} placeholder={t("₹ from everyone", "सबसे ₹")} aria-label="amount from everyone" />
          <button className="btn" onClick={collectAll}>{t("Everyone saved this", "सबने इतनी बचत दी")}</button>
        </div>
        {led.entries.length > 0 && <p className="rural-note">{t("Latest: ", "ताज़ा: ")}{led.entries.slice(-4).reverse().map((e, i) => `${e.date} ${nameOf(e.member)} ${typeLabel(e.type)} ${rs(e.amount)}`).join(" · ")}{" "}
          <button className="btn ghost sm" onClick={() => setLed({ ...led, entries: led.entries.slice(0, -1) })}>↶ {t("Undo last", "आख़िरी हटाएँ")}</button></p>}
      </>)}

      {s && (<>
        <label style={{ display: "block", margin: "10px 0" }}>{t("Accounts up to", "हिसाब इस तारीख़ तक")} <input type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} /></label>
        <div className="rural-facts">
          <div><small>{t("Group savings", "समूह की बचत")}</small><b>{rs(s.totals.savings)}</b></div>
          <div><small>{t("Loans out", "बाहर ऋण")}</small><b>{rs(s.totals.loans_out)}</b></div>
          <div><small>{t("Interest earned", "कमाया ब्याज")}</small><b>{rs(s.totals.interest_income)}</b></div>
          <div><small>{t("Should be in hand / bank", "हाथ / बैंक में होना चाहिए")}</small><b className={s.totals.cash < 0 ? "bad" : ""}>{rs(s.totals.cash)}</b></div>
        </div>
        {s.alerts.length > 0 && <ul className="rural-flags">{s.alerts.map((a) => <li key={a}>{a}</li>)}</ul>}
        <div style={{ overflowX: "auto" }}><table className="rural-table"><thead><tr><th>{t("Member", "सदस्य")}</th><th>{t("Savings", "बचत")}</th><th>{t("Loan balance", "ऋण बाक़ी")}</th><th>{t("Interest due", "ब्याज देय")}</th><th>{t("Total to pay", "कुल देना")}</th><th>{t("Year-end share", "वर्षांत हिस्सा")}</th><th></th></tr></thead>
          <tbody>{s.members.map((m) => (
            <tr key={m.id} className={m.status === "ok" ? "" : "bad"}><td>{m.name}</td><td>{rs(m.savings)}</td><td>{rs(m.outstanding)}</td><td>{rs(m.interest_due)}</td><td>{rs(m.total_due)}</td><td>{rs(m.year_end_share)}</td>
              <td>{m.overdue ? t("overdue", "बकाया") : m.missed_months >= 2 ? t("missed saving", "बचत छूटी") : "✓"}</td></tr>))}</tbody></table></div>

        <h3>{t("Can we lend?", "क्या हम ऋण दे सकते हैं?")}</h3>
        <div className="rural-row" style={{ gridTemplateColumns: "1fr 1fr" }}>
          <select value={lend.member} onChange={(e) => setLend({ ...lend, member: e.target.value })}><option value="">{t("Choose member", "सदस्य चुनिए")}</option>{led.members.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}</select>
          <input inputMode="numeric" placeholder={t("Loan amount ₹", "ऋण रक़म ₹")} value={lend.amount} onChange={(e) => setLend({ ...lend, amount: e.target.value })} />
        </div>
        {lendRes && lend.member && <><p className="rural-head">{lendRes.headline}</p><ul className="rural-flags good">{lendRes.checks.map((c) => <li key={c.id}>{c.ok ? "✓ " : "✗ "}{c.text}</li>)}</ul></>}

        <h3>{t("Share with the group", "समूह के साथ साझा करें")}</h3>
        <details className="rural-letter"><summary>{t("Meeting report", "बैठक की रिपोर्ट")}</summary><pre>{s.report}</pre>
          <button className="btn ghost sm" onClick={() => void copy("rep", s.report)}>{copied === "rep" ? t("Copied ✓", "कॉपी हुआ ✓") : t("Copy for WhatsApp", "WhatsApp के लिए कॉपी")}</button></details>
        <details className="rural-letter"><summary>{t("A member's statement", "किसी सदस्य का विवरण")}</summary>
          <select value={who || s.members[0].id} onChange={(e) => setWho(e.target.value)}>{s.members.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}</select>
          <pre>{s.statements[who || s.members[0].id]}</pre>
          <button className="btn ghost sm" onClick={() => void copy("st", s.statements[who || s.members[0].id])}>{copied === "st" ? t("Copied ✓", "कॉपी हुआ ✓") : t("Copy", "कॉपी")}</button></details>
        <p className="rural-note">{s.method}</p>
        <div className="rural-actions">
          <button className="btn" onClick={() => download(`${led.group || "group"}-ledger.json`, JSON.stringify(led, null, 2), "application/json")}>⬇ {t("Backup file", "बैकअप फ़ाइल")}</button>
          <button className="btn" onClick={() => download(`${led.group || "group"}-entries.csv`, csv(), "text/csv")}>⬇ {t("Entries (CSV)", "प्रविष्टियाँ (CSV)")}</button>
          <label className="btn" style={{ cursor: "pointer" }}>⬆ {t("Restore backup", "बैकअप वापस लाएँ")}<input type="file" accept=".json,application/json" hidden onChange={(e) => void importFile(e.target.files?.[0])} /></label>
          <button className="btn ghost sm" onClick={() => window.print()}>🖨 {t("Print", "छापें")}</button>
        </div>
      </>)}
      {!s && led.members.length === 0 && <label className="btn" style={{ cursor: "pointer", display: "inline-block", marginTop: 8 }}>⬆ {t("Restore a backup file", "बैकअप फ़ाइल वापस लाएँ")}<input type="file" accept=".json,application/json" hidden onChange={(e) => void importFile(e.target.files?.[0])} /></label>}
    </section>
  );
}

/* ------------------------------------------------------------------ E1 daily saving */
type Save = { band: string; headline: string; bullets: string[]; mode?: string; target_future?: number; need_monthly_rd?: number; per_day_rd?: number; per_week_rd?: number;
  deposited_rd?: number; interest_rd?: number; wage_share_pct?: number; matures?: number; put_in?: number; interest?: number; months_to_target?: number | null;
  table?: { daily: number; monthly: number; after: number; months_to_goal: number | null }[]; places: { name: string; rate: number; note: string }[]; rules: string[]; note: string };
const GOALS: [string, string, string][] = [["daughter", "Daughter's marriage or education", "बेटी की शादी या पढ़ाई"], ["son", "Son's education", "बेटे की पढ़ाई"], ["house", "House or roof repair", "मकान या छत की मरम्मत"],
  ["medical", "Medical emergency fund", "इलाज के लिए आपात निधि"], ["animal", "Cow, buffalo or goat", "गाय, भैंस या बकरी"], ["tools", "Tools, cart or a small shop", "औज़ार, ठेला या छोटी दुकान"],
  ["festival", "Festival or wedding in the family", "त्योहार या घर की शादी"], ["oldage", "Old age", "बुढ़ापा"], ["other", "Something else", "कुछ और"]];

function SavingTool({ init }: { init: Record<string, string> }) {
  const { t } = useT(); const lang = useLang((s) => s.lang);
  const guided = init.tool === "saving";
  const waiting = useWaiting("saving");
  const [f, setF] = useState(() => guided
    ? { goal: init.goal ?? "other", target: init.target ? String(Number(init.target)) : "", years: init.months ? String(Number(init.months) / 12) : "", daily: init.daily ?? "", wage: init.daily_wage ?? "", dpm: "26", rate: "6.7" }
    : store.get("saving", { goal: "daughter", target: "100000", years: "5", daily: "", wage: "400", dpm: "26", rate: "6.7" }));
  useEffect(() => { if (!guided) store.set("saving", f); }, [f, guided]);
  const set = (k: string) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  const n = (v: string) => Number(v) || 0;
  const months = Math.round(n(f.years) * 12);
  const ok = !waiting && ((n(f.target) > 0 && months > 0) || n(f.daily) > 0);
  const r = usePost<Save>("/rural/saving", { goal: f.goal, target: n(f.target) || null, months: months || null, daily: n(f.daily) || null, daily_wage: n(f.wage) || null, days_per_month: n(f.dpm) || 26, rate: n(f.rate), lang }, ok, 250);
  return (
    <section className="card wide rural-card" data-date={new Date().toLocaleDateString()}>
      <h2>{t("Save a little every day for a goal", "किसी लक्ष्य के लिए रोज़ थोड़ी बचत")}</h2>
      <Waiting tool="saving" />
      <p className="muted">{t("A small amount saved on the days you work adds up, and a recurring deposit adds interest. Tell me the goal and when, and I show what to put aside each working day. Or tell me what you can save a day and I show what it becomes.", "काम के दिनों में बचाई छोटी रक़म जुड़कर बड़ी हो जाती है, और आवर्ती जमा ब्याज भी जोड़ती है। लक्ष्य और समय बताइए, मैं दिखाऊँगा कि हर काम के दिन कितना अलग रखना है। या बताइए रोज़ कितना बचा सकते हैं, मैं दिखाऊँगा वह क्या बनेगा।")}</p>
      <div className="rural-form">
        <label>{t("Saving for", "किसके लिए")}<select value={f.goal} onChange={set("goal")}>{GOALS.map(([v, en, hi]) => <option key={v} value={v}>{t(en, hi)}</option>)}</select></label>
        <label>{t("What it costs today (₹)", "आज इसका ख़र्च (₹)")}<input inputMode="numeric" value={f.target} onChange={set("target")} /></label>
        <label>{t("Needed in (years)", "कितने साल में चाहिए")}<input inputMode="decimal" value={f.years} onChange={set("years")} /></label>
        <label>{t("Or: what I can save per working day (₹)", "या: रोज़ (काम के दिन) कितना बचा सकता हूँ (₹)")}<input inputMode="numeric" value={f.daily} onChange={set("daily")} /></label>
        <label>{t("My wage on a working day (₹, optional)", "काम के दिन मेरी मज़दूरी (₹, वैकल्पिक)")}<input inputMode="numeric" value={f.wage} onChange={set("wage")} /></label>
        <label>{t("Working days in a month", "महीने में काम के दिन")}<input inputMode="numeric" value={f.dpm} onChange={set("dpm")} /></label>
      </div>
      {r && (<>
        <div className={`rural-big ${r.band}`}><span style={{ fontSize: 32 }}>{r.per_day_rd !== undefined ? `₹${Math.round(r.per_day_rd)}` : r.matures !== undefined ? `₹${r.matures.toLocaleString("en-IN")}` : "–"}</span><small>{r.per_day_rd !== undefined ? t("per working day", "प्रति काम के दिन") : t("after the time", "उस समय बाद")}</small></div>
        <p className="rural-head">{r.headline}</p>
        <ul className="rural-flags good">{r.bullets.map((b) => <li key={b}>{b}</li>)}</ul>
        {r.table && <><h3>{t("If you can save a fixed amount a day", "रोज़ तय रक़म बचा सकें तो")}</h3>
          <table className="rural-table"><thead><tr><th>{t("Per working day", "प्रति काम के दिन")}</th><th>{t("Per month", "महीना")}</th><th>{t("After the time", "उस समय बाद")}</th><th>{t("Months to reach the goal", "लक्ष्य तक महीने")}</th></tr></thead>
            <tbody>{r.table.map((x) => <tr key={x.daily}><td>₹{x.daily}</td><td>₹{x.monthly.toLocaleString("en-IN")}</td><td>₹{x.after.toLocaleString("en-IN")}</td><td>{x.months_to_goal ?? "–"}</td></tr>)}</tbody></table></>}
        <h3>{t("Where to keep it", "कहाँ रखें")}</h3>
        <ul className="rural-links">{r.places.map((p) => <li key={p.name}><b>{p.name}</b>{p.rate ? ` (~${p.rate}%)` : ""}: {p.note}</li>)}</ul>
        <h3>{t("Four rules that make it work", "चार नियम जिनसे यह चलता है")}</h3>
        <ol className="rural-steps">{r.rules.map((x) => <li key={x}>{x}</li>)}</ol>
        <p className="rural-note">{r.note}</p>
        <Say text={r.headline} />
      </>)}
    </section>
  );
}

/* ------------------------------------------------------------------ C3 sell now or hold */
type Hold = { band: string; headline: string; verdict: string; sell_now: number; sell_now_future: number; breakeven_price: number | null; rise_needed_pct: number | null;
  hold_value: number | null; gain: number | null; holding_costs: number; crop_left_pct: number; cash_note: string; warn: string; tip: string; n_history: number;
  years: { year: number; from: number; to: number; rise_pct: number }[]; history: { n: number; enough: number; median_rise: number; worst: number; best: number } | null;
  season: { month: number; avg: number; index: number; years: number }[] };
const HOLD_EXAMPLE = "Oct 2021: 2000\nFeb 2022: 2150\nOct 2022: 2100\nFeb 2023: 2400\nOct 2023: 2250\nFeb 2024: 2300";

function HoldTool({ init }: { init: Record<string, string> }) {
  const { t, hi } = useT(); const lang = useLang((s) => s.lang);
  const guided = init.tool === "hold";
  const waiting = useWaiting("hold");
  const [f, setF] = useState(() => guided
    ? { qty: init.qty ?? "", price_now: init.price_now ?? "", months: init.months ?? "", price_later: init.price_later ?? "", storage: init.storage ?? "0", shrink: "0", handling: "0", rate: "7", from_month: "10" }
    : store.get("hold", { qty: "50", price_now: "2100", months: "4", price_later: "2400", storage: "10", shrink: "1", handling: "20", rate: "7", from_month: "10" }));
  const [history, setHistory] = useState("");
  useEffect(() => { if (!guided) store.set("hold", f); }, [f, guided]);
  const set = (k: string) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  const n = (v: string) => Number(v) || 0;
  const ok = !waiting && n(f.qty) > 0 && n(f.price_now) > 0 && n(f.months) > 0;
  const r = usePost<Hold>("/rural/hold", { qty: n(f.qty), price_now: n(f.price_now), months: n(f.months), price_later: n(f.price_later) || null, storage: n(f.storage),
    shrink: n(f.shrink), handling: n(f.handling), rate: n(f.rate), history, from_month: n(f.from_month) || null, lang }, ok, 250);
  const names = hi ? MON_HI : MON_EN;
  return (
    <section className="card wide rural-card" data-date={new Date().toLocaleDateString()}>
      <h2>{t("Sell the crop now, or wait for a better price?", "फ़सल अभी बेचें, या बेहतर भाव के लिए रुकें?")}</h2>
      <Waiting tool="hold" />
      <p className="muted">{t("Nobody can promise next season's price, and I will not guess it. I tell you how much higher the price must be just to break even after storage, shrinkage and the cost of money, and, if you paste your own past prices, how often that happened.", "अगले मौसम का भाव कोई नहीं बता सकता और मैं अंदाज़ा नहीं लगाऊँगा। मैं बताता हूँ कि भंडारण, छीजन और पैसे की क़ीमत के बाद बराबरी पर आने के लिए भाव कितना ऊँचा चाहिए, और आप अपने पुराने भाव डालें तो वैसा कितनी बार हुआ।")}</p>
      <div className="rural-form">
        <label>{t("Quintals you have", "कितने क्विंटल है")}<input inputMode="decimal" value={f.qty} onChange={set("qty")} /></label>
        <label>{t("Price today (₹ per quintal)", "आज का भाव (₹ प्रति क्विंटल)")}<input inputMode="numeric" value={f.price_now} onChange={set("price_now")} /></label>
        <label>{t("Months you could wait", "कितने महीने रुक सकते हैं")}<input inputMode="numeric" value={f.months} onChange={set("months")} /></label>
        <label>{t("Price you expect then (optional)", "तब का अपेक्षित भाव (वैकल्पिक)")}<input inputMode="numeric" value={f.price_later} onChange={set("price_later")} /></label>
        <label>{t("Storage cost (₹ per quintal per month)", "भंडारण ख़र्च (₹ प्रति क्विंटल प्रति माह)")}<input inputMode="decimal" value={f.storage} onChange={set("storage")} /></label>
        <label>{t("Loss while stored (% per month)", "भंडारण में छीजन (% प्रति माह)")}<input inputMode="decimal" value={f.shrink} onChange={set("shrink")} /></label>
        <label>{t("Handling / transport once (₹ per quintal)", "ढुलाई एक बार (₹ प्रति क्विंटल)")}<input inputMode="decimal" value={f.handling} onChange={set("handling")} /></label>
        <label>{t("What the money earns or saves (% a year)", "पैसे की कमाई या बचत (% सालाना)")}
          <select value={f.rate} onChange={set("rate")}><option value="7">{t("Safe deposit ~7%", "सुरक्षित जमा ~7%")}</option><option value="4">{t("Cheap farm loan ~4%", "सस्ता कृषि ऋण ~4%")}</option><option value="12">{t("Bank loan ~12%", "बैंक ऋण ~12%")}</option><option value="36">{t("Moneylender ~36%", "साहूकार ~36%")}</option><option value="60">{t("Moneylender ~60%", "साहूकार ~60%")}</option></select></label>
      </div>
      <details className="rural-letter"><summary>{t("Optional: paste your own past prices (to see how often waiting paid)", "वैकल्पिक: अपने पुराने भाव डालिए (देखने के लिए कि रुकना कितनी बार फ़ायदे का रहा)")}</summary>
        <label style={{ display: "block", margin: "8px 0" }}>{t("Starting month of the wait", "रुकने की शुरुआत का महीना")}
          <select value={f.from_month} onChange={set("from_month")}>{names.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}</select></label>
        <textarea rows={6} value={history} onChange={(e) => setHistory(e.target.value)} placeholder={HOLD_EXAMPLE} />
        <p className="rural-note">{t("One price per line, with the month and year, for example “Oct 2022: 2100” or “2023-02 2400”. Your mandi's records or your own sale slips work. At least 3 years is useful.", "हर पंक्ति में महीना, साल और भाव, जैसे “Oct 2022: 2100” या “2023-02 2400”। अपनी मंडी का रिकॉर्ड या अपनी बिक्री की पर्चियाँ चलेंगी। कम से कम 3 साल हों तो उपयोगी।")}</p></details>
      {r && (<>
        <div className={`rural-big ${r.band}`}><span style={{ fontSize: 30 }}>{r.breakeven_price !== null ? `₹${Math.round(r.breakeven_price).toLocaleString("en-IN")}` : "–"}</span><small>{t("break-even price per quintal", "बराबरी का भाव प्रति क्विंटल")}{r.rise_needed_pct !== null ? ` · +${r.rise_needed_pct.toFixed(1)}%` : ""}</small></div>
        <p className="rural-head">{r.headline} {r.verdict}</p>
        <table className="rural-table"><tbody>
          <tr><td>{t("Sell now", "अभी बेचें")}</td><td>₹{r.sell_now.toLocaleString("en-IN")}</td><td className="muted">{t("worth about", "आगे की क़ीमत लगभग")} ₹{r.sell_now_future.toLocaleString("en-IN")}</td></tr>
          <tr><td>{t("Hold: costs", "रुकें: ख़र्च")}</td><td>₹{r.holding_costs.toLocaleString("en-IN")}</td><td className="muted">{t("crop left", "बची फ़सल")} {r.crop_left_pct}%</td></tr>
          {r.hold_value !== null && <tr><td>{t("Hold at your expected price", "अपेक्षित भाव पर रुकें")}</td><td>₹{r.hold_value.toLocaleString("en-IN")}</td><td className={r.gain! > 0 ? "good" : "bad"}>{r.gain! > 0 ? "+" : ""}₹{r.gain!.toLocaleString("en-IN")}</td></tr>}
        </tbody></table>
        {r.history && <>
          <h3>{t("In your own past prices", "आपके अपने पुराने भावों में")}</h3>
          <p className="rural-head">{t(`The price rose by enough in ${r.history.enough} of ${r.history.n} years. Typical change ${r.history.median_rise}% (worst ${r.history.worst}%, best ${r.history.best}%).`, `${r.history.n} में से ${r.history.enough} साल भाव इतना बढ़ा। सामान्य बदलाव ${r.history.median_rise}% (सबसे बुरा ${r.history.worst}%, सबसे अच्छा ${r.history.best}%)।`)}</p>
          <table className="rural-table"><thead><tr><th>{t("Year", "साल")}</th><th>{t("Start", "शुरू")}</th><th>{t("End", "अंत")}</th><th>{t("Change", "बदलाव")}</th></tr></thead>
            <tbody>{r.years.map((y) => <tr key={y.year}><td>{y.year}</td><td>₹{y.from}</td><td>₹{y.to}</td><td className={y.rise_pct >= (r.rise_needed_pct ?? 0) ? "good" : "bad"}>{y.rise_pct}%</td></tr>)}</tbody></table></>}
        {r.season.length > 0 && <p className="rural-note">{t("Average price by month (100 = your average): ", "महीने के हिसाब से औसत भाव (100 = आपका औसत): ")}{r.season.map((s) => `${names[s.month - 1]} ${s.index}`).join(" · ")}</p>}
        <p className="rural-note">{r.cash_note} {r.tip}</p>
        <p className="rural-note">{r.warn}</p>
        <Say text={`${r.headline} ${r.verdict}`} />
      </>)}
    </section>
  );
}

/* ------------------------------------------------------------------ B3 why the payment did not come */
type Dbt = { headline: string; check_at: string; scam: boolean; scam_note: string; complain: string[]; note: string;
  causes: { id: string; score: number; title: string; why: string; steps: string[] }[]; letters: { office: string; bank: string } };

function DbtTool({ init }: { init: Record<string, string> }) {
  const { t } = useT(); const lang = useLang((s) => s.lang);
  const guided = init.tool === "dbt";
  const waiting = useWaiting("dbt");
  const [f, setF] = useState(() => ({ scheme: "pm_kisan", status: "pending", linked: "unsure", name_same: "unsure", merged: "unsure", last_used: "recent", aadhaar_mobile: "unsure",
    ...(guided ? Object.fromEntries(["scheme", "status", "linked", "name_same", "merged", "last_used"].filter((k) => init[k]).map((k) => [k, init[k]])) : {}) }));
  const [who, setWho] = useState({ name: "", village: "", block: "", bank: "" });
  const [text, setText] = useState("");
  const [go, setGo] = useState(guided && !!init.run);
  const set = (k: string) => (e: { target: { value: string } }) => { setF({ ...f, [k]: e.target.value }); setGo(true); };
  const r = usePost<Dbt>("/rural/dbt", { ...f, text, ...who, lang }, go && !waiting, 200);
  const [copied, setCopied] = useState("");
  const copy = async (k: string, s: string) => { try { await navigator.clipboard.writeText(s); setCopied(k); setTimeout(() => setCopied(""), 1500); } catch { /* clipboard blocked */ } };
  const yn = (k: string, en: string, hi: string) => (
    <label>{t(en, hi)}<select value={(f as Record<string, string>)[k]} onChange={set(k)}><option value="yes">{t("Yes", "हाँ")}</option><option value="no">{t("No", "नहीं")}</option><option value="unsure">{t("Not sure", "पक्का नहीं")}</option></select></label>);
  return (
    <section className="card wide rural-card" data-date={new Date().toLocaleDateString()}>
      <h2>{t("Why has my government payment not come?", "मेरा सरकारी पैसा क्यों नहीं आया?")}</h2>
      <Waiting tool="dbt" />
      <p className="muted">{t("A payment passes through a short chain: registered, approved, Aadhaar linked to one bank account, names match, account active. Almost every missing payment is a break at one link. Answer what you know: I rank the likely breaks and give the fix and a letter.", "भुगतान एक छोटी कड़ी से गुज़रता है: पंजीकरण, मंज़ूरी, आधार का एक बैंक खाते से जुड़ाव, नाम का मेल, चालू खाता। लगभग हर रुका भुगतान किसी एक कड़ी पर टूटता है। जो जानते हैं बताइए: मैं संभावित टूट क्रम से और उसका इलाज और चिट्ठी दूँगा।")}</p>
      <div className="rural-form">
        <label>{t("Which payment", "कौन सा भुगतान")}<select value={f.scheme} onChange={set("scheme")}>
          {[["pm_kisan", "PM-KISAN", "पीएम-किसान"], ["pension", "Pension", "पेंशन"], ["scholarship", "Scholarship", "छात्रवृत्ति"], ["lpg", "LPG subsidy", "गैस सब्सिडी"], ["mgnrega", "MGNREGA wages", "मनरेगा मज़दूरी"], ["ration", "Ration", "राशन"], ["other", "Something else", "कुछ और"]].map(([v, en, hi]) => <option key={v} value={v}>{t(en, hi)}</option>)}</select></label>
        <label>{t("What does the status say", "स्टेटस में क्या लिखा है")}<select value={f.status} onChange={set("status")}>
          {[["not_applied", "I never applied / not sure I am registered", "आवेदन नहीं किया / पता नहीं पंजीकृत हूँ"], ["pending", "Pending or under process", "पेंडिंग या प्रक्रिया में"], ["rejected", "Rejected or failed", "रिजेक्ट या फ़ेल"], ["approved", "Approved or paid, but nothing came", "मंज़ूर या भुगतान, पर पैसा नहीं आया"], ["other_account", "Paid to an account I do not know", "किसी अनजान खाते में भुगतान"], ["no_status", "I cannot see any status", "कोई स्टेटस नहीं दिख रहा"]].map(([v, en, hi]) => <option key={v} value={v}>{t(en, hi)}</option>)}</select></label>
        {yn("linked", "Aadhaar linked to this bank account for benefit transfer?", "आधार इस बैंक खाते से लाभ हस्तांतरण के लिए जुड़ा है?")}
        {yn("name_same", "Name spelled exactly the same on Aadhaar, passbook and scheme?", "आधार, पासबुक और योजना में नाम हूबहू एक है?")}
        {yn("merged", "Has your bank merged with another or changed its codes?", "क्या आपका बैंक किसी में मिला या कोड बदले?")}
        {yn("aadhaar_mobile", "Is your mobile number linked to Aadhaar?", "क्या आपका मोबाइल नंबर आधार से जुड़ा है?")}
        <label>{t("When did you last use the account yourself", "खाता आख़िरी बार कब चलाया")}<select value={f.last_used} onChange={set("last_used")}>
          <option value="recent">{t("In the last few months", "पिछले कुछ महीनों में")}</option><option value="old">{t("Over a year ago", "एक साल से ज़्यादा पहले")}</option><option value="never">{t("Never since opening", "खुलने के बाद कभी नहीं")}</option></select></label>
      </div>
      <textarea rows={2} value={text} onChange={(e) => setText(e.target.value)} onBlur={() => setGo(true)} placeholder={t("Anything else? e.g. someone asked me for a fee to release it", "और कुछ? जैसे: किसी ने छुड़ाने के लिए फ़ीस माँगी")} />
      <div className="rural-actions"><button className="btn go" onClick={() => setGo(true)}>{t("Find the break", "टूट खोजिए")}</button></div>
      {r && go && (<>
        <div className="rural-big amber"><span style={{ fontSize: 22 }}>{r.headline}</span></div>
        {r.scam && <div className="rural-rule bad">⚠ {r.scam_note}</div>}
        <ol className="rural-steps">{r.causes.map((c) => (
          <li key={c.id}><b>{c.title}</b><span className="tag">{t("likelihood", "संभावना")} {c.score}</span>
            <p>{c.why}</p><ul className="rural-flags good">{c.steps.map((s) => <li key={s}>{s}</li>)}</ul></li>))}</ol>
        <h3>{t("If it is still stuck", "फिर भी अटका रहे तो")}</h3>
        <ul className="rural-links">{r.complain.map((x) => <li key={x}>{x}</li>)}<li>{t("Check status at: ", "स्टेटस यहाँ देखिए: ")}{r.check_at}</li></ul>
        <h3>{t("Letters you can hand in", "चिट्ठियाँ जो आप दे सकते हैं")}</h3>
        <div className="rural-form three">
          {([["name", "Your name", "आपका नाम"], ["village", "Village", "गाँव"], ["block", "Block / office", "ब्लॉक / कार्यालय"], ["bank", "Bank and branch", "बैंक और शाखा"]] as const).map(([k, en, hi]) => (
            <label key={k}>{t(en, hi)}<input value={who[k]} onChange={(e) => setWho({ ...who, [k]: e.target.value })} /></label>))}
        </div>
        {(["office", "bank"] as const).map((k) => (
          <details key={k} className="rural-letter"><summary>{k === "office" ? t("To the block / scheme office", "ब्लॉक / योजना कार्यालय को") : t("To the bank manager", "बैंक प्रबंधक को")}</summary>
            <pre>{r.letters[k]}</pre><button className="btn ghost sm" onClick={() => void copy(k, r.letters[k])}>{copied === k ? t("Copied ✓", "कॉपी हुआ ✓") : t("Copy", "कॉपी")}</button></details>))}
        <p className="rural-note">{r.note}</p>
        <Say text={r.headline} />
      </>)}
    </section>
  );
}

/* ------------------------------------------------------------------ A4 UPI safety */
type Upi = { matched: string | null; level: string; headline: string; why: string; do: string[]; rules: string[]; recover: string; verdict: string };
type Drills = { drills: { id: string; scenario: string; why: string; options: { text: string; right: boolean }[] }[]; menu: { text: string; label: string }[]; rules: string[]; recover: string };

function UpiTool({ init }: { init: Record<string, string> }) {
  const { t } = useT(); const lang = useLang((s) => s.lang);
  const guided = init.tool === "upi";
  const waiting = useWaiting("upi");
  const [text, setText] = useState(guided ? init.text ?? "" : "");
  const [go, setGo] = useState(guided && !!init.run && !!init.text);
  const [data, setData] = useState<Drills | null>(null);
  useEffect(() => { ruralFetch(`/rural/upi/drills?lang=${lang}`).then(setData).catch(() => {}); }, [lang]);
  const r = usePost<Upi>("/rural/upi", { text, lang }, go && !waiting && !!text.trim(), 0);
  const [i, setI] = useState(0);
  const [picked, setPicked] = useState<number | null>(null);
  const [score, setScore] = useState({ right: 0, done: 0 });
  // scenarios and the answers inside each are both shuffled, so "always pick the middle one" cannot win
  const order = useMemo(() => (data ? [...data.drills].sort(() => Math.random() - 0.5).map((x) => ({ ...x, options: [...x.options].sort(() => Math.random() - 0.5) })) : []), [data]);
  const d = order[i];
  const choose = (k: number) => { if (picked !== null || !d) return; setPicked(k); setScore((s) => ({ right: s.right + (d.options[k].right ? 1 : 0), done: s.done + 1 })); };
  const next = () => { setPicked(null); setI((x) => x + 1); };
  const finished = order.length > 0 && i >= order.length;
  return (
    <>
      <section className="card wide rural-card" data-date={new Date().toLocaleDateString()}>
        <h2>{t("Is this UPI request safe?", "क्या यह UPI रिक्वेस्ट सुरक्षित है?")}</h2>
        <Waiting tool="upi" />
        <p className="muted">{t("Tap what is happening, or describe it. UPI fraud is a few tricks repeated: I name the trick and tell you what to do.", "जो हो रहा है उसे चुनिए या बताइए। UPI ठगी कुछ ही चालों का दोहराव है: मैं चाल का नाम और आपको क्या करना है बताता हूँ।")}</p>
        <div className="rural-actions">{(data?.menu ?? []).map((m) => <button key={m.text} className="btn ghost sm" onClick={() => { setText(m.text); setGo(true); }}>{m.label}</button>)}</div>
        <textarea rows={2} value={text} onChange={(e) => { setText(e.target.value); setGo(false); }} placeholder={t("e.g. a buyer says scan this QR to receive my money", "जैसे: ख़रीदार कहता है पैसे पाने के लिए यह QR स्कैन करो")} />
        <div className="rural-actions"><button className="btn go" onClick={() => setGo(true)}>{t("Check it", "जाँचिए")}</button></div>
        {r && go && (<>
          <div className={`rural-big ${r.level}`}><span style={{ fontSize: 26 }}>{r.headline}</span></div>
          <p className="rural-head">{r.why}</p>
          <h3>{t("What to do", "क्या करें")}</h3>
          <ul className="rural-flags good">{r.do.map((x) => <li key={x}>{x}</li>)}</ul>
          <div className="rural-rule">{r.verdict} {r.recover}</div>
          <Say text={`${r.headline} ${r.why} ${r.do[0] ?? ""}`} />
        </>)}
        <h3>{t("The six rules that cover almost every UPI fraud", "वे छह नियम जो लगभग हर UPI ठगी को पकड़ते हैं")}</h3>
        <ol className="rural-steps">{(data?.rules ?? []).map((x) => <li key={x}>{x}</li>)}</ol>
      </section>
      <section className="card wide rural-card">
        <h2>{t("Practice: what would you do?", "अभ्यास: आप क्या करेंगे?")}</h2>
        <p className="muted">{t("Real situations, three answers each. Learning on a drill costs nothing; learning on a real one costs money.", "असली जैसी स्थितियाँ, हर एक के तीन जवाब। अभ्यास में सीखना मुफ़्त है; असली में सीखना महँगा।")}</p>
        {d && !finished && (<>
          <div className="rural-head"><small>{i + 1}/{order.length}</small> {d.scenario}</div>
          <div className="upi-opts">{d.options.map((o, k) => (
            <button key={k} className={picked === null ? "" : o.right ? "right" : picked === k ? "wrong" : "dim"} onClick={() => choose(k)}>{o.text}</button>))}</div>
          {picked !== null && (<>
            <div className={`rural-rule ${d.options[picked].right ? "" : "bad"}`}>{d.options[picked].right ? "✓ " : "✗ "}{d.why}</div>
            <div className="rural-actions"><button className="btn go" onClick={next}>{i + 1 < order.length ? t("Next →", "अगला →") : t("See my score", "मेरा स्कोर देखें")}</button></div>
          </>)}
        </>)}
        {finished && (<>
          <div className={`rural-big ${score.right >= score.done * 0.75 ? "green" : score.right >= score.done / 2 ? "amber" : "red"}`}><span>{score.right}/{score.done}</span><small>{t("safe choices", "सुरक्षित जवाब")}</small></div>
          <p className="rural-head">{score.right === score.done ? t("All safe. Keep the six rules in mind.", "सब सुरक्षित। छह नियम याद रखिए।") : t("Read the explanation for each miss, then try again.", "जहाँ चूके वहाँ की व्याख्या पढ़िए, फिर दोबारा कीजिए।")}</p>
          <div className="rural-actions"><button className="btn go" onClick={() => { setI(0); setPicked(null); setScore({ right: 0, done: 0 }); }}>{t("Try again", "फिर से")}</button></div>
        </>)}
      </section>
    </>
  );
}

/* ------------------------------------------------------------------ A3 insurance policy */
type Pol = { irr_pct: number | null; band: string; headline: string; verdict: string; bullets: string[]; total_paid: number; maturity: number;
  alt_safe_fv: number; alt_gap: number; flags: { id: string; text: string }[]; advice: string[]; verify: string[]; note: string; scam: boolean };

function PolicyTool({ init }: { init: Record<string, string> }) {
  const { t } = useT(); const lang = useLang((s) => s.lang);
  const guided = init.tool === "policy";
  const waiting = useWaiting("policy");
  const [f, setF] = useState(() => guided
    ? { premium: init.premium ?? "", pay: init.pay_years ?? "", term: init.term_years ?? "", maturity: init.maturity ?? "", cover: init.cover ?? "", quote: "" }
    : store.get("policy", { premium: "50000", pay: "10", term: "20", maturity: "1000000", cover: "500000", quote: "" }));
  const [text, setText] = useState("");
  useEffect(() => { if (!guided) store.set("policy", f); }, [f, guided]);
  const set = (k: string) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  const n = (v: string) => Number(v) || 0;
  const ok = !waiting && n(f.premium) > 0 && n(f.pay) > 0 && n(f.term) >= n(f.pay) && n(f.maturity) > 0;
  const r = usePost<Pol>("/rural/policy", { premium: n(f.premium), pay_years: n(f.pay), term_years: n(f.term), maturity: n(f.maturity),
    sum_assured: n(f.cover) || null, term_quote: n(f.quote) || null, text, lang }, ok || (!waiting && text.length > 8), 300);
  return (
    <section className="card wide rural-card" data-date={new Date().toLocaleDateString()}>
      <h2>{t("Is my insurance policy a good deal?", "क्या मेरी बीमा पॉलिसी अच्छा सौदा है?")}</h2>
      <Waiting tool="policy" />
      <p className="muted">{t("Many endowment and money-back policies are sold as savings but return little. Enter what is on your policy paper: I work out what it really earns and compare it with a safe deposit.", "कई एंडोमेंट और मनी-बैक पॉलिसियाँ बचत बताकर बेची जाती हैं पर रिटर्न कम देती हैं। अपनी पॉलिसी के काग़ज़ की बातें भरिए: मैं निकालूँगा कि असल में कितना कमाती है और सुरक्षित जमा से तुलना दिखाऊँगा।")}</p>
      <div className="rural-form">
        <label>{t("Premium each year (₹)", "साल का प्रीमियम (₹)")}<input inputMode="numeric" value={f.premium} onChange={set("premium")} /></label>
        <label>{t("Years you pay", "कितने साल भरते हैं")}<input inputMode="numeric" value={f.pay} onChange={set("pay")} /></label>
        <label>{t("Policy ends after (years)", "पॉलिसी कितने साल की")}<input inputMode="numeric" value={f.term} onChange={set("term")} /></label>
        <label>{t("Total you get at the end (₹)", "अंत में कुल मिलेगा (₹)")}<input inputMode="numeric" value={f.maturity} onChange={set("maturity")} /></label>
        <label>{t("Life cover / sum assured (₹, optional)", "जीवन कवर / बीमित राशि (₹, वैकल्पिक)")}<input inputMode="numeric" value={f.cover} onChange={set("cover")} /></label>
        <label>{t("Quote for a pure term plan with that cover (₹ a year, optional)", "उतने कवर के शुद्ध टर्म प्लान का भाव (₹ साल, वैकल्पिक)")}<input inputMode="numeric" value={f.quote} onChange={set("quote")} /></label>
      </div>
      <label className="rural-form" style={{ display: "block" }}>{t("What did the seller or caller say? (optional)", "बेचने वाले या कॉल करने वाले ने क्या कहा? (वैकल्पिक)")}
        <textarea rows={2} value={text} onChange={(e) => setText(e.target.value)} placeholder={t("e.g. bank manager said it is better than an FD, guaranteed returns", "जैसे: बैंक मैनेजर ने कहा एफ़डी से बेहतर है, गारंटीड रिटर्न")} /></label>
      {r && (<>
        <div className={`rural-big ${r.band}`}><span>{r.irr_pct === null ? "–" : `${r.irr_pct.toFixed(1)}%`}</span><small>{t("a year", "साल में")}</small></div>
        <p className="rural-head">{r.headline} {r.verdict}</p>
        <ul className="rural-flags good">{r.bullets.map((b) => <li key={b}>{b}</li>)}</ul>
        {r.flags.length > 0 && <><h3>{t("Warning signs in what you were told", "आपको जो बताया गया उसमें चेतावनी-संकेत")}</h3><ul className="rural-flags">{r.flags.map((x) => <li key={x.id}>{x.text}</li>)}</ul></>}
        <h3>{t("What to do", "क्या करें")}</h3>
        <ul className="rural-flags good">{r.advice.map((a) => <li key={a}>{a}</li>)}</ul>
        <ul className="rural-links">{r.verify.map((v) => <li key={v}>{v}</li>)}</ul>
        <p className="rural-note">{r.note}</p>
        <Say text={`${r.headline} ${r.verdict}`} />
      </>)}
    </section>
  );
}

/* ------------------------------------------------------------------ B1 schemes */
type Sch = { id: string; name: string; status: string; gives: string; who: string; where: string; link: string; cash_per_year: number; docs: string[]; doc_ids: string[] };
type Ent = { schemes: Sch[]; count: number; cash_per_year: number; note: string; checked: string };

const WORK: [string, string, string][] = [["farmer", "Farmer (own or rented land)", "किसान (अपनी या बटाई की ज़मीन)"], ["farm_labour", "Farm labourer", "खेत मज़दूर"], ["labour", "Daily-wage labourer", "दिहाड़ी मज़दूर"],
  ["vendor", "Street vendor / small trader", "फेरीवाला / छोटा व्यापारी"], ["artisan", "Artisan (carpenter, potter, weaver...)", "कारीगर (बढ़ई, कुम्हार, बुनकर...)"], ["business", "Small business owner", "छोटा कारोबारी"], ["other", "Something else", "कुछ और"]];

function SchemesTool({ onPick, init }: { onPick: (ids: string[]) => void; init: Record<string, string> }) {
  const { t } = useT(); const lang = useLang((s) => s.lang);
  const guided = init.tool === "schemes";
  const [p, setP] = useState(() => { const base = store.get("profile", { age: "35", gender: "male", land: "none", work: "labour", bank: true, taxpayer: false, poor: "unsure",
    category: "general", daughter: false, kutcha: false, disability: false, widow: false, student: false, shg: false, lpg: true });
    return guided ? { ...base, ...(init.age ? { age: String(init.age) } : {}), ...(init.gender ? { gender: init.gender } : {}), ...(init.work ? { work: init.work } : {}),
      ...(init.land ? { land: init.land } : {}), ...(init.poor ? { poor: init.poor } : {}), ...(init.bank ? { bank: init.bank === "true" } : {}) } : base; });
  const [go, setGo] = useState(guided && !!init.run);
  useEffect(() => store.set("profile", p), [p]);
  const profile = { ...p, age: Number(p.age) || 0 };
  const r = usePost<Ent>("/rural/entitlements", { profile, lang }, go, 0);
  const chk = (k: keyof typeof p, en: string, hi: string) => <label className="rural-check"><input type="checkbox" checked={!!p[k]} onChange={(e) => { setP({ ...p, [k]: e.target.checked }); }} />{t(en, hi)}</label>;
  const sel = (k: keyof typeof p) => (e: { target: { value: string } }) => setP({ ...p, [k]: e.target.value });
  return (
    <section className="card wide rural-card" data-date={new Date().toLocaleDateString()}>
      <h2>{t("Which government schemes am I missing?", "मुझे कौन सी सरकारी योजनाएँ मिल सकती हैं?")}</h2>
      <Waiting tool="schemes" />
      <p className="muted">{t("Answer about the person who is applying. Nothing is saved on a server.", "जो व्यक्ति आवेदन करेगा उसके बारे में जवाब दीजिए। कुछ भी सर्वर पर नहीं रखा जाता।")}</p>
      <div className="rural-form">
        <label>{t("Age", "उम्र")}<input inputMode="numeric" value={p.age} onChange={sel("age")} /></label>
        <label>{t("Gender", "लिंग")}<select value={p.gender} onChange={sel("gender")}><option value="male">{t("Male", "पुरुष")}</option><option value="female">{t("Female", "महिला")}</option><option value="other">{t("Other", "अन्य")}</option></select></label>
        <label>{t("Work", "काम")}<select value={p.work} onChange={sel("work")}>{WORK.map(([v, en, hi]) => <option key={v} value={v}>{t(en, hi)}</option>)}</select></label>
        <label>{t("Land", "ज़मीन")}<select value={p.land} onChange={sel("land")}><option value="none">{t("No land", "ज़मीन नहीं")}</option><option value="own">{t("Own land", "अपनी ज़मीन")}</option><option value="tenant">{t("Rented / sharecrop", "बटाई / किराए की")}</option></select></label>
        <label>{t("Is the household poor / on a BPL or ration list?", "क्या परिवार ग़रीब / बीपीएल या राशन सूची में है?")}<select value={p.poor} onChange={sel("poor")}><option value="yes">{t("Yes", "हाँ")}</option><option value="no">{t("No", "नहीं")}</option><option value="unsure">{t("Not sure", "पक्का नहीं")}</option></select></label>
        <label>{t("Community (for scholarships)", "समुदाय (छात्रवृत्ति के लिए)")}<select value={p.category} onChange={sel("category")}><option value="general">{t("General", "सामान्य")}</option><option value="obc">OBC</option><option value="sc">SC</option><option value="st">ST</option><option value="minority">{t("Minority", "अल्पसंख्यक")}</option></select></label>
      </div>
      <div className="rural-checks">
        {chk("bank", "Has a bank account", "बैंक खाता है")}{chk("taxpayer", "Pays income tax", "आयकर देता/देती है")}{chk("daughter", "Has a daughter under 10", "10 से छोटी बेटी है")}
        {chk("kutcha", "Lives in a kutcha / one-room house", "कच्चे / एक कमरे के मकान में रहते हैं")}{chk("disability", "Has a disability of 80% or more", "80% या ज़्यादा दिव्यांगता")}{chk("widow", "Is a widow", "विधवा हैं")}
        {chk("student", "A child is studying", "बच्चा पढ़ रहा है")}{chk("shg", "Is in a self-help group", "स्वयं सहायता समूह में हैं")}{chk("lpg", "Already has an LPG connection", "गैस कनेक्शन पहले से है")}
      </div>
      <div className="rural-actions"><button className="btn go" onClick={() => setGo(true)}>{t("Show my schemes", "मेरी योजनाएँ दिखाइए")}</button></div>
      {r && go && (<>
        <p className="rural-head">{t(`${r.count} schemes to ask about.`, `${r.count} योजनाओं के बारे में पूछिए।`)} {r.cash_per_year > 0 && t(`Cash support alone is about ${inr(r.cash_per_year)} a year.`, `सिर्फ़ नक़द सहायता साल में लगभग ${inr(r.cash_per_year)} है।`)}</p>
        <div className="rural-schemes">
          {r.schemes.map((s) => (
            <article key={s.id} className={`rural-scheme ${s.status}`}>
              <header><b>{s.name}</b><span className="tag">{s.status === "likely" ? t("Likely", "संभावित") : t("Maybe", "शायद")}</span></header>
              <p>{s.gives}</p>
              <small>{t("For: ", "किसके लिए: ")}{s.who}</small>
              <small>{t("Apply at: ", "कहाँ: ")}{s.where} · {s.link}</small>
            </article>))}
        </div>
        <p className="rural-note">{r.note} ({t("reviewed", "समीक्षा")} {r.checked})</p>
        <div className="rural-actions">
          <button className="btn go" onClick={() => onPick(r.schemes.filter((s) => s.status === "likely").map((s) => s.id))}>{t("Check my documents for these →", "इनके लिए मेरे काग़ज़ जाँचिए →")}</button>
          <Say text={`${r.count} ${t("schemes to ask about", "योजनाएँ")}: ${r.schemes.slice(0, 5).map((s) => s.name).join(", ")}`} />
        </div>
      </>)}
    </section>
  );
}

/* ------------------------------------------------------------------ B2 documents */
type Ready = { summary: string; tip: string; steps: { n: number; id: string; name: string; how: string; blocks: number }[];
  schemes: { id: string; name: string; ready: boolean; have: number; total: number; missing: string[] }[]; all_docs: { id: string; name: string }[] };

function DocsTool({ picked, setPicked, init }: { picked: string[]; setPicked: (x: string[]) => void; init: Record<string, string> }) {
  const { t } = useT(); const lang = useLang((s) => s.lang);
  const [have, setHave] = useState<string[]>(() => (init.tool === "docs" && init.have !== undefined ? init.have.split(",").filter(Boolean) : store.get("have", [])));
  const [catalog, setCatalog] = useState<{ id: string; name: string }[]>([]);
  useEffect(() => store.set("have", have), [have]);
  useEffect(() => { ruralFetch(`/rural/schemes?lang=${lang}`).then((x) => setCatalog(x.schemes)).catch(() => {}); }, [lang]);
  const r = usePost<Ready>("/rural/readiness", { schemes: picked, have, lang }, true, 100);
  const toggle = (arr: string[], v: string) => (arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);
  return (
    <section className="card wide rural-card" data-date={new Date().toLocaleDateString()}>
      <h2>{t("Are my papers ready?", "क्या मेरे काग़ज़ तैयार हैं?")}</h2>
      <Waiting tool="docs" />
      <p className="muted">{t("Pick the schemes, tick what you already have. I tell you the one thing to fix first.", "योजनाएँ चुनिए, और जो काग़ज़ आपके पास हैं उन पर निशान लगाइए। मैं बताऊँगा सबसे पहले क्या ठीक करना है।")}</p>
      <h3>{t("1. Schemes I want", "1. मुझे ये योजनाएँ चाहिए")}</h3>
      <div className="rural-checks">{catalog.map((c) => <label key={c.id} className="rural-check"><input type="checkbox" checked={picked.includes(c.id)} onChange={() => setPicked(toggle(picked, c.id))} />{c.name}</label>)}</div>
      <h3>{t("2. Papers I already have", "2. जो काग़ज़ मेरे पास हैं")}</h3>
      <div className="rural-checks">{(r?.all_docs ?? []).map((d) => <label key={d.id} className="rural-check"><input type="checkbox" checked={have.includes(d.id)} onChange={() => setHave(toggle(have, d.id))} />{d.name}</label>)}</div>
      {r && picked.length > 0 && (<>
        <div className={`rural-big ${r.steps.length ? "amber" : "green"}`}><span style={{ fontSize: 22 }}>{r.summary}</span></div>
        {r.steps.length > 0 && <ol className="rural-steps">{r.steps.map((s) => <li key={s.id}><b>{s.name}</b><span className="tag">{t(`blocks ${s.blocks}`, `${s.blocks} में रुकावट`)}</span><p>{s.how}</p></li>)}</ol>}
        <div className="rural-schemes">{r.schemes.map((s) => (
          <article key={s.id} className={`rural-scheme ${s.ready ? "likely" : "maybe"}`}><header><b>{s.name}</b><span className="tag">{s.have}/{s.total}</span></header>
            {s.ready ? <small>{t("Ready to apply", "आवेदन के लिए तैयार")}</small> : <small>{t("Missing: ", "कमी: ")}{s.missing.join(", ")}</small>}</article>))}</div>
        <p className="rural-note">{r.tip}</p>
        <Say text={r.summary} />
      </>)}
      {picked.length === 0 && <p className="rural-note">{t("Pick at least one scheme above (or use \"Which schemes\" first).", "ऊपर से कम से कम एक योजना चुनिए (या पहले \"कौन सी योजनाएँ\" चलाइए)।")}</p>}
    </section>
  );
}

/* ------------------------------------------------------------------ C1 income */
type Plan = { headline: string; band: string; income_year: number; cost_year: number; net_year: number; short_months: string[]; peak_shortfall: number;
  borrow_cost: number; emergency_target: number; tips: string[]; note: string;
  months: { m: string; income: number; cost: number; balance: number }[]; plan: { month: string; text: string }[] };
type Row = { month: number; amount: string; label: string };
const MON_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MON_HI = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"];

function Rows({ rows, setRows, hint }: { rows: Row[]; setRows: (r: Row[]) => void; hint: string }) {
  const { t, hi } = useT(); const names = hi ? MON_HI : MON_EN;
  return (<div className="rural-rows">
    {rows.map((r, i) => (
      <div key={i} className="rural-row">
        <select value={r.month} onChange={(e) => setRows(rows.map((x, j) => j === i ? { ...x, month: Number(e.target.value) } : x))}>{names.map((n, m) => <option key={m} value={m + 1}>{n}</option>)}</select>
        <input inputMode="numeric" placeholder="₹" value={r.amount} onChange={(e) => setRows(rows.map((x, j) => j === i ? { ...x, amount: e.target.value } : x))} />
        <input placeholder={hint} value={r.label} onChange={(e) => setRows(rows.map((x, j) => j === i ? { ...x, label: e.target.value } : x))} />
        <button className="btn ghost sm" aria-label="remove" onClick={() => setRows(rows.filter((_, j) => j !== i))}>✕</button>
      </div>))}
    <button className="btn ghost sm" onClick={() => setRows([...rows, { month: 1, amount: "", label: "" }])}>+ {t("Add", "जोड़ें")}</button>
  </div>);
}

function IncomeTool({ init }: { init: Record<string, string> }) {
  const { t } = useT(); const lang = useLang((s) => s.lang);
  const guided = init.tool === "income";
  const waiting = useWaiting("income");
  const [inc, setInc] = useState<Row[]>(() => guided ? fromJSON<{ month: number; amount: number }[]>(init.income, []).map((r) => ({ month: r.month, amount: String(r.amount), label: "" })) : store.get("inc", [{ month: 10, amount: "120000", label: "Kharif harvest" }, { month: 4, amount: "60000", label: "Rabi harvest" }]));
  const [out, setOut] = useState<Row[]>(() => guided ? fromJSON<{ month: number; amount: number }[]>(init.out, []).map((r) => ({ month: r.month, amount: String(r.amount), label: "" })) : store.get("out", [{ month: 6, amount: "20000", label: "Seed and fertiliser" }, { month: 7, amount: "10000", label: "School fees" }]));
  const [cost, setCost] = useState(() => (guided ? (init.cost ? String(Number(init.cost)) : "") : store.get("cost", "8000")));
  const [sav, setSav] = useState(() => store.get("sav", "0"));
  useEffect(() => { if (guided) return; store.set("inc", inc); store.set("out", out); store.set("cost", cost); store.set("sav", sav); }, [inc, out, cost, sav]);
  const clean = (rows: Row[]) => rows.filter((r) => Number(r.amount) > 0).map((r) => ({ month: r.month, amount: Number(r.amount), label: r.label }));
  const r = usePost<Plan>("/rural/income", { income: clean(inc), monthly_cost: Number(cost) || 0, one_offs: clean(out), savings: Number(sav) || 0, lang }, !waiting && clean(inc).length > 0 && Number(cost) > 0);
  const max = useMemo(() => Math.max(1, ...(r?.months ?? []).flatMap((m) => [Math.abs(m.balance)])), [r]);
  return (
    <section className="card wide rural-card" data-date={new Date().toLocaleDateString()}>
      <h2>{t("Plan my money around harvest and wage seasons", "फ़सल और मज़दूरी के मौसम के हिसाब से पैसे की योजना")}</h2>
      <Waiting tool="income" />
      <p className="muted">{t("Tell me when money comes in and what you must spend. I show which months you run short and how much to keep aside from each good month.", "बताइए पैसा कब आता है और क्या ख़र्च करना ही है। मैं दिखाऊँगा किन महीनों में कमी पड़ती है और हर अच्छे महीने में से कितना अलग रखना है।")}</p>
      <h3>{t("Money that comes in (harvest, sale, wages in bulk)", "जो पैसा आता है (फ़सल, बिक्री, एकमुश्त मज़दूरी)")}</h3>
      <Rows rows={inc} setRows={setInc} hint={t("what it is", "यह क्या है")} />
      <div className="rural-form">
        <label>{t("Normal cost of living every month (₹)", "हर महीने का सामान्य ख़र्च (₹)")}<input inputMode="numeric" value={cost} onChange={(e) => setCost(e.target.value)} /></label>
        <label>{t("Savings you have today (₹)", "आज आपकी बचत (₹)")}<input inputMode="numeric" value={sav} onChange={(e) => setSav(e.target.value)} /></label>
      </div>
      <h3>{t("Big one-time costs (seed, fees, wedding, festival)", "बड़े एकमुश्त ख़र्च (बीज, फ़ीस, शादी, त्योहार)")}</h3>
      <Rows rows={out} setRows={setOut} hint={t("what it is", "यह क्या है")} />
      {r && (<>
        <div className={`rural-big ${r.band}`}><span style={{ fontSize: 20 }}>{r.headline}</span></div>
        <div className="rural-bars" role="img" aria-label="balance by month">
          {r.months.map((m) => (
            <div key={m.m} className="rural-bar">
              <div className="col"><i className={m.balance < 0 ? "neg" : "pos"} style={{ height: `${Math.min(100, Math.abs(m.balance) / max * 100)}%` }} /></div>
              <small>{m.m}</small><small className={m.balance < 0 ? "bad" : ""}>{m.balance < 0 ? "-" : ""}{Math.abs(m.balance) >= 1000 ? Math.round(Math.abs(m.balance) / 1000) + "k" : Math.abs(m.balance)}</small>
            </div>))}
        </div>
        <p className="rural-note">{t("Bars: money left at the end of each month if you spend as you go. Red means you are out of money.", "बार: अगर आप ज़रूरत के हिसाब से ख़र्च करते चलें तो हर महीने के अंत में बचा पैसा। लाल यानी पैसा ख़त्म।")}</p>
        {r.plan.length > 0 && <><h3>{t("What to keep aside", "क्या अलग रखें")}</h3><ul className="rural-flags good">{r.plan.map((p) => <li key={p.month}>{p.text}</li>)}</ul></>}
        <h3>{t("What to do", "क्या करें")}</h3>
        <ul className="rural-flags good">{r.tips.map((x) => <li key={x}>{x}</li>)}</ul>
        <p className="rural-note">{r.note}</p>
        <Say text={`${r.headline} ${r.tips[0] ?? ""}`} />
      </>)}
    </section>
  );
}

/* ------------------------------------------------------------------ page */
export default function Rural() {
  const { t } = useT();
  const params = useMemo(() => Object.fromEntries(hashParams().entries()), []);
  const [tool, setTool] = useState<Tool>((params.tool as Tool) || store.get("tool", "loan"));
  const [picked, setPicked] = useState<string[]>(() => (params.tool === "docs" && params.schemes ? params.schemes.split(",").filter(Boolean) : store.get("picked", [])));
  const top = useRef<HTMLDivElement>(null);
  useEffect(() => store.set("tool", tool), [tool]);
  useEffect(() => store.set("picked", picked), [picked]);
  const TABS: [Tool, string, string, string][] = [
    ["loan", "💰", "Moneylender check", "साहूकार का हिसाब"], ["scheme", "🔍", "Is this offer real?", "क्या ऑफ़र असली है?"],
    ["schemes", "🏛️", "My government schemes", "मेरी सरकारी योजनाएँ"], ["docs", "📄", "Are my papers ready?", "काग़ज़ तैयार हैं?"], ["income", "🌾", "Plan my year", "मेरा साल"], ["policy", "🧾", "Is my policy good?", "क्या मेरी पॉलिसी अच्छी है?"], ["upi", "📲", "UPI safety", "UPI सुरक्षा"], ["dbt", "💸", "Why no money?", "पैसा क्यों नहीं आया?"], ["hold", "📦", "Sell or hold?", "बेचें या रोकें?"], ["saving", "🐷", "Daily saving", "रोज़ की बचत"], ["shg", "📒", "Group ledger", "समूह की बही"], ["credit", "🏦", "Credit score", "क्रेडिट स्कोर"],
  ];
  return (
    <Page title="Rural" lead={t("Practical tools for farming and daily-wage families: stop paying too much, stop missing what you are owed, and plan money that comes in lumps.",
      "खेती और दिहाड़ी वाले परिवारों के लिए काम के औज़ार: ज़्यादा ब्याज देना बंद कीजिए, अपना हक़ मत छोड़िए, और एकमुश्त आने वाले पैसे की योजना बनाइए।")}>
      <OfflineBar />
      <div ref={top} className="rural-tabs" role="tablist">
        {TABS.map(([id, ic, en, hi]) => <button key={id} role="tab" aria-selected={tool === id} className={tool === id ? "on" : ""} onClick={() => setTool(id)}><span aria-hidden>{ic}</span>{t(en, hi)}</button>)}
      </div>
      <div className="grid">
        {tool === "loan" && <LoanTool init={params} />}
        {tool === "scheme" && <SchemeTool init={params} />}
        {tool === "schemes" && <SchemesTool init={params} onPick={(ids) => { setPicked(ids); setTool("docs"); window.scrollTo(0, 0); }} />}
        {tool === "docs" && <DocsTool picked={picked} setPicked={setPicked} init={params} />}
        {tool === "income" && <IncomeTool init={params} />}
        {tool === "policy" && <PolicyTool init={params} />}
        {tool === "upi" && <UpiTool init={params} />}
        {tool === "dbt" && <DbtTool init={params} />}
        {tool === "hold" && <HoldTool init={params} />}
        {tool === "saving" && <SavingTool init={params} />}
        {tool === "shg" && <ShgTool />}
        {tool === "credit" && <CreditTool init={params} />}
      </div>
    </Page>
  );
}
