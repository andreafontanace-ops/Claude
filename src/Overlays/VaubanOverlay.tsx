import React from "react";
import {
  AbsoluteFill,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

// A cut-out overlay, rendered on nothing: no background fill anywhere, so the
// alpha channel survives into the file and the portrait can be dropped
// straight over footage.
export const OVERLAY_DURATION = 150; // 5s @30fps

export const VaubanOverlay: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  // Comes up from under the frame, overshoots a little, settles.
  const rise = spring({
    frame,
    fps,
    durationInFrames: 34,
    config: { damping: 11, mass: 0.7, stiffness: 110 },
  });
  const y = interpolate(rise, [0, 1], [height * 0.62, 0]);
  const enterScale = interpolate(rise, [0, 1], [0.94, 1]);
  const opacity = interpolate(frame, [0, 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Once it has landed it keeps breathing, so it does not read as a sticker
  // pasted on the shot.
  const t = (frame - 34) / fps;
  const breath = frame > 34 ? Math.sin(t * 1.15) : 0;
  const floatY = breath * 5;
  const breathScale = 1 + breath * 0.006;

  const imgWidth = width * 0.64;

  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: "50%",
          // The engraving is a bust cut off at the chest, so it sits low and
          // the cut edge stays under the bottom of the frame.
          bottom: -height * 0.06,
          transform: `translateX(-50%) translateY(${y + floatY}px) scale(${
            enterScale * breathScale
          })`,
          transformOrigin: "50% 100%",
          opacity,
        }}
      >
        <Img
          src={staticFile("vauban.png")}
          style={{
            display: "block",
            width: imgWidth,
            height: "auto",
            filter: "drop-shadow(0 18px 34px rgba(0,0,0,0.45))",
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
