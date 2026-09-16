// Timeline for the Oltrepo composition, in frames @30fps. 12.3s, and only two
// things happen: the four regions that meet over this valley name themselves,
// then the camera drops onto the road and draws it.
import { marks } from "./geoData";

export const FPS = 30;
export const OLTREPO_DURATION = 370; // 12.3s

export const INTRO_FADE_IN = [0, 16] as const;

// The regions and the lines between them. The road runs down the Lombardia
// side of a watershed it shares with Piemonte and Emilia-Romagna.
export const BORDERS = [8, 36] as const;
export const REGION_LABEL_START = 20;
export const REGION_LABEL_STEP = 9;
export const REGION_FADE = [70, 92] as const;

export const ZOOM_ROUTE = [74, 146] as const;
export const COMUNI = [84, 124] as const;

// The two legs, split at Casale Staffora where the road leaves the river and
// starts climbing. The climb runs at about 60% of the valley's speed, because
// 3 km of hairpins to the pass is the point of the ride.
export const ROAD_VALLE = [152, 272] as const;
export const ROAD_SALITA = [268, 322] as const;

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

export const pinCue = (arrival: number) =>
  ({
    dropRange: [arrival - 14, arrival + 14] as const,
    labelRange: [arrival + 6, arrival + 26] as const,
  }) as const;
