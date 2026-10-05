import { useEffect, useMemo, useRef, useState } from "react";

import "../../styles-arena.css";
import { useLang } from "../../lib/lang";
import { useStore } from "../../lib/store";

/* One honest picture of what the backend does when a company is analysed:
 *   evidence (dated prices, numbers, headlines) is shared with three analyst desks that reason at the same time;
 *   every claim must cite evidence or it is dropped; then a Red Team reads what the analysts concluded and argues the
 *   other side; a committee weighs what survived. Nothing here is decoration: each movement is driven by an event the
 *   server really sent (agent.state, claim, claim.rejected, consensus, conviction), in the order it really happened. */

const W = 900, H = 400;
const ANALYSTS = ["Fundamental", "Quant", "Narrative"];
const RED = "Red Team";
const DESK_Y: Record<string, number> = { Fundamental: 70, Quant: 170, Narrative: 270, [RED]: 352 };
const GROUPS = [
  { id: "price", en: "Prices", hi: "भाव", y: 36 }, { id: "fundamental", en: "Company numbers", hi: "कंपनी के आँकड़े", y: 126 },
  { id: "news", en: "Headlines", hi: "सुर्ख़ियाँ", y: 216 }, { id: "other", en: "Filings & other", hi: "फ़ाइलिंग और अन्य", y: 306 },
];
const groupOf = (kind: string) => (/price|close|quote/i.test(kind) ? "price" : /fund|ratio|pe_|roe|margin|market_cap/i.test(kind) ? "fundamental" : /news|headline|tone/i.test(kind) ? "news" : "other");
const L = { x: 545, w: 100 }, Rr = { x: 675, w: 100 }, BIN_Y = 222;
const slot = (side: "bull" | "bear", i: number) => {
  const b = side === "bull" ? L : Rr;
  return { x: b.x + 14 + (i % 4) * 24, y: BIN_Y + 16 + Math.floor(i / 4) * 24 };
};
const curve = (x1: number, y1: number, x2: number, y2: number) => `M${x1},${y1} C${x1 + (x2 - x1) * 0.55},${y1} ${x1 + (x2 - x1) * 0.45},${y2} ${x2},${y2}`;

type Step = "idle" | "active" | "done";

