// Timeline for the Monginevro composition, in frames @30fps. 14s, descending
// in three steps: France as one shape, the Alpine region where it opens into
// its departments and Italy appears in grey beside it, then the frontier and
// the road that crosses it.
export const FPS = 30;
export const MONGINEVRO_DURATION = 420; // 14s

export const INTRO_FADE_IN = [0, 14] as const;
export const TITLE_HOLD = [14, 40] as const;
export const TITLE_FADE_OUT = [40, 56] as const;

export const ZOOM_REGION = [48, 118] as const;

// France breaks into its departments on the way down, and Italy fades up
// alongside: neither is in the opening shot.
export const PATCHWORK = [66, 110] as const;
export const BEYOND = [58, 104] as const;

// The great crossings, north to south. The Monginevro is not among them: it
// belongs in the gap they leave, and the next push-in fills it.
export const PASS_DROP_START = 100;
export const PASS_DROP_STEP = 20;
export const PASS_LABEL_DELAY = 16;
export const PASS_FADE = [184, 210] as const;

export const ZOOM_ROUTE = [194, 264] as const;

export const COL_PIN_DROP = [258, 286] as const;
export const COL_PIN_LABEL = [278, 298] as const;

// The road is drawn in two legs so the frontier gets a beat of its own
// instead of flashing past mid-draw. Leg spans are proportional to each
// leg's real length, so the line advances at a steady speed.
export const ROAD_ITALIA = [294, 323] as const;
export const BORDER = [319, 353] as const;
export const ROAD_FRANCIA = [347, 403] as const;

export const CESANA_LABEL = 298;
export const CLAVIERE_LABEL = 318;
export const BRIANCON_LABEL = 394;
