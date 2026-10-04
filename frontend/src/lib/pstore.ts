// Where a person's own entries (figures typed into a tool, a checklist) are remembered.
// Normally the browser's local storage, so a person finds their numbers next time. In kiosk mode,
// where many people share one device, nothing is written to disk at all: it lives in memory and
// is gone when "Next person" is pressed or the page is closed.
const mem = new Map<string, string>();
let kiosk = false;

export function setKioskStorage(on: boolean): void { kiosk = on; if (on) wipeDisk(); }

export const pstore = {
  get<T>(ns: string, k: string, d: T): T {
    try {
      const v = kiosk ? mem.get(ns + k) : localStorage.getItem("jarvis." + ns + k);
      return v ? (JSON.parse(v) as T) : d;
    } catch { return d; }
  },
  set(ns: string, k: string, v: unknown): void {
    try {
      if (kiosk) mem.set(ns + k, JSON.stringify(v));
      else localStorage.setItem("jarvis." + ns + k, JSON.stringify(v));
    } catch { /* storage blocked */ }
  },
};

/** Remove every person-entered value, in memory and on disk. Device settings (voice, language) stay. */
function wipeDisk(): void {
  try {
    for (const k of Object.keys(localStorage)) if (/^jarvis\.(rural|recovery)\./.test(k)) localStorage.removeItem(k);
  } catch { /* storage blocked */ }
}
export function wipePersonData(): void { mem.clear(); wipeDisk(); }
