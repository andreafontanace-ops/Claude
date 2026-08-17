import React from "react";
import { interpolate } from "remotion";
import { Camera, project } from "./useCamera";
import { Waypoint } from "./geoData";

export const WaypointTick: React.FC<{
  waypoint: Waypoint;
  camera: Camera;
  frame: number;
  revealFrame: number;
  showLabel?: boolean;
}> = ({ waypoint, camera, frame, revealFrame, showLabel = false }) => {
  const { left, top } = project(camera, waypoint.x, waypoint.y);

  const opacity = interpolate(frame, [revealFrame, revealFrame + 16], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const scale = interpolate(
    frame,
    [revealFrame, revealFrame + 10, revealFrame + 18],
    [0, 1.4, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  if (opacity <= 0) return null;

  const dotSize = showLabel ? 16 : 11;

  // `left, top` mark the exact geo point. The dot is centered on it and the
  // label (if any) is positioned independently below, so a tall label never
  // pulls the dot off the real coordinate.
  return (
    <div style={{ position: "absolute", left, top, width: 0, height: 0, opacity }}>
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          width: dotSize,
          height: dotSize,
          borderRadius: "50%",
          background: "#ffb199",
          border: "2.5px solid #fff5f0",
          boxShadow: "0 0 0 4px rgba(255,122,69,0.28)",
          transform: `translate(-50%, -50%) scale(${scale})`,
        }}
      />
      {showLabel && (
        <div
          style={{
            position: "absolute",
            left: 0,
            top: dotSize / 2 + 8,
            transform: "translate(-50%, 0)",
            background: "rgba(12, 18, 32, 0.78)",
            border: "1px solid rgba(255,255,255,0.13)",
            borderRadius: 8,
            padding: "5px 12px",
            whiteSpace: "nowrap",
            textAlign: "center",
          }}
        >
          <div style={{ color: "#fff", fontSize: 19, fontWeight: 700 }}>
            {waypoint.name}
          </div>
          <div style={{ color: "#9fb2d6", fontSize: 13, marginTop: 1 }}>
            {waypoint.elevation.toLocaleString("it-CH")} m
          </div>
        </div>
      )}
    </div>
  );
};
