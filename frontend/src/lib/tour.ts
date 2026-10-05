// Guided tours: the page plays a feature's walk-through on screen while the caption is read aloud.
//
// The steps come from the server (backend/tours.py: one source for the chat's text answer and for this player),
// in the language the person has chosen. A step is "open this page, press this, spotlight that, say this".
// The player never fails on a missing element: it shows the caption without a spotlight.

import { create } from "zustand";

import { useLang } from "./lang";
import { go } from "./router";
import { allowSpeech, getState, interrupt, onVoice, speak, voiceReplies } from "./speak";

export interface TourStep { route: string; sel: string | null; click: string | null; title: string; body: string }
export interface Tour { id: string; title: string; route: string; steps: TourStep[] }
export interface TourEntry { id: string; title: string; blurb: string; steps: number; route: string }

interface TourState {
  tour: Tour | null;
  i: number;
  auto: boolean;
  loading: boolean;
  done: boolean;
  start: (id: string) => Promise<void>;
  goTo: (i: number) => void;
  next: () => void;
  prev: () => void;
  stop: () => void;
  setAuto: (on: boolean) => void;
}

let advance: number | null = null;
const clearAdvance = () => { if (advance != null) { window.clearTimeout(advance); advance = null; } };

export const useTour = create<TourState>((set, get) => ({
  tour: null, i: 0, auto: true, loading: false, done: false,

  start: async (id) => {
    clearAdvance();
    interrupt();
    set({ loading: true, done: false });
    try {
      const lang = useLang.getState().lang;
      const r = await fetch(`/tours/${encodeURIComponent(id)}?lang=${lang}`);
      if (!r.ok) throw new Error("no tour");
      const tour: Tour = await r.json();
      set({ tour, i: 0, loading: false, done: false });
      allowSpeech();
    } catch {
      set({ loading: false, tour: null });
    }
  },

  goTo: (i) => {
    const t = get().tour;
    if (!t) return;
    clearAdvance();
    if (i >= t.steps.length) { set({ i: t.steps.length - 1, done: true }); interrupt(); return; }
    set({ i: Math.max(0, i), done: false });
  },
  next: () => get().goTo(get().i + 1),
  prev: () => get().goTo(get().i - 1),
  stop: () => { clearAdvance(); interrupt(); set({ tour: null, i: 0, done: false }); },
  setAuto: (on) => { clearAdvance(); set({ auto: on }); },
}));

/** Read a caption aloud and report when it has finished (or immediately, when the voice is off). */
export function narrate(text: string, lang: string, onEnd: () => void): () => void {
  if (!voiceReplies()) {
    // No voice: leave the caption up long enough to read at a comfortable pace.
    const ms = Math.max(5500, text.split(/\s+/).length * 330);
    const id = window.setTimeout(onEnd, ms);
    return () => window.clearTimeout(id);
  }
  let started = false;
  let finished = false;
  const off = onVoice((s) => {
    if (s === "speaking") started = true;
    else if (started && !finished && (s === "idle" || s === "stopped")) {
      finished = true;
      advance = window.setTimeout(onEnd, 900);
    }
  });
  speak(text, lang === "hi" ? "hi" : "en");
  // If nothing started (muted, or the voice is unavailable), fall back to reading time.
  const guard = window.setTimeout(() => {
    if (!started && getState() !== "speaking") {
      finished = true;
      advance = window.setTimeout(onEnd, Math.max(4500, text.split(/\s+/).length * 300));
    }
  }, 2500);
  return () => { off(); window.clearTimeout(guard); clearAdvance(); };
}

export function startTour(id: string): void { void useTour.getState().start(id); }

export function openRoute(route: string): void {
  const want = route.startsWith("/") ? route : "/" + route;
  const cur = location.hash.replace(/^#/, "") || "/";
  if (cur !== want) go(want);
}
