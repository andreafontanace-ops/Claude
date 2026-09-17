// Timeline for the Oltrepo composition, in frames @30fps. 8s, and only two
// things happen: the four regions that meet over this valley name themselves,
// then the camera drops onto the road and draws it.
//
// 8s is 240 frames against the 390 this ran at. Most of the 150 came off the
// road, which is where it was asked for, but not all of it could: the road was
// 188 frames, so taking the whole cut there would have left 38 - 17.5 km in
// 1.3s. The opening and the push carry the rest, proportionally.
import { marks } from "./geoData";

export const FPS = 30;
export const OLTREPO_DURATION = 240; // 8s

export const INTRO_FADE_IN = [0, 10] as const;

// The regions and the lines between them. The road runs down the Lombardia
// side of a watershed it shares with Piemonte and Emilia-Romagna.
export const BORDERS = [4, 22] as const;
export const REGION_LABEL_START = 10;
export const REGION_LABEL_STEP = 6;
// Close enough together that the four read as lighting up rather than as a
// queue - at this length there is no room for a queue.
export const REGION_LABEL_REVEAL = 12;
export const REGION_FADE = [42, 58] as const;

export const ZOOM_ROUTE = [44, 94] as const;
export const COMUNI = [52, 84] as const;

// The two legs, split at Casale Staffora where the road leaves the river and
// starts climbing. One colour either side of that split - the split only sets
// the speed now: 0.77 map units a frame along the valley, 0.52 up the climb,
// because the switchbacks to the pass are still the point of the ride.
export const ROAD_VALLE = [96, 166] as const;
export const ROAD_SALITA = [162, 198] as const;

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
// second of the two: as a place on the road it is reached when the valley leg
// ends. The Giovà is simply where the road stops.
export const CASALE_ARRIVAL = ROAD_VALLE[1];
export const GIOVA_ARRIVAL = ROAD_SALITA[1];

// Tighter than it was: the pin has to land with the line and its name has to
// be fully up with time left to read it, inside a 42-frame ending.
export const pinCue = (arrival: number) =>
  ({
    dropRange: [arrival - 16, arrival + 8] as const,
    labelRange: [arrival + 2, arrival + 18] as const,
  }) as const;
