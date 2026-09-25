// Timeline for the Giovà - Brallo composition, in frames @30fps. 12s:
//
//   the destination is named, the easy road is drawn to it (3s), crossed out,
//   and then the ridge road is drawn to the same place (5s).
//
// Both roads start at the Passo del Giovà and end at Brallo di Pregola, so the
// film is a comparison with one start and one finish, not two journeys.
import { marks } from "./geoData";

export const FPS = 30;
export const GIOVA_BRALLO_DURATION = 360; // 12s

export const INTRO_FADE_IN = [0, 12] as const;

// One slow push, done before the X lands: moving the frame under the X would
// make it look like it is sliding off the road.
export const CAMERA_PUSH = [0, 110] as const;

export const GIOVA_PIN = { dropRange: [6, 30], labelRange: [22, 40] } as const;

export const ROAD_FACILE = [28, 118] as const;

// Brallo di Pregola is named when the easy road reaches it, so by the time the
// ridge road sets off the viewer already knows where it is going.
export const BRALLO_PIN = { dropRange: [110, 134], labelRange: [126, 144] } as const;

export const CROSS_OUT = [142, 162] as const;

export const ROAD_CRINALE = [172, 322] as const;

// RoutePath advances with Easing.inOut(cubic), so a place sitting at arc
// fraction t is reached later or sooner than the linear reading of the road's
// frame range - this is the inverse of that curve.
const easeInOutCubicInverse = (e: number) =>
  e < 0.5 ? Math.cbrt(e / 4) : 1 - Math.cbrt(2 - 2 * e) / 2;

// The frame at which the drawn line reaches a place on a given road.
export const arrivalFrame = (road: "facile" | "crinale", id: string): number => {
  const [from, to] = road === "facile" ? ROAD_FACILE : ROAD_CRINALE;
  return Math.round(from + (to - from) * easeInOutCubicInverse(marks[road][id]));
};

// The frame at which the drawn line passes a given fraction of its road.
export const roadFrameAt = (road: "facile" | "crinale", t: number): number => {
  const [from, to] = road === "facile" ? ROAD_FACILE : ROAD_CRINALE;
  return Math.round(from + (to - from) * easeInOutCubicInverse(t));
};

// Where along each road its number plate sits: on stretches running north,
// so a sideways offset puts the plate beside the line rather than on it.
export const SHIELD_AT = { facile: 0.65, crinale: 0.4 } as const;

// A pin that lands with the line rather than after it.
export const pinCue = (arrival: number) =>
  ({
    dropRange: [arrival - 16, arrival + 8] as const,
    labelRange: [arrival + 2, arrival + 18] as const,
  }) as const;
