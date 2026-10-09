import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { useTrebeccoCamera } from "./useTrebeccoCamera";
import { RoutePath } from "../shared/RoutePath";
import { PinMarker } from "../shared/PinMarker";
import { TravelDot } from "../shared/TravelDot";
import { GrainOverlay } from "../shared/GrainOverlay";
import { RegionMap } from "../shared/RegionMap";
import { RoadShield } from "../shared/RoadShield";
import { MapName } from "../shared/MapName";
import { Camera, project } from "../shared/camera";
import { smoothPath, subPolyline } from "../shared/polyline";
import { fontFamily } from "../shared/fonts";
import { mapLabelStyle } from "../shared/labelStyle";
import { ROUTE_RED } from "../shared/palette";
import { SAFE_RECT } from "../shared/safeArea";
import {
  along,
  beyond,
  CASTLE,
  comuni,
  GRAVEL_AT,
  home,
  KM_TOTAL,
  LAKE_LABEL,
  lakes,
  leg1,
  leg2,
  PASS_ELEVATION,
  places,
  regionNames,
  regionTags,
  rivers,
  roadNet,
  TARGET,
} from "./geoData";
import {
  CASTLE_SHOW,
  CASTLE_OUT,
  LAKE_IN,
  LEG1,
  LEG2,
  MAP_DETAIL_IN,
  REGION_NAMES_OUT,
  REGION_TAGS_IN,
  SUMMARY_IN,
  TARGET_OUT,
  VARZI_PIN,
  frameAt,
  pinCue,
} from "./timeline";

const placeById = (id: string) => places.find((p) => p.id === id)!;
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// The white road's colour: the plate and the dashes on the line.
const GRAVEL = "#d8c39a";
const GRAVEL_INK = "#4a3b22";
const WATER = "#a9cfe8";
const WATER_EDGE = "#78a9cc";

const ROAD_WIDTH: Record<string, number> = {
  primary: 3.6,
  secondary: 3,
  tertiary: 2.2,
};

// The second leg's white road: cream dashes over the red line, from where the
// asphalt gives out to wherever the line has got to.
const GravelDashes: React.FC<{
  points: readonly (readonly [number, number])[];
  frame: number;
  range: readonly [number, number];
  from: number;
  scale: number;
}> = ({ points, frame, range, from, scale }) => {
  const p = interpolate(frame, range, [0, 1], {
    ...clamp,
    easing: Easing.inOut(Easing.cubic),
  });
  if (p <= from) return null;
  return (
    <path
      d={smoothPath(subPolyline(points, from, p))}
      fill="none"
      stroke={GRAVEL}
      strokeWidth={5 / scale}
      strokeLinecap="butt"
      strokeLinejoin="round"
      strokeDasharray={`${12 / scale} ${10 / scale}`}
    />
  );
};

// A village or the pass, named as the line reaches it: a small dot on the
// road and the name to one side of it.
const AlongTick: React.FC<{
  camera: Camera;
  frame: number;
  x: number;
  y: number;
  name: string;
  sub?: string;
  side: number;
  revealFrame: number;
}> = ({ camera, frame, x, y, name, sub, side, revealFrame }) => {
  const opacity = interpolate(
    frame,
    [revealFrame, revealFrame + 12],
    [0, 1],
    clamp,
  );
  if (opacity <= 0) return null;
  const pop = interpolate(
    frame,
    [revealFrame, revealFrame + 8, revealFrame + 14],
    [0, 1.4, 1],
    clamp,
  );
  const { left, top } = project(camera, x, y);
  return (
    <div
      style={{ position: "absolute", left, top, width: 0, height: 0, opacity }}
    >
      <div
        style={{
          position: "absolute",
          width: 16,
          height: 16,
          borderRadius: "50%",
          background: "#faf6ec",
          border: `4px solid ${ROUTE_RED}`,
          transform: `translate(-50%, -50%) scale(${pop})`,
        }}
      />
      <div
        style={{
          ...mapLabelStyle,
          position: "absolute",
          top: 0,
          [side > 0 ? "left" : "right"]: 20,
          transform: "translateY(-50%)",
          textAlign: side > 0 ? "left" : "right",
          fontSize: 30,
          lineHeight: 1.1,
          color: "#3a3326",
        }}
      >
        <div>{name}</div>
        {sub ? (
          <div style={{ fontSize: 24, color: "#6b5f47" }}>{sub}</div>
        ) : null}
      </div>
    </div>
  );
};

const CastleGlyph: React.FC<{ size: number }> = ({ size }) => (
  <svg width={size} height={size} viewBox="0 0 64 64">
    <path
      d="M6 58V30h6v-6h6v6h6V18h-4v-8h6v4h4v-4h4v4h4v-4h6v8h-4v12h6v-6h6v6h6v28H38V46a6 6 0 0 0-12 0v12Z"
      fill="#7a5c3e"
      stroke="#faf6ec"
      strokeWidth={3}
      strokeLinejoin="round"
    />
  </svg>
);

