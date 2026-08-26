import React from "react";
import { interpolate, spring, useVideoConfig } from "remotion";
import { Camera, project } from "./useCamera";
import { Waypoint } from "./geoData";
import { ROUTE_RED } from "./palette";

export const PinMarker: React.FC<{
  waypoint: Waypoint;
  camera: Camera;
  frame: number;
  dropRange: readonly [number, number];
  labelRange: readonly [number, number];
  labelHideRange?: readonly [number, number];
}> = ({ waypoint, camera, frame, dropRange, labelRange, labelHideRange }) => {
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

  // Impact squash, keyed off the frame rather than off `fallProgress`: the
  // spring settles at exactly 1, so driving the squash from its value left
  // the landed pin permanently flattened instead of springing back.
  const impact = dropStart + dropDuration * 0.72;
  const squashKeys = [impact, impact + 5, impact + 15] as const;
  const squash = interpolate(frame, squashKeys, [1, 1.24, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const squashY = interpolate(frame, squashKeys, [1, 0.8, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

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

  // The label is a wide box; once the final route card slides in below it
  // they would collide, so it fades back out on the way there.
  const labelHide = labelHideRange
    ? interpolate(frame, labelHideRange, [1, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 1;

  const labelOpacity =
    interpolate(frame, labelRange, [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }) * labelHide;
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
            width: 68,
            height: 68,
            borderRadius: "50%",
            border: "4px solid #e63946",
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
        <svg width={84} height={108} viewBox="0 0 56 72">
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
          background: "#faf6ec",
          border: "1px solid rgba(30,25,15,0.1)",
          borderRadius: 16,
          padding: "18px 28px",
          maxWidth: 900,
          textAlign: "center",
          boxShadow: "0 8px 20px rgba(40,30,15,0.18)",
        }}
      >
        <div
          style={{
            color: "#231f16",
            fontSize: 48,
            fontWeight: 800,
            letterSpacing: 0.1,
            lineHeight: 1.15,
          }}
        >
          {waypoint.name}
          {waypoint.subtitle ? (
            <span style={{ color: ROUTE_RED, fontWeight: 700 }}>
              {" "}
              ({waypoint.subtitle})
            </span>
          ) : null}
        </div>
        <div
          style={{
            color: "#8a7a52",
            fontSize: 29,
            fontWeight: 700,
            marginTop: 6,
            letterSpacing: 0.5,
            textTransform: "uppercase",
          }}
        >
          {waypoint.elevation.toLocaleString("it-CH")} m s.l.m.
        </div>
      </div>
    </div>
  );
};
