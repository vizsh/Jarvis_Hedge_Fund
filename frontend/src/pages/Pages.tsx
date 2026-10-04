import { StockSearch } from "../components/StockSearch";
import { useT } from "../lib/i18n";
import { ChatThread } from "../components/ChatThread";
import { GoalFan } from "./Demos";
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
// Home is a menu, not a long page: one screen of doors. Each opens its own page.
const TILES: { to: string; icon: string; en: [string, string]; hi: [string, string] }[] = [
  { to: "/portfolio", icon: "📊", en: ["Portfolio", "What you own, how it is spread, what to do next."], hi: ["पोर्टफोलियो", "आपके पास क्या है, कैसे बँटा है, आगे क्या करें।"] },
  { to: "/protect", icon: "🛡️", en: ["Protect", "Check a tip, a scam call, or what to do after losing money."], hi: ["सुरक्षा", "टिप, ठग कॉल की जाँच, या पैसे गँवाने के बाद क्या करें।"] },
  { to: "/rural", icon: "🌾", en: ["Rural", "Moneylender interest, government schemes, harvest planning."], hi: ["ग्रामीण", "साहूकार का ब्याज, सरकारी योजनाएँ, फ़सल के हिसाब से योजना।"] },
  { to: "/whatsapp", icon: "📱", en: ["WhatsApp", "The same tools as a phone chat: menu, voice notes, Hindi. Ready for a real number."], hi: ["व्हाट्सऐप", "वही औज़ार फ़ोन चैट में: मेनू, वॉइस नोट, हिंदी। असली नंबर के लिए तैयार।"] },
  { to: "/learn", icon: "📘", en: ["Learn", "Ask in plain words, test a crash, see where numbers come from."], hi: ["सीखें", "सरल शब्दों में पूछिए, गिरावट आज़माइए, आँकड़ों का स्रोत देखिए।"] },
  { to: "/practice", icon: "🎯", en: ["Practice", "Fee slider, emergency meter, fund overlap, scam-call rehearsal."], hi: ["अभ्यास", "फ़ीस स्लाइडर, इमरजेंसी मीटर, फ़ंड ओवरलैप, ठग कॉल का अभ्यास।"] },
  { to: "/govern", icon: "⚖️", en: ["Govern", "Try a trade against your limits, rebalance, audit trail."], hi: ["नियम", "अपनी सीमाओं में ट्रेड परखिए, रीबैलेंस, ऑडिट रिकॉर्ड।"] },
  { to: "/research", icon: "🔎", en: ["Research", "Analyse any listed stock, with the desks' views and evidence."], hi: ["शोध", "कोई भी सूचीबद्ध शेयर परखिए, विश्लेषकों की राय और सबूत के साथ।"] },
  { to: "/assistant", icon: "💬", en: ["Assistant", "Talk or type. It opens the right page and does the task."], hi: ["सहायक", "बोलिए या लिखिए। यह सही पेज खोलकर काम कर देता है।"] },
];

export function Home() {
  const { t, hi } = useT();
  return (
    <Page title="Know what you own. Stay in control."
          lead={t("A plain-language guard for your money. Pick where to go, or just ask the assistant at the bottom right.", "आपके पैसे की सरल भाषा में निगरानी। जहाँ जाना हो चुनिए, या नीचे दाएँ सहायक से सीधे पूछिए।")}>
      <nav className="tiles" aria-label={t("Pages", "पेज")}>
        {TILES.map((x) => (
          <a className="tile" key={x.to} href={"#" + x.to}>
            <span className="tile-ic" aria-hidden>{x.icon}</span>
            <h2>{hi ? x.hi[0] : x.en[0]}</h2>
            <p>{hi ? x.hi[1] : x.en[1]}</p>
            <span className="tile-go">{t("Open", "खोलें")} →</span>
          </a>
        ))}
      </nav>
    </Page>
  );
}

