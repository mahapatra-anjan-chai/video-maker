#!/usr/bin/env python3
"""make-demo.py: the README's screenshots, made from a made-up app so nothing real is shown.

Draws a 15 s screen recording of "Shopwise" (a shopping app that does not exist), cuts it with fast-cut (taps, a zoom,
two headline intros, title and end cards), then writes the review sheets and a GIF into docs/images/.

  python3 docs/demo/make-demo.py          (from the project folder; ~30 s)
"""
import math, os, shutil, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FC = os.path.join(ROOT, ".claude", "skills", "fast-cut", "scripts")
FONTS = os.path.join(ROOT, ".claude", "skills", "fast-cut", "assets", "fonts")
WORK = os.path.join(HERE, "work")
IMAGES = os.path.join(ROOT, "docs", "images")
W, H, FPS, DUR = 390, 844, 30, 15.0
S = 2                                            # drawn at 2x, so the 1080-wide cut stays sharp

INK, MUTED, BG, LINE, INDIGO = (17, 24, 39), (107, 114, 128), (246, 245, 242), (229, 231, 235), (79, 70, 229)
_fonts = {}


def font(weight, size):
    k = (weight, size)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(os.path.join(FONTS, "Poppins-%s.ttf" % weight), size * S)
    return _fonts[k]


def ease(u):
    u = min(1.0, max(0.0, u))
    return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


def shade(c, k):
    c = tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) if isinstance(c, str) else c
    return tuple(int(v * k) for v in c)


class Pen:
    """Draws in phone points; scales to the 2x canvas."""
    def __init__(self, img, dx=0, dy=0):
        self.d = ImageDraw.Draw(img); self.dx, self.dy = dx, dy

    def p(self, x, y):
        return ((x + self.dx) * S, (y + self.dy) * S)

    def box(self, x0, y0, x1, y1, r=0, fill=None, outline=None, width=1):
        self.d.rounded_rectangle([self.p(x0, y0), self.p(x1, y1)], radius=r * S, fill=fill, outline=outline, width=width * S)

    def poly(self, pts, fill):
        self.d.polygon([self.p(x, y) for x, y in pts], fill=fill)

    def circle(self, cx, cy, r, fill=None, outline=None, width=1):
        self.d.ellipse([self.p(cx - r, cy - r), self.p(cx + r, cy + r)], fill=fill, outline=outline, width=width * S)

    def text(self, x, y, s, f, fill, anchor="la"):
        self.d.text(self.p(x, y), s, font=f, fill=fill, anchor=anchor)

    def arc(self, cx, cy, r, a0, a1, fill, width):
        self.d.arc([self.p(cx - r, cy - r), self.p(cx + r, cy + r)], a0, a1, fill=fill, width=width * S)


def icon(pen, kind, cx, cy, s, color):
    c = shade(color, 0.62)
    if kind == "jacket":
        pen.poly([(cx - .28 * s, cy - .30 * s), (cx - .10 * s, cy - .36 * s), (cx, cy - .24 * s), (cx + .10 * s, cy - .36 * s),
                  (cx + .28 * s, cy - .30 * s), (cx + .28 * s, cy + .38 * s), (cx - .28 * s, cy + .38 * s)], c)
        pen.poly([(cx - .28 * s, cy - .30 * s), (cx - .45 * s, cy + .22 * s), (cx - .34 * s, cy + .26 * s), (cx - .26 * s, cy)], c)
        pen.poly([(cx + .28 * s, cy - .30 * s), (cx + .45 * s, cy + .22 * s), (cx + .34 * s, cy + .26 * s), (cx + .26 * s, cy)], c)
        pen.box(cx - .01 * s, cy - .24 * s, cx + .01 * s, cy + .38 * s, fill=shade(color, 0.45))
    elif kind == "shoe":
        pen.box(cx - .38 * s, cy - .10 * s, cx + .36 * s, cy + .16 * s, r=.12 * s, fill=c)
        pen.box(cx - .38 * s, cy - .30 * s, cx - .02 * s, cy + .05 * s, r=.10 * s, fill=c)
        pen.box(cx - .40 * s, cy + .12 * s, cx + .38 * s, cy + .22 * s, r=.05 * s, fill=shade(color, 0.45))
    elif kind == "lamp":
        pen.poly([(cx - .26 * s, cy - .05 * s), (cx + .26 * s, cy - .05 * s), (cx + .14 * s, cy - .36 * s), (cx - .14 * s, cy - .36 * s)], c)
        pen.box(cx - .02 * s, cy - .05 * s, cx + .02 * s, cy + .30 * s, fill=c)
        pen.box(cx - .20 * s, cy + .28 * s, cx + .20 * s, cy + .36 * s, r=.04 * s, fill=c)
    elif kind == "bag":
        pen.box(cx - .36 * s, cy - .16 * s, cx + .36 * s, cy + .30 * s, r=.10 * s, fill=c)
        pen.arc(cx, cy - .16 * s, .18 * s, 180, 360, c, max(2, int(.05 * s)))
    elif kind == "beanie":
        pen.d.pieslice([pen.p(cx - .32 * s, cy - .38 * s), pen.p(cx + .32 * s, cy + .22 * s)], 180, 360, fill=c)
        pen.box(cx - .34 * s, cy - .10 * s, cx + .34 * s, cy + .12 * s, r=.05 * s, fill=shade(color, 0.5))
        pen.circle(cx, cy - .40 * s, .07 * s, fill=c)
    elif kind == "mug":
        pen.box(cx - .24 * s, cy - .26 * s, cx + .18 * s, cy + .28 * s, r=.06 * s, fill=c)
        pen.circle(cx + .24 * s, cy, .12 * s, outline=c, width=max(2, int(.05 * s)))


