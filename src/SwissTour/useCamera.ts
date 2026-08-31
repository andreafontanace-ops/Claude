import { Easing, interpolate } from "remotion";
import { fitBoxToViewport, lerpCamera, Camera } from "./camera";

export type { Camera };
import { BBox, FULL_BBOX, REGION_BBOX } from "./geoData";
import { CAMERA_ZOOM } from "./timeline";

export const useCamera = (
  frame: number,
  viewportW: number,
  viewportH: number,
  targetBox: BBox = REGION_BBOX,
): Camera => {
  const wide = fitBoxToViewport(FULL_BBOX, viewportW, viewportH, 0.92);
  const region = fitBoxToViewport(targetBox, viewportW, viewportH, 1);

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
