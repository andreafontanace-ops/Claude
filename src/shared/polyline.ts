// Piecewise-linear interpolation along a polyline, parameterized by
// cumulative arc-length fraction t in [0, 1]. Used to place a "traveling
// dot" marker along a route without needing DOM path measurement.
export const pointAtProgress = (
  points: readonly (readonly [number, number])[],
  t: number,
): { x: number; y: number } => {
  if (points.length === 0) return { x: 0, y: 0 };
  if (points.length === 1) return { x: points[0][0], y: points[0][1] };

  const clamped = Math.max(0, Math.min(1, t));

  const segLengths: number[] = [];
  let total = 0;
  for (let i = 1; i < points.length; i++) {
    const dx = points[i][0] - points[i - 1][0];
    const dy = points[i][1] - points[i - 1][1];
    const len = Math.hypot(dx, dy);
    segLengths.push(len);
    total += len;
  }

  const target = clamped * total;
  let acc = 0;
  for (let i = 0; i < segLengths.length; i++) {
    const segLen = segLengths[i];
    if (acc + segLen >= target || i === segLengths.length - 1) {
      const segT = segLen === 0 ? 0 : (target - acc) / segLen;
      const [x0, y0] = points[i];
      const [x1, y1] = points[i + 1];
      return { x: x0 + (x1 - x0) * segT, y: y0 + (y1 - y0) * segT };
    }
    acc += segLen;
  }

  const last = points[points.length - 1];
  return { x: last[0], y: last[1] };
};

// The stretch of a polyline between arc fractions t0 and t1, with the ends
// interpolated onto the line rather than snapped to the nearest vertex.
export const subPolyline = (
  points: readonly (readonly [number, number])[],
  t0: number,
  t1: number,
): [number, number][] => {
  if (points.length < 2 || t1 <= t0) return [];
  const cum = [0];
  for (let i = 1; i < points.length; i++) {
    cum.push(
      cum[i - 1] +
        Math.hypot(
          points[i][0] - points[i - 1][0],
          points[i][1] - points[i - 1][1],
        ),
    );
  }
  const total = cum[cum.length - 1];
  const a = Math.max(0, t0) * total;
  const b = Math.min(1, t1) * total;
  const at = (s: number): [number, number] => {
    let i = 1;
    while (i < points.length - 1 && cum[i] < s) i++;
    const seg = cum[i] - cum[i - 1];
    const u = seg === 0 ? 0 : (s - cum[i - 1]) / seg;
    return [
      points[i - 1][0] + (points[i][0] - points[i - 1][0]) * u,
      points[i - 1][1] + (points[i][1] - points[i - 1][1]) * u,
    ];
  };
  const out: [number, number][] = [at(a)];
  for (let i = 0; i < points.length; i++) {
    if (cum[i] > a && cum[i] < b) out.push([points[i][0], points[i][1]]);
  }
  out.push(at(b));
  return out;
};

// A smooth SVG path through the points (Catmull-Rom as cubic Béziers) - the
// same curve the geo build scripts write into `d`.
export const smoothPath = (
  points: readonly (readonly [number, number])[],
): string => {
  if (points.length === 0) return "";
  const p = [points[0], ...points, points[points.length - 1]];
  let d = `M${points[0][0]},${points[0][1]}`;
  for (let i = 1; i < p.length - 2; i++) {
    const [p0, p1, p2, p3] = [p[i - 1], p[i], p[i + 1], p[i + 2]];
    d +=
      `C${p1[0] + (p2[0] - p0[0]) / 6},${p1[1] + (p2[1] - p0[1]) / 6} ` +
      `${p2[0] - (p3[0] - p1[0]) / 6},${p2[1] - (p3[1] - p1[1]) / 6} ${p2[0]},${p2[1]}`;
  }
  return d;
};
