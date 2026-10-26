import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  random,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { fitBoxToRect, project } from "../shared/camera";
import { countries, stages } from "./geoData";
import {
  clamp,
  DISPLAY,
  MONO,
  PLATE,
  scramble,
  SEASON_COLOR,
  SeasonId,
  slashPoly,
  slashX,
  useSeasonFonts,
  WHITE,
} from "./theme";

// Winter: the stage the viewers choose. 8s, 1080x1920, in two versions: on
// the dark Western Alps map (the three stages done, joined up, then snow and
// a giant ice-blue question mark landing as the fourth), or transparent, to
// lay over the footage. Speech bubbles start "typing" round it and a plate
// asks DOVE ANDIAMO? SCRIVILO NEI COMMENTI. Inside the safe area.
export const WINTER_QUESTION_DURATION = 240;

const ICE = SEASON_COLOR.INVERNO;
const BG = "#0e1012";
const LAND = "#1c2125";
const BORDER = "#4a545e";

const STAGES_IN = [6, 36] as const;
const TRAIL = [14, 50] as const;
const SNOW_IN = [40, 70] as const;
const DIM = [44, 74] as const;
const DROP = 62;
const BUBBLES = [128, 142, 156, 170];
const SLASH_IN = [100, 114] as const;
const STEP_IN = [108, 128] as const;
const ASK_IN = 110;
const SUB_IN = [120, 134] as const;

const KM = 111.32;
const K = Math.cos((45 * Math.PI) / 180);
const ll = (lon: number, lat: number) => ({
  x: (lon - 2.0) * K * KM,
  y: (49.5 - lat) * KM,
});
const OVERVIEW = (() => {
  const a = ll(4.6, 47.6);
  const b = ll(11.4, 43.2);
  return { x0: a.x, y0: a.y, x1: b.x, y1: b.y };
})();
const MAP_RECT = { x: 60, y: 260, w: 840, h: 840 };
const SEASON_OF: Record<string, SeasonId> = {
  verdon: "PRIMAVERA",
  novena: "ESTATE",
  staffora: "AUTUNNO",
};
const SHORT: Record<string, string> = {
  verdon: "VERDON",
  novena: "NOVENA",
  staffora: "STAFFORA",
};

// The question mark: centred over the Alps, above the plate.
const Q_X = 480;
const Q_TOP = 250;
const Q_SIZE = 900;
// Where its dot sits, for the location pulse (tuned to the glyph).
const DOT = { x: 452, y: 965 };

const P_TOP = 1170;
const P_BOTTOM = 1470;
const P_LEAN = 50;
const P_POLY = `${60 + P_LEAN},${P_TOP} 900,${P_TOP} ${900 - P_LEAN},${P_BOTTOM} 60,${P_BOTTOM}`;

const BUBBLE_SPOTS = [
  { x: 165, y: 360, flip: false },
  { x: 800, y: 470, flip: true },
  { x: 150, y: 800, flip: false },
  { x: 800, y: 900, flip: true },
];

const Bubble: React.FC<{
  x: number;
  y: number;
  flip: boolean;
  t: number;
  frame: number;
}> = ({ x, y, flip, t, frame }) => {
  if (t <= 0) return null;
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        transform: `translate(-50%, -50%) scale(${t})`,
      }}
    >
      <svg
        width={190}
        height={120}
        viewBox="0 0 190 120"
        style={{ filter: "drop-shadow(0 8px 14px rgba(0,0,0,0.45))" }}
      >
        <path
          d={
            flip
              ? "M14 4 H176 a10 10 0 0 1 10 10 V74 a10 10 0 0 1 -10 10 H64 L36 112 L42 84 H14 a10 10 0 0 1 -10 -10 V14 a10 10 0 0 1 10 -10 Z"
              : "M14 4 H176 a10 10 0 0 1 10 10 V74 a10 10 0 0 1 -10 10 H148 L154 112 L126 84 H14 a10 10 0 0 1 -10 -10 V14 a10 10 0 0 1 10 -10 Z"
          }
          fill={WHITE}
        />
        {[0, 1, 2].map((i) => (
          <circle
            key={i}
            cx={63 + i * 32}
            cy={44 - Math.max(0, Math.sin((frame - i * 4) / 4)) * 9}
            r={11}
            fill="#20262c"
          />
        ))}
      </svg>
    </div>
  );
};

