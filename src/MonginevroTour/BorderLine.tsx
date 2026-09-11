import React from "react";
import { Easing, interpolate } from "remotion";
import { BORDER_D } from "./geoData";

// The Italy-France border where the road crosses it, lifted straight out of
// the department outline. It draws itself outward from the crossing point
// rather than fading in as a whole, so the eye is taken to the spot the road
// is about to pass through.
export const BorderLine: React.FC<{
  frame: number;
  range: readonly [number, number];
  scale: number;
}> = ({ frame, range, scale }) => {
  const draw = interpolate(frame, [range[0], range[0] + 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  // It settles back to a quieter line once it has been noticed, so it does
  // not compete with the road for the rest of the shot.
  const glow = interpolate(frame, [range[0] + 10, range[1]], [1, 0.45], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  if (draw <= 0) return null;

  const width = 5 / scale;

  return (
    <g>
      <path
        d={BORDER_D}
        fill="none"
        stroke="#3d3527"
        strokeOpacity={0.16 * glow}
        strokeWidth={width * 4}
        strokeLinecap="round"
        pathLength={1}
        strokeDasharray={1}
        strokeDashoffset={1 - draw}
      />
      <path
        d={BORDER_D}
        fill="none"
        stroke="#3d3527"
        strokeOpacity={0.85}
        strokeWidth={width}
        strokeLinecap="round"
        strokeDasharray={`${10 / scale} ${7 / scale}`}
        pathLength={1}
      />
    </g>
  );
};
