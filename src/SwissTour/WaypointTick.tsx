import React from "react";
import { interpolate } from "remotion";
import { Camera, project } from "./useCamera";
import { Waypoint } from "./geoData";
import { ROUTE_RED } from "./palette";
import { mapLabelStyle } from "./labelStyle";

export const WaypointTick: React.FC<{
  waypoint: Waypoint;
  camera: Camera;
  frame: number;
  revealFrame: number;
  showLabel?: boolean;
  color?: string;
  // Where the name sits relative to the marker, in screen px. Tuned per
  // waypoint so the names sit clear of the route line rather than on it.
  labelDx?: number;
  labelDy?: number;
  // Set to let a long name wrap onto two lines instead of running wide,
  // which makes it far easier to park clear of the route.
  labelWidth?: number;
}> = ({
  waypoint,
  camera,
  frame,
  revealFrame,
  showLabel = false,
  color = ROUTE_RED,
  labelDx = 0,
  labelDy = 46,
  labelWidth,
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
  // name is offset independently, so the name never drags the dot off the
  // real coordinate.
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
            ...mapLabelStyle,
            position: "absolute",
            left: labelDx,
            top: labelDy,
            transform: "translate(-50%, -50%)",
            fontSize: 40,
            ...(labelWidth
              ? { width: labelWidth, whiteSpace: "normal", textAlign: "center", lineHeight: 1.1 }
              : null),
          }}
        >
          {waypoint.name}
        </div>
      )}
    </div>
  );
};
