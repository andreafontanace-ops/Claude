import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { useBralloCamera } from "./useBralloCamera";
import { CrossOut } from "./CrossOut";
import { RoadShield } from "./RoadShield";
import { RoutePath } from "../shared/RoutePath";
import { PinMarker } from "../shared/PinMarker";
import { WaypointTick } from "../shared/WaypointTick";
import { TravelDot } from "../shared/TravelDot";
import { GrainOverlay } from "../shared/GrainOverlay";
import { RegionMap } from "../shared/RegionMap";
import { fontFamily } from "../shared/fonts";
import { ROUTE_BLUE, ROUTE_RED } from "../shared/palette";
import { SAFE_RECT } from "../shared/safeArea";
import { beyond, comuni, home, places, roads, X_POINT } from "./geoData";
import {
  BRALLO_PIN,
  CROSS_OUT,
  GIOVA_PIN,
  INTRO_FADE_IN,
  ROAD_CRINALE,
  ROAD_FACILE,
  SHIELD_AT,
  arrivalFrame,
  pinCue,
  roadFrameAt,
} from "./timeline";

const placeById = (id: string) => places.find((p) => p.id === id)!;
const roadById = (id: string) => roads.find((r) => r.id === id)!;

export const GiovaBrallo: React.FC = () => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const camera = useBralloCamera(frame, SAFE_RECT);

  const giova = placeById("giova");
  const poggio = placeById("poggio");
  const colletta = placeById("colletta");
  const brallo = placeById("brallo");

  const facile = roadById("facile");
  const crinale = roadById("crinale");

  const introOpacity = interpolate(frame, INTRO_FADE_IN, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

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
            {/* Held short of opaque, as in the Val Staffora film: the region
                colour under the pale comuni keeps each side of the watershed
                readable. */}
            <RegionMap
              home={home}
              beyond={beyond}
              comuni={comuni}
              scale={camera.scale}
              comuneOpacity={0.62}
              borderOpacity={1}
            />
            {/* The easy road in blue, so the red X lands on something it
                contrasts with; the ridge road in the red the series uses for
                the road that was actually ridden. */}
            <RoutePath
              d={facile.d}
              frame={frame}
              range={ROAD_FACILE}
              color={ROUTE_BLUE}
              width={13 / camera.scale}
            />
            <RoutePath
              d={crinale.d}
              frame={frame}
              range={ROAD_CRINALE}
              color={ROUTE_RED}
              width={14 / camera.scale}
            />
          </g>
        </svg>

        <AbsoluteFill style={{ fontFamily }}>
          <TravelDot
            points={facile.points}
            camera={camera}
            frame={frame}
            range={ROAD_FACILE}
            color={ROUTE_BLUE}
          />
          <TravelDot
            points={crinale.points}
            camera={camera}
            frame={frame}
            range={ROAD_CRINALE}
            color={ROUTE_RED}
          />

          {/* Where both roads start. */}
          <PinMarker
            waypoint={giova}
            camera={camera}
            frame={frame}
            {...GIOVA_PIN}
            labelDx={0}
            labelDy={18}
            labelSize={42}
            labelWidth={280}
            showElevation
            elevationLocale="it-IT"
            pinScale={0.62}
          />

          {/* The one name on the easy road. It passes several villages, left
              unnamed on purpose; Pian del Poggio is how the road is known. */}
          <WaypointTick
            waypoint={poggio}
            camera={camera}
            frame={frame}
            revealFrame={arrivalFrame("facile", "poggio")}
            showLabel
            color={ROUTE_BLUE}
            labelDx={-74}
            labelDy={-60}
            labelWidth={190}
          />

          {/* Where both roads end, named as soon as the first one gets there. */}
          <PinMarker
            waypoint={brallo}
            camera={camera}
            frame={frame}
            {...BRALLO_PIN}
            labelDx={-60}
            labelDy={-200}
            labelSize={42}
            labelWidth={260}
            showElevation
            elevationLocale="it-IT"
            pinScale={0.62}
          />

          {/* Road numbers as the route screenshots label them: the easy road
              is the SP131 for most of its length (the SP48 before Pian del
              Poggio), the hard one the SP88. The easy road is the western of
              the two, so its plate goes west; the hard road's goes east. */}
          <RoadShield
            camera={camera}
            frame={frame}
            points={facile.points}
            at={SHIELD_AT.facile}
            dx={-100}
            revealFrame={roadFrameAt("facile", SHIELD_AT.facile)}
            label="SP131"
            color={ROUTE_BLUE}
          />
          <RoadShield
            camera={camera}
            frame={frame}
            points={crinale.points}
            at={SHIELD_AT.crinale}
            dx={88}
            revealFrame={roadFrameAt("crinale", SHIELD_AT.crinale)}
            label="SP88"
            color={ROUTE_RED}
          />

          <CrossOut
            camera={camera}
            frame={frame}
            x={X_POINT.x}
            y={X_POINT.y}
            range={CROSS_OUT}
          />

          {/* The hard road's landmark, cued off the red line as it passes. */}
          <PinMarker
            waypoint={colletta}
            camera={camera}
            frame={frame}
            {...pinCue(arrivalFrame("crinale", "colletta"))}
            labelDx={185}
            labelDy={-60}
            labelSize={42}
            labelWidth={280}
            showElevation
            elevationLocale="it-IT"
            pinScale={0.62}
          />

        </AbsoluteFill>
      </AbsoluteFill>

      <GrainOverlay />
    </AbsoluteFill>
  );
};
