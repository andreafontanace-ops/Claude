// Timeline for the Oltrepo composition, in frames @30fps. 16.7s, in three
// steps: the four provinces whose boundaries meet at the head of this valley,
// the Oltrepo between them, then the road itself - Varzi up the Val Staffora
// to the Passo del Giovà.
import { marks } from "./geoData";

export const FPS = 30;
export const OLTREPO_DURATION = 500; // 16.7s

export const INTRO_FADE_IN = [0, 12] as const;
export const TITLE_HOLD = [12, 40] as const;
export const TITLE_FADE_OUT = [64, 80] as const;

// The four provinces take their colour under the title, before the camera
// starts down: the opening shot is them, so they cannot arrive late.
export const PATCHWORK = [6, 40] as const;
export const PROV_DROP_START = 20;
export const PROV_DROP_STEP = 12;
export const PROV_LABEL_DELAY = 10;
export const PROV_FADE = [96, 120] as const;

// Both pushes happen after the names have gone: a name dropped at one
// framing and read at another is a name the eye loses.
export const ZOOM_REGION = [104, 180] as const;
export const COMUNI = [150, 188] as const;
export const ZOOM_ROUTE = [190, 266] as const;

// The head of the valley, named while the middle framing still holds it: at
// the closest framing it sits off under the profile card.
export const CHIAPPO_DROP = [136, 164] as const;
export const CHIAPPO_LABEL = [150, 168] as const;
export const CHIAPPO_FADE = [186, 212] as const;

// The two legs, split at Casale Staffora where the road leaves the river and
// starts climbing. The valley is drawn at a steady 0.40 map units a frame;
// the climb runs at about 60% of that, because 3 km of hairpins to the pass
// is the point of the ride and at valley speed it is over in a second.
export const ROAD_VALLE = [272, 390] as const;
export const ROAD_SALITA = [386, 442] as const;

export const PROFILE_IN = [244, 272] as const;

// The HyperFrames title card: 4s of ink bleeding through paper, laid over the
// opening shot. Its own bloom finishes at 2.8s; the rest is hold, so the cut
// away from it is set here rather than in the WebM.
export const INK_TITLE_LENGTH = 120;
export const INK_TITLE_FADE = [88, 112] as const;

// RoutePath advances with Easing.inOut(cubic), so a place sitting at arc
// fraction t is reached later or sooner than the linear reading of the leg's
// frame range - this is the inverse of that curve.
const easeInOutCubicInverse = (e: number) =>
  e < 0.5 ? Math.cbrt(e / 4) : 1 - Math.cbrt(2 - 2 * e) / 2;

const legRange = (leg: string) =>
  leg === "valle" ? ROAD_VALLE : ROAD_SALITA;

// The frame at which the drawn line reaches a place, so its name lands with
// the road rather than ahead of it or behind it.
export const arrivalFrame = (id: string): number => {
  const mark = marks[id];
  const [from, to] = legRange(mark.leg);
  return Math.round(from + (to - from) * easeInOutCubicInverse(mark.t));
};

// Casale Staffora closes one leg and opens the next, and `marks` keeps the
// second of the two: as a place on the road it is reached when the valley
// leg ends. The Giovà is simply where the road stops.
export const CASALE_ARRIVAL = ROAD_VALLE[1];
export const GIOVA_ARRIVAL = ROAD_SALITA[1];

export const pinCue = (arrival: number) =>
  ({
    dropRange: [arrival - 14, arrival + 14] as const,
    labelRange: [arrival + 6, arrival + 26] as const,
  }) as const;
