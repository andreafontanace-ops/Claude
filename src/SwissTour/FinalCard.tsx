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
              <div style={{ color: "#c0392b", fontSize: 30, lineHeight: "26px" }}>
                ↓
              </div>
            )}
            <div
              style={{
                fontSize: 46,
                fontWeight: 800,
                textTransform: "uppercase",
                color: stop.highlight ? "#c0392b" : "#231f16",
                letterSpacing: 0.3,
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
          marginTop: 20,
          fontSize: 27,
          fontWeight: 700,
          color: "#8a7a52",
          letterSpacing: 1,
          textAlign: "center",
          padding: "0 40px",
          textTransform: "uppercase",
        }}
      >
        Passo della Novena &middot; 2 478 m s.l.m.
      </div>
    </div>
  );
};
