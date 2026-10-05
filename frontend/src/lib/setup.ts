// The prototype's setup: which features this install shows, the five starting baskets, and the (dummy) price.
import { create } from "zustand";

export interface Feat { id: string; route: string; tier: "free" | "paid"; price: number; en: string; hi: string; blurb: string; blurb_hi: string }
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

/** The feature id for a route, e.g. "/portfolio" -> "portfolio". "/" is home. */
export function featureOf(route: string): string {
  const p = route.replace(/^\/+/, "").split("?")[0];
  return p === "" ? "home" : p;
}
