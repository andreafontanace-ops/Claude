export type Rect = { x: number; y: number; w: number; h: number };

// All three short-form players draw their own chrome over the video: a
// right-hand action rail (like / comment / share), a caption-and-handle
// block along the bottom, and a header strip at the top. The insets below
// are the widest of the three at 1080x1920, so anything kept inside this
// rect stays clear on TikTok, Reels and Shorts alike. They are approximate
// and shift between app versions and phone shapes, so they are deliberately
// generous rather than exact.
//
//                 right   bottom   top
//   TikTok         ~120    ~320    ~120
//   Instagram      ~180    ~420    ~250
//   YouTube        ~140    ~300    ~110
export const SAFE_RECT: Rect = { x: 60, y: 250, w: 840, h: 1250 };

// Where the title sits: inside the top of the safe rect, clear of the
// platform headers above it and of the map below.
export const SAFE_TITLE_TOP = 300;

export const FULL_RECT = (w: number, h: number): Rect => ({ x: 0, y: 0, w, h });
