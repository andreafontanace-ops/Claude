import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { useBobbioCamera } from "./useBobbioCamera";
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
import { beyond, comuni, home, places, road, shields, TREBBIA } from "./geoData";
import {
  BRALLO_PIN,
  INTRO_FADE_IN,
  ROAD,
  VAL_TREBBIA,
  pinCue,
  roadFrameAt,
} from "./timeline";

const placeById = (id: string) => places.find((p) => p.id === id)!;

// Where each plate sits relative to its point on the road, in screen pixels:
// the SP69 above the long eastward stretch, the SS461 below the last one,
// clear of Bobbio's name above it.
const SHIELD_OFFSET: Record<string, { dx: number; dy: number }> = {
  SP69: { dx: 0, dy: -62 },
  SS461: { dx: -48, dy: 78 },
};

export const BralloBobbio: React.FC = () => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const camera = useBobbioCamera(frame, SAFE_RECT);

  const brallo = placeById("brallo");
  const bobbio = placeById("bobbio");

  const introOpacity = interpolate(frame, INTRO_FADE_IN, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const trebbiaOpacity = interpolate(frame, VAL_TREBBIA, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const trebbia = project(camera, TREBBIA.x, TREBBIA.y);

  return (
    <AbsoluteFill
      style={{ background: "linear-gradient(180deg, #f7f2e6 0%, #f2ebd9 100%)" }}
    >
      <AbsoluteFill style={{ opacity: introOpacity }}>
        <svg
          width={width}
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          style={{ position: "absolute", top: 0, left: 0 }}
        >
          <g transform={`translate(${camera.tx},${camera.ty}) scale(${camera.scale})`}>
            <RegionMap
              home={home}
              beyond={beyond}
              comuni={comuni}
              scale={camera.scale}
              comuneOpacity={0.62}
              borderOpacity={1}
            />
            <RoutePath
              d={road.d}
              frame={frame}
              range={ROAD}
              color={ROUTE_RED}
              width={14 / camera.scale}
            />
          </g>
        </svg>

        <AbsoluteFill style={{ fontFamily }}>
          <TravelDot
            points={road.points}
            camera={camera}
            frame={frame}
            range={ROAD}
            color={ROUTE_RED}
          />

          {/* Where the last film ended, and this one starts. */}
          <PinMarker
            waypoint={brallo}
            camera={camera}
            frame={frame}
            {...BRALLO_PIN}
            labelDx={70}
            labelDy={18}
            labelSize={42}
            labelWidth={280}
            showElevation
            elevationLocale="it-IT"
            pinScale={0.62}
          />

          {/* Road numbers as the route screenshot labels them, each shown as
              the drawn line reaches its stretch. */}
          {shields.map((s) => (
            <RoadShield
              key={s.label}
              camera={camera}
              frame={frame}
              points={road.points}
              at={s.at}
              dx={SHIELD_OFFSET[s.label]?.dx ?? 0}
              dy={SHIELD_OFFSET[s.label]?.dy ?? -60}
              revealFrame={roadFrameAt(s.at)}
              label={s.label}
              color={ROUTE_RED}
            />
          ))}

          <PinMarker
            waypoint={bobbio}
            camera={camera}
            frame={frame}
            {...pinCue(ROAD[1])}
            labelDx={-40}
            labelDy={-160}
            labelSize={46}
            labelWidth={280}
            showElevation
            elevationLocale="it-IT"
            pinScale={0.62}
          />

          {/* The valley Bobbio sits in, named once the road has reached it. */}
          {trebbiaOpacity > 0 && (
            <div
              style={{
                ...mapLabelStyle,
                position: "absolute",
                left: trebbia.left - 30,
                top: trebbia.top + 78,
                width: 260,
                opacity: trebbiaOpacity,
                transform: "translate(-50%, -50%)",
                textAlign: "center",
                whiteSpace: "normal",
                lineHeight: 1.15,
                color: "#4a4033",
                fontSize: 34,
                letterSpacing: 3,
              }}
            >
              <div>VAL</div>
              <div>TREBBIA</div>
            </div>
          )}
        </AbsoluteFill>
      </AbsoluteFill>

      <GrainOverlay />
    </AbsoluteFill>
  );
};
