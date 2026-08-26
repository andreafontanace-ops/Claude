import React from "react";
import { interpolate } from "remotion";
import { fontFamily } from "./fonts";
import { ROUTE_BLUE, ROUTE_RED } from "./palette";
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

  // The ride is a loop, so it opens and closes on Airolo.
  const stops = [
    { label: "Airolo", color: ROUTE_BLUE },
    { label: "Passo del San Gottardo", color: ROUTE_BLUE },
    { label: "Furka", color: ROUTE_BLUE },
    { label: "Nufenenpass", color: ROUTE_RED },
    { label: "Airolo", color: ROUTE_RED },
  ];

  return (
    <div
      style={{
        position: "absolute",
        bottom: 90,
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
          <React.Fragment key={`${stop.label}-${i}`}>
            {i > 0 && (
              <div
                style={{
                  color: stops[i].color,
                  fontSize: 30,
                  lineHeight: "24px",
                }}
              >
                ↓
              </div>
            )}
            <div
              style={{
                fontSize: 52,
                fontWeight: 800,
                textTransform: "uppercase",
                color: stop.color,
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
          marginTop: 22,
          fontSize: 33,
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
