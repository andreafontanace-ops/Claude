import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
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
  useSeasonFonts,
  WHITE,
} from "./theme";

// The opening title of "4 stagioni, 4 tappe": a transparent 1080x1920
// overlay, 5s. Four slanted bars in the seasons' colours slam in one after
// another, each with its glyph and name; they close up to the left into the
// four-colour edge of a dark plate, on which the title lands - the first line
// white, the second in the four colours - over the Novena's contour lines,
// with the subtitle decoding below. Four coloured slashes take it away.
// Every line of text is a prop, so another title is one render away.
export const SEASONS_TITLE_DURATION = 150;

const ORDER: SeasonId[] = ["PRIMAVERA", "ESTATE", "AUTUNNO", "INVERNO"];
const COLORS = ORDER.map((s) => SEASON_COLOR[s]);

const X0 = 60;
const X1 = 900;
const TOP = 620;
const BOTTOM = 1320;
const LEAN = 60;
const LEAN_PER_PX = LEAN / (BOTTOM - TOP);
const PLATE_POLY = `${X0 + LEAN},${TOP} ${X1},${TOP} ${X1 - LEAN},${BOTTOM} ${X0},${BOTTOM}`;
const BAR_GAP = 12;
const BAR_H = (BOTTOM - TOP - 3 * BAR_GAP) / 4;
const EDGE = 18;

const BAR_IN = [0, 5, 10, 15];
const BARS_CLOSE = [36, 54] as const;
const PLATE_IN = 30;
const TOPO_IN = [48, 96] as const;
const LINE1_IN = 50;
const LINE2_IN = 57;
const SUB = [66, 92] as const;
const OUT = [122, 146] as const;

// x of the plate's left edge at height y (it leans right going up).
const leftAt = (y: number) => X0 + (BOTTOM - y) * LEAN_PER_PX;

export type SeasonsTitleProps = {
  line1: string;
  line2: string;
  sub1: string;
  sub2: string;
};

