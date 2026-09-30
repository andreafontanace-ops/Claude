// Timeline for the Bobbio - Passo del Penice - Varzi composition, in frames
// @30fps. 9s. The pass is the subject, so the film is built around it: the
// whole road is shown, the camera goes in close and rides the climb, stops on
// the pass while it is named, rides the descent, and pulls back out to the
// whole road as Varzi lands.
export const FPS = 30;
export const PENICE_DURATION = 270; // 9s

export const INTRO_FADE_IN = [0, 10] as const;

// The opening push from the wider map onto the whole road.
export const OPEN_PUSH = [0, 26] as const;

export const BOBBIO_PIN = { dropRange: [4, 28], labelRange: [18, 34] } as const;

// Up from Bobbio to the pass: 12.6 km.
export const CLIMB = [30, 116] as const;
// Held on the pass while it is named.
export const PASS_HOLD = [116, 146] as const;
// Down to Varzi: 15.3 km.
export const DESCENT = [146, 226] as const;

// The camera: in close behind the dot for the climb, a small push onto the
// pass, and back out to the whole road for the arrival.
export const FOLLOW_IN = [20, 50] as const;
export const PASS_PUSH_IN = [108, 128] as const;
export const PASS_PUSH_OUT = [138, 160] as const;
export const FOLLOW_OUT = [206, 244] as const;

// The whole road, faint, from the start: where the red line is headed.
export const GHOST_IN = [6, 24] as const;

export const MONTE_PENICE_IN = [96, 112] as const;
export const REGION_TAGS_IN = [124, 140] as const;
// The close-up furniture clears as the camera pulls back, leaving the three
// names, the road and the closing card.
export const DETAIL_OUT = [206, 222] as const;
export const SUMMARY_IN = [238, 254] as const;

// RoutePath advances with Easing.inOut(cubic), so the drawn line passes arc
// fraction t later or sooner than the linear reading - this is the inverse.
const easeInOutCubicInverse = (e: number) =>
  e < 0.5 ? Math.cbrt(e / 4) : 1 - Math.cbrt(2 - 2 * e) / 2;

export const frameAt = (range: readonly [number, number], t: number): number =>
  Math.round(range[0] + (range[1] - range[0]) * easeInOutCubicInverse(t));

// A pin that lands with the line rather than after it.
export const pinCue = (arrival: number) =>
  ({
    dropRange: [arrival - 16, arrival + 8] as const,
    labelRange: [arrival + 2, arrival + 18] as const,
  }) as const;
