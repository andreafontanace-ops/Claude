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
import { stages } from "./geoData";
import {
  clamp,
  DISPLAY,
  MONO,
  PLATE,
  scramble,
  SEASON_COLOR,
  SeasonIcon,
  SeasonId,
  slashPoly,
  slashX,
  useSeasonFonts,
  WHITE,
} from "./theme";

// A season's title card: a transparent 1080x1920 overlay, 4s, to lay over
// the footage as the chapter opens. One solid, slanted dark plate (it reads
// over any sky) carrying the season's glyph, TAPPA n DI 4, the season's name
// big, and the place. Behind the type, the place's own contour lines in the
// season's colour - the Verdon's gorge, the Val Taleggio's narrows, the
// Staffora's valley; winter, still a secret, gets falling snow instead.
// Inside the safe area, clear of every platform's buttons.
export const SEASON_CARD_DURATION = 120;

const SLASH_IN = [0, 14] as const;
const TEXTURE_IN = [6, 44] as const;
const ICON_IN = [12, 30] as const;
const STEP_IN = [14, 34] as const;
const NAME_IN = 14;
const PLACE = [26, 48] as const;
const SLASH_OUT = [100, 116] as const;

const X0 = 60;
const X1 = 900;
const TOP = 690;
const BOTTOM = 1250;
const LEAN = 60;
const LEAN_PER_PX = LEAN / (BOTTOM - TOP);
const PLATE_POLY = `${X0 + LEAN},${TOP} ${X1},${TOP} ${X1 - LEAN},${BOTTOM} ${X0},${BOTTOM}`;

export type SeasonCardProps = {
  season: SeasonId;
  n: number;
  place: string;
  stageId: string | null;
};

