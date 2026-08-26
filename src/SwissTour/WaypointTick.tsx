import React from "react";
import { interpolate } from "remotion";
import { Camera, project } from "./useCamera";
import { Waypoint } from "./geoData";
import { ROUTE_RED } from "./palette";

export const WaypointTick: React.FC<{
  waypoint: Waypoint;
  camera: Camera;
  frame: number;
  revealFrame: number;
  showLabel?: boolean;
  color?: string;
  labelSide?: "above" | "below";
}> = ({
  waypoint,
  camera,
  frame,
  revealFrame,
  showLabel = false,
  color = ROUTE_RED,
  labelSide = "below",
}) => {
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

  const dotSize = showLabel ? 26 : 18;

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
          background: color,
          border: "3px solid #faf6ec",
          boxShadow: "0 2px 6px rgba(0,0,0,0.22)",
          transform: `translate(-50%, -50%) scale(${scale})`,
        }}
      />
      {showLabel && (
        <div
          style={{
            position: "absolute",
            left: 0,
            top: labelSide === "below" ? dotSize / 2 + 8 : undefined,
            bottom: labelSide === "above" ? dotSize / 2 + 8 : undefined,
            transform: "translate(-50%, 0)",
            background: "#faf6ec",
            border: "1px solid rgba(30,25,15,0.1)",
            borderRadius: 12,
            padding: "10px 20px",
            whiteSpace: "nowrap",
            textAlign: "center",
            boxShadow: "0 6px 16px rgba(40,30,15,0.16)",
          }}
        >
          <div
            style={{
              color: "#231f16",
              fontSize: 36,
              fontWeight: 800,
            }}
          >
            {waypoint.name}
          </div>
        </div>
      )}
    </div>
  );
};
