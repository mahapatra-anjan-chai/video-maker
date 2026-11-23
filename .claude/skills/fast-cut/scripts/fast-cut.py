#!/usr/bin/env python3
"""fast-cut.py: edit a screen recording or a video by a cut list, in one FFmpeg pass. Nothing goes through a browser,
so a draft renders in seconds and a full-resolution final in well under a minute for a short ad.

  python3 fast-cut.py scan   --video raw/rec.mov [--size 1080x1920] [--still 1.2] [--speed 8] --out W/cut.json
  python3 fast-cut.py render --cut W/cut.json --out W/render/name-v1.mp4 [--draft]
  python3 fast-cut.py times  --cut W/cut.json        # output times of the taps and zooms (put a click on each tap)

scan reads the motion of the video and writes a starter cut list: everything kept at 1x, and every still stretch
(loading, an AI generating, a pause) longer than --still seconds sped up by --speed. Edit the numbers, then render.

cut.json (all times in seconds; texts and images use OUTPUT time):
{
  "size": [1080, 1920], "fps": 30, "fit": "cover",        # cover = fill and crop, contain = fit inside with "bg" bars
  "bg": "#000000", "audio": "mute",                        # "keep" keeps the sound of 1x segments; sped-up parts are silent
  "box": [80, 330, 920, 1520],                             # optional: all footage sits in x, y, w, h on "bg"; zooms stay inside
  "segments": [ {"color": "#1A1A2E", "dur": 2.5},                       # a plain card (titles go on it as texts)
                {"src": "raw/rec.mov", "from": 0, "to": 12.4, "speed": 1},
                {"src": "raw/rec.mov", "from": 25.0, "to": 32.0, "speed": 6} ],
  "zooms":  [ {"src": "raw/rec.mov", "from": 8.0, "to": 11.0, "scale": 1.3, "x": 0.5, "y": 0.42, "ease": 0.3} ],
  "taps":   [ {"src": "raw/rec.mov", "t": 4.2, "x": 0.25, "y": 0.8, "note": "opens the product"} ],
  "texts":  [ {"text": "See it on you", "from": 1.0, "to": 4.0, "y": 0.12, "size": 76, "color": "#FFFFFF",
               "box": "#000000B3", "weight": "SemiBold", "width": 0.86,
               "intro": {"size": 108, "y": 0.42, "hold": 1.45, "move": 0.65, "scrim": "#1A1A2EE6"}} ],
  "images": [ {"file": "img/logo.png", "from": 0, "to": 3, "x": 0.5, "y": 0.9, "w": 0.3} ]
}
Zooms and taps with "src" use SOURCE time and x, y as shares of the recording's own frame (read them off a contact
sheet); they land wherever the cut puts that moment. Without "src" they use output time and shares of the box (or frame).
A tap is a ripple at the spot; `times` lists when each lands. A text with "intro" opens big over the scrim at "from",
holds, then shrinks and glides to its own "y" / "size" while the scrim lifts and the footage shows through.
Paths in cut.json are relative to the cut.json file. A segment may still carry its own "box" when there is no top-level one.
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, tempfile

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


def font_of(t, size):
    from PIL import ImageFont
    return ImageFont.truetype(t.get("font") or os.path.join(FONTS, "Poppins-%s.ttf" % t.get("weight", "SemiBold")), int(size))


def wrap(text, font, maxw):
    lines = []
    for para in str(text).split("\n"):
        cur = ""
        for word in para.split(" "):
            test = (cur + " " + word).strip()
            if font.getlength(test) <= maxw or not cur:
                cur = test
            else:
                lines.append(cur); cur = word
        lines.append(cur)
    return lines


def text_png(t, W, H, path):
    from PIL import Image, ImageDraw
    size = int(t.get("size", 72))
    font = font_of(t, size)
    maxw = int(W * float(t.get("width", 0.86)))
    lines = wrap(t["text"], font, maxw)
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


def ease_out(u):
    u = min(1.0, max(0.0, u))
    return 1 - (1 - u) ** 3


def ease_in_out(u):
    u = min(1.0, max(0.0, u))
    return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


def intro_pngs(t, W, H, fps, folder, j, k):
    """A headline that opens big over a scrim, then shrinks and glides to its place (`y`, `size`) while the scrim lifts.
    Writes one full-frame PNG per frame of the intro and the resting frame; returns (pattern, frames, rest_png, length).
    k = output width / final width (0.5 in a draft)."""
    from PIL import Image, ImageDraw
    it = t["intro"]
    small = float(t.get("size", 72)) * k
    maxw = W * float(t.get("width", 0.86))
    big = float(it.get("size", 108)) * k
    lines = wrap(t["text"], font_of(t, small), maxw)            # the resting layout decides the lines; big keeps them
    f = font_of(t, big)
    big = min(big, big * maxw / max(f.getlength(l) for l in lines))
    f = font_of(t, big); big = f.size
    lh = int(big * 1.22)
    bw = int(max(f.getlength(l) for l in lines)) + 4; bh = lh * (len(lines) - 1) + int(big * 1.3)
    color = hex_rgba(t.get("color", "#FFFFFF"))
    line_imgs = []
    for l in lines:
        im = Image.new("RGBA", (bw, int(big * 1.3)), (0, 0, 0, 0))
        ImageDraw.Draw(im).text(((bw - f.getlength(l)) / 2, 0), l, font=f, fill=color)
        line_imgs.append(im)
    block = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    for i, im in enumerate(line_imgs):
        block.alpha_composite(im, (0, i * lh))
    cx = W * float(t.get("x", 0.5))
    yc_big = H * float(it.get("y", 0.42))
    r = small / big                                              # the resting scale of the big block
    yc_small = H * float(t.get("y", 0.12)) + bh * r / 2
    scrim = hex_rgba(it.get("scrim", "#1A1A2EE6"))
    s_in, rise_at = float(it.get("scrim_in", 0.3)), float(it.get("rise_at", 0.15))
    hold, move = float(it.get("hold", 1.45)), float(it.get("move", 0.65))
    mask = it.get("entrance") == "mask"                          # lines slide up out of a mask instead of fading up
    bar = None
    if t.get("mark"):                                            # after it lands, a bar marks the value phrase
        for i, l in enumerate(lines):
            at = l.find(t["mark"])
            if at >= 0:
                x0 = (bw - f.getlength(l)) / 2 + f.getlength(l[:at]); x1 = x0 + f.getlength(t["mark"])
                top_, bottom_ = f.getbbox("Hgy")[1], f.getbbox("Hgy")[3]
                pad = big * 0.12
                bar = (x0 - pad, i * lh + top_ - big * 0.08, x1 + pad, i * lh + bottom_ + big * 0.04)
                break
        if bar is None:
            sys.exit("mark %r is not in the headline %r" % (t["mark"], t["text"]))
    mark_col = hex_rgba(t.get("mark_color", "#5A34F5"))
    mark_at, mark_len = hold + move + 0.12, 0.45
    n = int(round((hold + move + (mark_at - hold - move + mark_len if bar else 0)) * fps))
    marked = {}

    def block_at(pm):                                            # the block with the bar grown to pm (0-1) behind the text
        if bar is None or pm <= 0:
            return block
        key = round(pm, 3)
        if key not in marked:
            im = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
            ImageDraw.Draw(im).rounded_rectangle([bar[0], bar[1], bar[0] + (bar[2] - bar[0]) * pm, bar[3]], radius=big * 0.12, fill=mark_col)
            im.alpha_composite(block); marked[key] = im
        return marked[key]

    def frame(tau):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        u = ease_in_out((tau - hold) / move) if tau > hold else 0.0
        a = scrim[3] * min(1.0, tau / s_in if s_in else 1.0) * (1 - u)
        if a > 0:
            img.paste(Image.new("RGBA", (W, H), scrim[:3] + (int(a),)), (0, 0))
        if tau <= hold:                                          # lines come in one after another
            top = yc_big - bh / 2
            for i, im in enumerate(line_imgs):
                e = ease_out((tau - rise_at - (0.12 if mask else 0.1) * i) / (0.6 if mask else 0.45))
                if e <= 0:
                    continue
                if mask:                                         # slide up inside the line's own box
                    lh_i = im.height; cut = Image.new("RGBA", im.size, (0, 0, 0, 0))
                    cut.alpha_composite(im, (0, int(lh_i * 1.05 * (1 - e)))) if e < 1 else cut.alpha_composite(im)
                    img.alpha_composite(cut, (int(cx - bw / 2), int(top + i * lh)))
                    continue
                if e < 1:
                    im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * e)))
                img.alpha_composite(im, (int(cx - bw / 2), int(top + i * lh + 0.025 * H * (1 - e))))
        else:                                                    # shrink and glide to the resting place, then mark
            s = 1 + (r - 1) * u
            im = block_at(ease_in_out((tau - mark_at) / mark_len)).resize((max(1, int(round(bw * s))), max(1, int(round(bh * s)))), Image.LANCZOS)
            yc = yc_big + (yc_small - yc_big) * u
            img.alpha_composite(im, (int(round(cx - im.width / 2)), int(round(yc - im.height / 2))))
        return img

    pattern = os.path.join(folder, "intro%d_%%04d.png" % j)
    for i in range(n):
        frame(i / float(fps)).save(pattern % i, compress_level=1)
    rest = os.path.join(folder, "rest%d.png" % j)
    frame(n / float(fps) + 1).save(rest, compress_level=1)
    return pattern, n, rest, n / float(fps)


def mask_frames(t, W, H, fps, dur, folder, j, k):
    """Text mask (no. 40) with footage: the word as a grey matte, one PNG per frame. The letters settle in over 0.5 s,
    hold, then from grow.at (s after "from") the camera flies through the letter "through" until it fills the frame.
    With "pull" it runs the other way: the frame starts filled from inside that letter and pulls back onto the word."""
    from PIL import Image, ImageDraw
    import math
    text = str(t["text"]); S = 4                                 # drawn at 4x so the fly-through stays sharp
    tt = dict(t, weight=t.get("weight", "Bold"))
    size = float(t.get("size", 300)) * k
    f = font_of(tt, size)
    maxw = W * float(t.get("width", 0.92))
    if f.getlength(text) > maxw:
        size *= maxw / f.getlength(text); f = font_of(tt, size)
    fh = font_of(tt, size * S)
    l, tp, r, b = fh.getbbox(text)
    word = Image.new("L", (r - l + 8 * S, b - tp + 8 * S), 0)
    ImageDraw.Draw(word).text((4 * S - l, 4 * S - tp), text, font=fh, fill=255)
    ww, wh = word.size[0] / S, word.size[1] / S                  # the word's box at 1x
    rx, ry = W * float(t.get("x", 0.5)) - ww / 2, H * float(t.get("y", 0.5)) - wh / 2      # y = the word's centre
    ch = t.get("through", text[len(text) // 2])
    i = text.find(ch) if ch in text else len(text) // 2
    ox = rx + 4 + (f.getlength(text[:i]) + f.getlength(text[i]) / 2) - (l / S)
    oy = ry + wh * 0.55
    g, pl = t.get("grow"), t.get("pull")                        # fly in at the end, or start inside and pull back out
    n = int(round(dur * fps))
    pattern = os.path.join(folder, "mask%d_%%04d.png" % j)
    for fi in range(n):
        tau = fi / float(fps)
        if pl:                                                   # the frame starts filled, the word forms around it
            e = 1.0
            sc_ = math.exp(math.log(float(pl.get("scale", 60))) * (1 - ease_out(tau / float(pl.get("dur", 0.85)))) ** float(pl.get("ease", 1.0)))
        else:
            e = ease_out(tau / 0.5); sc_ = 0.9 + 0.1 * e
        if g:
            g_at = float(g.get("at", dur - 0.6))
            u = min(1.0, max(0.0, (tau - g_at) / max(0.01, dur - g_at)))
            sc_ *= math.exp(math.log(float(g.get("scale", 40))) * u ** float(g.get("ease", 1.5)))
        qx0, qy0 = ox - ox / sc_, oy - oy / sc_                  # what of the 1x frame is in view at this scale
        qx1, qy1 = ox + (W - ox) / sc_, oy + (H - oy) / sc_
        crop = word.crop((int((qx0 - rx) * S), int((qy0 - ry) * S), int((qx1 - rx) * S), int((qy1 - ry) * S)))
        fr = crop.resize((W, H), Image.BILINEAR)
        if e < 1:
            fr = fr.point(lambda v: int(v * e))
        fr.save(pattern % fi, compress_level=1)
    return pattern


TFX = os.path.join(HERE, "..", "..", "text-animations", "scripts", "tfx.py")


def anim_clip(t, W, H, fps, base, sc, k, dur):
    """A text with "anim": render it once through the text-animations skill as a transparent MOV (cached by content).
    It sits in "anim_box" [x, y, w, h] (final pixels) or, by default, a band at the text's own "y" and "width"."""
    size = float(t.get("size", 72)) * k
    if t.get("anim_box"):
        bx, by, bw, bh = (sc(v) for v in t["anim_box"])
    else:
        lines = str(t["text"]).count("\n") + 1
        bw = int(W * float(t.get("width", 0.86))); bh = int(size * (1.3 * lines + 1.4))
        bx = int(W * float(t.get("x", 0.5)) - bw / 2); by = max(0, int(H * float(t.get("y", 0.12)) - size * 0.45))
    spec = [t["anim"], t["text"], W, H, bx, by, bw, bh, size, dur, fps, t.get("color"), t.get("accent"), t.get("accent2")]
    out = os.path.join(base, ".tfx-cache", hashlib.sha1(json.dumps(spec).encode()).hexdigest()[:12] + ".mov")
    args = [sys.executable, TFX, "clip", "--id", t["anim"], "--text", str(t["text"]).replace("\n", " "), "--size", "%dx%d" % (W, H),
            "--box", "%d,%d,%d,%d" % (bx, by, bw, bh), "--font-size", "%.1f" % size, "--dur", "%.3f" % dur, "--fps", str(fps), "--out", out]
    for key, flag in (("color", "--ink"), ("accent", "--accent"), ("accent2", "--accent2")):
        if t.get(key):
            args += [flag, t[key]]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        sys.exit("text animation %r failed:\n%s" % (t["anim"], (r.stdout + r.stderr)[-1500:]))
    return out


