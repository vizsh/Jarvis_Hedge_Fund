import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";

import { useStore } from "../lib/store";
import { EDGE_FRAG, EDGE_VERT, ORB_FRAG, ORB_VERT } from "./orbShaders";
import { edgeSegments, layoutGraph, type Placed } from "./layout";

const COUNT = 26000;

// Fibonacci sphere: even coverage with no polar bunching, which a naive
// random-spherical distribution gives you and which reads as a visible seam.
function fibonacciSphere(n: number, radius: number): Float32Array {
  const out = new Float32Array(n * 3);
  const phi = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < n; i++) {
    const y = 1 - (i / (n - 1)) * 2;
    const r = Math.sqrt(Math.max(0, 1 - y * y));
    const theta = phi * i;
    // Two populations: a dense nucleus and a thinner halo. A single uniform shell
    // reads as dust; the nucleus is what gives the orb a centre to bloom around.
    const u = Math.random();
    const rr = radius * (u < 0.42
      ? 0.10 + Math.pow(Math.random(), 0.5) * 0.52   // nucleus
      : 0.70 + Math.pow(Math.random(), 1.7) * 0.42); // halo
    out[i * 3 + 0] = Math.cos(theta) * r * rr;
    out[i * 3 + 1] = y * rr;
    out[i * 3 + 2] = Math.sin(theta) * r * rr;
  }
  return out;
}

