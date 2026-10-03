// The guide's state on the client. The server runs the conversation (what is asked, what each answer
// fills in); this only follows it: open the page it names, remember the open question so the dock
// can show it from any page, and let a tap on a choice answer it.
import { create } from "zustand";

import { go } from "./router";

export interface Guide {
  tool: string | null;
  route: string | null;
  label?: string;
  navigate: boolean;
  done: boolean;
  params: Record<string, string>;
  ask?: { slot: string; question: string; example?: string; optional?: boolean; choices?: { text: string; label: string }[] | null } | null;
  say?: string | null;
  next?: string[];
  step?: [number, number] | null;
  cancelled?: boolean;
}

interface PilotState {
  guide: Guide | null;
  set: (g: Guide | null) => void;
}

export const usePilot = create<PilotState>((set) => ({ guide: null, set: (guide) => set({ guide }) }));

/** Do what the guide says: show the open question, and move to its page. */
export function follow(g: Guide): void {
  usePilot.getState().set(g.cancelled ? null : g);
  if (g.navigate && g.route) {
    const q = new URLSearchParams(g.params ?? {}).toString();
    go(`${g.route}${q ? "?" + q : ""}`);
  }
}

/** Pages that carry the answer with them, for answers that are not part of a guided conversation. */
export function followVisual(v: { page: string; params?: Record<string, unknown> }): void {
  const q = new URLSearchParams(Object.entries(v.params ?? {}).map(([k, x]) => [k, String(x)])).toString();
  go(`/${v.page}${q ? "?" + q : ""}`);
}