def ripple_pngs(d, n, folder):
    """A tap: a dot pressed in, then a ring spreading out and fading. Purple edge (reads on white screens),
    lavender ring (reads on dark ones). d = size in px, n = frames."""
    from PIL import Image, ImageDraw
    S = 4; D = d * S; c = D / 2.0
    for i in range(n):
        p = i / float(n - 1)
        im = Image.new("RGBA", (D, D), (0, 0, 0, 0)); g = ImageDraw.Draw(im)
        q = ease_out((p - 0.12) / 0.88)
        if 0 < q < 1:
            rr = D * (0.17 + 0.29 * q); w = max(1, int(D * (0.035 - 0.022 * q)))
            g.ellipse([c - rr, c - rr, c + rr, c + rr], outline=(204, 171, 255, int(235 * (1 - q))), width=w)
        fade = 1.0 if p < 0.5 else max(0.0, 1 - (p - 0.5) / 0.5)
        if fade > 0:
            rd = D * 0.15 * (0.8 + 0.2 * ease_out(p / 0.2))
            g.ellipse([c - rd, c - rd, c + rd, c + rd], fill=(255, 255, 255, int(150 * fade)),
                      outline=(90, 52, 245, int(240 * fade)), width=int(D * 0.025))
        im.resize((d, d), Image.LANCZOS).save(os.path.join(folder, "ripple%02d.png" % i))
    return os.path.join(folder, "ripple%02d.png")


