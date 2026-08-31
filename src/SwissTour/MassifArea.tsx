import React from "react";
import { Easing, interpolate } from "remotion";
import { MASSIF_RING_D } from "./geoData";

// The block of mountains the two roads run either side of, drawn as the
// area they enclose: out along one branch, back along the other. A warm
// grey-brown reads as rock over the pastel cantons without competing with
// the blue and red of the roads.
export const MassifArea: React.FC<{
  frame: number;
  range: readonly [number, number];
}> = ({ frame, range }) => {
  const t = interpolate(frame, range, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  if (t <= 0) return null;

  return (
    <g opacity={t}>
      <path d={MASSIF_RING_D} fill="#6b5f47" fillOpacity={0.34} />
      <path
        d={MASSIF_RING_D}
        fill="none"
        stroke="#5b503b"
        strokeOpacity={0.5}
        strokeWidth={1.6}
      />
    </g>
  );
};
