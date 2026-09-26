import React, { useEffect, useState } from "react";
import {
  AbsoluteFill,
  continueRender,
  delayRender,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { SAFE_RECT } from "../shared/safeArea";

// An opening hook, laid over the rider's own footage: a transparent 1080x1920
// clip, 5.9s, three beats - the worry, the warning, the answer - and then
// out of the way.
//
// Built to survive being a GIF. GIF transparency is one bit: a pixel is fully
// there or fully gone, so an opacity fade turns into a hard pop and a soft
// shadow into a blotch. Nothing here fades. Everything enters and leaves by
// a hard-edged wipe or a scale, every colour is opaque, and the shadow under
// the type is a solid offset rather than a blur. The ProRes export carries a
// real alpha channel and would forgive a fade; the design does not rely on it.

export const HOOK_DURATION = 177; // 5.9s @30fps

const FONT = "Anton";
const INK = "#14110c";
const WHITE = "#ffffff";
const AMBER = "#f2b705"; // road-sign yellow
const RED = "#c0392b"; // the road in the map films

// Beats, in frames.
// Beat 1 reads in three lines, each wiping in a beat after the last.
const B1 = { in: [[0, 9], [5, 14], [10, 20]], out: [56, 64] } as const;
const B2 = { bar: [60, 68], text: [65, 75], sign: [68, 78], out: [106, 114] } as const;
const B3 = { line: [112, 122], stamp: [122, 136], out: [162, 172] } as const;

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// A hard-edged wipe: reveals left to right over `inR`, hides left to right
// over `outR`. As a clip-path it never makes a half-transparent pixel.
const wipe = (frame: number, inR: readonly [number, number], outR: readonly [number, number]) => {
  const shown = interpolate(frame, inR, [100, 0], clamp); // right inset while entering
  const gone = interpolate(frame, outR, [0, 100], clamp); // left inset while leaving
  return `inset(-20% ${shown}% -20% ${gone}%)`;
};

const type = (size: number, color = WHITE): React.CSSProperties => ({
  fontFamily: FONT,
  fontSize: size,
  lineHeight: 1,
  color,
  textTransform: "uppercase",
  letterSpacing: 1,
  whiteSpace: "nowrap",
  // Outline behind the glyphs, then a solid drop straight down: legible over
  // sky, tarmac or forest, and all of it opaque.
  WebkitTextStroke: `${Math.round(size * 0.11)}px ${INK}`,
  paintOrder: "stroke fill",
  textShadow: `0 ${Math.round(size * 0.08)}px 0 ${INK}`,
});

const WarningSign: React.FC<{ size: number }> = ({ size }) => (
  <svg width={size} height={size * 0.9} viewBox="0 0 100 90">
    <path
      d="M50 4 L96 86 L4 86 Z"
      fill={AMBER}
      stroke={INK}
      strokeWidth={8}
      strokeLinejoin="round"
    />
    <rect x={45} y={30} width={10} height={32} rx={3} fill={INK} />
    <circle cx={50} cy={73} r={6} fill={INK} />
  </svg>
);

export const HookStradaIsolata: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // The font is vendored in public/fonts so a render never needs the network.
  const [handle] = useState(() => delayRender("Loading Anton"));
  useEffect(() => {
    const face = new FontFace(FONT, `url(${staticFile("fonts/anton-latin-400-normal.woff2")})`);
    face
      .load()
      .then((loaded) => {
        document.fonts.add(loaded);
        continueRender(handle);
      })
      .catch((err) => {
        console.error(err);
        continueRender(handle);
      });
  }, [handle]);

  const pop = (start: number, from: number) =>
    interpolate(
      spring({ frame: frame - start, fps, config: { damping: 11, mass: 0.6, stiffness: 180 } }),
      [0, 1],
      [from, 1],
    );

  // Every beat is centred in SAFE_RECT, not in the frame: the right-hand
  // action rail and the bottom caption block of TikTok / Reels / Shorts
  // cover the rest. Widths below are sized to fit its 840px.
  const centered: React.CSSProperties = {
    position: "absolute",
    left: SAFE_RECT.x,
    top: SAFE_RECT.y,
    width: SAFE_RECT.w,
    height: SAFE_RECT.h,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
  };

  return (
    // No background: this is an overlay.
    <AbsoluteFill>
      {/* 1 - the worry */}
      {frame < B1.out[1] && (
        <div style={{ ...centered, gap: 22 }}>
          {(
            [
              ["Una strada per", 96],
              ["motociclisti", 140],
              ["solitari", 190],
            ] as const
          ).map(([text, size], i) => (
            // Padded so the clip doesn't shave the outline off the end letters.
            <div key={text} style={{ padding: "0 24px", clipPath: wipe(frame, B1.in[i], B1.out) }}>
              <div style={type(size)}>{text}</div>
            </div>
          ))}
        </div>
      )}

      {/* 2 - the warning: a road sign, and the words on a sign-yellow band */}
      {frame >= B2.bar[0] && frame < B2.out[1] && (
        <div style={{ ...centered, clipPath: wipe(frame, B2.bar, B2.out), gap: 26 }}>
          {frame >= B2.sign[0] && (
            <div style={{ transform: `scale(${pop(B2.sign[0], 0.4)})` }}>
              <WarningSign size={150} />
            </div>
          )}
          <div
            style={{
              background: AMBER,
              border: `8px solid ${INK}`,
              boxShadow: `0 12px 0 ${INK}`,
              padding: "18px 34px 14px",
            }}
          >
            <div
              style={{
                ...type(100, INK),
                WebkitTextStroke: "0px",
                textShadow: "none",
                transform: frame >= B2.text[0] ? `scale(${pop(B2.text[0], 1.25)})` : "scale(0)",
              }}
            >
              Serve attenzione
            </div>
          </div>
        </div>
      )}

      {/* 3 - the answer */}
      {frame >= B3.line[0] && frame < B3.out[1] && (
        <div style={{ ...centered, gap: 34 }}>
          <div
            style={{
              clipPath: wipe(frame, B3.line, B3.out),
              transform: `translateY(${interpolate(frame, B3.line, [40, 0], clamp)}px)`,
            }}
          >
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
              <div style={type(110)}>Ma con</div>
              <div style={type(110)}>un’adventure…</div>
            </div>
          </div>
          {frame >= B3.stamp[0] && (
            <div
              style={{
                clipPath: wipe(frame, [B3.stamp[0] - 1, B3.stamp[0]], B3.out),
                transform: `scale(${pop(B3.stamp[0], 1.5)}) rotate(-3deg)`,
                background: RED,
                border: `8px solid ${INK}`,
                boxShadow: `0 14px 0 ${INK}`,
                padding: "16px 56px 10px",
              }}
            >
              <div style={{ ...type(190), textShadow: "none" }}>Si fa.</div>
            </div>
          )}
        </div>
      )}
    </AbsoluteFill>
  );
};
