import { create } from "zustand";

export type ThemePref = "system" | "light" | "dark";
const KEY = "jarvis.theme";

const system = (): "light" | "dark" => (window.matchMedia?.("(prefers-color-scheme: light)").matches ? "light" : "dark");
const read = (): ThemePref => { try { const v = localStorage.getItem(KEY); return v === "dark" ? "dark" : "light"; } catch { return "system"; } };
export const resolved = (p: ThemePref): "light" | "dark" => (p === "system" ? system() : p);

function apply(p: ThemePref): void {
  document.documentElement.dataset.theme = resolved(p);
  window.dispatchEvent(new Event("jarvis:theme"));                  // charts that draw to a canvas re-read their colours
}

interface ThemeState { pref: ThemePref; theme: "light" | "dark"; set: (p: ThemePref) => void; toggle: () => void }

export const useTheme = create<ThemeState>((set, get) => ({
  pref: read(), theme: resolved(read()),
  set: (pref) => { try { if (pref === "system") localStorage.removeItem(KEY); else localStorage.setItem(KEY, pref); } catch { /* storage blocked */ } apply(pref); set({ pref, theme: resolved(pref) }); },
  toggle: () => get().set(get().theme === "dark" ? "light" : "dark"),
}));

apply(read());
window.matchMedia?.("(prefers-color-scheme: light)").addEventListener?.("change", () => { if (useTheme.getState().pref === "system") { apply("system"); useTheme.setState({ theme: system() }); } });
