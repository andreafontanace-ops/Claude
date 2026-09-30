import React from "react";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { usePeniceCamera } from "./usePeniceCamera";
import { RoutePath } from "../shared/RoutePath";
import { PinMarker } from "../shared/PinMarker";
import { TravelDot } from "../shared/TravelDot";
import { GrainOverlay } from "../shared/GrainOverlay";
import { RegionMap } from "../shared/RegionMap";
import { RoadShield } from "../shared/RoadShield";
import { project } from "../shared/camera";
import { fontFamily } from "../shared/fonts";
import { mapLabelStyle } from "../shared/labelStyle";
import { ROUTE_RED } from "../shared/palette";
import { SAFE_RECT } from "../shared/safeArea";
import {
  beyond,
  climb,
  comuni,
  descent,
  home,
  KM_TOTAL,
  MONTE_PENICE,
  places,
  regionTags,
} from "./geoData";
import {
  BOBBIO_PIN,
  CLIMB,
  DESCENT,
  DETAIL_OUT,
  GHOST_IN,
  MONTE_PENICE_IN,
  WIDE_TAGS_IN,
  SUMMARY_IN,
  frameAt,
  pinCue,
} from "./timeline";

const placeById = (id: string) => places.find((p) => p.id === id)!;

// Under the road in the closing whole-road framing, inside the safe area.
const SUMMARY_TOP = 1210;
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// The SS461 is the road the whole way; its plate once on each side of the
// pass, where the camera is riding that stretch.
const SHIELDS = [
  { road: climb, range: CLIMB, at: 0.42, dx: 0, dy: -70 },
  { road: descent, range: DESCENT, at: 0.5, dx: 0, dy: -90 },
];

