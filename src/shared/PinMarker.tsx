import React from "react";
import { interpolate, spring, useVideoConfig } from "remotion";
import { Camera, project } from "./camera";
import { Waypoint } from "./types";
import { ROUTE_RED } from "./palette";
import { mapLabelStyle } from "./labelStyle";

export const PinMarker: React.FC<{
  waypoint: Waypoint;
  camera: Camera;
  frame: number;
  dropRange: readonly [number, number];
  labelRange: readonly [number, number];
  labelDx?: number;
  labelDy?: number;
  labelSize?: number;
  // Set to let a long name wrap onto two lines instead of running wider
  // than the frame.
  labelWidth?: number;
  showElevation?: boolean;
  // it-CH prints 2'478, it-IT prints 2.478.
  elevationLocale?: string;
  // Size of the pin glyph itself. The label is sized separately so it can
  // stay readable while the marker shrinks to one of many on a wide map.
  pinScale?: number;
  // Fades the whole marker back out, for markers that hand the frame over
  // to another one.
  fadeRange?: readonly [number, number];
}> = ({
  waypoint,
  camera,
  frame,
  dropRange,
  labelRange,
  labelDx = 0,
  labelDy = 78,
  labelSize = 50,
  labelWidth,
  showElevation = false,
  elevationLocale = "it-CH",
  pinScale = 1,
  fadeRange,
}) => {
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

  const labelOpacity = interpolate(frame, labelRange, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const labelRise = interpolate(frame, labelRange, [10, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const fade = fadeRange
    ? interpolate(frame, fadeRange, [1, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 1;

  if (!visible || fade <= 0) return null;

  // `left, top` mark the exact geo point (Nufenenpass). The pin and the
  // ground ring are positioned independently off that single anchor, so the
  // pin's tip stays glued to the real coordinate.
  return (
    <div
      style={{ position: "absolute", left, top, width: 0, height: 0, opacity: fade }}
    >
      {landed && (
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            width: 68 * pinScale,
            height: 68 * pinScale,
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
          transform: `translate(-50%, -100%) translateY(${dropY * pinScale}px) scaleX(${squash}) scaleY(${squashY}) scale(${pinScale})`,
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
          ...mapLabelStyle,
          position: "absolute",
          left: labelDx,
          top: labelDy,
          transform: `translate(-50%, 0) translateY(${labelRise}px)`,
          opacity: labelOpacity,
          textAlign: "center",
          fontSize: labelSize,
          lineHeight: 1.1,
          ...(labelWidth ? { width: labelWidth, whiteSpace: "normal" } : null),
        }}
      >
        <div>{waypoint.name}</div>
        {waypoint.subtitle ? (
          <div style={{ color: ROUTE_RED, fontSize: labelSize * 0.84 }}>
            ({waypoint.subtitle})
          </div>
        ) : null}
        {showElevation ? (
          <div style={{ color: "#6b5f47", fontSize: labelSize * 0.66 }}>
            {waypoint.elevation.toLocaleString(elevationLocale)} m
          </div>
        ) : null}
      </div>
    </div>
  );
};
