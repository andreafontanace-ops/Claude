import React from "react";
import { Easing, interpolate } from "remotion";
import { Camera, project } from "./useCamera";
import { pointAtProgress } from "./polyline";
import { ROUTE_RED } from "./palette";

export const TravelDot: React.FC<{
  points: readonly (readonly [number, number])[];
  camera: Camera;
  frame: number;
  range: readonly [number, number];
  color?: string;
  reverse?: boolean;
}> = ({ points, camera, frame, range, color = ROUTE_RED, reverse = false }) => {
  const active = frame >= range[0] && frame <= range[1];
  if (!active) return null;

  const progress = interpolate(frame, range, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  const { x, y } = pointAtProgress(points, reverse ? 1 - progress : progress);
  const { left, top } = project(camera, x, y);

  return (
    <div
      style={{
        position: "absolute",
        left,
        top,
        transform: "translate(-50%, -50%)",
        width: 20,
        height: 20,
        borderRadius: "50%",
        background: color,
        border: "3px solid #faf6ec",
        boxShadow: "0 2px 6px rgba(0,0,0,0.25)",
      }}
    />
  );
};
