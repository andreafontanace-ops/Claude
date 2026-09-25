// Timeline for the Brallo - Bobbio composition, in frames @30fps. 8s: Brallo
// is named, the road is drawn to Bobbio, Bobbio is named, and the valley it
// sits in.
export const FPS = 30;
export const BRALLO_BOBBIO_DURATION = 240; // 8s

export const INTRO_FADE_IN = [0, 10] as const;

// A slow push, done before the road is half drawn so the frame is still by
// the time the names start landing.
export const CAMERA_PUSH = [0, 70] as const;

export const BRALLO_PIN = { dropRange: [4, 28], labelRange: [20, 36] } as const;

// 5.3s for 17 km: the one road is the whole film.
export const ROAD = [26, 186] as const;

export const VAL_TREBBIA = [192, 210] as const;

// RoutePath advances with Easing.inOut(cubic), so the drawn line passes arc
// fraction t later or sooner than the linear reading - this is the inverse.
const easeInOutCubicInverse = (e: number) =>
  e < 0.5 ? Math.cbrt(e / 4) : 1 - Math.cbrt(2 - 2 * e) / 2;

export const roadFrameAt = (t: number): number =>
  Math.round(ROAD[0] + (ROAD[1] - ROAD[0]) * easeInOutCubicInverse(t));

// A pin that lands with the line rather than after it.
export const pinCue = (arrival: number) =>
  ({
    dropRange: [arrival - 16, arrival + 8] as const,
    labelRange: [arrival + 2, arrival + 18] as const,
  }) as const;
