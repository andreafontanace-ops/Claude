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
import { LOMBARDIA, OLTREPO, VARZI as VARZI_MINI, VIEW } from "./titleShapes";
import { contours, TOPO_SIZE } from "./topo";

// The series title in a riding-film look: a transparent 1080x1920 clip, 4s,
// to lay over any footage. Everything sits on one solid, slanted dark plate,
// so it reads the same over a white sky as over a dark wood: real contour
// lines of the Oltrepò's mountains drawn across it, a GPS readout with a
// mini Lombardia, ADVEN / TOURING big on two lines, the subtitle, and a bike
// riding along the plate's foot laying the orange road down. An orange slash
// brings the plate in and another takes it away. Inside the safe area
// (x 60-900, y 250-1500), clear of every platform's buttons.
export const TITLE_MOTO_DURATION = 120; // 4s @30fps

const DISPLAY = "Barlow Condensed";
const MONO = "JetBrains Mono";
const WHITE = "#ffffff";
const ORANGE = "#ff5a1f";
const PLATE = "#141414";

const SLASH_IN = [0, 14] as const;
const TOPO_IN = [6, 40] as const;
const HUD_IN = [12, 24] as const;
const COORDS = [16, 40] as const;
const ADVEN_IN = 12;
const TOURING_IN = 17;
const SUB = [24, 46] as const;
const RIDE = [32, 82] as const;
const SLASH_OUT = [100, 116] as const;

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// The plate: a parallelogram leaning right, x 60-900, y 600-1370.
const X0 = 60;
const X1 = 900;
const TOP = 600;
const BOTTOM = 1370;
const LEAN = 70;
const PLATE_POLY = `${X0 + LEAN},${TOP} ${X1},${TOP} ${X1 - LEAN},${BOTTOM} ${X0},${BOTTOM}`;
const INNER_X = 130;
const ROAD_Y = 1326;
const ROAD_X0 = 120;
const ROAD_X1 = 820;
const BIKE = 0.74;

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

// A slanted bar crossing the frame from left to right; returns its leading
// edge's x.
const slashX = (frame: number, range: readonly [number, number]) =>
  interpolate(frame, range, [-200, 1260], {
    ...clamp,
    easing: Easing.inOut(Easing.cubic),
  });

// The same lean as the plate, over the plate's height and a little more.
const slashPoly = (x: number, w: number) => {
  const top = TOP - 40;
  const h = BOTTOM - TOP + 80;
  const lean = (h * LEAN) / (BOTTOM - TOP);
  return `polygon(${x - w}px ${top + h}px, ${x - w + lean}px ${top}px, ${x + lean}px ${top}px, ${x}px ${top + h}px)`;
};

