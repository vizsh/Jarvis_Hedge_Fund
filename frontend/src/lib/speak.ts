// Voice output: sentence-queued, interruptible, and mutable for a chosen span.
//
// The first version handed the whole paragraph to the browser in one utterance. That
// is why it felt like a machine reading aloud rather than someone explaining: no
// breath between ideas, no way to stop it halfway, and nothing on screen tracking
// where it had got to.
//
// This queues SENTENCES and pauses between them. The pause is where comprehension
// happens — it is the difference between being read at and being explained to. And
// because each sentence is a separate utterance, stopping is instant rather than
// "after it finishes the paragraph".
//
// Synthesis stays on-device: SpeechSynthesis renders from the OS voices. (Recognition
// is the opposite — the browser API uploads audio — which is why STT goes through
// faster-whisper instead.)

export type VoiceState = "idle" | "speaking" | "stopped" | "muted";

interface Listener {
  (state: VoiceState, meta: { sentence: number; total: number; text: string;
                              mutedUntil: number | null }): void;
}

let voice: SpeechSynthesisVoice | null = null;
let queue: string[] = [];
let index = 0;
let state: VoiceState = "idle";
let mutedUntil: number | null = null;
let rate = 1.0;
let listeners: Listener[] = [];
let current = "";

// Every start/stop bumps this. Handlers capture the value they were created under and
// no-op if it has moved on.
//
// Without it, Stop did not stop: `cancel()` still fires `onend` for the utterance it
// killed, and that stale handler advanced the index and scheduled the next sentence.
// If a new answer had begun by then, the dead handler resumed speaking into the LIVE
// queue -- so the voice carried on after the user had explicitly stopped it.
let generation = 0;

// Stop is a LATCH, not a one-shot.
//
// Silencing the current sentence was never enough: the next answer, or an incoming
// event, started it talking again immediately -- so "stop" felt like it did nothing.
// Once stopped, nothing is spoken until the user asks for something new (which clears
// it) or presses Resume. That is what having control means.
let stopped = false;

// The hard latch. `stopped` above is deliberately soft -- asking a new question lifts it,
// because staying silent for something the user just asked for would be perverse.
//
// The cost of that convenience is that Stop did not hold: `allowSpeech()` runs on every
// question AND on every guided-flow step, so the moment anything happened at all the
// voice came back. Pressing Stop and being talked at three seconds later is
// indistinguishable from Stop being broken.
//
// So: silenced is only ever set and cleared by an explicit user action on the control.
// No automatic path touches it. Nothing this program does on its own can start it
// talking again.
let silenced = false;

// The last line we were asked to say, and when.
//
// Duplicate delivery is the thing that made the voice "repeat everything twice and then
// go ahead". If the same SPEECH text arrives twice in quick succession -- two live
// WebSocket connections, a second browser tab, a reconnect that replays, or any future
// double-emit on the server -- `speak()` used to cancel the half-spoken first copy and
// restart the SAME line from the top. From the outside that is a stutter, not a bug you
// would think to describe as duplication.
//
// Fixing whichever transport is duplicating today does not stop the next one, so the
// guard lives here, at the point where sound is actually produced: within this window,
// an identical line is a duplicate and is ignored. No answer in this product legitimately
// repeats itself word for word inside a few seconds.
let lastSpoken = "";
let lastSpokenAt = 0;
const DEDUP_MS = 5000;

// The same guard, across tabs.
//
// Every open tab holds its own WebSocket and therefore hears every SPEECH event itself.
// Two tabs of this app — a reload that left the old one open, a second window, the page
// open on a laptop and a projector — means two voices reading the same sentence a
// fraction apart. That is the "repeating everything twice" symptom, and no amount of
// per-tab care fixes it, because each tab is behaving perfectly on its own.
//
// localStorage is shared and synchronous across same-origin tabs, so it works as a
// claim: the first tab to write this line wins it, and any other tab that sees a fresh
// claim for the same text stays quiet. If localStorage is unavailable the guard simply
// yields and the old behaviour returns, which is no worse than before.
const CLAIM_KEY = "jarvis.speechClaim";
const TAB_ID = Math.random().toString(36).slice(2, 10);

const OTHER_TAB_ALIVE_MS = 30_000;

/** Has a DIFFERENT tab spoken recently? Proof that someone else is handling the voice. */
function otherTabActive(): boolean {
  try {
    const raw = localStorage.getItem(CLAIM_KEY);
    if (!raw) return false;
    const prev = JSON.parse(raw) as { at: number; tab?: string };
    return !!prev.tab && prev.tab !== TAB_ID
      && Date.now() - prev.at < OTHER_TAB_ALIVE_MS;
  } catch {
    return false;
  }
}

