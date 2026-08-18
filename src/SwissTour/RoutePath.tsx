import React from "react";
import { Easing, interpolate } from "remotion";

export const RoutePath: React.FC<{
  d: string;
  frame: number;
  range: readonly [number, number];
  color?: string;
}> = ({ d, frame, range, color = "#ff7a45" }) => {
  const progress = interpolate(frame, range, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });

  return (
    <>
      {/* soft underlay glow */}
      <path
        d={d}
        fill="none"
        stroke={color}
        strokeOpacity={0.35}
        strokeWidth={7}
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
        strokeWidth={3}
        strokeLinecap="round"
        strokeLinejoin="round"
        pathLength={1}
        strokeDasharray={1}
        strokeDashoffset={1 - progress}
      />
    </>
  );
};