export const SeasonCard: React.FC<SeasonCardProps> = ({
  season,
  n,
  place,
  stageId,
}) => {
  useSeasonFonts();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (frame >= SLASH_OUT[1]) return <AbsoluteFill />;
  const color = SEASON_COLOR[season];
  const stage = stages.find((s) => s.id === stageId);

  const inX = slashX(frame, SLASH_IN);
  const outX = slashX(frame, SLASH_OUT);
  const lean = LEAN + 40;
  const reveal =
    frame < SLASH_IN[1]
      ? `polygon(-200px -200px, ${inX - 40 + lean}px -200px, ${inX - 40 + lean}px ${TOP - 40}px, ${inX - 40}px ${BOTTOM + 40}px, ${inX - 40}px 2200px, -200px 2200px)`
      : frame >= SLASH_OUT[0]
        ? `polygon(${outX - 60 + lean}px ${TOP - 40}px, 1300px ${TOP - 40}px, 1300px 2200px, ${outX - 60}px 2200px, ${outX - 60}px ${BOTTOM + 40}px)`
        : undefined;

  const texture = interpolate(frame, TEXTURE_IN, [0, 1], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  const icon = interpolate(frame, ICON_IN, [0, 1], clamp);
  const name = spring({
    frame: frame - NAME_IN,
    fps,
    config: { damping: 15, mass: 0.6, stiffness: 170 },
  });
  const placeIn = interpolate(frame, [PLACE[0], PLACE[0] + 4], [0, 1], clamp);
  // A long place name shrinks to fit the plate (about 0.42 em a letter plus
  // the tracking, in 700px).
  const placeSize = Math.min(66, Math.floor((700 / place.length - 4) / 0.42));

  // The place's contour lines, fitted into the plate.
  let topo: React.ReactNode = null;
  if (stage) {
    const b = stage.box;
    const s = (X1 - X0 + 80) / (b.x1 - b.x0);
    const drift = interpolate(frame, [0, SEASON_CARD_DURATION], [0, -30]);
    topo = (
      <g
        transform={`translate(${X0 - 40 + drift} ${(TOP + BOTTOM) / 2}) scale(${s}) translate(${-b.x0} ${-(b.y0 + b.y1) / 2})`}
      >
        {stage.contours.map((c, i) => (
          <path
            key={i}
            d={c.d}
            fill="none"
            stroke={color}
            strokeOpacity={c.index ? 0.42 : 0.2}
            strokeWidth={(c.index ? 3 : 1.6) / s}
            pathLength={1}
            strokeDasharray={texture >= 1 ? undefined : "1.05 1.05"}
            strokeDashoffset={texture >= 1 ? undefined : 1.05 * (1 - texture)}
          />
        ))}
      </g>
    );
  } else {
    // Winter: snow falling across the plate.
    topo = (
      <g opacity={texture}>
        {Array.from({ length: 70 }, (_, i) => {
          const x = X0 + random(`x${i}`) * (X1 - X0);
          const speed = 2 + random(`s${i}`) * 3;
          const r = 2 + random(`r${i}`) * 4;
          const y =
            TOP +
            ((random(`y${i}`) * (BOTTOM - TOP) + frame * speed) %
              (BOTTOM - TOP));
          const sway = Math.sin(frame / 14 + i) * 8;
          return (
            <circle
              key={i}
              cx={x + sway}
              cy={y}
              r={r}
              fill={WHITE}
              opacity={0.25 + random(`o${i}`) * 0.5}
            />
          );
        })}
      </g>
    );
  }

  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ clipPath: reveal }}>
        <svg
          width={1080}
          height={1920}
          style={{ position: "absolute", inset: 0 }}
        >
          <defs>
            <clipPath id={`plate-${season}`}>
              <polygon points={PLATE_POLY} />
            </clipPath>
          </defs>
          <polygon
            points={PLATE_POLY}
            fill={PLATE}
            style={{ filter: "drop-shadow(0 18px 30px rgba(0,0,0,0.45))" }}
          />
          <g clipPath={`url(#plate-${season})`}>{topo}</g>
          <polygon
            points={`${X0 + LEAN},${TOP} ${X0 + LEAN + 16},${TOP} ${X0 + 16},${BOTTOM} ${X0},${BOTTOM}`}
            fill={color}
          />
        </svg>

        {/* Glyph and TAPPA n DI 4. */}
        <div
          style={{
            position: "absolute",
            left: 150,
            top: TOP + 40,
            display: "flex",
            alignItems: "center",
            gap: 22,
          }}
        >
          <SeasonIcon
            season={season}
            size={110}
            t={icon}
            spin={Math.max(0, frame - ICON_IN[0]) / 30}
          />
          <div
            style={{
              fontFamily: MONO,
              fontWeight: 500,
              fontSize: 44,
              letterSpacing: 2,
              color,
              whiteSpace: "pre",
            }}
          >
            {scramble(`TAPPA ${n} DI 4`, frame, STEP_IN)}
          </div>
        </div>

        {/* The season, big. */}
        <div
          style={{
            position: "absolute",
            left: 140,
            top: TOP + 172,
            fontFamily: DISPLAY,
            fontWeight: 800,
            fontStyle: "italic",
            fontSize: 176,
            lineHeight: 1,
            letterSpacing: 2,
            color: WHITE,
            opacity: frame < NAME_IN ? 0 : 1,
            transform: `translateX(${(1 - name) * -90}px)`,
          }}
        >
          {season}
        </div>

        {/* The place. */}
        <div
          style={{
            position: "absolute",
            left: 146,
            top: TOP + 384,
            fontFamily: DISPLAY,
            fontWeight: 600,
            fontSize: placeSize,
            letterSpacing: 4,
            color,
            opacity: placeIn,
            whiteSpace: "pre",
          }}
        >
          {scramble(place, frame, PLACE)}
        </div>
      </AbsoluteFill>

      {frame <= SLASH_IN[1] && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: color,
            clipPath: slashPoly(inX, TOP - 40, BOTTOM + 40, 90, LEAN_PER_PX),
          }}
        />
      )}
      {frame >= SLASH_OUT[0] && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: color,
            clipPath: slashPoly(outX, TOP - 40, BOTTOM + 40, 110, LEAN_PER_PX),
          }}
        />
      )}
    </AbsoluteFill>
  );
};
