import React from "react";
import { cantons } from "./geoData";

const HIGHLIGHT_CANTONS = new Set(["Ticino", "Uri", "Valais"]);

export const SwitzerlandMap: React.FC<{ highlight?: boolean }> = ({
  highlight = true,
}) => {
  return (
    <g>
      {cantons.map((c) => {
        const isHighlighted = highlight && HIGHLIGHT_CANTONS.has(c.name);
        return (
          <path
            key={c.name}
            d={c.d}
            fillRule="evenodd"
            fill={isHighlighted ? "#2d4a73" : "#1c2b45"}
            stroke={isHighlighted ? "#6f9bd6" : "#3a5075"}
            strokeWidth={1.6}
            strokeLinejoin="round"
          />
        );
      })}
    </g>
  );
};
