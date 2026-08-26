import React from "react";
import { interpolate, spring, useVideoConfig } from "remotion";
import { fontFamily } from "./fonts";
import { INTRO_FADE_IN, TITLE_FADE_OUT, TITLE_HOLD } from "./timeline";

export const TitleCard: React.FC<{ frame: number }> = ({ frame }) => {
  const { fps } = useVideoConfig();

  const pop = spring({
    frame,
    fps,
    config: { damping: 12, mass: 0.5, stiffness: 160 },
  });
  const scale = interpolate(pop, [0, 1], [0.75, 1]);

  const fadeOut = interpolate(frame, TITLE_FADE_OUT, [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const opacity = Math.min(interpolate(frame, INTRO_FADE_IN, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  }), fadeOut);

  const subOpacity = interpolate(
    frame,
    [TITLE_HOLD[0], TITLE_HOLD[0] + 8],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  if (opacity <= 0) return null;

  return (
    <div
      style={{
        position: "absolute",
        top: 110,
        left: 0,
        right: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        opacity,
        transform: `scale(${scale})`,
        fontFamily,
      }}
    >
      <div
        style={{
          fontSize: 152,
          fontWeight: 800,
          color: "#231f16",
          letterSpacing: 1,
        }}
      >
        SVIZZERA
      </div>
      <div
        style={{
          marginTop: 18,
          fontSize: 40,
          fontWeight: 700,
          color: "#c0392b",
          letterSpacing: 1.5,
          opacity: subOpacity,
          textAlign: "center",
          padding: "0 30px",
          textTransform: "uppercase",
        }}
      >
        Ticino &middot; Uri &middot; Valais
      </div>
    </div>
  );
};
