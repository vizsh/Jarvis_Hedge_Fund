// Shared-device ("kiosk") mode: one phone or tablet used by many people, for example a village
// helper, a self-help-group leader or a panchayat desk. Nothing a person types is saved to disk,
// "Next person" wipes everything (figures, chat, the guide's open question, the server's memory of
// them), and an idle timer does the same if someone walks away.
import { create } from "zustand";

import { useChat, } from "./chat";
import { CLIENT_ID } from "./lang";
import { usePilot } from "./pilot";
import { go } from "./router";
import { pstore, setKioskStorage, wipePersonData } from "./pstore";
import { stop as stopSpeech } from "./speak";
import { cancelMic } from "./socket";

const KEY = "jarvis.kiosk";          // a device setting, not a person's data
const IDLE_KEY = "jarvis.kiosk.idle";

interface KioskState {
  on: boolean;
  epoch: number;                    // bumped on every wipe so pages and the dock start fresh
  idleSec: number;
  people: number;                   // people served in this session (a count only)
  enable: () => void;
  disable: () => void;
  nextPerson: () => Promise<void>;
  setIdle: (s: number) => void;
}

const startOn = (() => { try { return localStorage.getItem(KEY) === "1"; } catch { return false; } })();
const startIdle = (() => { try { return Number(localStorage.getItem(IDLE_KEY)) || 180; } catch { return 180; } })();
setKioskStorage(startOn);

export const useKiosk = create<KioskState>((set, get) => ({
  on: startOn,
  epoch: 0,
  idleSec: startIdle,
  people: 0,
  enable: () => {
    try { localStorage.setItem(KEY, "1"); } catch { /* storage blocked */ }
    setKioskStorage(true);
    set({ on: true });
    void get().nextPerson();
    set({ people: 0 });
  },
  disable: () => {
    try { localStorage.removeItem(KEY); } catch { /* storage blocked */ }
    wipePersonData();
    setKioskStorage(false);
    set({ on: false, epoch: get().epoch + 1 });
  },
  nextPerson: async () => {
    stopSpeech();
    cancelMic();
    wipePersonData();
    useChat.getState().clear();
    usePilot.getState().set(null);
    try {
      await fetch("/kiosk/reset", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ cid: CLIENT_ID }) });
    } catch { /* the server forgets on its own timeout too */ }
    set({ epoch: get().epoch + 1, people: get().people + 1 });
    go("/rural");
  },
  setIdle: (s) => { try { localStorage.setItem(IDLE_KEY, String(s)); } catch { /* storage blocked */ } set({ idleSec: s }); },
}));

export const isKiosk = (): boolean => useKiosk.getState().on;
export { pstore };