export const SeasonsTitle: React.FC<SeasonsTitleProps> = ({
  line1,
  line2,
  sub1,
  sub2,
}) => {
  useSeasonFonts();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (frame >= OUT[1] + 2) return <AbsoluteFill />;

  const close = interpolate(frame, BARS_CLOSE, [0, 1], {
    ...clamp,
    easing: Easing.inOut(Easing.cubic),
  });
  const pop = (start: number) =>
    spring({
      frame: frame - start,
      fps,
      config: { damping: 15, mass: 0.6, stiffness: 170 },
    });
  const topo = interpolate(frame, TOPO_IN, [0, 1], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  const subIn = interpolate(frame, [SUB[0], SUB[0] + 4], [0, 1], clamp);
  const l1 = pop(LINE1_IN);
  const l2 = pop(LINE2_IN);

  // The exit: four coloured slashes a few frames apart. The plate goes
  // behind the first one - hidden left of its trailing edge, along its lean -
  // and the other three follow over the footage.
  const outX = (k: number) =>
    interpolate(frame, [OUT[0] + k * 3, OUT[1] + k * 3 - 6], [-260, 1400], {
      ...clamp,
      easing: Easing.inOut(Easing.cubic),
    });
  const SLOPE = LEAN_PER_PX;
  const SLASH_BOTTOM = BOTTOM + 60;
  const edge = outX(0) - 70;
  const exitClip =
    frame >= OUT[0]
      ? `polygon(${edge + SLASH_BOTTOM * SLOPE}px 0px, 1500px 0px, 1500px 2000px, ${edge + (SLASH_BOTTOM - 2000) * SLOPE}px 2000px)`
      : undefined;

  const novena = stages.find((s) => s.id === "novena")!;
  const b = novena.box;
  const s = (X1 - X0 + 100) / (b.x1 - b.x0);
  const drift = interpolate(frame, [0, SEASONS_TITLE_DURATION], [0, -40]);

  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ clipPath: exitClip }}>
        {/* The plate, behind the bars until they close up. */}
        {frame >= PLATE_IN && (
          <svg
            width={1080}
            height={1920}
            style={{ position: "absolute", inset: 0 }}
          >
            <defs>
              <clipPath id="title-plate">
                <polygon points={PLATE_POLY} />
              </clipPath>
            </defs>
            <polygon
              points={PLATE_POLY}
              fill={PLATE}
              style={{ filter: "drop-shadow(0 18px 30px rgba(0,0,0,0.45))" }}
            />
            <g clipPath="url(#title-plate)">
              <g
                transform={`translate(${X0 - 50 + drift} ${(TOP + BOTTOM) / 2}) scale(${s}) translate(${-b.x0} ${-(b.y0 + b.y1) / 2})`}
              >
                {novena.contours.map((c, i) => (
                  <path
                    key={i}
                    d={c.d}
                    fill="none"
                    stroke={WHITE}
                    strokeOpacity={c.index ? 0.22 : 0.1}
                    strokeWidth={(c.index ? 3 : 1.6) / s}
                    pathLength={1}
                    strokeDasharray={topo >= 1 ? undefined : "1.05 1.05"}
                    strokeDashoffset={topo >= 1 ? undefined : 1.05 * (1 - topo)}
                  />
                ))}
              </g>
            </g>
          </svg>
        )}

        {/* The four season bars: in one after another, then closed up into
            the plate's four-colour edge. */}
        <svg
          width={1080}
          height={1920}
          style={{ position: "absolute", inset: 0 }}
        >
          {ORDER.map((season, i) => {
            const y0 = TOP + i * (BAR_H + BAR_GAP);
            const y1 = y0 + BAR_H;
            const slide = spring({
              frame: frame - BAR_IN[i],
              fps,
              config: { damping: 16, mass: 0.6, stiffness: 190 },
            });
            const shift = (1 - slide) * -1150;
            const width = EDGE + (X1 - X0 - EDGE) * (1 - close);
            const pts = [
              [leftAt(y0) + shift, y0],
              [leftAt(y0) + width + shift, y0],
              [leftAt(y1) + width + shift, y1],
              [leftAt(y1) + shift, y1],
            ]
              .map((p) => p.join(","))
              .join(" ");
            return frame >= BAR_IN[i] ? (
              <polygon key={season} points={pts} fill={COLORS[i]} />
            ) : null;
          })}
        </svg>
        {/* Their glyphs and names, gone as the bars close. */}
        {close < 1 &&
          ORDER.map((season, i) => {
            const y0 = TOP + i * (BAR_H + BAR_GAP);
            const slide = spring({
              frame: frame - BAR_IN[i],
              fps,
              config: { damping: 16, mass: 0.6, stiffness: 190 },
            });
            if (frame < BAR_IN[i]) return null;
            return (
              <div
                key={season}
                style={{
                  position: "absolute",
                  left: leftAt(y0 + BAR_H / 2) + 40,
                  top: y0 + BAR_H / 2,
                  transform: `translate(${(1 - slide) * -1150 - close * 500}px, -50%)`,
                  opacity: 1 - close * 1.6,
                  display: "flex",
                  alignItems: "center",
                  gap: 20,
                }}
              >
                <div
                  style={{
                    background: PLATE,
                    borderRadius: 60,
                    padding: 6,
                    display: "flex",
                  }}
                >
                  <SeasonIcon
                    season={season}
                    size={92}
                    t={slide}
                    spin={frame / 30}
                  />
                </div>
                <div
                  style={{
                    fontFamily: DISPLAY,
                    fontWeight: 800,
                    fontStyle: "italic",
                    fontSize: 118,
                    lineHeight: 1,
                    color: "#121212",
                  }}
                >
                  {season}
                </div>
              </div>
            );
          })}

        {/* The title. */}
        <div
          style={{
            position: "absolute",
            left: 128,
            top: TOP + 130,
            fontFamily: DISPLAY,
            fontWeight: 800,
            fontStyle: "italic",
            fontSize: 150,
            lineHeight: 1.02,
            whiteSpace: "nowrap",
          }}
        >
          <div
            style={{
              color: WHITE,
              opacity: frame < LINE1_IN ? 0 : 1,
              transform: `translateX(${(1 - l1) * -90}px)`,
            }}
          >
            {line1}
          </div>
          <div
            style={{
              opacity: frame < LINE2_IN ? 0 : 1,
              transform: `translateX(${(1 - l2) * 90}px)`,
              backgroundImage: `linear-gradient(90deg, ${COLORS.join(", ")})`,
              WebkitBackgroundClip: "text",
              backgroundClip: "text",
              color: "transparent",
              display: "inline-block",
              paddingRight: 24,
            }}
          >
            {line2}
          </div>
        </div>
        <div
          style={{
            position: "absolute",
            left: 140,
            top: TOP + 494,
            fontFamily: MONO,
            fontWeight: 500,
            fontSize: 44,
            lineHeight: 1.3,
            letterSpacing: 2,
            color: WHITE,
            opacity: subIn,
            whiteSpace: "pre",
          }}
        >
          <div>{scramble(sub1, frame, SUB)}</div>
          <div style={{ color: "#c9cfd4" }}>
            {scramble(sub2, frame, [SUB[0] + 6, SUB[1] + 6])}
          </div>
        </div>
      </AbsoluteFill>

      {/* The four exit slashes. */}
      {frame >= OUT[0] &&
        COLORS.map((c, k) => {
          const x = outX(k);
          const lean = (BOTTOM - TOP + 120) * LEAN_PER_PX;
          const top = TOP - 60;
          const bottom = BOTTOM + 60;
          return (
            <div
              key={c}
              style={{
                position: "absolute",
                inset: 0,
                background: c,
                clipPath: `polygon(${x - 70}px ${bottom}px, ${x - 70 + lean}px ${top}px, ${x + lean}px ${top}px, ${x}px ${bottom}px)`,
              }}
            />
          );
        })}
    </AbsoluteFill>
  );
};