ITEMS = [("Trail Sneakers", "$120", "#DCEBDD", "shoe"), ("Desk Lamp", "$45", "#E3E7F3", "lamp"),
         ("Field Jacket", "$89", "#F3E3D3", "jacket"), ("Weekend Bag", "$140", "#EADCF0", "bag"),
         ("Wool Beanie", "$25", "#F0E6D8", "beanie"), ("Ceramic Mug", "$18", "#DDEFEF", "mug")]
SCROLL = 150                                     # the home feed scrolls this far, so the jacket sits at (103, 391)


def status(pen, dark=False):
    c = (255, 255, 255) if dark else INK
    pen.text(24, 14, "9:41", font("Medium", 15), c)
    pen.box(338, 17, 364, 29, r=3, outline=c, width=1); pen.box(341, 20, 358, 26, r=1, fill=c)


def home(img, t):
    pen = Pen(img)
    pen.box(0, 0, W, H, fill=BG)
    scroll = SCROLL * ease((t - 0.5) / 1.7)
    for i, (name, price, col, kind) in enumerate(ITEMS):
        x = 20 if i % 2 == 0 else 203
        y = 204 + (i // 2) * 252 - scroll
        pressed = kind == "jacket" and 2.95 <= t < 3.25
        pen.box(x, y, x + 167, y + 170, r=16, fill=shade(col, 0.92) if pressed else col)
        icon(pen, kind, x + 83, y + 88, 110, col)
        pen.circle(x + 145, y + 22, 13, fill=(255, 255, 255))
        pen.text(x + 4, y + 180, name, font("SemiBold", 14), INK)
        pen.text(x + 4, y + 202, price, font("Regular", 13), MUTED)
    pen.box(0, 0, W, 196, fill=BG)                # the header stays put over the scrolling grid
    status(pen)
    pen.text(24, 50, "Shopwise", font("Bold", 26), INK)
    pen.circle(352, 64, 15, fill=LINE)
    pen.box(20, 98, 370, 142, r=22, fill=(255, 255, 255), outline=LINE)
    pen.circle(44, 120, 7, outline=MUTED, width=2)
    pen.text(62, 109, "Search jackets, lamps, gifts...", font("Regular", 15), (156, 163, 175))
    x = 20
    for j, chip in enumerate(["For you", "Outerwear", "Home", "Gifts"]):
        w = font("Medium", 13).getlength(chip) / S + 28
        pen.box(x, 156, x + w, 186, r=15, fill=INK if j == 0 else None, outline=None if j == 0 else LINE)
        pen.text(x + 14, 162, chip, font("Medium", 13), (255, 255, 255) if j == 0 else INK)
        x += w + 8
    pen.box(0, 784, W, H, fill=(255, 255, 255)); pen.box(0, 784, W, 785, fill=LINE)
    for k in range(4):
        pen.box(46 + k * 92, 802, 70 + k * 92, 826, r=7, fill=INK if k == 0 else LINE)


def loading(img, t):
    pen = Pen(img)
    pen.box(0, 0, W, H, fill=BG); status(pen)
    a = (t * 360) % 360
    pen.circle(195, 380, 26, outline=LINE, width=5)
    pen.arc(195, 380, 26, a, a + 100, INDIGO, 5)
    pen.text(195, 432, "Checking your size...", font("Medium", 17), INK, "mm")
    pen.text(195, 460, "Using your last 3 orders", font("Regular", 14), MUTED, "mm")


def product(img, t):
    dx = W * (1 - ease((t - 7.2) / 0.3))
    pen = Pen(img, dx=dx)
    pen.box(0, 0, W, H, fill=BG); status(pen)
    pen.text(28, 52, "<", font("SemiBold", 22), INK)
    pen.circle(352, 64, 15, fill=LINE)
    pen.box(20, 96, 370, 470, r=22, fill="#F3E3D3")
    icon(pen, "jacket", 195, 290, 300, "#F3E3D3")
    pen.text(24, 486, "Field Jacket", font("Bold", 24), INK)
    pen.text(24, 524, "$89", font("SemiBold", 20), INK)
    pen.text(76, 530, "4.8 stars  |  1.2k reviews", font("Regular", 13), MUTED)
    pen.box(24, 566, 228, 604, r=19, fill=(224, 231, 255))
    pen.circle(46, 585, 9, fill=INDIGO)
    pen.text(62, 573, "Size M fits you", font("SemiBold", 15), (55, 48, 163))
    pen.text(24, 618, "Matched to your last 3 orders and returns", font("Regular", 13), MUTED)
    for k, col in enumerate([(107, 114, 84), (30, 41, 59), (214, 196, 165)]):
        pen.circle(40 + k * 40, 672, 13, fill=col)
        if k == 0:
            pen.circle(40, 672, 18, outline=INK, width=2)
    pressed = 11.9 <= t < 12.2
    pen.box(20, 762, 370, 814, r=26, fill=(55, 65, 81) if pressed else INK)
    pen.text(195, 788, "Add to bag", font("SemiBold", 17), (255, 255, 255), "mm")
    if t >= 12.2:                                 # the bag sheet slides up
        u = ease((t - 12.2) / 0.35)
        dim = Image.new("RGBA", img.size, (0, 0, 0, int(90 * u)))
        img.alpha_composite(dim)
        pen = Pen(img, dy=260 * (1 - u))
        pen.box(0, 584, W, H + 30, r=24, fill=(255, 255, 255))
        pen.box(175, 596, 215, 601, r=2, fill=LINE)
        pen.circle(195, 646, 22, fill=(22, 163, 74))
        pen.d.line([pen.p(185, 646), pen.p(192, 653), pen.p(206, 638)], fill=(255, 255, 255), width=4 * S)
        pen.text(195, 692, "Added to bag", font("Bold", 20), INK, "mm")
        pen.text(195, 720, "Field Jacket, size M", font("Regular", 14), MUTED, "mm")
        pen.box(20, 760, 370, 810, r=25, fill=INDIGO)
        pen.text(195, 785, "Checkout  $89", font("SemiBold", 17), (255, 255, 255), "mm")


def frame(t):
    img = Image.new("RGBA", (W * S, H * S), BG + (255,))
    (home if t < 3.25 else loading if t < 7.2 else product)(img, t)
    return img.convert("RGB")


def record(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W * S, H * S),
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", path],
                         stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)):
        p.stdin.write(frame(i / FPS).tobytes())
    p.stdin.close(); p.wait()


