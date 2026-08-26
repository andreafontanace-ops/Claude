import React from "react";
import { interpolate, spring, useVideoConfig } from "remotion";
import { Camera, project } from "./useCamera";
import { Waypoint } from "./geoData";

export const PinMarker: React.FC<{
  waypoint: Waypoint;
  camera: Camera;
  frame: number;
  dropRange: readonly [number, number];
}> = ({ waypoint, camera, frame, dropRange }) => {
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

  if (!visible) return null;

  // `left, top` mark the exact geo point (Nufenenpass). The pin and the
  // ground ring are positioned independently off that single anchor, so the
  // pin's tip stays glued to the real coordinate.
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
    </div>
  );
};
