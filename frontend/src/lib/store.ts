// Single store fed by the WebSocket. Every panel reads from here; nothing fetches
// independently, so the whole HUD is always describing the same instant.

import { create } from "zustand";
import type {
  AgentState, BootLine, Claim, Conviction, Execution, EvidenceItem, FundState,
  GraphEdge, GraphNode, OrbState, Proposal, RejectedClaim, RiskDecision,
  SourceStatus, Telemetry, WireEvent,
} from "./types";

export type Phase = "boot" | "core" | "graph" | "terminal" | "simulate" | "execute";

interface State {
  connected: boolean;
  phase: Phase;
  manualPhase: boolean;        // hotkeys 1-5 pin the phase for presenting

  boot: BootLine[];
  sources: SourceStatus[];

  orb: OrbState;
  audio: number;               // 0..1 envelope driving the shader
  replay: { active: boolean; name: string | null; progress: number };
  telemetry: Telemetry | null;
  fund: FundState | null;

  simClock: string;
  ticker: string;

  desks: Record<string, { state: AgentState; note?: string; ms?: number }>;
  claims: Claim[];
  rejected: RejectedClaim[];
  conviction: Conviction | null;

  nodes: GraphNode[];
  edges: GraphEdge[];
  selected: GraphNode | null;
  evidence: Record<string, EvidenceItem>;

  proposal: Proposal | null;
  decision: RiskDecision | null;
  execution: Execution | null;

  transcript: string;
  speech: string;
  log: { seq: number; kind: string; text: string; level?: string }[];
  errors: string[];

  ingest: (e: WireEvent) => void;
  setPhase: (p: Phase, manual?: boolean) => void;
  setConnected: (v: boolean) => void;
  setAudio: (v: number) => void;
  setFund: (f: FundState) => void;
  setEvidence: (items: EvidenceItem[]) => void;
  select: (n: GraphNode | null) => void;
  reset: () => void;
}

const MAX_LOG = 300;

export const useStore = create<State>((set, get) => ({
  connected: false,
  phase: "boot",
  manualPhase: false,
  boot: [],
  sources: [],
  orb: "idle",
  audio: 0,
  replay: { active: false, name: null, progress: 0 },
  telemetry: null,
  fund: null,
  simClock: "",
  ticker: "TCS.NS",
  desks: {},
  claims: [],
  rejected: [],
  conviction: null,
  nodes: [],
  edges: [],
  selected: null,
  evidence: {},
  proposal: null,
  decision: null,
  execution: null,
  transcript: "",
  speech: "",
  log: [],
  errors: [],

  setPhase: (phase, manual = false) =>
    set((s) => ({ phase, manualPhase: manual ? true : s.manualPhase })),
  setConnected: (connected) => set({ connected }),
  setAudio: (audio) => set({ audio }),
  // /state is authoritative for the clock too. Keeping simClock on a separate path
  // let the scrubber and the fund panel drift apart and show two different dates.
  setFund: (fund) =>
    set(fund?.sim_clock ? { fund, simClock: fund.sim_clock } : { fund }),
  setEvidence: (items) =>
    set({ evidence: Object.fromEntries(items.map((i) => [i.id, i])) }),
  select: (selected) => set({ selected }),
  reset: () =>
    set({
      claims: [], rejected: [], conviction: null, nodes: [], edges: [],
      selected: null, proposal: null, decision: null, execution: null, desks: {},
    }),

  ingest: (e) => {
    const p = e.payload;
    const auto = (phase: Phase) => (get().manualPhase ? {} : { phase });
    const logLine = (kind: string, text: string, level?: string) => ({
      log: [...get().log, { seq: e.seq, kind, text, level }].slice(-MAX_LOG),
    });

    switch (e.type) {
      case "boot":
        set((s) => ({
          boot: [...s.boot, { line: p.line, level: p.level }],
          ...(get().manualPhase ? {} : { phase: "boot" as Phase }),
        }));
        break;

      case "source.status":
        set((s) => ({
          sources: [...s.sources.filter((x) => x.source !== p.source),
                    { source: p.source, online: p.online, rows: p.rows, kind: p.kind }],
        }));
        break;

      case "clock":
        set({ simClock: p.sim_clock, ...logLine("clock", `clock → ${String(p.sim_clock).slice(0, 10)}`) });
        break;

      case "intent":
        set({
          ...(p.ticker ? { ticker: p.ticker } : {}),
          ...logLine("intent", `${p.verb} ${p.ticker ?? ""} (${p.via})`),
        });
        break;

      case "agent.state":
        set((s) => ({
          desks: { ...s.desks, [p.desk]: { state: p.state, note: p.note } },
          ...(p.state === "thinking" ? auto("graph") : {}),
          ...logLine("desk", `${p.desk}: ${p.state}`),
        }));
        break;

      case "claim":
        set((s) => ({ claims: [...s.claims, p as Claim] }));
        break;

      case "claim.rejected":
        set((s) => ({
          rejected: [...s.rejected, p as RejectedClaim],
          ...logLine("gate", `DROPPED (${p.reason}) ${String(p.claim).slice(0, 48)}`, "warn"),
        }));
        break;

      case "conviction":
        set({
          conviction: p as Conviction,
          ...auto("terminal"),
          ...logLine("verdict",
            `conviction ${Number(p.score).toFixed(2)}${p.groupthink ? " · GROUPTHINK" : ""}`,
            p.groupthink ? "warn" : undefined),
        });
        break;

      case "graph.reset":
        set({ nodes: [], edges: [], selected: null, claims: [], rejected: [] });
        break;

      case "graph.node":
        set((s) =>
          s.nodes.some((n) => n.id === p.id) ? {} : { nodes: [...s.nodes, p as GraphNode] });
        break;

      case "graph.edge":
        set((s) => ({ edges: [...s.edges, p as GraphEdge] }));
        break;

      case "proposal":
        set({ proposal: p as Proposal, ...logLine("proposal", `${p.side} ${p.shares} ${p.ticker}`) });
        break;

      case "risk.decision":
        set({
          decision: p as RiskDecision,
          ...(p.counterfactual ? auto("simulate") : auto("terminal")),
          ...logLine("risk", p.approved ? "APPROVED" : `REJECTED ${p.violations?.[0]?.code ?? ""}`,
                     p.approved ? undefined : "fail"),
        });
        break;

      case "execution":
        set({
          execution: p as Execution, ...auto("execute"),
          ...logLine("fill", `PAPER ${p.side} ${p.shares} ${p.ticker}`),
        });
        break;

      case "telemetry": {
        const next: any = { telemetry: p as Telemetry, orb: p.orb ?? get().orb };
        if (p.sim_clock) next.simClock = p.sim_clock;
        // The replay flag rides on telemetry so it survives a reconnect mid-take.
        if (p.replay !== undefined) {
          next.replay = { active: !!p.replay, name: p.replay_name ?? null, progress: 0 };
        }
        set(next);
        break;
      }

      case "speech":
        set({ speech: p.text, ...logLine("jarvis", p.text) });
        break;

      case "transcript":
        set({ transcript: p.text });
        break;

      case "error":
        set((s) => ({
          errors: [...s.errors, `${p.where}: ${p.message}`].slice(-8),
          ...logLine("error", `${p.where}: ${p.message}`, "fail"),
        }));
        break;
    }
  },
}));
