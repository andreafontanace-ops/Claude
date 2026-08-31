import { BBox } from "./geoData";
import { Rect } from "./safeArea";

export type Camera = {
  scale: number;
  tx: number;
  ty: number;
};

// Computes a translate+scale transform so that `box` is fully visible
// ("contain") and centered inside `rect`, which may be the whole frame or
// just the part of it the platform chrome leaves alone.
export const fitBoxToRect = (box: BBox, rect: Rect, padding = 1): Camera => {
  const contentW = (box.x1 - box.x0) * padding;
  const contentH = (box.y1 - box.y0) * padding;
  const cx = (box.x0 + box.x1) / 2;
  const cy = (box.y0 + box.y1) / 2;
  const scale = Math.min(rect.w / contentW, rect.h / contentH);
  const tx = rect.x + rect.w / 2 - scale * cx;
  const ty = rect.y + rect.h / 2 - scale * cy;
  return { scale, tx, ty };
};

export const fitBoxToViewport = (
  box: BBox,
  viewportW: number,
  viewportH: number,
  padding = 1,
): Camera =>
  fitBoxToRect(box, { x: 0, y: 0, w: viewportW, h: viewportH }, padding);

export const lerpCamera = (a: Camera, b: Camera, t: number): Camera => ({
  scale: a.scale + (b.scale - a.scale) * t,
  tx: a.tx + (b.tx - a.tx) * t,
  ty: a.ty + (b.ty - a.ty) * t,
});
