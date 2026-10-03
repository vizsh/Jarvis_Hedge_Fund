import { PanicSim } from "./Demos";
import { useEffect, useState } from "react";

import { Page } from "./Page";
import { WatchlistPanel } from "../components/Watchlist";
import { useStore } from "../lib/store";

const inr = (v: number) => `₹${Math.round(Math.abs(v)).toLocaleString("en-IN")}`;

const SAMPLES = [
  { label: "A typical scam tip",
    text: "🚀 SURE SHOT 10x multibagger! TCS profit up 300%, target Rs 9000. Buy now before Monday, insider news. Join my VIP telegram t.me/xyz. 100% guaranteed returns." },
  { label: "A claim that doesn't match the data",
    text: "Infosys profit surged 80% last quarter, great time to buy. Target Rs 2500." },
  { label: "A calm, ordinary note",
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
      {arc(0, 33, "#22ffa0")}{arc(33, 66, "#ffb020")}{arc(66, 100, "#ff476b")}
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
      <h2>Check a stock tip</h2>
      <p className="muted">Paste something from Telegram, WhatsApp or Instagram. It is checked against
        dated company data on this machine — no AI opinion involved.</p>
      <textarea id="tip-text" className="tip-box" rows={5} value={text}
                placeholder="Paste the tip here…" onChange={(e) => setText(e.target.value)} />
      <div className="row">
        <button className="btn go" disabled={busy || !text.trim()} onClick={() => run()}>
          {busy ? "Checking…" : "Check this tip"}
        </button>
        <span className="muted small">or try:</span>
        {SAMPLES.map((s) => (
          <button key={s.label} className="chip" onClick={() => { setText(s.text); void run(s.text); }}>
            {s.label}
          </button>
        ))}
      </div>

      {res && !res.empty && (
        <div className="scan-result">
          <RiskGauge score={res.score} />
          <Highlighted text={text} flags={res.flags} />
          <div className={`vbanner ${res.tone}`}>
            <div className="v-label">{res.verdict}</div>
            <div className="v-score">Risk score <b>{res.score}</b>/100</div>
          </div>
          <p className="summary">{res.summary}</p>

          {!!res.flags.length && (
            <>
              <h3>Scam-style tactics found</h3>
              {res.flags.map((f: any) => (
                <div className="flagrow" key={f.code}>
                  <div><b>{f.label}</b> — <code>“{f.quote}”</code></div>
                  <div className="muted small">{f.why}</div>
                </div>
              ))}
            </>
          )}

          {!!res.claims.length && (
            <>
              <h3>Claims we could test</h3>
              {res.claims.map((c: any, i: number) => (
                <div className="claimrow" key={i}>
                  <span className={`pill ${c.status}`}>{c.status}</span>
                  <div>
                    <div><b>“{c.text}”</b></div>
                    <div className="muted small">{c.evidence}</div>
                    {c.source && <div className="faint small">Source: {c.source}</div>}
                  </div>
                </div>
              ))}
            </>
          )}

          {!!res.companies.length && (
            <>
              <h3>What our data says about {res.companies.map((c: any) => c.name).join(", ")}</h3>
              {res.companies.map((c: any) => c.evidence.map((e: string, i: number) =>
                <div className="muted small" key={c.ticker + i}>{c.name}: {e}</div>))}
            </>
          )}
          <p className="faint small">{res.disclaimer}</p>
        </div>
      )}
    </section>
  );
}

/* ------------------------------------------------------------ tax shield */
function TaxShield() {
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
    setMsg(j.ok ? "Saved." : (j.reason ?? "Could not save."));
    if (j.ok) { setForm({ ticker: "", price: "", date: "" }); void load(); }
  };

  if (!d) return <section className="card"><h2>Tax shield</h2><p className="muted">Loading…</p></section>;
  return (
    <section className="card">
      <h2>Tax shield</h2>
      <p className="muted">Shares sold within a year are taxed at 20%; after a year, 12.5%. For each holding:
        what selling today costs, and what waiting would save.</p>
      <div className="bigstat">
        <div className="bs-n">{inr(d.total_saving)}</div>
        <div className="bs-l">you could save by waiting on holdings close to the one-year mark</div>
      </div>
      {d.sample && (
        <p className="faint small">These purchase dates are examples for the sample portfolio. Cost basis is
          something only you know, so for your own holdings add it below — it is never guessed.</p>
      )}
      <div className="tablewrap">
        <table className="tbl">
          <thead><tr><th>Holding</th><th>Held</th><th>Gain</th><th>Tax if sold today</th><th>What to do</th></tr></thead>
          <tbody>
            {d.rows.map((r: any) => (
              <tr key={r.ticker}>
                <td><b>{r.name}</b><div className="faint small">{r.shares} shares</div></td>
                <td>
                  {r.held_days != null ? (
                    <>
                      <div className="holdbar"><span style={{ width: `${Math.min(100, (r.held_days / 365) * 100)}%` }} /></div>
                      <div className="faint small">{r.held_days} of 365 days</div>
                    </>
                  ) : "—"}
                </td>
                <td className={r.gain < 0 ? "neg" : ""}>{r.gain != null ? (r.gain < 0 ? "-" : "") + inr(r.gain) : "—"}</td>
                <td>{r.tax_now != null ? inr(r.tax_now) : "—"}</td>
                <td><span className={`pill s-${r.status}`}>{r.status.replace("_", " ")}</span>
                  <div className="small">{r.action}</div></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="row addlot">
        <input id="lot-ticker" placeholder="Company (e.g. Wipro)" value={form.ticker}
               onChange={(e) => setForm({ ...form, ticker: e.target.value })} />
        <input id="lot-price" type="number" placeholder="Price you paid" value={form.price}
               onChange={(e) => setForm({ ...form, price: e.target.value })} />
        <input id="lot-date" type="date" value={form.date}
               onChange={(e) => setForm({ ...form, date: e.target.value })} />
        <button className="btn" disabled={!form.ticker || !form.price || !form.date} onClick={add}>Add purchase</button>
        {msg && <span className="muted small">{msg}</span>}
      </div>
      <p className="faint small">{d.caveat}</p>
    </section>
  );
}

export default function Protect() {
  return (
    <Page title="Protect" lead="Catch scams before they cost you, and stop paying tax you didn't need to.">
      <div className="grid g2">
        <TipScanner />
        <TaxShield />
      </div>
      <div className="grid"><PanicSim /></div>
      <div className="grid"><WatchlistPanel /></div>
    </Page>
  );
}
