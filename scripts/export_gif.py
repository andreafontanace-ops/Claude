#!/usr/bin/env python3
"""Turn a transparent PNG sequence (from `remotion render --sequence`) into a
looping GIF with a transparent background.

GIF transparency is 1-bit: a pixel is either fully see-through or fully
opaque. Alpha is thresholded, so compositions meant for GIF should avoid
fades and soft shadows (see src/Hook/HookStradaIsolata.tsx).

    python3 scripts/export_gif.py SEQ_DIR OUT.gif [--src-fps 30] [--fps 25]
                                  [--width 1080] [--threshold 128]

--fps defaults to 25 because GIF frame delays are whole centiseconds:
25 fps is exactly 4 cs per frame, 30 fps would drift (3.33 cs).
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

TRANSPARENT = 255  # palette index reserved for "no pixel"


def load(path, width, threshold):
    im = Image.open(path).convert("RGBA")
    if width and im.width != width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    a = np.asarray(im)
    return a[..., :3], a[..., 3] >= threshold


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("seq", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--src-fps", type=float, default=30)
    ap.add_argument("--fps", type=float, default=25)
    ap.add_argument("--width", type=int, default=0, help="output width in px (0 = keep)")
    ap.add_argument("--threshold", type=int, default=128, help="alpha at or above this is opaque")
    args = ap.parse_args()

    files = sorted(args.seq.glob("*.png"))
    if not files:
        sys.exit(f"no PNG frames in {args.seq}")

    # Resample by nearest source frame, keeping the full duration.
    n_out = max(1, round(len(files) * args.fps / args.src_fps))
    picks = [min(len(files) - 1, round(i * args.src_fps / args.fps)) for i in range(n_out)]
    frames = [load(files[i], args.width, args.threshold) for i in picks]

    # One global palette of 255 colours built from the opaque pixels of all
    # frames, so colours don't shimmer between frames.
    opaque = np.concatenate([rgb[mask] for rgb, mask in frames]) if any(m.any() for _, m in frames) else np.zeros((1, 3), np.uint8)
    step = max(1, len(opaque) // 1_000_000)
    sample = opaque[::step]
    swatch = Image.fromarray(sample.reshape(1, -1, 3))
    pal_img = swatch.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    palette = pal_img.getpalette()[: 255 * 3]
    palette += [0, 0, 0] * (256 - len(palette) // 3)
    pal_img.putpalette(palette)

    # Merge runs of identical frames ourselves, summing their delays: Pillow
    # would otherwise drop them (trailing empty frames lose their time).
    delay = round(1000 / args.fps)
    out, durations, prev = [], [], None
    for rgb, mask in frames:
        q = Image.fromarray(rgb).quantize(palette=pal_img, dither=Image.Dither.NONE)
        idx = np.asarray(q).copy()
        idx[~mask] = TRANSPARENT
        if prev is not None and np.array_equal(idx, prev):
            durations[-1] += delay
            continue
        prev = idx
        p = Image.fromarray(idx, "P")
        p.putpalette(palette)
        p.info["transparency"] = TRANSPARENT
        out.append(p)
        durations.append(delay)

    out[0].save(
        args.out,
        save_all=True,
        append_images=out[1:],
        duration=durations,
        loop=0,
        disposal=2,  # clear to transparent between frames: no ghosting
        transparency=TRANSPARENT,
        optimize=False,
    )
    kb = args.out.stat().st_size / 1024
    print(f"{args.out}: {len(out)} frames @ {args.fps:g} fps "
          f"({sum(durations) / 1000:.2f} s), {out[0].width}x{out[0].height}, {kb:.0f} KB")


if __name__ == "__main__":
    main()
