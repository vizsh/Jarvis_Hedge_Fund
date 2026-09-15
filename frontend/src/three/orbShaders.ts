// The particle core. One BufferGeometry, two destinations, one uniform between them.
//
// The single most important decision in this file: the orb and the provenance graph
// are the SAME particles. uMorph slides each particle from its home on the sphere to
// its seat in the graph. A crossfade between two components reads as two components;
// a morph reads as one machine changing its mind, which is the whole effect we want.
//
// Each particle carries:
//   aSphere  its resting position on the shell
//   aTarget  its seat in the graph (set when a graph arrives)
//   aSeed    per-particle randomness so nothing moves in lockstep
//   aTint    0 neutral, 1 bull, 2 bear, 3 evidence, 4 risk -- colour by role in the graph

export const ORB_VERT = /* glsl */ `
precision highp float;

attribute vec3  aSphere;
attribute vec3  aTarget;
attribute float aSeed;
attribute float aTint;

uniform float uTime;
uniform float uMorph;      // 0 = orb, 1 = graph
uniform float uAudio;      // 0..1 mic or TTS envelope
uniform float uEnergy;     // 0..1 thinking intensity
uniform float uAlert;      // 0..1 risk breach
uniform float uSize;
uniform float uPixelRatio;

varying float vTint;
varying float vDepth;
varying float vSpark;
varying float vCore;

// Cheap 3D simplex-ish noise. Good enough for organic drift, far cheaper than the real
// thing at 24k vertices on an integrated GPU.
vec3 hash3(vec3 p) {
  p = vec3(dot(p, vec3(127.1, 311.7, 74.7)),
           dot(p, vec3(269.5, 183.3, 246.1)),
           dot(p, vec3(113.5, 271.9, 124.6)));
  return -1.0 + 2.0 * fract(sin(p) * 43758.5453123);
}

float noise(vec3 p) {
  vec3 i = floor(p), f = fract(p);
  vec3 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(dot(hash3(i + vec3(0,0,0)), f - vec3(0,0,0)),
                     dot(hash3(i + vec3(1,0,0)), f - vec3(1,0,0)), u.x),
                 mix(dot(hash3(i + vec3(0,1,0)), f - vec3(0,1,0)),
                     dot(hash3(i + vec3(1,1,0)), f - vec3(1,1,0)), u.x), u.y),
             mix(mix(dot(hash3(i + vec3(0,0,1)), f - vec3(0,0,1)),
                     dot(hash3(i + vec3(1,0,1)), f - vec3(1,0,1)), u.x),
                 mix(dot(hash3(i + vec3(0,1,1)), f - vec3(0,1,1)),
                     dot(hash3(i + vec3(1,1,1)), f - vec3(1,1,1)), u.x), u.y), u.z);
}

void main() {
  vTint = aTint;
  vCore = 1.0 - clamp(length(aSphere) / 1.95, 0.0, 1.0);

  // --- orb pose -------------------------------------------------------------
  vec3 dir = normalize(aSphere);
  float n = noise(aSphere * 1.35 + vec3(0.0, uTime * 0.16, 0.0));

  // Breathing shell. Audio pushes it outward; thinking makes it churn.
  float breathe = 0.035 * sin(uTime * 0.9 + aSeed * 6.2831);
  float displace = n * (0.16 + uEnergy * 0.30) + breathe + uAudio * 0.34;
  vec3 orbPos = aSphere + dir * displace;

  // Slow differential rotation so the shell never looks like a rigid body.
  float spin = uTime * (0.055 + 0.045 * aSeed) + uEnergy * uTime * 0.09;
  float c = cos(spin), s = sin(spin);
  orbPos = vec3(orbPos.x * c - orbPos.z * s, orbPos.y, orbPos.x * s + orbPos.z * c);

  // --- graph pose -----------------------------------------------------------
  // A little per-particle jitter around the node keeps clusters from reading as
  // hard dots, and a slow orbit keeps the constellation alive.
  vec3 jitter = hash3(vec3(aSeed * 91.7)) * 0.10;
  float orbit = uTime * 0.25 + aSeed * 6.2831;
  vec3 graphPos = aTarget + jitter + vec3(sin(orbit), cos(orbit * 0.8), cos(orbit)) * 0.035;

  // --- the morph ------------------------------------------------------------
  // Stagger by seed so the shell peels apart in waves instead of snapping. The arc
  // term lifts particles off a straight line so they sweep rather than slide.
  float stagger = clamp((uMorph - aSeed * 0.35) / 0.65, 0.0, 1.0);
  float e = stagger * stagger * (3.0 - 2.0 * stagger);
  vec3 pos = mix(orbPos, graphPos, e);
  pos += normalize(cross(orbPos, vec3(0.0, 1.0, 0.0))) * sin(e * 3.14159) * 0.55;

  vec4 mv = modelViewMatrix * vec4(pos, 1.0);
  gl_Position = projectionMatrix * mv;

  vDepth = -mv.z;
  // Sparkle: a slow per-particle twinkle, pushed hard during an alert.
  vSpark = 0.55 + 0.45 * sin(uTime * 2.1 + aSeed * 24.0) + uAlert * 0.5;

  float size = uSize * (0.35 + aSeed * 0.9) * (1.0 + vCore * 0.5) * (1.0 + uAudio * 0.8 + uEnergy * 0.3);
  gl_PointSize = clamp(size * uPixelRatio * (9.5 / max(vDepth, 0.6)), 0.8, 8.0);
}
`;

