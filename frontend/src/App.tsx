import { Fragment, useEffect } from "react";

import { connect } from "./lib/socket";
import { installBargeIn } from "./lib/bargein";
import { go, useRoute, useHash } from "./lib/router";
import { initVoices } from "./lib/speak";
import { useGuide } from "./lib/guide";
import { useUI } from "./lib/ui";
import { Dock, TopNav } from "./components/Nav";
import { FlowRunner } from "./components/Flow";
import { Palette } from "./components/Palette";
import { DrillDown } from "./components/DrillDown";
import { ReportView } from "./components/Report";
import { PortfolioBuilder } from "./components/Portfolio";
import Protect from "./pages/Protect";
import Rural from "./pages/Rural";
import WhatsApp from "./pages/WhatsApp";
import { KioskBar } from "./components/KioskBar";
import { useKiosk } from "./lib/kiosk";
import Govern from "./pages/Govern";
import Practice from "./pages/Practice";
import { Assistant, Home, Learn, Portfolio, Research } from "./pages/Pages";
import { TourOverlay } from "./components/TourOverlay";
import { featureOf, useSetup } from "./lib/setup";
import { Locked, Setup } from "./pages/Setup";

// Where each named panel lives, so the command palette and guided flows can send you there.
const PANEL_ROUTE: Record<string, string> = {
  xray: "/portfolio", chart: "/portfolio", positions: "/portfolio", correlation: "/portfolio",
  attribution: "/portfolio", stress: "/learn", glossary: "/learn",
  tax: "/protect", watchlist: "/protect", lots: "/protect",
  rebalance: "/govern", screener: "/govern", sandbox: "/govern",
  desks: "/research", calibration: "/research", claims: "/research",
  actions: "/", assistant: "/assistant",
};

export default function App() {
  const route = useRoute();
  const hash = useHash();
  const epoch = useKiosk((s) => s.epoch);
  const kiosk = useKiosk((s) => s.on);
  const builder = useUI((s) => s.builder);
  const setBuilder = useUI((s) => s.setBuilder);
  const setReport = useGuide((s) => s.setReport);

  useEffect(() => { connect(); initVoices(); installBargeIn(); void useSetup.getState().load(); }, []);
  const setupState = useSetup();
  const setupFeatures = setupState.features;
  // First visit: go to setup once, then never force it again.
  useEffect(() => { if (setupState.loaded && !setupState.done && route !== "/setup") go("/setup"); }, [setupState.loaded, setupState.done, route]);

  useEffect(() => {
    const onOpen = (e: Event) => {
      const panel = (e as CustomEvent<string>).detail;
      if (panel === "builder") setBuilder(true);
      else if (panel === "report") setReport(true);
      else if (PANEL_ROUTE[panel]) go(PANEL_ROUTE[panel]);
    };
    window.addEventListener("jarvis:open", onOpen);
    return () => window.removeEventListener("jarvis:open", onOpen);
  }, [setBuilder, setReport]);

  const isLocked = route !== "/" && route !== "/setup" && !setupFeatures.includes(featureOf(route));
  const page =
    isLocked ? <Locked route={route} />
    : route === "/portfolio" ? <Portfolio />
    : route === "/protect" ? <Protect key={hash} />
    : route === "/rural" ? <Rural key={hash} />
    : route === "/whatsapp" ? <WhatsApp />
    : route === "/learn" ? <Learn key={hash} />
    : route === "/practice" ? <Practice key={hash} />
    : route === "/govern" ? <Govern />
    : route === "/research" ? <Research />
    : route === "/assistant" ? <Assistant />
    : route === "/setup" ? <Setup />
    : <Home />;

  return (
    <div className={`app ${route === "/assistant" ? "is-assistant" : ""} ${kiosk ? "kiosk" : ""}`}>
      <KioskBar />
      <TopNav />
      <div className="app-body"><Fragment key={epoch}>{page}</Fragment></div>
      <Dock key={epoch} />
      {builder && <PortfolioBuilder onClose={() => setBuilder(false)} />}
      <FlowRunner />
      <Palette />
      <DrillDown />
      <ReportView />
      <TourOverlay />
    </div>
  );
}
