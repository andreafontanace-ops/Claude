import React from "react";
import { Easing, interpolate } from "remotion";

export const RoutePath: React.FC<{
  d: string;
  frame: number;
  range: readonly [number, number];
  color?: string;
  // Draw from the far end of the path back towards its start, for showing
  // the same road ridden in the opposite direction.
  reverse?: boolean;
  opacity?: number;
  width?: number;
}> = ({
  d,
  frame,
  range,
  color = "#c0392b",
  reverse = false,
  opacity = 1,
  width = 3.4,
}) => {
  const progress = interpolate(frame, range, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });

  // A round linecap still paints a dot for a zero-length dash, which would
  // leave a stray blob sitting on the map before the leg starts drawing.
  if (progress <= 0 || opacity <= 0) return null;

  // dasharray 1 over a pathLength of 1 means one "on" dash and one "off":
  // a positive offset slides the visible dash in from the start, a negative
  // one slides it in from the end.
  const dashOffset = reverse ? -(1 - progress) : 1 - progress;

  return (
    <g opacity={opacity}>
      {/* white casing so the line reads on any pastel tile underneath */}
      <path
        d={d}
        fill="none"
        stroke="#faf6ec"
        strokeWidth={width * 1.9}
        strokeLinecap="round"
        strokeLinejoin="round"
        pathLength={1}
        strokeDasharray={1}
        strokeDashoffset={dashOffset}
      />
      <path
        d={d}
        fill="none"
        stroke={color}
        strokeWidth={width}
        strokeLinecap="round"
        strokeLinejoin="round"
        pathLength={1}
        strokeDasharray={1}
        strokeDashoffset={dashOffset}
      />
    </g>
  );
};
