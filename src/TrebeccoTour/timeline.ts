// Timeline for the Varzi - Zavattarello - Trebecco composition, in frames
// @30fps. 11s: down from the four regions onto the Oltrepò, the SP207 to
// Zavattarello with the villages named as the line reaches them, a close-up
// on the Castello Dal Verme, then the white road to Trebecco.
export const FPS = 30;
export const TREBECCO_DURATION = 330; // 11s

// From 150 km across down onto the road.
export const INTRO_ZOOM = [0, 78] as const;
export const REGION_NAMES_OUT = [46, 64] as const;
// The comuni and the road network come up as the camera arrives.
export const MAP_DETAIL_IN = [36, 72] as const;
export const REGION_TAGS_IN = [74, 92] as const;
// The marker on the road while it is a speck in the opening.
export const TARGET_OUT = [52, 66] as const;

export const VARZI_PIN = { dropRange: [62, 86], labelRange: [76, 92] } as const;

// Varzi - Zavattarello, 12.7 km on the SP207.
export const LEG1 = [86, 186] as const;

// The castle close-up, landing as the line reaches Zavattarello.
export const CASTLE_IN = [182, 206] as const;
export const CASTLE_SHOW = [198, 214] as const;
export const CASTLE_OUT = [236, 258] as const;

// Zavattarello - Trebecco, 7.2 km, most of it white road.
export const LEG2 = [240, 302] as const;
export const LAKE_IN = [262, 280] as const;

export const SUMMARY_IN = [308, 324] as const;

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
