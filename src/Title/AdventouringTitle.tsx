import React, { useEffect, useState } from "react";
import {
  AbsoluteFill,
  continueRender,
  delayRender,
  Easing,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { pointAtProgress, smoothPath, subPolyline } from "../shared/polyline";
import { ROUTE_RED } from "../shared/palette";
import { SAFE_RECT } from "../shared/safeArea";
import { LOMBARDIA, OLTREPO, VARZI, VIEW } from "./titleShapes";

// The series title, laid over the rider's own footage: a transparent
// 1080x1920 clip, 4s. A map cartouche - the cream, ink and road red of the
// map films - unfolds; Lombardia draws itself and its south, the Oltrepò,
// turns red with a beacon on Varzi; ADVENTOURING rises letter by letter over
// "nel sud della Lombardia"; an adventure bike rides in underneath, laying
// the red road down behind it. Then the card folds away and the footage is
// clean. Centred in SAFE_RECT, clear of every platform's buttons.
export const TITLE_DURATION = 120; // 4s @30fps

const SERIF = "Zilla Slab";
const INK = "#231f16";
const PAPER = "#faf6ec";
const LOMB_FILL = "#e3cf7a"; // Lombardia, as on the maps
const BROWN = "#6b5f47";

const CARD_IN = [0, 16] as const;
const MAP_DRAW = [8, 40] as const;
const MAP_FILL = [30, 44] as const;
const SOUTH_IN = [40, 52] as const;
const TITLE_START = 18;
const LETTER_STEP = 2;
const SUB_IN = [38, 54] as const;
const RIDE = [40, 90] as const;
const CARD_OUT = [102, 117] as const;

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const ease = Easing.bezier(0.33, 0, 0.2, 1);

const CARD_W = 760;
const ROAD_W = 640;
const ROAD_H = 140;
const BIKE_SCALE = 0.78;

// The road the bike rides: gentle bends, sampled as points so the bike can
// sit on it and the drawn part can be cut out of it frame by frame.
const ROAD: [number, number][] = Array.from({ length: 81 }, (_, i) => {
  const x = (i / 80) * ROAD_W;
  return [x, 100 + 12 * Math.sin(x / 62) + 6 * Math.sin(x / 27 + 1)];
});

// An adventure bike, side on, facing right: tall front with a beak and a
// screen, panniers and a top box, a rider. Wheels are drawn separately so
// they can turn. Ground (the wheels' bottoms) is y = 124.
const WHEELS = {
  rear: { x: 45, y: 100, r: 24 },
  front: { x: 160, y: 98, r: 26 },
};
const BikeBody: React.FC = () => (
  <g fill={INK} stroke={PAPER} strokeWidth={3} strokeLinejoin="round">
    {/* swingarm and engine */}
    <path d="M45 97 L96 90 L98 98 L45 104 Z" />
    <path d="M80 82 L118 82 L126 104 L92 110 L78 98 Z" />
    {/* frame, tail, seat, tank */}
    <path d="M76 66 L122 66 L122 86 L80 86 Z" />
    <path d="M30 64 L72 60 L78 70 L34 74 Z" />
    <path d="M52 56 L98 54 L102 62 L56 66 Z" />
    <path d="M94 58 L104 44 L130 44 L137 58 L121 68 L98 66 Z" />
    {/* top box and pannier */}
    <rect x={14} y={44} width={32} height={20} rx={4} />
    <rect x={22} y={68} width={44} height={28} rx={5} />
    {/* fork, front fender, beak, fairing, screen */}
    <path d="M157 98 L163 96 L144 44 L138 46 Z" />
    <path d="M148 70 L178 76 L172 82 L146 77 Z" />
    <path d="M136 56 L168 62 L146 67 Z" />
    <path d="M128 44 L146 34 L157 48 L150 60 L132 58 Z" />
    <path d="M144 36 L137 16 L144 14 L155 34 Z" />
    {/* rider: helmet, torso, arm, leg, boot */}
    <circle cx={104} cy={16} r={12} />
    <path d="M90 30 L112 28 L117 52 L98 60 L84 58 Z" />
    <path d="M108 34 L138 42 L136 48 L106 42 Z" />
    <path d="M86 56 L110 56 L120 72 L110 78 L98 66 Z" />
    <path d="M110 72 L120 72 L126 98 L116 100 Z" />
    <path d="M112 96 L132 96 L132 102 L112 102 Z" />
  </g>
);

const Wheel: React.FC<{ x: number; y: number; r: number; turn: number }> = ({
  x,
  y,
  r,
  turn,
}) => (
  <g transform={`translate(${x} ${y}) rotate(${turn})`}>
    <circle r={r} fill="none" stroke={PAPER} strokeWidth={13} />
    <circle r={r} fill="none" stroke={INK} strokeWidth={8} />
    {[0, 60, 120].map((a) => (
      <line
        key={a}
        x1={-r * 0.7 * Math.cos((a * Math.PI) / 180)}
        y1={-r * 0.7 * Math.sin((a * Math.PI) / 180)}
        x2={r * 0.7 * Math.cos((a * Math.PI) / 180)}
        y2={r * 0.7 * Math.sin((a * Math.PI) / 180)}
        stroke={INK}
        strokeWidth={3}
      />
    ))}
    <circle r={5} fill={INK} />
  </g>
);

const useFonts = () => {
  const [handle] = useState(() => delayRender("Loading Zilla Slab"));
  useEffect(() => {
    const faces = [
      new FontFace(
        SERIF,
        `url(${staticFile("fonts/zilla-slab-latin-700-normal.woff2")})`,
        {
          weight: "700",
        },
      ),
      new FontFace(
        SERIF,
        `url(${staticFile("fonts/zilla-slab-latin-500-italic.woff2")})`,
        {
          weight: "500",
          style: "italic",
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

export const AdventouringTitle: React.FC = () => {
  useFonts();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // The card unfolds from its middle like a map, and folds back the same way.
  const open =
    interpolate(frame, CARD_IN, [0, 1], { ...clamp, easing: ease }) -
    interpolate(frame, CARD_OUT, [0, 1], {
      ...clamp,
      easing: Easing.in(Easing.cubic),
    });
  if (open <= 0) return <AbsoluteFill />;
  const inset = (1 - open) * 50;

  const draw = interpolate(frame, MAP_DRAW, [0, 1], { ...clamp, easing: ease });
  const fill = interpolate(frame, MAP_FILL, [0, 1], clamp);
  const south = interpolate(frame, SOUTH_IN, [0, 1], clamp);
  const beat = (Math.max(0, frame - SOUTH_IN[0]) % 30) / 30;

  const sub = interpolate(frame, SUB_IN, [0, 100], { ...clamp, easing: ease });

  const ride = interpolate(frame, RIDE, [0, 1], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  const at = 0.06 + 0.82 * ride;
  const pos = pointAtProgress(ROAD, at);
  const ahead = pointAtProgress(ROAD, Math.min(1, at + 0.01));
  // Follows the road's lean, but only a little: an icon, not a crash.
  const tilt = Math.max(
    -6,
    Math.min(6, (Math.atan2(ahead.y - pos.y, ahead.x - pos.x) * 180) / Math.PI),
  );
  const travelled = at * ROAD_W * 1.05;
  const bounce = ride < 1 ? Math.sin(frame * 1.7) * 1.2 : 0;
  const bikeIn = interpolate(frame, [RIDE[0], RIDE[0] + 6], [0, 1], clamp);

  const word = "ADVENTOURING";

  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: SAFE_RECT.x + (SAFE_RECT.w - CARD_W) / 2,
          top: 600,
          width: CARD_W,
          clipPath: `inset(${inset}% -40px ${inset}% -40px)`,
        }}
      >
        <div
          style={{
            background: PAPER,
            border: `3px solid ${INK}`,
            borderRadius: 6,
            boxShadow: "0 18px 40px rgba(0,0,0,0.35)",
            padding: 10,
          }}
        >
          <div
            style={{
              border: `1.5px solid ${INK}`,
              borderRadius: 3,
              padding: "26px 30px 18px",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
            }}
          >
            {/* Lombardia, drawing itself; its south in road red. */}
            <svg width={230} height={230} viewBox={`0 0 ${VIEW} ${VIEW}`}>
              <path
                d={LOMBARDIA}
                fill={LOMB_FILL}
                fillOpacity={fill}
                stroke="none"
              />
              <path
                d={OLTREPO}
                fill={ROUTE_RED}
                fillOpacity={0.85 * south}
                stroke={ROUTE_RED}
                strokeWidth={3}
                strokeOpacity={south}
                strokeLinejoin="round"
              />
              <path
                d={LOMBARDIA}
                fill="none"
                stroke={INK}
                strokeWidth={4}
                strokeLinejoin="round"
                // Overshoot the dash so the outline closes for sure - a long
                // path measures a little short against its own dash.
                pathLength={1}
                strokeDasharray={draw >= 1 ? undefined : "1.06 1.06"}
                strokeDashoffset={draw >= 1 ? undefined : 1.06 * (1 - draw)}
              />
              {south > 0 && (
                <g opacity={south}>
                  <circle
                    cx={VARZI.x}
                    cy={VARZI.y}
                    r={10 + 34 * beat}
                    fill="none"
                    stroke={ROUTE_RED}
                    strokeWidth={4}
                    opacity={1 - beat}
                  />
                  <circle
                    cx={VARZI.x}
                    cy={VARZI.y}
                    r={9}
                    fill={PAPER}
                    stroke={INK}
                    strokeWidth={4}
                  />
                </g>
              )}
            </svg>

            {/* ADVENTOURING, each letter rising out of a slot. */}
            <div
              style={{
                display: "flex",
                marginTop: 14,
                overflow: "hidden",
                paddingBottom: 4,
                fontFamily: SERIF,
                fontWeight: 700,
                fontSize: 76,
                lineHeight: 1,
                letterSpacing: 4,
                color: INK,
              }}
            >
              {word.split("").map((ch, i) => {
                const start = TITLE_START + i * LETTER_STEP;
                const s = spring({
                  frame: frame - start,
                  fps,
                  config: { damping: 14, mass: 0.6, stiffness: 160 },
                });
                return (
                  <span
                    key={i}
                    style={{
                      display: "inline-block",
                      transform: `translateY(${(1 - s) * 100}%)`,
                      opacity: frame < start ? 0 : 1,
                      // ADVEN + TOURING: the touring half in road red.
                      color: i >= 5 ? ROUTE_RED : INK,
                    }}
                  >
                    {ch}
                  </span>
                );
              })}
            </div>

            <div
              style={{
                fontFamily: SERIF,
                fontWeight: 500,
                fontStyle: "italic",
                fontSize: 44,
                lineHeight: 1.1,
                color: BROWN,
                marginTop: 6,
                clipPath: `inset(-10% ${100 - sub}% -10% 0)`,
              }}
            >
              nel sud della Lombardia
            </div>

            {/* The road and the bike laying it down. */}
            <svg
              width={ROAD_W}
              height={ROAD_H}
              style={{ marginTop: 4, overflow: "visible" }}
            >
              <path
                d={smoothPath(ROAD)}
                fill="none"
                stroke={INK}
                strokeOpacity={0.18}
                strokeWidth={3}
                strokeDasharray="2 8"
                strokeLinecap="round"
              />
              {at > 0.06 && (
                <path
                  d={smoothPath(subPolyline(ROAD, 0, at))}
                  fill="none"
                  stroke={ROUTE_RED}
                  strokeWidth={9}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              )}
              <g
                opacity={bikeIn}
                transform={`translate(${pos.x} ${pos.y + bounce}) rotate(${tilt}) scale(${BIKE_SCALE}) translate(-102 -124)`}
              >
                <Wheel
                  {...WHEELS.rear}
                  turn={((travelled / WHEELS.rear.r) * 57.3) / BIKE_SCALE}
                />
                <Wheel
                  {...WHEELS.front}
                  turn={((travelled / WHEELS.front.r) * 57.3) / BIKE_SCALE}
                />
                <BikeBody />
              </g>
            </svg>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
