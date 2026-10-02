// Voice input: ONE controller, three ways to trigger it.
//
// The orb, the microphone button in the command panel, and the SPACE key all call the
// functions in this file and read the same state. They used to be three separate
// things -- a hold-to-talk button, a hold-to-talk key, and nothing at all on the orb --
// each with its own half of a fragile press-and-release protocol. The result was a
// microphone that only worked if you held the right control down for the right length
// of time and never touched anything else.
//
// The model now is the one people expect from every voice assistant:
//
//     tap  ->  LISTENING  ->  (you speak, then pause)  ->  TRANSCRIBING  ->  answer
//
// - Tapping again while listening sends what has been said so far.
// - Pausing for about a second after speaking sends it automatically.
// - Escape, or tapping with nothing heard, throws the recording away.
//
// State is deliberately explicit and visible. Every transition has words attached
// ("Listening", "Transcribing", "I heard ...") because the failure this replaces was
// silence: you could not tell whether the microphone was working until it was too late.

import { create } from "zustand";

import * as socket from "./socket";
import { allowSpeech, interrupt } from "./speak";

export type VoiceStatus =
  | "idle"          // ready, waiting to be tapped
  | "starting"      // asked the browser for the microphone (permission prompt may be up)
  | "listening"     // recording; speak now
  | "processing";   // audio is being transcribed locally

interface VoiceState {
  status: VoiceStatus;
  heard: string;            // what the transcriber made of the last utterance
  heardAt: number;          // when, so the UI can fade it
  error: string | null;     // why the last attempt failed, in words
  speaking: boolean;        // has speech actually been detected in this recording

  toggle: () => void;
  start: () => Promise<void>;
  finish: () => Promise<void>;
  cancel: () => void;
  clearError: () => void;
}

// One in-flight operation at a time. Without this a double-tap during the permission
// prompt started two recorders, and the second one never got stopped.
let busy = false;
let speakingPoll = 0;

export const useVoice = create<VoiceState>((set, get) => ({
  status: "idle",
  heard: "",
  heardAt: 0,
  error: null,
  speaking: false,

  toggle: () => {
    const { status } = get();
    if (status === "idle") void get().start();
    else if (status === "listening") void get().finish();
    // "starting" and "processing": a tap here is almost certainly impatience, and
    // acting on it would only race the operation already running.
  },

  start: async () => {
    if (busy || get().status !== "idle") return;
    busy = true;
    // Stop JARVIS mid-sentence. People do not talk over a voice, and the microphone
    // would otherwise record the answer it is trying to listen for.
    interrupt();
    // Asking out loud is as much a request to be answered as typing is. If a soft Stop
    // from earlier is still latched, lift it -- a hard "voice off" still wins.
    allowSpeech();
    set({ status: "starting", error: null, speaking: false });

    const ok = await socket.startMic((why) => {
      // Fired from the capture loop when the utterance is over (or never began).
      if (why === "nospeech") {
        get().cancel();
        set({ error: "I did not hear anything. Tap the microphone and speak after it says Listening." });
      } else {
        void get().finish();
      }
    });
    busy = false;

    if (!ok) {
      set({ status: "idle", error: socket.micError ?? "The microphone could not be started." });
      return;
    }
    set({ status: "listening" });
    // The UI wants to know the moment speech is picked up, to confirm "yes, I can hear
    // you" while the person is still talking.
    window.clearInterval(speakingPoll);
    speakingPoll = window.setInterval(() => {
      if (get().status !== "listening") { window.clearInterval(speakingPoll); return; }
      const now = socket.heardSpeechNow;
      if (now !== get().speaking) set({ speaking: now });
    }, 120);
  },

  finish: async () => {
    if (get().status !== "listening") return;
    window.clearInterval(speakingPoll);
    set({ status: "processing", speaking: false });
    const result = await socket.stopMic();
    if (result?.transcript) {
      set({ heard: result.transcript, heardAt: Date.now() });
    }
    if (!result || !result.ok) {
      set({ error: socket.micError ?? "I could not make that out. Tap the microphone and try again." });
    } else {
      set({ error: null });
    }
    set({ status: "idle" });
  },

  cancel: () => {
    window.clearInterval(speakingPoll);
    socket.cancelMic();
    busy = false;
    set({ status: "idle", speaking: false });
  },

  clearError: () => set({ error: null }),
}));

/** Keyboard: SPACE taps the microphone (or holds it, push-to-talk style).
 *
 *  Pressing SPACE starts listening. If it is released quickly it behaves like a tap and
 *  keeps listening until you pause; if it is held for a while, releasing sends -- both
 *  habits work, because both are things people actually do.
 */
export function installVoiceKeys(isTyping: () => boolean): () => void {
  let downAt = 0;
  let startedByKey = false;

  const down = (e: KeyboardEvent) => {
    if (e.code !== "Space" || isTyping()) return;
    e.preventDefault();
    if (e.repeat) return;
    const v = useVoice.getState();
    if (v.status === "listening") { void v.finish(); return; }   // second press = send
    if (v.status === "idle") {
      downAt = performance.now();
      startedByKey = true;
      void v.start();
    }
  };
  const up = (e: KeyboardEvent) => {
    if (e.code !== "Space" || isTyping()) return;
    e.preventDefault();
    if (!startedByKey) return;
    startedByKey = false;
    // A long hold is push-to-talk: letting go means "I am done". A short press is a tap
    // that started a recording, which should keep going until you pause.
    if (performance.now() - downAt > 700 && useVoice.getState().status === "listening") {
      void useVoice.getState().finish();
    }
  };
  const esc = (e: KeyboardEvent) => {
    if (e.key !== "Escape") return;
    const v = useVoice.getState();
    if (v.status === "listening" || v.status === "starting") {
      e.preventDefault();
      // Escape also means "silence the voice" and "close the dialog" elsewhere. While
      // the microphone is open it means only this, so nothing else may react to it.
      e.stopImmediatePropagation();
      v.cancel();
    }
  };
  // Alt-tabbing away mid-recording must not leave the microphone open.
  const blur = () => {
    const v = useVoice.getState();
    if (v.status === "listening") void v.finish();
  };

  window.addEventListener("keydown", down);
  window.addEventListener("keyup", up);
  window.addEventListener("keydown", esc, true);
  window.addEventListener("blur", blur);
  return () => {
    window.removeEventListener("keydown", down);
    window.removeEventListener("keyup", up);
    window.removeEventListener("keydown", esc, true);
    window.removeEventListener("blur", blur);
  };
}
