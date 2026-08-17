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
