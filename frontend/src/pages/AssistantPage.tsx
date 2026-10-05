import { Canvas } from "@react-three/fiber";
import { Bloom, EffectComposer, Vignette } from "@react-three/postprocessing";

import "../styles-assistant.css";

import { JobsLauncher } from "../components/Actions";
import { ChatThread } from "../components/ChatThread";
import { Composer } from "../components/Composer";
import { TourPicker } from "../components/TourPicker";
import { OrbMic } from "../components/VoiceInput";
import { Orb } from "../three/Orb";

/** The assistant: a conversation on the left (each question above its own answer, the message box under it), and on the right
 *  the voice orb, the guided tours of every feature, and the ready-made jobs. */
export function Assistant() {
  return (
    <div className="as-stage">
      <ChatColumn />
      <aside className="as-rail" aria-label="Voice, tours and jobs">
        <div className="as-orb" data-theme="dark" data-tour="orb">
          <Canvas camera={{ position: [0, 0.35, 6.0], fov: 54 }} dpr={[1, 1.5]} gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}>
            <Orb />
            <EffectComposer>
              <Bloom intensity={0.75} luminanceThreshold={0.22} luminanceSmoothing={0.6} mipmapBlur radius={0.6} />
              <Vignette eskil={false} offset={0.22} darkness={0.85} />
            </EffectComposer>
          </Canvas>
          <OrbMic />
        </div>
        <TourPicker />
        <div className="as-jobs" data-tour="jobs"><JobsLauncher compact /></div>
      </aside>
    </div>
  );
}

function ChatColumn() {
  return (
    <div className="as-col">
      <ChatThread />
      <div className="as-dock"><Composer /></div>
    </div>
  );
}
