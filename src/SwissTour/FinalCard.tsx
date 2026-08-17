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

  const stops = [
    { label: "Airolo" },
    { label: "Passo del San Gottardo" },
    { label: "Furka" },
    { label: "Nufenenpass", highlight: true },
  ];

  return (
    <div
      style={{
        position: "absolute",
        bottom: 96,
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
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        {stops.map((stop, i) => (
          <React.Fragment key={stop.label}>
            {i > 0 && (
              <div style={{ color: "#ff9d6f", fontSize: 20, lineHeight: "20px" }}>
                ↓
              </div>
            )}
            <div
              style={{
                fontSize: 30,
                fontWeight: 700,
                color: stop.highlight ? "#ffb199" : "#ffffff",
                letterSpacing: 0.5,
                textAlign: "center",
              }}
            >
              {stop.label}
            </div>
          </React.Fragment>
        ))}
      </div>
      <div
        style={{
          marginTop: 16,
          fontSize: 19,
          fontWeight: 500,
          color: "#9fb2d6",
          letterSpacing: 1.5,
          textAlign: "center",
          padding: "0 40px",
        }}
      >
        PASSO DELLA NOVENA · 2 478 M S.L.M.
      </div>
    </div>
  );
};
