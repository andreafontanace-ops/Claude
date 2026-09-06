import { Easing, interpolate } from "remotion";
import { fitBoxToRect, lerpCamera, Camera, project } from "../shared/camera";

export type { Camera };
export { project };
import { BBox } from "../shared/types";
import { FULL_BBOX, REGION_BBOX } from "./geoData";
import { FULL_RECT, Rect } from "../shared/safeArea";
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