function claimLine(text: string): boolean {
  // A tab you are not looking at defers to one you are -- but only if that other tab
  // actually exists. Muting every hidden page outright would silence a single
  // minimised window, which is a legitimate way to use this thing; deferring only when
  // another tab has spoken in the last half-minute kills the stale-duplicate case
  // without taking the voice away from someone who has merely looked elsewhere.
  if (typeof document !== "undefined"
      && document.visibilityState === "hidden" && otherTabActive()) {
    return false;
  }
  try {
    const raw = localStorage.getItem(CLAIM_KEY);
    if (raw) {
      const prev = JSON.parse(raw) as { text: string; at: number; tab?: string };
      if (prev.text === text && Date.now() - prev.at < DEDUP_MS) return false;
    }
    localStorage.setItem(CLAIM_KEY,
                         JSON.stringify({ text, at: Date.now(), tab: TAB_ID }));
    // Write, then read back. Two visible tabs can both pass the check above before
    // either writes; whoever's id survives the last write owns the line and the other
    // stays quiet. Not a lock — there isn't one for localStorage — but it settles the
    // ordinary race, and the visibility rule above covers the ordinary cause.
    const after = JSON.parse(localStorage.getItem(CLAIM_KEY) || "{}");
    return after.tab === TAB_ID;
  } catch {
    return true;          // private mode, blocked storage: speak rather than go mute
  }
}

// A crisp male en-GB/en-IN reads closest to the reference.
const PREFERRED = [
  /Ravi/i, /en-IN/i, /Google UK English Male/i, /George/i, /Daniel/i,
  /Microsoft Guy/i, /Microsoft Ryan/i, /Male/i,
];

function pick(): SpeechSynthesisVoice | null {
  const voices = window.speechSynthesis?.getVoices?.() ?? [];
  if (!voices.length) return null;
  for (const pattern of PREFERRED) {
    const hit = voices.find((v) => pattern.test(v.name) || pattern.test(v.lang));
    if (hit) return hit;
  }
  return voices.find((v) => v.lang.startsWith("en")) ?? voices[0];
}

export function initVoices(): void {
  if (!("speechSynthesis" in window)) return;
  voice = pick();
  // Chrome populates the list asynchronously, so the first pick usually returns
  // nothing and has to be redone once it arrives.
  window.speechSynthesis.onvoiceschanged = () => { voice = pick(); };
  // Restore a mute that was still running when the page reloaded — otherwise a
  // deliberate "quiet for 10 minutes" is undone by an accidental refresh.
  const saved = Number(localStorage.getItem("jarvis.mutedUntil") || 0);
  if (saved > Date.now()) mutedUntil = saved;
}

export function onVoice(fn: Listener): () => void {
  listeners.push(fn);
  return () => { listeners = listeners.filter((l) => l !== fn); };
}

function emit(): void {
  const meta = { sentence: index, total: queue.length, text: current, mutedUntil };
  listeners.forEach((l) => l(state, meta));
}

function setState(next: VoiceState): void {
  state = next;
  emit();
}

/** Split into speakable units. Abbreviations and decimals must not create a break —
 *  "₹2.92 lakh" read as two sentences sounds broken. */
function sentences(text: string): string[] {
  const guarded = text
    .replace(/(\d)\.(\d)/g, "$1<DOT>$2")     // 2.92
    .replace(/\b(Mr|Mrs|Dr|vs|approx|e\.g|i\.e)\./gi, "$1<DOT>");
  return guarded
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.replace(/<DOT>/g, ".").trim())
    .filter(Boolean);
}

/** Ticker suffixes and symbols read terribly aloud. */
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
  if (mutedUntil) {                      // expired
    mutedUntil = null;
    localStorage.removeItem("jarvis.mutedUntil");
  }
  return false;
}

function speakNext(): void {
  if (index >= queue.length) { setState("idle"); return; }
  if (isMuted()) { setState("muted"); return; }

  current = queue[index];
  const u = new SpeechSynthesisUtterance(forSpeech(current));
  if (voice) u.voice = voice;
  u.rate = rate;
  u.pitch = 0.94;
  u.volume = 1.0;

  const gen = generation;
  u.onend = () => {
    if (gen !== generation) return;          // cancelled: this handler is dead
    index += 1;
    // The pause between sentences is deliberate and scaled to length: a long
    // sentence needs a longer beat before the next one lands.
    const beat = Math.min(420, 140 + current.length * 1.6) / rate;
    window.setTimeout(() => {
      if (gen === generation && state === "speaking") speakNext();
    }, beat);
  };
  u.onerror = () => {
    if (gen !== generation) return;
    index += 1;
    speakNext();
  };

  setState("speaking");
  window.speechSynthesis.speak(u);
}

