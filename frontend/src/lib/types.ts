// Mirror of core/events.py. Keep in lockstep with the frozen contract:
// add optional fields, never retype or remove one.

export type EventType =
  | "boot" | "source.status" | "clock" | "transcript" | "intent"
  | "agent.state" | "claim" | "claim.rejected" | "conviction"
  | "graph.node" | "graph.edge" | "graph.reset"
  | "proposal" | "risk.decision" | "execution"
  | "telemetry" | "speech" | "error";

export type OrbState = "idle" | "listening" | "thinking" | "speaking" | "alert";
export type AgentState = "idle" | "thinking" | "done" | "failed";

export interface WireEvent {
  v: number;
  type: EventType;
  seq: number;
  ts: number;
  payload: Record<string, any>;
}

export interface BootLine { line: string; level: "ok" | "warn" | "fail" }
export interface SourceStatus { source: string; online: boolean; rows: number; kind?: string }

export interface GraphNode {
  id: string; label: string; kind: "ticker" | "source" | "fact" | "claim" | "risk";
  detail?: string | null; uri?: string | null;
}
export interface GraphEdge { src: string; dst: string; kind: string }

export interface Claim {
  desk: string; claim: string; stance: "bull" | "bear" | "neutral";
  weight: number; source_ids: string[];
}
export interface RejectedClaim { desk: string; claim: string; reason: string }

export interface Conviction {
  score: number; agreement: number; net_stance: number; evidence_quality: number;
  groupthink: boolean; dissent: string | null; conceded?: number;
  claims_accepted: number; claims_rejected: number;
}

export interface Violation {
  code: string; message: string; measured: number; limit: number; headroom: number;
}
export interface Remedy {
  max_shares: number; binding_constraint: string; explanation: string;
  resulting: Record<string, number>;
}
export interface RiskDecision {
  approved: boolean; policy_version: string; violations: Violation[];
  remedy: Remedy | null; metrics?: Record<string, any>;
  counterfactual?: {
    from: string; to: string; overrides: Record<string, number>;
    was_approved: boolean; now_approved: boolean;
  } | null;
}

export interface Proposal {
  ticker: string; side: string; shares: number; price: number; rationale?: string;
}
export interface Execution {
  ticker: string; side: string; shares: number; price: number;
  nav_after: number; paper: boolean;
}

export interface Telemetry {
  tick: number; orb: OrbState; model: string;
  claims_accepted: number; claims_rejected: number; violations_blocked: number;
  nav: number; sim_clock: string;
  visible: { signals: number; prices: number; documents: number };
}

export interface Position {
  ticker: string; shares: number; price: number; value: number;
  weight: number; sector: string; name?: string; sector_label?: string;
}
export interface FundState {
  sim_clock: string;
  portfolio_id?: string | null;
  portfolio_name?: string; nav: number; cash: number; cash_pct: number;
  positions: Position[]; exposures: Record<string, number>;
  policy: { version: string; profile?: string; name?: string;
            describes?: string; limits: Record<string, number> };
  counters: Record<string, number>;
  model: string;
  visible: { signals: number; prices: number; documents: number };
  broker_execution: boolean;
}

export interface EvidenceItem {
  id: string; text: string; source_name: string; published_at: string;
  confidence: number; source_uri: string | null; kind: string;
}
