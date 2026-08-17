import React from "react";
import { Easing, interpolate } from "remotion";
import { Camera, project } from "./useCamera";
import { pointAtProgress } from "./polyline";

export const TravelDot: React.FC<{
  points: readonly (readonly [number, number])[];
  camera: Camera;
  frame: number;
  range: readonly [number, number];
}> = ({ points, camera, frame, range }) => {
  const active = frame >= range[0] && frame <= range[1];
  if (!active) return null;

  const progress = interpolate(frame, range, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  const { x, y } = pointAtProgress(points, progress);
  const { left, top } = project(camera, x, y);

  return (
    <div
      style={{
        position: "absolute",
        left,
        top,
        transform: "translate(-50%, -50%)",
        width: 16,
        height: 16,
        borderRadius: "50%",
        background: "#fff5f0",
        boxShadow: "0 0 0 4px rgba(255,122,69,0.55), 0 0 14px 4px rgba(255,122,69,0.5)",
      }}
    />
  );
};
