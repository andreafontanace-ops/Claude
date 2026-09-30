#!/usr/bin/env python3
"""A still photo as a 9:16 clip that moves like a time-lapse shot on a slider:
the clouds race across, and the camera dollies forward with parallax.

    python3 scripts/photo/cinemagraph.py PHOTO.png SKY_MASK.png OUT.mp4 \\
        --horizon 835,650 [--center-x 850] [--seconds 8] \\
        [--speed 60] [--dolly 0.22] [--push 0.05]

PHOTO is usually the output of remove_people.py and SKY_MASK that of
sky_mask.py. Positions are in the photo's pixels.

The sky: one layer that really travels, faster higher up (nearer clouds cross
the frame faster), and churns as it goes so the clouds change shape. What it
travels over - the sky hidden behind the mountains, the town, the tower - is
rebuilt with LaMa from the sky around it, so clouds slide out from behind
the ridges instead of stopping at them. Only sky well inside the mask is
kept as it is: the pixels on its edge still carry some mountain or stone and
would drag a ghost of the skyline along.

The camera: a dolly towards --horizon (the vanishing point, on the horizon).
Treating everything below the horizon as ground, a point's distance goes
with 1/(its height below the horizon), so a forward move makes the near
ground - the bridge deck, the parapets - spread out much faster than the far
valley, while the town, hills and sky barely change. --dolly is how much the
bottom edge of the frame grows by the end; --push adds a plain zoom on top.

Needs opencv, numpy, Pillow, ffmpeg (hyperframes/bin/ffmpeg or on PATH) and,
for the sky plate, torch + remove_people.py's LaMa (else OpenCV's fill).
"""
import argparse, os, shutil, subprocess, sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OW, OH = 1080, 1920


def ffmpeg():
    local = os.path.join(REPO, "hyperframes", "bin", "ffmpeg")
    return local if os.path.exists(local) else shutil.which("ffmpeg")


def smoothstep(t):
    return t * t * (3 - 2 * t)


