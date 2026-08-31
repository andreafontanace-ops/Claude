import { Easing, interpolate } from "remotion";
import { fitBoxToRect, lerpCamera, Camera } from "./camera";

export type { Camera };
import { BBox, FULL_BBOX, REGION_BBOX } from "./geoData";
import { FULL_RECT, Rect } from "./safeArea";
import { CAMERA_ZOOM } from "./timeline";

export const useCamera = (
  frame: number,
  viewportW: number,
  viewportH: number,
  targetBox: BBox = REGION_BBOX,
  // Which part of the frame to compose into. Defaults to all of it; the
  // short-form compositions pass the platform-safe rect instead.
  rect: Rect = FULL_RECT(viewportW, viewportH),
): Camera => {
  const wide = fitBoxToRect(FULL_BBOX, rect, 0.92);
  const region = fitBoxToRect(targetBox, rect, 1);

  const t = interpolate(frame, CAMERA_ZOOM, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.45, 0, 0.15, 1),
  });

  return lerpCamera(wide, region, t);
};

export const project = (camera: Camera, x: number, y: number) => ({
  left: camera.tx + x * camera.scale,
  top: camera.ty + y * camera.scale,
});
