import { create } from "zustand";

// Answer language. The choice is sent to the backend, which translates (see
// backend/vernacular.py) and also picks the Hindi voice; it is remembered per browser.
const KEY = "jarvis.lang";
const read = (): "en" | "hi" => {
  try { return localStorage.getItem(KEY) === "hi" ? "hi" : "en"; } catch { return "en"; }
};

const VKEY = "jarvis.voice.";
/** The voice chosen for a language, or undefined to use the server's default. */
export function voiceFor(lang: string): string | undefined {
  try { return localStorage.getItem(VKEY + lang) || undefined; } catch { return undefined; }
}
export function setVoiceFor(lang: string, id: string): void {
  try { localStorage.setItem(VKEY + lang, id); } catch { /* storage blocked */ }
}

export const useLang = create<{ lang: "en" | "hi"; set: (l: "en" | "hi") => void }>((set) => ({
  lang: read(),
  set: (lang) => {
    try { localStorage.setItem(KEY, lang); } catch { /* storage blocked */ }
    set({ lang });
    void fetch("/language", { method: "POST", headers: { "Content-Type": "application/json" },
                              body: JSON.stringify({ lang }) });
  },
}));

// The backend forgets on restart, so tell it again on load.
if (read() === "hi") {
  void fetch("/language", { method: "POST", headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ lang: "hi" }) });
}
