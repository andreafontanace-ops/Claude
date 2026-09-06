import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { FranceMap } from "./FranceMap";
import { VarsTitle } from "./VarsTitle";
import { useVarsCamera } from "./useVarsCamera";
import { RoutePath } from "../shared/RoutePath";
import { PinMarker } from "../shared/PinMarker";
import { WaypointTick } from "../shared/WaypointTick";
import { TravelDot } from "../shared/TravelDot";
import { fontFamily } from "../shared/fonts";
import { ROUTE_RED } from "../shared/palette";
import { SAFE_RECT, SAFE_TITLE_TOP } from "../shared/safeArea";
import { passes, places, varsRoad } from "./geoData";
import {
  GUILLESTRE_LABEL,
  PASS_DROP_START,
  PASS_DROP_STEP,
  PASS_FADE,
  PASS_LABEL_DELAY,
  ROAD_DRAW,
  SAINTPAUL_LABEL,
  ZOOM_VARS,
} from "./timeline";

const placeById = (id: string) => places.find((p) => p.id === id)!;

// How the secondary pass markers are sized on the Route des Grandes Alpes
// frame: small enough that six of them fit without crowding.
const PASS_PIN_SCALE = 0.75;
const PASS_LABEL_SIZE = 40;

export const ColDeVars: React.FC = () => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  // Everything is composed inside the platform-safe rect, so nothing that
  // matters ends up under the action rail or the caption block.
  const camera = useVarsCamera(frame, SAFE_RECT);

  const guillestre = placeById("guillestre");
  const col = placeById("vars");
  const saintpaul = placeById("saintpaul");

  // The Col de Vars pin arrives as one of six, then grows into the subject
  // of the film as the camera comes down onto it.
  const heroT = interpolate(frame, ZOOM_VARS, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const heroScale = PASS_PIN_SCALE + (1 - PASS_PIN_SCALE) * heroT;
  const heroLabelSize = PASS_LABEL_SIZE + (54 - PASS_LABEL_SIZE) * heroT;
  // Its name starts centred under the pin and slides off to the west, which
  // is the only side of the pass the road does not run through.
  const heroLabelDx = -245 * heroT;
  const heroLabelDy = 20 - 100 * heroT;

  // The commune patchwork only exists for the two Alpine departments, so it
  // arrives with the final push-in rather than being on from the start.
  const communeOpacity = interpolate(frame, [ZOOM_VARS[0] + 12, ZOOM_VARS[0] + 36], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const dropFrame = (index: number) => PASS_DROP_START + index * PASS_DROP_STEP;

  return (
    <AbsoluteFill
      style={{
        background: "linear-gradient(180deg, #f7f2e6 0%, #f2ebd9 100%)",
      }}
    >
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        style={{ position: "absolute", top: 0, left: 0 }}
      >
        <g transform={`translate(${camera.tx},${camera.ty}) scale(${camera.scale})`}>
          <FranceMap scale={camera.scale} communeOpacity={communeOpacity} />
          <RoutePath
            d={varsRoad.d}
            frame={frame}
            range={ROAD_DRAW}
            color={ROUTE_RED}
            width={15 / camera.scale}
          />
        </g>
      </svg>

      <AbsoluteFill style={{ fontFamily }}>
        <TravelDot
          points={varsRoad.points}
          camera={camera}
          frame={frame}
          range={ROAD_DRAW}
          color={ROUTE_RED}
        />

        {/* The Route des Grandes Alpes, north to south. All but the Col de
            Vars step back out once the eye has run down the line. */}
        {passes.map((pass, i) =>
          pass.id === "vars" ? null : (
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
          ),
        )}

        <WaypointTick
          waypoint={guillestre}
          camera={camera}
          frame={frame}
          revealFrame={GUILLESTRE_LABEL}
          showLabel
          color={ROUTE_RED}
          labelDx={-10}
          labelDy={-64}
        />
        <WaypointTick
          waypoint={saintpaul}
          camera={camera}
          frame={frame}
          revealFrame={SAINTPAUL_LABEL}
          showLabel
          color={ROUTE_RED}
          labelDx={-6}
          labelDy={96}
          labelWidth={420}
        />

        {/* The subject: dropped with the others, kept when they go. */}
        <PinMarker
          waypoint={col}
          camera={camera}
          frame={frame}
          dropRange={[dropFrame(3), dropFrame(3) + 26]}
          labelRange={[
            dropFrame(3) + PASS_LABEL_DELAY,
            dropFrame(3) + PASS_LABEL_DELAY + 14,
          ]}
          labelDx={heroLabelDx}
          labelDy={heroLabelDy}
          labelSize={heroLabelSize}
          showElevation
          elevationLocale="it-IT"
          pinScale={heroScale}
        />

        <VarsTitle frame={frame} top={SAFE_TITLE_TOP} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
