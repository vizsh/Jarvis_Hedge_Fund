"use client";

import { useRef, useState, type MouseEvent, type ReactNode } from "react";
import { motion, useSpring } from "framer-motion";

type TiltedCardProps = {
  children: ReactNode;
  className?: string;
  containerClassName?: string;
  rotateAmplitude?: number;
  glareOpacity?: number;
};

/**
 * ReactBits-style TiltedCard — 3D perspective tilt that follows the cursor,
 * with a soft glare highlight.
 */
export default function TiltedCard({
  children,
  className = "",
  containerClassName = "",
  rotateAmplitude = 8,
  glareOpacity = 0.14,
}: TiltedCardProps) {
  const ref = useRef<HTMLDivElement>(null);
  const rotateX = useSpring(0, { stiffness: 180, damping: 18, mass: 0.5 });
  const rotateY = useSpring(0, { stiffness: 180, damping: 18, mass: 0.5 });
  const [glare, setGlare] = useState({ x: 50, y: 50, opacity: 0 });

  const handleMouseMove = (e: MouseEvent<HTMLDivElement>) => {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width;
    const py = (e.clientY - rect.top) / rect.height;
    rotateY.set((px - 0.5) * rotateAmplitude * 2);
    rotateX.set(-(py - 0.5) * rotateAmplitude * 2);
    setGlare({ x: px * 100, y: py * 100, opacity: glareOpacity });
  };

  const handleMouseLeave = () => {
    rotateX.set(0);
    rotateY.set(0);
    setGlare((g) => ({ ...g, opacity: 0 }));
  };

  return (
    <div
      className={containerClassName}
      style={{ perspective: "1100px" }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      <motion.div
        ref={ref}
        style={{ rotateX, rotateY, transformStyle: "preserve-3d" }}
        className={`relative will-change-transform ${className}`}
      >
        {children}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 z-20 rounded-[inherit] transition-opacity duration-300"
          style={{
            opacity: glare.opacity,
            background: `radial-gradient(circle at ${glare.x}% ${glare.y}%, rgba(255,255,255,0.9), transparent 55%)`,
            mixBlendMode: "overlay",
          }}
        />
      </motion.div>
    </div>
  );
}
