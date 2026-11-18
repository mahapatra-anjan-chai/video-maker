#!/usr/bin/env python3
"""One sheet of the new subtitles as delivered: the bottom strip of the frame in the middle of every cue, plus the
frame just before and after each band, where the old subtitle could peek through. Times under each strip.

  python3 review-subs.py --video out.mp4 --cues W/cues-ja.json --out W/review/v1/subs.jpg [--band 0.8,1.0]
"""
import argparse, io, json, subprocess
from PIL import Image, ImageDraw


def grab(video, t, y0, h, W):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.3f" % t, "-i", video, "-frames:v", "1", "-vf",
                          "crop=%d:%d:0:%d,scale=%d:-2" % (W, h, y0, W // 2), "-f", "image2pipe", "-vcodec", "png", "-"],
                         capture_output=True).stdout
    return Image.open(io.BytesIO(raw)).convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--cues", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--band", default="0.8,1.0")
    ap.add_argument("--cols", type=int, default=2)
    a = ap.parse_args()
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                      "stream=width,height", "-of", "json", a.video], capture_output=True, text=True).stdout)
    W, H = info["streams"][0]["width"], info["streams"][0]["height"]
    b0, b1 = [float(x) for x in a.band.split(",")]
    y0, h = int(H * b0) // 2 * 2, int(H * (b1 - b0)) // 2 * 2
    cues = json.load(open(a.cues))
    ts = []
    for i, c in enumerate(cues):
        if i == 0 or c["start"] - cues[i - 1]["end"] > 0.3:
            ts.append((c["start"] - 0.2, "before"))
        ts.append(((c["start"] + c["end"]) / 2, c["text"][:18]))
        if i == len(cues) - 1 or cues[i + 1]["start"] - c["end"] > 0.3:
            ts.append((c["end"] + 0.2, "after"))
    ims = [(t, label, grab(a.video, max(0, t), y0, h, W)) for t, label in ts]
    w, hh = ims[0][2].size
    rows = (len(ims) + a.cols - 1) // a.cols
    sheet = Image.new("RGB", (w * a.cols, (hh + 20) * rows), "black")
    d = ImageDraw.Draw(sheet)
    for k, (t, label, im) in enumerate(ims):
        x, y = (k % a.cols) * w, (k // a.cols) * (hh + 20)
        sheet.paste(im, (x, y))
        d.text((x + 6, y + hh + 4), "%d:%05.2f  %s" % (t // 60, t % 60, "" if label not in ("before", "after") else label),
               fill="yellow" if label in ("before", "after") else "white")
    sheet.save(a.out, quality=86)
    print("%d strips -> %s" % (len(ims), a.out))


if __name__ == "__main__":
    main()
