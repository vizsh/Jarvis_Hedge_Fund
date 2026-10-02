// Voice output, rebuilt around audio the app fully controls.
//
// The previous engine used the browser's speechSynthesis. That could not be interrupted
// reliably: Chrome keeps playing queued utterances after cancel(), long utterances can
// stall, and the voice depends on whatever the operating system ships. "Stop" therefore
// sometimes did not stop, and the voice sounded like a 2005 screen reader.
//
// Now the server (Piper, a local neural voice) turns ONE SENTENCE into a WAV and this file
// plays it through a single <audio> element. Stopping is `audio.pause()` plus dropping the
// queue and aborting any sentence still being fetched -- instant, and nothing else can
// resurrect it, because there is no second queue inside the browser to fight with.
//
// Sentences are fetched one ahead of the one playing, so speech starts after the first
// sentence is synthesised (~0.3s) rather than after the whole answer.
//
// If /tts is unavailable (Piper not installed) it falls back to speechSynthesis so the app
// is never mute -- but the interruptible path is the primary one.

export type VoiceState = "idle" | "speaking" | "stopped" | "muted";

interface Listener {
  (state: VoiceState, meta: { sentence: number; total: number; text: string;
                              mutedUntil: number | null }): void;
}

let queue: string[] = [];
let index = 0;
let state: VoiceState = "idle";
let mutedUntil: number | null = null;
let rate = 1.0;
let listeners: Listener[] = [];
let current = "";

// Every interrupt bumps this; async work captured under an older value goes quiet.
let generation = 0;
let aborter: AbortController | null = null;
let useFallback = false;

// `stopped`: soft latch, lifted by asking something new. `silenced`: hard latch, only the
// user lifts it (the STOP VOICE / VOICE OFF button).
let stopped = false;
let silenced = false;

const audio = typeof Audio !== "undefined" ? new Audio() : (null as unknown as HTMLAudioElement);
if (audio) audio.preload = "auto";

// Same line twice in quick succession is a duplicate delivery, not a second request.
let lastSpoken = "";
let lastSpokenAt = 0;
const DEDUP_MS = 5000;
const CLAIM_KEY = "jarvis.speechClaim";
const TAB_ID = Math.random().toString(36).slice(2, 10);
const OTHER_TAB_ALIVE_MS = 30_000;

try {
  const m = Number(localStorage.getItem("jarvis.mutedUntil") || 0);
  if (m > Date.now()) mutedUntil = m;
  const r = Number(localStorage.getItem("jarvis.rate") || 0);
  if (r) rate = r;
} catch { /* storage blocked */ }

export function initVoices(): void { /* nothing to load: the server owns the voice */ }

export function onVoice(fn: Listener): () => void {
  listeners.push(fn);
  fn(state, { sentence: index, total: queue.length, text: current, mutedUntil });
  return () => { listeners = listeners.filter((l) => l !== fn); };
}

function emit(): void {
  const meta = { sentence: index, total: queue.length, text: current, mutedUntil };
  listeners.forEach((l) => l(state, meta));
}
function setState(next: VoiceState): void { state = next; emit(); }

/** Split into speakable units. Decimals and abbreviations must not create a break. */
function sentences(text: string): string[] {
  const guarded = text
    .replace(/(\d)\.(\d)/g, "$1<DOT>$2")
    .replace(/\b(Mr|Mrs|Dr|vs|approx|e\.g|i\.e)\./gi, "$1<DOT>");
  return guarded.split(/(?<=[.!?])\s+/)
    .map((s) => s.replace(/<DOT>/g, ".").trim()).filter(Boolean);
}

/** Numbers and symbols read badly aloud. */
function forSpeech(text: string): string {
  return text
    .replace(/\.NS\b/g, "")
    .replace(/\bNAV\b/g, "net asset value")
    .replace(/₹\s?([\d.,]+)\s*lakh/gi, "$1 lakh rupees")
    .replace(/₹\s?([\d.,]+)\s*crore/gi, "$1 crore rupees")
    .replace(/₹\s?([\d,]+)/g, "$1 rupees")
    .replace(/%/g, " percent")
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function isMuted(): boolean {
  if (mutedUntil && Date.now() < mutedUntil) return true;
  if (mutedUntil) { mutedUntil = null; try { localStorage.removeItem("jarvis.mutedUntil"); } catch { /* */ } }
  return false;
}

function otherTabActive(): boolean {
  try {
    const raw = localStorage.getItem(CLAIM_KEY);
    if (!raw) return false;
    const prev = JSON.parse(raw) as { at: number; tab?: string };
    return !!prev.tab && prev.tab !== TAB_ID && Date.now() - prev.at < OTHER_TAB_ALIVE_MS;
  } catch { return false; }
}

/** First visible tab to claim a line reads it; a second tab stays quiet. */
function claimLine(text: string): boolean {
  if (document.visibilityState === "hidden" && otherTabActive()) return false;
  try {
    const raw = localStorage.getItem(CLAIM_KEY);
    if (raw) {
      const prev = JSON.parse(raw) as { text: string; at: number };
      if (prev.text === text && Date.now() - prev.at < DEDUP_MS) return false;
    }
    localStorage.setItem(CLAIM_KEY, JSON.stringify({ text, at: Date.now(), tab: TAB_ID }));
    return (JSON.parse(localStorage.getItem(CLAIM_KEY) || "{}") as { tab?: string }).tab === TAB_ID;
  } catch { return true; }
}

// --- fetching ---------------------------------------------------------------------
const wavs = new Map<string, Promise<Blob | null>>();

function fetchWav(text: string, signal: AbortSignal): Promise<Blob | null> {
  const key = text;
  const hit = wavs.get(key);
  if (hit) return hit;
  const p = fetch("/tts", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }), signal,
  }).then(async (r) => (r.status === 200 ? await r.blob() : null)).catch(() => null);
  wavs.set(key, p);
  p.then((b) => { if (!b) wavs.delete(key); });
  if (wavs.size > 60) wavs.delete(wavs.keys().next().value as string);
  return p;
}

