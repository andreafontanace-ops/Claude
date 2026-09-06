import { Easing, interpolate } from "remotion";
import { Camera, fitBoxToRect, lerpCameraZoom } from "../shared/camera";
import { Rect } from "../shared/safeArea";
import { ALPS_BBOX, FRANCE_BBOX, VARS_BBOX } from "./geoData";
import { ZOOM_ALPS, ZOOM_VARS } from "./timeline";

const ease = Easing.bezier(0.45, 0, 0.15, 1);

// Two pushes rather than one: France down to the Route des Grandes Alpes,
// then the Alps down to the Col de Vars and its road. Chained so the second
// starts from wherever the first left off, even if their ranges overlap.
export const useVarsCamera = (frame: number, rect: Rect): Camera => {
  const france = fitBoxToRect(FRANCE_BBOX, rect, 0.94);
  const alps = fitBoxToRect(ALPS_BBOX, rect, 1);
  const vars = fitBoxToRect(VARS_BBOX, rect, 1);

  const t1 = interpolate(frame, ZOOM_ALPS, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ease,
  });
  const t2 = interpolate(frame, ZOOM_VARS, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ease,
  });

  return lerpCameraZoom(lerpCameraZoom(france, alps, t1, rect), vars, t2, rect);
};
