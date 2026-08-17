import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { SwitzerlandMap } from "./SwitzerlandMap";
import { RoutePath } from "./RoutePath";
import { PinMarker } from "./PinMarker";
import { WaypointTick } from "./WaypointTick";
import { TravelDot } from "./TravelDot";
import { TitleCard } from "./TitleCard";
import { FinalCard } from "./FinalCard";
import { ArrivalPulse } from "./ArrivalPulse";
import { useCamera } from "./useCamera";
import { fontFamily } from "./fonts";
import { routeSegments, waypoints } from "./geoData";
import { PIN_DROP, PIN_LABEL, ROUTE_A, ROUTE_B } from "./timeline";

const byId = (id: string) => waypoints.find((w) => w.id === id)!;

export const SwissAlpsTour: React.FC = () => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const camera = useCamera(frame, width, height);

  const segAirolo = routeSegments[0];
  const segFurka = routeSegments[1];

  const nufenen = byId("nufenen");
  const airolo = byId("airolo");
  const gotthard = byId("gotthard");
  const andermatt = byId("andermatt");
  const furka = byId("furka");
  const oberwald = byId("oberwald");
  const ulrichen = byId("ulrichen");

  return (
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(120% 120% at 50% 0%, #16233d 0%, #0a1120 60%, #060a14 100%)",
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
          <RoutePath d={segAirolo.d} frame={frame} range={ROUTE_A} />
          <RoutePath d={segFurka.d} frame={frame} range={ROUTE_B} />
        </g>
      </svg>

      <AbsoluteFill style={{ fontFamily }}>
        <TravelDot
          points={segAirolo.points}
          camera={camera}
          frame={frame}
          range={ROUTE_A}
        />
        <TravelDot
          points={segFurka.points}
          camera={camera}
          frame={frame}
          range={ROUTE_B}
        />

        <WaypointTick
          waypoint={airolo}
          camera={camera}
          frame={frame}
          revealFrame={ROUTE_A[0]}
          showLabel
        />
        <WaypointTick
          waypoint={gotthard}
          camera={camera}
          frame={frame}
          revealFrame={284}
          showLabel
        />
        <WaypointTick
          waypoint={andermatt}
          camera={camera}
          frame={frame}
          revealFrame={311}
        />
        <WaypointTick
          waypoint={furka}
          camera={camera}
          frame={frame}
          revealFrame={ROUTE_A[1]}
          showLabel
        />
        <WaypointTick
          waypoint={oberwald}
          camera={camera}
          frame={frame}
          revealFrame={402}
        />
        <WaypointTick
          waypoint={ulrichen}
          camera={camera}
          frame={frame}
          revealFrame={427}
        />

        <PinMarker
          waypoint={nufenen}
          camera={camera}
          frame={frame}
          dropRange={PIN_DROP}
          labelRange={PIN_LABEL}
        />
        <ArrivalPulse
          waypoint={nufenen}
          camera={camera}
          frame={frame}
          triggerFrame={ROUTE_B[1]}
        />

        <TitleCard frame={frame} />
        <FinalCard frame={frame} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
