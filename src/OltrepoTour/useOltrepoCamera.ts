import { Easing, interpolate } from "remotion";
import { Camera, fitBoxToRect, lerpCameraZoom } from "../shared/camera";
import { Rect } from "../shared/safeArea";
import { REGION_BBOX, ROUTE_BBOX } from "./geoData";
import { ZOOM_ROUTE } from "./timeline";

const ease = Easing.bezier(0.45, 0, 0.15, 1);

// One push, not three: the Oltrepo and the lines across it, down onto the
// road. Interpolating the scale geometrically keeps that drop reading at a
// steady speed rather than lunging and then crawling.
export const useOltrepoCamera = (frame: number, rect: Rect): Camera => {
  const region = fitBoxToRect(REGION_BBOX, rect, 1);
  const route = fitBoxToRect(ROUTE_BBOX, rect, 1);

  const t = interpolate(frame, ZOOM_ROUTE, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ease,
  });

  return lerpCameraZoom(region, route, t, rect);
};
