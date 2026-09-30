#!/usr/bin/env python3
"""A still photo as a 9:16 clip: the photo stays still, the clouds drift and
billow, and the frame pushes slowly in.

    python3 scripts/photo/cinemagraph.py PHOTO.png SKY_MASK.png OUT.mp4 \\
        [--center-x 850] [--focus 835,700] [--seconds 8] [--speed 11] [--push 0.07]

PHOTO is usually the output of remove_people.py and SKY_MASK that of
sky_mask.py. --center-x is where the 9:16 window sits in the photo, --focus
the point the push closes in on, both in the photo's pixels.

How the sky moves without tearing:
  - only sky well inside the mask goes on the moving plate: the pixels at its
    edge still carry some mountain or stone, and dragged along they would draw
    a ghost of the skyline. What is behind the mountains is filled in softly;
  - how far a pixel may move grows with its distance from the skyline (high
    clouds are nearer, and move faster), from 30% at the edge to full speed
    260px above it, so the clouds stretch gently rather than smear.
Needs opencv, numpy, Pillow and ffmpeg (hyperframes/bin/ffmpeg or on PATH).
"""
import argparse, os, shutil, subprocess

import cv2
import numpy as np
from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OW, OH = 1080, 1920


def ffmpeg():
    local = os.path.join(REPO, "hyperframes", "bin", "ffmpeg")
    return local if os.path.exists(local) else shutil.which("ffmpeg")


def smoothstep(t):
    return t * t * (3 - 2 * t)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("photo")
    ap.add_argument("sky")
    ap.add_argument("out")
    ap.add_argument("--center-x", type=float, help="photo px; default the middle")
    ap.add_argument("--focus", help="x,y in photo px; default the window centre")
    ap.add_argument("--seconds", type=float, default=8)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--speed", type=float, default=11.0, help="cloud drift, output px per second")
    ap.add_argument("--push", type=float, default=0.07, help="zoom gained over the clip")
    args = ap.parse_args()

    src = np.asarray(Image.open(args.photo).convert("RGB"))
    sky_src = np.asarray(Image.open(args.sky).convert("L")) > 127
    h0, w0 = src.shape[:2]
    s = max(OH / h0, OW / w0)
    W, H = round(w0 * s), round(h0 * s)
    cx = args.center_x if args.center_x is not None else w0 / 2
    X0 = int(min(max(0, round(cx * s - OW / 2)), W - OW))
    Y0 = (H - OH) // 2
    fx, fy = (float(v) for v in args.focus.split(",")) if args.focus else ((X0 + OW / 2) / s, (Y0 + OH / 2) / s)
    FX, FY = fx * s - X0, fy * s - Y0

    big = cv2.resize(src, (W, H), interpolation=cv2.INTER_LANCZOS4)
    blur = cv2.GaussianBlur(big, (0, 0), 1.2)
    big = cv2.addWeighted(big, 1.35, blur, -0.35, 0)  # back some crispness after enlarging
    sky = cv2.resize(sky_src.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST).astype(bool)

    sky_in = cv2.erode(sky.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=10).astype(bool)
    small = cv2.resize(big, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    hole = cv2.resize((~sky_in).astype(np.uint8) * 255, (W // 4, H // 4), interpolation=cv2.INTER_NEAREST)
    hole = cv2.dilate(hole, np.ones((3, 3), np.uint8), iterations=1)
    filled = cv2.inpaint(cv2.cvtColor(small, cv2.COLOR_RGB2BGR), hole, 9, cv2.INPAINT_TELEA)
    filled = cv2.cvtColor(cv2.resize(filled, (W, H), interpolation=cv2.INTER_CUBIC), cv2.COLOR_BGR2RGB)
    keep = cv2.GaussianBlur(sky_in.astype(np.float32), (0, 0), 2.5)[..., None]
    plate = (big * keep + filled * (1 - keep)).astype(np.uint8)

    dist = cv2.distanceTransform(sky.astype(np.uint8), cv2.DIST_L2, 5)
    free = 0.3 + 0.7 * smoothstep(np.clip(dist / 260.0, 0, 1))
    alpha = cv2.GaussianBlur(sky.astype(np.float32), (0, 0), 1.5)[..., None]

    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    rng = np.random.default_rng(7)
    waves = [(rng.uniform(0.002, 0.006), rng.uniform(-0.004, 0.004), rng.uniform(0.3, 0.7), rng.uniform(0, 6.28))
             for _ in range(4)]

    n = round(args.fps * args.seconds)
    proc = subprocess.Popen(
        [ffmpeg(), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}",
         "-r", str(args.fps), "-i", "-", "-c:v", "libx264", "-crf", "16", "-preset", "slow",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", args.out],
        stdin=subprocess.PIPE)
    for f in range(n):
        t = f / args.fps
        bx = np.zeros_like(xx); by = np.zeros_like(yy)
        for kx, ky, w, ph in waves:  # billow: slow, a few px, on top of the drift
            bx += 3.0 * np.sin(kx * xx + ky * yy + w * t + ph)
            by += 2.0 * np.cos(ky * xx + kx * yy + w * t * 0.8 + ph)
        dx = (args.speed * t + bx) * free
        dy = by * free
        moved = cv2.remap(plate, xx - dx, yy - dy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        frame = (moved * alpha + big * (1 - alpha)).astype(np.uint8)[Y0:Y0 + OH, X0:X0 + OW]
        z = 1 + args.push * smoothstep(f / max(1, n - 1))
        M = np.float32([[z, 0, FX * (1 - z)], [0, z, FY * (1 - z)]])
        frame = cv2.warpAffine(frame, M, (OW, OH), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        proc.stdin.write(np.ascontiguousarray(frame).tobytes())
    proc.stdin.close()
    proc.wait()
    print(f"wrote {args.out}: {n} frames, {args.seconds:g}s, {OW}x{OH}")


if __name__ == "__main__":
    main()