export function Arena() {
  const hi = useLang((s) => s.lang) === "hi";
  const t = (en: string, h: string) => (hi ? h : en);
  const desks = useStore((s) => s.desks);
  const claims = useStore((s) => s.claims);
  const rejected = useStore((s) => s.rejected);
  const evidence = useStore((s) => s.evidence);
  const conviction = useStore((s) => s.conviction);
  const consensus = useStore((s) => s.consensus);
  const nodes = useStore((s) => s.nodes);
  const ticker = useStore((s) => s.ticker);
  const select = useStore((s) => s.select);
  const [lit, setLit] = useState<string[]>([]);
  const [now, setNow] = useState(Date.now());
  const startRef = useRef<number | null>(null);

  const state = (n: string) => desks[n]?.state ?? "idle";
  const running = ANALYSTS.some((n) => state(n) === "thinking") || state(RED) === "thinking";
  const analystsDone = ANALYSTS.every((n) => ["done", "failed"].includes(state(n)));
  const gathering = nodes.length > 0 || Object.keys(evidence).length > 0;

  useEffect(() => { if (running && startRef.current === null) startRef.current = Date.now(); if (!running && conviction) { /* keep final time */ } }, [running, conviction]);
  useEffect(() => { if (!Object.keys(desks).length) startRef.current = null; }, [desks]);
  useEffect(() => { if (!running) return; const id = window.setInterval(() => setNow(Date.now()), 250); return () => window.clearInterval(id); }, [running]);

  // what each step of the real process is doing right now
  const steps: { id: string; en: string; hi: string; s: Step }[] = [
    { id: "gather", en: "Gather dated evidence", hi: "तारीख़वार सबूत जुटाना", s: gathering ? (Object.keys(desks).length ? "done" : "active") : "idle" },
    { id: "analysts", en: "Analysts reason in parallel", hi: "विश्लेषक साथ-साथ सोचते हैं", s: analystsDone ? "done" : ANALYSTS.some((n) => state(n) === "thinking") ? "active" : "idle" },
    { id: "red", en: "Red Team argues the other side", hi: "रेड टीम दूसरा पक्ष रखती है", s: ["done", "failed"].includes(state(RED)) ? "done" : state(RED) === "thinking" ? "active" : "idle" },
    { id: "committee", en: "Committee weighs what survived", hi: "समिति बचे हुए दावे तौलती है", s: conviction ? "done" : ["done", "failed"].includes(state(RED)) ? "active" : "idle" },
    { id: "summary", en: "Plain summary", hi: "सरल सारांश", s: conviction ? "done" : "idle" },
  ];

  const evItems = useMemo(() => Object.values(evidence), [evidence]);
  const byGroup = useMemo(() => {
    const m: Record<string, typeof evItems> = { price: [], fundamental: [], news: [], other: [] };
    evItems.forEach((e) => m[groupOf(e.kind)].push(e));
    return m;
  }, [evItems]);
  const cited = useMemo(() => new Set(claims.flatMap((c) => c.source_ids)), [claims]);

  const bull = claims.filter((c) => c.stance === "bull"), bear = claims.filter((c) => c.stance === "bear");
  const wBull = bull.reduce((a, c) => a + c.weight, 0), wBear = bear.reduce((a, c) => a + c.weight, 0);
  const tilt = wBull + wBear ? ((wBear - wBull) / (wBull + wBear)) * 11 : 0;
  const seconds = startRef.current ? Math.round(((running ? now : Date.now()) - startRef.current) / 1000) : 0;
  const idle = !Object.keys(desks).length && !claims.length;
  const dispName = (n: string) => (hi ? ({ Fundamental: "बुनियादी", Quant: "आँकड़े", Narrative: "ख़बरें", [RED]: "रेड टीम" } as Record<string, string>)[n] : n) ?? n;

  const stackIndex = { bull: -1, bear: -1 };
  const tokens = claims.map((c, i) => {
    const side = c.stance === "bear" ? "bear" : "bull";
    stackIndex[side] += 1;
    return { c, i, side, idx: stackIndex[side] as number };
  });

  return (
    <section className={`arena card ${running ? "running" : ""} ${idle ? "idle" : ""}`} aria-label={t("How the analysts reached this", "विश्लेषक इस नतीजे तक कैसे पहुँचे")}>
      <header className="arena-head">
        <div>
          <h2>{t("How the analysts are working on", "विश्लेषक कैसे काम कर रहे हैं:")} <span className="arena-tk">{ticker.replace(/\.(NS|BO)$/, "")}</span></h2>
          <p className="muted">{idle ? t("Pick a company above and run the analysts. You will see the evidence shared, three analysts reason at once, a Red Team argue the other side, and a committee weigh what survives.", "ऊपर से कंपनी चुनिए और विश्लेषक चलाइए। आप देखेंगे कि सबूत साझा होते हैं, तीन विश्लेषक साथ सोचते हैं, रेड टीम दूसरा पक्ष रखती है, और समिति बचे हुए दावे तौलती है।")
            : running ? t(`Working… ${seconds}s. Every movement below is something the server just did.`, `काम चल रहा है… ${seconds} सेकंड। नीचे हर हलचल सर्वर ने अभी की है।`)
            : conviction ? t("Finished. Below the picture: the same result in plain words.", "पूरा हुआ। चित्र के नीचे: वही नतीजा सरल शब्दों में।") : ""}</p>
        </div>
      </header>

      <ol className="arena-steps">
        {steps.map((s, i) => (<li key={s.id} className={s.s}><span className="dot" aria-hidden>{s.s === "done" ? "✓" : i + 1}</span>{hi ? s.hi : s.en}</li>))}
      </ol>

      <div className="arena-stage">
        <svg viewBox={`0 0 ${W} ${H}`} className="arena-svg" role="img" aria-label={t("Evidence flows to three analyst desks; their claims go to a committee balance; the Red Team argues the opposite side", "सबूत तीन विश्लेषक डेस्क तक जाते हैं; उनके दावे समिति के तराज़ू तक; रेड टीम उलटा पक्ष रखती है")}>
          {/* evidence pool */}
          {GROUPS.map((g) => {
            const items = byGroup[g.id];
            return (
              <g key={g.id} transform={`translate(24,${g.y})`}>
                <text x="0" y="0" className="ar-label">{hi ? g.hi : g.en}<tspan className="ar-count"> {items.length || ""}</tspan></text>
                {items.slice(0, 32).map((e, i) => (
                  <rect key={e.id} x={(i % 8) * 15} y={10 + Math.floor(i / 8) * 15} width="11" height="11" rx="3"
                        className={`ar-ev ${cited.has(e.id) ? "cited" : ""} ${lit.includes(e.id) ? "lit" : ""}`}
                        onClick={() => select({ id: e.id, label: e.text, kind: "fact", detail: `${e.source_name} · ${e.published_at.slice(0, 10)}`, uri: e.source_uri })}>
                    <title>{e.text}</title>
                  </rect>))}
                {!items.length && <rect x="0" y="10" width="118" height="11" rx="3" className="ar-ev empty" />}
              </g>);
          })}

          {/* the shared lines: evidence -> every desk */}
          {[...ANALYSTS, RED].map((n) => {
            const p = curve(168, 170, 250, DESK_Y[n]);
            const thinking = state(n) === "thinking";
            return (<g key={n}>
              <path d={p} className={`ar-line ${thinking ? "on" : ""}`} />
              {thinking && [0, 1, 2, 3].map((k) => (<circle key={k} r="2.6" className="ar-pulse"><animateMotion dur="2.2s" begin={`${k * 0.55}s`} repeatCount="indefinite" path={p} /></circle>))}
            </g>);
          })}

          {/* desks */}
          {[...ANALYSTS, RED].map((n) => {
            const st = state(n), d = desks[n];
            const mine = tokens.filter((x) => x.c.desk === n).length;
            const drop = rejected.filter((r) => r.desk === n).length;
            return (
              <g key={n} transform={`translate(250,${DESK_Y[n] - 27})`} className={`ar-desk ${st} ${n === RED ? "red" : ""}`}>
                {st === "thinking" && <rect x="-5" y="-5" width="170" height="64" rx="16" className="ar-ring" />}
                <rect width="160" height="54" rx="12" className="ar-desk-box" />
                <text x="14" y="23" className="ar-desk-name">{dispName(n)}</text>
                <text x="14" y="41" className="ar-desk-sub">
                  {st === "thinking" ? (n === RED ? (desks[RED]?.note ?? t("arguing the other side", "दूसरा पक्ष रख रही है")) : t("reasoning…", "सोच रहे हैं…")) : st === "waiting" ? t("waits for the analysts", "विश्लेषकों का इंतज़ार") : st === "done" ? `${mine} ${t("claims", "दावे")}${drop ? ` · ${drop} ${t("dropped", "हटे")}` : ""}${d?.ms ? ` · ${(d.ms / 1000).toFixed(1)}s` : ""}` : st === "failed" ? t("did not finish", "पूरा नहीं हुआ") : t("ready", "तैयार")}
                </text>
                {st === "done" && <path d="M138 20l5 5 9-10" className="ar-tick" />}
              </g>);
          })}

          {/* the Red Team reads the analysts' conclusions */}
          <path d="M236,70 L236,352 L250,352" className={`ar-line dashed ${state(RED) === "thinking" ? "on" : ""}`} />
          <path d="M236,170 L242,170 M236,270 L242,270" className="ar-line dashed" />
          {state(RED) === "thinking" && [0, 1, 2].map((k) => (<circle key={k} r="2.6" className="ar-pulse red"><animateMotion dur="2s" begin={`${k * 0.65}s`} repeatCount="indefinite" path="M236,70 L236,352" /></circle>))}

          {/* committee: a balance */}
          <text x="660" y="116" textAnchor="middle" className="ar-label">{t("Committee", "समिति")}</text>
          <g style={{ transform: `rotate(${tilt}deg)`, transformOrigin: "660px 175px", transition: "transform 1s cubic-bezier(.2,.7,.2,1)" }}>
            <line x1="548" x2="772" y1="175" y2="175" className="ar-beam" />
            <circle cx="548" cy="175" r="4" className="ar-beam-end good" /><circle cx="772" cy="175" r="4" className="ar-beam-end bad" />
          </g>
          <path d="M660,175 l-9,24 h18z" className="ar-pivot" />
          <rect x={L.x} y={BIN_Y} width={L.w} height="104" rx="12" className="ar-bin good" /><rect x={Rr.x} y={BIN_Y} width={Rr.w} height="104" rx="12" className="ar-bin bad" />
          <text x={L.x + L.w / 2} y={BIN_Y + 122} textAnchor="middle" className="ar-label good">{t("Supports", "पक्ष में")} <tspan className="ar-count">{wBull ? wBull.toFixed(1) : ""}</tspan></text>
          <text x={Rr.x + Rr.w / 2} y={BIN_Y + 122} textAnchor="middle" className="ar-label bad">{t("Cautions", "सावधानी")} <tspan className="ar-count">{wBear ? wBear.toFixed(1) : ""}</tspan></text>

          {/* claims travelling from a desk to its side of the balance; dropped ones fade on the way */}
          {tokens.map(({ c, i, side, idx }) => {
            const to = slot(side, idx);
            const p = curve(410, DESK_Y[c.desk] ?? 170, to.x, to.y);
            return (<circle key={`c${i}`} r={4 + Math.min(4, c.weight * 5)} cx="0" cy="0" className={`ar-token ${side} ${c.desk === RED ? "red" : ""}`}
                            onClick={() => setLit(c.source_ids)} onMouseEnter={() => setLit(c.source_ids)} onMouseLeave={() => setLit([])}>
              <title>{`${c.desk}: ${c.claim}`}</title>
              <animateMotion dur="1s" begin="0s" fill="freeze" path={p} calcMode="spline" keySplines=".2 .7 .2 1" keyTimes="0;1" />
            </circle>);
          })}
          {rejected.map((r, i) => {
            const p = curve(410, DESK_Y[r.desk] ?? 170, 500, (DESK_Y[r.desk] ?? 170) + 30);
            return (<g key={`r${i}`} className="ar-drop"><circle r="4" cx="0" cy="0"><animateMotion dur="1s" fill="freeze" path={p} /></circle>
              <text x="505" y={(DESK_Y[r.desk] ?? 170) + 34} className="ar-drop-l">✕ {t("no valid citation", "सही हवाला नहीं")}</text></g>);
          })}

          {/* the outcome */}
          <path d="M772,175 L806,175" className={`ar-line ${conviction ? "on" : ""}`} />
          <g transform="translate(806,138)" className={`ar-out ${conviction ? "ready" : ""}`}>
            <rect width="82" height="74" rx="14" className="ar-out-box" />
            <text x="41" y="30" textAnchor="middle" className="ar-out-t">{t("Plain", "सरल")}</text>
            <text x="41" y="48" textAnchor="middle" className="ar-out-t">{t("summary", "सारांश")}</text>
            {conviction && <path d="M30 60l8 7 14-14" className="ar-tick" />}
          </g>
        </svg>
      </div>

      <dl className="arena-stats">
        <div><dt>{t("Evidence shared", "साझा सबूत")}</dt><dd>{evItems.length || "—"}</dd></div>
        <div><dt>{t("Claims kept", "रखे गए दावे")}</dt><dd>{claims.length}</dd></div>
        <div><dt>{t("Dropped (no citation)", "हटाए (हवाला नहीं)")}</dt><dd>{rejected.length}</dd></div>
        <div><dt>{t("Analysts agree", "विश्लेषक सहमत")}</dt><dd>{conviction ? `${Math.round(conviction.agreement * 100)}%` : consensus ? `${Math.round((Math.max(consensus.bull, consensus.bear) / ((consensus.bull + consensus.bear) || 1)) * 100)}%` : "—"}</dd></div>
        <div><dt>{t("Evidence quality", "सबूत की गुणवत्ता")}</dt><dd>{conviction ? `${Math.round(conviction.evidence_quality * 100)}%` : "—"}</dd></div>
      </dl>

      {conviction?.groupthink && <p className="arena-note">{t("The analysts agreed closely. Models trained alike agree more than independent people would, so that agreement counts for less, not more.", "विश्लेषक बहुत हद तक सहमत रहे। एक जैसे मॉडल स्वतंत्र लोगों से ज़्यादा सहमत होते हैं, इसलिए यह सहमति कम गिनी जाती है, ज़्यादा नहीं।")}</p>}
      {conviction?.dissent && <p className="arena-dissent"><b>{t("The Red Team's best counter-case:", "रेड टीम का सबसे मज़बूत उलटा तर्क:")}</b> {conviction.dissent}</p>}
      {claims.length > 0 && (
        <ul className="arena-feed" aria-label={t("Claims so far", "अब तक के दावे")}>
          {claims.slice(-5).reverse().map((c, i) => (
            <li key={claims.length - i} className={c.stance} onMouseEnter={() => setLit(c.source_ids)} onMouseLeave={() => setLit([])}>
              <span className="who">{dispName(c.desk)}</span><span className="side">{c.stance === "bear" ? t("cautions", "सावधानी") : c.stance === "bull" ? t("supports", "पक्ष में") : ""}</span><span className="txt">{c.claim}</span>
              <span className="cites">{c.source_ids.length} {t("cited", "हवाले")}</span>
            </li>))}
        </ul>)}
    </section>
  );
}
