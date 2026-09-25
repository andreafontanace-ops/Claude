import React from "react";
import { interpolate, spring, useVideoConfig } from "remotion";
import { Camera, project } from "../shared/camera";

// The red X that lands on the easy road. Anchored in map units, so it stays on
// the line it is crossing out; sized in screen pixels, so it reads the same at
// any zoom.
//
// It falls in slightly too big and settles, like a stamp: one beat, legible in
// half a second with the sound off.
const SIZE = 150;
const STROKE = 26;
const RED = "#e63946";
const CASING = "#faf6ec";

export const CrossOut: React.FC<{
  camera: Camera;
  frame: number;
  x: number;
  y: number;
  range: readonly [number, number];
}> = ({ camera, frame, x, y, range }) => {
  const { fps } = useVideoConfig();
  if (frame < range[0]) return null;

  const { left, top } = project(camera, x, y);

  const land = spring({
    frame: frame - range[0],
    fps,
    durationInFrames: range[1] - range[0],
    config: { damping: 11, mass: 0.6, stiffness: 170 },
  });
  const scale = interpolate(land, [0, 1], [1.7, 1]);
  const opacity = interpolate(frame, [range[0], range[0] + 5], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const half = SIZE / 2;
  const arm = half - STROKE / 2;
  const strokes = (color: string, width: number) => (
    <g stroke={color} strokeWidth={width} strokeLinecap="round">
      <line x1={half - arm} y1={half - arm} x2={half + arm} y2={half + arm} />
      <line x1={half + arm} y1={half - arm} x2={half - arm} y2={half + arm} />
    </g>
  );

  return (
    <svg
      width={SIZE}
      height={SIZE}
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      style={{
        position: "absolute",
        left,
        top,
        opacity,
        overflow: "visible",
        transform: `translate(-50%, -50%) scale(${scale})`,
        filter: "drop-shadow(0 6px 10px rgba(0,0,0,0.3))",
      }}
    >
      {/* Cream casing first, so the X reads over the blue line and over any
          tile underneath it. */}
      {strokes(CASING, STROKE + 12)}
      {strokes(RED, STROKE)}
    </svg>
  );
};
