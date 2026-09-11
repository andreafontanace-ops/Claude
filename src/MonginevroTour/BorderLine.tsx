import React from "react";
import { interpolate } from "remotion";
import { FRONTIER_D } from "./geoData";

// The Italy-France frontier, Mont Blanc down to the sea, lifted straight out
// of the boundary data. It is the film's subject, so it is on screen from the
// first frame; the crossing simply makes it louder for a moment.
export const BorderLine: React.FC<{
  frame: number;
  introRange: readonly [number, number];
  emphasisRange: readonly [number, number];
  scale: number;
}> = ({ frame, introRange, emphasisRange, scale }) => {
  const opacity = interpolate(frame, introRange, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const emphasis = interpolate(
    frame,
    [emphasisRange[0], emphasisRange[0] + 14, emphasisRange[1]],
    [0, 1, 0.5],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  if (opacity <= 0) return null;

  const width = 5 / scale;

  return (
    <g opacity={opacity}>
      {emphasis > 0 && (
        <path
          d={FRONTIER_D}
          fill="none"
          stroke="#3d3527"
          strokeOpacity={0.18 * emphasis}
          strokeWidth={width * 4}
          strokeLinecap="round"
        />
      )}
      <path
        d={FRONTIER_D}
        fill="none"
        stroke="#3d3527"
        strokeOpacity={0.8}
        strokeWidth={width}
        strokeLinecap="round"
        strokeDasharray={`${10 / scale} ${7 / scale}`}
      />
    </g>
  );
};
