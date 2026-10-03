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

/** This browser tab's identity. Replies to what this tab asked carry it back, so another tab or
 *  device (possibly in the other language) never shows or speaks them. */
export const CLIENT_ID = Math.random().toString(36).slice(2, 10);

// Every question also carries this screen's language, so the answer follows what is selected HERE.
// Announce the choice on load too (English as well as Hindi): the server remembers the last one
// any screen set, and an English screen must not inherit another screen's Hindi.
void fetch("/language", { method: "POST", headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({ lang: read() }) });
