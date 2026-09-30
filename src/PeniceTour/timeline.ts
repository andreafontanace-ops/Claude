// Timeline for the Bobbio - Passo del Penice - Varzi composition, in frames
// @30fps. 9s. The pass is the subject, so the film is built around it: it
// opens in close on Bobbio, rides the climb, stops on the pass while it is
// named, rides the descent, and pulls back out to the whole road as Varzi
// lands.
export const FPS = 30;
export const PENICE_DURATION = 270; // 9s

export const BOBBIO_PIN = { dropRange: [2, 24], labelRange: [14, 30] } as const;

// Up from Bobbio to the pass: 12.6 km.
export const CLIMB = [22, 112] as const;
// Held on the pass while it is named.
export const PASS_HOLD = [112, 142] as const;
// Down to Varzi: 15.3 km.
export const DESCENT = [142, 224] as const;

// The camera: in close behind the dot from the first frame, a small push
// onto the pass, and back out to the whole road for the arrival.
export const PASS_PUSH_IN = [104, 124] as const;
export const PASS_PUSH_OUT = [134, 156] as const;
export const FOLLOW_OUT = [206, 244] as const;

// The whole road, faint, from the start: where the red line is headed.
export const GHOST_IN = [4, 20] as const;

export const MONTE_PENICE_IN = [92, 108] as const;
// The close-up furniture - the peak, the plates, the region names set for
// the close framing - clears as the camera pulls back; the region names set
// for the whole-road framing take over.
export const DETAIL_OUT = [206, 222] as const;
export const WIDE_TAGS_IN = [230, 246] as const;
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