# ---------------------------------------------------------------- where things land in the output
def timeline(c):
    """[(segment, output start, output length, speed)] and the total length."""
    rows, t = [], 0.0
    for s in c["segments"]:
        sp = float(s.get("speed", 1)) if "src" in s else 1.0
        d = (float(s["to"]) - float(s["from"])) / sp if "src" in s else float(s["dur"])
        rows.append((s, t, d, sp)); t += d
    return rows, t


def zoom_at(zooms, T):
    """Zoom factor and focus (area shares) at output time T: the same sums zoom_exprs hands to zoompan."""
    envs = [min(1, max(0, (T - z["from"]) / z.get("ease", 0.3))) * min(1, max(0, (z["to"] - T) / z.get("ease", 0.3))) for z in zooms]
    rest = 0.5 * (1 - min(1, sum(envs)))
    return (1 + sum((float(z["scale"]) - 1) * e for z, e in zip(zooms, envs)),
            sum(float(z.get("x", 0.5)) * e for z, e in zip(zooms, envs)) + rest,
            sum(float(z.get("y", 0.5)) * e for z, e in zip(zooms, envs)) + rest)


def resolve(c, base, info, area, sc):
    """Zooms and taps given in source time and source position ("src") -> output time and shares of the area the
    footage fills (the top-level box, else the frame). A tap's position is where it shows after any zoom."""
    ax, ay, aw, ah = area
    rows, total = timeline(c)
    key = lambda p: os.path.normpath(os.path.join(base, p))

    def out_time(src, t):
        for s, o, d, sp in rows:
            if "src" in s and key(s["src"]) == key(src) and float(s["from"]) - 1e-6 <= t <= float(s["to"]) + 1e-6:
                return o + (t - float(s["from"])) / sp, s
        sys.exit("%s at %.2f s is not in the cut" % (src, t))

    def share(s, x, y):
        sw, sh = info[key(s["src"])]["w"], info[key(s["src"])]["h"]
        if s.get("box") and not c.get("box"):
            bx, by, bw, bh = (sc(v) for v in s["box"]); fit = "contain"
        else:
            bx, by, bw, bh = 0, 0, aw, ah; fit = c.get("fit", "cover")
        k = min(bw / sw, bh / sh) if fit == "contain" else max(bw / sw, bh / sh)
        return (bx + (bw - sw * k) / 2 + x * sw * k) / aw, (by + (bh - sh * k) / 2 + y * sh * k) / ah

    zooms = []
    for z in c.get("zooms", []):
        z = dict(z)
        if "src" in z:
            a, s = out_time(z["src"], float(z["from"])); b, _ = out_time(z["src"], float(z["to"]))
            z["x"], z["y"] = share(s, float(z.get("x", 0.5)), float(z.get("y", 0.5)))
            z["from"], z["to"] = a, b
        zooms.append(z)
    taps = []
    for tp in c.get("taps", []):
        if "src" in tp:
            T, s = out_time(tp["src"], float(tp["t"])); x, y = share(s, float(tp["x"]), float(tp["y"]))
        else:
            T, x, y = float(tp["t"]), float(tp["x"]), float(tp["y"])
        z, fx, fy = zoom_at(zooms, T)
        taps.append({"t": round(T, 3), "x": z * x - (z - 1) * fx, "y": z * y - (z - 1) * fy, "note": tp.get("note", "")})
    return zooms, taps, rows, total


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


