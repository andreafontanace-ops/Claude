import React from "react";
import { interpolate } from "remotion";
import { Camera, project } from "./camera";
import { mapLabelStyle } from "./labelStyle";

// A name with no marker under it: a region, or the valley itself. Anchored in
// map units so it travels with the camera, but set in screen pixels so it
// keeps its size while the camera drops.
export const MapName: React.FC<{
  camera: Camera;
  frame: number;
  x: number;
  y: number;
  lines: string[];
  revealFrame: number;
  revealFrames?: number;
  fadeRange?: readonly [number, number];
  width?: number;
  size?: number;
}> = ({
  camera,
  frame,
  x,
  y,
  lines,
  revealFrame,
  revealFrames = 18,
  fadeRange,
  width = 300,
  size = 40,
}) => {
  const { left, top } = project(camera, x, y);

  const reveal = interpolate(
    frame,
    [revealFrame, revealFrame + revealFrames],
    [0, 1],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    },
  );
  const fade = fadeRange
    ? interpolate(frame, fadeRange, [1, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 1;
  const opacity = Math.min(reveal, fade);
  if (opacity <= 0) return null;

  return (
    <div
      style={{
        ...mapLabelStyle,
        position: "absolute",
        left,
        top,
        width,
        opacity,
        transform: "translate(-50%, -50%)",
        textAlign: "center",
        whiteSpace: "normal",
        lineHeight: 1.15,
        color: "#4a4033",
        fontSize: size,
        letterSpacing: 3,
      }}
    >
      {lines.map((line) => (
        <div key={line}>{line}</div>
      ))}
    </div>
  );
};
