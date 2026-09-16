import React from "react";
import { interpolate, OffthreadVideo, staticFile } from "remotion";
import { INK_TITLE_FADE, INK_TITLE_LENGTH } from "./timeline";

// The title card, rendered by HyperFrames rather than drawn here: its
// `ink-bleed-reveal` primitive blooms ink through paper under a gooey
// blur-and-threshold chain computed in a canvas work buffer. That is not a
// thing to reimplement in React - but it is a thing to composite.
//
// public/overlays/ink-title.webm is built by hyperframes/ and checked in, so
// a Remotion render never needs HyperFrames installed. See hyperframes/README.md.
export const InkTitle: React.FC<{ frame: number }> = ({ frame }) => {
  const opacity = interpolate(frame, INK_TITLE_FADE, [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  if (frame >= INK_TITLE_LENGTH || opacity <= 0) return null;

  // Remotion owns the clock on both sides of the seam: the card is 4s of
  // video, and when to cut away from it is a number in timeline.ts like every
  // other beat, not something baked into the WebM.
  return (
    <OffthreadVideo
      src={staticFile("overlays/ink-title.webm")}
      style={{ position: "absolute", inset: 0, opacity }}
      transparent
    />
  );
};
