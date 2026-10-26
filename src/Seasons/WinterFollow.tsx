import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  random,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {
  clamp,
  DISPLAY,
  MONO,
  PLATE,
  scramble,
  SEASON_COLOR,
  SeasonIcon,
  slashPoly,
  slashX,
  useSeasonFonts,
  WHITE,
} from "./theme";

// Winter, the secret stage: a transparent 1080x1920 overlay, 5s, to close
// the video. The same plate as the season cards, snow falling across it:
// TAPPA 4 DI 4, INVERNO, SEGUIMI PER SCOPRIRLO, and a follow button that gets
// tapped and turns to SEGUITO. Inside the safe area.
export const WINTER_FOLLOW_DURATION = 150;

const ICE = SEASON_COLOR.INVERNO;
const SLASH_IN = [0, 14] as const;
const SNOW_IN = [6, 30] as const;
const ICON_IN = [12, 30] as const;
const STEP_IN = [14, 34] as const;
const TITLE_IN = 16;
const CTA_IN = 30;
const BUTTON_IN = 44;
const TAP = 92;
const SLASH_OUT = [132, 148] as const;

const X0 = 60;
const X1 = 900;
const TOP = 600;
const BOTTOM = 1340;
const LEAN = 70;
const LEAN_PER_PX = LEAN / (BOTTOM - TOP);
const PLATE_POLY = `${X0 + LEAN},${TOP} ${X1},${TOP} ${X1 - LEAN},${BOTTOM} ${X0},${BOTTOM}`;

