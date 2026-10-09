import { Easing, interpolate } from "remotion";
import { Camera, fitBoxToRect, lerpCameraZoom } from "../shared/camera";
import { Rect } from "../shared/safeArea";
import { REGION_BBOX, ROUTE_BBOX } from "./geoData";
import { INTRO_ZOOM } from "./timeline";

const ease = Easing.bezier(0.45, 0, 0.15, 1);

// One drop from the regions onto the road, then the camera holds. Geometric,
// so a 12x zoom reads at a steady speed.
export const useTrebeccoCamera = (frame: number, rect: Rect): Camera => {
  const region = fitBoxToRect(REGION_BBOX, rect, 1);
  const route = fitBoxToRect(ROUTE_BBOX, rect, 1);
  const down = interpolate(frame, INTRO_ZOOM, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ease,
  });
  return lerpCameraZoom(region, route, down, rect);
};
