import { Easing, interpolate } from "remotion";
import { Camera, fitBoxToRect, lerpCameraZoom } from "../shared/camera";
import { Rect } from "../shared/safeArea";
import { OPEN_BBOX, ROUTE_BBOX } from "./geoData";
import { CAMERA_PUSH } from "./timeline";

const ease = Easing.bezier(0.33, 0, 0.2, 1);

// The same slow push as the Giovà - Brallo film, so the two cut together.
export const useBobbioCamera = (frame: number, rect: Rect): Camera => {
  const open = fitBoxToRect(OPEN_BBOX, rect, 1);
  const route = fitBoxToRect(ROUTE_BBOX, rect, 1);
  const t = interpolate(frame, CAMERA_PUSH, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ease,
  });
  return lerpCameraZoom(open, route, t, rect);
};
