// WebSocket client with auto-reconnect and an audio envelope for the orb.

import { useChat, type AnswerData } from "./chat";
import { useStore } from "./store";
import { CLIENT_ID, useLang } from "./lang";
import type { EvidenceItem, FundState, WireEvent } from "./types";
import {
  allowSpeech, forceStop, isSilenced, resumeVoice as resumeSpeech, speak,
} from "./speak";

const WS_URL = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`;

let socket: WebSocket | null = null;
let retry = 0;
let refreshTimer: number | null = null;
// One pending reconnect at a time. Every `onclose` used to schedule its own, so a
// flapping server (or a restart, which is exactly when this happens) could leave
// several timers racing -- each one creating a socket, and each extra socket
// delivering every SPEECH event another time.
let reconnectTimer: number | null = null;

// Voice controls re-exported so components import one module rather than reaching
// into the speech engine directly.
export function forceStopVoice(): void { forceStop(); }
export function resumeVoice(): void { resumeSpeech(); }
export function voiceSilenced(): boolean { return isSilenced(); }

export function connect(): void {
  // One socket, ever. A second connection delivers every event twice -- including
  // SPEECH -- so the voice stuttered and restarted over itself.
  if (socket && (socket.readyState === WebSocket.OPEN
                 || socket.readyState === WebSocket.CONNECTING)) {
    return;
  }
  if (reconnectTimer) { window.clearTimeout(reconnectTimer); reconnectTimer = null; }

  // Bind every handler to THIS instance. They used to close over the module-level
  // `socket`, so a stale socket's error handler would close whichever socket happened
  // to be current -- killing a healthy connection and triggering yet another reconnect.
  const ws = new WebSocket(WS_URL);
  socket = ws;

  const isCurrent = () => socket === ws;

  ws.onopen = () => {
    if (!isCurrent()) { ws.close(); return; }   // superseded while connecting
    retry = 0;
    useStore.getState().setConnected(true);
    refreshState();
  };

  ws.onmessage = (msg) => {
    if (!isCurrent()) return;                   // a zombie must not reach the store
    const event: WireEvent = JSON.parse(msg.data);
    // Only this screen's own replies, in this screen's language: a reply another tab or device
    // asked for, or an announcement in the other language, is neither shown nor spoken here.
    if (event.type === "speech" && !event.payload?._replay) {
      const sp = event.payload as { cid?: string; lang?: string };
      if (sp.cid && sp.cid !== CLIENT_ID) return;
      if (!sp.cid && sp.lang && sp.lang !== useLang.getState().lang) return;
    }
    useStore.getState().ingest(event);

    // Anything that moves the fund or the clock invalidates the panels. Debounced so a
    // burst of graph events during an investigation does not hammer the API.
    if (["execution", "clock", "risk.decision"].includes(event.type) ||
        (event.type === "telemetry" && event.payload?.replay === false)) {
      if (refreshTimer) window.clearTimeout(refreshTimer);
      refreshTimer = window.setTimeout(refreshState, 220);
    }
    if (event.type === "graph.reset" || event.type === "intent") {
      const ticker = event.payload?.ticker;
      if (ticker) void loadEvidence(ticker);
    }
    // TTS is text-only here, so drive the orb's speaking envelope from the line length
    // rather than faking a waveform we do not have.
    // Replayed history is rendered but never spoken. It already happened.
    if (event.type === "speech" && event.payload?.text && !event.payload?._replay) {
      const line = String(event.payload.text);
      // Every spoken line also lands in the chat thread, as a structured answer card when the
      // line came with one, so the reply can be read as well as heard (or only read).
      useChat.getState().push({ who: "jarvis", text: line, answer: event.payload?.answer as AnswerData | undefined });
      pulseSpeech(line.length);
      speak(line, (event.payload?.lang as string) || "en");
    }
  };

  ws.onclose = () => {
    if (!isCurrent()) return;                   // an old socket closing is not news
    useStore.getState().setConnected(false);
    retry += 1;
    if (reconnectTimer) window.clearTimeout(reconnectTimer);
    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null;
      connect();
    }, Math.min(600 * retry, 5000));
  };

  ws.onerror = () => ws.close();                // close THIS one, never the current one
}

/** `shown`: what the chat bubble displays when it differs from what is asked (a Hindi label for an English question). */
export function send(text: string, shown?: string): void {
  allowSpeech();          // asking is an explicit request to be answered
  useChat.getState().push({ who: "you", text: shown ?? text });
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: "command", text, lang: useLang.getState().lang, cid: CLIENT_ID }));
  }
}

export function sendBoot(): void {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: "boot" }));
  }
}

export async function refreshState(): Promise<void> {
  try {
    const res = await fetch("/state");
    const fund: FundState = await res.json();
    if (fund && fund.sim_clock) useStore.getState().setFund(fund);
  } catch { /* backend restarting; the socket reconnect will re-trigger this */ }
}

export async function loadEvidence(ticker: string): Promise<void> {
  try {
    const res = await fetch(`/evidence/${encodeURIComponent(ticker)}`);
    const data: { items: EvidenceItem[] } = await res.json();
    useStore.getState().setEvidence(data.items ?? []);
  } catch { /* non-fatal: the graph still renders, clicks just show less detail */ }
}

export async function loadPrices(ticker: string): Promise<{ time: string; value: number }[]> {
  try {
    const res = await fetch(`/prices/${encodeURIComponent(ticker)}?limit=260`);
    const data = await res.json();
    return (data.bars ?? []).map((b: any) => ({ time: b.date, value: b.close }));
  } catch {
    return [];
  }
}

// --- audio -----------------------------------------------------------------------
let ctx: AudioContext | null = null;
let analyser: AnalyserNode | null = null;
let raf = 0;
// The capture loop runs on a TIMER, not requestAnimationFrame. Frames are throttled or
// paused whenever the page is not actively painting (covered window, busy GPU, a
// background tab), and a silence detector that stops ticking never sends anything.
let vadTimer = 0;

let recorder: MediaRecorder | null = null;
let chunks: Blob[] = [];
let micStream: MediaStream | null = null;
let startedAt = 0;
let peakLevel = 0;      // loudest frame seen, so we can tell "silent" from "unheard"
// The live spectrum, for the waveform. Drawing the REAL frame matters: a decorative
// animation would happily bounce along while the microphone was picking up nothing,
// which is exactly the failure it exists to make visible.
export let spectrum: Uint8Array = new Uint8Array(0);

export let micError: string | null = null;
/** Live read-outs for the interface: how loud now, and whether speech has been heard. */
export let lastLevel = 0;
export let heardSpeechNow = false;

// --- voice-activity detection ---------------------------------------------------
// Click-to-talk only works if the recorder can tell when you have finished. Hold-to-talk
// let the key release do that job; a click does not, so the capture loop has to.
//
//   silence   you spoke, then went quiet            -> send what was said
//   nospeech  nothing but room noise for too long   -> give up, say so, nothing sent
//   max       a hard ceiling so a stuck mic cannot record forever
const SILENCE_MS = 1300;      // quiet this long AFTER speech = end of utterance
const NO_SPEECH_MS = 7000;    // never heard speech in this long = abandon
const MAX_MS = 20000;
export type AutoStop = "silence" | "nospeech" | "max";

/** Mic envelope -> orb, plus recording for local transcription. */
export async function startMic(onAuto?: (why: AutoStop) => void): Promise<boolean> {
  micError = null;
  if (!navigator.mediaDevices?.getUserMedia) {
    // getUserMedia is gated to secure origins. localhost counts; a LAN IP does not,
    // and the failure is otherwise silent -- the button just never records.
    micError = window.isSecureContext
      ? "This browser has no microphone API."
      : "Microphone needs https or localhost. Open http://localhost:8000.";
    return false;
  }
  try {
    // getUserMedia does not always settle. A permission prompt left open, or a policy
    // that blocks capture without rejecting, leaves the promise pending forever --
    // which latched the "starting" guard and disabled the microphone permanently.
    const stream = await Promise.race([
      navigator.mediaDevices.getUserMedia({
        // Noise suppression and echo cancellation are tuned for telephony: they carve
      // up speech in ways a recogniser hates. Whisper does better on rawer audio.
      // Auto-gain stays ON because a quiet mic is the commonest cause of a bad
      // transcript.
      audio: {
        channelCount: 1,
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: true,
      },
      }),
      new Promise<MediaStream>((_, reject) =>
        setTimeout(() => {
          const e = new Error("timeout");
          e.name = "TimeoutError";
          reject(e);
        }, 8000)),
    ]);
    micStream = stream;

    // Record the utterance for faster-whisper. We deliberately do NOT use the browser
    // Web Speech API: it is free and easy but ships audio to Google, which would
    // quietly break the on-prem claim the whole project rests on.
    chunks = [];
    peakLevel = 0;
    const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus" : "audio/webm";
    // 32kbps opus was starving the recogniser. Speech needs the headroom.
    recorder = new MediaRecorder(stream, { mimeType: mime, audioBitsPerSecond: 96000 });
    recorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
    // Emit a chunk every 250ms rather than only on stop: a very short press otherwise
    // produced a truncated container that decoded to silence.
    recorder.start(250);
    startedAt = performance.now();

    ctx = ctx ?? new AudioContext();
    analyser = ctx.createAnalyser();
    analyser.fftSize = 256;
    ctx.createMediaStreamSource(stream).connect(analyser);

    const bins = new Uint8Array(analyser.frequencyBinCount);
    // Per-recording VAD state. The speech threshold is relative to the room's own noise
    // floor, measured in the first third of a second, because a fixed number is too
    // sensitive in a noisy hall and deaf on a quiet laptop microphone.
    let noiseSum = 0, noiseN = 0, speechMs = 0, heardSpeech = false;
    let lastLoud = 0, lastFrame = performance.now(), fired = false;
    lastLevel = 0;
    heardSpeechNow = false;

    const loop = () => {
      if (!analyser) return;
      analyser.getByteFrequencyData(bins);
      let sum = 0;
      for (let i = 0; i < bins.length; i++) sum += bins[i];
      const level = Math.min(1, sum / bins.length / 90);
      peakLevel = Math.max(peakLevel, level);
      lastLevel = level;
      spectrum = bins.slice(0, 48);
      useStore.getState().setAudio(level);

      const now = performance.now();
      const dt = now - lastFrame;
      lastFrame = now;
      const t = now - startedAt;

      if (t < 350) {
        noiseSum += level; noiseN += 1;
      } else {
        const floor = noiseN ? noiseSum / noiseN : 0.02;
        const threshold = Math.max(0.09, floor * 2.2 + 0.04);
        if (level > threshold) {
          speechMs += dt;
          lastLoud = now;
          if (speechMs > 140) { heardSpeech = true; heardSpeechNow = true; }
        }
        if (!fired && onAuto) {
          if (heardSpeech && t > 900 && now - lastLoud > SILENCE_MS) {
            fired = true; onAuto("silence");
          } else if (!heardSpeech && t > NO_SPEECH_MS) {
            fired = true; onAuto("nospeech");
          } else if (t > MAX_MS) {
            fired = true; onAuto("max");
          }
        }
      }
    };
    vadTimer = window.setInterval(loop, 40);
    loop();
    return true;
  } catch (err: any) {
    // Name the reason. "Nothing happened" is the least actionable failure there is.
    micError = err?.name === "NotAllowedError"
      ? "Microphone permission was denied. Allow it in the address bar and retry."
      : err?.name === "NotFoundError"
        ? "No microphone found."
        : err?.name === "TimeoutError"
          ? "The microphone never responded — check the permission prompt, then retry."
          : `Microphone unavailable (${err?.name ?? "unknown"}).`;
    releaseStream();
    return false;
  }
}

/** Stop recording, post the utterance for local transcription, return what was heard. */
/** `raw`: return the transcript only, without dispatching it as a command or translating it. */
export interface HeardResult {
  transcript?: string; ok: boolean; confirm?: boolean; understood?: string | null;
  label?: string | null; figures?: string[]; confidence?: number;
}

/** `understand`: transcribe and explain what was understood, but answer nothing until confirmed. */
export async function stopMic(raw = false, understand = false): Promise<HeardResult | null> {
  cancelAnimationFrame(raf);
  window.clearInterval(vadTimer);
  analyser = null;
  spectrum = new Uint8Array(0);
  useStore.getState().setAudio(0);

  const rec = recorder;
  recorder = null;
  if (!rec || rec.state === "inactive") { releaseStream(); return null; }

  const blob: Blob = await new Promise((resolve) => {
    rec.onstop = () => resolve(new Blob(chunks, { type: rec.mimeType }));
    rec.stop();
  });
  releaseStream();

  const heldMs = performance.now() - startedAt;
  // Separate the three ways this goes wrong, because they need different advice.
  if (heldMs < 500) {
    micError = "That was too short to catch anything. Tap the mic, speak, and pause.";
    return { ok: false };
  }
  if (peakLevel < 0.04) {
    micError = "I could not hear any speech. Check the right microphone is selected "
      + "and speak a little closer.";
    return { ok: false };
  }
  if (blob.size < 2000) {
    micError = "The recording came out empty. Tap the mic and try again.";
    return { ok: false };
  }

  try {
    const res = await fetch(`/stt?lang=${useLang.getState().lang}&cid=${CLIENT_ID}${raw ? "&raw=true" : ""}${understand ? "&understand=true" : ""}`, {
      method: "POST",
      headers: { "Content-Type": blob.type || "audio/webm" },
      body: blob,
    });
    const out = await res.json();
    if (!out.ok) {
      micError = out.reason === "low confidence"
        ? `I heard "${out.transcript}" but was not confident enough to act on it.`
        : out.reason === "stt unavailable"
          ? "Local transcription is not installed."
          : "I could not make that out. Try again.";
    }
    return out;
  } catch {
    micError = "Could not reach the transcriber.";
    return { ok: false };
  }
}

/** Abandon the recording: stop everything and send nothing. */
export function cancelMic(): void {
  cancelAnimationFrame(raf);
  window.clearInterval(vadTimer);
  analyser = null;
  spectrum = new Uint8Array(0);
  useStore.getState().setAudio(0);
  const rec = recorder;
  recorder = null;
  if (rec && rec.state !== "inactive") {
    rec.onstop = null;
    try { rec.stop(); } catch { /* already stopped */ }
  }
  chunks = [];
  releaseStream();
}

function releaseStream(): void {
  micStream?.getTracks().forEach((t) => t.stop());
  micStream = null;
}

/** Decaying envelope so the orb visibly "speaks" a line of the given length. */
function pulseSpeech(chars: number): void {
  const ms = Math.min(6000, 700 + chars * 26);
  const t0 = performance.now();
  const tick = () => {
    const elapsed = performance.now() - t0;
    if (elapsed > ms) { useStore.getState().setAudio(0); return; }
    const envelope = 0.34 + 0.3 * Math.sin(elapsed / 90) * Math.sin(elapsed / 37);
    useStore.getState().setAudio(Math.max(0, envelope));
    requestAnimationFrame(tick);
  };
  tick();
}
