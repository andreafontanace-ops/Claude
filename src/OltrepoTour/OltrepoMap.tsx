import React from "react";
import { comuni, italy, province } from "./geoData";

// The colour is spent on the four provinces and on the comuni inside them.
// Italy underneath is the same map drained of it: at the widest the film goes,
// the regions are flat fields rather than shapes you could name, so they are
// there for the coastline and nothing else.
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

// The comuni get the same eight hues washed out. At the closest framing they
// fill the whole frame, and at full strength the road has to fight them.
const PALE = [
  "#e5ddf0",
  "#d6e5d2",
  "#efe4cd",
  "#f1e8bc",
  "#f2dfe3",
  "#d9e5eb",
  "#eedcc5",
  "#e2e8d1",
];

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

// The four are picked by hand rather than by hash: they sit side by side for
// the whole opening, and two neighbouring tiles landing on near-identical
// pastels is exactly what that shot cannot afford.
const PROVINCE_FILL: Record<string, string> = {
  Pavia: "#e3cf7a",
  Alessandria: "#a7c3cf",
  Piacenza: "#e3b8c0",
  Genova: "#a9c9a3",
};

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
export const OltrepoMap: React.FC<{
  scale: number;
  // 0 while the north-west is one grey sheet, 1 once the four provinces have
  // taken their colour inside it.
  patchworkOpacity: number;
  comuneOpacity: number;
}> = ({ scale, patchworkOpacity, comuneOpacity }) => {
  const border = 3 / scale;

  return (
    <g>
      {italy.map((r, i) => (
        <path
          key={`italy-${r.name}-${i}`}
          d={r.d}
          fillRule="evenodd"
          fill={GREY[hashIndex(r.name, GREY.length)]}
          stroke="#efeae0"
          strokeWidth={border}
          strokeLinejoin="round"
        />
      ))}

      {patchworkOpacity > 0 && (
        <g opacity={patchworkOpacity}>
          {province.map((p, i) => (
            <path
              key={`prov-${p.name}-${i}`}
              d={p.d}
              fillRule="evenodd"
              fill={PROVINCE_FILL[p.name] ?? PALETTE[hashIndex(p.name, PALETTE.length)]}
              stroke="#faf6ec"
              strokeWidth={border * 1.4}
              strokeLinejoin="round"
            />
          ))}
        </g>
      )}

      {comuneOpacity > 0 && (
        <g opacity={comuneOpacity}>
          {comuni.map((c, i) => (
            <path
              key={`com-${c.name}-${i}`}
              d={c.d}
              fillRule="evenodd"
              fill={PALE[hashIndex(c.name, PALE.length)]}
              stroke="#faf6ec"
              strokeWidth={border * 0.6}
              strokeLinejoin="round"
            />
          ))}
        </g>
      )}

      {/* The province lines again on top, so the comuni cannot bury the one
          edge that matters here: Pavia, Alessandria and Piacenza meet on the
          Monte Chiappo at the head of this valley, and the ridge the road
          rides runs out of that point. */}
      {comuneOpacity > 0 && (
        <g opacity={comuneOpacity}>
          {province.map((p, i) => (
            <path
              key={`prov-edge-${p.name}-${i}`}
              d={p.d}
              fill="none"
              stroke="#faf6ec"
              strokeWidth={border * 2.2}
              strokeLinejoin="round"
            />
          ))}
        </g>
      )}
    </g>
  );
};
