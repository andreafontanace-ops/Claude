import React from "react";
import { cantons } from "./geoData";

// A soft, qualitative "patchwork" palette - every canton gets its own
// pastel tile, like a printed travel map, rather than a political choropleth.
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

export const SwitzerlandMap: React.FC = () => {
  return (
    <g>
      {cantons.map((c) => (
        <path
          key={c.name}
          d={c.d}
          fillRule="evenodd"
          fill={PALETTE[hashIndex(c.name, PALETTE.length)]}
          stroke="#faf6ec"
          strokeWidth={2.2}
          strokeLinejoin="round"
        />
      ))}
    </g>
  );
};
