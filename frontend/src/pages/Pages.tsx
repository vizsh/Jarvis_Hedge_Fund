import { Canvas } from "@react-three/fiber";
import { Bloom, EffectComposer, Vignette } from "@react-three/postprocessing";
import { useEffect, useState } from "react";

import { Page } from "./Page";
import { Orb } from "../three/Orb";
import { go } from "../lib/router";
import { send } from "../lib/socket";
import { useStore } from "../lib/store";
import { useUI } from "../lib/ui";
import { ActionQueue, JobsLauncher } from "../components/Actions";
import { CalibrationPanel } from "../components/Calibration";
import { CommandBar, Scrubber } from "../components/Chrome";
import { Num } from "../components/DrillDown";
import { AskPanel, StressPanel, XRayPanel } from "../components/Insight";
import {
  ClaimsPanel, ConvictionPanel, DeskPanel, PositionsPanel, SourcesPanel,
} from "../components/Panels";
import { ProfileSwitch } from "../components/Portfolio";
import { PortfolioChart } from "../components/Chart";
import { OrbMic } from "../components/VoiceInput";
import { CorrelationPanel, AttributionPanel } from "../components/FundDesk";

/* ------------------------------------------------------------ Home */
const PILLARS = [
  { title: "Protect", tag: "Stay safe", to: "/protect",
    body: "Paste a tip from Telegram or WhatsApp and see if the facts back it up. Find out when waiting a few days would save you tax.",
    links: [["Check a stock tip", "/protect"], ["See my tax shield", "/protect"]] },
  { title: "Learn", tag: "Understand your money", to: "/learn",
    body: "Ask anything in plain words and get a short answer. Click any number to see exactly where it came from.",
    links: [["Ask a question", "/learn"], ["Stress-test my portfolio", "/learn"]] },
  { title: "Govern", tag: "Stay inside your limits", to: "/govern",
    body: "Try a trade against your own limits, preview a fix side by side, and keep a record nobody can quietly edit.",
    links: [["Try the risk firewall", "/govern"], ["Simulate a rebalance", "/govern"]] },
];

export function Home() {
  return (
    <Page title="Know what you own. Stay in control."
          lead="A plain-language guard for your investments — it checks tips, explains your risk, and keeps every trade inside the limits you chose.">
      <div className="pillars">
        {PILLARS.map((p) => (
          <a className="pillar" key={p.title} href={"#" + p.to}>
            <div className="pillar-tag">{p.tag}</div>
            <h2>{p.title}</h2>
            <p>{p.body}</p>
            <ul>{p.links.map(([l]) => <li key={l}>{l} →</li>)}</ul>
          </a>
        ))}
      </div>
      <div className="grid g2">
        <ActionQueue />
        <div className="stack">
          <XRayPanel onOpenBuilder={() => useUI.getState().setBuilder(true)} />
          <div className="note">
            Prefer to talk? Use the microphone at the bottom right on any page — or open the{" "}
            <a href="#/assistant">full assistant</a>. You can stop it mid-sentence at any time.
          </div>
        </div>
      </div>
    </Page>
  );
}

/* ------------------------------------------------------------ Portfolio */
export function Portfolio() {
  const setBuilder = useUI((s) => s.setBuilder);
  return (
    <Page title="Portfolio" lead="What you own, how it is spread, and how it has behaved. Click any number to see how it was worked out.">
      <div className="grid g2">
        <XRayPanel onOpenBuilder={() => setBuilder(true)} />
        <div className="stack"><PortfolioChart /><ProfileSwitch /></div>
      </div>
      <div className="grid g2"><PositionsPanel /><CorrelationPanel /></div>
      <div className="grid"><AttributionPanel /></div>
    </Page>
  );
}

/* ------------------------------------------------------------ Learn */
function Glossary() {
  const [terms, setTerms] = useState<Record<string, string>>({});
  useEffect(() => { fetch("/glossary").then((r) => r.json()).then((d) => setTerms(d.terms ?? {})).catch(() => {}); }, []);
  return (
    <section className="card">
      <h2>Plain-English glossary</h2>
      <p className="muted">The words finance uses to sound complicated, in one sentence each.</p>
      {Object.entries(terms).slice(0, 12).map(([k, v]) => (
        <details key={k} className="gloss"><summary>{k}</summary><p>{v}</p></details>
      ))}
    </section>
  );
}

export function Learn() {
  return (
    <Page title="Learn" lead="Ask in your own words, see what a crash would do to you, and find out where every number comes from.">
      <div className="grid g2">
        <AskPanel />
        <div className="stack">
          <section className="card">
            <h2>Every number is a door</h2>
            <p className="muted">Click any underlined figure to see what it is made of, the formula, and the exact
              prices and dates behind it.</p>
            <p className="tryit">Try it: your technology share is <Num metric="sector" k="IT" value="this number" /> —
              or your overall <Num metric="score" value="score" />.</p>
          </section>
          <Glossary />
        </div>
      </div>
      <div className="grid"><StressPanel /></div>
    </Page>
  );
}

/* ------------------------------------------------------------ Research */
export function Research() {
  const [q, setQ] = useState("TCS");
  const orb = useStore((s) => s.orb);
  return (
    <Page title="Research desk" lead="Four AI analysts and a forced dissenter study a company. Their claims must cite real evidence, or they are thrown away.">
      <section className="card">
        <div className="row">
          <input id="research-ticker" value={q} onChange={(e) => setQ(e.target.value)}
                 onKeyDown={(e) => { if (e.key === "Enter" && q.trim()) send(`analyse ${q}`); }}
                 placeholder="Company, e.g. Infosys" style={{ flex: 1, minWidth: 160 }} />
          <button className="btn go" disabled={!q.trim() || orb === "thinking"} onClick={() => send(`analyse ${q}`)}>
            {orb === "thinking" ? "Analysing… (about 30 seconds)" : "Run the analysts"}
          </button>
        </div>
        <p className="faint small">Runs entirely on this machine. The track record of each desk is shown below —
          including the ones that do worse than a coin flip.</p>
      </section>
      <div className="grid g2"><DeskPanel /><ConvictionPanel /></div>
      <div className="grid g2"><ClaimsPanel /><CalibrationPanel /></div>
      <div className="grid g2"><SourcesPanel /><section className="card"><h2>Time machine</h2>
        <p className="muted">Rewind the clock: the analysts can then only see what was known on that day.</p><Scrubber /></section></div>
    </Page>
  );
}

/* ------------------------------------------------------------ Assistant */
export function Assistant() {
  return (
    <div className="assistant-stage">
      <div className="canvas-layer">
        <Canvas camera={{ position: [0, 0.35, 6.0], fov: 54 }} dpr={[1, 1.5]}
                gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}>
          <Orb />
          <EffectComposer>
            <Bloom intensity={2.0} luminanceThreshold={0.05} luminanceSmoothing={0.5} mipmapBlur radius={0.7} />
            <Vignette eskil={false} offset={0.22} darkness={0.85} />
          </EffectComposer>
        </Canvas>
      </div>
      <OrbMic />
      <div className="assistant-side"><JobsLauncher compact /></div>
      <div className="assistant-bottom"><CommandBar /></div>
    </div>
  );
}

export { go };
