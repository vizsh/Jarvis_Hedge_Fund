"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useScroll, useSpring, useTransform } from "framer-motion";
import CreditCardArt from "./credit-card";

/* ------------------------------------------------------------------ */
/*  CardJourney                                                        */
/*  Wraps the middle sections. A sticky full-screen layer hosts the    */
/*  black credit card. Instead of drifting freely, the card DOCKS at   */
/*  one designed slot per section and holds while you read, then       */
/*  glides to the next slot at section boundaries:                     */
/*                                                                     */
/*    Problem     →  open center between the two stat clusters          */
/*    Pillars     →  docks INTO the dashed card recess in the bento      */
/*    Explainable →  center slot between the copy and the dashboard      */
/*    HowItWorks  →  right-hand slot beside the step grid                */
/*    end         →  dives away before the footer                      */
/* ------------------------------------------------------------------ */

function useIsDesktop() {
  const [isDesktop, setIsDesktop] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1024px)");
    const onChange = () => setIsDesktop(mq.matches);
    onChange();
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);
  return isDesktop;
}

/* progress stops for the 4-section track (each section ≈ 1/3 of scroll) */
const STOPS = [0, 0.16, 0.3, 0.42, 0.56, 0.62, 0.78, 0.86, 0.94, 0.985, 1];

const DESKTOP = {
  x: ["0vw", "0vw", "0vw", "0vw", "-2vw", "-4vw", "-4vw", "27vw", "27vw", "27vw", "27vw"],
  y: ["-13vh", "-13vh", "11vh", "11vh", "6vh", "0vh", "1vh", "0vh", "2vh", "55vh", "72vh"],
  rotate: [-6, -6, -3, -3, -3, -3, -3, 6, 5, -14, -18],
  scale: [1, 1, 0.8, 0.8, 0.86, 0.9, 0.9, 0.96, 0.96, 0.9, 0.88],
};

const MOBILE = {
  x: ["0vw", "0vw", "5vw", "5vw", "-5vw", "-5vw", "-5vw", "7vw", "7vw", "7vw", "7vw"],
  y: ["-6vh", "-6vh", "10vh", "10vh", "6vh", "6vh", "7vh", "8vh", "10vh", "50vh", "64vh"],
  rotate: [-5, -5, 4, 4, -3, -3, -3, 4, 4, -10, -14],
  scale: [0.9, 0.9, 0.85, 0.85, 0.85, 0.85, 0.85, 0.9, 0.9, 0.85, 0.82],
};

export default function CardJourney({
  children,
}: {
  children: React.ReactNode;
}) {
  const trackRef = useRef<HTMLDivElement>(null);
  const isDesktop = useIsDesktop();

  const { scrollYProgress } = useScroll({
    target: trackRef,
    offset: ["start start", "end end"],
  });

  // snappy enough to land in a slot, smooth enough to feel cinematic
  const smooth = useSpring(scrollYProgress, {
    stiffness: 110,
    damping: 24,
    mass: 0.5,
  });

  const pose = isDesktop ? DESKTOP : MOBILE;

  const x = useTransform(smooth, STOPS, pose.x);
  const y = useTransform(smooth, STOPS, pose.y);
  const rotate = useTransform(smooth, STOPS, pose.rotate);
  const scale = useTransform(smooth, STOPS, pose.scale);
  const opacity = useTransform(
    smooth,
    [0, 0.03, 0.95, 0.985],
    [0.5, 1, 1, 0],
  );

  return (
    <div ref={trackRef} className="relative">
      {/* sticky viewport-height layer that cancels its own layout space */}
      <div className="pointer-events-none sticky top-0 z-40 -mb-[100vh] h-screen">
        <div className="absolute inset-0 flex items-center justify-center">
          <motion.div
            style={{ x, y, rotate, scale, opacity }}
            className="will-change-transform"
          >
            <CreditCardArt />
          </motion.div>
        </div>
      </div>

      {children}
    </div>
  );
}
