// The prototype's setup: which features this install shows, the five starting baskets, and the (dummy) price.
import { create } from "zustand";

export interface Feat { id: string; group: string; route: string; tier: "free" | "paid"; price: number; en: string; hi: string; blurb: string; blurb_hi: string }
export interface Persona { id: string; en: string; hi: string; who: string; who_hi: string; features: string[]; price: number }

interface SetupState {
  loaded: boolean;
  done: boolean;
  features: string[];          // ids the menu shows (home is always there)
  all: Feat[];                 // every feature, home first
  personas: Persona[];
  load: () => Promise<void>;
  save: (persona: string | null, features: string[]) => Promise<void>;
}

export const useSetup = create<SetupState>((set) => ({
  loaded: false, done: false, features: ["home"], all: [], personas: [],
  load: async () => {
    try {
      const r = await fetch("/setup");
      const d = await r.json();
      set({ loaded: true, done: d.current.done, features: d.current.features, all: d.features, personas: d.personas });
    } catch {
      set({ loaded: true, done: true, features: ["home"] });   // backend down: keep the menu usable rather than lock everything
    }
  },
  save: async (persona, features) => {
    const r = await fetch("/setup", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ persona, features }) });
    const d = await r.json();
    set({ done: true, features: d.current.features });
  },
}));

/** The four loss channels (docs/CONTEXT.md section 4). Features are grouped by the loss they address, not by price. */
export const GROUP_LABEL: Record<string, { en: string; hi: string; blurb: string; blurb_hi: string }> = {
  fraud:  { en: "Fraud shield", hi: "ठगी से बचाव", blurb: "Scam scripts, calls and the first hour after a loss.", blurb_hi: "ठगी के तरीक़े, कॉल और नुकसान के बाद का पहला घंटा।" },
  credit: { en: "Credit cost", hi: "क़र्ज़ की लागत", blurb: "What informal and formal loans really cost, in rupees a year.", blurb_hi: "अनौपचारिक और औपचारिक क़र्ज़ का असल सालाना ख़र्च, रुपयों में।" },
  invest: { en: "Investing protection", hi: "निवेश की सुरक्षा", blurb: "Fees, overlap, tips and company research, shown as arithmetic.", blurb_hi: "फ़ीस, ओवरलैप, टिप और कंपनी शोध, हिसाब के साथ।" },
  reach:  { en: "Reach and trust", hi: "पहुँच और भरोसा", blurb: "Language, phone access, plain lessons and an audit record.", blurb_hi: "भाषा, फ़ोन की पहुँच, सरल पाठ और ऑडिट रिकॉर्ड।" },
};

/** The feature id for a route, e.g. "/portfolio" -> "portfolio". "/" is home. */
export function featureOf(route: string): string {
  const p = route.replace(/^\/+/, "").split("?")[0];
  return p === "" ? "home" : p;
}
