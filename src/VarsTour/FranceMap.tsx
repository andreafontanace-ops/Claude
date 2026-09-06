import React from "react";
import { communes, departments, neighbours } from "./geoData";

// The same pastel patchwork as the Swiss map: every department gets its own
// tile, like a printed touring map rather than a political choropleth.
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

const hashIndex = (name: string, mod: number) => {
  let h = 0;
  for (let i = 0; i < name.length; i++) {
    h = (h * 31 + name.charCodeAt(i)) >>> 0;
  }
  return h % mod;
};

// Line weights are given in screen pixels and divided by the camera scale,
// because the whole map sits inside a scaled <g>: without this the borders
// would balloon from hairlines to slabs as the camera pushes in 25x.
export const FranceMap: React.FC<{
  scale: number;
  // 0 on the wide frames, 1 once the camera is down on the pass, where the
  // department outlines alone would leave two flat fields of colour.
  communeOpacity: number;
}> = ({ scale, communeOpacity }) => {
  const border = 3 / scale;

  return (
    <g>
      {/* Italy and Switzerland: unlabelled and flat, so the Alpine frames
          have land on the far side of the border instead of bare paper. */}
      <g>
        {neighbours.map((n, i) => (
          <path
            key={`${n.name}-${i}`}
            d={n.d}
            fillRule="evenodd"
            fill="#e6ddc8"
            stroke="#dcd2bb"
            strokeWidth={border}
            strokeLinejoin="round"
          />
        ))}
      </g>
      {departments.map((c) => (
        <path
          key={c.name}
          d={c.d}
          fillRule="evenodd"
          fill={PALETTE[hashIndex(c.name, PALETTE.length)]}
          stroke="#faf6ec"
          strokeWidth={border}
          strokeLinejoin="round"
        />
      ))}

      {communeOpacity > 0 && (
        <g opacity={communeOpacity}>
          {communes.map((c, i) => (
            <path
              key={`${c.name}-${i}`}
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

      {/* Department edges again on top: the Hautes-Alpes / Alpes-de-Haute-
          Provence line runs straight over the pass, and it should still read
          once the communes have filled in underneath. */}
      {communeOpacity > 0 && (
        <g opacity={communeOpacity}>
          {departments.map((c) => (
            <path
              key={`edge-${c.name}`}
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
