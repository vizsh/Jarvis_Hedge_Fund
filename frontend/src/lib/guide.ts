// The guidance layer's own state: which flow is running, what the palette is showing,
// which number is open for inspection.
//
// Kept out of the main WebSocket store on purpose. Everything in `store.ts` describes
// what the BACKEND believes; everything here describes where the USER is. Mixing the
// two means a socket event can close a dialog the person is reading, which is the kind
// of bug that only ever shows up in front of an audience.

import { create } from "zustand";

import { allowSpeech, speak, stop as stopSpeech } from "./speak";
import { useLang } from "./lang";

export interface FlowStep {
  kind: "say" | "show" | "choose" | "ask" | "confirm" | "done";
  text: string;
  panel: string | null;
  endpoint: string | null;
  question: string | null;
  options: { key: string; label: string; consequence: string; endpoint: string | null }[];
  speak: boolean;
  note: string | null;
}

export interface Flow {
  id: string;
  title: string;
  subtitle: string;
  icon: string;
  minutes: number;
  audience: string;
  step_count: number;
  steps?: FlowStep[];
}

export interface Action {
  id: string;
  severity: "urgent" | "important" | "opportunity" | "ok";
  title: string;
  detail: string;
  why: string;
  cta: string;
  flow: string | null;
  question: string | null;
  stake: number;
  deadline_days: number | null;
  deadline_label: string | null;
  data: Record<string, unknown>;
  rank: number;
}

interface GuideState {
  // flow runner
  flow: Flow | null;
  step: number;
  stepData: unknown;            // whatever this step's endpoint returned
  stepBusy: boolean;
  guidedVoice: boolean;         // read each beat aloud

  // overlays — at most one is open at a time
  palette: boolean;
  drill: { metric: string; key?: string } | null;
  report: boolean;
  onboarding: boolean;

  // which panel a flow has asked the shell to raise
  highlight: string | null;

  startFlow: (id: string) => Promise<void>;
  next: () => Promise<void>;
  back: () => Promise<void>;
  endFlow: () => void;
  setGuidedVoice: (on: boolean) => void;

  openPalette: () => void;
  closePalette: () => void;
  openDrill: (metric: string, key?: string) => void;
  closeDrill: () => void;
  setReport: (on: boolean) => void;
  setOnboarding: (on: boolean) => void;
}

export const useGuide = create<GuideState>((set, get) => ({
  flow: null,
  step: 0,
  stepData: null,
  stepBusy: false,
  guidedVoice: true,
  palette: false,
  drill: null,
  report: false,
  onboarding: false,
  highlight: null,

  startFlow: async (id) => {
    const res = await fetch(`/flows/${id}?lang=${useLang.getState().lang}`);
    const flow: Flow = await res.json();
    if (!flow?.steps?.length) return;
    // Opening a flow closes everything else. Two overlays at once is never what
    // somebody wanted, and the one underneath is unreachable anyway.
    set({ flow, step: 0, stepData: null, palette: false, drill: null, report: false });
    await runStep(set, get, 0);
  },

  next: async () => {
    const { flow, step } = get();
    if (!flow?.steps) return;
    if (step >= flow.steps.length - 1) {
      get().endFlow();
      return;
    }
    await runStep(set, get, step + 1);
  },

  back: async () => {
    const { step } = get();
    if (step <= 0) return;
    await runStep(set, get, step - 1);
  },

  endFlow: () => {
    stopSpeech();
    set({ flow: null, step: 0, stepData: null, highlight: null });
  },

  setGuidedVoice: (guidedVoice) => {
    if (!guidedVoice) stopSpeech();
    set({ guidedVoice });
  },

  openPalette: () => set({ palette: true, drill: null }),
  closePalette: () => set({ palette: false }),
  openDrill: (metric, key) => set({ drill: { metric, key }, palette: false }),
  closeDrill: () => set({ drill: null }),
  setReport: (report) => set({ report, palette: false }),
  setOnboarding: (onboarding) => set({ onboarding, palette: false }),
}));

/** Advance to a step: raise its panel, fetch its numbers, and read it aloud. */
async function runStep(
  set: (p: Partial<GuideState>) => void,
  get: () => GuideState,
  index: number,
): Promise<void> {
  const { flow, guidedVoice } = get();
  const step = flow?.steps?.[index];
  if (!step) return;

  set({ step: index, stepBusy: true, stepData: null, highlight: step.panel });

  // Speaking is the whole point of a guided flow, so a step that wants to be spoken
  // must clear any earlier Stop latch — otherwise the tour runs in silence and looks
  // broken rather than muted.
  // The step wording arrives in the chosen language (see /flows?lang=), so it is spoken in it.
  const lang = useLang.getState().lang;
  if (guidedVoice && step.speak && step.text) {
    allowSpeech();
    speak(step.text, lang);
  }

  if (step.kind === "ask" && step.question) {
    try {
      const res = await fetch("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: step.question }),
      });
      set({ stepData: await res.json() });
    } catch {
      set({ stepData: null });
    }
  } else if (step.endpoint) {
    try {
      // the x-ray carries finding sentences, so it is asked for in the chosen language
      const url = step.endpoint.startsWith("/xray") ? `${step.endpoint}${step.endpoint.includes("?") ? "&" : "?"}lang=${lang}` : step.endpoint;
      const res = await fetch(url);
      set({ stepData: await res.json() });
    } catch {
      set({ stepData: null });
    }
  }
  set({ stepBusy: false });
}

/** Run an option's side effect (switch profile, refetch a variant) and continue. */
export async function chooseOption(endpoint: string | null): Promise<void> {
  if (endpoint) {
    const method = endpoint.startsWith("/profiles") ? "POST" : "GET";
    try {
      await fetch(endpoint, { method });
    } catch {
      /* a failed option must not strand the flow */
    }
  }
  await useGuide.getState().next();
}