export const WinterFollow: React.FC = () => {
  useSeasonFonts();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (frame >= SLASH_OUT[1]) return <AbsoluteFill />;

  const inX = slashX(frame, SLASH_IN);
  const outX = slashX(frame, SLASH_OUT);
  const lean = LEAN + 40;
  const reveal =
    frame < SLASH_IN[1]
      ? `polygon(-200px -200px, ${inX - 40 + lean}px -200px, ${inX - 40 + lean}px ${TOP - 40}px, ${inX - 40}px ${BOTTOM + 40}px, ${inX - 40}px 2200px, -200px 2200px)`
      : frame >= SLASH_OUT[0]
        ? `polygon(${outX - 60 + lean}px ${TOP - 40}px, 1300px ${TOP - 40}px, 1300px 2200px, ${outX - 60}px 2200px, ${outX - 60}px ${BOTTOM + 40}px)`
        : undefined;

  const pop = (start: number) =>
    spring({
      frame: frame - start,
      fps,
      config: { damping: 15, mass: 0.6, stiffness: 170 },
    });
  const snow = interpolate(frame, SNOW_IN, [0, 1], clamp);
  const title = pop(TITLE_IN);
  const cta = pop(CTA_IN);
  const button = pop(BUTTON_IN);
  const press = interpolate(frame, [TAP - 4, TAP, TAP + 6], [1, 0.9, 1], clamp);
  const followed = frame >= TAP;
  const ripple = interpolate(frame, [TAP, TAP + 18], [0, 1], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  const nudge = !followed
    ? 1 + 0.04 * Math.max(0, Math.sin((frame - BUTTON_IN) / 5))
    : 1;

  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ clipPath: reveal }}>
        <svg
          width={1080}
          height={1920}
          style={{ position: "absolute", inset: 0 }}
        >
          <defs>
            <clipPath id="winter-plate">
              <polygon points={PLATE_POLY} />
            </clipPath>
          </defs>
          <polygon
            points={PLATE_POLY}
            fill={PLATE}
            style={{ filter: "drop-shadow(0 18px 30px rgba(0,0,0,0.45))" }}
          />
          <g clipPath="url(#winter-plate)" opacity={snow}>
            {Array.from({ length: 90 }, (_, i) => {
              const x = X0 + random(`wx${i}`) * (X1 - X0);
              const speed = 2 + random(`ws${i}`) * 3.5;
              const r = 2 + random(`wr${i}`) * 4.5;
              const y =
                TOP +
                ((random(`wy${i}`) * (BOTTOM - TOP) + frame * speed) %
                  (BOTTOM - TOP));
              return (
                <circle
                  key={i}
                  cx={x + Math.sin(frame / 14 + i) * 9}
                  cy={y}
                  r={r}
                  fill={WHITE}
                  opacity={0.2 + random(`wo${i}`) * 0.45}
                />
              );
            })}
          </g>
          <polygon
            points={`${X0 + LEAN},${TOP} ${X0 + LEAN + 16},${TOP} ${X0 + 16},${BOTTOM} ${X0},${BOTTOM}`}
            fill={ICE}
          />
        </svg>

        <div
          style={{
            position: "absolute",
            left: 160,
            top: TOP + 40,
            display: "flex",
            alignItems: "center",
            gap: 22,
          }}
        >
          <SeasonIcon
            season="INVERNO"
            size={110}
            t={interpolate(frame, ICON_IN, [0, 1], clamp)}
            spin={Math.max(0, frame - ICON_IN[0]) / 30}
          />
          <div
            style={{
              fontFamily: MONO,
              fontWeight: 500,
              fontSize: 44,
              letterSpacing: 2,
              color: ICE,
              whiteSpace: "pre",
            }}
          >
            {scramble("TAPPA 4 DI 4 · ???", frame, STEP_IN)}
          </div>
        </div>

        <div
          style={{
            position: "absolute",
            left: 146,
            top: TOP + 166,
            fontFamily: DISPLAY,
            fontWeight: 800,
            fontStyle: "italic",
            fontSize: 172,
            lineHeight: 1,
            color: ICE,
            opacity: frame < TITLE_IN ? 0 : 1,
            transform: `translateX(${(1 - title) * -90}px)`,
          }}
        >
          INVERNO
        </div>

        <div
          style={{
            position: "absolute",
            left: 150,
            top: TOP + 352,
            fontFamily: DISPLAY,
            fontWeight: 800,
            fontStyle: "italic",
            fontSize: 104,
            lineHeight: 0.98,
            color: WHITE,
            opacity: frame < CTA_IN ? 0 : 1,
            transform: `translateX(${(1 - cta) * 90}px)`,
          }}
        >
          <div>SEGUIMI PER</div>
          <div>SCOPRIRLO</div>
        </div>

        {/* The follow button, tapped. */}
        {frame >= BUTTON_IN && (
          <div
            style={{
              position: "absolute",
              left: 156,
              top: TOP + 590,
              width: 400,
              height: 104,
              transform: `scale(${button * press * nudge})`,
              transformOrigin: "50% 50%",
            }}
          >
            <div
              style={{
                width: "100%",
                height: "100%",
                borderRadius: 52,
                background: followed ? ICE : WHITE,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 14,
                fontFamily: DISPLAY,
                fontWeight: 800,
                fontStyle: "italic",
                fontSize: 62,
                color: "#101418",
                boxShadow: "0 8px 20px rgba(0,0,0,0.35)",
              }}
            >
              {followed ? "✓ SEGUITO" : "+ SEGUI"}
            </div>
            {followed && ripple < 1 && (
              <div
                style={{
                  position: "absolute",
                  left: 200,
                  top: 52,
                  width: 120,
                  height: 120,
                  borderRadius: "50%",
                  border: `6px solid ${WHITE}`,
                  transform: `translate(-50%, -50%) scale(${0.4 + ripple * 2.2})`,
                  opacity: 1 - ripple,
                }}
              />
            )}
          </div>
        )}
      </AbsoluteFill>

      {frame <= SLASH_IN[1] && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: ICE,
            clipPath: slashPoly(inX, TOP - 40, BOTTOM + 40, 90, LEAN_PER_PX),
          }}
        />
      )}
      {frame >= SLASH_OUT[0] && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: ICE,
            clipPath: slashPoly(outX, TOP - 40, BOTTOM + 40, 110, LEAN_PER_PX),
          }}
        />
      )}
    </AbsoluteFill>
  );
};
