import { PanicSim } from "./Demos";
import { ToolDeck, type Tool } from "../components/ToolDeck";
import { hashParams } from "../lib/router";
import { RecoveryCoach } from "./Recovery";
import { useEffect, useState } from "react";

import { Page } from "./Page";
import { WatchlistPanel } from "../components/Watchlist";
import { useStore } from "../lib/store";
import { useT } from "../lib/i18n";

const CLAIM_HI: Record<string, string> = { SUPPORTED: "सही निकला", CONTRADICTED: "ग़लत निकला", UNVERIFIED: "जाँचा नहीं जा सका" };
const STATUS_HI: Record<string, string> = { WAIT: "रुकिए", SHORT_TERM: "कम अवधि", LONG_TERM: "लंबी अवधि", LOSS: "घाटा", NO_BASIS: "भाव दर्ज नहीं" };

const inr = (v: number) => `₹${Math.round(Math.abs(v)).toLocaleString("en-IN")}`;

const SAMPLES = [
  { label: "A typical scam tip", hi: "ठगी वाली एक आम टिप",
    text: "🚀 SURE SHOT 10x multibagger! TCS profit up 300%, target Rs 9000. Buy now before Monday, insider news. Join my VIP telegram t.me/xyz. 100% guaranteed returns." },
  { label: "A claim that doesn't match the data", hi: "डेटा से न मिलने वाला दावा",
    text: "Infosys profit surged 80% last quarter, great time to buy. Target Rs 2500." },
  { label: "A calm, ordinary note", hi: "एक शांत, सामान्य नोट",
    text: "HDFC Bank reported steady results. Reasonable to hold for the long term if you are diversified." },
];

/* ------------------------------------------------------------ tip scanner */
function RiskGauge({ score }: { score: number }) {
  const [shown, setShown] = useState(0);
  useEffect(() => { const t = setTimeout(() => setShown(score), 60); return () => clearTimeout(t); }, [score]);
  const ang = -90 + (Math.max(0, Math.min(100, shown)) / 100) * 180;
  const arc = (a: number, b: number, c: string) => {
    const p = (t: number) => [100 + 80 * Math.cos(Math.PI * (1 - t / 100)), 100 - 80 * Math.sin(Math.PI * (1 - t / 100))];
    const [x1, y1] = p(a), [x2, y2] = p(b);
    return <path d={`M${x1} ${y1} A80 80 0 0 1 ${x2} ${y2}`} stroke={c} strokeWidth="14" fill="none" />;
  };
  return (
    <svg viewBox="0 0 200 118" className="gauge" role="img" aria-label={`Risk ${score} out of 100`}>
      {arc(0, 33, "#62d2a2")}{arc(33, 66, "#ff9f5a")}{arc(66, 100, "#ff7a70")}
      <g className="needle" style={{ transform: `rotate(${ang}deg)` }}>
        <line x1="100" y1="100" x2="100" y2="34" stroke="#fff" strokeWidth="3" strokeLinecap="round" />
      </g>
      <circle cx="100" cy="100" r="6" fill="#fff" />
      <text x="100" y="116" textAnchor="middle" fontSize="13" fill="#fff">{score}/100</text>
    </svg>
  );
}