def fill_behind(big, sky_in, rows):
    """The sky plate: sky_in kept, everything else in the top `rows` rebuilt
    as sky. LaMa at half size - clouds are soft, and it sees only sky, so it
    can only invent more sky."""
    top = big[:rows]
    hole = (~sky_in[:rows]).astype(np.uint8) * 255
    hole = cv2.dilate(hole, np.ones((3, 3), np.uint8), iterations=2)
    h, w = top.shape[:2]
    try:
        sys.path.insert(0, HERE)
        from remove_people import inpaint, model
        small = Image.fromarray(cv2.resize(top, (w // 2, h // 2), interpolation=cv2.INTER_AREA))
        small_hole = Image.fromarray(cv2.resize(hole, (w // 2, h // 2), interpolation=cv2.INTER_NEAREST))
        filled = np.asarray(inpaint(model(), small, small_hole))
        how = "LaMa"
    except ImportError:
        small = cv2.resize(top, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
        small_hole = cv2.resize(hole, (w // 4, h // 4), interpolation=cv2.INTER_NEAREST)
        filled = cv2.cvtColor(cv2.inpaint(cv2.cvtColor(small, cv2.COLOR_RGB2BGR), small_hole, 9,
                                          cv2.INPAINT_TELEA), cv2.COLOR_BGR2RGB)
        how = "OpenCV"
    filled = cv2.resize(filled, (w, h), interpolation=cv2.INTER_CUBIC)
    keep = cv2.GaussianBlur(sky_in[:rows].astype(np.float32), (0, 0), 2.5)[..., None]
    print(f"sky plate rebuilt behind the skyline with {how}")
    return (top * keep + filled * (1 - keep)).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("photo")
    ap.add_argument("sky")
    ap.add_argument("out")
    ap.add_argument("--horizon", required=True, help="x,y: the vanishing point the camera moves towards")
    ap.add_argument("--center-x", type=float, help="where the 9:16 window sits; default the horizon point")
    ap.add_argument("--seconds", type=float, default=8)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--speed", type=float, default=60.0, help="cloud speed at the top of the frame, px/s")
    ap.add_argument("--dolly", type=float, default=0.22, help="growth of the frame's bottom edge by the end")
    ap.add_argument("--push", type=float, default=0.05, help="plain zoom on top of the dolly")
    args = ap.parse_args()

    src = np.asarray(Image.open(args.photo).convert("RGB"))
    sky_src = np.asarray(Image.open(args.sky).convert("L")) > 127
    h0, w0 = src.shape[:2]
    s = max(OH / h0, OW / w0)
    W, H = round(w0 * s), round(h0 * s)
    hx, hy = (float(v) for v in args.horizon.split(","))
    cx = args.center_x if args.center_x is not None else hx
    X0 = int(min(max(0, round(cx * s - OW / 2)), W - OW))
    Y0 = (H - OH) // 2
    VX, VY = hx * s - X0, hy * s - Y0  # in window pixels

    big = cv2.resize(src, (W, H), interpolation=cv2.INTER_LANCZOS4)
    blur = cv2.GaussianBlur(big, (0, 0), 1.2)
    big = cv2.addWeighted(big, 1.35, blur, -0.35, 0)  # back some crispness after enlarging
    sky = cv2.resize(sky_src.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST).astype(bool)
    rows = int(np.nonzero(sky.any(axis=1))[0].max()) + 40
    sky_in = cv2.erode(sky.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=10).astype(bool)
    plate = fill_behind(big, sky_in, rows)
    alpha = cv2.GaussianBlur(sky[:rows].astype(np.float32), (0, 0), 1.5)[..., None]

    # Nearer clouds cross faster: full speed at the top, about half at the
    # lowest sky. Depends on height only, so the clouds shear a little but
    # never stretch.
    yy, xx = np.mgrid[0:rows, 0:W].astype(np.float32)
    rate = args.speed * (1.0 - 0.5 * np.clip(yy / rows, 0, 1))
    rng = np.random.default_rng(7)
    waves = [(rng.uniform(0.002, 0.005), rng.uniform(-0.004, 0.004), rng.uniform(0.9, 1.8), rng.uniform(0, 6.28))
             for _ in range(5)]
    need = args.speed * args.seconds
    if X0 - need < 0:
        print(f"note: the clouds travel {need:.0f}px but only {X0}px of sky lies left of the frame; "
              "the rest is mirrored")

    # The dolly, as an inverse map from window pixels to the frame before it.
    oy, ox = np.mgrid[0:OH, 0:OW].astype(np.float32)
    below = np.maximum(oy - VY, 0)
    a_end = args.dolly / max(1.0, OH - VY)

    n = round(args.fps * args.seconds)
    proc = subprocess.Popen(
        [ffmpeg(), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}",
         "-r", str(args.fps), "-i", "-", "-c:v", "libx264", "-crf", "16", "-preset", "slow",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", args.out],
        stdin=subprocess.PIPE)
    for f in range(n):
        t = f / args.fps
        bx = np.zeros_like(xx); by = np.zeros_like(yy)
        for kx, ky, w, ph in waves:  # churn: the clouds change shape as they go
            bx += 4.0 * np.sin(kx * xx + ky * yy + w * t + ph)
            by += 3.0 * np.cos(ky * xx + kx * yy + w * t * 0.8 + ph)
        moved = cv2.remap(plate, xx - rate * t - bx, yy - by, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        frame = big.copy()
        frame[:rows] = (moved * alpha + big[:rows] * (1 - alpha)).astype(np.uint8)
        frame = frame[Y0:Y0 + OH, X0:X0 + OW]

        e = smoothstep(f / max(1, n - 1))
        grow = 1 + a_end * e * below          # dolly: more the nearer the ground
        z = 1 + args.push * e                 # and a plain push on top
        k = grow * z
        mx = VX + (ox - VX) / k
        my = VY + (oy - VY) / k
        frame = cv2.remap(frame, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        proc.stdin.write(np.ascontiguousarray(frame).tobytes())
        if f in (0, n // 2, n - 1):
            Image.fromarray(frame).save(os.path.splitext(args.out)[0] + f"-frame{f:03d}.png")
    proc.stdin.close()
    proc.wait()
    print(f"wrote {args.out}: {n} frames, {args.seconds:g}s, {OW}x{OH}")


if __name__ == "__main__":
    main()
