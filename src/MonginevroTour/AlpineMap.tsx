import React from "react";
import { beyond, communesFr, communesIt, departments } from "./geoData";

// France carries the patchwork. Everything past the frontier is the same map
// drained of colour, so the border reads as the line where the colour stops
// rather than as a stroke someone drew on top.
const PALETTE = [
  "#cdbfe0", // lavender
  "#a9c9a3", // sage
  "#e0c9a0", // sand
  "#e3cf7a", // mustard
  "#e3b8c0", // rose
  "#a7c3cf", // powder blue
  "#d8b98f", // clay
  "#b9c7a0", // olive
];

// The same eight tiles with the colour taken out of them: enough variation to
// keep Cesana and Claviere legible as places, not enough to compete.
const GREY = [
  "#d0cbc2",
  "#c8c4bb",
  "#d7d2c9",
  "#c2beb5",
  "#ccc7be",
  "#d4cfc6",
  "#c5c1b8",
  "#cec9c0",
];

// The French and Italian boundary files come from different surveys and do
// not meet exactly, which leaves a hairline of bare paper along the frontier.
// A plain backing layer, drawn with a fat stroke of its own colour so it
// swells past its own edges, fills that gap; France is drawn over the top, so
// the overspill never shows.
const GREY_PLUG = "#ccc7be";

// The opening: France in one flat tone, before the map has been broken into
// its pieces.
const FLAT = "#a9c9a3";

const hashIndex = (name: string, mod: number) => {
  let h = 0;
  for (let i = 0; i < name.length; i++) {
    h = (h * 31 + name.charCodeAt(i)) >>> 0;
  }
  return h % mod;
};

// Line weights are in screen pixels divided by the camera scale: the map sits
// inside a scaled <g>, and without this the borders would go from hairlines
// to slabs as the camera pushes in.
export const AlpineMap: React.FC<{
  scale: number;
  // 0 while France is one flat shape, 1 once it has opened into departments.
  patchworkOpacity: number;
  // 0 until the camera has left the country behind and Italy enters frame.
  beyondOpacity: number;
  communeOpacity: number;
}> = ({ scale, patchworkOpacity, beyondOpacity, communeOpacity }) => {
  const border = 3 / scale;

  return (
    <g>
      {beyondOpacity > 0 && (
        <g opacity={beyondOpacity}>
          {beyond.map((c, i) => (
            <path
              key={`plug-${c.name}-${i}`}
              d={c.d}
              fillRule="evenodd"
              fill={GREY_PLUG}
              stroke={GREY_PLUG}
              strokeWidth={border * 4}
              strokeLinejoin="round"
            />
          ))}
          {beyond.map((c, i) => (
            <path
              key={`${c.name}-${i}`}
              d={c.d}
              fillRule="evenodd"
              fill={GREY[hashIndex(c.name, GREY.length)]}
              stroke="#efeae0"
              strokeWidth={border}
              strokeLinejoin="round"
            />
          ))}
        </g>
      )}

      {/* France as one shape: same stroke as fill, so the departments it is
          made of leave no seams. */}
      {departments.map((c, i) => (
        <path
          key={`flat-${c.name}-${i}`}
          d={c.d}
          fillRule="evenodd"
          fill={FLAT}
          stroke={FLAT}
          strokeWidth={border}
          strokeLinejoin="round"
        />
      ))}

      {patchworkOpacity > 0 && (
        <g opacity={patchworkOpacity}>
          {departments.map((c, i) => (
            <path
              key={`${c.name}-${i}`}
              d={c.d}
              fillRule="evenodd"
              fill={PALETTE[hashIndex(c.name, PALETTE.length)]}
              stroke="#faf6ec"
              strokeWidth={border}
              strokeLinejoin="round"
            />
          ))}
        </g>
      )}

      {communeOpacity > 0 && (
        <g opacity={communeOpacity}>
          {communesIt.map((c, i) => (
            <path
              key={`it-plug-${c.name}-${i}`}
              d={c.d}
              fillRule="evenodd"
              fill={GREY_PLUG}
              stroke={GREY_PLUG}
              strokeWidth={border * 3}
              strokeLinejoin="round"
            />
          ))}
          {communesIt.map((c, i) => (
            <path
              key={`it-${c.name}-${i}`}
              d={c.d}
              fillRule="evenodd"
              fill={GREY[hashIndex(c.name, GREY.length)]}
              stroke="#efeae0"
              strokeWidth={border * 0.6}
              strokeLinejoin="round"
            />
          ))}
          {communesFr.map((c, i) => (
            <path
              key={`fr-${c.name}-${i}`}
              d={c.d}
              fillRule="evenodd"
              fill={PALETTE[hashIndex(c.name, PALETTE.length)]}
              stroke="#faf6ec"
              strokeWidth={border * 0.6}
              strokeLinejoin="round"
            />
          ))}
        </g>
      )}

      {/* The frontier itself, last, so the communes cannot bury it. */}
      {communeOpacity > 0 && (
        <g opacity={communeOpacity}>
          {departments.map((c, i) => (
            <path
              key={`edge-${c.name}-${i}`}
              d={c.d}
              fill="none"
              stroke="#faf6ec"
              strokeWidth={border * 1.6}
              strokeLinejoin="round"
            />
          ))}
        </g>
      )}
    </g>
  );
};