def main():
    rec = os.path.join(WORK, "raw", "shopwise.mp4")
    record(rec)
    cut = os.path.join(HERE, "cut.json")
    out = os.path.join(WORK, "render", "shopwise-demo.mp4")
    run = lambda *a: subprocess.run([sys.executable] + list(a), check=True)
    run(os.path.join(FC, "fast-cut.py"), "render", "--cut", cut, "--out", out)
    review = os.path.join(WORK, "review")
    run(os.path.join(FC, "review.py"), "--cut", cut, "--video", out, "--out", review)
    os.makedirs(IMAGES, exist_ok=True)
    for name in ("headlines", "taps", "zooms"):
        im = Image.open(os.path.join(review, name + ".png")).convert("RGB")
        im.save(os.path.join(IMAGES, "demo-%s.jpg" % name), quality=84, optimize=True)
    gif = os.path.join(IMAGES, "demo.gif")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", out, "-vf",
                    "fps=12,scale=270:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4",
                    gif], check=True)
    shutil.copy(out, os.path.join(WORK, "shopwise-demo.mp4"))
    for f in sorted(os.listdir(IMAGES)):
        print("%-24s %6.0f KB" % (f, os.path.getsize(os.path.join(IMAGES, f)) / 1024))


if __name__ == "__main__":
    main()
