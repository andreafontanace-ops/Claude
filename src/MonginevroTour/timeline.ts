// Timeline for the Monginevro composition, in frames @30fps. 14s in four
// stages: the two countries, the passes along their border, the push-in onto
// the Colle del Monginevro, and the road that crosses from one to the other.
export const FPS = 30;
export const MONGINEVRO_DURATION = 420; // 14s

export const INTRO_FADE_IN = [0, 14] as const;
export const TITLE_HOLD = [14, 40] as const;
export const TITLE_FADE_OUT = [40, 56] as const;

export const ZOOM_PASSES = [48, 120] as const;

// The great crossings, north to south. The Monginevro is not among them: it
// belongs in the gap they leave, and the next push-in fills it.
export const PASS_DROP_START = 98;
export const PASS_DROP_STEP = 20;
export const PASS_LABEL_DELAY = 16;
export const PASS_FADE = [186, 212] as const;

export const ZOOM_ROUTE = [196, 266] as const;

export const COL_PIN_DROP = [260, 288] as const;
export const COL_PIN_LABEL = [280, 300] as const;

// The road is drawn in two legs so the frontier gets a beat of its own
// instead of flashing past mid-draw. Leg spans are proportional to each
// leg's real length, so the line advances at a steady speed.
export const ROAD_ITALIA = [296, 325] as const;
export const BORDER = [321, 355] as const;
export const ROAD_FRANCIA = [349, 405] as const;

export const CESANA_LABEL = 300;
export const CLAVIERE_LABEL = 320;
export const BRIANCON_LABEL = 396;
