#!/usr/bin/env python3
"""Removes people (or anything else) from a photo with LaMa inpainting.

    python3 scripts/photo/remove_people.py IN.jpg OUT.png \\
        --box 767,719,808,794 --box 808,634,832,668

Each --box is x0,y0,x1,y1 in the photo's pixels, drawn generously round one
person. LaMa (big-lama, Apache-2.0) rebuilds what was behind them; only the
pixels inside the boxes change, everything else stays the original photo.
LaMa works best near the 512px it was trained at, so when all the boxes fit
in a 512px window it only sees that window.

Needs torch; the model (200MB) is fetched from GitHub on first use into
~/.cache/lama. Writes OUT and OUT-before-after.png for checking.
"""
import argparse, os, urllib.request

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFilter

MODEL_URL = "https://github.com/enesmsahin/simple-lama-inpainting/releases/download/v0.1.0/big-lama.pt"
MODEL = os.path.expanduser("~/.cache/lama/big-lama.pt")


def model():
    if not os.path.exists(MODEL):
        os.makedirs(os.path.dirname(MODEL), exist_ok=True)
        print("downloading big-lama ...")
        urllib.request.urlretrieve(MODEL_URL, MODEL)
    return torch.jit.load(MODEL, map_location="cpu").eval()


def inpaint(net, img, mask):
    w, h = img.size
    pw, ph = -w % 8, -h % 8  # LaMa wants sides divisible by 8
    a = np.pad(np.asarray(img).astype(np.float32) / 255, ((0, ph), (0, pw), (0, 0)), mode="reflect")
    m = np.pad((np.asarray(mask) > 127).astype(np.float32), ((0, ph), (0, pw)))
    with torch.no_grad():
        out = net(torch.from_numpy(a).permute(2, 0, 1)[None], torch.from_numpy(m)[None, None])
    out = out[0].permute(1, 2, 0).clamp(0, 1).numpy()[:h, :w]
    return Image.fromarray((out * 255).round().astype(np.uint8))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--box", action="append", required=True, help="x0,y0,x1,y1")
    args = ap.parse_args()

    im = Image.open(args.src).convert("RGB")
    boxes = [tuple(int(v) for v in b.split(",")) for b in args.box]
    mask = Image.new("L", im.size, 0)
    for b in boxes:
        ImageDraw.Draw(mask).rectangle(b, fill=255)
    mask = mask.filter(ImageFilter.MaxFilter(5))

    x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes)
    x1 = max(b[2] for b in boxes); y1 = max(b[3] for b in boxes)
    S = 512
    if x1 - x0 < S - 64 and y1 - y0 < S - 64 and im.width >= S and im.height >= S:
        wx = min(max(0, (x0 + x1) // 2 - S // 2), im.width - S)
        wy = min(max(0, (y0 + y1) // 2 - S // 2), im.height - S)
        window = (wx, wy, wx + S, wy + S)
    else:
        window = (0, 0, im.width, im.height)

    win, mwin = im.crop(window), mask.crop(window)
    filled = inpaint(model(), win, mwin)
    soft = mwin.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.5))
    clean = im.copy()
    clean.paste(Image.composite(filled, win, soft), window[:2])
    clean.save(args.out)

    # Before / after of the area worked on, enlarged.
    pad = 40
    area = (max(0, x0 - pad), max(0, y0 - pad), min(im.width, x1 + pad), min(im.height, y1 + pad))
    k = max(1, 600 // max(area[2] - area[0], area[3] - area[1]))
    size = ((area[2] - area[0]) * k, (area[3] - area[1]) * k)
    ba = Image.new("RGB", (size[0] * 2, size[1]))
    ba.paste(im.crop(area).resize(size, Image.LANCZOS), (0, 0))
    ba.paste(clean.crop(area).resize(size, Image.LANCZOS), (size[0], 0))
    ba.save(os.path.splitext(args.out)[0] + "-before-after.png")
    print(f"wrote {args.out} ({len(boxes)} boxes, LaMa window {window})")


if __name__ == "__main__":
    main()
