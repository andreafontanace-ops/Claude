import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { OltrepoMap } from "./OltrepoMap";
import { useOltrepoCamera } from "./useOltrepoCamera";
import { RoutePath } from "../shared/RoutePath";
import { PinMarker } from "../shared/PinMarker";
import { WaypointTick } from "../shared/WaypointTick";
import { TravelDot } from "../shared/TravelDot";
import { GrainOverlay } from "../shared/GrainOverlay";
import { Camera, project } from "../shared/camera";
import { fontFamily } from "../shared/fonts";
import { mapLabelStyle } from "../shared/labelStyle";
import { Waypoint } from "../shared/types";
import { ROUTE_RED } from "../shared/palette";
import { SAFE_RECT } from "../shared/safeArea";
import { places, regionLabels, roadLegs } from "./geoData";
import {
  BORDERS,
  CASALE_ARRIVAL,
  COMUNI,
  GIOVA_ARRIVAL,
  INTRO_FADE_IN,
  REGION_FADE,
  REGION_LABEL_REVEAL,
  REGION_LABEL_START,
  REGION_LABEL_STEP,
  ROAD_SALITA,
  ROAD_VALLE,
  ZOOM_ROUTE,
  arrivalFrame,
  pinCue,
} from "./timeline";

const placeById = (id: string) => places.find((p) => p.id === id)!;
const legById = (id: string) => roadLegs.find((l) => l.id === id)!;

// A name with no marker under it: a region, or the valley itself. Anchored in
// map units so it travels with the camera, but set in screen pixels so it
// keeps its size while the camera drops.
const MapName: React.FC<{
  camera: Camera;
  frame: number;
  x: number;
  y: number;
  lines: string[];
  revealFrame: number;
  revealFrames?: number;
  fadeRange?: readonly [number, number];
  width?: number;
  size?: number;
}> = ({
  camera,
  frame,
  x,
  y,
  lines,
  revealFrame,
  revealFrames = 18,
  fadeRange,
  width = 300,
  size = 40,
}) => {
  const { left, top } = project(camera, x, y);

  const reveal = interpolate(frame, [revealFrame, revealFrame + revealFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fade = fadeRange
    ? interpolate(frame, fadeRange, [1, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 1;
  const opacity = Math.min(reveal, fade);
  if (opacity <= 0) return null;

  return (
    <div
      style={{
        ...mapLabelStyle,
        position: "absolute",
        left,
        top,
        width,
        opacity,
        transform: "translate(-50%, -50%)",
        textAlign: "center",
        whiteSpace: "normal",
        lineHeight: 1.15,
        color: "#4a4033",
        fontSize: size,
        letterSpacing: 3,
      }}
    >
      {lines.map((line) => (
        <div key={line}>{line}</div>
      ))}
    </div>
  );
};

export const ValStaffora: React.FC = () => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const camera = useOltrepoCamera(frame, SAFE_RECT);

  const varzi = placeById("varzi");
  const casanova = placeById("casanova");
  const smargh = placeById("smargh");
  const casale = placeById("casale");
  const poggio = placeById("poggio");
  const giova = placeById("giova");

  const legValle = legById("valle");
  const legSalita = legById("salita");

  const ramp = (range: readonly [number, number]) =>
    interpolate(frame, range, [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });

  const introOpacity = ramp(INTRO_FADE_IN);
  const borderOpacity = ramp(BORDERS);
  // Held short of opaque on purpose: the comuni are pale tiles, and letting
  // the region colour under them show through keeps the valley on the
  // Lombardia side of the watershed and the far slope on the other.
  const comuneOpacity = ramp(COMUNI) * 0.62;

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
            <OltrepoMap
              scale={camera.scale}
              comuneOpacity={comuneOpacity}
              borderOpacity={borderOpacity}
            />
            {/* One colour the whole way. The split at Casale Staffora is
                still there, but it only buys pacing now: above it the road
                goes from 4.5% to 12%, and it is drawn at 60% of the valley's
                speed so the climb gets the time it deserves. */}
            <RoutePath
              d={legValle.d}
              frame={frame}
              range={ROAD_VALLE}
              color={ROUTE_RED}
              width={14 / camera.scale}
            />
            <RoutePath
              d={legSalita.d}
              frame={frame}
              range={ROAD_SALITA}
              color={ROUTE_RED}
              width={14 / camera.scale}
            />
          </g>
        </svg>

        <AbsoluteFill style={{ fontFamily }}>
          <TravelDot
            points={legValle.points}
            camera={camera}
            frame={frame}
            range={ROAD_VALLE}
            color={ROUTE_RED}
          />
          <TravelDot
            points={legSalita.points}
            camera={camera}
            frame={frame}
            range={ROAD_SALITA}
            color={ROUTE_RED}
          />

          {/* The four regions that meet over this valley, named one after
              another while the lines between them are still in frame. */}
          {regionLabels.map((region: Waypoint, i) => (
            <MapName
              key={region.id}
              camera={camera}
              frame={frame}
              x={region.x}
              y={region.y}
              lines={[region.name]}
              revealFrame={REGION_LABEL_START + i * REGION_LABEL_STEP}
              revealFrames={REGION_LABEL_REVEAL}
              fadeRange={REGION_FADE}
              width={420}
              size={38}
            />
          ))}

          {/* Three names on the road: where it starts, the middle of the
              valley, and where it is going. At 3.4s of drawing, a name per
              village arrives faster than it can be read - Casanova, Casale and
              Pian del Poggio keep their dots, which mark the same real
              coordinates without asking to be read. */}
          <WaypointTick
            waypoint={varzi}
            camera={camera}
            frame={frame}
            revealFrame={ROAD_VALLE[0]}
            showLabel
            color={ROUTE_RED}
            labelDx={-150}
            labelDy={18}
            showElevation
            elevationLocale="it-IT"
          />
          <WaypointTick
            waypoint={casanova}
            camera={camera}
            frame={frame}
            revealFrame={arrivalFrame("casanova")}
            color={ROUTE_RED}
          />
          <WaypointTick
            waypoint={smargh}
            camera={camera}
            frame={frame}
            revealFrame={arrivalFrame("smargh")}
            showLabel
            color={ROUTE_RED}
            labelDx={-240}
            labelDy={16}
            labelWidth={340}
            showElevation
            elevationLocale="it-IT"
          />
          <WaypointTick
            waypoint={casale}
            camera={camera}
            frame={frame}
            revealFrame={CASALE_ARRIVAL}
            color={ROUTE_RED}
          />
          <WaypointTick
            waypoint={poggio}
            camera={camera}
            frame={frame}
            revealFrame={arrivalFrame("poggio")}
            color={ROUTE_RED}
          />

          {/* Where the road is going. */}
          <PinMarker
            waypoint={giova}
            camera={camera}
            frame={frame}
            {...pinCue(GIOVA_ARRIVAL)}
            labelDx={165}
            labelDy={-95}
            labelSize={42}
            labelWidth={260}
            showElevation
            elevationLocale="it-IT"
            pinScale={0.62}
          />

          {/* The valley the road climbs, named once the camera is down on
              it. East of the line, not west: the far side of the frame is
              already Piemonte, and the Staffora is not in it. */}
          <MapName
            camera={camera}
            frame={frame}
            x={varzi.x + 19}
            y={varzi.y + 10}
            lines={["VAL", "STAFFORA"]}
            revealFrame={ZOOM_ROUTE[1] + 6}
            width={280}
            size={34}
          />
        </AbsoluteFill>
      </AbsoluteFill>

      {/* Last, over everything: the paper the map is printed on. */}
      <GrainOverlay />
    </AbsoluteFill>
  );
};
