import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { fitBoxToRect, lerpCameraZoom, project } from "../shared/camera";
import { countries, countryLabels, stages } from "./geoData";
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

// Where a stage is: a full-screen 1080x1920 clip, 6s, cut between the
// rider's shots. A dark map of the Western Alps with the three stages lit in
// their seasons' colours; one drop onto this stage, where the finer borders,
// the lakes, the river that makes the place and its real contour lines come
// up; a pin lands; and a plate slides in with where it is and how high.
export const SEASON_MAP_DURATION = 180;

const ZOOM = [10, 108] as const;
const LOCAL_IN = [64, 100] as const;
const CONTOURS_IN = [80, 132] as const;
const RIVER_IN = [92, 136] as const;
const PIN = [102, 124] as const;
const TAGS_IN = [108, 126] as const;
const SLASH_IN = [112, 126] as const;
const STEP_IN = [120, 140] as const;
const NAME_IN = 122;
const SUB_IN = [128, 140] as const;
const COORDS = [130, 158] as const;

const BG = "#0e1012";
const LAND = "#1c2125";
const LAND_HOME = "#262d33";
const BORDER = "#4a545e";
const WATER = "#1d3a4e";

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

// The map sits in the upper part of the safe area; the plate takes the foot.
const MAP_RECT = { x: 60, y: 260, w: 840, h: 840 };
const P_TOP = 1150;
const P_BOTTOM = 1470;
const P_LEAN = 50;
const P_POLY = `${60 + P_LEAN},${P_TOP} 900,${P_TOP} ${900 - P_LEAN},${P_BOTTOM} 60,${P_BOTTOM}`;

const HOME: Record<string, string> = {
  verdon: "France",
  novena: "Switzerland",
  staffora: "Italy",
};
const SEASON_OF: Record<string, SeasonId> = {
  verdon: "PRIMAVERA",
  novena: "ESTATE",
  staffora: "AUTUNNO",
};

