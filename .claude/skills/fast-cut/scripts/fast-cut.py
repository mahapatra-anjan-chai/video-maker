#!/usr/bin/env python3
"""fast-cut.py: edit a screen recording or a video by a cut list, in one FFmpeg pass. Nothing goes through a browser,
so a draft renders in seconds and a full-resolution final in well under a minute for a short ad.

  python3 fast-cut.py scan   --video raw/rec.mov [--size 1080x1920] [--still 1.2] [--speed 8] --out W/cut.json
  python3 fast-cut.py render --cut W/cut.json --out W/render/name-v1.mp4 [--draft]

scan reads the motion of the video and writes a starter cut list: everything kept at 1x, and every still stretch
(loading, an AI generating, a pause) longer than --still seconds sped up by --speed. Edit the numbers, then render.

cut.json (all times in seconds; zooms, texts and images use OUTPUT time):
{
  "size": [1080, 1920], "fps": 30, "fit": "cover",        # cover = fill and crop, contain = fit inside with "bg" bars
  "bg": "#000000", "audio": "mute",                        # "keep" keeps the sound of 1x segments; sped-up parts are silent
  "segments": [ {"src": "raw/rec.mov", "from": 0, "to": 12.4, "speed": 1},
                {"src": "raw/rec.mov", "from": 25.0, "to": 32.0, "speed": 6} ],
  "zooms":  [ {"from": 3.0, "to": 5.0, "scale": 1.3, "x": 0.5, "y": 0.42, "ease": 0.3} ],   # x, y = focus point, 0-1
  "texts":  [ {"text": "See it on you", "from": 1.0, "to": 4.0, "y": 0.12, "size": 76, "color": "#FFFFFF",
               "box": "#000000B3", "weight": "SemiBold", "width": 0.86} ],
  "images": [ {"file": "img/logo.png", "from": 0, "to": 3, "x": 0.5, "y": 0.9, "w": 0.3} ]
}
Paths in cut.json are relative to the cut.json file.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "assets", "fonts")


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height",
                        "-of", "json", path], capture_output=True, text=True, check=True)
    d = json.loads(r.stdout)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), {})
    return {"dur": float(d["format"]["duration"]), "w": v.get("width"), "h": v.get("height"),
            "audio": any(s["codec_type"] == "audio" for s in d["streams"])}


# ---------------------------------------------------------------- scan: find the still stretches
def motion(video, fps=8, w=96):
    """Mean absolute difference between consecutive small grey frames, one value per 1/fps s."""
    import numpy as np
    info = probe(video)
    h = int(round(w * info["h"] / info["w"] / 2)) * 2
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", "fps=%d,scale=%d:%d,format=gray" % (fps, w, h),
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.int16)
    d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
    return [0.0] + [float(x) for x in d], info


def still_runs(diffs, fps, min_len, thresh=None):
    peak = max(diffs) or 1.0
    thresh = thresh if thresh is not None else max(0.35, 0.02 * peak)     # tiny cursor blinks and shimmer count as still
    runs, start = [], None
    for i, v in enumerate(diffs + [peak]):
        if v < thresh and start is None:
            start = i
        elif v >= thresh and start is not None:
            if (i - start) / fps >= min_len:
                runs.append((start / fps, i / fps))
            start = None
    return runs


def cmd_scan(a):
    diffs, info = motion(a.video)
    runs = still_runs(diffs, 8, a.still)
    dur = info["dur"]
    rel = os.path.relpath(os.path.abspath(a.video), os.path.dirname(os.path.abspath(a.out)))
    segs, t = [], 0.0
    for s, e in runs:
        s, e = max(0.0, s + 0.15), min(dur, e - 0.15)        # keep the first and last moments of a pause at 1x
        if e - s < 0.4:
            continue
        if s > t:
            segs.append({"src": rel, "from": round(t, 2), "to": round(s, 2), "speed": 1})
        segs.append({"src": rel, "from": round(s, 2), "to": round(e, 2), "speed": a.speed, "note": "still"})
        t = e
    if dur - t > 0.05:
        segs.append({"src": rel, "from": round(t, 2), "to": round(dur, 2), "speed": 1})
    W, H = (int(x) for x in a.size.split("x")) if a.size else (info["w"], info["h"])
    cut = {"size": [W, H], "fps": 30, "fit": "cover", "bg": "#000000", "audio": "mute", "segments": segs,
           "zooms": [], "texts": [], "images": []}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    json.dump(cut, open(a.out, "w"), indent=2)
    out_t = sum((s["to"] - s["from"]) / s["speed"] for s in segs)
    print("%s  %.1f s -> %.1f s  (%d still stretches sped up %gx)" % (a.out, dur, out_t, sum(1 for s in segs if s.get("note")), a.speed))
    for s in segs:
        print("  %6.2f-%6.2f  x%-4g %s" % (s["from"], s["to"], s["speed"], s.get("note", "")))


# ---------------------------------------------------------------- render
def hex_rgba(h, default=(0, 0, 0, 0)):
    if not h:
        return default
    h = h.lstrip("#")
    if len(h) == 6:
        h += "FF"
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4, 6))


def text_png(t, W, H, path):
    from PIL import Image, ImageDraw, ImageFont
    weight = t.get("weight", "SemiBold")
    font_path = t.get("font") or os.path.join(FONTS, "Poppins-%s.ttf" % weight)
    size = int(t.get("size", 72))
    font = ImageFont.truetype(font_path, size)
    maxw = int(W * float(t.get("width", 0.86)))
    lines = []
    for para in str(t["text"]).split("\n"):
        cur = ""
        for word in para.split(" "):
            test = (cur + " " + word).strip()
            if font.getlength(test) <= maxw or not cur:
                cur = test
            else:
                lines.append(cur); cur = word
        lines.append(cur)
    lh = int(size * 1.22)
    tw = int(max(font.getlength(l) for l in lines)); th = lh * len(lines)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = W * float(t.get("x", 0.5)); top = int(H * float(t.get("y", 0.12)))
    align = t.get("align", "center")
    box = hex_rgba(t.get("box"))
    if box[3]:
        px, py = int(size * 0.55), int(size * 0.35)
        bx0 = (cx - tw / 2 if align == "center" else cx) - px
        d.rounded_rectangle([bx0, top - py, bx0 + tw + 2 * px, top + th + py * 0.8], radius=int(size * 0.45), fill=box)
    for i, l in enumerate(lines):
        lx = cx - font.getlength(l) / 2 if align == "center" else cx
        d.text((lx, top + i * lh), l, font=font, fill=hex_rgba(t.get("color", "#FFFFFF")))
    img.save(path)


def image_png(im, base, W, H, path):
    from PIL import Image
    src = Image.open(os.path.join(base, im["file"])).convert("RGBA")
    w = int(W * float(im.get("w", 0.3))); h = int(src.height * w / src.width)
    src = src.resize((w, h), Image.LANCZOS)
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    canvas.paste(src, (int(W * float(im.get("x", 0.5)) - w / 2), int(H * float(im.get("y", 0.5)) - h / 2)), src)
    canvas.save(path)


def zoom_exprs(zooms, fps):
    """zoompan z / x / y expressions: each zoom eases in and out over `ease` s around its window (output time)."""
    if not zooms:
        return None
    t = "(on/%d)" % fps
    env = lambda z: "min(1,max(0,(%s-%.3f)/%.3f))*min(1,max(0,(%.3f-%s)/%.3f))" % (
        t, z["from"], z.get("ease", 0.3), z["to"], t, z.get("ease", 0.3))
    zexpr = "1+" + "+".join("%.4f*%s" % (float(z["scale"]) - 1, env(z)) for z in zooms)
    wsum = "(" + "+".join(env(z) for z in zooms) + ")"
    cx = "(" + "+".join("%.4f*%s" % (float(z.get("x", 0.5)), env(z)) for z in zooms) + "+0.5*(1-min(1,%s)))" % wsum
    cy = "(" + "+".join("%.4f*%s" % (float(z.get("y", 0.5)), env(z)) for z in zooms) + "+0.5*(1-min(1,%s)))" % wsum
    return zexpr, cx, cy


def cmd_render(a):
    base = os.path.dirname(os.path.abspath(a.cut))
    c = json.load(open(a.cut))
    W, H = c["size"]; fps = int(c.get("fps", 30))
    if a.draft:                                  # half size, fast preset: a look at the cut in seconds
        W, H = (W // 4) * 2, (H // 4) * 2
    fit, bg = c.get("fit", "cover"), c.get("bg", "#000000").lstrip("#")
    keep_audio = c.get("audio", "mute") == "keep"
    segs = c["segments"]
    srcs = []
    for s in segs:
        p = os.path.join(base, s["src"])
        if p not in srcs:
            srcs.append(p)
    info = {p: probe(p) for p in srcs}
    args = ["ffmpeg", "-y", "-v", "error"]
    for p in srcs:
        args += ["-i", p]
    fg, labels = [], []
    if fit == "contain":
        fitf = "scale=%d:%d:force_original_aspect_ratio=decrease,pad=%d:%d:(ow-iw)/2:(oh-ih)/2:color=0x%s" % (W, H, W, H, bg)
    else:
        fitf = "scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d" % (W, H, W, H)
    out_dur = 0.0
    for i, s in enumerate(segs):
        k = srcs.index(os.path.join(base, s["src"])); sp = float(s.get("speed", 1))
        d = (float(s["to"]) - float(s["from"])) / sp; out_dur += d
        fg.append("[%d:v]trim=start=%.3f:end=%.3f,setpts=(PTS-STARTPTS)/%.4f,fps=%d,%s,setsar=1,format=yuv420p[v%d]"
                  % (k, s["from"], s["to"], sp, fps, fitf, i))
        if keep_audio:
            if sp == 1 and info[srcs[k]]["audio"]:
                fg.append("[%d:a]atrim=start=%.3f:end=%.3f,asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo[a%d]"
                          % (k, s["from"], s["to"], i))
            else:
                fg.append("anullsrc=r=48000:cl=stereo,atrim=0:%.4f[a%d]" % (d, i))
            labels.append("[v%d][a%d]" % (i, i))
        else:
            labels.append("[v%d]" % i)
    fg.append("%sconcat=n=%d:v=1:a=%d[vc]%s" % ("".join(labels), len(segs), 1 if keep_audio else 0, "[ac]" if keep_audio else ""))
    last = "vc"
    z = zoom_exprs(c.get("zooms", []), fps)
    if z:
        fg.append("[vc]zoompan=z='%s':x='(iw-iw/zoom)*%s':y='(ih-ih/zoom)*%s':d=1:s=%dx%d:fps=%d[vz]" % (z[0], z[1], z[2], W, H, fps))
        last = "vz"
    tmp = tempfile.mkdtemp(prefix="fastcut-")
    layers = [("t", t) for t in c.get("texts", [])] + [("i", im) for im in c.get("images", [])]
    n_in = len(srcs)
    for j, (kind, L) in enumerate(layers):
        png = os.path.join(tmp, "layer%d.png" % j)
        scaled = dict(L)
        if kind == "t":
            if a.draft:
                scaled["size"] = int(L.get("size", 72)) / 2
            text_png(scaled, W, H, png)
        else:
            image_png(L, base, W, H, png)
        dur = float(L["to"]) - float(L["from"]); fade = min(0.2, dur / 3)
        args += ["-loop", "1", "-framerate", str(fps), "-t", "%.3f" % dur, "-i", png]
        fg.append("[%d:v]format=rgba,fade=t=in:st=0:d=%.3f:alpha=1,fade=t=out:st=%.3f:d=%.3f:alpha=1,setpts=PTS-STARTPTS+%.3f/TB[l%d]"
                  % (n_in + j, fade, dur - fade, fade, float(L["from"]), j))
        fg.append("[%s][l%d]overlay=0:0:eof_action=pass[o%d]" % (last, j, j))
        last = "o%d" % j
    args += ["-filter_complex", ";".join(fg), "-map", "[%s]" % last]
    if keep_audio:
        args += ["-map", "[ac]", "-c:a", "aac", "-b:a", "192k"]
    enc = ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "28"] if a.draft else ["-c:v", "libx264", "-preset", "medium", "-crf", "18"]
    args += enc + ["-pix_fmt", "yuv420p", "-r", str(fps), "-t", "%.3f" % out_dur,
                   "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-movflags", "+faststart", a.out]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    r = subprocess.run(args, capture_output=True, text=True)
    shutil.rmtree(tmp, ignore_errors=True)
    if r.returncode:
        sys.exit("ffmpeg failed:\n" + r.stderr[-2000:])
    p = probe(a.out)
    print("%s  %dx%d  %.2f s  (%s)" % (a.out, p["w"], p["h"], p["dur"], "draft" if a.draft else "final"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan"); s.add_argument("--video", required=True); s.add_argument("--out", required=True)
    s.add_argument("--size", default=None); s.add_argument("--still", type=float, default=1.2); s.add_argument("--speed", type=float, default=8)
    r = sub.add_parser("render"); r.add_argument("--cut", required=True); r.add_argument("--out", required=True)
    r.add_argument("--draft", action="store_true")
    a = ap.parse_args()
    {"scan": cmd_scan, "render": cmd_render}[a.cmd](a)


if __name__ == "__main__":
    main()
