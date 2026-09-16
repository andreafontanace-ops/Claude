import React from "react";
import { interpolate, spring, useVideoConfig } from "remotion";
import { fontFamily } from "../shared/fonts";
import { mapLabelStyle } from "../shared/labelStyle";
import { INTRO_FADE_IN, TITLE_FADE_OUT } from "./timeline";

export const OltrepoTitle: React.FC<{ frame: number; top: number }> = ({
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

  if (opacity <= 0) return null;

  return (
    <div
      style={{
        position: "absolute",
        top,
        left: 0,
        right: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 10,
        opacity,
        transform: `scale(${scale})`,
        fontFamily,
      }}
    >
      <div
        style={{
          ...mapLabelStyle,
          WebkitTextStroke: "10px #f7f2e6",
          fontSize: 52,
          letterSpacing: 9,
          color: "#6b5f47",
        }}
      >
        OLTREPÒ PAVESE
      </div>
      <div
        style={{ ...mapLabelStyle, WebkitTextStroke: "14px #f7f2e6", fontSize: 84 }}
      >
        DA VARZI AL BRALLO
      </div>
    </div>
  );
};