/* ------------------------------------------------------------ Portfolio */
export function Portfolio() {
  const setBuilder = useUI((s) => s.setBuilder);
  return (
    <Page title="Portfolio" lead="What you own, how it is spread, and how it has behaved. Click any number to see how it was worked out.">
      <div className="grid"><ActionQueue /></div>
      <div className="grid g2">
        <XRayPanel onOpenBuilder={() => setBuilder(true)} />
        <div className="stack"><PortfolioChart /><ProfileSwitch /></div>
      </div>
      <div className="grid g2"><div className="stack"><PositionsPanel /><AttributionPanel /></div><CorrelationPanel /></div>
    </Page>
  );
}

/* ------------------------------------------------------------ Learn */
function Glossary() {
  const { hi, t } = useT();
  const [terms, setTerms] = useState<Record<string, string>>({});
  const [all, setAll] = useState(false);
  useEffect(() => { fetch(`/glossary?lang=${hi ? "hi" : "en"}`).then((r) => r.json()).then((d) => setTerms(d.terms ?? {})).catch(() => {}); }, [hi]);
  return (
    <section className="card">
      <h2>{t("Plain-English glossary", "सरल शब्दकोश")}</h2>
      <p className="muted">{t("The words finance uses to sound complicated, in one sentence each.", "वित्त के वे शब्द जो मुश्किल लगते हैं, एक-एक वाक्य में।")}</p>
      {Object.entries(terms).slice(0, all ? 200 : 7).map(([k, v]) => (
        <details key={k} className="gloss"><summary>{k}</summary><p>{v}</p></details>
      ))}
      {Object.keys(terms).length > 7 && <button className="btn ghost sm" style={{ marginTop: 8 }} onClick={() => setAll(!all)}>{all ? t("Show fewer", "कम दिखाएँ") : t(`Show all ${Object.keys(terms).length} terms`, `सभी ${Object.keys(terms).length} शब्द दिखाएँ`)}</button>}
    </section>
  );
}

export function Learn() {
  const { t } = useT();
  return (
    <Page title="Learn" lead={t("Ask in your own words, see what a crash would do to you, and find out where every number comes from.", "अपने शब्दों में पूछिए, देखिए कि गिरावट का आप पर क्या असर होगा, और जानिए कि हर आँकड़ा कहाँ से आता है।")}>
      <div className="grid"><GoalFan /></div>
      <div className="grid g2">
        <div className="stack">
          <AskPanel />
          <section className="card">
            <h2>{t("Every number is a door", "हर आँकड़ा एक दरवाज़ा है")}</h2>
            <p className="muted">{t("Click any underlined figure to see what it is made of, the formula, and the exact prices and dates behind it.", "रेखांकित किसी भी आँकड़े को दबाइए और देखिए कि वह किससे बना है, उसका सूत्र क्या है, और उसके पीछे के सही भाव और तारीख़ें क्या हैं।")}</p>
            <p className="tryit">{t("Try it: your technology share is", "आज़माइए: आपका टेक्नोलॉजी हिस्सा है")} <Num metric="sector" k="IT" value={t("this number", "यह आँकड़ा")} /> {t("— or your overall", "— या आपका कुल")} <Num metric="score" value={t("score", "स्कोर")} />.</p>
          </section>
        </div>
        <Glossary />
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
        <StockSearch />
        <p className="faint small">Runs entirely on this machine. The track record of each desk is shown below —
          including the ones that do worse than a coin flip.</p>
      </section>
      <div className="grid g2"><DeskPanel /><ConvictionPanel /></div>
      <div className="grid g2">
        <div className="stack"><ClaimsPanel /><SourcesPanel /><section className="card"><h2>Time machine</h2>
          <p className="muted">Rewind the clock: the analysts can then only see what was known on that day.</p><Scrubber /></section></div>
        <CalibrationPanel />
      </div>
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
      <ChatThread />
      <div className="assistant-side"><JobsLauncher compact /></div>
      <div className="assistant-bottom"><CommandBar /></div>
    </div>
  );
}

export { go };
