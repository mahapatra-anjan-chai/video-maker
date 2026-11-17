#!/usr/bin/env python3
"""contact-sheet.py: one look at a whole video. One FFmpeg pass pulls evenly spaced frames, then a grid with the time
printed under every frame (this FFmpeg has no drawtext, so the labels are drawn with Pillow).

  python3 contact-sheet.py --video raw/rec.mp4 --out analysis/sheet.png               # ~24 frames over the whole video
  python3 contact-sheet.py --video raw/rec.mp4 --from 40 --to 50 --every 0.25 --out analysis/detail.png   # one close-up

Rule of thumb: ONE overview sheet, then at most ONE detail sheet of the moments that decide the edit. Then build.
"""
import argparse, glob, os, shutil, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont

FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "fonts", "Poppins-SemiBold.ttf")

ap = argparse.ArgumentParser()
ap.add_argument("--video", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--from", dest="t0", type=float, default=0.0)
ap.add_argument("--to", dest="t1", type=float, default=None)
ap.add_argument("--every", type=float, default=None, help="seconds between frames (default: about 24 frames in the range)")
ap.add_argument("--cols", type=int, default=8)
ap.add_argument("--width", type=int, default=220, help="width of each frame in the sheet")
a = ap.parse_args()

dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.video],
                           capture_output=True, text=True, check=True).stdout.strip())
t1 = min(a.t1 if a.t1 is not None else dur, dur)
every = a.every or max(0.1, round((t1 - a.t0) / 24, 2))
tmp = tempfile.mkdtemp(prefix="sheet-")
subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.3f" % a.t0, "-to", "%.3f" % t1, "-i", a.video,
                "-vf", "fps=1/%.4f,scale=%d:-2" % (every, a.width), os.path.join(tmp, "f%04d.png")], check=True)
frames = sorted(glob.glob(os.path.join(tmp, "f*.png")))
if not frames:
    raise SystemExit("no frames in that range")
fw, fh = Image.open(frames[0]).size
label_h, pad = 34, 6
cols = min(a.cols, len(frames)); rows = -(-len(frames) // cols)
sheet = Image.new("RGB", (cols * (fw + pad) + pad, rows * (fh + label_h + pad) + pad), (24, 24, 28))
draw = ImageDraw.Draw(sheet)
font = ImageFont.truetype(FONT, 22) if os.path.exists(FONT) else ImageFont.load_default()
for i, f in enumerate(frames):
    t = a.t0 + i * every
    x = pad + (i % cols) * (fw + pad); y = pad + (i // cols) * (fh + label_h + pad)
    sheet.paste(Image.open(f), (x, y))
    stamp = "%d:%05.2f" % (int(t // 60), t % 60)
    draw.text((x + 4, y + fh + 4), stamp, fill=(235, 235, 240), font=font)
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
sheet.save(a.out)
shutil.rmtree(tmp, ignore_errors=True)
print("%s: %d frames, every %.2f s, %.2f-%.2f s of %.2f s" % (a.out, len(frames), every, a.t0, t1, dur))
