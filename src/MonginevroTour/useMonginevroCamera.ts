import { Easing, interpolate } from "remotion";
import { Camera, fitBoxToRect, lerpCameraZoom } from "../shared/camera";
import { Rect } from "../shared/safeArea";
import { REGION_BBOX, ROUTE_BBOX, WIDE_BBOX } from "./geoData";
import { ZOOM_REGION, ZOOM_ROUTE } from "./timeline";

const ease = Easing.bezier(0.45, 0, 0.15, 1);

// Two pushes: France down onto the Alpine region on its eastern edge, then
// that region down onto the frontier and the road across it.
export const useMonginevroCamera = (frame: number, rect: Rect): Camera => {
  const wide = fitBoxToRect(WIDE_BBOX, rect, 1.0);
  const region = fitBoxToRect(REGION_BBOX, rect, 1);
  const route = fitBoxToRect(ROUTE_BBOX, rect, 1);

  const t1 = interpolate(frame, ZOOM_REGION, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ease,
  });
  const t2 = interpolate(frame, ZOOM_ROUTE, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ease,
  });

  return lerpCameraZoom(lerpCameraZoom(wide, region, t1, rect), route, t2, rect);
};
