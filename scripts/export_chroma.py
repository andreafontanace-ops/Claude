#!/usr/bin/env python3
"""Turns a transparent PNG sequence into an MP4 on a flat key colour, for
editors that can't read alpha (CapCut, InShot, VN on a phone): lay the clip
over the footage and remove the colour with the editor's chroma key.

    python3 scripts/export_chroma.py SEQ_DIR OUT.mp4 [--key ff00ff] [--fps 30]

The key defaults to magenta, a colour none of the series' overlays use
(green would take spring's green with it). Edges are made hard - a pixel is
either the clip or the key - because a half-transparent edge or a soft
shadow blended into the key comes out as a coloured fringe after keying.
"""
import argparse, os, shutil, subprocess, sys

import numpy as np
from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ffmpeg():
    local = os.path.join(REPO, "hyperframes", "bin", "ffmpeg")
    return local if os.path.exists(local) else shutil.which("ffmpeg")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("seq")
    ap.add_argument("out")
    ap.add_argument("--key", default="ff00ff")
    ap.add_argument("--fps", type=int, default=30)
    args = ap.parse_args()

    files = sorted(f for f in os.listdir(args.seq) if f.endswith(".png"))
    if not files:
        sys.exit(f"no PNG frames in {args.seq}")
    w, h = Image.open(os.path.join(args.seq, files[0])).size
    key = np.array([int(args.key[i:i + 2], 16) for i in (0, 2, 4)], np.uint8)
    proc = subprocess.Popen(
        [ffmpeg(), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
         "-r", str(args.fps), "-i", "-", "-c:v", "libx264", "-crf", "14", "-preset", "slow",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", args.out],
        stdin=subprocess.PIPE)
    for f in files:
        a = np.asarray(Image.open(os.path.join(args.seq, f)).convert("RGBA"))
        frame = np.where(a[..., 3:4] >= 128, a[..., :3], key).astype(np.uint8)
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    proc.wait()
    print(f"wrote {args.out}: {len(files)} frames on #{args.key}")


if __name__ == "__main__":
    main()
