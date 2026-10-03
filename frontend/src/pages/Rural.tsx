import { useEffect, useMemo, useRef, useState } from "react";

import "../styles-rural.css";
import { Page } from "./Page";
import { hashParams } from "../lib/router";
import { useT } from "../lib/i18n";
import { useLang } from "../lib/lang";
import { speak } from "../lib/speak";

type Tool = "loan" | "scheme" | "schemes" | "docs" | "income";

const store = {
  get<T>(k: string, d: T): T { try { const v = localStorage.getItem("jarvis.rural." + k); return v ? JSON.parse(v) : d; } catch { return d; } },
  set(k: string, v: unknown) { try { localStorage.setItem("jarvis.rural." + k, JSON.stringify(v)); } catch { /* storage blocked */ } },
};

function usePost<T>(url: string, body: unknown, enabled = true, delay = 250): T | null {
  const [out, setOut] = useState<T | null>(null);
  const key = JSON.stringify(body);
  useEffect(() => {
    if (!enabled) { setOut(null); return; }
    const id = window.setTimeout(() => {
      fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: key })
        .then((r) => r.json()).then(setOut).catch(() => {});
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
  const [f, setF] = useState(() => store.get("loan", { principal: "50000", rate: "5", unit: "per100_month", months: "10", mode: "interest_only" }));
  useEffect(() => { if (init.principal) setF((o) => ({ ...o, principal: init.principal, rate: init.rate ?? o.rate, unit: init.unit ?? o.unit, months: init.months ?? o.months })); }, []); // eslint-disable-line
  useEffect(() => store.set("loan", f), [f]);
  const ok = Number(f.principal) > 0 && Number(f.rate) > 0 && Number(f.months) > 0;
  const r = usePost<Loan>("/rural/loan", { principal: Number(f.principal), rate: Number(f.rate), unit: f.unit, months: Number(f.months), mode: f.mode, lang }, ok);
  const set = (k: string) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  return (
    <section className="card wide rural-card">
      <h2>{t("What does the moneylender's interest really cost?", "साहूकार का ब्याज असल में कितना पड़ता है?")}</h2>
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
  const [text, setText] = useState(init.text ?? "");
  const [n, setN] = useState({ put: "", get: "", months: "" });
  const [go, setGo] = useState(!!init.text);
  const body = { text, put: n.put ? Number(n.put) : null, get: n.get ? Number(n.get) : null, months: n.months ? Number(n.months) : null, lang };
  const r = usePost<Offer>("/rural/scheme", body, go && (!!text.trim() || !!(n.put && n.get && n.months)), 0);
  const EX: [string, string, string][] = [
    ["Pay ₹10,000 now, get ₹20,000 in 6 months, guaranteed. Bring 3 friends and earn more. Only today!", "आज ही ₹10,000 लगाइए, 6 महीने में ₹20,000 पक्का। 3 दोस्तों को जोड़ें, और कमाएँ।", "A typical double-money offer"],
    ["Bank says our recurring deposit pays 6.8% a year, passbook and receipt provided.", "बैंक की आवर्ती जमा साल का 6.8% देती है, पासबुक और रसीद मिलेगी।", "An ordinary bank offer"],
  ];
  return (
    <section className="card wide rural-card">
      <h2>{t("Is this scheme or offer real?", "क्या यह योजना या ऑफ़र असली है?")}</h2>
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

/* ------------------------------------------------------------------ B1 schemes */
type Sch = { id: string; name: string; status: string; gives: string; who: string; where: string; link: string; cash_per_year: number; docs: string[]; doc_ids: string[] };
type Ent = { schemes: Sch[]; count: number; cash_per_year: number; note: string; checked: string };

const WORK: [string, string, string][] = [["farmer", "Farmer (own or rented land)", "किसान (अपनी या बटाई की ज़मीन)"], ["farm_labour", "Farm labourer", "खेत मज़दूर"], ["labour", "Daily-wage labourer", "दिहाड़ी मज़दूर"],
  ["vendor", "Street vendor / small trader", "फेरीवाला / छोटा व्यापारी"], ["artisan", "Artisan (carpenter, potter, weaver...)", "कारीगर (बढ़ई, कुम्हार, बुनकर...)"], ["business", "Small business owner", "छोटा कारोबारी"], ["other", "Something else", "कुछ और"]];

function SchemesTool({ onPick }: { onPick: (ids: string[]) => void }) {
  const { t } = useT(); const lang = useLang((s) => s.lang);
  const [p, setP] = useState(() => store.get("profile", { age: "35", gender: "male", land: "none", work: "labour", bank: true, taxpayer: false, poor: "unsure",
    category: "general", daughter: false, kutcha: false, disability: false, widow: false, student: false, shg: false, lpg: true }));
  const [go, setGo] = useState(false);
  useEffect(() => store.set("profile", p), [p]);
  const profile = { ...p, age: Number(p.age) || 0 };
  const r = usePost<Ent>("/rural/entitlements", { profile, lang }, go, 0);
  const chk = (k: keyof typeof p, en: string, hi: string) => <label className="rural-check"><input type="checkbox" checked={!!p[k]} onChange={(e) => { setP({ ...p, [k]: e.target.checked }); }} />{t(en, hi)}</label>;
  const sel = (k: keyof typeof p) => (e: { target: { value: string } }) => setP({ ...p, [k]: e.target.value });
  return (
    <section className="card wide rural-card">
      <h2>{t("Which government schemes am I missing?", "मुझे कौन सी सरकारी योजनाएँ मिल सकती हैं?")}</h2>
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

function DocsTool({ picked, setPicked }: { picked: string[]; setPicked: (x: string[]) => void }) {
  const { t } = useT(); const lang = useLang((s) => s.lang);
  const [have, setHave] = useState<string[]>(() => store.get("have", []));
  const [catalog, setCatalog] = useState<{ id: string; name: string }[]>([]);
  useEffect(() => store.set("have", have), [have]);
  useEffect(() => { fetch(`/rural/schemes?lang=${lang}`).then((r) => r.json()).then((x) => setCatalog(x.schemes)).catch(() => {}); }, [lang]);
  const r = usePost<Ready>("/rural/readiness", { schemes: picked, have, lang }, true, 100);
  const toggle = (arr: string[], v: string) => (arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);
  return (
    <section className="card wide rural-card">
      <h2>{t("Are my papers ready?", "क्या मेरे काग़ज़ तैयार हैं?")}</h2>
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

function IncomeTool() {
  const { t } = useT(); const lang = useLang((s) => s.lang);
  const [inc, setInc] = useState<Row[]>(() => store.get("inc", [{ month: 10, amount: "120000", label: "Kharif harvest" }, { month: 4, amount: "60000", label: "Rabi harvest" }]));
  const [out, setOut] = useState<Row[]>(() => store.get("out", [{ month: 6, amount: "20000", label: "Seed and fertiliser" }, { month: 7, amount: "10000", label: "School fees" }]));
  const [cost, setCost] = useState(() => store.get("cost", "8000"));
  const [sav, setSav] = useState(() => store.get("sav", "0"));
  useEffect(() => { store.set("inc", inc); store.set("out", out); store.set("cost", cost); store.set("sav", sav); }, [inc, out, cost, sav]);
  const clean = (rows: Row[]) => rows.filter((r) => Number(r.amount) > 0).map((r) => ({ month: r.month, amount: Number(r.amount), label: r.label }));
  const r = usePost<Plan>("/rural/income", { income: clean(inc), monthly_cost: Number(cost) || 0, one_offs: clean(out), savings: Number(sav) || 0, lang }, clean(inc).length > 0 && Number(cost) > 0);
  const max = useMemo(() => Math.max(1, ...(r?.months ?? []).flatMap((m) => [Math.abs(m.balance)])), [r]);
  return (
    <section className="card wide rural-card">
      <h2>{t("Plan my money around harvest and wage seasons", "फ़सल और मज़दूरी के मौसम के हिसाब से पैसे की योजना")}</h2>
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
  const [picked, setPicked] = useState<string[]>(() => store.get("picked", []));
  const top = useRef<HTMLDivElement>(null);
  useEffect(() => store.set("tool", tool), [tool]);
  useEffect(() => store.set("picked", picked), [picked]);
  const TABS: [Tool, string, string, string][] = [
    ["loan", "💰", "Moneylender check", "साहूकार का हिसाब"], ["scheme", "🔍", "Is this offer real?", "क्या ऑफ़र असली है?"],
    ["schemes", "🏛️", "My government schemes", "मेरी सरकारी योजनाएँ"], ["docs", "📄", "Are my papers ready?", "काग़ज़ तैयार हैं?"], ["income", "🌾", "Plan my year", "मेरा साल"],
  ];
  return (
    <Page title="Rural" lead={t("Practical tools for farming and daily-wage families: stop paying too much, stop missing what you are owed, and plan money that comes in lumps.",
      "खेती और दिहाड़ी वाले परिवारों के लिए काम के औज़ार: ज़्यादा ब्याज देना बंद कीजिए, अपना हक़ मत छोड़िए, और एकमुश्त आने वाले पैसे की योजना बनाइए।")}>
      <div ref={top} className="rural-tabs" role="tablist">
        {TABS.map(([id, ic, en, hi]) => <button key={id} role="tab" aria-selected={tool === id} className={tool === id ? "on" : ""} onClick={() => setTool(id)}><span aria-hidden>{ic}</span>{t(en, hi)}</button>)}
      </div>
      <div className="grid">
        {tool === "loan" && <LoanTool init={params} />}
        {tool === "scheme" && <SchemeTool init={params} />}
        {tool === "schemes" && <SchemesTool onPick={(ids) => { setPicked(ids); setTool("docs"); window.scrollTo(0, 0); }} />}
        {tool === "docs" && <DocsTool picked={picked} setPicked={setPicked} />}
        {tool === "income" && <IncomeTool />}
      </div>
    </Page>
  );
}