// --- playback ---------------------------------------------------------------------
async function playNext(g: number): Promise<void> {
  if (g !== generation) return;
  if (index >= queue.length) { current = ""; setState("idle"); return; }
  if (isMuted()) { setState("muted"); return; }

  current = queue[index];
  const spoken = forSpeech(current);
  setState("speaking");
  const signal = aborter!.signal;

  // Fetch this sentence and warm the next one.
  const mine = fetchWav(spoken, signal);
  if (queue[index + 1]) void fetchWav(forSpeech(queue[index + 1]), signal);
  const blob = await mine;
  if (g !== generation) return;

  if (!blob) {                       // server voice unavailable -> never be silent
    useFallback = true;
    speakFallback(spoken, g);
    return;
  }

  const url = URL.createObjectURL(blob);
  audio.src = url;
  audio.playbackRate = rate;
  const done = () => {
    audio.onended = null; audio.onerror = null;
    URL.revokeObjectURL(url);
    if (g !== generation) return;
    index += 1;
    window.setTimeout(() => void playNext(g), Math.min(260, 90 + current.length) / rate);
  };
  audio.onended = done;
  audio.onerror = done;
  try { await audio.play(); } catch { done(); }
}

function speakFallback(text: string, g: number): void {
  const synth = window.speechSynthesis;
  if (!synth) { index += 1; void playNext(g); return; }
  const u = new SpeechSynthesisUtterance(text);
  u.rate = rate;
  u.onend = u.onerror = () => { if (g === generation) { index += 1; void playNext(g); } };
  synth.speak(u);
}

function haltAudio(): void {
  generation += 1;
  queue = []; index = 0; current = "";
  aborter?.abort();
  aborter = null;
  if (audio) {
    audio.onended = null; audio.onerror = null;
    audio.pause();
    audio.removeAttribute("src");
    audio.load();
  }
  window.speechSynthesis?.cancel();
}

export function speak(text: string): void {
  if (!text) return;
  if (silenced) { setState("stopped"); return; }
  if (isMuted()) { setState("muted"); return; }
  if (stopped) { setState("stopped"); return; }

  const now = Date.now();
  if (text === lastSpoken && now - lastSpokenAt < DEDUP_MS) return;
  if (!claimLine(text)) return;
  lastSpoken = text; lastSpokenAt = now;

  haltAudio();                       // a new verdict supersedes the last one
  queue = sentences(text);
  index = 0;
  aborter = new AbortController();
  void playNext(generation);
}

/** Cut off whatever is being said RIGHT NOW without latching anything. Used when the user
 *  starts talking, or taps the orb: the voice must stop mid-word, but the answer to the
 *  next question must still play. */
export function interrupt(): void {
  haltAudio();
  lastSpoken = ""; lastSpokenAt = 0;
  if (!silenced && !stopped) setState("idle");
}

/** Interrupt AND stay quiet until a new question is asked (soft latch). */
export function stop(): void {
  stopped = true;
  haltAudio();
  setState(isMuted() ? "muted" : "stopped");
}

/** Everything off and it stays off until the user turns it back on (hard latch). */
export function forceStop(): void {
  silenced = true; stopped = true;
  haltAudio();
  lastSpoken = ""; lastSpokenAt = 0;
  setState("stopped");
}

export function resumeVoice(): void {
  silenced = false; stopped = false; mutedUntil = null;
  try { localStorage.removeItem("jarvis.mutedUntil"); } catch { /* */ }
  setState("idle");
}

export function allowSpeech(): void {
  if (silenced || !stopped) return;
  stopped = false;
  if (!isMuted()) setState("idle");
}

export function isStopped(): boolean { return stopped || silenced; }
export function isSilenced(): boolean { return silenced; }
export function isSpeaking(): boolean { return state === "speaking"; }

export function muteFor(minutes: number): void {
  mutedUntil = Date.now() + minutes * 60_000;
  try { localStorage.setItem("jarvis.mutedUntil", String(mutedUntil)); } catch { /* */ }
  haltAudio();
  setState("muted");
}

export function unmute(): void {
  mutedUntil = null; stopped = false;
  try { localStorage.removeItem("jarvis.mutedUntil"); } catch { /* */ }
  setState("idle");
}

export function setRate(value: number): void {
  rate = Math.max(0.7, Math.min(1.5, value));
  try { localStorage.setItem("jarvis.rate", String(rate)); } catch { /* */ }
  if (audio) audio.playbackRate = rate;     // takes effect on the sentence already playing
}

export function getRate(): number { return rate; }
export function getState(): VoiceState { return state; }
export function mutedUntilTs(): number | null { return mutedUntil; }
export function isEnabled(): boolean { return !isMuted(); }
export function setEnabled(on: boolean): void { on ? unmute() : muteFor(60); }
export function usingFallback(): boolean { return useFallback; }