export const WinterQuestion: React.FC<{ overlay: boolean }> = ({ overlay }) => {
  useSeasonFonts();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const camera = fitBoxToRect(OVERVIEW, MAP_RECT);
  const stagesIn = interpolate(frame, STAGES_IN, [0, 1], clamp);
  const trail = interpolate(frame, TRAIL, [0, 1], {
    ...clamp,
    easing: Easing.inOut(Easing.cubic),
  });
  const snow = interpolate(frame, SNOW_IN, [0, 1], clamp);
  const dim = interpolate(frame, DIM, [0, 0.45], clamp);
  const drop = spring({
    frame: frame - DROP,
    fps,
    config: { damping: 9, mass: 0.8, stiffness: 110 },
  });
  const settled = frame > DROP + 24;
  const pulse = (Math.max(0, frame - DROP - 20) % 34) / 34;
  const wobble = settled ? Math.sin((frame - DROP) / 16) * 2.5 : 0;

  const inX = slashX(frame, SLASH_IN);
  const plateClip =
    frame < SLASH_IN[1]
      ? `polygon(-200px ${P_TOP - 40}px, ${inX - 40 + 66}px ${P_TOP - 40}px, ${inX - 40}px ${P_BOTTOM + 40}px, -200px ${P_BOTTOM + 40}px)`
      : undefined;
  const ask = spring({
    frame: frame - ASK_IN,
    fps,
    config: { damping: 15, mass: 0.6, stiffness: 170 },
  });
  const subIn = interpolate(frame, SUB_IN, [0, 1], clamp);

  const pts = stages.map((s) => project(camera, s.x, s.y));
  const trailD =
    "M" + pts.map((p) => `${p.left.toFixed(1)},${p.top.toFixed(1)}`).join("L");

  return (
    <AbsoluteFill style={{ background: overlay ? undefined : BG }}>
      {!overlay && (
        <svg
          width={1080}
          height={1920}
          style={{ position: "absolute", inset: 0 }}
        >
          <g
            transform={`translate(${camera.tx} ${camera.ty}) scale(${camera.scale})`}
          >
            {countries.map((c) => (
              <path
                key={c.name}
                d={c.d}
                fill={LAND}
                stroke={BORDER}
                strokeWidth={1.6}
                vectorEffect="non-scaling-stroke"
                fillRule="evenodd"
              />
            ))}
          </g>
          {/* The journey so far: spring, summer, autumn, joined up. */}
          <path
            d={trailD}
            fill="none"
            stroke={WHITE}
            strokeOpacity={0.55}
            strokeWidth={4}
            strokeDasharray="14 12"
            strokeLinecap="round"
            style={{ clipPath: `inset(0 ${(1 - trail) * 100}% 0 0)` }}
          />
          {stages.map((s, i) => {
            const p = pts[i];
            const c = SEASON_COLOR[SEASON_OF[s.id]];
            const t = interpolate(
              frame,
              [STAGES_IN[0] + i * 8, STAGES_IN[0] + i * 8 + 10],
              [0, 1],
              clamp,
            );
            return (
              <g key={s.id} opacity={t}>
                <circle
                  cx={p.left}
                  cy={p.top}
                  r={14 * t}
                  fill={c}
                  stroke={BG}
                  strokeWidth={4}
                />
              </g>
            );
          })}
          <rect width={1080} height={1920} fill={BG} opacity={dim} />
        </svg>
      )}
      {!overlay &&
        stages.map((s, i) => {
          const p = pts[i];
          const t =
            interpolate(
              frame,
              [STAGES_IN[0] + i * 8 + 4, STAGES_IN[0] + i * 8 + 16],
              [0, 1],
              clamp,
            ) *
            (1 - dim);
          return (
            <div
              key={s.id}
              style={{
                position: "absolute",
                left: p.left + 24,
                top: p.top,
                transform: "translateY(-50%)",
                fontFamily: DISPLAY,
                fontWeight: 600,
                fontSize: 40,
                letterSpacing: 5,
                color: SEASON_COLOR[SEASON_OF[s.id]],
                opacity: t * stagesIn,
                textShadow: `0 2px 10px ${BG}`,
              }}
            >
              {SHORT[s.id]}
            </div>
          );
        })}

      {/* Snow over everything. */}
      <svg
        width={1080}
        height={1920}
        style={{ position: "absolute", inset: 0 }}
        opacity={snow}
      >
        {Array.from({ length: overlay ? 36 : 130 }, (_, i) => {
          const x = random(`qx${i}`) * 1080;
          const speed = 2.5 + random(`qs${i}`) * 4;
          const r = 2.5 + random(`qr${i}`) * 5;
          const y = ((random(`qy${i}`) * 1920 + frame * speed) % 1960) - 20;
          return (
            <circle
              key={i}
              cx={x + Math.sin(frame / 15 + i) * 10}
              cy={y}
              r={r}
              fill={WHITE}
              opacity={0.35 + random(`qo${i}`) * 0.5}
            />
          );
        })}
      </svg>

      {/* The giant question mark, landing as the fourth stage. */}
      {frame >= DROP && (
        <>
          <div
            style={{
              position: "absolute",
              left: DOT.x,
              top: DOT.y,
              width: 150,
              height: 150,
              borderRadius: "50%",
              border: `8px solid ${ICE}`,
              transform: `translate(-50%, -50%) scale(${0.4 + pulse * 1.6})`,
              opacity: settled ? 1 - pulse : 0,
            }}
          />
          <div
            style={{
              position: "absolute",
              left: Q_X,
              top: Q_TOP,
              transform: `translateX(-50%) translateY(${(1 - drop) * -1400}px) rotate(${-6 + wobble}deg)`,
              transformOrigin: "50% 90%",
              fontFamily: DISPLAY,
              fontWeight: 800,
              fontStyle: "italic",
              fontSize: Q_SIZE,
              lineHeight: 1,
              color: ICE,
              WebkitTextStroke: "18px #0b1a24",
              paintOrder: "stroke fill",
              // Over footage the glow would be a frame-wide soft alpha that
              // bloats the ProRes; the dark outline does the work there.
              textShadow: overlay
                ? "0 16px 0 rgba(11,26,36,0.6)"
                : "0 0 80px rgba(143,216,255,0.55), 0 24px 40px rgba(0,0,0,0.5)",
            }}
          >
            ?
          </div>
        </>
      )}

      {/* People already typing their suggestions. */}
      {BUBBLE_SPOTS.map((b, i) => (
        <Bubble
          key={i}
          {...b}
          frame={frame}
          t={spring({
            frame: frame - BUBBLES[i],
            fps,
            config: { damping: 11, mass: 0.5, stiffness: 160 },
          })}
        />
      ))}

      {/* The ask. */}
      {frame >= SLASH_IN[0] && (
        <AbsoluteFill style={{ clipPath: plateClip }}>
          <svg
            width={1080}
            height={1920}
            style={{ position: "absolute", inset: 0 }}
          >
            <polygon
              points={P_POLY}
              fill={PLATE}
              stroke="#2a2f34"
              strokeWidth={2}
              style={{ filter: "drop-shadow(0 14px 24px rgba(0,0,0,0.45))" }}
            />
            <polygon
              points={`${60 + P_LEAN},${P_TOP} ${60 + P_LEAN + 14},${P_TOP} 74,${P_BOTTOM} 60,${P_BOTTOM}`}
              fill={ICE}
            />
          </svg>
          <div
            style={{
              position: "absolute",
              left: 128,
              top: P_TOP + 26,
              fontFamily: MONO,
              fontWeight: 500,
              fontSize: 38,
              letterSpacing: 2,
              color: ICE,
              whiteSpace: "pre",
            }}
          >
            {scramble("TAPPA 4 · INVERNO", frame, STEP_IN)}
          </div>
          <div
            style={{
              position: "absolute",
              left: 118,
              top: P_TOP + 82,
              fontFamily: DISPLAY,
              fontWeight: 800,
              fontStyle: "italic",
              fontSize: 112,
              lineHeight: 1,
              color: WHITE,
              opacity: frame < ASK_IN ? 0 : 1,
              transform: `translateX(${(1 - ask) * -70}px)`,
            }}
          >
            DOVE ANDIAMO?
          </div>
          <div
            style={{
              position: "absolute",
              left: 124,
              top: P_TOP + 210,
              display: "flex",
              alignItems: "center",
              gap: 16,
              opacity: subIn,
              transform: `translateY(${(1 - subIn) * 12}px)`,
            }}
          >
            <svg width={52} height={46} viewBox="0 0 52 46">
              <path
                d="M6 2 H46 a4 4 0 0 1 4 4 V30 a4 4 0 0 1 -4 4 H20 L10 44 L12 34 H6 a4 4 0 0 1 -4 -4 V6 a4 4 0 0 1 4 -4 Z"
                fill={ICE}
              />
            </svg>
            <div
              style={{
                fontFamily: DISPLAY,
                fontWeight: 600,
                fontSize: 52,
                letterSpacing: 4,
                color: WHITE,
                whiteSpace: "nowrap",
              }}
            >
              SCRIVILO NEI COMMENTI
            </div>
          </div>
        </AbsoluteFill>
      )}
      {frame >= SLASH_IN[0] && frame <= SLASH_IN[1] && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: ICE,
            clipPath: slashPoly(
              inX,
              P_TOP - 30,
              P_BOTTOM + 30,
              80,
              P_LEAN / (P_BOTTOM - P_TOP),
            ),
          }}
        />
      )}
    </AbsoluteFill>
  );
};
