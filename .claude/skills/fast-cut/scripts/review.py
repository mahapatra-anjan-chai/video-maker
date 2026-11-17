#!/usr/bin/env python3
"""review.py: look at a fast-cut render in the chat, no page needed. One pass over the video writes:

  overview.png    a frame every --every s with its time: the whole cut at a glance
  headlines.png   every text frame by frame: an intro opening big, holding, gliding to the top; cards fading in
  taps.png        every tap: just before, the ripple, just after
  zooms.png       every zoom: before, pushing in, full, easing out
  moments.mp4     those moments back to back at real speed, with sound, small enough to play in the chat

  python3 review.py --cut W/cut.json --video render/video-v2.mp4 --out W/review/v2
Send the PNGs and the MP4 with SendUserFile; give notes by the times printed under the frames.
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "..", "assets", "fonts", "Poppins-Medium.ttf")
TW = 180                                        # tile width in px


def grab(video, times, fps):
    """All the frames in ONE decode, small, kept only where wanted: {t: PIL image}."""
    from PIL import Image
    w, h = (int(x) for x in subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                            "-of", "csv=p=0", video], capture_output=True, text=True, check=True).stdout.strip().split(","))
    th = int(round(TW * h / w / 2)) * 2
    want = {max(0, int(round(t * fps))) for t in times}
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", video, "-vf", "fps=%d,scale=%d:%d" % (fps, TW, th), "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    by_n, n, size = {}, 0, TW * th * 3
    while True:
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        if n in want:
            by_n[n] = Image.frombytes("RGB", (TW, th), buf)
        n += 1
    p.wait()
    last = max(by_n) if by_n else None
    return {t: by_n.get(max(0, int(round(t * fps))), by_n.get(last)) for t in times}


def mmss(t):
    return "%d:%05.2f" % (int(t // 60), t % 60)


def sheet(rows, path, per_row=None):
    """rows: [(heading, [(time, image, caption)])]; each row is one moment, frames left to right."""
    from PIL import Image, ImageDraw, ImageFont
    f_head, f_t = ImageFont.truetype(FONT, 17), ImageFont.truetype(FONT, 14)
    th = next(im.height for _, fr in rows for _, im, _ in fr if im)
    gap, head_h, cap_h = 6, 28, 22
    cols = per_row or max(len(fr) for _, fr in rows)
    W = cols * (TW + gap) + gap
    H = sum(head_h + th + cap_h + gap for _ in rows) + gap
    img = Image.new("RGB", (W, H), (16, 16, 28)); d = ImageDraw.Draw(img)
    y = gap
    for head, frames in rows:
        d.text((gap, y + 4), head, font=f_head, fill=(204, 171, 255))
        y += head_h
        for i, (t, im, cap) in enumerate(frames):
            x = gap + i * (TW + gap)
            if im:
                img.paste(im, (x, y))
            d.text((x + 2, y + th + 3), mmss(t) + ("  " + cap if cap else ""), font=f_t, fill=(235, 235, 245))
        y += th + cap_h + gap
    img.save(path)
    return path


def reel(video, windows, path):
    """The moments back to back, half size, with sound when the video has it."""
    snd = "audio" in subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", video],
                                    capture_output=True, text=True).stdout
    parts = []
    for i, (a, b) in enumerate(windows):
        parts.append("[0:v]trim=%.3f:%.3f,setpts=PTS-STARTPTS,scale=540:-2[v%d]" % (a, b, i))
        if snd:
            parts.append("[0:a]atrim=%.3f:%.3f,asetpts=PTS-STARTPTS[a%d]" % (a, b, i))
    ins = "".join(("[v%d][a%d]" if snd else "[v%d]") % ((i, i) if snd else (i,)) for i in range(len(windows)))
    fg = ";".join(parts) + ";" + ins + "concat=n=%d:v=1:a=%d[v]%s" % (len(windows), 1 if snd else 0, "[a]" if snd else "")
    args = ["ffmpeg", "-y", "-v", "error", "-i", video, "-filter_complex", fg, "-map", "[v]"]
    args += ["-map", "[a]", "-c:a", "aac", "-b:a", "128k"] if snd else []
    subprocess.run(args + ["-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-movflags", "+faststart", path], check=True)
    return path


def merge(windows, dur):
    out = []
    for a, b in sorted((max(0, a), min(dur, b)) for a, b in windows):
        if out and a <= out[-1][1] + 0.2:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cut", required=True); ap.add_argument("--video", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--every", type=float, default=2.5)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    info = json.loads(subprocess.run([sys.executable, os.path.join(HERE, "fast-cut.py"), "times", "--cut", a.cut],
                                     capture_output=True, text=True, check=True).stdout)
    fps = int(json.load(open(a.cut)).get("fps", 30))
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.video],
                               capture_output=True, text=True, check=True).stdout) - 0.05
    clamp = lambda t: min(max(0.0, t), dur)
    plan = {"overview": [], "headlines": [], "taps": [], "zooms": []}
    t = 0.0
    while t < dur:
        plan["overview"].append((clamp(t), "")); t += a.every
    for h in info["texts"]:                          # an intro: opening, rising, holding, gliding, resting
        if h["length"]:
            L = h["length"]; offs = [0.05, 0.3, 0.55, 0.85, L - 0.65, L - 0.45, L - 0.25, L + 0.3]
            caps = ["", "rising", "", "big", "glide", "", "", "rests"]
        else:
            offs = [0.0, 0.15, 0.4, 1.0]; caps = ["", "fade in", "", ""]
        plan["headlines"].append((h["text"], [(clamp(h["from"] + o), c) for o, c in zip(offs, caps)]))
    for tp in info["taps"]:
        plan["taps"].append((tp["note"] or "tap", [(clamp(tp["t"] - 0.25), "before"), (clamp(tp["t"] + 0.1), "tap"), (clamp(tp["t"] + 0.6), "after")]))
    for i, (z0, z1) in enumerate(info["zooms"]):
        mid = (z0 + z1) / 2
        plan["zooms"].append(("zoom %d" % (i + 1), [(clamp(z0 - 0.2), "before"), (clamp(z0 + 0.25), "in"), (clamp(mid), "full"), (clamp(z1 - 0.15), "out")]))
    times = [t for t, _ in plan["overview"]] + [t for k in ("headlines", "taps", "zooms") for _, fr in plan[k] for t, _ in fr]
    frames = grab(a.video, times, fps)
    pick = lambda fr: [(t, frames[t], c) for t, c in fr]
    out = []
    ov = [(t, frames[t], "") for t, _ in plan["overview"]]
    out.append(sheet([("Whole cut, a frame every %g s" % a.every, ov[i:i + 10]) for i in range(0, len(ov), 10)],
                     os.path.join(a.out, "overview.png")))
    if plan["headlines"]:
        out.append(sheet([(h, pick(fr)) for h, fr in plan["headlines"]], os.path.join(a.out, "headlines.png")))
    if plan["taps"]:                                 # three taps to a row
        rows = [(" | ".join(h for h, _ in plan["taps"][i:i + 3]), sum((pick(fr) for _, fr in plan["taps"][i:i + 3]), []))
                for i in range(0, len(plan["taps"]), 3)]
        out.append(sheet(rows, os.path.join(a.out, "taps.png")))
    if plan["zooms"]:                                # two zooms to a row
        rows = [(" | ".join(h for h, _ in plan["zooms"][i:i + 2]), sum((pick(fr) for _, fr in plan["zooms"][i:i + 2]), []))
                for i in range(0, len(plan["zooms"]), 2)]
        out.append(sheet(rows, os.path.join(a.out, "zooms.png")))
    wins = [(h["from"] - 0.4, h["from"] + h["length"] + 0.6) for h in info["texts"] if h["length"]]
    wins += [(tp["t"] - 0.8, tp["t"] + 1.0) for tp in info["taps"]] + [(z0 - 0.4, z1 + 0.4) for z0, z1 in info["zooms"]]
    if wins:
        out.append(reel(a.video, merge(wins, dur), os.path.join(a.out, "moments.mp4")))
    for p in out:
        print(p)


if __name__ == "__main__":
    main()
