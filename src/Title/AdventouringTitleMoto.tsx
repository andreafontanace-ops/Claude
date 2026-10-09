import React, { useEffect, useState } from "react";
import {
  AbsoluteFill,
  continueRender,
  delayRender,
  Easing,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { SAFE_RECT } from "../shared/safeArea";
import { LOMBARDIA, OLTREPO, VARZI as VARZI_MINI, VIEW } from "./titleShapes";
import { contours, TOPO_SIZE } from "./topo";

// The series title in a riding-film look: a transparent 1080x1920 clip, 4s.
// Real contour lines of the Oltrepò's mountains draw themselves behind; an
// orange slash sweeps across and leaves ADVENTOURING in its wake; a GPS
// readout and a mini Lombardia tick in above; the subtitle decodes; a bike
// rides in laying the road down; then a second slash wipes it all away.
// Centred in SAFE_RECT, clear of every platform's buttons.
export const TITLE_MOTO_DURATION = 120; // 4s @30fps

const DISPLAY = "Barlow Condensed";
const MONO = "JetBrains Mono";
const WHITE = "#ffffff";
const ORANGE = "#ff5a1f";

const TOPO_IN = [0, 30] as const;
const SCRIM_IN = [0, 10] as const;
const SLASH_IN = [6, 22] as const;
const HUD_IN = [16, 28] as const;
const COORDS = [20, 44] as const;
const SUB = [24, 46] as const;
const RIDE = [34, 82] as const;
const SLASH_OUT = [100, 116] as const;

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const ease = Easing.bezier(0.33, 0, 0.2, 1);

const CX = SAFE_RECT.x + SAFE_RECT.w / 2; // 480
const HUD_TOP = 690;
const TITLE_TOP = 790;
const TITLE_H = 150;
const SUB_TOP = 955;
const ROAD_Y = 1118;
const ROAD_X0 = CX - 380;
const ROAD_X1 = CX + 380;
const TOPO_PX = 940;

// A deterministic scramble: each character cycles through look-alikes and
// settles on its own frame, left to right.
const GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
const scramble = (
  text: string,
  frame: number,
  range: readonly [number, number],
) => {
  const span = range[1] - range[0];
  return text
    .split("")
    .map((ch, i) => {
      if (ch === " " || "°′″·.".includes(ch))
        return frame >= range[0] ? ch : " ";
      const settle = range[0] + (span * (i + 1)) / text.length;
      if (frame >= settle) return ch;
      if (frame < range[0] + (span * i) / text.length / 2) return " ";
      const pool = /[0-9]/.test(ch) ? "0123456789" : GLYPHS;
      return pool[(i * 7 + frame * 13) % pool.length];
    })
    .join("");
};

// An adventure bike in silhouette, side on, facing right: top box, side
// case, tall tank, beak and screen, rider leaning in. 200 x 120, ground at
// y = 118; the wheels are separate so they can turn.
const WHEELS = [
  { x: 40, y: 90, r: 28 },
  { x: 160, y: 88, r: 30 },
];
const BikeBody: React.FC = () => (
  <g fill={WHITE}>
    <rect x={4} y={32} width={36} height={26} rx={6} />
    <rect x={14} y={58} width={46} height={30} rx={6} />
    <path d="M36 56 C60 49 82 49 102 52 L106 61 L40 65 Z" />
    <path d="M96 51 C104 38 124 35 137 43 L141 58 L100 65 Z" />
    <path d="M76 64 L128 61 L133 84 C121 97 92 99 79 89 Z" />
    <path d="M38 87 L96 80 L99 89 L41 96 Z" />
    <path d="M131 45 L139 40 L166 86 L158 91 Z" />
    <path d="M128 40 C136 29 151 27 159 35 L161 51 L137 55 Z" />
    <path d="M146 31 L139 8 L148 6 L161 30 Z" />
    <path d="M141 56 C155 52 171 55 182 64 L148 70 Z" />
    <circle cx={110} cy={9} r={11} />
    <path d="M96 19 C108 16 118 20 121 28 L117 52 L96 56 C91 44 91 30 96 19 Z" />
    <path d="M112 24 L135 32 L133 38 L110 32 Z" />
    <path d="M95 50 L117 52 L126 66 L113 71 Z" />
    <path d="M118 64 L127 64 L129 86 L120 88 Z" />
    <path d="M118 84 L135 84 L135 91 L118 91 Z" />
  </g>
);

const Wheel: React.FC<{ x: number; y: number; r: number; turn: number }> = ({
  x,
  y,
  r,
  turn,
}) => (
  <g transform={`translate(${x} ${y}) rotate(${turn})`}>
    <circle r={r - 4} fill="none" stroke={WHITE} strokeWidth={9} />
    {[0, 60, 120].map((a) => {
      const c = Math.cos((a * Math.PI) / 180) * (r - 8);
      const s = Math.sin((a * Math.PI) / 180) * (r - 8);
      return (
        <line
          key={a}
          x1={-c}
          y1={-s}
          x2={c}
          y2={s}
          stroke={WHITE}
          strokeWidth={2.5}
        />
      );
    })}
    <circle r={5} fill={WHITE} />
  </g>
);

const useFonts = () => {
  const [handle] = useState(() => delayRender("Loading title fonts"));
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

// A slanted bar crossing the frame from left to right; `x` is its leading
// edge. The clip it returns reveals (or hides) what lies behind that edge.
const slashX = (frame: number, range: readonly [number, number]) =>
  interpolate(frame, range, [-260, 1200], {
    ...clamp,
    easing: Easing.inOut(Easing.cubic),
  });

// `pool` lays a soft dark pool behind the type for bright skies. It costs:
// a third of the frame half-transparent makes a ProRes 4444 several times
// larger (the alpha is stored lossless), so it is off by default and the
// type carries its own shadow instead.
export const AdventouringTitleMoto: React.FC<{ pool?: boolean }> = ({
  pool = false,
}) => {
  useFonts();
  const frame = useCurrentFrame();

  const inX = slashX(frame, SLASH_IN);
  const outX = slashX(frame, SLASH_OUT);
  const gone = frame >= SLASH_OUT[1];
  if (gone) return <AbsoluteFill />;
  // Everything left of the outgoing slash is wiped away.
  const exitClip =
    frame >= SLASH_OUT[0]
      ? `inset(0 0 0 ${Math.max(0, outX - 60)}px)`
      : undefined;

  const scrim =
    interpolate(frame, SCRIM_IN, [0, 1], clamp) *
    interpolate(frame, SLASH_OUT, [1, 0], clamp);
  const topoDraw = interpolate(frame, TOPO_IN, [0, 1], {
    ...clamp,
    easing: ease,
  });
  const topoZoom = interpolate(frame, [0, TITLE_MOTO_DURATION], [1, 1.08]);
  const hud = interpolate(frame, HUD_IN, [0, 1], { ...clamp, easing: ease });
  const pulse = (Math.max(0, frame - HUD_IN[0]) % 24) / 24;
  const subIn = interpolate(frame, [SUB[0], SUB[0] + 6], [0, 1], clamp);

  const ride = interpolate(frame, RIDE, [0, 1], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  const head = ROAD_X0 + (ROAD_X1 - 60 - ROAD_X0) * ride;
  const speed = interpolate(
    frame,
    [RIDE[0], RIDE[0] + 10, RIDE[1] - 12, RIDE[1]],
    [0, 1, 0.4, 0],
    clamp,
  );
  const bounce = ride < 1 ? Math.sin(frame * 1.9) * 1.4 : 0;
  const BIKE = 0.82;

  // The same lean (about 14 degrees) however tall the bar.
  const slashPoly = (x: number, top: number, h: number, w: number) => {
    const lean = h * 0.25;
    return `polygon(${x - w}px ${top + h}px, ${x - w + lean}px ${top}px, ${x + lean}px ${top}px, ${x}px ${top + h}px)`;
  };

  return (
    <AbsoluteFill style={{ clipPath: exitClip }}>
      {/* A soft dark pool behind the type, so white reads over any sky. */}
      {pool && (
        <div
          style={{
            position: "absolute",
            left: CX - 560,
            top: 520,
            width: 1120,
            height: 820,
            opacity: scrim,
            background:
              "radial-gradient(ellipse at center, rgba(10,10,10,0.5) 0%, rgba(10,10,10,0.28) 40%, rgba(10,10,10,0) 70%)",
          }}
        />
      )}

      {/* Real contour lines of the Oltrepò's mountains, fading to the edges. */}
      <svg
        width={TOPO_PX}
        height={TOPO_PX}
        viewBox={`0 0 ${TOPO_SIZE} ${TOPO_SIZE}`}
        style={{
          position: "absolute",
          left: CX - TOPO_PX / 2,
          top: 940 - TOPO_PX / 2,
          opacity: scrim,
          transform: `scale(${topoZoom}) rotate(-4deg)`,
          WebkitMaskImage:
            "radial-gradient(ellipse at center, #000 25%, transparent 68%)",
          maskImage:
            "radial-gradient(ellipse at center, #000 25%, transparent 68%)",
        }}
      >
        {contours.map((c, i) => (
          <path
            key={i}
            d={c.d}
            fill="none"
            stroke={WHITE}
            strokeOpacity={c.index ? 0.5 : 0.26}
            strokeWidth={c.index ? 2.4 : 1.3}
            pathLength={1}
            strokeDasharray={topoDraw >= 1 ? undefined : "1.05 1.05"}
            strokeDashoffset={topoDraw >= 1 ? undefined : 1.05 * (1 - topoDraw)}
          />
        ))}
      </svg>

      {/* HUD: Lombardia with its south lit, and where the films start. */}
      <div
        style={{
          position: "absolute",
          left: CX - 380,
          top: HUD_TOP,
          display: "flex",
          alignItems: "center",
          gap: 22,
          opacity: hud,
          transform: `translateX(${(1 - hud) * -40}px)`,
        }}
      >
        <svg width={84} height={84} viewBox={`0 0 ${VIEW} ${VIEW}`}>
          <path
            d={LOMBARDIA}
            fill="rgba(255,255,255,0.12)"
            stroke={WHITE}
            strokeWidth={10}
            strokeLinejoin="round"
          />
          <path d={OLTREPO} fill={ORANGE} />
          <circle
            cx={VARZI_MINI.x}
            cy={VARZI_MINI.y}
            r={14 + 60 * pulse}
            fill="none"
            stroke={ORANGE}
            strokeWidth={10}
            opacity={1 - pulse}
          />
          <circle cx={VARZI_MINI.x} cy={VARZI_MINI.y} r={16} fill={WHITE} />
        </svg>
        <div
          style={{
            fontFamily: MONO,
            fontWeight: 500,
            fontSize: 30,
            letterSpacing: 2,
            color: WHITE,
            whiteSpace: "pre",
            lineHeight: 1.25,
            textShadow: "0 2px 0 rgba(0,0,0,0.35), 0 3px 10px rgba(0,0,0,0.6)",
          }}
        >
          <div style={{ color: ORANGE }}>
            {scramble("OLTREPÒ PAVESE", frame, COORDS)}
          </div>
          <div>{scramble("44°49′25″N  9°11′49″E", frame, COORDS)}</div>
        </div>
      </div>

      {/* The title, revealed behind the slash's trailing edge. */}
      <div
        style={{
          position: "absolute",
          left: SAFE_RECT.x,
          width: SAFE_RECT.w,
          top: TITLE_TOP,
          height: TITLE_H,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          clipPath: `inset(-20px ${Math.max(-60, SAFE_RECT.x + SAFE_RECT.w - (inX - 40))}px -20px -60px)`,
        }}
      >
        <div
          style={{
            fontFamily: DISPLAY,
            fontWeight: 800,
            fontStyle: "italic",
            fontSize: 150,
            lineHeight: 1,
            letterSpacing: 1,
            color: WHITE,
            textShadow: "0 4px 0 rgba(0,0,0,0.35), 0 8px 24px rgba(0,0,0,0.55)",
            transform: `translateX(${interpolate(frame, SLASH_IN, [-24, 0], clamp)}px)`,
          }}
        >
          ADVEN<span style={{ color: ORANGE }}>TOURING</span>
        </div>
      </div>
      {/* The slash itself. */}
      {frame >= SLASH_IN[0] && frame <= SLASH_IN[1] && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: ORANGE,
            clipPath: slashPoly(inX, TITLE_TOP - 16, TITLE_H + 32, 110),
          }}
        />
      )}

      {/* Subtitle, decoding. */}
      <div
        style={{
          position: "absolute",
          left: SAFE_RECT.x,
          width: SAFE_RECT.w,
          top: SUB_TOP,
          textAlign: "center",
          fontFamily: DISPLAY,
          fontWeight: 600,
          fontSize: 46,
          letterSpacing: 13,
          color: WHITE,
          opacity: subIn,
          whiteSpace: "pre",
          textShadow: "0 2px 0 rgba(0,0,0,0.35), 0 3px 12px rgba(0,0,0,0.6)",
        }}
      >
        {scramble("NEL SUD DELLA LOMBARDIA", frame, SUB)}
      </div>

      {/* The road, laid down by the bike riding it. */}
      <svg
        width={1080}
        height={1920}
        style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}
      >
        <line
          x1={ROAD_X0}
          y1={ROAD_Y}
          x2={ROAD_X1}
          y2={ROAD_Y}
          stroke={WHITE}
          strokeOpacity={0.35 * subIn}
          strokeWidth={2}
          strokeDasharray="10 12"
        />
        {head > ROAD_X0 + 2 && (
          <line
            x1={ROAD_X0}
            y1={ROAD_Y}
            x2={head + 40}
            y2={ROAD_Y}
            stroke={ORANGE}
            strokeWidth={7}
            strokeLinecap="round"
          />
        )}
        {frame >= RIDE[0] && (
          <g
            transform={`translate(${head} ${ROAD_Y - 2 + bounce}) scale(${BIKE}) translate(-100 -118)`}
          >
            {/* speed lines */}
            {[30, 60, 92].map((y, i) => (
              <line
                key={y}
                x1={-20 - 90 * speed - i * 20}
                y1={y}
                x2={-14 - i * 6}
                y2={y}
                stroke={WHITE}
                strokeOpacity={0.7 * speed}
                strokeWidth={4}
                strokeLinecap="round"
              />
            ))}
            {WHEELS.map((w) => (
              <Wheel
                key={w.x}
                {...w}
                turn={((head - ROAD_X0) / (w.r * BIKE)) * 57.3}
              />
            ))}
            <BikeBody />
          </g>
        )}
      </svg>

      {/* The outgoing slash. */}
      {frame >= SLASH_OUT[0] && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: ORANGE,
            clipPath: slashPoly(outX, HUD_TOP - 30, ROAD_Y - HUD_TOP + 70, 120),
          }}
        />
      )}
    </AbsoluteFill>
  );
};