export function Orb() {
  const points = useRef<THREE.Points>(null);
  const lines = useRef<THREE.LineSegments>(null);
  const { size } = useThree();

  const nodes = useStore((s) => s.nodes);
  const edges = useStore((s) => s.edges);
  const orb = useStore((s) => s.orb);
  const phase = useStore((s) => s.phase);
  const audio = useStore((s) => s.audio);
  const decision = useStore((s) => s.decision);

  const sphere = useMemo(() => fibonacciSphere(COUNT, 1.95), []);

  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry();
    const seeds = new Float32Array(COUNT);
    const tints = new Float32Array(COUNT);
    for (let i = 0; i < COUNT; i++) seeds[i] = Math.random();
    g.setAttribute("position", new THREE.BufferAttribute(sphere.slice(), 3));
    g.setAttribute("aSphere", new THREE.BufferAttribute(sphere, 3));
    g.setAttribute("aTarget", new THREE.BufferAttribute(sphere.slice(), 3));
    g.setAttribute("aSeed", new THREE.BufferAttribute(seeds, 1));
    g.setAttribute("aTint", new THREE.BufferAttribute(tints, 1));
    g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 12);
    return g;
  }, [sphere]);

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uMorph: { value: 0 },
      uAudio: { value: 0 },
      uEnergy: { value: 0 },
      uAlert: { value: 0 },
      uSize: { value: 1.55 },
      uPixelRatio: { value: Math.min(window.devicePixelRatio, 2) },
      uColdColor: { value: new THREE.Color("#7c4dff") },
      uWarmColor: { value: new THREE.Color("#25d9ff") },
    }),
    [],
  );

  const edgeUniforms = useMemo(
    () => ({ uTime: { value: 0 }, uMorph: { value: 0 } }),
    [],
  );

  const edgeGeometry = useMemo(() => new THREE.BufferGeometry(), []);

  // --- assign particles to graph seats ------------------------------------------
  // Every node gets a cluster proportional to nothing in particular except legibility:
  // the ticker and desks get more particles so they read as anchors.
  useEffect(() => {
    const target = geometry.getAttribute("aTarget") as THREE.BufferAttribute;
    const tint = geometry.getAttribute("aTint") as THREE.BufferAttribute;

    if (!nodes.length) {
      target.array.set(sphere);
      (tint.array as Float32Array).fill(0);
      target.needsUpdate = true;
      tint.needsUpdate = true;
      return;
    }

    const placed = layoutGraph(nodes, edges);
    const seats: Placed[] = [...placed.values()];
    const weight = (p: Placed) =>
      p.kind === "ticker" ? 6 : p.kind === "desk" ? 3 : p.kind === "claim" ? 2 : 1;
    const total = seats.reduce((s, p) => s + weight(p), 0);

    const arr = target.array as Float32Array;
    const tarr = tint.array as Float32Array;
    let i = 0;
    for (const seat of seats) {
      const share = Math.max(1, Math.round((weight(seat) / total) * COUNT));
      const radius = seat.kind === "ticker" ? 0.42 : seat.kind === "desk" ? 0.28 : 0.17;
      for (let k = 0; k < share && i < COUNT; k++, i++) {
        // Cluster as a small ball around the seat, denser toward the centre.
        const u = Math.random(), v = Math.random(), w = Math.cbrt(Math.random());
        const th = u * Math.PI * 2, ph = Math.acos(2 * v - 1);
        arr[i * 3 + 0] = seat.pos[0] + Math.sin(ph) * Math.cos(th) * radius * w;
        arr[i * 3 + 1] = seat.pos[1] + Math.sin(ph) * Math.sin(th) * radius * w;
        arr[i * 3 + 2] = seat.pos[2] + Math.cos(ph) * radius * w;
        tarr[i] = seat.tint;
      }
    }
    // Leftovers drift far out as ambient dust rather than piling on the last node.
    for (; i < COUNT; i++) {
      arr[i * 3 + 0] = sphere[i * 3 + 0] * 5.5;
      arr[i * 3 + 1] = sphere[i * 3 + 1] * 5.5;
      arr[i * 3 + 2] = sphere[i * 3 + 2] * 5.5;
      tarr[i] = 0;
    }
    target.needsUpdate = true;
    tint.needsUpdate = true;

    const seg = edgeSegments(edges, placed);
    edgeGeometry.setAttribute("position", new THREE.BufferAttribute(seg.positions, 3));
    edgeGeometry.setAttribute("aProgress", new THREE.BufferAttribute(seg.progress, 1));
    edgeGeometry.setAttribute("aEdgeSeed", new THREE.BufferAttribute(seg.seeds, 1));
    edgeGeometry.setAttribute("aTint", new THREE.BufferAttribute(seg.tints, 1));
    edgeGeometry.computeBoundingSphere();
  }, [nodes, edges, geometry, edgeGeometry, sphere]);

  useEffect(() => {
    uniforms.uPixelRatio.value = Math.min(window.devicePixelRatio, 2);
  }, [size, uniforms]);

  // --- per-frame ------------------------------------------------------------------
  const smoothed = useRef({ morph: 0, energy: 0, alert: 0, audio: 0 });

  useFrame((state, dt) => {
    const t = state.clock.elapsedTime;
    const d = Math.min(dt, 0.05);

    const wantMorph = nodes.length > 0 && phase !== "boot" && phase !== "core" ? 1 : 0;
    const wantEnergy = orb === "thinking" ? 1 : orb === "speaking" ? 0.45 : 0.12;
    const breach = decision && !decision.approved ? 1 : 0;
    const wantAlert = orb === "alert" || breach ? 1 : 0;

    const s = smoothed.current;
    // Critically-damped-ish easing. The morph is deliberately slower than the rest --
    // it is the moment the audience is watching and it should feel weighty.
    s.morph += (wantMorph - s.morph) * Math.min(1, d * 1.6);
    s.energy += (wantEnergy - s.energy) * Math.min(1, d * 3.0);
    s.alert += (wantAlert - s.alert) * Math.min(1, d * 4.0);
    s.audio += (audio - s.audio) * Math.min(1, d * 12.0);

    uniforms.uTime.value = t;
    uniforms.uMorph.value = s.morph;
    uniforms.uEnergy.value = s.energy;
    uniforms.uAlert.value = s.alert;
    uniforms.uAudio.value = s.audio;
    edgeUniforms.uTime.value = t;
    edgeUniforms.uMorph.value = s.morph;

    if (points.current) {
      // Ease the whole assembly back as it expands into a graph, so the constellation
      // stays in frame instead of pushing past the camera.
      const z = -s.morph * 1.4;
      points.current.position.z += (z - points.current.position.z) * Math.min(1, d * 2);
      points.current.rotation.y += d * (0.04 + s.energy * 0.05) * (1 - s.morph * 0.75);
      if (lines.current) {
        lines.current.position.copy(points.current.position);
        lines.current.rotation.copy(points.current.rotation);
      }
    }
  });

  return (
    <group>
      <points ref={points} geometry={geometry} frustumCulled={false}>
        <shaderMaterial
          vertexShader={ORB_VERT}
          fragmentShader={ORB_FRAG}
          uniforms={uniforms}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </points>
      <lineSegments ref={lines} geometry={edgeGeometry} frustumCulled={false}>
        <shaderMaterial
          vertexShader={EDGE_VERT}
          fragmentShader={EDGE_FRAG}
          uniforms={edgeUniforms}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </lineSegments>
    </group>
  );
}
