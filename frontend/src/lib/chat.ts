import { create } from "zustand";

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
  voice: boolean;
  push: (m: Omit<ChatMessage, "id" | "at">) => void;
  clear: () => void;
  setVoice: (on: boolean) => void;
}

let nextId = 1;

export const useChat = create<ChatState>((set) => ({
  messages: [],
  voice: voiceReplies(),
  push: (m) => set((s) => ({ messages: [...s.messages.slice(-60), { ...m, id: nextId++, at: Date.now() }] })),
  clear: () => set({ messages: [] }),
  setVoice: (on) => { setVoiceReplies(on); set({ voice: on }); },
}));

/** The plain text of an answer, for reading aloud or copying. */
export function answerText(a: AnswerData): string {
  return [a.headline, ...a.bullets, a.action].filter(Boolean).join(" ");
}