function Highlighted({ text, flags }: { text: string; flags: any[] }) {
  const quotes = flags.map((f) => f.quote).filter(Boolean);
  if (!quotes.length) return null;
  const esc = quotes.map((q: string) => q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
  const parts = text.split(new RegExp(`(${esc})`, "i"));
  return (
    <div className="tiphl" aria-label="Tip with scam-style phrases marked">
      {parts.map((p, i) => (i % 2 ? <mark key={i}>{p}</mark> : <span key={i}>{p}</span>))}
    </div>
  );
}

function TipScanner() {
  const { hi, t, d } = useT();
  const [text, setText] = useState("");
  const [res, setRes] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const run = async (t = text) => {
    if (!t.trim()) return;
    setBusy(true);
    try {
      const r = await fetch("/scan", { method: "POST", headers: { "Content-Type": "application/json" },
                                       body: JSON.stringify({ text: t }) });
      setRes(await r.json());
    } finally { setBusy(false); }
  };

  return (
    <section className="card">
      <h2>{t("Check a stock tip", "स्टॉक टिप जाँचिए")}</h2>
      <p className="muted">{t("Paste something from Telegram, WhatsApp or Instagram. A panel of specialists reads what the tip is really suggesting, then tests it against price, company numbers, market facts and the rules. Numbers come from code and dated data.", "टेलीग्राम, व्हाट्सऐप या इंस्टाग्राम से कुछ चिपकाइए। इसे इसी मशीन पर दर्ज तारीख़ वाले कंपनी डेटा से परखा जाता है — कोई AI राय शामिल नहीं।")}</p>
      {hi && <p className="faint small">ध्यान दें: टिप का पाठ अंग्रेज़ी में होना चाहिए; जाँचने वाले नियम अंग्रेज़ी शब्दों पर चलते हैं।</p>}
      <textarea id="tip-text" className="tip-box" rows={5} value={text}
                placeholder={t("Paste the tip here…", "टिप यहाँ चिपकाइए…")} onChange={(e) => setText(e.target.value)} />
      <div className="row">
        <button className="btn go" disabled={busy || !text.trim()} onClick={() => run()}>
          {busy ? t("Checking…", "जाँच रहा हूँ…") : t("Check this tip", "यह टिप जाँचिए")}
        </button>
        <span className="muted small">{t("or try:", "या आज़माइए:")}</span>
        {SAMPLES.map((s) => (
          <button key={s.label} className="chip" onClick={() => { setText(s.text); void run(s.text); }}>
            {hi ? s.hi : s.label}
          </button>
        ))}
      </div>

      {res && !res.empty && (
        <div className="scan-result">
          <RiskGauge score={res.score} />
          <Highlighted text={text} flags={res.flags} />
          <div className={`vbanner ${res.tone}`}>
            <div className="v-label">{d(res.verdict)}</div>
            <div className="v-score">{t("Risk score", "जोखिम स्कोर")} <b>{res.score}</b>/100</div>
          </div>
          <p className="summary">{d(res.summary)}</p>

          {res.agents && (
            <div className="panel-tip">
              <div className="pt-meters">
                <div><b>{res.scam_likelihood}%</b><span>{t("chance it is a scam", "ठगी की संभावना")}</span></div>
                <div><b>{res.reliability}/100</b><span>{t("real backing for the idea", "विचार के पीछे असली आधार")}</span></div>
              </div>
              {res.reading?.summary && <p className="pt-read"><b>{t("What it is suggesting:", "यह क्या सुझाता है:")}</b> {res.reading.summary} <small>({res.reading.how === "model+rules" ? t("read by the local model and checked against the text", "लोकल मॉडल ने समझा और पाठ से मिलाया") : t("read by rules", "नियमों से समझा")})</small></p>}
              <h3>{t("What each specialist found", "हर विशेषज्ञ ने क्या पाया")}</h3>
              {res.agents.map((a: any) => (
                <details className={`pt-agent ${a.stance}`} key={a.agent} open={a.stance === "against"}>
                  <summary><i>{a.stance === "against" ? t("Against", "ख़िलाफ़") : a.stance === "for" ? t("For", "पक्ष में") : a.stance === "neutral" ? t("Neutral", "तटस्थ") : t("Cannot tell", "पता नहीं")}</i> <b>{a.agent}</b>: {a.headline}</summary>
                  <p>{a.reasoning}</p>
                </details>))}
              {!!res.reliability_reasons?.length && <p className="faint small">{t("How the backing score was reached", "आधार का अंक कैसे बना")}: {res.reliability_reasons.join("; ")}</p>}
              <h3>{t("What to do", "क्या करें")}</h3>
              <ol className="pt-steps">{res.steps.map((x: string) => <li key={x}>{x}</li>)}</ol>
            </div>)}

          {!!res.flags.length && (
            <>
              <h3>{t("Scam-style tactics found", "ठगी जैसी चालें मिलीं")}</h3>
              {res.flags.map((f: any) => (
                <div className="flagrow" key={f.code}>
                  <div><b>{d(f.label)}</b> — <code>“{f.quote}”</code></div>
                  <div className="muted small">{d(f.why)}</div>
                </div>
              ))}
            </>
          )}

          {!!res.claims.length && (
            <>
              <h3>{t("Claims we could test", "जिन दावों को हम परख सके")}</h3>
              {res.claims.map((c: any, i: number) => (
                <div className="claimrow" key={i}>
                  <span className={`pill ${c.status}`}>{hi ? CLAIM_HI[c.status] ?? c.status : c.status}</span>
                  <div>
                    <div><b>“{c.text}”</b></div>
                    <div className="muted small">{d(c.evidence)}</div>
                    {c.source && <div className="faint small">{t("Source", "स्रोत")}: {c.source}</div>}
                  </div>
                </div>
              ))}
            </>
          )}

          {!!res.companies.length && (
            <>
              <h3>{t("What our data says about", "हमारा डेटा इनके बारे में क्या कहता है")} {res.companies.map((c: any) => c.name).join(", ")}</h3>
              {res.companies.map((c: any) => c.evidence.map((e: string, i: number) =>
                <div className="muted small" key={c.ticker + i}>{c.name}: {d(e)}</div>))}
            </>
          )}
          <p className="faint small">{d(res.disclaimer)}</p>
        </div>
      )}
    </section>
  );
}

/* ------------------------------------------------------------ tax shield */
function TaxShield() {
  const { hi, t, d: dt } = useT();
  const [d, setD] = useState<any>(null);
  const fund = useStore((s) => s.fund);
  const [form, setForm] = useState({ ticker: "", price: "", date: "" });
  const [msg, setMsg] = useState("");

  const load = () => fetch("/tax/shield").then((r) => r.json()).then(setD).catch(() => {});
  useEffect(() => { load(); }, [fund?.portfolio_id, fund?.nav]);

  const add = async () => {
    const r = await fetch("/lots", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticker: form.ticker, shares: 0, buy_price: Number(form.price), buy_date: form.date }) });
    const j = await r.json();
    setMsg(j.ok ? t("Saved.", "सहेज लिया।") : (dt(j.reason) || t("Could not save.", "सहेज नहीं सका।")));
    if (j.ok) { setForm({ ticker: "", price: "", date: "" }); void load(); }
  };

  if (!d) return <section className="card"><h2>{t("Tax shield", "टैक्स ढाल")}</h2><p className="muted">{t("Loading…", "लोड हो रहा है…")}</p></section>;
  return (
    <section className="card">
      <h2>{t("Tax shield", "टैक्स ढाल")}</h2>
      <p className="muted">{t("Shares sold within a year are taxed at 20%; after a year, 12.5%. For each holding: what selling today costs, and what waiting would save.", "एक साल के भीतर बेचे शेयरों पर 20% टैक्स लगता है; एक साल के बाद 12.5%। हर शेयर के लिए: आज बेचने पर कितना ख़र्च, और रुकने पर कितना बचत।")}</p>
      <div className="bigstat">
        <div className="bs-n">{inr(d.total_saving)}</div>
        <div className="bs-l">{t("you could save by waiting on holdings close to the one-year mark", "एक साल के क़रीब वाले शेयरों पर रुकने से आप इतना बचा सकते हैं")}</div>
      </div>
      {d.sample && (
        <p className="faint small">{t("These purchase dates are examples for the sample portfolio. Cost basis is something only you know, so for your own holdings add it below — it is never guessed.", "ये ख़रीद तारीख़ें नमूना पोर्टफ़ोलियो के उदाहरण हैं। ख़रीद की लागत सिर्फ़ आप जानते हैं, इसलिए अपने शेयरों की नीचे जोड़िए — उसका अंदाज़ा कभी नहीं लगाया जाता।")}</p>
      )}
      <div className="tablewrap">
        <table className="tbl">
          <thead><tr><th>{t("Holding", "शेयर")}</th><th>{t("Held", "रखा")}</th><th>{t("Gain", "मुनाफ़ा")}</th><th>{t("Tax if sold today", "आज बेचें तो टैक्स")}</th><th>{t("What to do", "क्या करें")}</th></tr></thead>
          <tbody>
            {d.rows.map((r: any) => (
              <tr key={r.ticker}>
                <td><b>{r.name}</b><div className="faint small">{r.shares} {t("shares", "शेयर")}</div></td>
                <td>
                  {r.held_days != null ? (
                    <>
                      <div className="holdbar"><span style={{ width: `${Math.min(100, (r.held_days / 365) * 100)}%` }} /></div>
                      <div className="faint small">{hi ? `365 में से ${r.held_days} दिन` : `${r.held_days} of 365 days`}</div>
                    </>
                  ) : "—"}
                </td>
                <td className={r.gain < 0 ? "neg" : ""}>{r.gain != null ? (r.gain < 0 ? "-" : "") + inr(r.gain) : "—"}</td>
                <td>{r.tax_now != null ? inr(r.tax_now) : "—"}</td>
                <td><span className={`pill s-${r.status}`}>{hi ? STATUS_HI[r.status] ?? r.status : r.status.replace("_", " ")}</span>
                  <div className="small">{dt(r.action)}</div></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="row addlot">
        <input id="lot-ticker" placeholder={t("Company (e.g. Wipro)", "कंपनी (जैसे Wipro)")} value={form.ticker}
               onChange={(e) => setForm({ ...form, ticker: e.target.value })} />
        <input id="lot-price" type="number" placeholder={t("Price you paid", "आपने जो भाव दिया")} value={form.price}
               onChange={(e) => setForm({ ...form, price: e.target.value })} />
        <input id="lot-date" type="date" value={form.date}
               onChange={(e) => setForm({ ...form, date: e.target.value })} />
        <button className="btn" disabled={!form.ticker || !form.price || !form.date} onClick={add}>{t("Add purchase", "ख़रीद जोड़ें")}</button>
        {msg && <span className="muted small">{msg}</span>}
      </div>
      <p className="faint small">{dt(d.caveat)}</p>
    </section>
  );
}

export default function Protect() {
  const { t } = useT();
  const prm = hashParams();
  const start = ({ recovery: "recovery", tip: "tip", tax: "tax", panic: "panic", watch: "watch" } as Record<string, string>)[prm.get("tool") ?? ""] ?? (prm.get("type") ? "recovery" : prm.get("episode") ? "panic" : "recovery");
  const [tool, setTool] = useState(start);
  const TOOLS: Tool[] = [
    { id: "recovery", icon: "lifebuoy", tone: "urgent", title: t("I think I was scammed", "मुझे लगता है ठगी हुई"), blurb: t("The first hour, in order, with the words to say", "पहला घंटा, क्रम से, बोलने के शब्दों के साथ") },
    { id: "tip", icon: "tip", title: t("Check a stock tip", "स्टॉक टिप जाँचें"), blurb: t("Paste a Telegram or WhatsApp tip and test its facts", "टेलीग्राम या व्हाट्सऐप की टिप डालकर उसके तथ्य जाँचें") },
    { id: "tax", icon: "loan", title: t("Tax shield", "टैक्स बचत"), blurb: t("When waiting a few days would cost you less tax", "कुछ दिन रुकने पर कब कम टैक्स लगेगा") },
    { id: "panic", icon: "trend", title: t("Panic-sell replay", "घबराकर बेचने का असर"), blurb: t("What selling in a past crash would have cost", "पिछली गिरावट में बेचने की क़ीमत क्या होती") },
    { id: "watch", icon: "bell", title: t("Tell me if…", "बताइए अगर…"), blurb: t("Standing rules that speak up only when something flips", "स्थायी नियम जो सिर्फ़ तब बोलते हैं जब कुछ पलटे") },
  ];
  return (
    <Page title="Protect" lead={t("Catch scams before they cost you, and stop paying tax you didn't need to.", "ठगी को पैसे ख़र्च कराने से पहले पकड़िए, और जो टैक्स देना ज़रूरी नहीं था, उसे देना बंद कीजिए।")}>
      <ToolDeck tools={TOOLS} active={tool} onPick={setTool} label={t("Protection tools", "सुरक्षा के औज़ार")}>
        {tool === "recovery" && <div className="grid"><RecoveryCoach /></div>}
        {tool === "tip" && <div className="grid"><TipScanner /></div>}
        {tool === "tax" && <div className="grid"><TaxShield /></div>}
        {tool === "panic" && <div className="grid"><PanicSim /></div>}
        {tool === "watch" && <div className="grid"><WatchlistPanel /></div>}
      </ToolDeck>
    </Page>
  );
}
