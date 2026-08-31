import React from "react";
import { interpolate } from "remotion";
import { Camera, project } from "./useCamera";
import { Waypoint } from "./geoData";
import { mapLabelStyle } from "./labelStyle";

// A summit inside the highlighted massif: a small peak glyph with its
// height under it. The name is carried by the massif caption instead, so
// it isn't printed twice.
export const PeakMarker: React.FC<{
  peak: Waypoint;
  camera: Camera;
  frame: number;
  revealFrame: number;
  labelDx?: number;
  labelDy?: number;
}> = ({ peak, camera, frame, revealFrame, labelDx = 0, labelDy = 34 }) => {
  const { left, top } = project(camera, peak.x, peak.y);

  const opacity = interpolate(frame, [revealFrame, revealFrame + 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const scale = interpolate(
    frame,
    [revealFrame, revealFrame + 9, revealFrame + 16],
    [0, 1.35, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  if (opacity <= 0) return null;

  return (
    <div style={{ position: "absolute", left, top, width: 0, height: 0, opacity }}>
      <svg
        width={44}
        height={38}
        viewBox="0 0 44 38"
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          transform: `translate(-50%, -78%) scale(${scale})`,
        }}
      >
        <path
          d="M22 3 L41 34 L3 34 Z"
          fill="#4a4132"
          stroke="#faf6ec"
          strokeWidth={3}
          strokeLinejoin="round"
        />
        <path d="M22 3 L30 16 L22 20 L14 16 Z" fill="#faf6ec" />
      </svg>
      <div
        style={{
          ...mapLabelStyle,
          position: "absolute",
          left: labelDx,
          top: labelDy,
          transform: "translate(-50%, 0)",
          fontSize: 30,
          color: "#4a4132",
          WebkitTextStroke: "7px #faf6ec",
        }}
      >
        {peak.elevation.toLocaleString("it-CH")} m
      </div>
    </div>
  );
};
