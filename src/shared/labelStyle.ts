import React from "react";

// Names sit straight on the map with no chip behind them, so they need a
// cream outline of their own to stay legible wherever the route or a canton
// edge runs underneath. `paint-order` puts the stroke behind the glyphs so
// the letterforms stay sharp instead of being eaten by the outline.
export const mapLabelStyle: React.CSSProperties = {
  color: "#231f16",
  fontWeight: 800,
  whiteSpace: "nowrap",
  WebkitTextStroke: "8px #faf6ec",
  paintOrder: "stroke fill",
};
