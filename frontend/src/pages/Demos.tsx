import { useEffect, useMemo, useState } from "react";

import { hashParams } from "../lib/router";

const inr = (v: number) => `₹${Math.round(Math.abs(v)).toLocaleString("en-IN")}`;
const post = (url: string, body: unknown) =>
  fetch(url, { method: "POST", headers: { "Content-Type": "application/json" },
               body: JSON.stringify(body) }).then((r) => r.json());

/* ------------------------------------------------------------ panic-sell replay */
export function PanicSim() {
  const [key, setKey] = useState(() => hashParams().get("episode") || "covid");
  const [d, setD] = useState<any>(null);
  const [day, setDay] = useState(0);

  useEffect(() => {
    fetch(`/panic?key=${key}`).then((r) => r.json()).then((x) => {
      setD(x);
      setDay(Math.min(x.trough_index ?? 0, Math.max(0, (x.points?.length ?? 1) - 1)));
    }).catch(() => {});
  }, [key]);

  const geo = useMemo(() => {
    if (!d?.points?.length) return null;
    const vals: number[] = d.points.map((p: any) => p.value);
    const lo = Math.min(...vals) * 0.97, hi = Math.max(...vals) * 1.03;
    const W = 640, H = 220;
    const x = (i: number) => (i / (vals.length - 1)) * W;
    const y = (v: number) => H - ((v - lo) / (hi - lo)) * H;
    return { vals, x, y, W, H };
  }, [d]);

  if (!d?.points?.length || !geo) return (
    <section className="card"><h2>Panic-sell replay</h2><p className="muted">Load a portfolio to replay a crash.</p></section>);

  const sellVal = d.points[day].value;
  const hold = d.end_value;
  const diff = hold - sellVal;
  const hline = geo.vals.map((v, i) => `${geo.x(i)},${geo.y(v)}`).join(" ");
  const sline = `${geo.x(day)},${geo.y(sellVal)} ${geo.x(geo.vals.length - 1)},${geo.y(sellVal)}`;

  return (
    <section className="card">
      <h2>Panic-sell replay</h2>
      <p className="muted">Real prices from a real crash, applied to your holdings. Drag to choose the day you would have sold.</p>
      <div className="chips">
        {Object.entries(d.episodes as Record<string, string>).map(([k, l]) => (
          <button key={k} className={`btn sm ${k === key ? "go" : "ghost"}`} onClick={() => setKey(k)}>{l}</button>))}
      </div>
      <svg viewBox={`0 0 ${geo.W} ${geo.H}`} className="panicchart" role="img" aria-label="Portfolio value through the crash">
        <polyline points={hline} fill="none" stroke="var(--cyan)" strokeWidth="2" />
        <polyline points={sline} fill="none" stroke="var(--red)" strokeWidth="2" strokeDasharray="5 4" />
        <circle cx={geo.x(day)} cy={geo.y(sellVal)} r="6" fill="var(--red)" />
        <circle cx={geo.x(d.trough_index)} cy={geo.y(d.trough_value)} r="4" fill="none" stroke="var(--amber, #ffb020)" strokeWidth="2" />
      </svg>
      <input type="range" min={0} max={d.points.length - 1} value={day} aria-label="Day you sell"
             onChange={(e) => setDay(Number(e.target.value))} style={{ width: "100%" }} />
      <div className="tiny muted">Sell on {d.points[day].date} · lowest point was {d.points[d.trough_index].date} (ring)</div>
      <div className="sim">
        <div><div className="muted small">If you sold</div><b className="big neg">{inr(sellVal)}</b><div className="small">locked in, no recovery</div></div>
        <div className={`vbanner ${diff >= 0 ? "red" : "green"}`}>
          {diff >= 0
            ? `Selling cost you ${inr(diff)} versus waiting`
            : `Selling would have saved ${inr(diff)} here`}
          <div className="small">over the following months of this episode</div>
        </div>
        <div><div className="muted small">If you held to {d.points[d.points.length - 1].date}</div><b className="big pos">{inr(hold)}</b>
          <div className="small">started at {inr(d.start_value)}</div></div>
      </div>
      <p className="tiny muted">History is not a promise: some crashes keep falling. The 2022 episode shows that holding is not always the winner.</p>
    </section>
  );
}

