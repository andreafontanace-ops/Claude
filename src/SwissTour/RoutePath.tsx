import React from "react";
import { Easing, interpolate } from "remotion";

export const RoutePath: React.FC<{
  d: string;
  frame: number;
  range: readonly [number, number];
  color?: string;
}> = ({ d, frame, range, color = "#c0392b" }) => {
  const progress = interpolate(frame, range, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });

  return (
    <>
      {/* white casing so the line reads on any pastel tile underneath */}
      <path
        d={d}
        fill="none"
        stroke="#faf6ec"
        strokeWidth={6.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        pathLength={1}
        strokeDasharray={1}
        strokeDashoffset={1 - progress}
      />
      <path
        d={d}
        fill="none"
        stroke={color}
        strokeWidth={3.4}
        strokeLinecap="round"
        strokeLinejoin="round"
        pathLength={1}
        strokeDasharray={1}
        strokeDashoffset={1 - progress}
      />
    </>
  );
};
