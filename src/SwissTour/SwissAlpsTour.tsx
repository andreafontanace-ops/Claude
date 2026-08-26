import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { SwitzerlandMap } from "./SwitzerlandMap";
import { RoutePath } from "./RoutePath";
import { PinMarker } from "./PinMarker";
import { WaypointTick } from "./WaypointTick";
import { TravelDot } from "./TravelDot";
import { TitleCard } from "./TitleCard";
import { ArrivalPulse } from "./ArrivalPulse";
import { useCamera } from "./useCamera";
import { fontFamily } from "./fonts";
import { ROUTE_BLUE, ROUTE_RED } from "./palette";
import { routeSegments, waypoints } from "./geoData";
import { PIN_DROP, ROUTE_A, ROUTE_B, ROUTE_C } from "./timeline";

const byId = (id: string) => waypoints.find((w) => w.id === id)!;

export const SwissAlpsTour: React.FC = () => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const camera = useCamera(frame, width, height);

  const segAirolo = routeSegments[0];
  const segFurka = routeSegments[1];
  const segBedretto = routeSegments[2];

  const nufenen = byId("nufenen");
  const airolo = byId("airolo");
  const gotthard = byId("gotthard");
  const andermatt = byId("andermatt");
  const furka = byId("furka");
  const oberwald = byId("oberwald");
  const ulrichen = byId("ulrichen");
  const allacqua = byId("allacqua");
  const bedretto = byId("bedretto");

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
          <SwitzerlandMap />
          <RoutePath d={segAirolo.d} frame={frame} range={ROUTE_A} color={ROUTE_BLUE} />
          <RoutePath d={segFurka.d} frame={frame} range={ROUTE_B} color={ROUTE_RED} />
          <RoutePath d={segBedretto.d} frame={frame} range={ROUTE_C} color={ROUTE_RED} />
        </g>
      </svg>

      <AbsoluteFill style={{ fontFamily }}>
        <TravelDot
          points={segAirolo.points}
          camera={camera}
          frame={frame}
          range={ROUTE_A}
          color={ROUTE_BLUE}
        />
        <TravelDot
          points={segFurka.points}
          camera={camera}
          frame={frame}
          range={ROUTE_B}
          color={ROUTE_RED}
        />
        <TravelDot
          points={segBedretto.points}
          camera={camera}
          frame={frame}
          range={ROUTE_C}
          color={ROUTE_RED}
        />

        <WaypointTick
          waypoint={airolo}
          camera={camera}
          frame={frame}
          revealFrame={ROUTE_A[0]}
          color={ROUTE_BLUE}
        />
        <WaypointTick
          waypoint={gotthard}
          camera={camera}
          frame={frame}
          revealFrame={144}
          showLabel
          color={ROUTE_BLUE}
          labelSide="above"
        />
        <WaypointTick
          waypoint={andermatt}
          camera={camera}
          frame={frame}
          revealFrame={156}
          color={ROUTE_BLUE}
        />
        <WaypointTick
          waypoint={furka}
          camera={camera}
          frame={frame}
          revealFrame={ROUTE_A[1]}
          color={ROUTE_BLUE}
        />
        <WaypointTick
          waypoint={oberwald}
          camera={camera}
          frame={frame}
          revealFrame={197}
          color={ROUTE_RED}
        />
        <WaypointTick
          waypoint={ulrichen}
          camera={camera}
          frame={frame}
          revealFrame={206}
          color={ROUTE_RED}
        />
        <WaypointTick
          waypoint={allacqua}
          camera={camera}
          frame={frame}
          revealFrame={241}
          color={ROUTE_RED}
        />
        <WaypointTick
          waypoint={bedretto}
          camera={camera}
          frame={frame}
          revealFrame={247}
          color={ROUTE_RED}
        />

        <PinMarker
          waypoint={nufenen}
          camera={camera}
          frame={frame}
          dropRange={PIN_DROP}
        />
        <ArrivalPulse
          waypoint={nufenen}
          camera={camera}
          frame={frame}
          triggerFrame={ROUTE_B[1]}
        />

        <TitleCard frame={frame} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
