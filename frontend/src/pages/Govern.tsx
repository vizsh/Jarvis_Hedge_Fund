import { TamperDemo } from "./Demos";
import { useEffect, useState } from "react";

import { Page } from "./Page";
import { useStore } from "../lib/store";

const inr = (v: number) => `₹${Math.round(Math.abs(v)).toLocaleString("en-IN")}`;
const pc = (v: number) => `${(v * 100).toFixed(1)}%`;
const post = (url: string, body?: unknown) =>
  fetch(url, { method: "POST", headers: { "Content-Type": "application/json" },
               body: body === undefined ? undefined : JSON.stringify(body) });

/* ------------------------------------------------------------ firewall */
function Firewall({ onStage }: { onStage: () => void }) {
  const [f, setF] = useState({ side: "BUY", ticker: "Persistent", shares: "30" });
  const [res, setRes] = useState<any>(null);

  const check = async (shares = f.shares, side = f.side, ticker = f.ticker) => {
    const r = await post("/firewall/check", { ticker, side, shares: Number(shares) });
    setRes(await r.json());
  };
  const stageRemedy = async () => {
    await post("/sandbox/stage", {
      origin: "firewall", note: "Largest size the firewall would approve",
      trades: [{ ticker: res.ticker, side: res.side, shares: res.remedy.max_shares, reason: "compliant counter-offer" }],
    });
    onStage();
  };

  return (
    <section className="card">
      <h2>Risk firewall</h2>
      <p className="muted">Try to place a trade. Plain arithmetic checks it against your limits — no AI is
        involved, so nothing can talk it into a bad order.</p>
      <div className="row">
        <select id="fw-side" value={f.side} onChange={(e) => setF({ ...f, side: e.target.value })}>
          <option>BUY</option><option>SELL</option>
        </select>
        <input id="fw-shares" type="number" min={1} value={f.shares} style={{ width: 90 }}
               onChange={(e) => setF({ ...f, shares: e.target.value })} />
        <span className="muted">shares of</span>
        <input id="fw-ticker" value={f.ticker} placeholder="company" style={{ flex: 1, minWidth: 120 }}
               onChange={(e) => setF({ ...f, ticker: e.target.value })} />
        <button className="btn go" onClick={() => check()}>Check</button>
      </div>
      <div className="row">
        <span className="faint small">Try:</span>
        {[["BUY", "Persistent", "30"], ["BUY", "TCS", "5"], ["SELL", "TCS", "9999"], ["BUY", "Nestle India", "10"]].map(([s, t, n]) => (
          <button key={t + n} className="chip" onClick={() => { setF({ side: s, ticker: t, shares: n }); void check(n, s, t); }}>
            {s.toLowerCase()} {n} {t}
          </button>
        ))}
      </div>

      {res && !res.ok && <p className="muted">{res.reason}</p>}
      {res?.ok && (
        <div className={`fw-result ${res.approved ? "ok" : "no"}`}>
          <div className="fw-badge">{res.approved ? "APPROVED" : "BLOCKED"}</div>
          <div className="fw-line">{res.side} {res.shares} × {res.name} at ₹{res.price.toLocaleString("en-IN")} = {inr(res.value)}</div>
          {res.violations.map((v: any, i: number) => (
            <div className="fw-viol" key={i}>
              <div>{v.message}</div>
              <div className="faint small">
                measured {typeof v.measured === "number" && v.measured < 5 ? pc(v.measured) : v.measured}
                {" · "}limit {typeof v.limit === "number" && v.limit < 5 ? pc(v.limit) : v.limit}
              </div>
            </div>
          ))}
          {res.approved && <div className="muted small">Within every limit: {res.policy}.</div>}
          {!res.approved && res.remedy && res.remedy.max_shares > 0 && (
            <div className="fw-remedy">
              <div>Largest order that fits your limits: <b>{res.remedy.max_shares} shares</b>.</div>
              <div className="faint small">{res.remedy.explanation}</div>
              <div className="row">
                <button className="btn" onClick={() => check(String(res.remedy.max_shares))}>Check that size</button>
                <button className="btn go" onClick={stageRemedy}>Preview it in the simulator ↓</button>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

/* ------------------------------------------------------------ rebalance simulator */
const FIELDS: [string, string, (v: any) => string][] = [
  ["score", "Score", (v) => String(Math.round(v))],
  ["grade", "Grade", (v) => String(v)],
  ["cash_pct", "Cash", pc],
  ["effective_holdings", "Behaves like", (v) => `${Number(v).toFixed(1)} stocks`],
  ["holdings", "Holdings", (v) => String(v)],
];

function RebalanceSim({ refreshKey, onBooked }: { refreshKey: number; onBooked: () => void }) {
  const [p, setP] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<any>(null);
  const fund = useStore((s) => s.fund);

  const loadStaged = () => fetch("/sandbox").then((r) => r.json()).then((j) => setP(j.staged ? j : null)).catch(() => {});
  useEffect(() => { void loadStaged(); }, [refreshKey, fund?.nav]);

  const build = async (deploy: boolean) => {
    setBusy(true);
    try {
      const j = await (await post(`/sandbox/from-rebalance?deploy=${deploy}`)).json();
      setP(j.staged ? j : { staged: false });
    } finally { setBusy(false); }
  };
  const discard = async () => { await post("/sandbox/discard"); setP(null); };
  const approve = async () => {
    setBusy(true);
    try {
      setDone(await (await post("/sandbox/commit")).json());
      setP(null);
      onBooked();
    } finally { setBusy(false); }
  };

  const col = (title: string, s: any, deltas?: any[]) => (
    <div className={`sim-col ${deltas ? "after" : ""}`}>
      <h3>{title}</h3>
      {FIELDS.map(([k, l, f]) => {
        const d = deltas?.find((x) => x.key === k);
        return <div className="kvr" key={k}><span>{l}</span><b className={d ? d.direction : ""}>{f(s[k])}</b></div>;
      })}
      <div className="kvr"><span>Biggest industry</span><b>{s.top_sector ? pc(s.top_sector[1]) : "—"}</b></div>
    </div>
  );

  return (
    <section className="card">
      <h2>Rebalance simulator</h2>
      <p className="muted">See your portfolio now next to what it would become — before anything is booked.
        Nothing here is real money: this is paper trading.</p>
      {!p && (
        <div className="row">
          <button className="btn go" disabled={busy} onClick={() => build(true)}>Build the smallest fix</button>
          <button className="btn" disabled={busy} onClick={() => build(false)}>Only sell, don't buy</button>
        </div>
      )}
      {p && p.staged === false && <p className="muted">Nothing to change — you are already inside every limit.</p>}
      {p?.staged && (
        <>
          <div className="sim">
            {col("Now", p.before)}
            <div className="sim-mid">
              {p.trades.map((t: any, i: number) => (
                <div className={`xfer ${t.side}`} key={i}>
                  <b>{t.side}</b> {t.shares} {t.name}<span>{inr(t.value)}</span>
                </div>
              ))}
              <div className="faint small">Trading cost about {inr(p.cost)}</div>
            </div>
            {col("After", p.after, p.deltas)}
          </div>
          <p className="verdict-line">{p.verdict}</p>
          {!!p.skipped?.length && <p className="faint small">Skipped: {p.skipped.join("; ")}</p>}
          <div className="row">
            <button className="btn go" disabled={busy} onClick={approve}>Approve and book on paper</button>
            <button className="btn ghost" disabled={busy} onClick={discard}>Throw it away</button>
          </div>
          <p className="faint small">Approving re-checks every trade against the firewall and writes it to the ledger.</p>
        </>
      )}

      {done && (
        <div className="modal-wrap" onClick={() => setDone(null)}>
          <div className="ok-modal" onClick={(e) => e.stopPropagation()}>
            <svg className="check" viewBox="0 0 52 52" aria-hidden="true">
              <circle className="check-c" cx="26" cy="26" r="23" fill="none" />
              <path className="check-p" fill="none" d="M14 27 l8 8 l16 -17" />
            </svg>
            <h3>{done.applied_count} trade{done.applied_count === 1 ? "" : "s"} booked on paper</h3>
            {done.applied?.map((t: any, i: number) => (
              <div className="small" key={i}>{t.side} {t.shares} {t.ticker?.replace(".NS", "")} · {inr(t.value)}</div>
            ))}
            {!!done.refused_count && <p className="small neg">{done.refused_count} refused by the firewall.</p>}
            <p className="faint small">Written to the append-only ledger.</p>
            <button className="btn go" onClick={() => setDone(null)}>Done</button>
          </div>
        </div>
      )}
    </section>
  );
}

/* ------------------------------------------------------------ ledger */
function Ledger({ refreshKey }: { refreshKey: number }) {
  const [d, setD] = useState<any>(null);
  const load = () => fetch("/ledger").then((r) => r.json()).then(setD).catch(() => {});
  useEffect(() => { void load(); }, [refreshKey]);
  if (!d) return null;
  return (
    <section className="card">
      <h2>Audit ledger</h2>
      <p className="muted">Every booked trade, in order. Each entry carries the fingerprint of the one before it,
        so editing history anywhere breaks the chain and shows up here.</p>
      <div className={`chain ${d.chain.ok ? "ok" : "bad"}`}>
        {d.chain.ok ? `✔ Chain intact — ${d.chain.entries} entr${d.chain.entries === 1 ? "y" : "ies"}`
                    : `✖ Chain broken at entry #${d.chain.broken_at}`}
        {d.chain.head && <code> head {d.chain.head}</code>}
        <button className="btn sm ghost" onClick={load}>Refresh</button>
      </div>
      {d.entries.length === 0 ? <p className="muted">No trades booked yet.</p> : (
        <div className="tablewrap"><table className="tbl">
          <thead><tr><th>#</th><th>When</th><th>Trade</th><th>Price</th><th>NAV after</th><th>Why</th><th>Fingerprint</th></tr></thead>
          <tbody>{d.entries.map((e: any) => (
            <tr key={e.id}>
              <td>{e.id}</td><td className="small">{String(e.ts).replace("T", " ").slice(0, 19)}</td>
              <td><b className={e.side === "SELL" ? "neg" : "pos"}>{e.side}</b> {e.shares} {e.ticker?.replace(".NS", "")}</td>
              <td>₹{Number(e.price).toLocaleString("en-IN")}</td><td>{inr(e.nav_after)}</td>
              <td className="small">{e.reason}</td><td><code>{String(e.hash).slice(0, 10)}</code></td>
            </tr>))}</tbody>
        </table></div>
      )}
    </section>
  );
}

export default function Govern() {
  const [key, setKey] = useState(0);
  const bump = () => setKey((k) => k + 1);
  return (
    <Page title="Govern" lead="Rules that no AI can override: check a trade, simulate a fix, and keep an honest record.">
      <div className="grid g2"><Firewall onStage={bump} /><RebalanceSim refreshKey={key} onBooked={bump} /></div>
      <div className="grid"><Ledger refreshKey={key} /></div>
      <div className="grid"><TamperDemo /></div>
    </Page>
  );
}
