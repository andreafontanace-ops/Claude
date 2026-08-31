// Timeline for the AiroloFork composition, in frames @ 30fps.
// Two branches leave Airolo together and meet at Ulrichen, then the block
// of mountains they ran either side of lights up.
export const FORK_DURATION = 360; // 12s

// The intro beats deliberately match the SwissAlpsTour ones so the two
// videos open the same way; TitleCard reads those from ./timeline.

export const FORK_PIN_DROP = [84, 112] as const;
export const FORK_PIN_LABEL = [104, 126] as const;

export const OUTBOUND = [112, 252] as const; // Airolo -> Ulrichen, both branches

export const MASSIF_AREA = [258, 288] as const;
export const PEAK_ROTONDO = 276;
export const PEAK_LUCENDRO = 288;
export const MASSIF_LABEL = [292, 314] as const;
