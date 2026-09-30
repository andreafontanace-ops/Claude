#!/usr/bin/env python3
"""Finds the sky in a landscape photo: the bright, grey-white or blue region
connected to the top edge. Writes a black/white mask and a magenta preview.

    python3 scripts/photo/sky_mask.py IN.png MASK.png [--protect x0,y0,x1,y1 ...]
        [--min-bright 182]

--min-bright separates clouds from hazy distant mountains (on the Ponte Gobbo
photo the far mountains top out near 170, the clouds start above 180).
--protect keeps thin things - a cross, an aerial, wires - out of the sky, which
the morphological cleanup would otherwise swallow.
"""
import argparse, os

import numpy as np
from PIL import Image
from scipy import ndimage as ndi


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--protect", action="append", default=[], help="x0,y0,x1,y1")
    ap.add_argument("--min-bright", type=float, default=182)
    ap.add_argument("--max-row", type=float, default=0.5, help="the sky ends above this fraction of the height")
    args = ap.parse_args()

    im = np.asarray(Image.open(args.src).convert("RGB")).astype(np.float32)
    H, W, _ = im.shape
    r, b = im[..., 0], im[..., 2]
    mx, mn = im.max(-1), im.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1)
    cand = ((mx > args.min_bright) & (sat < 0.3)) | ((b > 190) & (b > r + 30))
    cand[int(H * args.max_row):] = False
    cand = ndi.binary_opening(cand, iterations=2)
    lab, _ = ndi.label(cand)
    sky = np.isin(lab, list(set(np.unique(lab[0])) - {0}))
    sky = ndi.binary_closing(sky, iterations=3)
    sky = ndi.binary_fill_holes(sky)
    for p in args.protect:
        x0, y0, x1, y1 = (int(v) for v in p.split(","))
        sky[y0:y1, x0:x1] = False

    Image.fromarray((sky * 255).astype(np.uint8)).save(args.out)
    prev = im.copy()
    prev[sky] = prev[sky] * 0.4 + np.array([255, 0, 255]) * 0.6
    Image.fromarray(prev.astype(np.uint8)).resize((W // 2, H // 2)).save(
        os.path.splitext(args.out)[0] + "-preview.png")
    print(f"wrote {args.out}: {sky.mean():.0%} of the photo is sky")


if __name__ == "__main__":
    main()
