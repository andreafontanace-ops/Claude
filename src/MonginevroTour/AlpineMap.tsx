import React from "react";
import { communes, neighbours, regions } from "./geoData";

// The same pastel patchwork as the other tours, here covering two countries
// at once: Italian provinces and French departments are close enough in size
// to read as one map rather than two stitched together.
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

// Line weights are in screen pixels divided by the camera scale: the map sits
// inside a scaled <g>, and without this the borders would go from hairlines
// to slabs as the camera pushes in.
export const AlpineMap: React.FC<{
  scale: number;
  communeOpacity: number;
}> = ({ scale, communeOpacity }) => {
  const border = 3 / scale;

  return (
    <g>
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

      {regions.map((c, i) => (
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

      {/* Province and department edges again on top, so the national border
          still reads once the communes have filled in underneath. */}
      {communeOpacity > 0 && (
        <g opacity={communeOpacity}>
          {regions.map((c, i) => (
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
