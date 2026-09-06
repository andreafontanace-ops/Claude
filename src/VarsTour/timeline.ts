// Timeline for the ColDeVars composition, in frames @30fps. 14s, three
// stages: France and the title, the Route des Grandes Alpes passes, then
// the road itself.
export const FPS = 30;
export const VARS_DURATION = 420; // 14s

export const INTRO_FADE_IN = [0, 14] as const;
export const TITLE_HOLD = [14, 40] as const;
// Gone before the push-in gets going, so it never drifts over a moving map.
export const TITLE_FADE_OUT = [40, 56] as const;

// Stage 1 -> 2: all of France down onto the French Alps.
export const ZOOM_ALPS = [48, 120] as const;

// The passes land one after another, north to south, so the eye travels
// down the Route des Grandes Alpes instead of taking it in all at once.
export const PASS_DROP_START = 98;
export const PASS_DROP_STEP = 20;
export const PASS_LABEL_DELAY = 16;

// Everything except the Col de Vars steps back out of the frame.
export const PASS_FADE = [212, 238] as const;

// Stage 2 -> 3: down onto the pass and its road.
export const ZOOM_VARS = [222, 296] as const;

// The subject arrives only once the camera is down on it.
export const VARS_PIN_DROP = [292, 320] as const;
export const VARS_PIN_LABEL = [312, 332] as const;

export const ROAD_DRAW = [330, 404] as const;
export const GUILLESTRE_LABEL = 336;
export const SAINTPAUL_LABEL = 394;
