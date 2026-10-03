import { useEffect, useRef, useState } from "react";

import * as socket from "../lib/socket";
import { useVoice } from "../lib/voice";
import { hiError, useT } from "../lib/i18n";

/** A microphone, drawn as an icon rather than labelled "HOLD".
 *
 *  The old control was a text button reading HOLD, which says nothing about what it is
 *  for. A microphone glyph is the one symbol everybody already reads as "talk here". */
export function MicIcon({ size = 18 }: { size?: number }) {
  return (
    <svg className="mic-icon" viewBox="0 0 24 24" width={size} height={size} fill="none"
         stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"
         strokeLinejoin="round" aria-hidden="true">
      <rect x="9" y="2.5" width="6" height="11.5" rx="3" />
      <path d="M5 11.2a7 7 0 0 0 14 0" />
      <path d="M12 18.2V21.5" />
      <path d="M8.6 21.5h6.8" />
    </svg>
  );
}

const sentence = (s: string, n = 64) => (s.length > n ? s.slice(0, n - 1) + "…" : s);

/** The microphone button in the command panel. Tap to start, tap again to send. */
export function MicButton() {
  const { t } = useT();
  const status = useVoice((s) => s.status);
  const toggle = useVoice((s) => s.toggle);

  const label =
    status === "listening" ? t("STOP", "रोकें")
    : status === "processing" ? t("WAIT", "रुकिए")
    : status === "starting" ? "…"
    : t("SPEAK", "बोलिए");

  return (
    <button
      id="mic-button"
      type="button"
      className={`btn mic ${status}`}
      onClick={toggle}
      disabled={status === "processing"}
      aria-pressed={status === "listening"}
      aria-label={status === "listening" ? t("Stop listening and send", "सुनना बंद करके भेजें") : t("Speak to JARVIS", "जार्विस से बोलिए")}
      title={t("Tap to speak, then pause or tap again to send. Esc cancels.", "बोलने के लिए दबाइए, फिर रुकिए या दोबारा दबाकर भेजिए। Esc रद्द करता है।")}
    >
      <MicIcon size={15} />
      <span>{label}</span>
    </button>
  );
}

/** The button at the centre of the orb.
 *
 *  Anchored where the orb renders. The camera in App.tsx sits at (0, 0.35, 6) with a
 *  54-degree vertical field of view, so the world origin -- the orb's centre -- projects
 *  to the horizontal middle and about 56% of the way down, independent of window size.
 *  Everything about its state is spelled out in words under it, because the failure
 *  this replaces was a microphone you could not tell was listening.
 */
export function OrbMic() {
  const { hi, t } = useT();
  const status = useVoice((s) => s.status);
  const speaking = useVoice((s) => s.speaking);
  const heard = useVoice((s) => s.heard);
  const heardAt = useVoice((s) => s.heardAt);
  const error = useVoice((s) => s.error);
  const toggle = useVoice((s) => s.toggle);
  const ring = useRef<HTMLSpanElement>(null);
  const [, tick] = useState(0);

  // Drive the ring from the REAL input level, one frame at a time. A canned pulse would
  // keep animating while the microphone heard nothing, which is the lie to avoid.
  useEffect(() => {
    const el = ring.current;
    if (status !== "listening") { el?.style.setProperty("--lvl", "0"); return; }
    let raf = 0;
    const loop = () => {
      el?.style.setProperty("--lvl", String(Math.min(1, socket.lastLevel * 1.6)));
      raf = requestAnimationFrame(loop);
    };
    loop();
    return () => cancelAnimationFrame(raf);
  }, [status]);

  // Let "I heard ..." fade back to the idle prompt after a few seconds.
  useEffect(() => {
    if (!heardAt) return;
    const id = window.setTimeout(() => tick((n) => n + 1), 7000);
    return () => window.clearTimeout(id);
  }, [heardAt]);

  const recentlyHeard = !!heard && Date.now() - heardAt < 7000;

  let caption: string;
  let sub: string | null = null;
  if (status === "starting") {
    caption = t("ALLOW THE MICROPHONE", "माइक की अनुमति दीजिए");
    sub = t("Choose Allow if your browser asks", "ब्राउज़र पूछे तो अनुमति चुनिए");
  } else if (status === "listening") {
    caption = speaking ? t("HEARING YOU", "सुन रहा हूँ") : t("LISTENING — SPEAK NOW", "सुन रहा हूँ — अब बोलिए");
    sub = speaking ? t("Pause when you are done, or tap to send", "बोल चुकें तो रुकिए, या भेजने के लिए दबाइए") : t("Tap again to cancel, or just start talking", "रद्द करने के लिए फिर दबाइए, या बोलना शुरू कीजिए");
  } else if (status === "processing") {
    caption = t("TRANSCRIBING", "लिख रहा हूँ");
    sub = t("Running on this machine — nothing leaves it", "यहीं इसी मशीन पर चल रहा है — कुछ बाहर नहीं जाता");
  } else if (error) {
    caption = t("TAP TO TRY AGAIN", "फिर कोशिश के लिए दबाइए");
    sub = hiError(error, hi);
  } else if (recentlyHeard) {
    caption = t("I HEARD", "मैंने सुना");
    sub = `“${sentence(heard)}”`;
  } else {
    caption = t("TAP THE ORB TO SPEAK", "बोलने के लिए ऑर्ब दबाइए");
  }

  return (
    <div className={`orbmic ${status} ${speaking ? "hearing" : ""} ${error && status === "idle" ? "bad" : ""}`}>
      <button
        id="orb-mic"
        type="button"
        className="orbmic-btn"
        onClick={toggle}
        aria-label={t("Speak to JARVIS", "जार्विस से बोलिए")}
        aria-pressed={status === "listening"}
        title={t("Tap to speak. Pause, or tap again, to send.", "बोलने के लिए दबाइए। रुकिए, या भेजने के लिए फिर दबाइए।")}
      >
        <span className="orbmic-ring r1" ref={ring} />
        <span className="orbmic-ring r2" />
        <span className="orbmic-core"><MicIcon size={26} /></span>
      </button>
      <div className="orbmic-text" role="status" aria-live="polite">
        <div className="orbmic-cap">{caption}</div>
        {sub && <div className="orbmic-sub">{sub}</div>}
      </div>
    </div>
  );
}
