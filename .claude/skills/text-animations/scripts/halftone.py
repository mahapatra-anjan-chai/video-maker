#!/usr/bin/env python3
"""An animated halftone background: pale blobs drift and morph; around each one a warm glow and a band of halftone
dots, biggest just outside the blob's edge and fading out into the paper.
A seamless loop at any size, coloured from a look, to lay under titles, cards and UI.

  python3 halftone.py --look brand --size 1920x1080 --dur 12 --out bg.mp4
  python3 halftone.py --look mycompany --mode dark --size 1080x1920 --out bg.mp4      a look kept on this Mac works too
  python3 halftone.py --colors "#FFF8F2,#F6C9A8,#E8633F,#F4A37E" --out bg.mp4     paper, soft blob, dots, second dots
  python3 halftone.py --look brand --still bg.png                                  one frame, to preview in the chat

--look reads .claude/skills/youtube-edit/styles/<look>.json (its highlight, anchor and punchline colours). Light mode:
a near-white paper tinted by the highlight, soft blobs in the highlight, dots in the punchline and anchor. Dark mode:
the look's dark colour as paper, blobs in the anchor, dots in the highlight and punchline. --speed 1-3 sets the drift;
--grid is the number of dot columns (one dot per ~11 px by default). Deterministic: the same arguments give the same frames, and the last frame
leads back into the first.

In HyperFrames, put the MP4 in an untimed layer as a muted <video> with its own data-start (see hyperframes-core);
in fast-cut, as the footage of a segment.
"""
import argparse, json, math, os, subprocess, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
STYLES = os.path.join(os.path.dirname(os.path.dirname(HERE)), "youtube-edit", "styles")


def hexrgb(h):
    h = h.strip().lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32)


def mix(a, b, t):
    return a * (1 - t) + b * t


