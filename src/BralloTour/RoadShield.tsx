import React from "react";
import { interpolate } from "remotion";
import { Camera, project } from "../shared/camera";
import { pointAtProgress } from "../shared/polyline";
import { fontFamily } from "../shared/fonts";

// A road number set beside its road: "SP88" on a plate in the road's own
// colour, so which label belongs to which line needs no reading.
//
// Anchored to a point along the road (by arc fraction), then pushed off it
// sideways in screen pixels so it sits beside the line rather than on it.
export const RoadShield: React.FC<{
  camera: Camera;
  frame: number;
  points: readonly (readonly [number, number])[];
  // Where along the road, 0..1 by arc length.
  at: number;
  dx: number;
  dy?: number;
  revealFrame: number;
  label: string;
  color: string;
}> = ({ camera, frame, points, at, dx, dy = 0, revealFrame, label, color }) => {
  const opacity = interpolate(frame, [revealFrame, revealFrame + 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const pop = interpolate(frame, [revealFrame, revealFrame + 8, revealFrame + 14], [0.6, 1.08, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  if (opacity <= 0) return null;

  const p = pointAtProgress(points, at);
  const { left, top } = project(camera, p.x, p.y);

  return (
    <div
      style={{
        position: "absolute",
        left: left + dx,
        top: top + dy,
        opacity,
        transform: `translate(-50%, -50%) scale(${pop})`,
        padding: "6px 14px",
        borderRadius: 10,
        background: color,
        border: "4px solid #faf6ec",
        boxShadow: "0 3px 8px rgba(0,0,0,0.25)",
        color: "#ffffff",
        fontFamily,
        fontWeight: 800,
        fontSize: 34,
        letterSpacing: 1,
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </div>
  );
};