export const AdventouringTitleMoto: React.FC = () => {
  useFonts();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (frame >= SLASH_OUT[1]) return <AbsoluteFill />;

  const inX = slashX(frame, SLASH_IN);
  const outX = slashX(frame, SLASH_OUT);
  // Revealed behind the incoming slash, hidden behind the outgoing one. The
  // clip leans with the slash so the plate's edge never shows a vertical cut.
  const lean = LEAN + 40;
  const reveal =
    frame < SLASH_IN[1]
      ? `polygon(-200px -200px, ${inX - 40 + lean}px -200px, ${inX - 40 + lean}px ${TOP - 40}px, ${inX - 40}px ${BOTTOM + 40}px, ${inX - 40}px 2200px, -200px 2200px)`
      : frame >= SLASH_OUT[0]
        ? `polygon(${outX - 60 + lean}px ${TOP - 40}px, 1300px ${TOP - 40}px, 1300px 2200px, ${outX - 60}px 2200px, ${outX - 60}px ${BOTTOM + 40}px)`
        : undefined;

  const topoDraw = interpolate(frame, TOPO_IN, [0, 1], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  const topoDrift = interpolate(frame, [0, TITLE_MOTO_DURATION], [0, -40]);
  const hud = interpolate(frame, HUD_IN, [0, 1], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  const pulse = (Math.max(0, frame - HUD_IN[0]) % 24) / 24;
  const pop = (start: number) =>
    spring({
      frame: frame - start,
      fps,
      config: { damping: 15, mass: 0.6, stiffness: 170 },
    });
  const adven = pop(ADVEN_IN);
  const touring = pop(TOURING_IN);
  const subIn = interpolate(frame, [SUB[0], SUB[0] + 4], [0, 1], clamp);

  const ride = interpolate(frame, RIDE, [0, 1], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  const head = ROAD_X0 + 40 + (ROAD_X1 - 40 - ROAD_X0 - 40) * ride;
  const speed = interpolate(
    frame,
    [RIDE[0], RIDE[0] + 10, RIDE[1] - 12, RIDE[1]],
    [0, 1, 0.4, 0],
    clamp,
  );
  const bounce = ride < 1 ? Math.sin(frame * 1.9) * 1.4 : 0;

  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ clipPath: reveal }}>
        <svg
          width={1080}
          height={1920}
          style={{ position: "absolute", inset: 0 }}
        >
          <defs>
            <clipPath id="plate">
              <polygon points={PLATE_POLY} />
            </clipPath>
          </defs>
          {/* The plate, with a soft shadow so it sits on the footage. */}
          <polygon
            points={PLATE_POLY}
            fill={PLATE}
            style={{ filter: "drop-shadow(0 18px 30px rgba(0,0,0,0.45))" }}
          />
          {/* Real contour lines of the Oltrepò's mountains, inside the plate. */}
          <g clipPath="url(#plate)">
            <g
              transform={`translate(${X0 - 60 + topoDrift} ${TOP - 140}) scale(${980 / TOPO_SIZE})`}
            >
              {contours.map((c, i) => (
                <path
                  key={i}
                  d={c.d}
                  fill="none"
                  stroke={WHITE}
                  strokeOpacity={c.index ? 0.32 : 0.16}
                  strokeWidth={c.index ? 3 : 1.8}
                  pathLength={1}
                  strokeDasharray={topoDraw >= 1 ? undefined : "1.05 1.05"}
                  strokeDashoffset={
                    topoDraw >= 1 ? undefined : 1.05 * (1 - topoDraw)
                  }
                />
              ))}
            </g>
          </g>
          {/* The orange edge down the plate's left side. */}
          <polygon
            points={`${X0 + LEAN},${TOP} ${X0 + LEAN + 16},${TOP} ${X0 + 16},${BOTTOM} ${X0},${BOTTOM}`}
            fill={ORANGE}
          />

          {/* The road along the plate's foot, laid down by the bike. */}
          <line
            x1={ROAD_X0}
            y1={ROAD_Y}
            x2={ROAD_X1}
            y2={ROAD_Y}
            stroke={WHITE}
            strokeOpacity={0.3}
            strokeWidth={3}
            strokeDasharray="12 12"
          />
          {head > ROAD_X0 + 2 && frame >= RIDE[0] && (
            <line
              x1={ROAD_X0}
              y1={ROAD_Y}
              x2={head + 30}
              y2={ROAD_Y}
              stroke={ORANGE}
              strokeWidth={8}
              strokeLinecap="round"
            />
          )}
          {frame >= RIDE[0] && (
            <g
              transform={`translate(${head} ${ROAD_Y - 3 + bounce}) scale(${BIKE}) translate(-100 -118)`}
            >
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

        {/* GPS readout: Lombardia with its south lit, and Varzi. */}
        <div
          style={{
            position: "absolute",
            left: INNER_X + 40,
            top: TOP + 38,
            display: "flex",
            alignItems: "center",
            gap: 24,
            opacity: hud,
            transform: `translateX(${(1 - hud) * -30}px)`,
          }}
        >
          <svg width={104} height={104} viewBox={`0 0 ${VIEW} ${VIEW}`}>
            <path
              d={LOMBARDIA}
              fill="rgba(255,255,255,0.14)"
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
              fontSize: 36,
              letterSpacing: 1,
              color: WHITE,
              whiteSpace: "pre",
              lineHeight: 1.3,
            }}
          >
            <div style={{ color: ORANGE }}>
              {scramble("OLTREPÒ PAVESE", frame, COORDS)}
            </div>
            <div>{scramble("44°49′25″N 9°11′49″E", frame, COORDS)}</div>
          </div>
        </div>

        {/* ADVEN / TOURING, big, on two lines. */}
        <div
          style={{
            position: "absolute",
            left: INNER_X + 18,
            top: TOP + 150,
            fontFamily: DISPLAY,
            fontWeight: 800,
            fontStyle: "italic",
            fontSize: 214,
            lineHeight: 0.86,
            letterSpacing: 2,
          }}
        >
          <div
            style={{
              color: WHITE,
              opacity: frame < ADVEN_IN ? 0 : 1,
              transform: `translateX(${(1 - adven) * -90}px)`,
            }}
          >
            ADVEN
          </div>
          <div
            style={{
              color: ORANGE,
              opacity: frame < TOURING_IN ? 0 : 1,
              transform: `translateX(${(1 - touring) * 90}px)`,
            }}
          >
            TOURING
          </div>
        </div>

        {/* Subtitle, decoding. */}
        <div
          style={{
            position: "absolute",
            left: INNER_X + 24,
            top: TOP + 548,
            fontFamily: DISPLAY,
            fontWeight: 600,
            fontSize: 54,
            letterSpacing: 7,
            color: WHITE,
            opacity: subIn,
            whiteSpace: "pre",
          }}
        >
          {scramble("NEL SUD DELLA LOMBARDIA", frame, SUB)}
        </div>
      </AbsoluteFill>

      {/* The slashes that bring the plate in and take it away. */}
      {frame <= SLASH_IN[1] && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: ORANGE,
            clipPath: slashPoly(inX, 90),
          }}
        />
      )}
      {frame >= SLASH_OUT[0] && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: ORANGE,
            clipPath: slashPoly(outX, 110),
          }}
        />
      )}
    </AbsoluteFill>
  );
};
