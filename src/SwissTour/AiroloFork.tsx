import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { SwitzerlandMap } from "./SwitzerlandMap";
import { RoutePath } from "./RoutePath";
import { PinMarker } from "./PinMarker";
import { WaypointTick } from "./WaypointTick";
import { TravelDot } from "./TravelDot";
import { TitleCard } from "./TitleCard";
import { useCamera } from "./useCamera";
import { fontFamily } from "./fonts";
import { ROUTE_BLUE, ROUTE_RED } from "./palette";
import { forkBranches, FORK_BBOX, waypoints } from "./geoData";
import {
  FORK_PIN_DROP,
  FORK_PIN_LABEL,
  GHOST_FADE,
  GOMS_LINK,
  OUTBOUND,
  RETURN,
} from "./forkTimeline";

const byId = (id: string) => waypoints.find((w) => w.id === id)!;
const branchById = (id: string) => forkBranches.find((b) => b.id === id)!;

const LINK_COLOR = "#8a7a52";

// Where each branch is, as a fraction of its own length, when it reaches a
// given place - measured off the real geometry by scripts/geo/build_route.py.
const at = (range: readonly [number, number], fraction: number) =>
  Math.round(range[0] + (range[1] - range[0]) * fraction);

export const AiroloFork: React.FC = () => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const camera = useCamera(frame, width, height, FORK_BBOX);

  const north = branchById("gottardo-furka");
  const novena = branchById("novena");
  const link = branchById("goms-link");

  const airolo = byId("airolo");
  const gotthard = byId("gotthard");
  const andermatt = byId("andermatt");
  const furka = byId("furka");
  const oberwald = byId("oberwald");
  const ulrichen = byId("ulrichen");
  const nufenen = byId("nufenen");
  const allacqua = byId("allacqua");
  const bedretto = byId("bedretto");

  // Once both branches are drawn they fade to a faint trace, so the return
  // leg has something to redraw over rather than landing on an identical line.
  const outboundOpacity = interpolate(frame, GHOST_FADE, [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const ghostOpacity = interpolate(frame, GHOST_FADE, [0, 0.22], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

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

          <RoutePath
            d={link.d}
            frame={frame}
            range={GOMS_LINK}
            color={LINK_COLOR}
            width={2.4}
          />

          <RoutePath
            d={north.d}
            frame={frame}
            range={OUTBOUND}
            color={ROUTE_BLUE}
            opacity={outboundOpacity}
          />
          <RoutePath
            d={novena.d}
            frame={frame}
            range={OUTBOUND}
            color={ROUTE_RED}
            opacity={outboundOpacity}
          />

          {/* faint trace of both roads, left behind for the return leg */}
          <RoutePath
            d={north.d}
            frame={frame}
            range={GHOST_FADE}
            color={ROUTE_BLUE}
            opacity={ghostOpacity}
          />
          <RoutePath
            d={novena.d}
            frame={frame}
            range={GHOST_FADE}
            color={ROUTE_RED}
            opacity={ghostOpacity}
          />

          <RoutePath
            d={north.d}
            frame={frame}
            range={RETURN}
            color={ROUTE_BLUE}
            reverse
          />
          <RoutePath
            d={novena.d}
            frame={frame}
            range={RETURN}
            color={ROUTE_RED}
            reverse
          />
        </g>
      </svg>

      <AbsoluteFill style={{ fontFamily }}>
        <TravelDot
          points={north.points}
          camera={camera}
          frame={frame}
          range={OUTBOUND}
          color={ROUTE_BLUE}
        />
        <TravelDot
          points={novena.points}
          camera={camera}
          frame={frame}
          range={OUTBOUND}
          color={ROUTE_RED}
        />
        <TravelDot
          points={north.points}
          camera={camera}
          frame={frame}
          range={RETURN}
          color={ROUTE_BLUE}
          reverse
        />
        <TravelDot
          points={novena.points}
          camera={camera}
          frame={frame}
          range={RETURN}
          color={ROUTE_RED}
          reverse
        />

        {/* Gotthard / Furka branch */}
        <WaypointTick
          waypoint={gotthard}
          camera={camera}
          frame={frame}
          revealFrame={at(OUTBOUND, 0.313)}
          showLabel
          color={ROUTE_BLUE}
          labelDx={-165}
          labelDy={-40}
          labelWidth={280}
        />
        <WaypointTick
          waypoint={andermatt}
          camera={camera}
          frame={frame}
          revealFrame={at(OUTBOUND, 0.482)}
          color={ROUTE_BLUE}
        />
        <WaypointTick
          waypoint={furka}
          camera={camera}
          frame={frame}
          revealFrame={at(OUTBOUND, 0.874)}
          showLabel
          color={ROUTE_BLUE}
          labelDx={-95}
          labelDy={-62}
        />
        <WaypointTick
          waypoint={oberwald}
          camera={camera}
          frame={frame}
          revealFrame={OUTBOUND[1]}
          showLabel
          color={ROUTE_BLUE}
          labelDx={-118}
          labelDy={-12}
        />

        {/* Novena branch */}
        <WaypointTick
          waypoint={bedretto}
          camera={camera}
          frame={frame}
          revealFrame={at(OUTBOUND, 0.241)}
          color={ROUTE_RED}
        />
        <WaypointTick
          waypoint={allacqua}
          camera={camera}
          frame={frame}
          revealFrame={at(OUTBOUND, 0.347)}
          color={ROUTE_RED}
        />
        <WaypointTick
          waypoint={nufenen}
          camera={camera}
          frame={frame}
          revealFrame={at(OUTBOUND, 0.66)}
          showLabel
          color={ROUTE_RED}
          labelDx={0}
          labelDy={86}
        />
        <WaypointTick
          waypoint={ulrichen}
          camera={camera}
          frame={frame}
          revealFrame={OUTBOUND[1]}
          showLabel
          color={ROUTE_RED}
          labelDx={-30}
          labelDy={62}
        />

        {/* The start: both roads leave from under this pin. */}
        <PinMarker
          waypoint={airolo}
          camera={camera}
          frame={frame}
          dropRange={FORK_PIN_DROP}
          labelRange={FORK_PIN_LABEL}
          labelDy={72}
        />

        <TitleCard frame={frame} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