def setup(a):
    """The cut, its sources, output size and the area the footage fills (top-level "box", else the frame)."""
    base = os.path.dirname(os.path.abspath(a.cut))
    c = json.load(open(a.cut))
    W, H = c["size"]
    if getattr(a, "draft", False):               # half size, fast preset: a look at the cut in seconds
        W, H = (W // 4) * 2, (H // 4) * 2
    sc = lambda v: int(round(v * W / c["size"][0] / 2)) * 2      # box coordinates are in final-size pixels
    srcs = []
    fills = [f for t in c.get("texts", []) for f in t.get("fill", [])]     # footage inside letters (text-mask)
    for s in c["segments"] + fills:
        if "src" in s:
            p = os.path.normpath(os.path.join(base, s["src"]))
            if p not in srcs:
                srcs.append(p)
    info = {p: probe(p) for p in srcs}
    if c.get("box"):
        if any(s.get("box") for s in c["segments"]):
            sys.exit('use the top-level "box" or per-segment boxes, not both')
        area = tuple(sc(v) for v in c["box"])
    else:
        area = (0, 0, W, H)
    return base, c, W, H, sc, srcs, info, area


def cmd_times(a):
    """Output times of the taps and zooms (for the sound mix: a click on every tap)."""
    base, c, W, H, sc, srcs, info, area = setup(a)
    zooms, taps, rows, total = resolve(c, base, info, area, sc)
    heads = [{"from": float(t["from"]), "to": float(t["to"]), "text": t["text"].replace("\n", " "),
              "length": float(t["intro"].get("hold", 1.45)) + float(t["intro"].get("move", 0.65)) if t.get("intro") else 0}
             for t in c.get("texts", [])]
    print(json.dumps({"duration": round(total, 3), "taps": [{"t": t["t"], "note": t["note"]} for t in taps],
                      "zooms": [[round(z["from"], 3), round(z["to"], 3)] for z in zooms], "texts": heads}, indent=1))


def cmd_render(a):
    base, c, W, H, sc, srcs, info, area = setup(a)
    fps = int(c.get("fps", 30)); k_out = W / float(c["size"][0])
    fit, bg = c.get("fit", "cover"), c.get("bg", "#000000").lstrip("#")
    keep_audio = c.get("audio", "mute") == "keep"
    ax, ay, aw, ah = area
    zooms, taps, rows, out_dur = resolve(c, base, info, area, sc)
    args = ["ffmpeg", "-y", "-v", "error"]
    for p in srcs:
        args += ["-i", p]
    n_in = len(srcs)
    fg, labels = [], []
    if fit == "contain":
        fitf = "scale=%d:%d:force_original_aspect_ratio=decrease,pad=%d:%d:(ow-iw)/2:(oh-ih)/2:color=0x%s" % (aw, ah, aw, ah, bg)
    else:
        fitf = "scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d" % (aw, ah, aw, ah)
    for i, (s, o, d, sp) in enumerate(rows):
        if "src" not in s:                     # a plain colour card
            k = None
            fg.append("color=c=0x%s:s=%dx%d:r=%d:d=%.3f,setsar=1,format=yuv420p[v%d]" % (s.get("color", "#" + bg).lstrip("#"), aw, ah, fps, d, i))
        else:
            k = srcs.index(os.path.normpath(os.path.join(base, s["src"])))
            if s.get("box"):
                bx, by, bw, bh = (sc(v) for v in s["box"])
                place = ("scale=%d:%d:force_original_aspect_ratio=decrease,pad=%d:%d:%d+(%d-iw)/2:%d+(%d-ih)/2:color=0x%s"
                         % (bw, bh, W, H, bx, bw, by, bh, s.get("bg", bg).lstrip("#")))
            else:
                place = fitf
            fg.append("[%d:v]trim=start=%.3f:end=%.3f,setpts=(PTS-STARTPTS)/%.4f,fps=%d,%s,setsar=1,format=yuv420p[v%d]"
                      % (k, s["from"], s["to"], sp, fps, place, i))
        if keep_audio:
            if k is not None and sp == 1 and info[srcs[k]]["audio"]:
                fg.append("[%d:a]atrim=start=%.3f:end=%.3f,asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo[a%d]"
                          % (k, s["from"], s["to"], i))
            else:
                fg.append("anullsrc=r=48000:cl=stereo,atrim=0:%.4f[a%d]" % (d, i))
            labels.append("[v%d][a%d]" % (i, i))
        else:
            labels.append("[v%d]" % i)
    fg.append("%sconcat=n=%d:v=1:a=%d[vc]%s" % ("".join(labels), len(rows), 1 if keep_audio else 0, "[ac]" if keep_audio else ""))
    last = "vc"
    z = zoom_exprs(zooms, fps)
    if z:                                        # zoom from a 2x copy so the slow push does not step a pixel at a time
        fg.append("[vc]scale=%d:%d,zoompan=z='%s':x='(iw-iw/zoom)*%s':y='(ih-ih/zoom)*%s':d=1:s=%dx%d:fps=%d[vz]"
                  % (2 * aw, 2 * ah, z[0], z[1], z[2], aw, ah, fps))
        last = "vz"
    if c.get("box"):                             # the footage (and its zooms) stay inside the box on a "bg" canvas
        fg.append("color=c=0x%s:s=%dx%d:r=%d:d=%.3f,setsar=1,format=yuv420p[cv]" % (bg, W, H, fps, out_dur))
        fg.append("[cv][%s]overlay=%d:%d[vb]" % (last, ax, ay))
        last = "vb"
        for i, (s, o, d, sp) in enumerate(rows):
            col = s.get("color", "#" + bg).lstrip("#") if "src" not in s else bg
            if col.lower() != bg.lower():        # a card in another colour still fills the frame
                fg.append("color=c=0x%s:s=%dx%d:r=%d:d=%.3f,format=yuv420p,setpts=PTS-STARTPTS+%.3f/TB[cd%d]" % (col, W, H, fps, d, o, i))
                fg.append("[%s][cd%d]overlay=0:0:eof_action=pass[cb%d]" % (last, i, i))
                last = "cb%d" % i
    tmp = tempfile.mkdtemp(prefix="fastcut-")
    if taps:
        d = int(round(170 * k_out / 2)) * 2; nfr = int(round(0.55 * fps))
        args += ["-framerate", str(fps), "-i", ripple_pngs(d, nfr, tmp)]
        fg.append("[%d:v]format=rgba,split=%d%s" % (n_in, len(taps), "".join("[r%d]" % j for j in range(len(taps)))))
        n_in += 1
        for j, tp in enumerate(taps):
            fg.append("[r%d]setpts=PTS-STARTPTS+%.3f/TB[rt%d]" % (j, tp["t"], j))
            fg.append("[%s][rt%d]overlay=%d:%d:eof_action=pass[tp%d]"
                      % (last, j, int(round(ax + tp["x"] * aw - d / 2)), int(round(ay + tp["y"] * ah - d / 2)), j))
            last = "tp%d" % j
    layers = [("t", t) for t in c.get("texts", [])] + [("i", im) for im in c.get("images", [])]
    for j, (kind, L) in enumerate(layers):
        png = os.path.join(tmp, "layer%d.png" % j)
        start, fade_in = float(L["from"]), True
        if kind == "t" and L.get("intro"):       # the big opening, then the resting headline from where it lands
            pattern, nfr, png, length = intro_pngs(L, W, H, fps, tmp, j, k_out)
            args += ["-framerate", str(fps), "-i", pattern]
            fg.append("[%d:v]format=rgba,setpts=PTS-STARTPTS+%.3f/TB[in%d]" % (n_in, start, j))
            fg.append("[%s][in%d]overlay=0:0:eof_action=pass[io%d]" % (last, j, j))
            last = "io%d" % j; n_in += 1
            start += length; fade_in = False
        elif kind == "t" and L.get("anim") == "text-mask" and L.get("fill"):   # footage inside the letters
            dur = float(L["to"]) - start
            pattern = mask_frames(L, W, H, fps, dur, tmp, j, k_out)
            args += ["-framerate", str(fps), "-i", pattern]
            parts = []
            for q, f in enumerate(L["fill"]):
                kk = srcs.index(os.path.normpath(os.path.join(base, f["src"])))
                z = float(f.get("zoom", 1.3)); fx, fy = f.get("focus", [0.5, 0.5])      # which part of the recording shows through
                cy = H * float(L.get("y", 0.5))
                fg.append("[%d:v]trim=start=%.3f:end=%.3f,setpts=(PTS-STARTPTS)/%.4f,fps=%d,scale=%d:%d:force_original_aspect_ratio=increase,"
                          "crop=%d:%d:'min(max(0,%.4f*iw-%d),iw-ow)':'min(max(0,%.4f*ih-%d),ih-oh)',eq=saturation=%.2f,setsar=1,format=yuv420p[mf%d_%d]"
                          % (kk, f["from"], f["to"], float(f.get("speed", 1)), fps, int(W * z) // 2 * 2, int(H * z) // 2 * 2, W, H,
                             float(fx), W // 2, float(fy), int(cy), float(L.get("saturation", 1.15)), j, q))
                parts.append("[mf%d_%d]" % (j, q))
            fg.append("%sconcat=n=%d:v=1,tpad=stop_mode=clone:stop_duration=%.3f,trim=0:%.3f,setpts=PTS-STARTPTS,format=rgba[mfill%d]"
                      % ("".join(parts), len(parts), dur, dur, j))
            fg.append("[%d:v]format=gray,setpts=PTS-STARTPTS[mm%d]" % (n_in, j))
            fg.append("[mfill%d][mm%d]alphamerge,setpts=PTS-STARTPTS+%.3f/TB[l%d]" % (j, j, start, j))
            fg.append("[%s][l%d]overlay=0:0:eof_action=pass[o%d]" % (last, j, j))
            last = "o%d" % j; n_in += 1
            continue
        elif kind == "t" and L.get("anim"):      # one of the text-animations skill's 58, rendered with an alpha channel
            dur = float(L["to"]) - start; fade = min(0.2, dur / 3)
            args += ["-i", anim_clip(L, W, H, fps, base, sc, k_out, dur)]
            fg.append("[%d:v]format=rgba,fade=t=out:st=%.3f:d=%.3f:alpha=1,setpts=PTS-STARTPTS+%.3f/TB[l%d]" % (n_in, dur - fade, fade, start, j))
            fg.append("[%s][l%d]overlay=0:0:eof_action=pass[o%d]" % (last, j, j))
            last = "o%d" % j; n_in += 1
            continue
        elif kind == "t":
            scaled = dict(L)
            scaled["size"] = float(L.get("size", 72)) * k_out
            text_png(scaled, W, H, png)
        else:
            image_png(L, base, W, H, png)
        dur = float(L["to"]) - start; fade = min(0.2, dur / 3)
        args += ["-loop", "1", "-framerate", str(fps), "-t", "%.3f" % dur, "-i", png]
        fg.append("[%d:v]format=rgba,%sfade=t=out:st=%.3f:d=%.3f:alpha=1,setpts=PTS-STARTPTS+%.3f/TB[l%d]"
                  % (n_in, "fade=t=in:st=0:d=%.3f:alpha=1," % fade if fade_in else "", dur - fade, fade, start, j))
        fg.append("[%s][l%d]overlay=0:0:eof_action=pass[o%d]" % (last, j, j))
        last = "o%d" % j; n_in += 1
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
    if taps:
        print("taps at " + "  ".join("%.2f" % t["t"] for t in taps))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan"); s.add_argument("--video", required=True); s.add_argument("--out", required=True)
    s.add_argument("--size", default=None); s.add_argument("--still", type=float, default=1.2); s.add_argument("--speed", type=float, default=8)
    r = sub.add_parser("render"); r.add_argument("--cut", required=True); r.add_argument("--out", required=True)
    r.add_argument("--draft", action="store_true")
    t = sub.add_parser("times"); t.add_argument("--cut", required=True)
    a = ap.parse_args()
    {"scan": cmd_scan, "render": cmd_render, "times": cmd_times}[a.cmd](a)


if __name__ == "__main__":
    main()
