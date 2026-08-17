import React from "react";
import { interpolate } from "remotion";
import { fontFamily } from "./fonts";
import { FINAL_CARD, OUTRO_FADE } from "./timeline";

export const FinalCard: React.FC<{ frame: number }> = ({ frame }) => {
  const opacity = interpolate(frame, FINAL_CARD, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const rise = interpolate(frame, FINAL_CARD, [16, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const globalFade = interpolate(frame, OUTRO_FADE, [1, 0.92], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  if (opacity <= 0) return null;

  return (
    <div
      style={{
        position: "absolute",
        bottom: 86,
        left: 0,
        right: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        opacity: opacity * globalFade,
        transform: `translateY(${rise}px)`,
        fontFamily,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 14,
          fontSize: 30,
          fontWeight: 700,
          color: "#ffffff",
          letterSpacing: 1,
        }}
      >
        <span>Airolo</span>
        <span style={{ color: "#ff9d6f" }}>→</span>
        <span>Passo del San Gottardo</span>
        <span style={{ color: "#ff9d6f" }}>→</span>
        <span>Furka</span>
        <span style={{ color: "#ff9d6f" }}>→</span>
        <span style={{ color: "#ffb199" }}>Nufenenpass</span>
      </div>
      <div
        style={{
          marginTop: 10,
          fontSize: 20,
          fontWeight: 500,
          color: "#9fb2d6",
          letterSpacing: 2,
        }}
      >
        PASSO DELLA NOVENA · 2 478 M S.L.M.
      </div>
    </div>
  );
};
