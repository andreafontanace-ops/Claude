import { Easing, interpolate } from "remotion";
import { Camera, fitBoxToRect, lerpCameraZoom } from "../shared/camera";
import { Rect } from "../shared/safeArea";
import { CASTLE_BBOX, REGION_BBOX, ROUTE_BBOX } from "./geoData";
import { CASTLE_IN, CASTLE_OUT, INTRO_ZOOM } from "./timeline";

const ease = Easing.bezier(0.45, 0, 0.15, 1);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// One drop from the regions onto the road, then one push onto the castle and
// back. Both geometric, so a 12x zoom reads at a steady speed.
export const useTrebeccoCamera = (frame: number, rect: Rect): Camera => {
  const region = fitBoxToRect(REGION_BBOX, rect, 1);
  const route = fitBoxToRect(ROUTE_BBOX, rect, 1);
  const castle = fitBoxToRect(CASTLE_BBOX, rect, 1);

  const down = interpolate(frame, INTRO_ZOOM, [0, 1], {
    ...clamp,
    easing: ease,
  });
  const base = lerpCameraZoom(region, route, down, rect);

  const close =
    interpolate(frame, CASTLE_IN, [0, 1], { ...clamp, easing: ease }) -
    interpolate(frame, CASTLE_OUT, [0, 1], { ...clamp, easing: ease });
  return lerpCameraZoom(base, castle, close, rect);
};
