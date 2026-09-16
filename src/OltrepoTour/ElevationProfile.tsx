import React from "react";
import { Easing, interpolate } from "remotion";
import { fontFamily } from "../shared/fonts";
import { ROUTE_RED } from "../shared/palette";
import { profile, TOTAL_KM } from "./geoData";
import { PROFILE_IN, ROAD_CRINALE, ROAD_VALLE } from "./timeline";

// The card, in frame pixels. It sits in the band the route framing was lifted
// out of, under the names and clear of the caption strip below.
const CARD = { left: 60, top: 1290, width: 840, height: 200 };

// The plot inside it, in the card's own coordinates.
const PLOT = { x: 34, y: 58, w: 772, h: 92 };

const MIN_M = 380;
const MAX_M = 1560;

const VALLEY_KM = profile.find((p) => p.id === "giova")!.km;

const ASCENT = profile.reduce(
  (sum, p, i) =>
    i === 0 ? 0 : sum + Math.max(0, p.elevation - profile[i - 1].elevation),
  0,
);

const px = (km: number) => PLOT.x + (km / TOTAL_KM) * PLOT.w;
const py = (m: number) =>
  PLOT.y + PLOT.h - ((m - MIN_M) / (MAX_M - MIN_M)) * PLOT.h;

const LINE = "M" + profile.map((p) => `${px(p.km)},${py(p.elevation)}`).join("L");
const AREA = `${LINE}L${px(TOTAL_KM)},${PLOT.y + PLOT.h}L${PLOT.x},${PLOT.y + PLOT.h}Z`;

// The same easing RoutePath draws with, so the profile fills in step with the
// line on the map rather than drifting ahead of it.
const ease = Easing.inOut(Easing.cubic);

const legProgress = (frame: number, range: readonly [number, number]) =>
  interpolate(frame, range, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ease,
  });

const elevationAt = (km: number) => {
  for (let i = 1; i < profile.length; i++) {
    if (km <= profile[i].km) {
      const a = profile[i - 1];
      const b = profile[i];
      const t = b.km === a.km ? 0 : (km - a.km) / (b.km - a.km);
      return a.elevation + (b.elevation - a.elevation) * t;
    }
  }
  return profile[profile.length - 1].elevation;
};

const AXIS: { id: string; label: string; anchor: "start" | "middle" | "end" }[] = [
  { id: "varzi", label: "VARZI", anchor: "start" },
  { id: "giova", label: "GIOVÀ", anchor: "middle" },
  { id: "brallo", label: "BRALLO", anchor: "end" },
];

export const ElevationProfile: React.FC<{ frame: number }> = ({ frame }) => {
  const opacity = interpolate(frame, PROFILE_IN, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const rise = interpolate(frame, PROFILE_IN, [40, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  if (opacity <= 0) return null;

  const km =
    legProgress(frame, ROAD_VALLE) * VALLEY_KM +
    legProgress(frame, ROAD_CRINALE) * (TOTAL_KM - VALLEY_KM);
  const tipX = px(km);
  const tipY = py(elevationAt(km));

  const peak = profile.find((p) => p.id === "colletta")!;

  return (
    <div
      style={{
        position: "absolute",
        left: CARD.left,
        top: CARD.top,
        width: CARD.width,
        height: CARD.height,
        opacity,
        transform: `translateY(${rise}px)`,
        filter: "drop-shadow(0 8px 18px rgba(80,66,40,0.18))",
        fontFamily,
      }}
    >
      <svg
        width={CARD.width}
        height={CARD.height}
        viewBox={`0 0 ${CARD.width} ${CARD.height}`}
      >
        <defs>
          <linearGradient id="profileFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={ROUTE_RED} stopOpacity={0.42} />
            <stop offset="100%" stopColor={ROUTE_RED} stopOpacity={0.06} />
          </linearGradient>
          <clipPath id="profileClip">
            <rect x={0} y={0} width={tipX} height={CARD.height} />
          </clipPath>
        </defs>

        <rect
          x={2}
          y={2}
          width={CARD.width - 4}
          height={CARD.height - 4}
          rx={22}
          fill="#faf6ec"
          fillOpacity={0.97}
          stroke="#ded5c1"
          strokeWidth={2}
        />

        <text x={PLOT.x} y={36} fontSize={26} fontWeight={800} fill="#6b5f47" letterSpacing={3}>
          PROFILO
        </text>
        <text
          x={PLOT.x + PLOT.w}
          y={36}
          fontSize={26}
          fontWeight={800}
          fill="#231f16"
          textAnchor="end"
        >
          {TOTAL_KM.toLocaleString("it-IT", { maximumFractionDigits: 0 })} km ·{" "}
          {"+" + ASCENT.toLocaleString("it-IT")} m
        </text>

        {/* The unridden road, drawn faint the whole way across, so the shape
            of what is still to come is there from the first frame. */}
        <path d={LINE} fill="none" stroke="#c9c0ab" strokeWidth={3} strokeLinejoin="round" />

        <g clipPath="url(#profileClip)">
          <path d={AREA} fill="url(#profileFill)" />
          <path
            d={LINE}
            fill="none"
            stroke={ROUTE_RED}
            strokeWidth={5}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </g>

        {km > 0.2 && (
          <>
            <line
              x1={tipX}
              y1={tipY}
              x2={tipX}
              y2={PLOT.y + PLOT.h}
              stroke={ROUTE_RED}
              strokeWidth={2}
              strokeOpacity={0.45}
            />
            <circle cx={tipX} cy={tipY} r={8} fill={ROUTE_RED} stroke="#faf6ec" strokeWidth={3} />
          </>
        )}

        {/* The high point of the ride, called out where it happens. */}
        <circle cx={px(peak.km)} cy={py(peak.elevation)} r={5} fill="#6b5f47" />
        <text
          x={px(peak.km) + 14}
          y={py(peak.elevation) + 7}
          fontSize={22}
          fontWeight={800}
          fill="#6b5f47"
        >
          {peak.elevation.toLocaleString("it-IT")} m
        </text>

        <line
          x1={PLOT.x}
          y1={PLOT.y + PLOT.h}
          x2={PLOT.x + PLOT.w}
          y2={PLOT.y + PLOT.h}
          stroke="#ded5c1"
          strokeWidth={2}
        />
        {AXIS.map(({ id, label, anchor }) => {
          const point = profile.find((p) => p.id === id)!;
          return (
            <text
              key={id}
              x={px(point.km)}
              y={PLOT.y + PLOT.h + 28}
              fontSize={20}
              fontWeight={700}
              fill="#8a7d63"
              letterSpacing={1.5}
              textAnchor={anchor}
            >
              {label}
            </text>
          );
        })}
      </svg>
    </div>
  );
};
