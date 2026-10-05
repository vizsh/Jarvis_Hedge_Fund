import { useEffect, useRef } from "react";

import * as socket from "../lib/socket";

/** Live microphone waveform.
 *
 *  This exists because of a real failure: you could not tell whether the microphone
 *  was hearing you until after you released the key and the transcript came back
 *  wrong. It draws the ACTUAL FFT frame — a decorative animation would bounce along
 *  happily while the mic picked up silence, which is the one thing it must not do.
 *
 *  The bar turns amber when the signal is too quiet to transcribe reliably, so the
 *  fix ("speak up, or pick the other microphone") is visible before you finish talking.
 */
export function Waveform({ active }: { active: boolean }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const raf = useRef(0);

  useEffect(() => {
    if (!active) { cancelAnimationFrame(raf.current); return; }
    const el = canvas.current;
    const ctx = el?.getContext("2d");
    if (!el || !ctx) return;

    const draw = () => {
      const dpr = Math.min(window.devicePixelRatio, 2);
      const w = el.clientWidth, h = el.clientHeight;
      if (el.width !== w * dpr) { el.width = w * dpr; el.height = h * dpr; }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);

      const bins = socket.spectrum;
      const n = bins.length || 1;
      let peak = 0;
      for (let i = 0; i < bins.length; i++) peak = Math.max(peak, bins[i] / 255);

      // Below this the recogniser will struggle; say so while it can still be fixed.
      const weak = peak < 0.12;
      const bar = w / n;
      for (let i = 0; i < n; i++) {
        const v = (bins[i] ?? 0) / 255;
        const bh = Math.max(1.5, v * h * 0.92);
        ctx.fillStyle = weak
          ? `rgba(255, 159, 90,${0.25 + v * 0.7})`
          : `rgba(242, 185, 75,${0.25 + v * 0.75})`;
        ctx.fillRect(i * bar, (h - bh) / 2, Math.max(1, bar - 1), bh);
      }
      raf.current = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf.current);
  }, [active]);

  if (!active) return null;
  return <canvas className="waveform" ref={canvas} />;
}
