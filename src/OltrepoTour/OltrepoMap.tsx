import React from "react";
import { beyond, comuni, home } from "./geoData";

// The colour is spent on the four regions that meet over this valley and on
// the comuni inside them. The rest of the country is the same map drained of
// it. The boundary between two regions is then simply where the colour
// changes - the stroke on top only makes it unmissable.
const REGION_FILL: Record<string, string> = {
  Lombardia: "#e3cf7a",
  Piemonte: "#a7c3cf",
  "Emilia-Romagna": "#e3b8c0",
  Liguria: "#a9c9a3",
};

// The comuni get the same hues washed out. At the closest framing they fill
// the whole frame, and at full strength the road has to fight them.
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
  comuneOpacity: number;
  // The region boundaries, drawn over everything so the comuni cannot bury
  // them. 0 until they are the thing being looked at.
  borderOpacity: number;
}> = ({ scale, comuneOpacity, borderOpacity }) => {
  const border = 3 / scale;

  return (
    <g>
      {beyond.map((r, i) => (
        <path
          key={`beyond-${r.name}-${i}`}
          d={r.d}
          fillRule="evenodd"
          fill={GREY[hashIndex(r.name, GREY.length)]}
          stroke="#efeae0"
          strokeWidth={border}
          strokeLinejoin="round"
        />
      ))}

      {home.map((r, i) => (
        <path
          key={`home-${r.name}-${i}`}
          d={r.d}
          fillRule="evenodd"
          fill={REGION_FILL[r.name] ?? "#e0d9c8"}
          stroke="#faf6ec"
          strokeWidth={border}
          strokeLinejoin="round"
        />
      ))}

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

      {/* The region lines last. Two strokes: a cream casing so the line reads
          over any tile, and the line itself. */}
      {borderOpacity > 0 && (
        <g opacity={borderOpacity}>
          {home.map((r, i) => (
            <path
              key={`edge-casing-${r.name}-${i}`}
              d={r.d}
              fill="none"
              stroke="#faf6ec"
              strokeWidth={border * 3.4}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          ))}
          {home.map((r, i) => (
            <path
              key={`edge-${r.name}-${i}`}
              d={r.d}
              fill="none"
              stroke="#8a7d63"
              strokeWidth={border * 1.5}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          ))}
        </g>
      )}
    </g>
  );
};
