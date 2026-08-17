// Central timeline for the SwissAlpsTour composition, in frames @ 30fps.
export const FPS = 30;
export const DURATION = 600; // 20s

export const INTRO_FADE_IN = [0, 30] as const;
export const TITLE_HOLD = [30, 95] as const;
export const TITLE_FADE_OUT = [95, 130] as const;

export const CAMERA_ZOOM = [90, 200] as const;

export const PIN_DROP = [180, 222] as const;
export const PIN_LABEL = [212, 245] as const;

export const ROUTE_A = [235, 372] as const; // Airolo -> Furka
export const ROUTE_B = [372, 478] as const; // Furka -> Nufenenpass

export const ARRIVAL_PULSE = [468, 510] as const;

export const FINAL_CARD = [500, 575] as const;
export const OUTRO_FADE = [572, 600] as const;
