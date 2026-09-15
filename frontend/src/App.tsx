import { Canvas } from "@react-three/fiber";
import { Bloom, EffectComposer, Vignette } from "@react-three/postprocessing";
import { useEffect, useState } from "react";

import { Orb } from "./three/Orb";
import { useStore, type Phase } from "./lib/store";
import { connect, sendBoot } from "./lib/socket";
import { initVoices } from "./lib/speak";
import { CommandBar, Scrubber, TopBar } from "./components/Chrome";
import { ReplayBanner, Teleprompter } from "./components/Teleprompter";
import { CalibrationPanel } from "./components/Calibration";
import { PortfolioBuilder, ProfileSwitch } from "./components/Portfolio";
import { AskPanel, StressPanel, XRayPanel } from "./components/Insight";
import { AttributionPanel, CorrelationPanel, RebalancePanel, ScreenerPanel }
  from "./components/FundDesk";
import { PortfolioChart, TaxPanel } from "./components/Chart";
import { ActionQueue, JobsLauncher } from "./components/Actions";
import { FlowRunner } from "./components/Flow";
import { Palette } from "./components/Palette";
import { DrillDown } from "./components/DrillDown";
import { WatchlistPanel } from "./components/Watchlist";
import { ReportView } from "./components/Report";
import { useGuide } from "./lib/guide";
import {
  BootSequence, ClaimsPanel, ConvictionPanel, DeskPanel, ExecutionPanel, FundPanel,
  Inspector, LogPanel, PositionsPanel, PriceChart, RiskPanel, SourcesPanel,
} from "./components/Panels";

const HOTKEYS: Record<string, Phase> = {
  "1": "boot", "2": "core", "3": "graph", "4": "terminal", "5": "simulate", "6": "execute",
};

export default function App() {
  // Two audiences, one product. "Simple" is what a private investor needs: their
  // portfolio, what is wrong with it, and what happens if it goes badly. "Expert"
  // adds the agent mesh, the citation gate and the calibration record.
  const [mode, setMode] = useState<"simple" | "desk" | "expert">("simple");
  const [builder, setBuilder] = useState(false);
  const phase = useStore((s) => s.phase);
  const setPhase = useStore((s) => s.setPhase);
  const boot = useStore((s) => s.boot);
  const setReport = useGuide((s) => s.setReport);
  const onboarding = useGuide((s) => s.onboarding);
  const setOnboarding = useGuide((s) => s.setOnboarding);

  useEffect(() => { connect(); initVoices(); }, []);

  // The palette and the action queue need to raise panels that live in the rails.
  // A custom event is the smallest thing that does this without either component
  // having to know the shell's layout.
  useEffect(() => {
    const onOpen = (e: Event) => {
      const panel = (e as CustomEvent<string>).detail;
      if (panel === "builder") { setBuilder(true); return; }
      if (panel === "report") { setReport(true); return; }
      if (["correlation", "rebalance", "tax", "screener", "attribution"].includes(panel)) {
        setMode("desk");
      } else if (["desks", "calibration", "claims"].includes(panel)) {
        setMode("expert");
      } else {
        setMode("simple");
      }
    };
    window.addEventListener("jarvis:open", onOpen);
    return () => window.removeEventListener("jarvis:open", onOpen);
  }, [setReport]);

  // First run: land on the setup flow rather than on somebody else's money.
  useEffect(() => {
    if (localStorage.getItem("jarvis.seen")) return;
    localStorage.setItem("jarvis.seen", "1");
    setOnboarding(true);
  }, [setOnboarding]);

  useEffect(() => {
    if (!onboarding) return;
    setOnboarding(false);
    void useGuide.getState().startFlow("onboarding");
  }, [onboarding, setOnboarding]);

  // Hotkeys 1-6 pin the phase. Presenting is a live performance and the speaker needs
  // to be able to jump back to a panel without re-running a 14-second investigation.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return;
      if (HOTKEYS[e.key]) setPhase(HOTKEYS[e.key], true);
      if (e.key === "b" || e.key === "B") sendBoot();
      // R replays the golden take, E stops it. This is the break-glass path when the
      // model, the mic or the GPU has let you down in front of an audience.
      if (e.key === "r" || e.key === "R") {
        void fetch("/replay/start?name=demo", { method: "POST" });
      }
      if (e.key === "e" || e.key === "E") {
        void fetch("/replay/stop", { method: "POST" });
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setPhase]);

  const booting = phase === "boot" && boot.length > 0;

  return (
    <div className="shell">
      <div className="canvas-layer">
        <Canvas
          camera={{ position: [0, 0.35, 6.0], fov: 54 }}
          dpr={[1, 2]}
          gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
        >
          <Orb />
          <EffectComposer>
            {/* luminanceThreshold low because the particles are already dim; the
                point is to bloom the dense core, not to clip the highlights */}
            <Bloom intensity={2.4} luminanceThreshold={0.05} luminanceSmoothing={0.5}
                   mipmapBlur radius={0.72} />
            <Vignette eskil={false} offset={0.22} darkness={0.85} />
          </EffectComposer>
        </Canvas>
      </div>

      {booting && <BootSequence />}
      {builder && <PortfolioBuilder onClose={() => setBuilder(false)} />}

      {/* The guidance layer. Each of these is at most one at a time and each closes
          the others, because two stacked overlays is never what anybody wanted. */}
      <FlowRunner />
      <Palette />
      <DrillDown />
      <ReportView />

      <div className="hud" style={{ opacity: booting ? 0.12 : 1, transition: "opacity 0.6s" }}>
        <TopBar onOpenBuilder={() => setBuilder(true)} />

        <div className="rail-left">
          <div className="mode-switch">
            {(["simple", "desk", "expert"] as const).map((m) => (
              <div key={m} className={`seg-item ${mode === m ? "on" : ""}`}
                   onClick={() => setMode(m)}>
                {m === "simple" ? "My money" : m === "desk" ? "Fund desk" : "Machinery"}
              </div>
            ))}
          </div>
          {mode === "simple" ? (
            <>
              {/* The action queue leads. Everything below it answers a question; this
                  is the only panel that proposes one. */}
              <ActionQueue />
              <XRayPanel onOpenBuilder={() => setBuilder(true)} />
              <PortfolioChart />
              <ProfileSwitch />
            </>
          ) : mode === "desk" ? (
            <>
              <CorrelationPanel />
              <AttributionPanel />
              <ProfileSwitch />
            </>
          ) : (
            <>
              <DeskPanel />
              <ConvictionPanel />
              <CalibrationPanel />
              <SourcesPanel />
              <LogPanel />
            </>
          )}
        </div>

        <div className="stage">
          <ReplayBanner />
          <Teleprompter />
          <Inspector />
        </div>

        <div className="rail-right">
          {mode === "simple" ? (
            <>
              <JobsLauncher compact />
              <AskPanel />
              <WatchlistPanel />
              <StressPanel />
              <PositionsPanel />
            </>
          ) : mode === "desk" ? (
            <>
              <RebalancePanel />
              <TaxPanel />
              <ScreenerPanel />
              <PositionsPanel />
            </>
          ) : (
            <>
              <RiskPanel />
              <ExecutionPanel />
              <FundPanel />
              <PriceChart />
              <ClaimsPanel />
              <PositionsPanel />
            </>
          )}
        </div>

        <div className="bottom">
          <CommandBar />
          <Scrubber />
        </div>
      </div>
    </div>
  );
}
