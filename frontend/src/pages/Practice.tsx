import { useEffect, useMemo, useRef, useState } from "react";

import "../styles-practice.css";
import { Page } from "./Page";
import { allowSpeech, speak, stop as stopSpeech } from "../lib/speak";
import { useLang } from "../lib/lang";
import { hashParams } from "../lib/router";
import { EmergencyMeter, FeeDrag, WeeklyDigest } from "./PracticeMore";

const post = (url: string, body: unknown) =>
  fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
    .then((r) => r.json());
const inr = (v: number) => `₹${Math.round(v).toLocaleString("en-IN")}`;
const short = (n: string) => n.replace(" Mahindra Bank", "").replace(" Industries", "").replace(" Technologies", "");

/** Number that counts up to its target, so a result lands instead of just appearing. */
function CountUp({ to, suffix = "", decimals = 0 }: { to: number; suffix?: string; decimals?: number }) {
  const [v, setV] = useState(0);
  useEffect(() => {
    let raf = 0; const t0 = performance.now();
    const tick = (t: number) => {
      const k = Math.min(1, (t - t0) / 900);
      setV(to * (1 - Math.pow(1 - k, 3)));
      if (k < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    const safety = setTimeout(() => setV(to), 1200);           // rAF is throttled in background tabs
    return () => { cancelAnimationFrame(raf); clearTimeout(safety); };
  }, [to]);
  return <>{v.toFixed(decimals)}{suffix}</>;
}

/* ------------------------------------------------------------ fund overlap */
const ROW = 30, SHOW = 12;

function Ring({ pct, tone }: { pct: number; tone: string }) {
  const R = 52, C = 2 * Math.PI * R;
  const [p, setP] = useState(0);
  useEffect(() => { const t = setTimeout(() => setP(pct), 60); return () => clearTimeout(t); }, [pct]);
  return (
    <svg viewBox="0 0 130 130" className="ring">
      <circle cx="65" cy="65" r={R} className="ring-bg" />
      <circle cx="65" cy="65" r={R} className={`ring-fg ${tone}`} strokeDasharray={C}
              strokeDashoffset={C * (1 - Math.min(100, p) / 100)} transform="rotate(-90 65 65)" />
      <text x="65" y="64" textAnchor="middle" className="ring-num"><CountUp to={pct} decimals={0} suffix="%" /></text>
      <text x="65" y="84" textAnchor="middle" className="ring-sub">same stocks</text>
    </svg>
  );
}

function OverlapChecker() {
  const [funds, setFunds] = useState<any[]>([]);
  const [pick, setPick] = useState<string[]>(() => {
    const q = hashParams(); const a = q.get("a"), b = q.get("b");
    return a && b ? [a, b] : ["largecap_a", "bluechip_b"];
  });
  const [mine, setMine] = useState<string[]>([]);
  const [d, setD] = useState<any>(null);
  const [hot, setHot] = useState<string | null>(null);

  useEffect(() => { fetch("/funds").then((r) => r.json()).then((x) => setFunds(x.funds)).catch(() => {}); }, []);
  useEffect(() => { fetch("/myfunds").then((r) => r.json()).then((x) => setMine(x.funds)).catch(() => {}); }, []);
  const own = async (id: string) => {
    const on = !mine.includes(id);
    setMine((m) => (on ? [...m, id] : m.filter((x) => x !== id)));
    const r = await post("/myfunds", { fund_id: id, on });
    if (r?.funds) setMine(r.funds);
  };
  useEffect(() => {
    if (pick.length === 2) fetch(`/funds/overlap?a=${pick[0]}&b=${pick[1]}`).then((r) => r.json()).then(setD).catch(() => {});
  }, [pick]);

  const toggle = (id: string) =>
    setPick((p) => (p.includes(id) ? p.filter((x) => x !== id) : p.length === 2 ? [p[1], id] : [...p, id]));

  const rows = useMemo(() => {
    if (!d) return null;
    const A = d.a.holdings.slice(0, SHOW), B = d.b.holdings.slice(0, SHOW);
    const yb = new Map<string, number>(B.map((h: any, i: number) => [h.ticker, i]));
    const links = A.map((h: any, i: number) => ({ h, i, j: yb.get(h.ticker) }))
      .filter((l: any) => l.j !== undefined);
    return { A, B, links };
  }, [d]);

  return (
    <section className="card wide">
      <h2>Fund overlap checker</h2>
      <p className="muted">Two "different" funds can quietly hold the same stocks, so you pay two managers for one portfolio.
        Pick any two funds and watch the shared holdings light up.</p>
      <div className="fundpick">
        {funds.map((f) => {
          const n = pick.indexOf(f.id);
          return (
            <button key={f.id} className={`fundcard ${n >= 0 ? "sel" : ""}`} onClick={() => toggle(f.id)}>
              {n >= 0 && <span className="slot">{n === 0 ? "A" : "B"}</span>}
              <span role="button" tabIndex={0} className={`ownstar ${mine.includes(f.id) ? "on" : ""}`}
                    title="I own this fund (the assistant remembers it)"
                    onClick={(e) => { e.stopPropagation(); void own(f.id); }}
                    onKeyDown={(e) => { if (e.key === "Enter") { e.stopPropagation(); void own(f.id); } }}>{mine.includes(f.id) ? "★ I own this" : "☆ I own this"}</span>
              <b>{f.name.replace("Sample ", "")}</b>
              <span className="tiny muted">{f.kind} · fee {f.er}%</span>
            </button>);
        })}
      </div>

      {d && rows && (
        <div className="ovl">
          <div className="ovl-grid">
            <div className="ovl-col">
              <div className="ovl-title">{d.a.name.replace("Sample ", "")} <span className="tiny muted">fee {d.a.er}%</span></div>
              {rows.A.map((h: any) => {
                const shared = d.shared.some((s: any) => s.ticker === h.ticker);
                return <div key={h.ticker} style={{ height: ROW }} onMouseEnter={() => setHot(h.ticker)} onMouseLeave={() => setHot(null)}
                            className={`ovl-row ${shared ? "shared" : ""} ${hot === h.ticker ? "hot" : ""}`}>
                  <span>{short(h.name)}</span><b>{h.w}%</b></div>;
              })}
            </div>
            <svg className="ovl-links" viewBox={`0 0 160 ${ROW * SHOW}`} preserveAspectRatio="none">
              {rows.links.map((l: any, k: number) => {
                const y1 = l.i * ROW + ROW / 2, y2 = l.j * ROW + ROW / 2;
                const w = Math.max(2, l.h.w * 1.1);
                return <path key={l.h.ticker} d={`M0 ${y1} C80 ${y1}, 80 ${y2}, 160 ${y2}`} fill="none"
                             className={`ribbon ${d.verdict} ${hot === l.h.ticker ? "hot" : ""}`}
                             strokeWidth={w} style={{ animationDelay: `${k * 70}ms` }} />;
              })}
            </svg>
            <div className="ovl-col">
              <div className="ovl-title">{d.b.name.replace("Sample ", "")} <span className="tiny muted">fee {d.b.er}%</span></div>
              {rows.B.map((h: any) => {
                const shared = d.shared.some((s: any) => s.ticker === h.ticker);
                return <div key={h.ticker} style={{ height: ROW }} onMouseEnter={() => setHot(h.ticker)} onMouseLeave={() => setHot(null)}
                            className={`ovl-row ${shared ? "shared" : ""} ${hot === h.ticker ? "hot" : ""}`}>
                  <b>{h.w}%</b><span>{short(h.name)}</span></div>;
              })}
            </div>
          </div>

          <div className="ovl-side">
            <Ring pct={d.overlap_pct} tone={d.verdict} />
            <div className={`vbanner ${d.verdict}`}>
              {d.verdict === "red" ? "Mostly the same portfolio" : d.verdict === "amber" ? "Noticeable overlap" : "Genuinely different"}
              <div className="small">{d.shared_stocks} stocks in common</div>
            </div>
            {d.verdict !== "green" && (
              <div className="statbox"><b>{inr(d.wasted_fee_per_lakh)}</b><span>a year per ₹1 lakh goes to paying for the same stocks twice</span></div>)}
            {d.own_in_a > 0 && (
              <div className="statbox"><b>{d.own_in_a}% / {d.own_in_b}%</b>
                <span>of what you hold directly ({d.own_names.join(", ")}) is already inside these funds</span></div>)}
          </div>
        </div>
      )}
      <p className="tiny muted">Holdings shown are illustrative samples typical of each fund type, not live factsheets. Overlap = the smaller weight of every stock both funds hold.</p>
    </section>
  );
}

/* ------------------------------------------------------------ scam call rehearsal */
type Step = { status: string; node?: number; line?: string; flags?: any[]; hints?: string[];
              pressure: number; feedback?: string; loss?: number; kind?: string };

function Wave({ on }: { on: boolean }) {
  return <div className={`wave ${on ? "on" : ""}`}>{Array.from({ length: 22 }, (_, i) => <i key={i} style={{ animationDelay: `${i * 55}ms` }} />)}</div>;
}

function ScamCall() {
  const lang = useLang((s) => s.lang);
  const hi = lang === "hi";
  const [list, setList] = useState<any[]>([]);
  const [sc, setSc] = useState<any>(null);
  const [phase, setPhase] = useState<"pick" | "ring" | "call" | "end">("pick");
  const [step, setStep] = useState<Step | null>(null);
  const [shown, setShown] = useState("");
  const [seen, setSeen] = useState<any[]>([]);
  const [log, setLog] = useState<{ who: string; text: string }[]>([]);
  const [text, setText] = useState("");
  const [secs, setSecs] = useState(0);
  const [voice, setVoice] = useState(true);
  const [busy, setBusy] = useState(false);
  const [talking, setTalking] = useState(false);
  const typer = useRef<number | undefined>(undefined);

  useEffect(() => {
    // a language switch mid-call restarts it: the script is in one language only
    stopSpeech(); setPhase("pick");
    fetch(`/scamcall/scenarios?lang=${lang}`).then((r) => r.json()).then((x) => setList(x.scenarios)).catch(() => {});
  }, [lang]);
  useEffect(() => {
    if (phase !== "call") return;
    const t = setInterval(() => setSecs((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [phase]);
  useEffect(() => () => { stopSpeech(); window.clearInterval(typer.current); }, []);

  const say = (line: string) => {
    window.clearInterval(typer.current);
    setShown(""); setTalking(true);
    let i = 0;
    typer.current = window.setInterval(() => {
      i += 2; setShown(line.slice(0, i));
      if (i >= line.length) { window.clearInterval(typer.current); setTimeout(() => setTalking(false), 400); }
    }, 28);
    if (voice) { allowSpeech(); speak(line, lang); }
  };

  const begin = (s: any) => { setSc(s); setPhase("ring"); setSeen([]); setLog([]); setSecs(0); setShown(""); setStep(null); };
  const accept = async () => {
    setPhase("call");
    const r: Step = await post("/scamcall/step", { scenario: sc.id, node: 0, reply: null, lang });
    setStep(r); setSeen(r.flags ?? []); setLog([{ who: "caller", text: r.line! }]); say(r.line!);
  };
  const reply = async (t: string) => {
    if (!step || busy || !t.trim()) return;
    setBusy(true); setText(""); stopSpeech();
    setLog((l) => [...l, { who: "you", text: t }]);
    const r: Step = await post("/scamcall/step", { scenario: sc.id, node: step.node ?? 0, reply: t, pressure: step.pressure, lang });
    setBusy(false);
    if (r.status === "continue") {
      setStep(r); setSeen((s) => [...s, ...(r.flags ?? [])]); setLog((l) => [...l, { who: "caller", text: r.line! }]); say(r.line!);
    } else { setStep(r); setPhase("end"); window.clearInterval(typer.current); }
  };
  const hang = () => reply(hi ? "यह ठगी है। मैं फ़ोन काट रहा हूँ।" : "I am hanging up. This is a scam.");

  // Different order every call so the safe answer is not always in the same place.
  const options = useMemo(() => {
    const h = step?.hints ?? [];
    return h.map((x, i) => ({ x, k: (i * 7 + (step?.node ?? 0) * 3) % 5 })).sort((a, b) => a.k - b.k).map((o) => o.x);
  }, [step]);

  if (phase === "pick") return (
    <section className="card wide">
      <h2>{hi ? "ठगी वाली कॉल का अभ्यास" : "Scam call rehearsal"}</h2>
      <p className="muted">{hi ? "असली कॉल आने से पहले मना करना सीखिए। कॉल करने वाला वही चालें चलेगा जो असली ठग चलते हैं। यहाँ कुछ भी असली नहीं है और कोई डेटा आपकी मशीन से बाहर नहीं जाता।"
        : "Practise saying no before it is real. A caller will pressure you using the exact tactics scammers use. Nothing here is real and no data leaves your machine."}</p>
      <div className="scgrid">
        {list.map((s) => (
          <button key={s.id} className="sccard" onClick={() => begin(s)}>
            <span className="scicon">☎</span><b>{s.title}</b>
            <span className="small muted">{hi ? `${inr(s.loss)} तक दाँव पर · ${s.steps} चरण` : `Up to ${inr(s.loss)} at stake · ${s.steps} turns`}</span>
            <span className="scgo">{hi ? "कॉल उठाइए →" : "Receive the call →"}</span>
          </button>))}
      </div>
    </section>);

  return (
    <section className="card wide">
      <div className="phone">
        <div className="phone-top">
          <div className={`avatar ${phase === "ring" ? "ringing" : ""}`}>☎</div>
          <div>
            <div className="callname">{sc.caller}</div>
            <div className="small muted">{phase === "ring" ? sc.intro : sc.number}</div>
            {phase !== "ring" && <div className="small calltime">{phase === "end" ? (hi ? "कॉल ख़त्म" : "Call ended") : `${String(Math.floor(secs / 60)).padStart(2, "0")}:${String(secs % 60).padStart(2, "0")}`}</div>}
          </div>
          <label className="small voicetog"><input type="checkbox" checked={voice} onChange={(e) => { setVoice(e.target.checked); if (!e.target.checked) stopSpeech(); }} /> {hi ? "कॉलर की आवाज़" : "caller voice"}</label>
        </div>

        {phase === "ring" && (
          <div className="ringactions">
            <button className="callbtn red" onClick={() => setPhase("pick")} aria-label="Decline">✕</button>
            <button className="callbtn green" onClick={accept} aria-label="Answer">✆</button>
          </div>)}

        {phase === "call" && step && (
          <>
            <div className="pressure"><span>{hi ? "दबाव" : "Pressure"}</span>
              <div className="pbar"><div style={{ width: `${step.pressure}%` }} className={step.pressure > 60 ? "hi" : ""} /></div></div>
            <Wave on={talking} />
            <div className="bubble caller">{shown}</div>
            <div className="flagpops">
              {(step.flags ?? []).map((f) => <span key={f.code} className="flagpop" title={f.why}>⚑ {f.label}</span>)}
            </div>
            <div className="replies">
              {options.map((o) => <button key={o} className="reply" disabled={busy} onClick={() => reply(o)}>{o}</button>)}
            </div>
            <div className="cmdrow">
              <input className="field" placeholder={hi ? "…या अपना जवाब लिखिए" : "…or type your own reply"} value={text} onChange={(e) => setText(e.target.value)}
                     onKeyDown={(e) => { if (e.key === "Enter") void reply(text); }} />
              <button className="btn go" disabled={busy} onClick={() => reply(text)}>{hi ? "बोलें" : "Say"}</button>
              <button className="btn ghost danger" onClick={hang}>{hi ? "फ़ोन काटें" : "Hang up"}</button>
            </div>
          </>)}

        {phase === "end" && step && (
          <div className={`endcard ${step.status}`}>
            <div className="endicon">{step.status === "won" ? "🛡" : "⚠"}</div>
            <div className="endtitle">{step.status === "won" ? (hi ? "आप सुरक्षित रहे" : "You stayed safe") : (hi ? `आपके ${inr(step.loss ?? 0)} जा सकते थे` : `You would have lost ${inr(step.loss ?? 0)}`)}</div>
            <p>{step.feedback}</p>
            <h3>{hi ? "आप पर आज़माई गई चालें" : "Tactics used on you"}</h3>
            <div className="tactics">
              {[...new Map(seen.map((f) => [f.code, f])).values()].map((f: any) => (
                <div key={f.code} className="tactic"><b>⚑ {f.label}</b><span className="small muted">{f.why}</span></div>))}
            </div>
            <div className="rule">{hi ? <>तीन का नियम: <b>रुकिए</b> (कॉल पर कभी कार्रवाई मत कीजिए), <b>फ़ोन काटिए</b>, फिर <b>आधिकारिक नंबर</b> या 1930 पर फ़ोन कीजिए।</>
              : <>Rule of three: <b>Stop</b> (never act on a call), <b>Hang up</b>, then <b>call the official number</b> or 1930.</>}</div>
            <div className="cmdrow">
              <button className="btn go" onClick={() => begin(sc)}>{hi ? "फिर से" : "Try again"}</button>
              <button className="btn ghost" onClick={() => { setPhase("pick"); stopSpeech(); }}>{hi ? "दूसरा परिदृश्य" : "Another scenario"}</button>
            </div>
          </div>)}

        {phase !== "ring" && (
          <div className="calllog" aria-label="Conversation so far">
            {log.slice(0, -1).map((m, i) => <div key={i} className={`logline ${m.who}`}>{m.who === "you" ? "You: " : "Caller: "}{m.text}</div>)}
          </div>)}
      </div>
    </section>);
}

export default function Practice() {
  return (
    <Page title="Practice" lead="Learn by doing: compare funds before you buy two of the same, and rehearse a scam call before a real one arrives.">
      <div className="grid"><OverlapChecker /></div>
      <div className="grid"><FeeDrag /></div>
      <div className="grid"><EmergencyMeter /></div>
      <div className="grid"><WeeklyDigest /></div>
      <div className="grid"><ScamCall /></div>
    </Page>
  );
}
