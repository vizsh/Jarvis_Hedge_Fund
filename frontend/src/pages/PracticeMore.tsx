import { useEffect, useMemo, useRef, useState } from "react";

import { useLang } from "../lib/lang";
import { hashParams } from "../lib/router";
import { allowSpeech, onVoice, speak, stop as stopSpeech } from "../lib/speak";

const inr = (v: number) => {
  const a = Math.abs(v), s = v < 0 ? "-" : "";
  if (a >= 1e7) return `${s}₹${(a / 1e7).toFixed(2)} crore`;
  if (a >= 1e5) return `${s}₹${(a / 1e5).toFixed(2)} lakh`;
  return `${s}₹${Math.round(a).toLocaleString("en-IN")}`;
};
let overrides: Record<string, string | number> | undefined;
const num = (key: string, d: number) => {
  const o = overrides?.[key];
  if (o !== undefined && !Number.isNaN(Number(o))) return Number(o);
  const v = hashParams().get(key);
  return v !== null && v !== "" && !Number.isNaN(Number(v)) ? Number(v) : d;
};

function Slider({ label, value, set, min, max, step, fmt }: {
  label: string; value: number; set: (n: number) => void; min: number; max: number; step: number; fmt: (n: number) => string;
}) {
  return (
    <label className="small slider"><span>{label}: <b>{fmt(value)}</b></span>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => set(Number(e.target.value))} /></label>);
}

