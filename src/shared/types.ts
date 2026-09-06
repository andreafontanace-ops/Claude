// Shapes every tour's generated geoData.ts conforms to. The data itself is
// emitted per tour by the Python build scripts; only the types are shared,
// so a component written once works for Switzerland, France or anywhere
// else the same pipeline is pointed at.

export type BBox = { x0: number; y0: number; x1: number; y1: number };

// A named area on the base map: a Swiss canton, a French department, an
// Italian region.
export type RegionShape = {
  name: string;
  d: string;
};

// A place on the route, already projected into map units.
export type Waypoint = {
  id: string;
  name: string;
  subtitle?: string | null;
  x: number;
  y: number;
  elevation: number;
};

export type RouteSegment = {
  id: string;
  d: string;
  points: [number, number][];
};