/* ------------------------------------------------------------ tamper demo */
export function TamperDemo() {
  const [res, setRes] = useState<any>(null);
  const [rehash, setRehash] = useState(false);
  const [real, setReal] = useState<any>(null);
  const [target, setTarget] = useState<number | null>(null);

  const run = async (id: number, rh: boolean) => {
    setTarget(id);
    setRes(await post("/ledger/tamper", { id, field: "price", value: 1, rehash: rh }));
  };
  const start = async () => {
    await post("/ledger/demo-seed", {});
    const l = await fetch("/ledger?limit=8").then((r) => r.json());
    const ids: number[] = l.entries.map((e: any) => e.id).sort((a: number, b: number) => a - b);
    if (ids.length) await run(ids[Math.floor(ids.length / 2)], rehash);
  };
  useEffect(() => { if (target !== null) void run(target, rehash); }, [rehash]); // eslint-disable-line

  return (
    <section className="card">
      <h2>Tamper test</h2>
      <p className="muted">Try to rewrite history. Each entry carries the fingerprint of the one before it, so one edit shows up down the whole chain.</p>
      <div className="chips">
        <button className="btn sm go" onClick={start}>{res ? "Edit another entry" : "Tamper with an entry"}</button>
        <label className="small"><input type="checkbox" checked={rehash} onChange={(e) => setRehash(e.target.checked)} /> forger also recomputes the fingerprint</label>
        {target !== null && <button className="btn sm ghost" onClick={async () => setReal(await post("/ledger/tamper/real", { id: target }))}>Try a real database edit</button>}
      </div>
      {res && (
        <>
          <div className="blocks">
            {res.rows.map((r: any, i: number) => (
              <div key={r.id} className={`blk ${r.ok ? "ok" : "bad"} ${r.edited ? "edited" : ""}`}
                   onClick={() => run(r.id, rehash)} title="Click to tamper with this one">
                <div className="small">#{r.id} {r.side} {r.shares} {String(r.ticker).replace(".NS", "")}</div>
                <div className="small">₹{r.price}{r.edited && " ← edited"}</div>
                <code>{r.shown_hash}</code>
                {i > 0 && <div className="tiny">{r.prev_ok ? "link ✔" : "link ✖"}</div>}
              </div>))}
          </div>
          <div className={`chain ${res.intact ? "ok" : "bad"}`}>
            {res.intact ? "Chain intact" : `Tampering detected at entry #${res.broken_at} — everything after it can no longer be trusted`}
          </div>
        </>
      )}
      {real && (
        <div className={`chain ${real.blocked ? "ok" : "bad"}`}>
          {real.blocked ? `Database refused the edit: “${real.message}”. Nothing changed.` : real.message}
        </div>)}
    </section>
  );
}

/* ------------------------------------------------------------ goal fan chart */
export function GoalFan() {
  const [monthly, setMonthly] = useState(() => Number(hashParams().get("monthly")) || 10000);
  const [years, setYears] = useState(() => Number(hashParams().get("years")) || 10);
  const [target, setTarget] = useState(() => Number(hashParams().get("target")) || 3000000);
  const [haircut, setHaircut] = useState(0);
  const [d, setD] = useState<any>(null);

  useEffect(() => {
    const t = setTimeout(() => {
      fetch(`/goal?monthly=${monthly}&years=${years}&target=${target}&haircut=${haircut / 100}`)
        .then((r) => r.json()).then(setD).catch(() => {});
    }, 200);
    return () => clearTimeout(t);
  }, [monthly, years, target, haircut]);

  const W = 640, H = 220;
  const g = useMemo(() => {
    if (!d?.ok) return null;
    const pts = d.points as any[];
    const hi = Math.max(...pts.map((p) => p.p90), target) * 1.05;
    const x = (m: number) => (m / (years * 12)) * W;
    const y = (v: number) => H - (v / hi) * H;
    const up = pts.map((p) => `${x(p.month)},${y(p.p90)}`);
    const dn = pts.map((p) => `${x(p.month)},${y(p.p10)}`).reverse();
    return { band: [...up, ...dn].join(" "), mid: pts.map((p) => `${x(p.month)},${y(p.p50)}`).join(" "),
             ty: y(target), last: pts[pts.length - 1] };
  }, [d, years, target]);

  const slider = (label: string, v: number, set: (n: number) => void, min: number, max: number, step: number, fmt: (n: number) => string) => (
    <label className="small slider"><span>{label}: <b>{fmt(v)}</b></span>
      <input type="range" min={min} max={max} step={step} value={v} onChange={(e) => set(Number(e.target.value))} /></label>);

  return (
    <section className="card">
      <h2>Will I get there?</h2>
      <p className="muted">Your holdings plus a monthly SIP, shown as a range of outcomes built from how this portfolio actually behaved.</p>
      <div className="sliders">
        {slider("Monthly SIP", monthly, setMonthly, 0, 100000, 1000, inr)}
        {slider("Years", years, setYears, 1, 30, 1, (n) => `${n}`)}
        {slider("Goal", target, setTarget, 500000, 20000000, 100000, inr)}
        {slider("If returns are worse by", haircut, setHaircut, 0, 40, 5, (n) => `${n}%`)}
      </div>
      {g && d && (
        <>
          <svg viewBox={`0 0 ${W} ${H}`} className="panicchart" role="img" aria-label="Range of outcomes">
            <polygon points={g.band} fill="var(--cyan)" opacity="0.18" />
            <polyline points={g.mid} fill="none" stroke="var(--cyan)" strokeWidth="2" />
            <line x1="0" x2={W} y1={g.ty} y2={g.ty} stroke="var(--amber, #ffb020)" strokeDasharray="6 4" />
          </svg>
          <div className="sim">
            <div><div className="muted small">Bad case (1 in 10)</div><b className="big">{inr(g.last.p10)}</b></div>
            <div className={`vbanner ${d.prob_target >= 0.7 ? "green" : d.prob_target >= 0.4 ? "amber" : "red"}`}>
              {Math.round(d.prob_target * 100)}% of paths reach {inr(target)}
              <div className="small">you put in {inr(d.invested)} · typical result {inr(g.last.p50)}</div>
            </div>
            <div><div className="muted small">Good case (1 in 10)</div><b className="big">{inr(g.last.p90)}</b></div>
          </div>
          <p className="tiny muted">Built from {d.history_years} years of history, mostly a rising market, so the real
            future can be worse — use the slider above to test that. A range of possibilities, not a forecast.</p>
        </>
      )}
    </section>
  );
}