export const SeasonMap: React.FC<{ stageId: string }> = ({ stageId }) => {
  useSeasonFonts();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const stage = stages.find((s) => s.id === stageId)!;
  const season = SEASON_OF[stageId];
  const color = SEASON_COLOR[season];

  const zoom = interpolate(frame, ZOOM, [0, 1], {
    ...clamp,
    easing: Easing.inOut(Easing.cubic),
  });
  const camera = lerpCameraZoom(
    fitBoxToRect(OVERVIEW, MAP_RECT),
    fitBoxToRect(stage.box, MAP_RECT),
    zoom,
    MAP_RECT,
  );
  const local = interpolate(frame, LOCAL_IN, [0, 1], clamp);
  const cont = interpolate(frame, CONTOURS_IN, [0, 1], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  const river = interpolate(frame, RIVER_IN, [0, 1], {
    ...clamp,
    easing: Easing.inOut(Easing.cubic),
  });
  const labelsOut = interpolate(frame, [40, 70], [1, 0], clamp);
  const tags = interpolate(frame, TAGS_IN, [0, 1], clamp);
  const pulse = (frame % 30) / 30;

  // The contours' data reach 0.75 of the window out from the stage.
  const fadeR = (stage.box.x1 - stage.box.x0) * 0.72;
  const pinFall = spring({
    frame: frame - PIN[0],
    fps,
    config: { damping: 10, mass: 0.6, stiffness: 130 },
  });
  const pin = project(camera, stage.x, stage.y);

  const inX = slashX(frame, SLASH_IN);
  const plateShown = frame >= SLASH_IN[0];
  const plateClip =
    frame < SLASH_IN[1]
      ? `polygon(-200px ${P_TOP - 40}px, ${inX - 40 + 66}px ${P_TOP - 40}px, ${inX - 40}px ${P_BOTTOM + 40}px, -200px ${P_BOTTOM + 40}px)`
      : undefined;
  const name = spring({
    frame: frame - NAME_IN,
    fps,
    config: { damping: 15, mass: 0.6, stiffness: 170 },
  });
  const subIn = interpolate(frame, SUB_IN, [0, 1], clamp);
  // 2.478 m, as in the other films (it-IT leaves four digits ungrouped).
  const elev = stage.elevation
    ? ` · ${String(stage.elevation).replace(/\B(?=(\d{3})+(?!\d))/g, ".")} m`
    : "";

  return (
    <AbsoluteFill style={{ background: BG }}>
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
              fill={c.name === HOME[stageId] ? LAND_HOME : LAND}
              stroke={BORDER}
              strokeWidth={1.6}
              vectorEffect="non-scaling-stroke"
              fillRule="evenodd"
            />
          ))}
          {/* Close to the stage: the finer borders, the water, the ground. */}
          <g opacity={local}>
            {stage.areas.map((a, i) => (
              <path
                key={i}
                d={a.d}
                fill={a.home ? LAND_HOME : LAND}
                stroke={BORDER}
                strokeWidth={1.4}
                vectorEffect="non-scaling-stroke"
                fillRule="evenodd"
              />
            ))}
            {stage.lakes.map((d, i) => (
              <path key={i} d={d} fill={WATER} fillRule="evenodd" />
            ))}
          </g>
          {/* The contours fade out in a circle round the stage: their data
              stops at a square, and a square edge on the map reads as a
              tile, not as ground. */}
          <defs>
            <radialGradient
              id={`fade-${stage.id}`}
              gradientUnits="userSpaceOnUse"
              cx={stage.x}
              cy={stage.y}
              r={fadeR}
            >
              <stop offset="0.55" stopColor="#fff" />
              <stop offset="1" stopColor="#000" />
            </radialGradient>
            <mask
              id={`fade-mask-${stage.id}`}
              maskUnits="userSpaceOnUse"
              x={stage.x - fadeR}
              y={stage.y - fadeR}
              width={fadeR * 2}
              height={fadeR * 2}
            >
              <rect
                x={stage.x - fadeR}
                y={stage.y - fadeR}
                width={fadeR * 2}
                height={fadeR * 2}
                fill={`url(#fade-${stage.id})`}
              />
            </mask>
          </defs>
          <g mask={`url(#fade-mask-${stage.id})`}>
            {cont > 0 &&
              stage.contours.map((c, i) => (
                <path
                  key={i}
                  d={c.d}
                  fill="none"
                  stroke={color}
                  strokeOpacity={c.index ? 0.45 : 0.2}
                  strokeWidth={c.index ? 2.2 : 1.2}
                  vectorEffect="non-scaling-stroke"
                  pathLength={1}
                  strokeDasharray={cont >= 1 ? undefined : "1.05 1.05"}
                  strokeDashoffset={cont >= 1 ? undefined : 1.05 * (1 - cont)}
                />
              ))}
          </g>
          {stage.river && river > 0 && (
            <g>
              <path
                d={stage.river}
                fill="none"
                stroke={color}
                strokeOpacity={0.3}
                strokeWidth={14}
                strokeLinecap="round"
                strokeLinejoin="round"
                vectorEffect="non-scaling-stroke"
                pathLength={1}
                strokeDasharray={river >= 1 ? undefined : "1.05 1.05"}
                strokeDashoffset={river >= 1 ? undefined : 1.05 * (1 - river)}
              />
              <path
                d={stage.river}
                fill="none"
                stroke={color}
                strokeWidth={4.5}
                strokeLinecap="round"
                strokeLinejoin="round"
                vectorEffect="non-scaling-stroke"
                pathLength={1}
                strokeDasharray={river >= 1 ? undefined : "1.05 1.05"}
                strokeDashoffset={river >= 1 ? undefined : 1.05 * (1 - river)}
              />
            </g>
          )}
        </g>

        {/* All three stages, lit in their colours while the map is wide. */}
        {stages.map((s) => {
          const p = project(camera, s.x, s.y);
          const c = SEASON_COLOR[SEASON_OF[s.id]];
          const mine = s.id === stageId;
          const fade = mine
            ? interpolate(frame, [PIN[0] - 4, PIN[0] + 4], [1, 0], clamp)
            : labelsOut;
          if (fade <= 0) return null;
          return (
            <g key={s.id} opacity={fade}>
              {mine && (
                <circle
                  cx={p.left}
                  cy={p.top}
                  r={16 + 50 * pulse}
                  fill="none"
                  stroke={c}
                  strokeWidth={5}
                  opacity={1 - pulse}
                />
              )}
              <circle
                cx={p.left}
                cy={p.top}
                r={mine ? 15 : 11}
                fill={c}
                stroke={BG}
                strokeWidth={4}
              />
            </g>
          );
        })}
      </svg>

      {/* Country names on the wide map. */}
      {labelsOut > 0 &&
        countryLabels.map((l) => {
          const p = project(camera, l.x, l.y);
          return (
            <div
              key={l.label}
              style={{
                position: "absolute",
                left: p.left,
                top: p.top,
                transform: "translate(-50%, -50%)",
                fontFamily: DISPLAY,
                fontWeight: 600,
                fontSize: 52,
                letterSpacing: 10,
                color: "#9aa4ad",
                opacity: labelsOut,
                whiteSpace: "nowrap",
              }}
            >
              {l.label}
            </div>
          );
        })}

      {/* The finer areas' names, close up. */}
      {tags > 0 &&
        stage.tags.map((t) => {
          const p = project(camera, t.x, t.y);
          return (
            <div
              key={t.label}
              style={{
                position: "absolute",
                left: p.left,
                top: p.top,
                transform: "translate(-50%, -50%)",
                fontFamily: DISPLAY,
                fontWeight: 600,
                fontSize: 40,
                letterSpacing: 7,
                color: "#c3cbd2",
                opacity: tags * 0.9,
                whiteSpace: "nowrap",
                textShadow: `0 2px 10px ${BG}`,
              }}
            >
              {t.label}
            </div>
          );
        })}

      {/* The pin, in the season's colour. */}
      {frame >= PIN[0] && (
        <div style={{ position: "absolute", left: pin.left, top: pin.top }}>
          <div
            style={{
              position: "absolute",
              width: 70,
              height: 70,
              borderRadius: "50%",
              border: `5px solid ${color}`,
              transform: `translate(-50%, -50%) scale(${0.4 + pulse * 1.4})`,
              opacity: (1 - pulse) * pinFall,
            }}
          />
          <svg
            width={84}
            height={108}
            viewBox="0 0 56 72"
            style={{
              position: "absolute",
              transform: `translate(-50%, -100%) translateY(${(1 - pinFall) * -260}px)`,
              filter: "drop-shadow(0 8px 10px rgba(0,0,0,0.6))",
            }}
          >
            <path
              d="M28 2C13.6 2 2 13.6 2 28c0 19.5 26 42 26 42s26-22.5 26-42C54 13.6 42.4 2 28 2z"
              fill={color}
              stroke={BG}
              strokeWidth={2}
            />
            <circle cx={28} cy={27} r={10.5} fill={BG} />
          </svg>
        </div>
      )}

      {/* The plate: which stage, where, how high. */}
      {plateShown && (
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
            />
            <polygon
              points={`${60 + P_LEAN},${P_TOP} ${60 + P_LEAN + 14},${P_TOP} ${74},${P_BOTTOM} 60,${P_BOTTOM}`}
              fill={color}
            />
          </svg>
          <div
            style={{
              position: "absolute",
              left: 128,
              top: P_TOP + 26,
              display: "flex",
              alignItems: "center",
              gap: 16,
            }}
          >
            <SeasonIcon
              season={season}
              size={52}
              t={interpolate(frame, STEP_IN, [0, 1], clamp)}
              spin={frame / 30}
            />
            <div
              style={{
                fontFamily: MONO,
                fontWeight: 500,
                fontSize: 36,
                letterSpacing: 2,
                color,
                whiteSpace: "pre",
              }}
            >
              {scramble(`TAPPA ${stage.n} · ${season}`, frame, STEP_IN)}
            </div>
          </div>
          <div
            style={{
              position: "absolute",
              left: 118,
              top: P_TOP + 88,
              fontFamily: DISPLAY,
              fontWeight: 800,
              fontStyle: "italic",
              fontSize: 84,
              lineHeight: 1,
              color: WHITE,
              whiteSpace: "nowrap",
              opacity: frame < NAME_IN ? 0 : 1,
              transform: `translateX(${(1 - name) * -70}px)`,
            }}
          >
            {stage.name}
          </div>
          <div
            style={{
              position: "absolute",
              left: 122,
              top: P_TOP + 186,
              fontFamily: DISPLAY,
              fontWeight: 600,
              fontSize: 44,
              letterSpacing: 2,
              color: "#c9cfd4",
              opacity: subIn,
              transform: `translateY(${(1 - subIn) * 12}px)`,
              whiteSpace: "nowrap",
            }}
          >
            {stage.sub}
          </div>
          <div
            style={{
              position: "absolute",
              left: 118,
              top: P_TOP + 246,
              fontFamily: MONO,
              fontWeight: 500,
              fontSize: 35,
              letterSpacing: 1,
              color: WHITE,
              whiteSpace: "pre",
            }}
          >
            {scramble(stage.coords + elev, frame, COORDS)}
          </div>
        </AbsoluteFill>
      )}
      {frame >= SLASH_IN[0] && frame <= SLASH_IN[1] && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: color,
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
