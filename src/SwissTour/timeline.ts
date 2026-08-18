// Central timeline for the SwissAlpsTour composition, in frames @ 30fps.
// Tuned for short-form vertical video (Reels/TikTok): ~11s, quick beats.
export const FPS = 30;
export const DURATION = 330; // 11s

export const INTRO_FADE_IN = [0, 15] as const;
export const TITLE_HOLD = [15, 48] as const;
export const TITLE_FADE_OUT = [48, 66] as const;

export const CAMERA_ZOOM = [42, 105] as const;

export const PIN_DROP = [95, 124] as const;
export const PIN_LABEL = [116, 138] as const;

export const ROUTE_A = [135, 205] as const; // Airolo -> Furka
export const ROUTE_B = [205, 265] as const; // Furka -> Nufenenpass

export const ARRIVAL_PULSE = [265, 295] as const;

export const FINAL_CARD = [272, 315] as const;
export const OUTRO_FADE = [312, 330] as const;
