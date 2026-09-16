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
  ROAD_CRINALE,
  ROAD_VALLE,
  ZOOM_ROUTE,
  arrivalFrame,
  pinCue,
} from "./timeline";

const placeById = (id: string) => places.find((p) => p.id === id)!;
const legById = (id: string) => roadLegs.find((l) => l.id === id)!;

const PASS_PIN_SCALE = 0.62;
const PASS_LABEL_SIZE = 42;

// A name for something that is not a place: the valley the first leg climbs,
// the road the second one rides. Parked in screen space, clear of the line.
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
  const colletta = placeById("colletta");
  const brallopass = placeById("brallopass");
  const brallo = placeById("brallo");

  const legValle = legById("valle");
  const legCrinale = legById("crinale");

  const ramp = (range: readonly [number, number]) =>
    interpolate(frame, range, [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });

  // The map gains a level at each step down: the four regions open into the
  // four provinces, the provinces into the comuni the road runs through.
  const patchworkOpacity = ramp(PATCHWORK);
  // Held short of opaque on purpose: the comuni are pale tiles, and letting
  // the province colour under them show through keeps the road inside Pavia
  // and the far side of the ridge inside Piacenza, which a full-strength
  // patchwork of 171 comuni loses completely.
  const comuneOpacity = ramp(COMUNI) * 0.62;

  const dropFrame = (index: number) => PROV_DROP_START + index * PROV_DROP_STEP;

  const collettaArrival = arrivalFrame("colletta");
  const brallopassArrival = arrivalFrame("brallopass");

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
          {/* Blue up the valley, red along the ridge: the two halves of the
              ride read apart at a glance, and the pass is where it changes. */}
          <RoutePath
            d={legValle.d}
            frame={frame}
            range={ROAD_VALLE}
            color={ROUTE_BLUE}
            width={14 / camera.scale}
          />
          <RoutePath
            d={legCrinale.d}
            frame={frame}
            range={ROAD_CRINALE}
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
          points={legCrinale.points}
          camera={camera}
          frame={frame}
          range={ROAD_CRINALE}
          color={ROUTE_RED}
        />

        {/* Le Quattro Province: Pavia, Alessandria, Piacenza and Genova, whose
            four boundaries meet on the Monte Chiappo at the head of this
            valley. The road is the ridge between them. */}
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

        {/* The head of the valley, and the point the whole ride is organised
            around: Pavia, Alessandria and Piacenza meet on this summit. */}
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
          left={245}
          top={560}
          width={280}
          lines={["VAL", "STAFFORA"]}
        />
        <MapNote
          frame={frame}
          revealFrame={collettaArrival}
          left={775}
          top={762}
          width={250}
          lines={["SP88", "CRINALE"]}
        />

        {/* Up the Staffora. Only the places the road actually passes through
            get a name; the rest are ticks, so the valley reads as a sequence
            without the names fighting each other. */}
        <WaypointTick
          waypoint={varzi}
          camera={camera}
          frame={frame}
          revealFrame={ROAD_VALLE[0]}
          showLabel
          color={ROUTE_BLUE}
          labelDx={160}
          labelDy={-30}
          showElevation
          elevationLocale="it-IT"
        />
        <WaypointTick
          waypoint={casanova}
          camera={camera}
          frame={frame}
          revealFrame={arrivalFrame("casanova")}
          color={ROUTE_BLUE}
        />
        <WaypointTick
          waypoint={smargh}
          camera={camera}
          frame={frame}
          revealFrame={arrivalFrame("smargh")}
          showLabel
          color={ROUTE_BLUE}
          labelDx={-195}
          labelDy={14}
          labelWidth={320}
        />
        <WaypointTick
          waypoint={casale}
          camera={camera}
          frame={frame}
          revealFrame={arrivalFrame("casale")}
          color={ROUTE_BLUE}
        />
        {/* Pian del Poggio is a tick without a name: the Giova, the Colletta
            and the Brallo all land within 400px of it, and a fourth name in
            that corner is the one that makes the other three unreadable. */}
        <WaypointTick
          waypoint={poggio}
          camera={camera}
          frame={frame}
          revealFrame={arrivalFrame("poggio")}
          color={ROUTE_BLUE}
        />

        {/* The three high points, in the order the road takes them. */}
        <PinMarker
          waypoint={giova}
          camera={camera}
          frame={frame}
          {...pinCue(GIOVA_ARRIVAL)}
          labelDx={-185}
          labelDy={-55}
          labelSize={PASS_LABEL_SIZE}
          labelWidth={280}
          showElevation
          elevationLocale="it-IT"
          pinScale={PASS_PIN_SCALE}
        />
        <PinMarker
          waypoint={colletta}
          camera={camera}
          frame={frame}
          {...pinCue(collettaArrival)}
          labelDx={195}
          labelDy={-60}
          labelSize={PASS_LABEL_SIZE}
          labelWidth={280}
          showElevation
          elevationLocale="it-IT"
          pinScale={PASS_PIN_SCALE}
        />
        <PinMarker
          waypoint={brallopass}
          camera={camera}
          frame={frame}
          {...pinCue(brallopassArrival)}
          labelDx={-10}
          labelDy={-190}
          labelSize={PASS_LABEL_SIZE}
          labelWidth={300}
          showElevation
          elevationLocale="it-IT"
          pinScale={PASS_PIN_SCALE}
        />
        <WaypointTick
          waypoint={brallo}
          camera={camera}
          frame={frame}
          revealFrame={ROAD_CRINALE[1]}
          showLabel
          color={ROUTE_RED}
          labelDx={80}
          labelDy={62}
          labelWidth={250}
        />

        <ElevationProfile frame={frame} />

        <OltrepoTitle frame={frame} top={SAFE_TITLE_TOP} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