export const BobbioVarzi: React.FC = () => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const camera = usePeniceCamera(frame, SAFE_RECT);

  const bobbio = placeById("bobbio");
  const penice = placeById("penice");
  const varzi = placeById("varzi");

  const detail = interpolate(frame, DETAIL_OUT, [1, 0], clamp);
  const ghostOpacity = interpolate(frame, GHOST_IN, [0, 0.32], clamp);
  // The peak and the region names around the pass arrive together, as the
  // climb nears the top.
  const peakIn = interpolate(frame, MONTE_PENICE_IN, [0, 1], clamp);
  const peakOpacity = peakIn * detail;
  const wideTagOpacity = interpolate(frame, WIDE_TAGS_IN, [0, 1], clamp);
  const summaryOpacity = interpolate(frame, SUMMARY_IN, [0, 1], clamp);
  const summaryRise = interpolate(frame, SUMMARY_IN, [16, 0], clamp);
  const peak = project(camera, MONTE_PENICE.x, MONTE_PENICE.y);

  return (
    <AbsoluteFill
      style={{
        background: "linear-gradient(180deg, #f7f2e6 0%, #f2ebd9 100%)",
      }}
    >
      <AbsoluteFill>
        <svg
          width={width}
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          style={{ position: "absolute", top: 0, left: 0 }}
        >
          <g
            transform={`translate(${camera.tx},${camera.ty}) scale(${camera.scale})`}
          >
            <RegionMap
              home={home}
              beyond={beyond}
              comuni={comuni}
              scale={camera.scale}
              comuneOpacity={0.62}
              borderOpacity={1}
            />
            {/* The whole road, faint: the red line draws over it. */}
            {[climb, descent].map((r) => (
              <path
                key={`ghost-${r.id}`}
                d={r.d}
                fill="none"
                stroke={ROUTE_RED}
                strokeWidth={8 / camera.scale}
                strokeLinecap="round"
                strokeLinejoin="round"
                opacity={ghostOpacity}
              />
            ))}
            <RoutePath
              d={climb.d}
              frame={frame}
              range={CLIMB}
              color={ROUTE_RED}
              width={14 / camera.scale}
            />
            <RoutePath
              d={descent.d}
              frame={frame}
              range={DESCENT}
              color={ROUTE_RED}
              width={14 / camera.scale}
            />
          </g>
        </svg>

        <AbsoluteFill style={{ fontFamily }}>
          {/* The regions named on their own ground: one set for the close
              framing, handing over to one for the whole road at the end. */}
          {regionTags.map((t, i) => {
            const opacity = t.wide
              ? wideTagOpacity
              : detail * (t.atPass ? peakIn : 1);
            if (opacity <= 0) return null;
            const p = project(camera, t.x, t.y);
            return (
              <div
                key={i}
                style={{
                  ...mapLabelStyle,
                  position: "absolute",
                  left: p.left,
                  top: p.top,
                  transform: "translate(-50%, -50%)",
                  opacity: opacity * 0.85,
                  color: "#6b5f47",
                  fontSize: 30,
                  letterSpacing: 5,
                }}
              >
                {t.name}
              </div>
            );
          })}

          {/* The summit above the pass: a landmark, not a stop. */}
          {peakOpacity > 0 && (
            <div
              style={{
                position: "absolute",
                left: peak.left,
                top: peak.top,
                opacity: peakOpacity,
                transform: "translate(-50%, -50%)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
              }}
            >
              <svg width={34} height={30} viewBox="0 0 34 30">
                <path
                  d="M17 2 L32 28 L2 28 Z"
                  fill="#6b5f47"
                  stroke="#faf6ec"
                  strokeWidth={3}
                  strokeLinejoin="round"
                />
              </svg>
              <div
                style={{
                  ...mapLabelStyle,
                  position: "absolute",
                  top: 34,
                  textAlign: "center",
                  color: "#4a4033",
                  fontSize: 28,
                  lineHeight: 1.1,
                }}
              >
                <div>MONTE PENICE</div>
                <div style={{ color: "#6b5f47", fontSize: 24 }}>
                  {MONTE_PENICE.elevation.toLocaleString("it-IT")} m
                </div>
              </div>
            </div>
          )}

          <TravelDot
            points={climb.points}
            camera={camera}
            frame={frame}
            range={CLIMB}
            color={ROUTE_RED}
          />
          <TravelDot
            points={descent.points}
            camera={camera}
            frame={frame}
            range={DESCENT}
            color={ROUTE_RED}
          />

          <AbsoluteFill style={{ opacity: detail }}>
            {SHIELDS.map((s) => (
              <RoadShield
                key={s.road.id}
                camera={camera}
                frame={frame}
                points={s.road.points}
                at={s.at}
                dx={s.dx}
                dy={s.dy}
                revealFrame={frameAt(s.range, s.at)}
                label="SS461"
                color={ROUTE_RED}
              />
            ))}
          </AbsoluteFill>

          {/* Where the last film ended, and this one starts. */}
          <PinMarker
            waypoint={bobbio}
            camera={camera}
            frame={frame}
            {...BOBBIO_PIN}
            labelDx={-100}
            labelDy={18}
            labelSize={42}
            labelWidth={260}
            showElevation
            elevationLocale="it-IT"
            pinScale={0.62}
          />

          {/* The subject of the film: a bigger pin, landing as the line tops out. */}
          <PinMarker
            waypoint={penice}
            camera={camera}
            frame={frame}
            {...pinCue(CLIMB[1])}
            labelDx={0}
            labelDy={-230}
            labelSize={54}
            labelWidth={420}
            showElevation
            elevationLocale="it-IT"
            pinScale={0.9}
          />

          <PinMarker
            waypoint={varzi}
            camera={camera}
            frame={frame}
            {...pinCue(DESCENT[1])}
            labelDx={40}
            labelDy={18}
            labelSize={46}
            labelWidth={260}
            showElevation
            elevationLocale="it-IT"
            pinScale={0.62}
          />

          {/* The closing card, under the whole road once it is all in frame. */}
          {summaryOpacity > 0 && (
            <div
              style={{
                position: "absolute",
                left: SAFE_RECT.x,
                width: SAFE_RECT.w,
                top: SUMMARY_TOP,
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                gap: 22,
                opacity: summaryOpacity,
                transform: `translateY(${summaryRise}px)`,
              }}
            >
              <div
                style={{
                  padding: "8px 20px",
                  borderRadius: 12,
                  background: ROUTE_RED,
                  border: "5px solid #faf6ec",
                  boxShadow: "0 3px 8px rgba(0,0,0,0.25)",
                  color: "#ffffff",
                  fontWeight: 800,
                  fontSize: 46,
                  letterSpacing: 1,
                }}
              >
                SS461
              </div>
              <div style={{ ...mapLabelStyle, fontSize: 56 }}>
                {KM_TOTAL} km
              </div>
            </div>
          )}
        </AbsoluteFill>
      </AbsoluteFill>

      <GrainOverlay />
    </AbsoluteFill>
  );
};
