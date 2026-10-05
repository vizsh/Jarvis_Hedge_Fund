import { create } from "zustand";

import type { ChartData } from "../components/charts/PriceChart";
import { setVoiceReplies, voiceReplies } from "./speak";

/** What the assistant returned for a question: the same dict the backend's Answer serialises to. */
export interface AnswerData {
  headline: string;
  bullets: string[];
  action: string | null;
  detail: string | null;
  kind: string;
  follow_ups: string[];
  follow_ups_hi?: string[];
  facts?: { label: string; value: string; tone?: string }[];
  table?: { columns: string[]; rows: string[][] } | null;
  visual?: { page: string; label: string; params: Record<string, string | number> } | null;
  lang?: string;
  level?: string;
  subject?: string | null;
  data?: AnswerExtra;
}

export interface ReadItem { title: string; why: string; tag?: string; confidence?: "solid" | "light" | "weak"; basis?: string }
export interface AnswerExtra {
  intent?: string;
  tour?: string;
  tour_title?: string;
  tour_manual?: boolean;
  concept?: string;
  category?: string;
  scam?: string;
  ticker?: string;
  tickers?: string[];
  chart?: ChartData | null;
  sections?: { kind: "good" | "watch"; title: string; items: ReadItem[] }[];
  coverage?: { ran: number; of: number };
  freshness?: { label: string; date: string | null; age_days: number | null }[];
  investigate?: string;
  [k: string]: unknown;
}

export interface ChatMessage {
  id: number;
  who: "you" | "jarvis";
  text?: string;
  answer?: AnswerData;
  at: number;
}

interface ChatState {
  messages: ChatMessage[];
  pending: number;            // when the last question was sent and not yet answered (0 = nothing waiting)
  voice: boolean;
  push: (m: Omit<ChatMessage, "id" | "at">) => void;
  /** A question that was spoken: the server answers it directly, so the answer may arrive before the transcript does. */
  pushSpoken: (text: string) => void;
  clear: () => void;
  setVoice: (on: boolean) => void;
}

let nextId = 1;

export const useChat = create<ChatState>((set) => ({
  messages: [],
  voice: voiceReplies(),
  pending: 0,
  push: (m) => set((s) => ({ messages: [...s.messages.slice(-60), { ...m, id: nextId++, at: Date.now() }], pending: m.who === "you" ? Date.now() : 0 })),
  pushSpoken: (text) => set((s) => {
    const ms = s.messages;
    const last = ms[ms.length - 1];
    const prev = ms[ms.length - 2];
    if (ms.some((m) => m.who === "you" && m.text === text && Date.now() - m.at < 15000)) return s;
    const q: ChatMessage = { id: nextId++, who: "you", text, at: Date.now() };
    // answer already shown with no question above it: put the question in front of it
    if (last && last.who === "jarvis" && Date.now() - last.at < 20000 && (!prev || prev.who === "jarvis")) {
      return { messages: [...ms.slice(0, -1), q, last], pending: 0 };
    }
    return { messages: [...ms.slice(-60), q], pending: Date.now() };
  }),
  clear: () => set({ messages: [], pending: 0 }),
  setVoice: (on) => { setVoiceReplies(on); set({ voice: on }); },
}));

/** The plain text of an answer, for reading aloud or copying. */
export function answerText(a: AnswerData): string {
  return [a.headline, ...a.bullets, a.action].filter(Boolean).join(" ");
}
