import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { OltrepoMap } from "./OltrepoMap";
import { OltrepoTitle } from "./OltrepoTitle";
import { ElevationProfile } from "./ElevationProfile";
import { useOltrepoCamera } from "./useOltrepoCamera";
import { RoutePath } from "../shared/RoutePath";
import { PinMarker } from "../shared/PinMarker";
import { WaypointTick } from "../shared/WaypointTick";
import { TravelDot } from "../shared/TravelDot";
import { fontFamily } from "../shared/fonts";
import { mapLabelStyle } from "../shared/labelStyle";
import { ROUTE_BLUE, ROUTE_RED } from "../shared/palette";
import { SAFE_RECT, SAFE_TITLE_TOP } from "../shared/safeArea";
import { landmarks, places, provinceLabels, roadLegs } from "./geoData";
import {
  CASALE_ARRIVAL,
  CHIAPPO_DROP,
  CHIAPPO_FADE,
  CHIAPPO_LABEL,
  COMUNI,
  GIOVA_ARRIVAL,
  PATCHWORK,
  PROV_DROP_START,
  PROV_DROP_STEP,
  PROV_FADE,
  PROV_LABEL_DELAY,
  ROAD_SALITA,
  ROAD_VALLE,
  ZOOM_ROUTE,
  arrivalFrame,
  pinCue,
} from "./timeline";

const placeById = (id: string) => places.find((p) => p.id === id)!;
const legById = (id: string) => roadLegs.find((l) => l.id === id)!;

const PASS_PIN_SCALE = 0.62;

// A name for something that is not a place: the valley the road climbs.
// Parked in screen space, clear of the line.
const MapNote: React.FC<{
  frame: number;
  revealFrame: number;
  left: number;
  top: number;
  width: number;
  lines: string[];
}> = ({ frame, revealFrame, left, top, width, lines }) => {
  const opacity = interpolate(frame, [revealFrame, revealFrame + 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
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
        color: "#6b5f47",
        fontSize: 34,
        letterSpacing: 4,
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

  // The map gains a level at each step down: the four provinces take their
  // colour, then the comuni the road runs through come up inside them.
  const patchworkOpacity = ramp(PATCHWORK);
  // Held short of opaque on purpose: the comuni are pale tiles, and letting
  // the province colour under them show through keeps the valley inside
  // Pavia and the far side of the ridge inside Piacenza, which a
  // full-strength patchwork of 171 comuni loses completely.
  const comuneOpacity = ramp(COMUNI) * 0.62;

  const dropFrame = (index: number) => PROV_DROP_START + index * PROV_DROP_STEP;

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
          <OltrepoMap
            scale={camera.scale}
            patchworkOpacity={patchworkOpacity}
            comuneOpacity={comuneOpacity}
          />
          {/* Blue along the river, red up the climb: the two halves of the
              ride read apart at a glance, and Casale Staffora is where the
              gradient changes from 4.5% to 12%. */}
          <RoutePath
            d={legValle.d}
            frame={frame}
            range={ROAD_VALLE}
            color={ROUTE_BLUE}
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
          color={ROUTE_BLUE}
        />
        <TravelDot
          points={legSalita.points}
          camera={camera}
          frame={frame}
          range={ROAD_SALITA}
          color={ROUTE_RED}
        />

        {/* Le Quattro Province: Pavia, Alessandria, Piacenza and Genova. The
            first three meet on the Monte Chiappo at the head of this valley;
            Genova stops 8 km short of it, so the four are a region with a
            name rather than a point on a map. */}
        {provinceLabels.map((prov, i) => (
          <PinMarker
            key={prov.id}
            waypoint={prov}
            camera={camera}
            frame={frame}
            dropRange={[dropFrame(i), dropFrame(i) + 24]}
            labelRange={[
              dropFrame(i) + PROV_LABEL_DELAY,
              dropFrame(i) + PROV_LABEL_DELAY + 14,
            ]}
            labelDy={14}
            labelSize={38}
            pinScale={0.55}
            fadeRange={PROV_FADE}
          />
        ))}

        {/* The head of the valley: where the Staffora starts and where three
            of the four provinces meet. */}
        <PinMarker
          waypoint={landmarks[0]}
          camera={camera}
          frame={frame}
          dropRange={CHIAPPO_DROP}
          labelRange={CHIAPPO_LABEL}
          labelDx={190}
          labelDy={-50}
          labelSize={40}
          labelWidth={280}
          showElevation
          elevationLocale="it-IT"
          pinScale={0.62}
          fadeRange={CHIAPPO_FADE}
        />

        <MapNote
          frame={frame}
          revealFrame={ZOOM_ROUTE[1] + 10}
          left={230}
          top={520}
          width={280}
          lines={["VAL", "STAFFORA"]}
        />

        {/* Up the Staffora, every place on the road named. The valley is 3 km
            wide and 14 km long, so the names take turns either side of the
            line rather than stacking on one flank. */}
        <WaypointTick
          waypoint={varzi}
          camera={camera}
          frame={frame}
          revealFrame={ROAD_VALLE[0]}
          showLabel
          color={ROUTE_BLUE}
          labelDx={-165}
          labelDy={14}
          showElevation
          elevationLocale="it-IT"
        />
        <WaypointTick
          waypoint={casanova}
          camera={camera}
          frame={frame}
          revealFrame={arrivalFrame("casanova")}
          showLabel
          color={ROUTE_BLUE}
          labelDx={205}
          labelDy={0}
          labelWidth={300}
          showElevation
          elevationLocale="it-IT"
        />
        <WaypointTick
          waypoint={smargh}
          camera={camera}
          frame={frame}
          revealFrame={arrivalFrame("smargh")}
          showLabel
          color={ROUTE_BLUE}
          labelDx={-225}
          labelDy={10}
          labelWidth={340}
          showElevation
          elevationLocale="it-IT"
        />
        <WaypointTick
          waypoint={casale}
          camera={camera}
          frame={frame}
          revealFrame={CASALE_ARRIVAL}
          showLabel
          color={ROUTE_RED}
          labelDx={205}
          labelDy={-10}
          labelWidth={290}
          showElevation
          elevationLocale="it-IT"
        />
        <WaypointTick
          waypoint={poggio}
          camera={camera}
          frame={frame}
          revealFrame={arrivalFrame("poggio")}
          showLabel
          color={ROUTE_RED}
          labelDx={-195}
          labelDy={6}
          labelWidth={290}
          showElevation
          elevationLocale="it-IT"
        />

        {/* Where the road is going. */}
        <PinMarker
          waypoint={giova}
          camera={camera}
          frame={frame}
          {...pinCue(GIOVA_ARRIVAL)}
          labelDx={175}
          labelDy={-105}
          labelSize={42}
          labelWidth={280}
          showElevation
          elevationLocale="it-IT"
          pinScale={PASS_PIN_SCALE}
        />

        <ElevationProfile frame={frame} />

        <OltrepoTitle frame={frame} top={SAFE_TITLE_TOP} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