export function speak(text: string): void {
  if (!("speechSynthesis" in window) || !text) return;
  if (silenced) { setState("stopped"); return; }  // hard latch: only the user lifts it
  if (isMuted()) { setState("muted"); return; }
  if (stopped) { setState("stopped"); return; }   // silenced until the user resumes

  // Same line, moments apart: a duplicate delivery, not a second request. Restarting
  // the line is what produced the stutter, so drop it and let the first copy finish.
  const now = Date.now();
  if (text === lastSpoken && now - lastSpokenAt < DEDUP_MS) return;
  // And the same line claimed by another tab moments ago is that tab's to read.
  if (!claimLine(text)) return;
  lastSpoken = text;
  lastSpokenAt = now;

  // A new verdict supersedes the last one; overlapping lines are unintelligible.
  generation += 1;                           // invalidate handlers from the old line
  window.speechSynthesis.cancel();
  queue = sentences(text);
  index = 0;
  speakNext();
}

export function stop(): void {
  stopped = true;
  // Order matters: invalidate handlers FIRST, so anything `cancel()` wakes up is
  // already stale by the time it runs.
  generation += 1;
  queue = [];
  index = 0;
  current = "";

  const synth = window.speechSynthesis;
  if (synth) {
    // Chrome can leave an utterance mid-flight if it was paused, and occasionally
    // needs a second cancel on the next tick to actually go quiet.
    if (synth.paused) synth.resume();
    synth.cancel();
    window.setTimeout(() => { if (generation) synth.cancel(); }, 40);
  }
  setState(isMuted() ? "muted" : "stopped");
}

/** Lift the stop latch.
 *
 *  Called by Resume, and automatically whenever the user asks something new -- asking
 *  a question is an unambiguous request to be answered, so it would be perverse to
 *  stay silent for it. */
export function allowSpeech(): void {
  // The hard latch outranks this. A new question is a reason to lift a soft stop; it is
  // not consent to undo a force-stop the user pressed deliberately.
  if (silenced) return;
  if (!stopped) return;
  stopped = false;
  if (!isMuted()) setState("idle");
}

export function isStopped(): boolean { return stopped || silenced; }

/** Force stop: everything off, now, and it stays off.
 *
 *  Louder than `stop()` in two ways. It sets the hard latch, so no automatic path can
 *  start the voice again; and it cancels repeatedly on a short trailing schedule,
 *  because Chrome will occasionally resurrect an utterance that was mid-flight when
 *  cancel() landed -- one cancel is a suggestion, three is an instruction.
 */
export function forceStop(): void {
  silenced = true;
  stopped = true;
  generation += 1;
  queue = [];
  index = 0;
  current = "";
  // Let the same line be spoken again once the user un-silences: the dedup window is
  // about duplicate DELIVERY, and after a deliberate stop a repeat is intentional.
  lastSpoken = "";
  lastSpokenAt = 0;

  const synth = window.speechSynthesis;
  if (synth) {
    if (synth.paused) synth.resume();
    synth.cancel();
    for (const delay of [30, 120, 350]) {
      window.setTimeout(() => { if (silenced) synth.cancel(); }, delay);
    }
  }
  setState("stopped");
}

/** Lift the force stop. Only ever called from the control the user pressed. */
export function resumeVoice(): void {
  silenced = false;
  stopped = false;
  mutedUntil = null;
  localStorage.removeItem("jarvis.mutedUntil");
  setState("idle");
}

export function isSilenced(): boolean { return silenced; }

/** Mute for a span. This is the "I have understood, be quiet" control — the reason it
 *  takes minutes rather than being a toggle is that a presenter wants silence for the
 *  next stretch, not a switch they must remember to flip back. */
export function muteFor(minutes: number): void {
  mutedUntil = Date.now() + minutes * 60_000;
  localStorage.setItem("jarvis.mutedUntil", String(mutedUntil));
  generation += 1;
  queue = [];
  index = 0;
  window.speechSynthesis?.cancel();
  setState("muted");
}

export function unmute(): void {
  mutedUntil = null;
  stopped = false;
  localStorage.removeItem("jarvis.mutedUntil");
  setState("idle");
}

export function setRate(value: number): void {
  rate = Math.max(0.6, Math.min(1.6, value));
  localStorage.setItem("jarvis.rate", String(rate));
  // Re-speak the remainder at the new pace rather than waiting for the next answer.
  if (state === "speaking") {
    const rest = queue.slice(index);
    generation += 1;
    window.speechSynthesis.cancel();
    queue = rest;
    index = 0;
    speakNext();
  }
}

export function getRate(): number {
  return Number(localStorage.getItem("jarvis.rate") || rate);
}

export function getState(): VoiceState { return state; }
export function mutedUntilTs(): number | null { return mutedUntil; }
export function isEnabled(): boolean { return !isMuted(); }
export function setEnabled(on: boolean): void { on ? unmute() : muteFor(60); }
