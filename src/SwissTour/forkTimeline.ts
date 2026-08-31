// Timeline for the AiroloFork composition, in frames @ 30fps.
// Two branches leave Airolo together, meet in the Goms, then the same two
// roads are ridden back the other way, given the same time as the way out.
export const FORK_DURATION = 480; // 16s

// The intro beats deliberately match the SwissAlpsTour ones so the two
// videos open the same way; TitleCard reads those from ./timeline.

export const FORK_PIN_DROP = [84, 112] as const;
export const FORK_PIN_LABEL = [104, 126] as const;

export const OUTBOUND = [112, 252] as const; // Airolo -> Goms, both branches
export const GOMS_LINK = [252, 272] as const; // the valley road tying them
export const GHOST_FADE = [274, 294] as const; // drawn lines dim to a trace
export const RETURN = [294, 434] as const; // Goms -> Airolo, same two roads
