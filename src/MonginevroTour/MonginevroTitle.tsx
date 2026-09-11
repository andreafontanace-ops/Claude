import React from "react";
import { interpolate, spring, useVideoConfig } from "remotion";
import { fontFamily } from "../shared/fonts";
import { mapLabelStyle } from "../shared/labelStyle";
import { INTRO_FADE_IN, TITLE_FADE_OUT } from "./timeline";

export const MonginevroTitle: React.FC<{ frame: number; top: number }> = ({
  frame,
  top,
}) => {
  const { fps } = useVideoConfig();

  const pop = spring({
    frame,
    fps,
    config: { damping: 12, mass: 0.5, stiffness: 160 },
  });
  const scale = interpolate(pop, [0, 1], [0.75, 1]);

  const fadeIn = interpolate(frame, INTRO_FADE_IN, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(frame, TITLE_FADE_OUT, [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const opacity = Math.min(fadeIn, fadeOut);

  // The arrow lands a beat after the two names, which is the whole subject of
  // the film in one gesture.
  const arrow = spring({
    frame: frame - 12,
    fps,
    config: { damping: 11, mass: 0.5, stiffness: 190 },
  });

  if (opacity <= 0) return null;

  return (
    <div
      style={{
        position: "absolute",
        top,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        gap: 26,
        opacity,
        transform: `scale(${scale})`,
        fontFamily,
      }}
    >
      <div style={{ ...mapLabelStyle, WebkitTextStroke: "14px #f7f2e6", fontSize: 108 }}>
        ITALIA
      </div>
      <div
        style={{
          ...mapLabelStyle,
          WebkitTextStroke: "14px #f7f2e6",
          fontSize: 96,
          color: "#c0392b",
          transform: `translateX(${interpolate(arrow, [0, 1], [-34, 0])}px)`,
          opacity: arrow,
        }}
      >
        &rarr;
      </div>
      <div style={{ ...mapLabelStyle, WebkitTextStroke: "14px #f7f2e6", fontSize: 108 }}>
        FRANCIA
      </div>
    </div>
  );
};