export const ORB_FRAG = /* glsl */ `
precision highp float;

uniform float uAlert;
uniform float uMorph;
uniform vec3  uColdColor;
uniform vec3  uWarmColor;

varying float vTint;
varying float vDepth;
varying float vSpark;
varying float vCore;

void main() {
  // Round, soft-edged point. Discarding early is much cheaper than blending a
  // full quad 24k times.
  vec2 uv = gl_PointCoord - 0.5;
  float d = dot(uv, uv);
  if (d > 0.25) discard;
  float alpha = smoothstep(0.25, 0.0, d);

  // Role colours only assert themselves once the graph has formed, so the idle orb
  // stays a single coherent object rather than a bag of confetti.
  vec3 col = mix(uColdColor, uWarmColor, clamp(vDepth * 0.055, 0.0, 1.0));
  vec3 bull = vec3(0.13, 1.00, 0.63);
  vec3 bear = vec3(1.00, 0.28, 0.42);
  vec3 fact = vec3(0.45, 0.78, 1.00);
  vec3 risk = vec3(1.00, 0.72, 0.20);

  vec3 role = col;
  if (vTint > 0.5 && vTint < 1.5) role = bull;
  else if (vTint > 1.5 && vTint < 2.5) role = bear;
  else if (vTint > 2.5 && vTint < 3.5) role = fact;
  else if (vTint > 3.5) role = risk;

  col = mix(col, role, clamp(uMorph * 1.25, 0.0, 1.0));
  col = mix(col, risk, uAlert * 0.35);
  col *= vSpark;

  // Additive-ish core: bright centre, quick falloff. Reads as emissive against black.
  // Radial gain: the nucleus burns white-hot, the halo stays cool and sparse.
  float gain = 0.30 + pow(vCore, 2.0) * 3.4;
  col = mix(col, vec3(0.86, 0.96, 1.0), pow(vCore, 3.0) * 0.72);

  float core = pow(alpha, 2.4);
  gl_FragColor = vec4(col * gain * (0.30 + core * 1.3), alpha * 0.72);
}
`;

// --- connective tissue between graph nodes ----------------------------------------
// Pulses travel along each edge from source to target, so the graph reads as something
// flowing rather than a static wireframe.
export const EDGE_VERT = /* glsl */ `
precision highp float;
attribute float aProgress;   // 0..1 along the edge
attribute float aEdgeSeed;
attribute float aTint;
uniform float uTime;
uniform float uMorph;
varying float vAlpha;
varying float vTint;
void main() {
  vTint = aTint;
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  gl_Position = projectionMatrix * mv;

  // A travelling bright band; the rest of the line stays dim.
  float head = fract(uTime * 0.32 + aEdgeSeed);
  float dist = abs(aProgress - head);
  dist = min(dist, 1.0 - dist);
  float pulse = smoothstep(0.14, 0.0, dist);
  vAlpha = (0.10 + pulse * 0.9) * smoothstep(0.35, 1.0, uMorph);
}
`;

export const EDGE_FRAG = /* glsl */ `
precision highp float;
varying float vAlpha;
varying float vTint;
void main() {
  vec3 cyan = vec3(0.33, 0.85, 1.00);
  vec3 bull = vec3(0.13, 1.00, 0.63);
  vec3 bear = vec3(1.00, 0.28, 0.42);
  vec3 col = cyan;
  if (vTint > 0.5 && vTint < 1.5) col = bull;
  else if (vTint > 1.5 && vTint < 2.5) col = bear;
  gl_FragColor = vec4(col, vAlpha);
}
`;
