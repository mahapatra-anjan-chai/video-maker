#!/usr/bin/env python3
"""make-visuals.py: the README's two diagrams, drawn with Pillow so they read the same everywhere.

  docs/images/workflow.png    what happens to a recording, from your folder to a versioned MP4
  docs/images/pmm-steps.png   the steps a PMM takes, who does each, and roughly how long

  python3 docs/make-visuals.py
"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, ".claude", "skills", "fast-cut", "assets", "fonts")
OUT = os.path.join(ROOT, "docs", "images")
S = 2                                            # drawn at 2x for sharp text on retina screens

BG, CARD, INK, MUTED, LINE = (248, 250, 252), (255, 255, 255), (15, 23, 42), (71, 85, 105), (226, 232, 240)
INDIGO, SKY, ROSE, AMBER, GREEN = (79, 70, 229), (14, 165, 233), (219, 39, 119), (217, 119, 6), (22, 163, 74)
TINT = {INDIGO: (238, 242, 255), SKY: (224, 242, 254), ROSE: (252, 231, 243), AMBER: (254, 243, 199), GREEN: (220, 252, 231)}
_f = {}


def F(weight, size):
    if (weight, size) not in _f:
        _f[(weight, size)] = ImageFont.truetype(os.path.join(FONTS, "Poppins-%s.ttf" % weight), size * S)
    return _f[(weight, size)]


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)
        self.box(0, 0, w, h, 28, fill=BG)

    def box(self, x0, y0, x1, y1, r=0, fill=None, outline=None, width=1):
        self.d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], radius=r * S, fill=fill, outline=outline, width=width * S)

    def text(self, x, y, s, f, fill, anchor="la"):
        self.d.text((x * S, y * S), s, font=f, fill=fill, anchor=anchor)

    def wrap(self, x, y, s, f, fill, width, gap=1.45):
        """Wrapped text; returns the y below it."""
        lines, cur = [], ""
        for word in s.split(" "):
            t = (cur + " " + word).strip()
            if f.getlength(t) / S <= width or not cur:
                cur = t
            else:
                lines.append(cur); cur = word
        lines.append(cur)
        lh = f.size / S * gap
        for i, l in enumerate(lines):
            self.text(x, y + i * lh, l, f, fill)
        return y + len(lines) * lh

    def arrow(self, x0, y0, x1, y1, color, width=3):
        self.d.line([x0 * S, y0 * S, x1 * S, y1 * S], fill=color, width=width * S)
        import math
        a = math.atan2(y1 - y0, x1 - x0); k = 9
        pts = [(x1, y1), (x1 - k * math.cos(a - 0.5), y1 - k * math.sin(a - 0.5)), (x1 - k * math.cos(a + 0.5), y1 - k * math.sin(a + 0.5))]
        self.d.polygon([(px * S, py * S) for px, py in pts], fill=color)

    def chip(self, x, y, s, color, f=None):
        f = f or F("SemiBold", 12)
        w = f.getlength(s) / S + 20
        self.box(x, y, x + w, y + 24, 12, fill=TINT[color])
        self.text(x + 10, y + 12, s, f, color, "lm")
        return x + w + 8

    def save(self, name):
        os.makedirs(OUT, exist_ok=True)
        p = os.path.join(OUT, name)
        self.img.save(p, optimize=True)
        print("%-16s %dx%d  %.0f KB" % (name, self.img.width, self.img.height, os.path.getsize(p) / 1024))


def workflow():
    c = Canvas(1200, 640)
    c.text(48, 44, "How Video maker works", F("Bold", 30), INK)
    c.text(48, 88, "You bring a screen recording and a brief. Claude Code plans, cuts, voices, scores and renders it on your Mac.",
           F("Regular", 16), MUTED)
    stages = [
        (INDIGO, "1  YOU BRING", "Recordings + brief",
         ["Screen recordings of the feature", "Brief: audience, length, 9:16 or 16:9, intro and end copy", "Optional: script, logo, music notes"]),
        (SKY, "2  CLAUDE PLANS", "Reads it, asks 3 things",
         ["Personal or work, which look, OK to spend on voice and music", "Contact sheet + motion scan of each recording", "A cut table you can change"]),
        (ROSE, "3  CLAUDE BUILDS", "Cut, effects, sound",
         ["Trims, speeds up loading and AI waits", "Taps with clicks, zooms, headlines that open big", "Voiceover, licensed music ducked under it"]),
        (AMBER, "4  YOU REVIEW", "In the chat",
         ["Headline, tap and zoom sheets with timestamps", "A short clip of just those moments", "Notes by time: \"0:17 slower glide\""]),
        (GREEN, "5  YOU SHIP", "Versioned MP4",
         ["v1, v2, ... never overwritten", "Each version's cut list kept", "Ask for cut-downs: 15 s, 16:9"]),
    ]
    x, y, w, h, gap = 48, 140, 204, 330, 22
    for i, (col, tag, title, items) in enumerate(stages):
        x0 = x + i * (w + gap)
        c.box(x0, y, x0 + w, y + h, 18, fill=CARD, outline=LINE)
        c.box(x0, y, x0 + w, y + 8, 4, fill=col)
        c.text(x0 + 18, y + 30, tag, F("SemiBold", 12), col)
        c.wrap(x0 + 18, y + 50, title, F("Bold", 18), INK, w - 36)
        yy = y + 112
        for it in items:
            c.d.ellipse([(x0 + 20) * S, (yy + 8) * S, (x0 + 26) * S, (yy + 14) * S], fill=col)
            yy = c.wrap(x0 + 34, yy, it, F("Regular", 13), MUTED, w - 52, 1.5) + 10
        if i < len(stages) - 1:
            c.arrow(x0 + w + 3, y + h / 2, x0 + w + gap - 3, y + h / 2, (148, 163, 184), 3)
    # the notes loop: review back to build
    lx0, lx1, ly = x + 2 * (w + gap) + w / 2, x + 3 * (w + gap) + w / 2, y + h + 26
    c.d.line([lx1 * S, (y + h) * S, lx1 * S, ly * S, lx0 * S, ly * S], fill=AMBER, width=3 * S, joint="curve")
    c.arrow(lx0, ly, lx0, y + h + 4, AMBER, 3)
    c.text((lx0 + lx1) / 2, ly + 16, "notes become a new version in minutes", F("Medium", 13), AMBER, "mm")
    # where things run
    yb = 548
    c.box(48, yb, 1152, yb + 56, 14, fill=CARD, outline=LINE)
    c.text(68, yb + 28, "On your Mac", F("SemiBold", 13), INK, "lm")
    xx = 170
    for s in ["Claude Code", "FFmpeg", "HyperFrames", "Parakeet transcription"]:
        xx = c.chip(xx, yb + 16, s, INDIGO)
    c.text(xx + 18, yb + 28, "Cloud APIs", F("SemiBold", 13), INK, "lm")
    xx += 110
    for s in ["ElevenLabs: voice, sound effects", "Epidemic Sound: music"]:
        xx = c.chip(xx, yb + 16, s, ROSE)
    c.save("workflow.png")


def steps():
    rows = [
        ("You", INDIGO, "5 min", "Pick one feature, one message",
         "Write the value in a single line a customer would say, e.g. \"Know your size before you buy\". That line becomes the headline."),
        ("You", INDIGO, "10 min", "Record the flow on a real device",
         "One clean take per feature, believable data, notifications off. Pause a beat on every result so it can breathe."),
        ("You", INDIGO, "2 min", "Make the video's folder",
         "videos/<name>/raw/ for the recordings. Add script.txt for a voiceover, img/ for a logo, docs/ for anything else."),
        ("You", INDIGO, "5 min", "Write the brief",
         "Audience, length (e.g. 60 to 90 s), shape (9:16 or 16:9), intro and end-card copy, moments that must stay."),
        ("You + Claude", ROSE, "1 min", "Say: Edit my video \"<name>\"",
         "Answer three checks: personal or work, which look, and a yes on the voice and music cost (shown before anything is spent)."),
        ("Claude", SKY, "~10 min", "Draft",
         "Cut table, sped-up waits, taps, zooms and headlines. A half-size draft renders in seconds."),
        ("You + Claude", ROSE, "5 min per round", "Review in the chat, give notes",
         "Sheets of every headline, tap and zoom, plus a short clip of those moments. Notes by timestamp; each round is a new version."),
        ("You", GREEN, "1 min", "Ship it",
         "The MP4 is in Movies > YouTube Renders, one file per version. Ask for cut-downs: a 15 s teaser, a 16:9 for the site."),
    ]
    W, top, rh = 1200, 140, 118
    c = Canvas(W, top + len(rows) * rh + 70)
    c.text(48, 44, "Step by step for PMMs", F("Bold", 30), INK)
    c.text(48, 88, "From a feature to a shareable video in under an hour. You own the message; Claude does the editing.",
           F("Regular", 16), MUTED)
    for i, (who, col, time, title, detail) in enumerate(rows):
        y = top + i * rh
        c.box(48, y, W - 48, y + rh - 16, 18, fill=CARD, outline=LINE)
        c.d.ellipse([72 * S, (y + 24) * S, 124 * S, (y + 76) * S], fill=col)
        c.text(98, y + 50, str(i + 1), F("Bold", 22), (255, 255, 255), "mm")
        c.text(150, y + 22, title, F("Bold", 19), INK)
        c.wrap(150, y + 54, detail, F("Regular", 14), MUTED, 760)
        xx = c.chip(W - 300, y + 24, who, col)
        c.chip(xx, y + 24, time, AMBER if "min" in time else col)
        if i < len(rows) - 1:
            c.d.line([98 * S, (y + 78) * S, 98 * S, (y + rh + 22) * S], fill=LINE, width=3 * S)
    yb = top + len(rows) * rh + 4
    c.text(48, yb + 18, "Good to know:", F("SemiBold", 14), INK)
    c.text(168, yb + 18, "work videos use your brand look and keep unreleased footage on your Mac; keys live only in .env.",
           F("Regular", 14), MUTED)
    c.save("pmm-steps.png")


if __name__ == "__main__":
    workflow()
    steps()