/* ------------------------------------------------------------ fee drag */
export function FeeDrag({ init, compact = false }: { init?: Record<string, string | number>; compact?: boolean }) {
  const hi = useLang((s) => s.lang) === "hi";
  overrides = init;                       // chat answers pass the figures they computed
  const [lump, setLump] = useState(num("lump", 100000));
  const [monthly, setMonthly] = useState(num("monthly", 0));
  const [years, setYears] = useState(num("years", 20));
  const [gross, setGross] = useState(num("gross", 12));
  const [fee, setFee] = useState(num("fee", 2));
  const [low, setLow] = useState(num("low", 0.2));
  const [d, setD] = useState<any>(null);
  const [at, setAt] = useState<number | null>(null);
  const [shown, setShown] = useState(0);

  useEffect(() => {
    const t = setTimeout(() => {
      fetch(`/feedrag?principal=${lump}&monthly=${monthly}&years=${years}&gross=${gross}&fee=${fee}&low=${low}`)
        .then((r) => r.json()).then(setD).catch(() => {});
    }, 150);
    return () => clearTimeout(t);
  }, [lump, monthly, years, gross, fee, low]);

  // count the headline loss up when it changes, so the number lands
  useEffect(() => {
    if (!d) return;
    const target = d.lost_vs_low as number; const from = shown; const t0 = performance.now();
    let raf = 0;
    const tick = (t: number) => {
      const k = Math.min(1, (t - t0) / 600);
      setShown(from + (target - from) * (1 - Math.pow(1 - k, 3)));
      if (k < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    const safety = setTimeout(() => setShown(target), 800);
    return () => { cancelAnimationFrame(raf); clearTimeout(safety); };
  }, [d]); // eslint-disable-line

  const W = 640, H = 230;
  const g = useMemo(() => {
    if (!d?.points) return null;
    const pts = d.points as any[];
    const hiV = Math.max(...pts.map((p) => p.free)) * 1.04;
    const x = (i: number) => (i / (pts.length - 1)) * W;
    const y = (v: number) => H - (v / hiV) * H;
    const line = (k: string) => pts.map((p, i) => `${x(i)},${y(p[k])}`).join(" ");
    const band = [...pts.map((p, i) => `${x(i)},${y(p.low)}`), ...pts.map((p, i) => `${x(pts.length - 1 - i)},${y(pts[pts.length - 1 - i].high)}`)].join(" ");
    return { x, y, line, band, pts };
  }, [d]);

  const move = (e: React.PointerEvent<SVGSVGElement>) => {
    if (!g) return;
    const r = e.currentTarget.getBoundingClientRect();
    setAt(Math.max(0, Math.min(g.pts.length - 1, Math.round(((e.clientX - r.left) / r.width) * (g.pts.length - 1)))));
  };

  const eaten = d ? Math.round(d.share_of_gain_lost * 100) : 0;
  const p = at !== null && g ? g.pts[at] : null;

  return (
    <section className={compact ? "fd-inline" : "card wide"}>
      {!compact && <h2>{hi ? "फ़ीस का असर" : "Fee drag"}</h2>}
      {!compact && <p className="muted">{hi ? "छोटी सालाना फ़ीस सालों में बड़ी रक़म खा जाती है। स्लाइडर हिलाइए और देखिए।"
                                : "A small yearly fee quietly eats a big share of your growth. Move the sliders and watch."}</p>}
      <div className="sliders">
        <Slider label={hi ? "एक बार का निवेश" : "Lump sum"} value={lump} set={setLump} min={0} max={5000000} step={50000} fmt={inr} />
        <Slider label={hi ? "मासिक SIP" : "Monthly SIP"} value={monthly} set={setMonthly} min={0} max={100000} step={1000} fmt={inr} />
        <Slider label={hi ? "साल" : "Years"} value={years} set={setYears} min={1} max={40} step={1} fmt={(n) => `${n}`} />
        <Slider label={hi ? "फ़ीस से पहले रिटर्न" : "Return before fees"} value={gross} set={setGross} min={6} max={18} step={0.5} fmt={(n) => `${n}%`} />
        <Slider label={hi ? "आपके फ़ंड की फ़ीस" : "Your fund's fee"} value={fee} set={setFee} min={0} max={3} step={0.1} fmt={(n) => `${n.toFixed(1)}%`} />
        <Slider label={hi ? "सस्ते फ़ंड की फ़ीस" : "Cheap fund's fee"} value={low} set={setLow} min={0} max={3} step={0.1} fmt={(n) => `${n.toFixed(1)}%`} />
      </div>

      {g && d && (
        <div className={compact ? "fdwrap one" : "fdwrap"}>
          <div>
            <svg viewBox={`0 0 ${W} ${H}`} className="panicchart fdchart" onPointerMove={move} onPointerLeave={() => setAt(null)}
                 role="img" aria-label="Growth with and without fees">
              <polygon points={g.band} className="fd-band" />
              <polyline points={g.line("free")} className="fd-free" />
              <polyline points={g.line("low")} className="fd-low" />
              <polyline points={g.line("high")} className="fd-high" />
              {p && <><line x1={g.x(at!)} x2={g.x(at!)} y1={0} y2={H} className="fd-cursor" />
                <circle cx={g.x(at!)} cy={g.y(p.high)} r="5" className="fd-dot-high" /><circle cx={g.x(at!)} cy={g.y(p.low)} r="5" className="fd-dot-low" /></>}
            </svg>
            <div className="fd-legend">
              <span className="lg low">{hi ? "सस्ता फ़ंड" : "Cheap fund"} ({low.toFixed(1)}%)</span>
              <span className="lg high">{hi ? "आपका फ़ंड" : "Your fund"} ({fee.toFixed(1)}%)</span>
              <span className="lg free">{hi ? "बिना फ़ीस" : "No fee"}</span>
            </div>
            <div className="tiny muted" style={{ minHeight: 18 }}>
              {p ? `${hi ? "साल" : "Year"} ${p.year}: ${inr(p.high)} vs ${inr(p.low)} → ${inr(p.low - p.high)} ${hi ? "का फ़र्क़" : "gap"}` : (hi ? "ग्राफ़ पर उँगली/माउस फेरिए" : "Hover the chart to read any year")}
            </div>
          </div>
          <div className="fd-side">
            <div className="fd-big"><span>{hi ? "फ़ीस में गया" : "Lost to the fee"}</span><b>{inr(shown)}</b>
              <small>{hi ? `${years} साल में, सस्ते फ़ंड की तुलना में` : `over ${years} years, versus the cheap fund`}</small></div>
            <div className="fd-bar" aria-label={`${eaten}% of growth eaten`}>
              <div className="kept" style={{ width: `${100 - eaten}%` }} /><div className="eaten" style={{ width: `${eaten}%` }} />
            </div>
            <div className="small">{hi ? `आपकी बढ़ोतरी का ${eaten}% फ़ीस खा गई` : `${eaten}% of your growth went to the fee`}</div>
            <div className="small muted">{hi ? "अंत में" : "You end with"} <b>{inr(d.final_high)}</b> {hi ? "बनाम" : "vs"} <b>{inr(d.final_low)}</b></div>
          </div>
        </div>)}
      <p className="tiny muted">{hi ? "अनुमान है, वादा नहीं: शुद्ध रिटर्न = रिटर्न - फ़ीस, हर महीने चक्रवृद्धि।" : "A projection, not a promise: net return = return - fee, compounded monthly."}</p>
    </section>
  );
}

/* ------------------------------------------------------------ emergency fund */
export function EmergencyMeter({ init, compact = false }: { init?: Record<string, string | number>; compact?: boolean }) {
  const hi = useLang((s) => s.lang) === "hi";
  overrides = init;
  const [cash, setCash] = useState(num("cash", 300000));
  const [exp, setExp] = useState(num("exp", 40000));
  const [inc, setInc] = useState(num("inc", 0));
  const [inv, setInv] = useState(num("inv", 0));
  const [d, setD] = useState<any>(null);

  useEffect(() => {
    const t = setTimeout(() => {
      fetch(`/emergency?cash=${cash}&expenses=${exp}&income=${inc}&invest=${inv}`).then((r) => r.json()).then(setD).catch(() => {});
    }, 150);
    return () => clearTimeout(t);
  }, [cash, exp, inc, inv]);

  const months = useMemo(() => {
    if (!d) return [];
    const run = d.runway_cash ?? 24;
    const n = Math.max(12, Math.ceil(run) + 1);
    return Array.from({ length: Math.min(n, 24) }, (_, i) => ({ m: i + 1, fill: Math.max(0, Math.min(1, run - i)) }));
  }, [d]);

  const band = d?.band ?? "amber";
  const label = band === "green" ? (hi ? "सुरक्षित" : "Safe") : band === "amber" ? (hi ? "ठीक-ठाक" : "Getting there") : (hi ? "जोखिम में" : "At risk");

  return (
    <section className={compact ? "fd-inline" : "card wide"}>
      {!compact && <h2>{hi ? "इमरजेंसी फ़ंड मीटर" : "Emergency-fund meter"}</h2>}
      {!compact && <p className="muted">{hi ? "अगर आमदनी रुक जाए तो आपका पैसा कितने महीने चलेगा?" : "If your income stopped, how many months would your money last?"}</p>}
      <div className="sliders">
        <Slider label={hi ? "नक़द बचत" : "Cash savings"} value={cash} set={setCash} min={0} max={3000000} step={10000} fmt={inr} />
        <Slider label={hi ? "मासिक ख़र्च" : "Monthly spending"} value={exp} set={setExp} min={5000} max={300000} step={1000} fmt={inr} />
        <Slider label={hi ? "बची हुई आमदनी (किराया आदि)" : "Income that continues"} value={inc} set={setInc} min={0} max={200000} step={1000} fmt={inr} />
        <Slider label={hi ? "बेचे जा सकने वाले निवेश" : "Investments you could sell"} value={inv} set={setInv} min={0} max={5000000} step={50000} fmt={inr} />
      </div>
      {d && (
        <div className={compact ? "emwrap one" : "emwrap"}>
          <div className={`em-ring ${band}`}>
            <b>{d.runway_cash === null ? "∞" : d.runway_cash.toFixed(1)}</b>
            <span>{hi ? "महीने" : "months"}</span>
            <small>{label}</small>
          </div>
          <div className="em-bars" role="img" aria-label="Months of cover">
            {months.map((b, i) => (
              <div key={b.m} className={`em-col ${b.m === d.target_months ? "target" : ""}`} title={`${hi ? "महीना" : "Month"} ${b.m}`}>
                <div className="em-track"><div className={`em-fill ${b.m <= 3 ? "r" : b.m <= 5 ? "a" : "g"}`}
                     style={{ height: `${b.fill * 100}%`, transitionDelay: `${i * 35}ms` }} /></div>
                <span>{b.m}</span>
              </div>))}
          </div>
          <div className="em-side">
            <div className="statbox"><b>{inr(d.target_amount)}</b><span>{hi ? "छह महीने का लक्ष्य" : "Six-month target"}</span></div>
            {d.shortfall > 0
              ? <div className="statbox"><b>{inr(d.shortfall)}</b><span>{hi ? `कम है। हर महीने ${inr(d.save_per_month_12)} बचाइए तो साल भर में पूरा।` : `short. Save ${inr(d.save_per_month_12)} a month to close it in a year.`}</span></div>
              : <div className="statbox"><b>✓</b><span>{hi ? "आप लक्ष्य पर हैं।" : "You have met the target."}</span></div>}
            {inv > 0 && d.runway_all !== null && <div className="statbox"><b>{d.runway_all.toFixed(1)} {hi ? "महीने" : "mo"}</b>
              <span>{hi ? "निवेश बेचकर (20% गिरावट के बाद): नुक़सान पक्का होता है।" : "if you also sold investments after a 20% fall. Selling into a crash locks in losses."}</span></div>}
          </div>
        </div>)}
    </section>
  );
}

/* ------------------------------------------------------------ weekly digest */
export function WeeklyDigest() {
  const lang = useLang((s) => s.lang);
  const hi = lang === "hi";
  const [d, setD] = useState<any>(null);
  const [active, setActive] = useState(-1);
  const playing = useRef(false);

  useEffect(() => { stopSpeech(); playing.current = false; setActive(-1);
    fetch(`/digest?lang=${lang}`).then((r) => r.json()).then(setD).catch(() => {}); }, [lang]);
  useEffect(() => () => { playing.current = false; stopSpeech(); }, []);

  // Intro, each section, outro: spoken one after another so the highlight is always exactly in sync.
  const lines: { title?: string; text: string }[] = useMemo(() => d ? [
    { text: hi ? "नमस्कार। यह आपका साप्ताहिक सार है।" : "Hello. Here is your weekly summary." },
    ...d.sections,
    { text: hi ? "बस इतना ही। सवाल पूछना हो तो मुझसे पूछिए।" : "That is all for this week. Ask me anything you want to go deeper on." },
  ] : [], [d, hi]);

  const play = () => {
    if (!lines.length) return;
    allowSpeech();                  // pressing play is an explicit request to be heard
    playing.current = true;
    let i = 0;
    const speakLine = () => {
      if (!playing.current || i >= lines.length) { playing.current = false; setActive(-1); return; }
      setActive(i);
      let started = false;
      const off = onVoice((st) => {
        if (st === "speaking") started = true;
        if (started && st === "idle") { off(); i += 1; speakLine(); }
        if (st === "stopped" || st === "muted") { off(); playing.current = false; setActive(-1); }
      });
      speak(lines[i].text, lang, true);
    };
    speakLine();
  };
  const halt = () => { playing.current = false; stopSpeech(); setActive(-1); };

  return (
    <section className="card wide">
      <h2>{hi ? "साप्ताहिक आवाज़ सार" : "Weekly voice digest"}</h2>
      <p className="muted">{hi ? "आपके पोर्टफ़ोलियो का एक मिनट का सार, आपकी भाषा में। हर आँकड़ा सीधे आपके डेटा से।" : "A one-minute spoken summary of your portfolio. Every figure comes straight from your data."}</p>
      <div className="chips">
        <button className="btn go" onClick={play} disabled={!d || active >= 0}>▶ {hi ? "सुनिए" : "Play briefing"}</button>
        <button className="btn ghost" onClick={halt}>■ {hi ? "रोकें" : "Stop"}</button>
        {d && <span className="tiny muted">≈ {Math.max(30, Math.round(d.words / 2.4))} {hi ? "सेकंड" : "seconds"}</span>}
      </div>
      <div className="digest">
        {lines.map((l, i) => (
          <div key={i} className={`dg-line ${active === i ? "on" : ""} ${active > i ? "done" : ""}`}>
            {l.title && <b>{l.title}: </b>}{l.text}
          </div>))}
      </div>
    </section>
  );
}
