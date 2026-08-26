// Central timeline for the SwissAlpsTour composition, in frames @ 30fps.
// Tuned for short-form vertical video (Reels/TikTok): ~11s, quick beats.
export const FPS = 30;
export const DURATION = 330; // 11s

export const INTRO_FADE_IN = [0, 14] as const;
export const TITLE_HOLD = [14, 42] as const;
export const TITLE_FADE_OUT = [42, 58] as const;

export const CAMERA_ZOOM = [38, 96] as const;

export const PIN_DROP = [84, 112] as const;
export const PIN_LABEL = [104, 124] as const;

// The ride is one loop, drawn in three legs. Leg spans are proportional to
// each leg's real length so the line advances at a roughly steady speed.
export const ROUTE_A = [120, 186] as const; // Airolo -> Gottardo -> Furka
export const ROUTE_B = [186, 224] as const; // Furka -> Nufenenpass
export const ROUTE_C = [224, 260] as const; // Nufenenpass -> Val Bedretto -> Airolo

export const ARRIVAL_PULSE = [224, 254] as const;

export const FINAL_CARD = [264, 302] as const;
export const OUTRO_FADE = [314, 330] as const;