def palette(look=None, colors=None, mode="light"):
    """(paper, soft, dot, dot2) as RGB arrays."""
    if colors:
        c = [hexrgb(x) for x in colors.split(",")]
        while len(c) < 4:
            c.append(c[-1])
        return c[:4]
    path = os.path.join(STYLES, look + ".json") if look else None
    if not path or not os.path.exists(path):
        sys.exit("no look named %r in %s (or give --colors)" % (look, STYLES))
    j = json.load(open(path))
    col = {k: hexrgb(v) for k, v in (j.get("colors") or {}).items() if isinstance(v, str) and v.startswith("#")}
    dark = [hexrgb(v) for v in (j.get("extra_colors") or {}).values() if isinstance(v, str) and v.startswith("#")]
    hi = col.get("cyan"); anchor = col.get("blue"); punch = col.get("magenta")
    if hi is None or anchor is None or punch is None:             # a look with other names: by lightness
        vals = sorted([v for v in col.values() if v.sum() < 740], key=lambda v: -v.sum())
        if len(vals) < 2:
            sys.exit("the look %r needs at least two colours besides white" % look)
        hi, anchor, punch = vals[0], vals[-1], vals[len(vals) // 2]
    white = np.array([255, 255, 255], np.float32)
    if mode == "dark":
        paper = dark[0] if dark else mix(anchor, np.zeros(3, np.float32), 0.8)
        return [paper, mix(paper, anchor, 0.55), hi, punch]
    return [mix(white, hi, 0.07), mix(white, hi, 0.55), punch, anchor]


def field(gx, gy, theta, aspect, speed=1.0):
    """Soft blobs on closed paths (the loop is seamless: everything turns with theta = 2 pi t / dur)."""
    th = theta * speed
    blobs = [(0.20, 0.30, 0.16, 0.14, 1, 2, 0.0, 0.17), (0.80, 0.22, 0.14, 0.16, 2, 1, 1.7, 0.15),
             (0.55, 0.80, 0.20, 0.12, 1, 1, 3.1, 0.19), (0.08, 0.86, 0.12, 0.14, 2, 3, 4.4, 0.13),
             (0.93, 0.72, 0.10, 0.18, 3, 2, 5.2, 0.14), (0.45, 0.08, 0.22, 0.10, 1, 2, 2.3, 0.12),
             (0.62, 0.45, 0.18, 0.20, 2, 1, 0.8, 0.10)]
    wx = gx + 0.06 * np.sin(2 * np.pi * (1.6 * gy) + th) + 0.03 * np.sin(2 * np.pi * (3.4 * gy) - 2 * th)
    wy = gy + 0.06 * np.cos(2 * np.pi * (1.3 * gx) + 2 * th) + 0.03 * np.cos(2 * np.pi * (2.9 * gx) + th)
    g = np.zeros_like(gx)
    for cx, cy, ax, ay, n, m, ph, r in blobs:
        x = cx + ax * np.cos(n * th + ph); y = cy + ay * np.sin(m * th + ph * 0.7)
        rr = r * (1 + 0.18 * np.sin(th + ph))
        g += np.exp(-(((wx - x) * aspect) ** 2 + (wy - y) ** 2) / (2 * rr * rr))
    return 1 - np.exp(-1.5 * g)                                   # 0 (between blobs) .. ~1 (inside a blob)


def frame(W, H, cols, theta, pal, speed, dotmap):
    from PIL import Image
    paper, soft, dot, dot2 = pal
    cell = W / cols
    rows = int(math.ceil(H / cell))
    gy, gx = np.mgrid[0:rows, 0:cols].astype(np.float32)
    gx = (gx + 0.5) / cols; gy = (gy + 0.5) * cell / H
    f = field(gx, gy, theta, W / H, speed)
    # light blobs stay smooth paper; the warmer field between them is a halftone: dots grow away from the blobs
    v = np.where(f < 0.36, np.exp(-((0.36 - f) / 0.3) ** 2), np.exp(-((f - 0.36) / 0.1) ** 2))   # peaks just outside a blob
    big = Image.fromarray((v * 255).astype(np.uint8)).resize((cols * 8, rows * 8), Image.BICUBIC)
    sv = np.asarray(big.crop((0, 0, cols * 8, int(round(H / cell * 8)))).resize((W, H), Image.BICUBIC), np.float32)[..., None] / 255
    img = mix(paper[None, None], soft[None, None], (sv ** 1.2) * 0.75)
    inside = np.clip((f - 0.42) / 0.3, 0, 1)                     # the blobs themselves: a faint warm fill
    big2 = Image.fromarray((inside * 255).astype(np.uint8)).resize((cols * 8, rows * 8), Image.BICUBIC)
    si = np.asarray(big2.crop((0, 0, cols * 8, int(round(H / cell * 8)))).resize((W, H), Image.BICUBIC), np.float32)[..., None] / 255
    img = mix(img, soft[None, None], si * 0.22)
    r = (0.46 * cell) * v ** 1.6
    second = 0.5 + 0.5 * np.sin(2 * np.pi * (gx * 1.3 - gy * 0.9) + theta * speed)
    c = int(math.ceil(cell))
    rr = np.repeat(np.repeat(r, c, 0), c, 1)
    mixmap = np.repeat(np.repeat(second, c, 0), c, 1)
    dist, cy, cx = dotmap
    R = rr[cy, cx]; M = mixmap[cy, cx][..., None]
    a = np.clip(R - dist + 0.5, 0, 1)[..., None] * (R > 0.4)[..., None]
    ink = mix(mix(dot[None, None], dot2[None, None], M * 0.5), soft[None, None], 0.15)
    img = mix(img, ink, a * 0.9)
    return np.clip(img, 0, 255).astype(np.uint8)


def dotmap(W, H, cols):
    cell = W / cols
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx = np.floor(xx / cell); cy = np.floor(yy / cell)
    dist = np.hypot(xx - (cx + 0.5) * cell, yy - (cy + 0.5) * cell)
    c = int(math.ceil(cell))
    # index into the cell-size-repeated maps: the cell's top-left pixel in that map
    return dist, (cy * c).astype(int), (cx * c).astype(int)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--look"); ap.add_argument("--colors"); ap.add_argument("--mode", choices=["light", "dark"], default="light")
    ap.add_argument("--size", default="1920x1080"); ap.add_argument("--dur", type=float, default=12.0); ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--grid", type=int, default=0, help="dot columns (default: about one dot per 11 px)")
    ap.add_argument("--speed", type=int, default=1, help="1 (calm) to 3 (busy); whole numbers keep the loop seamless"); ap.add_argument("--out"); ap.add_argument("--still")
    a = ap.parse_args()
    if not (a.look or a.colors):
        ap.error("give --look <name> or --colors")
    if not (a.out or a.still):
        ap.error("give --out video.mp4 and/or --still frame.png")
    W, H = (int(v) for v in a.size.lower().split("x"))
    cols = a.grid or max(12, round(W / 11))
    pal = palette(a.look, a.colors, a.mode)
    dm = dotmap(W, H, cols)
    if a.still:
        from PIL import Image
        Image.fromarray(frame(W, H, cols, 0.9, pal, a.speed, dm)).save(a.still)
        print(a.still)
    if a.out:
        n = int(round(a.dur * a.fps))
        os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H), "-r", str(a.fps),
                              "-i", "-", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                              a.out], stdin=subprocess.PIPE)
        for i in range(n):
            p.stdin.write(frame(W, H, cols, 2 * math.pi * i / n, pal, a.speed, dm).tobytes())
        p.stdin.close(); p.wait()
        if p.returncode:
            sys.exit("ffmpeg failed")
        print("%s  %dx%d, %.1f s loop" % (a.out, W, H, a.dur))


if __name__ == "__main__":
    main()
