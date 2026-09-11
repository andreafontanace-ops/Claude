import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { AlpineMap } from "./AlpineMap";
import { BorderLine } from "./BorderLine";
import { MonginevroTitle } from "./MonginevroTitle";
import { useMonginevroCamera } from "./useMonginevroCamera";
import { RoutePath } from "../shared/RoutePath";
import { PinMarker } from "../shared/PinMarker";
import { WaypointTick } from "../shared/WaypointTick";
import { TravelDot } from "../shared/TravelDot";
import { project } from "../shared/camera";
import { fontFamily } from "../shared/fonts";
import { mapLabelStyle } from "../shared/labelStyle";
import { ROUTE_RED } from "../shared/palette";
import { SAFE_RECT, SAFE_TITLE_TOP } from "../shared/safeArea";
import { BORDER_POINT, passes, places, roadLegs } from "./geoData";
import {
  BORDER,
  BRIANCON_LABEL,
  CESANA_LABEL,
  CLAVIERE_LABEL,
  COL_PIN_DROP,
  COL_PIN_LABEL,
  PASS_DROP_START,
  PASS_DROP_STEP,
  PASS_FADE,
  PASS_LABEL_DELAY,
  ROAD_FRANCIA,
  ROAD_ITALIA,
  ZOOM_ROUTE,
} from "./timeline";

const placeById = (id: string) => places.find((p) => p.id === id)!;
const legById = (id: string) => roadLegs.find((l) => l.id === id)!;

const PASS_PIN_SCALE = 0.75;
const PASS_LABEL_SIZE = 40;

export const Monginevro: React.FC = () => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const camera = useMonginevroCamera(frame, SAFE_RECT);

  const cesana = placeById("cesana");
  const claviere = placeById("claviere");
  const col = placeById("col");
  const briancon = placeById("briancon");

  const legItalia = legById("italia");
  const legFrancia = legById("francia");

  const communeOpacity = interpolate(
    frame,
    [ZOOM_ROUTE[0] + 12, ZOOM_ROUTE[0] + 36],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  // The two country names sit either side of the frontier, in screen space so
  // they keep their size: Italy is the east side of this border, France the
  // west.
  const borderAt = project(camera, BORDER_POINT.x, BORDER_POINT.y);
  const countryOpacity = interpolate(frame, [BORDER[0] + 8, BORDER[0] + 26], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const countryStyle: React.CSSProperties = {
    ...mapLabelStyle,
    position: "absolute",
    top: borderAt.top - 430,
    fontSize: 46,
    color: "#3d3527",
    opacity: countryOpacity,
    transform: "translate(-50%, 0)",
  };

  const dropFrame = (index: number) => PASS_DROP_START + index * PASS_DROP_STEP;

  return (
    <AbsoluteFill
      style={{ background: "linear-gradient(180deg, #f7f2e6 0%, #f2ebd9 100%)" }}
    >
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        style={{ position: "absolute", top: 0, left: 0 }}
      >
        <g transform={`translate(${camera.tx},${camera.ty}) scale(${camera.scale})`}>
          <AlpineMap scale={camera.scale} communeOpacity={communeOpacity} />
          <BorderLine frame={frame} range={BORDER} scale={camera.scale} />
          <RoutePath
            d={legItalia.d}
            frame={frame}
            range={ROAD_ITALIA}
            color={ROUTE_RED}
            width={15 / camera.scale}
          />
          <RoutePath
            d={legFrancia.d}
            frame={frame}
            range={ROAD_FRANCIA}
            color={ROUTE_RED}
            width={15 / camera.scale}
          />
        </g>
      </svg>

      <AbsoluteFill style={{ fontFamily }}>
        <TravelDot
          points={legItalia.points}
          camera={camera}
          frame={frame}
          range={ROAD_ITALIA}
          color={ROUTE_RED}
        />
        <TravelDot
          points={legFrancia.points}
          camera={camera}
          frame={frame}
          range={ROAD_FRANCIA}
          color={ROUTE_RED}
        />

        {/* The great Italy-France crossings, north to south. */}
        {passes.map((pass, i) => (
          <PinMarker
            key={pass.id}
            waypoint={pass}
            camera={camera}
            frame={frame}
            dropRange={[dropFrame(i), dropFrame(i) + 26]}
            labelRange={[
              dropFrame(i) + PASS_LABEL_DELAY,
              dropFrame(i) + PASS_LABEL_DELAY + 14,
            ]}
            labelDy={16}
            labelSize={PASS_LABEL_SIZE}
            showElevation
            elevationLocale="it-IT"
            pinScale={PASS_PIN_SCALE}
            fadeRange={PASS_FADE}
          />
        ))}

        {countryOpacity > 0 && (
          <>
            <div style={{ ...countryStyle, left: borderAt.left + 300 }}>ITALIA</div>
            <div style={{ ...countryStyle, left: borderAt.left - 300 }}>FRANCIA</div>
          </>
        )}

        {/* The road runs east to west, so the names take turns above and
            below it rather than stacking on one side. */}
        <WaypointTick
          waypoint={cesana}
          camera={camera}
          frame={frame}
          revealFrame={CESANA_LABEL}
          showLabel
          color={ROUTE_RED}
          labelDx={10}
          labelDy={-116}
          labelWidth={300}
        />
        <WaypointTick
          waypoint={claviere}
          camera={camera}
          frame={frame}
          revealFrame={CLAVIERE_LABEL}
          showLabel
          color={ROUTE_RED}
          labelDx={60}
          labelDy={96}
        />
        <WaypointTick
          waypoint={briancon}
          camera={camera}
          frame={frame}
          revealFrame={BRIANCON_LABEL}
          showLabel
          color={ROUTE_RED}
          labelDx={-10}
          labelDy={100}
        />

        {/* The subject, dropped into the gap the other passes left. */}
        <PinMarker
          waypoint={col}
          camera={camera}
          frame={frame}
          dropRange={COL_PIN_DROP}
          labelRange={COL_PIN_LABEL}
          labelDx={-230}
          labelDy={-250}
          labelSize={46}
          labelWidth={380}
          showElevation
          elevationLocale="it-IT"
        />

        <MonginevroTitle frame={frame} top={SAFE_TITLE_TOP} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
