// Voice barge-in: talk over JARVIS and it stops, the way you can with Alexa.
//
// While it is speaking, the microphone is watched for sustained speech. The monitor stream
// asks the browser for echo cancellation, which removes the app's own voice from what the
// microphone hears -- that is what lets this work on speakers at all. It is still
// imperfect, so it is OFF by default and the toggle says to use headphones. Tapping the
// orb, the mic button, the Stop button, Esc or SPACE always interrupts instantly regardless.
import { create } from "zustand";

import { interrupt, onVoice } from "./speak";
import { useVoice } from "./voice";

const KEY = "jarvis.bargein";
const read = () => { try { return localStorage.getItem(KEY) === "1"; } catch { return false; } };

export const useBargeIn = create<{ on: boolean; set: (v: boolean) => void }>((set) => ({
  on: read(),
  set: (on) => { try { localStorage.setItem(KEY, on ? "1" : "0"); } catch { /* */ } set({ on }); },
}));

let stream: MediaStream | null = null;
let ctx: AudioContext | null = null;
let timer = 0;

function stopMonitor(): void {
  window.clearInterval(timer);
  stream?.getTracks().forEach((t) => t.stop());
  stream = null;
  ctx?.close().catch(() => undefined);
  ctx = null;
}

async function startMonitor(): Promise<void> {
  if (stream || !navigator.mediaDevices?.getUserMedia) return;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
    });
  } catch { stream = null; return; }
  ctx = new AudioContext();
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 256;
  ctx.createMediaStreamSource(stream).connect(analyser);
  const bins = new Uint8Array(analyser.frequencyBinCount);
  const t0 = performance.now();
  let floor = 0, n = 0, loudMs = 0, last = t0;
  timer = window.setInterval(() => {
    analyser.getByteFrequencyData(bins);
    let sum = 0;
    for (let i = 0; i < bins.length; i++) sum += bins[i];
    const level = Math.min(1, sum / bins.length / 90);
    const now = performance.now(), dt = now - last; last = now;
    if (now - t0 < 800) { floor += level; n += 1; return; }   // learn what "its own voice" sounds like
    const threshold = Math.max(0.16, (n ? floor / n : 0.05) * 3.2 + 0.06);
    loudMs = level > threshold ? loudMs + dt : 0;
    if (loudMs > 380 && useVoice.getState().status === "idle") {
      stopMonitor();
      interrupt();
      void useVoice.getState().start();     // and listen to what was said
    }
  }, 40);
}

let installed = false;
export function installBargeIn(): void {
  if (installed) return;
  installed = true;
  onVoice((state) => {
    if (state === "speaking" && useBargeIn.getState().on) void startMonitor();
    else stopMonitor();
  });
  useBargeIn.subscribe((s) => { if (!s.on) stopMonitor(); });
}
