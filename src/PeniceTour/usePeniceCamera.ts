import { Easing, interpolate } from "remotion";
import { Camera, fitBoxToRect, lerpCameraZoom } from "../shared/camera";
import { pointAtProgress } from "../shared/polyline";
import { Rect } from "../shared/safeArea";
import { climb, descent, ROUTE_BBOX } from "./geoData";
import {
  CLIMB,
  DESCENT,
  FOLLOW_OUT,
  PASS_PUSH_IN,
  PASS_PUSH_OUT,
} from "./timeline";

const ease = Easing.bezier(0.33, 0, 0.2, 1);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// How much closer than the whole-road framing the camera rides: about 8 m a
// pixel, where the hairpins read as hairpins.
const FOLLOW_ZOOM = 2.3;
// And the extra push onto the pass while it is named.
const PASS_ZOOM = 1.22;

// Where the drawn line's head is at `frame`, in map units - the same eased
// progress RoutePath and TravelDot use, so the camera is on the dot.
export const headAt = (frame: number): { x: number; y: number } => {
  if (frame < DESCENT[0]) {
    const t = interpolate(frame, CLIMB, [0, 1], {
      ...clamp,
      easing: Easing.inOut(Easing.cubic),
    });
    return pointAtProgress(climb.points, t);
  }
  const t = interpolate(frame, DESCENT, [0, 1], {
    ...clamp,
    easing: Easing.inOut(Easing.cubic),
  });
  return pointAtProgress(descent.points, t);
};

// The camera aims at the head averaged over a second either side of now, so
// it glides through the hairpins instead of jerking round every one.
const aimAt = (frame: number) => {
  let x = 0;
  let y = 0;
  let n = 0;
  for (let f = frame - 15; f <= frame + 15; f += 3) {
    const p = headAt(f);
    x += p.x;
    y += p.y;
    n++;
  }
  return { x: x / n, y: y / n };
};

export const usePeniceCamera = (frame: number, rect: Rect): Camera => {
  const whole = fitBoxToRect(ROUTE_BBOX, rect, 1);

  const push =
    interpolate(frame, PASS_PUSH_IN, [0, 1], { ...clamp, easing: ease }) -
    interpolate(frame, PASS_PUSH_OUT, [0, 1], { ...clamp, easing: ease });
  const scale = whole.scale * FOLLOW_ZOOM * Math.pow(PASS_ZOOM, push);
  const aim = aimAt(frame);
  const follow: Camera = {
    scale,
    tx: rect.x + rect.w / 2 - scale * aim.x,
    ty: rect.y + rect.h / 2 - scale * aim.y,
  };

  const out = interpolate(frame, FOLLOW_OUT, [0, 1], {
    ...clamp,
    easing: ease,
  });
  return lerpCameraZoom(follow, whole, out, rect);
};