export const VarziTrebecco: React.FC = () => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const camera = useTrebeccoCamera(frame, SAFE_RECT);
  const s = camera.scale;

  const varzi = placeById("varzi");
  const zavattarello = placeById("zavattarello");
  const trebecco = placeById("trebecco");

  const detail = interpolate(frame, MAP_DETAIL_IN, [0, 1], clamp);
  const castleOpacity =
    interpolate(frame, CASTLE_SHOW, [0, 1], clamp) *
    interpolate(frame, [CASTLE_OUT[0] + 4, CASTLE_OUT[0] + 16], [1, 0], clamp);
  const castlePop = interpolate(
    frame,
    [CASTLE_SHOW[0], CASTLE_SHOW[0] + 8, CASTLE_SHOW[0] + 16],
    [0.5, 1.15, 1],
    clamp,
  );
  const castle = project(camera, CASTLE.x, CASTLE.y);
  const lakeOpacity = interpolate(frame, LAKE_IN, [0, 1], clamp);
  const lake = project(camera, LAKE_LABEL.x, LAKE_LABEL.y);
  const target = project(camera, TARGET.x, TARGET.y);
  const targetOpacity = interpolate(frame, TARGET_OUT, [1, 0], clamp);
  const ring = (frame % 30) / 30;
  const summaryOpacity = interpolate(frame, SUMMARY_IN, [0, 1], clamp);
  const summaryRise = interpolate(frame, SUMMARY_IN, [16, 0], clamp);

  const legRange = (leg: string) => (leg === "leg1" ? LEG1 : LEG2);

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
        <g transform={`translate(${camera.tx},${camera.ty}) scale(${s})`}>
          <RegionMap
            home={home}
            beyond={beyond}
            comuni={comuni}
            scale={s}
            comuneOpacity={0.62 * detail}
            borderOpacity={1}
          />

          {/* The map under the road: torrents, the lake, the main roads. */}
          <g opacity={detail}>
            {rivers.map((d, i) => (
              <path
                key={`r${i}`}
                d={d}
                fill="none"
                stroke={WATER_EDGE}
                strokeWidth={2.6 / s}
                strokeLinecap="round"
              />
            ))}
            {lakes.map((d, i) => (
              <path
                key={`l${i}`}
                d={d}
                fill={WATER}
                stroke={WATER_EDGE}
                strokeWidth={2 / s}
              />
            ))}
            {roadNet.map((r, i) => (
              <path
                key={`c${i}`}
                d={r.d}
                fill="none"
                stroke="#b3a68c"
                strokeWidth={(ROAD_WIDTH[r.cls] + 2.4) / s}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            ))}
            {roadNet.map((r, i) => (
              <path
                key={`w${i}`}
                d={r.d}
                fill="none"
                stroke="#fffdf6"
                strokeWidth={ROAD_WIDTH[r.cls] / s}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            ))}
          </g>

          <RoutePath
            d={leg1.d}
            points={leg1.points}
            frame={frame}
            range={LEG1}
            color={ROUTE_RED}
            width={14 / s}
          />
          <RoutePath
            d={leg2.d}
            points={leg2.points}
            frame={frame}
            range={LEG2}
            color={ROUTE_RED}
            width={14 / s}
          />
          <GravelDashes
            points={leg2.points}
            frame={frame}
            range={LEG2}
            from={GRAVEL_AT}
            scale={s}
          />
        </g>
      </svg>

      <AbsoluteFill style={{ fontFamily }}>
        {/* The opening: the four regions, the road a speck between them. */}
        {regionNames.map((r) => (
          <MapName
            key={r.name}
            camera={camera}
            frame={frame}
            x={r.x}
            y={r.y}
            lines={[r.name]}
            revealFrame={-18}
            fadeRange={REGION_NAMES_OUT}
            width={460}
            size={40}
          />
        ))}
        {/* Close up, the two the road runs between. */}
        {regionTags.map((r) => (
          <MapName
            key={`tag-${r.lines[0]}`}
            camera={camera}
            frame={frame}
            x={r.x}
            y={r.y}
            lines={r.lines}
            revealFrame={REGION_TAGS_IN[0]}
            revealFrames={REGION_TAGS_IN[1] - REGION_TAGS_IN[0]}
            width={420}
            size={28}
          />
        ))}

        {/* Where the opening zoom is headed, while the road is a speck. */}
        {targetOpacity > 0 && (
          <div
            style={{
              position: "absolute",
              left: target.left,
              top: target.top,
              opacity: targetOpacity,
            }}
          >
            <div
              style={{
                position: "absolute",
                width: 34,
                height: 34,
                borderRadius: "50%",
                background: ROUTE_RED,
                border: "5px solid #faf6ec",
                transform: "translate(-50%, -50%)",
                boxShadow: "0 3px 8px rgba(0,0,0,0.3)",
              }}
            />
            <div
              style={{
                position: "absolute",
                width: 120,
                height: 120,
                borderRadius: "50%",
                border: `6px solid ${ROUTE_RED}`,
                transform: `translate(-50%, -50%) scale(${0.3 + ring})`,
                opacity: 1 - ring,
              }}
            />
          </div>
        )}

        {lakeOpacity > 0 && (
          <div
            style={{
              ...mapLabelStyle,
              position: "absolute",
              // Left of the lake: Trebecco's name and pin crowd its right.
              left: lake.left - 90,
              top: lake.top,
              transform: "translate(-50%, -50%)",
              opacity: lakeOpacity,
              fontSize: 26,
              fontStyle: "italic",
              fontWeight: 700,
              color: "#2f6f99",
              textAlign: "center",
              lineHeight: 1.1,
              whiteSpace: "normal",
              width: 160,
            }}
          >
            {LAKE_LABEL.name}
          </div>
        )}

        <TravelDot
          points={leg1.points}
          camera={camera}
          frame={frame}
          range={LEG1}
          color={ROUTE_RED}
        />
        <TravelDot
          points={leg2.points}
          camera={camera}
          frame={frame}
          range={LEG2}
          color={ROUTE_RED}
        />

        {along.map((a) => (
          <AlongTick
            key={a.name}
            camera={camera}
            frame={frame}
            x={a.x}
            y={a.y}
            name={a.name}
            sub={a.name.startsWith("Passo") ? `${PASS_ELEVATION} m` : undefined}
            side={a.side}
            revealFrame={frameAt(legRange(a.leg), a.at)}
          />
        ))}

        <RoadShield
          camera={camera}
          frame={frame}
          points={leg1.points}
          at={0.66}
          dx={-70}
          dy={0}
          revealFrame={frameAt(LEG1, 0.66)}
          label="SP207"
          color={ROUTE_RED}
        />
        <AbsoluteFill
          style={{
            opacity: interpolate(
              frame,
              [
                frameAt(LEG2, GRAVEL_AT + 0.05),
                frameAt(LEG2, GRAVEL_AT + 0.05) + 12,
              ],
              [0, 1],
              clamp,
            ),
          }}
        >
          <RoadShield
            camera={camera}
            frame={frame}
            points={leg2.points}
            at={GRAVEL_AT}
            dx={70}
            dy={95}
            revealFrame={frameAt(LEG2, GRAVEL_AT + 0.05)}
            label="STRADA BIANCA"
            color={GRAVEL}
            textColor={GRAVEL_INK}
          />
        </AbsoluteFill>

        <PinMarker
          waypoint={varzi}
          camera={camera}
          frame={frame}
          {...VARZI_PIN}
          labelDx={0}
          labelDy={18}
          labelSize={42}
          labelWidth={260}
          pinScale={0.62}
        />
        <PinMarker
          waypoint={zavattarello}
          camera={camera}
          frame={frame}
          {...pinCue(LEG1[1])}
          labelDx={-150}
          labelDy={-20}
          labelSize={44}
          labelWidth={340}
          pinScale={0.7}
        />

        {/* The castle, while the camera is in close on it. */}
        {castleOpacity > 0 && (
          <div
            style={{
              position: "absolute",
              left: castle.left,
              top: castle.top,
              opacity: castleOpacity,
              transform: `translate(-50%, -100%) scale(${castlePop})`,
              transformOrigin: "50% 100%",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              filter: "drop-shadow(0 4px 8px rgba(0,0,0,0.3))",
            }}
          >
            <div
              style={{
                ...mapLabelStyle,
                fontSize: 40,
                color: "#5a4128",
                marginBottom: 6,
              }}
            >
              {CASTLE.name}
            </div>
            <CastleGlyph size={96} />
          </div>
        )}

        <PinMarker
          waypoint={trebecco}
          camera={camera}
          frame={frame}
          {...pinCue(LEG2[1])}
          labelDx={-30}
          labelDy={-150}
          labelSize={46}
          labelWidth={300}
          pinScale={0.7}
        />

        {/* The closing card: the two kinds of road, and how far. */}
        {summaryOpacity > 0 && (
          <div
            style={{
              position: "absolute",
              left: SAFE_RECT.x,
              width: SAFE_RECT.w,
              top: 1360,
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              gap: 18,
              opacity: summaryOpacity,
              transform: `translateY(${summaryRise}px)`,
              fontWeight: 800,
            }}
          >
            <div
              style={{
                padding: "8px 18px",
                borderRadius: 12,
                background: ROUTE_RED,
                border: "5px solid #faf6ec",
                color: "#fff",
                fontSize: 40,
              }}
            >
              SP207
            </div>
            <div style={{ ...mapLabelStyle, fontSize: 44 }}>+</div>
            <div
              style={{
                padding: "8px 18px",
                borderRadius: 12,
                background: GRAVEL,
                border: "5px solid #faf6ec",
                color: GRAVEL_INK,
                fontSize: 40,
              }}
            >
              STRADA BIANCA
            </div>
            <div style={{ ...mapLabelStyle, fontSize: 52 }}>{KM_TOTAL} km</div>
          </div>
        )}
      </AbsoluteFill>

      <GrainOverlay />
    </AbsoluteFill>
  );
};
