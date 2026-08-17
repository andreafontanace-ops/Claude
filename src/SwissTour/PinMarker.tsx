import React from "react";
import { interpolate, spring, useVideoConfig } from "remotion";
import { Camera, project } from "./useCamera";
import { Waypoint } from "./geoData";

export const PinMarker: React.FC<{
  waypoint: Waypoint;
  camera: Camera;
  frame: number;
  dropRange: readonly [number, number];
  labelRange: readonly [number, number];
}> = ({ waypoint, camera, frame, dropRange, labelRange }) => {
  const { fps } = useVideoConfig();
  const { left, top } = project(camera, waypoint.x, waypoint.y);

  const dropStart = dropRange[0];
  const dropDuration = dropRange[1] - dropRange[0];
  const dropFrame = frame - dropStart;

  const fallProgress = spring({
    frame: dropFrame,
    fps,
    durationInFrames: dropDuration,
    config: { damping: 9, mass: 0.6, stiffness: 120 },
  });

  const visible = frame >= dropStart;
  const dropY = interpolate(fallProgress, [0, 1], [-320, 0]);
  const landed = frame > dropStart + dropDuration * 0.55;

  const squash = interpolate(
    fallProgress,
    [0.85, 1, 1.15],
    [1, 1.35, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const squashY = interpolate(
    fallProgress,
    [0.85, 1, 1.15],
    [1, 0.72, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const ringScale = interpolate(
    frame,
    [dropStart + dropDuration * 0.5, dropStart + dropDuration * 0.5 + 22],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const ringOpacity = interpolate(
    frame,
    [dropStart + dropDuration * 0.5, dropStart + dropDuration * 0.5 + 22],
    [0.55, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const labelOpacity = interpolate(frame, labelRange, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const labelY = interpolate(frame, labelRange, [10, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  if (!visible) return null;

  // `left, top` mark the exact geo point (Nufenenpass). Everything below is
  // positioned relative to that single anchor, independently, so the pin's
  // tip and the ground ring stay glued to the real coordinate regardless of
  // how tall the label happens to be.
  return (
    <div style={{ position: "absolute", left, top, width: 0, height: 0 }}>
      {landed && (
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            width: 46,
            height: 46,
            borderRadius: "50%",
            border: "3px solid #e63946",
            transform: `translate(-50%, -50%) scale(${ringScale})`,
            opacity: ringOpacity,
          }}
        />
      )}

      <div
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          transform: `translate(-50%, -100%) translateY(${dropY}px) scaleX(${squash}) scaleY(${squashY})`,
          transformOrigin: "50% 100%",
          filter: "drop-shadow(0 6px 10px rgba(0,0,0,0.45))",
        }}
      >
        <svg width={56} height={72} viewBox="0 0 56 72">
          <path
            d="M28 2C13.6 2 2 13.6 2 28c0 19.5 26 42 26 42s26-22.5 26-42C54 13.6 42.4 2 28 2z"
            fill="#e63946"
            stroke="#fff5f0"
            strokeWidth={2}
          />
          <circle cx={28} cy={27} r={10.5} fill="#fff5f0" />
        </svg>
      </div>

      <div
        style={{
          position: "absolute",
          left: 0,
          top: 14,
          transform: `translate(-50%, 0) translateY(${labelY}px)`,
          opacity: labelOpacity,
          background: "rgba(12, 18, 32, 0.82)",
          border: "1px solid rgba(255,255,255,0.15)",
          borderRadius: 10,
          padding: "10px 18px",
          whiteSpace: "nowrap",
          textAlign: "center",
          boxShadow: "0 8px 24px rgba(0,0,0,0.35)",
        }}
      >
        <div
          style={{
            color: "#ffffff",
            fontSize: 26,
            fontWeight: 700,
            letterSpacing: 0.2,
          }}
        >
          {waypoint.name}
          {waypoint.subtitle ? (
            <span style={{ color: "#ffb199", fontWeight: 600 }}>
              {" "}
              ({waypoint.subtitle})
            </span>
          ) : null}
        </div>
        <div
          style={{
            color: "#9fb2d6",
            fontSize: 17,
            marginTop: 2,
            letterSpacing: 0.5,
          }}
        >
          {waypoint.elevation.toLocaleString("it-CH")} m s.l.m.
        </div>
      </div>
    </div>
  );
};
