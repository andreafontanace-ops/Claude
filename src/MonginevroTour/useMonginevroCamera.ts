import { Easing, interpolate } from "remotion";
import { Camera, fitBoxToRect, lerpCameraZoom } from "../shared/camera";
import { Rect } from "../shared/safeArea";
import { PASSES_BBOX, ROUTE_BBOX, WIDE_BBOX } from "./geoData";
import { ZOOM_PASSES, ZOOM_ROUTE } from "./timeline";

const ease = Easing.bezier(0.45, 0, 0.15, 1);

// Two pushes: the two countries down onto the passes along their border, then
// the border down onto the Monginevro and its road.
export const useMonginevroCamera = (frame: number, rect: Rect): Camera => {
  const wide = fitBoxToRect(WIDE_BBOX, rect, 1.0);
  const passes = fitBoxToRect(PASSES_BBOX, rect, 1);
  const route = fitBoxToRect(ROUTE_BBOX, rect, 1);

  const t1 = interpolate(frame, ZOOM_PASSES, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ease,
  });
  const t2 = interpolate(frame, ZOOM_ROUTE, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ease,
  });

  return lerpCameraZoom(lerpCameraZoom(wide, passes, t1, rect), route, t2, rect);
};
