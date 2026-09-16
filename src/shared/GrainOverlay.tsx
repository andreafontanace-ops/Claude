import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";

// Ported from the HyperFrames registry component `grain-overlay`
// (npx hyperframes add grain-overlay -> hyperframes/compositions/components/
// grain-overlay.html). The texture and the keyframes are theirs; what changes
// is who drives the clock.
//
// A CSS animation runs on wall-clock time, which is exactly what a
// frame-by-frame renderer does not have: left alone it would either freeze on
// frame 0 or land somewhere different on every render. Pausing it and feeding
// it a negative delay equal to the current time seeks it to the right point in
// its cycle instead - deterministic, frame-exact, and no intermediate file.
const NOISE =
  "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E\")";

const KEYFRAMES = `
@keyframes hf-grain-noise {
  0%, 100% { transform: translate(0, 0); }
  10% { transform: translate(-5%, -5%); }
  20% { transform: translate(-10%, 5%); }
  30% { transform: translate(5%, -10%); }
  40% { transform: translate(-5%, 15%); }
  50% { transform: translate(-10%, 5%); }
  60% { transform: translate(15%, 0); }
  70% { transform: translate(0, 10%); }
  80% { transform: translate(-15%, 0); }
  90% { transform: translate(10%, 5%); }
}`;

export const GrainOverlay: React.FC<{
  // The registry ships this at 0.15, which reads as video noise. On a pale
  // paper map a fraction of that reads as print instead.
  opacity?: number;
  // Seconds per cycle. The registry default is 0.5s, stepped, so the grain
  // jumps ten times a second rather than sliding.
  cycle?: number;
}> = ({ opacity = 0.07, cycle = 0.5 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        pointerEvents: "none",
        mixBlendMode: "multiply",
      }}
    >
      <style>{KEYFRAMES}</style>
      <div
        style={{
          position: "absolute",
          top: "-50%",
          left: "-50%",
          width: "200%",
          height: "200%",
          background: NOISE,
          opacity,
          animation: `hf-grain-noise ${cycle}s steps(1) infinite`,
          animationDelay: `${-(frame / fps)}s`,
          animationPlayState: "paused",
        }}
      />
    </div>
  );
};
