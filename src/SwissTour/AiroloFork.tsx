import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { SwitzerlandMap } from "./SwitzerlandMap";
import { RoutePath } from "./RoutePath";
import { PinMarker } from "./PinMarker";
import { WaypointTick } from "./WaypointTick";
import { TravelDot } from "./TravelDot";
import { TitleCard } from "./TitleCard";
import { MassifArea } from "./MassifArea";
import { PeakMarker } from "./PeakMarker";
import { useCamera, project } from "./useCamera";
import { fontFamily } from "./fonts";
import { mapLabelStyle } from "./labelStyle";
import { ROUTE_BLUE, ROUTE_RED } from "./palette";
import {
  forkBranches,
  FORK_BBOX,
  MASSIF_CENTER,
  peaks,
  waypoints,
} from "./geoData";
import { SAFE_RECT, SAFE_TITLE_TOP } from "./safeArea";
import {
  FORK_PIN_DROP,
  FORK_PIN_LABEL,
  MASSIF_AREA,
  MASSIF_LABEL,
  OUTBOUND,
  PEAK_LUCENDRO,
  PEAK_ROTONDO,
} from "./forkTimeline";

const byId = (id: string) => waypoints.find((w) => w.id === id)!;
const peakById = (id: string) => peaks.find((p) => p.id === id)!;
const branchById = (id: string) => forkBranches.find((b) => b.id === id)!;

// Where each branch is, as a fraction of its own length, when it reaches a
// given place - measured off the real geometry by scripts/geo/build_route.py.
const at = (range: readonly [number, number], fraction: number) =>
  Math.round(range[0] + (range[1] - range[0]) * fraction);

export const AiroloFork: React.FC = () => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  // Composed inside the platform-safe rect, not the whole frame, so nothing
  // that matters ends up under the action rail or the caption block.
  const camera = useCamera(frame, width, height, FORK_BBOX, SAFE_RECT);

  const north = branchById("gottardo-furka");
  const novena = branchById("novena");

  const airolo = byId("airolo");
  const gotthard = byId("gotthard");
  const andermatt = byId("andermatt");
  const furka = byId("furka");
  const oberwald = byId("oberwald");
  const ulrichen = byId("ulrichen");
  const nufenen = byId("nufenen");
  const allacqua = byId("allacqua");
  const bedretto = byId("bedretto");

  const massifLabel = project(camera, MASSIF_CENTER.x, MASSIF_CENTER.y);
  const massifLabelOpacity = interpolate(frame, MASSIF_LABEL, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const massifLabelRise = interpolate(frame, MASSIF_LABEL, [14, 0], {
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
          <MassifArea frame={frame} range={MASSIF_AREA} />
          <RoutePath
            d={north.d}
            frame={frame}
            range={OUTBOUND}
            color={ROUTE_BLUE}
          />
          <RoutePath
            d={novena.d}
            frame={frame}
            range={OUTBOUND}
            color={ROUTE_RED}
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

        {/* Gotthard / Furka branch - only the pass carries a name. */}
        <WaypointTick
          waypoint={gotthard}
          camera={camera}
          frame={frame}
          revealFrame={at(OUTBOUND, 0.284)}
          color={ROUTE_BLUE}
        />
        <WaypointTick
          waypoint={andermatt}
          camera={camera}
          frame={frame}
          revealFrame={at(OUTBOUND, 0.438)}
          color={ROUTE_BLUE}
        />
        <WaypointTick
          waypoint={furka}
          camera={camera}
          frame={frame}
          revealFrame={at(OUTBOUND, 0.794)}
          showLabel
          showElevation
          color={ROUTE_BLUE}
          labelDx={-95}
          labelDy={-72}
        />
        <WaypointTick
          waypoint={oberwald}
          camera={camera}
          frame={frame}
          revealFrame={at(OUTBOUND, 0.908)}
          color={ROUTE_BLUE}
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
          showElevation
          color={ROUTE_RED}
          labelDx={30}
          labelDy={126}
        />

        {/* Where both branches land, so it belongs to neither colour. */}
        <WaypointTick
          waypoint={ulrichen}
          camera={camera}
          frame={frame}
          revealFrame={OUTBOUND[1]}
          showLabel
          color="#231f16"
          labelDx={18}
          labelDy={74}
        />

        <PeakMarker
          peak={peakById("rotondo")}
          camera={camera}
          frame={frame}
          revealFrame={PEAK_ROTONDO}
          labelDy={36}
        />
        <PeakMarker
          peak={peakById("lucendro")}
          camera={camera}
          frame={frame}
          revealFrame={PEAK_LUCENDRO}
          labelDy={36}
        />

        {/* Caption sits in the empty map above the massif rather than on top
            of it, which leaves the shaded area to the two summit markers. */}
        <div
          style={{
            position: "absolute",
            left: massifLabel.left,
            top: massifLabel.top - 360,
            width: 560,
            transform: `translate(-50%, -100%) translateY(${massifLabelRise}px)`,
            opacity: massifLabelOpacity,
            textAlign: "center",
          }}
        >
          <div
            style={{
              ...mapLabelStyle,
              fontSize: 44,
              color: "#3d3527",
              whiteSpace: "normal",
              lineHeight: 1.1,
            }}
          >
            MASSICCIO DEL GOTTARDO
          </div>
          <div style={{ ...mapLabelStyle, fontSize: 31, color: "#6b5f47" }}>
            Pizzo Rotondo &middot; 3192 m
          </div>
        </div>

        {/* The start: both roads leave from under this pin. */}
        <PinMarker
          waypoint={airolo}
          camera={camera}
          frame={frame}
          dropRange={FORK_PIN_DROP}
          labelRange={FORK_PIN_LABEL}
          labelDy={72}
        />

        <TitleCard frame={frame} subtitle={null} top={SAFE_TITLE_TOP} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
