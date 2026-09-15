// Provenance graph layout.
//
// Force-directed was the obvious reach, but this graph is a DAG with strict levels
// (ticker -> desk -> claim -> evidence), and a force sim on levelled data mostly
// produces an expensive hairball that settles differently every run. A deterministic
// radial layout is legible, stable across runs -- which matters when you are narrating
// it on stage -- and costs nothing per frame.
//
// Level 0  ticker      centre
// Level 1  desks       inner ring, evenly spaced
// Level 2  claims      mid ring, clustered under the desk that made them
// Level 3  evidence    outer shell, near the claims citing it

import type { GraphEdge, GraphNode } from "../lib/types";

export type Placed = { id: string; pos: [number, number, number]; kind: string; tint: number };

const R_DESK = 2.1;
const R_CLAIM = 3.9;
const R_FACT = 5.9;

export const TINT = { neutral: 0, bull: 1, bear: 2, fact: 3, risk: 4 } as const;

function tintFor(node: GraphNode): number {
  if (node.kind === "fact") return TINT.fact;
  if (node.kind === "risk") return TINT.risk;
  const detail = (node.detail || "").toLowerCase();
  if (detail.startsWith("bull")) return TINT.bull;
  if (detail.startsWith("bear")) return TINT.bear;
  return TINT.neutral;
}

export function layoutGraph(nodes: GraphNode[], edges: GraphEdge[]): Map<string, Placed> {
  const placed = new Map<string, Placed>();
  if (!nodes.length) return placed;

  const byId = new Map(nodes.map((n) => [n.id, n]));
  const ticker = nodes.find((n) => n.kind === "ticker");
  const desks = nodes.filter((n) => n.id.startsWith("desk:"));
  const claims = nodes.filter((n) => n.id.startsWith("claim:"));
  const facts = nodes.filter((n) => n.kind === "fact" && !n.id.startsWith("claim:"));

  if (ticker) {
    placed.set(ticker.id, { id: ticker.id, pos: [0, 0, 0], kind: "ticker", tint: TINT.neutral });
  }

  // Desks on a ring, tilted slightly out of plane so the graph has depth from any angle.
  const deskAngle = new Map<string, number>();
  desks.forEach((desk, i) => {
    const a = (i / Math.max(desks.length, 1)) * Math.PI * 2;
    deskAngle.set(desk.id, a);
    const tilt = (i % 2 === 0 ? 1 : -1) * 0.42;
    placed.set(desk.id, {
      id: desk.id,
      pos: [Math.cos(a) * R_DESK, tilt, Math.sin(a) * R_DESK],
      kind: "desk",
      tint: TINT.neutral,
    });
  });

  // Claims fan out under their parent desk, within a wedge so ownership stays readable.
  const claimsByDesk = new Map<string, GraphNode[]>();
  for (const claim of claims) {
    const deskId = `desk:${claim.id.split(":")[1]}`;
    if (!claimsByDesk.has(deskId)) claimsByDesk.set(deskId, []);
    claimsByDesk.get(deskId)!.push(claim);
  }
  const claimAngle = new Map<string, number>();
  for (const [deskId, group] of claimsByDesk) {
    const base = deskAngle.get(deskId) ?? 0;
    const wedge = 0.85;
    group.forEach((claim, i) => {
      const offset = group.length === 1 ? 0 : (i / (group.length - 1) - 0.5) * wedge;
      const a = base + offset;
      claimAngle.set(claim.id, a);
      placed.set(claim.id, {
        id: claim.id,
        pos: [Math.cos(a) * R_CLAIM, (i % 2 === 0 ? 0.6 : -0.6) + Math.sin(a) * 0.3,
              Math.sin(a) * R_CLAIM],
        kind: "claim",
        tint: tintFor(claim),
      });
    });
  }

  // Evidence sits outside the claims that cite it. A fact cited by several claims lands
  // at their angular mean, which is what makes shared evidence visibly shared.
  const citedBy = new Map<string, number[]>();
  for (const edge of edges) {
    if (edge.kind !== "cites") continue;
    const a = claimAngle.get(edge.src);
    if (a === undefined) continue;
    if (!citedBy.has(edge.dst)) citedBy.set(edge.dst, []);
    citedBy.get(edge.dst)!.push(a);
  }

  facts.forEach((fact, i) => {
    const angles = citedBy.get(fact.id);
    let a: number;
    if (angles && angles.length) {
      // Circular mean, so angles either side of 0 don't average to the wrong place.
      const x = angles.reduce((s, v) => s + Math.cos(v), 0);
      const y = angles.reduce((s, v) => s + Math.sin(v), 0);
      a = Math.atan2(y, x);
    } else {
      a = (i / Math.max(facts.length, 1)) * Math.PI * 2;
    }
    // Uncited evidence is pushed further out and sits dimmer -- visible, but clearly
    // not load-bearing for any claim on screen.
    const radius = angles && angles.length ? R_FACT : R_FACT + 1.5;
    const lift = ((i * 37) % 11) / 11 - 0.5;
    placed.set(fact.id, {
      id: fact.id,
      pos: [Math.cos(a) * radius, lift * 2.4, Math.sin(a) * radius],
      kind: "fact",
      tint: TINT.fact,
    });
  });

  // Anything unclassified still needs a seat.
  for (const node of nodes) {
    if (placed.has(node.id)) continue;
    const a = Math.random() * Math.PI * 2;
    placed.set(node.id, {
      id: node.id,
      pos: [Math.cos(a) * R_FACT, (Math.random() - 0.5) * 2, Math.sin(a) * R_FACT],
      kind: node.kind,
      tint: tintFor(node),
    });
  }
  return placed;
}

export function edgeSegments(
  edges: GraphEdge[],
  placed: Map<string, Placed>,
  perEdge = 12,
): { positions: Float32Array; progress: Float32Array; seeds: Float32Array; tints: Float32Array } {
  // Each edge becomes a short polyline so the travelling pulse has vertices to light up.
  const usable = edges.filter((e) => placed.has(e.src) && placed.has(e.dst));
  const segs = usable.length * (perEdge - 1) * 2;
  const positions = new Float32Array(segs * 3);
  const progress = new Float32Array(segs);
  const seeds = new Float32Array(segs);
  const tints = new Float32Array(segs);

  let p = 0;
  usable.forEach((edge, ei) => {
    const a = placed.get(edge.src)!.pos;
    const b = placed.get(edge.dst)!.pos;
    const seed = (ei * 0.6180339887) % 1;
    const tint = edge.kind === "bull" ? 1 : edge.kind === "bear" ? 2 : 0;
    for (let i = 0; i < perEdge - 1; i++) {
      for (const t of [i / (perEdge - 1), (i + 1) / (perEdge - 1)]) {
        // Bow the line outward so edges arc instead of crossing through the centre.
        const bow = Math.sin(t * Math.PI) * 0.35;
        positions[p * 3 + 0] = a[0] + (b[0] - a[0]) * t;
        positions[p * 3 + 1] = a[1] + (b[1] - a[1]) * t + bow;
        positions[p * 3 + 2] = a[2] + (b[2] - a[2]) * t;
        progress[p] = t;
        seeds[p] = seed;
        tints[p] = tint;
        p++;
      }
    }
  });
  return { positions, progress, seeds, tints };
}
