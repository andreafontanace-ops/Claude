import React, { useEffect, useState } from "react";
import {
  continueRender,
  delayRender,
  Easing,
  interpolate,
  staticFile,
} from "remotion";

// "4 stagioni, 4 tappe": the look shared by the season cards, the maps and
// the winter call to follow. The ADVENTOURING moto title's language - dark
// plates, condensed italic type, orange slashes - with each season wearing
// its own colour.

export type SeasonId = "PRIMAVERA" | "ESTATE" | "AUTUNNO" | "INVERNO";

export const SEASON_COLOR: Record<SeasonId, string> = {
  PRIMAVERA: "#7bd389",
  ESTATE: "#ffb627",
  AUTUNNO: "#e8692c",
  INVERNO: "#8fd8ff",
};

export const DISPLAY = "Barlow Condensed";
export const MONO = "JetBrains Mono";
export const PLATE = "#141414";
export const WHITE = "#ffffff";
export const clamp = {
  extrapolateLeft: "clamp",
  extrapolateRight: "clamp",
} as const;

export const useSeasonFonts = () => {
  const [handle] = useState(() => delayRender("Loading season fonts"));
  useEffect(() => {
    const faces = [
      new FontFace(
        DISPLAY,
        `url(${staticFile("fonts/barlow-condensed-latin-800-italic.woff2")})`,
        {
          weight: "800",
          style: "italic",
        },
      ),
      new FontFace(
        DISPLAY,
        `url(${staticFile("fonts/barlow-condensed-latin-600-normal.woff2")})`,
        {
          weight: "600",
        },
      ),
      new FontFace(
        MONO,
        `url(${staticFile("fonts/jetbrains-mono-latin-500-normal.woff2")})`,
        {
          weight: "500",
        },
      ),
    ];
    Promise.all(faces.map((f) => f.load()))
      .then((loaded) => {
        loaded.forEach((f) => document.fonts.add(f));
        continueRender(handle);
      })
      .catch((err) => {
        console.error(err);
        continueRender(handle);
      });
  }, [handle]);
};

// A deterministic scramble: each character cycles and settles on its own
// frame, left to right - a GPS readout finding its fix.
const GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
export const scramble = (
  text: string,
  frame: number,
  range: readonly [number, number],
) => {
  const span = range[1] - range[0];
  return text
    .split("")
    .map((ch, i) => {
      if (ch === " " || "°′″·.,/?".includes(ch))
        return frame >= range[0] ? ch : " ";
      const settle = range[0] + (span * (i + 1)) / text.length;
      if (frame >= settle) return ch;
      if (frame < range[0] + (span * i) / text.length / 2) return " ";
      const pool = /[0-9]/.test(ch) ? "0123456789" : GLYPHS;
      return pool[(i * 7 + frame * 13) % pool.length];
    })
    .join("");
};

// A slanted bar crossing the frame left to right; returns its leading edge.
export const slashX = (frame: number, range: readonly [number, number]) =>
  interpolate(frame, range, [-220, 1300], {
    ...clamp,
    easing: Easing.inOut(Easing.cubic),
  });

// The bar itself, leaning like the plates, between `top` and `bottom`.
export const slashPoly = (
  x: number,
  top: number,
  bottom: number,
  w: number,
  leanPerPx: number,
) => {
  const lean = (bottom - top) * leanPerPx;
  return `polygon(${x - w}px ${bottom}px, ${x - w + lean}px ${top}px, ${x + lean}px ${top}px, ${x}px ${bottom}px)`;
};

// The four season glyphs, 100 x 100, in the season's colour. `t` runs 0..1
// as the glyph arrives (petals open, rays grow, the leaf swings in, the
// flake turns); `spin` keeps them alive afterwards.
export const SeasonIcon: React.FC<{
  season: SeasonId;
  size: number;
  t: number;
  spin: number;
}> = ({ season, size, t, spin }) => {
  const c = SEASON_COLOR[season];
  const e = Easing.out(Easing.back(1.6))(Math.max(0, Math.min(1, t)));
  return (
    <svg width={size} height={size} viewBox="0 0 100 100">
      {season === "PRIMAVERA" && (
        <g transform={`translate(50 50) rotate(${spin * 20})`}>
          {[0, 72, 144, 216, 288].map((a) => (
            <ellipse
              key={a}
              cx={0}
              cy={-22 * e}
              rx={13 * e}
              ry={22 * e}
              fill={c}
              transform={`rotate(${a})`}
              opacity={0.95}
            />
          ))}
          <circle r={11 * e} fill={WHITE} />
        </g>
      )}
      {season === "ESTATE" && (
        <g transform={`translate(50 50) rotate(${spin * 30})`}>
          {Array.from({ length: 10 }, (_, i) => i * 36).map((a) => (
            <line
              key={a}
              x1={0}
              y1={-26}
              x2={0}
              y2={-26 - 18 * e}
              stroke={c}
              strokeWidth={7}
              strokeLinecap="round"
              transform={`rotate(${a})`}
            />
          ))}
          <circle r={19 * e} fill={c} />
        </g>
      )}
      {season === "AUTUNNO" && (
        <g
          transform={`translate(50 54) rotate(${-30 * (1 - e) + Math.sin(spin * 4) * 8}) scale(${e})`}
        >
          <path
            d="M0 -40 C 26 -26 30 6 0 34 C -30 6 -26 -26 0 -40 Z"
            fill={c}
          />
          <path
            d="M0 -32 L0 44 M0 -8 L14 -18 M0 6 L-15 -6 M0 18 L13 8"
            stroke="#141414"
            strokeWidth={4}
            strokeLinecap="round"
            fill="none"
          />
        </g>
      )}
      {season === "INVERNO" && (
        <g
          transform={`translate(50 50) rotate(${spin * 40 + 60 * (1 - e)}) scale(${e})`}
          stroke={c}
          strokeWidth={6}
          strokeLinecap="round"
          fill="none"
        >
          {[0, 60, 120, 180, 240, 300].map((a) => (
            <g key={a} transform={`rotate(${a})`}>
              <line x1={0} y1={0} x2={0} y2={-40} />
              <line x1={0} y1={-24} x2={-11} y2={-34} />
              <line x1={0} y1={-24} x2={11} y2={-34} />
            </g>
          ))}
        </g>
      )}
    </svg>
  );
};
