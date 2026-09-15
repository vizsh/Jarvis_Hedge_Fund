import { useEffect, useState } from "react";

import { useStore } from "../lib/store";
import { send, sendBoot } from "../lib/socket";

export interface ScriptStep {
  key: string;
  command: string;
  say: string;
  beat?: string;
}

/** Presenter view: the line to say, and one key to fire the command behind it.
 *
 *  The point is that you are never typing while talking. Advancing runs the command
 *  and moves the prompt on together, so your hands leave the keyboard between beats.
 */
export function Teleprompter() {
  const [steps, setSteps] = useState<ScriptStep[]>([]);
  const [title, setTitle] = useState("");
  const [index, setIndex] = useState(0);
  const [open, setOpen] = useState(false);
  const replay = useStore((s) => s.replay);

  useEffect(() => {
    fetch("/script")
      .then((r) => r.json())
      .then((d) => { setSteps(d.steps ?? []); setTitle(d.title ?? ""); })
      .catch(() => { /* no script file; the HUD still works without one */ });
  }, []);

  useEffect(() => {
    const fire = (step: ScriptStep | undefined) => {
      if (!step) return;
      const cmd = (step.command || "").trim();
      if (cmd === "@boot") sendBoot();
      else if (cmd && cmd !== "@none") send(cmd);
    };

    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return;

      if (e.key === "t" || e.key === "T") { setOpen((v) => !v); return; }
      if (!open) return;

      if (e.key === "ArrowRight" || e.key === "PageDown") {
        e.preventDefault();
        setIndex((i) => {
          const next = Math.min(i + 1, steps.length - 1);
          fire(steps[next]);
          return next;
        });
      }
      if (e.key === "ArrowLeft" || e.key === "PageUp") {
        e.preventDefault();
        // Step back WITHOUT firing: you are usually going back to re-say a line, not
        // to re-run a trade. Re-running is an explicit Enter.
        setIndex((i) => Math.max(i - 1, 0));
      }
      if (e.key === "Enter") { e.preventDefault(); fire(steps[index]); }
      if (e.key === "Home") { e.preventDefault(); setIndex(0); }
    };

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, steps, index]);

  if (!open || !steps.length) {
    return (
      <div className="prompter-hint">
        {replay.active ? null : <span>press <b>T</b> for presenter mode</span>}
      </div>
    );
  }

  const step = steps[index];
  return (
    <div className="prompter">
      <div className="prompter-head">
        <span>{title}</span>
        <span>
          {index + 1} / {steps.length} · {step.key}
          {replay.active && <b className="replay-tag"> REPLAY</b>}
        </span>
      </div>
      <div className="prompter-say">{step.say}</div>
      <div className="prompter-foot">
        <span className="cmd">
          {step.command === "@none" ? "— narration only —"
            : step.command === "@boot" ? "cold boot"
            : step.command}
        </span>
        {step.beat && <span className="beat">{step.beat}</span>}
        <span className="keys">→ next · ← back · ⏎ re-run · T hide</span>
      </div>
      <div className="prompter-rail">
        {steps.map((s, i) => (
          <div key={s.key} className={`tick ${i === index ? "on" : ""} ${i < index ? "done" : ""}`}
               onClick={() => setIndex(i)} title={s.key} />
        ))}
      </div>
    </div>
  );
}

/** Honest indicator. A fallback you cannot distinguish from the live system is a lie
 *  waiting to be found — and "that is a recording, here is the live one" is a fine
 *  answer to have ready. */
export function ReplayBanner() {
  const replay = useStore((s) => s.replay);
  if (!replay.active) return null;
  return (
    <div className="replay-banner">
      <span className="pulse" />
      REPLAY · {replay.name ?? "recorded take"}
      <span className="bar"><span style={{ width: `${replay.progress * 100}%` }} /></span>
      <button className="btn" onClick={() => fetch("/replay/stop", { method: "POST" })}>
        Stop
      </button>
    </div>
  );
}
