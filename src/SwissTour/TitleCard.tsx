import React from "react";
import { interpolate } from "remotion";
import { fontFamily } from "./fonts";
import {
  INTRO_FADE_IN,
  TITLE_FADE_OUT,
  TITLE_HOLD,
} from "./timeline";

export const TitleCard: React.FC<{ frame: number }> = ({ frame }) => {
  const fadeIn = interpolate(frame, INTRO_FADE_IN, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(frame, TITLE_FADE_OUT, [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const opacity = Math.min(fadeIn, fadeOut);
  const rise = interpolate(frame, INTRO_FADE_IN, [24, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const subOpacity = interpolate(
    frame,
    [TITLE_HOLD[0], TITLE_HOLD[0] + 10],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  if (opacity <= 0) return null;

  return (
    <div
      style={{
        position: "absolute",
        top: 100,
        left: 0,
        right: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        opacity,
        transform: `translateY(${rise}px)`,
        fontFamily,
      }}
    >
      <div
        style={{
          fontSize: 128,
          fontWeight: 800,
          color: "#ffffff",
          letterSpacing: 4,
          textShadow: "0 8px 30px rgba(0,0,0,0.5)",
        }}
      >
        SVIZZERA
      </div>
      <div
        style={{
          marginTop: 18,
          fontSize: 34,
          fontWeight: 600,
          color: "#a9c1ec",
          letterSpacing: 2,
          opacity: subOpacity,
          textAlign: "center",
          padding: "0 40px",
        }}
      >
        ALPI LEPONTINE · TICINO · URI · VALAIS
      </div>
    </div>
  );
};
