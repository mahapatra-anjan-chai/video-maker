#!/usr/bin/env python3
"""Measure a reference video's style and lay it out for the eye: pacing, palette, on-screen type, and the moments
where things move.

  python3 style-scan.py --video videos/<p>/refs/<ref>.mp4 --out videos/<p>/refs/<ref>/ [--text-fps 2] [--strips 8]

Writes into --out:
  scan.json      the numbers: pacing (the kit's teardown.py: cuts, bursts, quiet stretches, loudness), palette (k-means
                 on a frame a second, with the background and accent colours picked out), on-screen text (share of
                 time with text, size as a share of the frame height, where it sits on a 3x3 grid, upper-case share,
                 words a card, how long a card stays, and how often a line grows word by word)
  shots.jpg      one frame from the middle of every shot, with its start and length
  motion.jpg     strips of 8 frames over ~0.7 s at the busiest moments that are not cuts: entrances, camera moves,
                 transitions and animated graphics show here, so read the techniques off this sheet
  motion.json    every move measured at the full frame rate (motion.py): kind, direction, length, ease family and
  MOTION.md      GSAP ease, overshoot, staggers, time from a cut, holds, steady cutting, beats (with --bpm)
  curves.png     each move's measured progress with the fitted ease drawn over it, to check the fits by eye
  text.jpg       the largest on-screen text cards, cropped, to read the type treatment (weight, case, boxes, colour)
  palette.png    the colours with their share of the screen
  SCAN.md        the numbers in words, for the style card

Measures only what pixels say reliably; camera moves, transition types, textures and illustration style are for the
eye, from the sheets. Reference files and these sheets stay in videos/ (never committed).
"""
import argparse, io, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(HERE))
TEARDOWN = os.path.join(SKILLS, "youtube-edit", "scripts", "teardown.py")
OCR = os.path.join(SKILLS, "localize", "scripts", "ocr.swift")
TITLE = 0.025     # text at least this share of the frame height counts as a title


def probe(video):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height,r_frame_rate:format=duration", "-of", "json", video],
                                  capture_output=True, text=True, check=True).stdout)
    s = j["streams"][0]
    n, d = s["r_frame_rate"].split("/")
    return s["width"], s["height"], float(n) / float(d), float(j["format"]["duration"])


def frames(video, fps, w, h, fmt="rgb24", start=None, dur=None):
    import numpy as np
    ch = 3 if fmt == "rgb24" else 1
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", "%.3f" % start] if start is not None else []) + ["-i", video] + \
          (["-t", "%.3f" % dur] if dur is not None else []) + \
          ["-vf", "fps=%g,scale=%d:%d" % (fps, w, h), "-pix_fmt", fmt, "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype="uint8").reshape(-1, h, w, ch) if ch == 3 else np.frombuffer(raw, dtype="uint8").reshape(-1, h, w)


def hexc(c):
    return "#%02X%02X%02X" % tuple(int(v) for v in c)


def palette(video, W, H, k=8):
    """k-means on a 96 px frame a second; the background is the commonest colour on the frame's border."""
    import numpy as np
    h = max(2, round(54 * H / W / (9 / 16)) // 2 * 2) if W else 54
    f = frames(video, 1, 96, h).astype("float32")
    px = f.reshape(-1, 3)
    rng = np.random.default_rng(7)
    sample = px[rng.choice(len(px), min(len(px), 40000), replace=False)]
    cent = sample[rng.choice(len(sample), k, replace=False)]
    for _ in range(25):
        lab = np.argmin(((sample[:, None, :] - cent[None]) ** 2).sum(2), 1)
        cent = np.array([sample[lab == i].mean(0) if (lab == i).any() else cent[i] for i in range(k)])
    lab = np.argmin(((px[:, None, :] - cent[None]) ** 2).sum(2), 1)
    share = np.bincount(lab, minlength=k) / len(lab)
    border = np.concatenate([f[:, 0].reshape(-1, 3), f[:, -1].reshape(-1, 3), f[:, :, 0].reshape(-1, 3), f[:, :, -1].reshape(-1, 3)])
    blab = np.argmin(((border[:, None, :] - cent[None]) ** 2).sum(2), 1)
    bg = int(np.bincount(blab, minlength=k).argmax())
    out = []
    for i in np.argsort(-share):
        if share[i] < 0.005 or any(((cent[i] - cent[j]) ** 2).sum() < 400 for j in np.argsort(-share) if share[j] > share[i]):
            continue            # an empty cluster, or a twin of a bigger one
        c = cent[i]; mx, mn = c.max(), c.min()
        sat = 0.0 if mx < 1 else (mx - mn) / mx
        role = "background" if i == bg else ("accent" if sat > 0.45 and c.mean() > 50 and share[i] < 0.15 else "")
        out.append({"hex": hexc(c), "share": round(float(share[i]), 3), "saturation": round(float(sat), 2),
                    "lightness": round(float(c.mean() / 255), 2), "role": role})
    # accents: small, saturated colours the main clusters swallow (a highlight bar, a brand colour on a button)
    mx, mn = px.max(1), px.min(1)
    hot = px[((mx - mn) / np.maximum(mx, 1) > 0.5) & (mx > 70)]
    if len(hot) > 50:
        hs = hot[rng.choice(len(hot), min(len(hot), 20000), replace=False)]
        kc = hs[rng.choice(len(hs), 4, replace=False)]
        for _ in range(20):
            hl = np.argmin(((hs[:, None, :] - kc[None]) ** 2).sum(2), 1)
            kc = np.array([hs[hl == i].mean(0) if (hl == i).any() else kc[i] for i in range(4)])
        hl = np.argmin(((hot[:, None, :] - kc[None]) ** 2).sum(2), 1)
        cnt = np.bincount(hl, minlength=4)
        for i in np.argsort(-cnt):
            if cnt[i] / len(px) >= 0.002 and all(((kc[i] - np.array([int(o["hex"][j:j + 2], 16) for j in (1, 3, 5)])) ** 2).sum() > 900 for o in out):
                out.append({"hex": hexc(kc[i]), "share": round(float(cnt[i] / len(px)), 3), "saturation": None,
                            "lightness": round(float(kc[i].mean() / 255), 2), "role": "accent"})
    hsv_s = (f.max(3) - f.min(3)) / np.maximum(f.max(3), 1)
    return out, {"mean_saturation": round(float(hsv_s.mean()), 2), "mean_lightness": round(float(f.mean() / 255), 2)}


def text_scan(video, W, H, fps, dur, tmp):
    """Vision OCR on the full frame (1280 wide) every 1/fps s."""
    import numpy as np
    d = os.path.join(tmp, "ocr"); os.makedirs(d)
    sw = 1280; sh = int(round(H * sw / W / 2) * 2)
    subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", "fps=%g,scale=%d:%d" % (fps, sw, sh), "-q:v", "3",
                    os.path.join(d, "%05d.jpg")], check=True)
    raw = os.path.join(tmp, "ocr.json")
    subprocess.run(["swift", OCR, d, raw], check=True, capture_output=True)
    reads = json.load(open(raw))
    items, timeline = [], []
    for fr in reads:
        t = (int(fr["file"][:5]) - 1) / fps
        its = [x for x in fr["items"] if x["conf"] >= 0.4 and len(x["text"].strip()) > 1]
        timeline.append((t, its))
        for x in its:
            items.append({"t": t, "text": x["text"], "x0": x["x0"] / sw, "x1": x["x1"] / sw, "y0": x["y0"] / sh, "y1": x["y1"] / sh})
    if not items:
        return {"share_of_time": 0.0, "cards": 0}, [], (sw, sh)
    hts = np.array([i["y1"] - i["y0"] for i in items])
    grid = np.zeros((3, 3), dtype=int)
    for i in items:
        cx, cy = (i["x0"] + i["x1"]) / 2, (i["y0"] + i["y1"]) / 2
        grid[min(2, int(cy * 3)), min(2, int(cx * 3))] += 1
    letters = "".join(i["text"] for i in items)
    alpha = [c for c in letters if c.isalpha()]
    # cards: the same line seen on consecutive reads; a line whose later reads extend it grew word by word
    cards, grow = [], 0
    for t, its in timeline:
        for x in its:
            key = x["text"].strip().lower()
            hit = next((c for c in cards if c["open"] and (key.startswith(c["key"][:8]) or c["key"].startswith(key[:8]))), None)
            if hit and t - hit["last"] <= 1.5 / fps:
                if len(key) > len(hit["key"]) + 2 and key.startswith(hit["key"][: max(3, len(hit["key"]) - 1)]):
                    hit["grew"] = True
                hit["key"] = key if len(key) > len(hit["key"]) else hit["key"]
                hit["last"] = t
            else:
                cards.append({"key": key, "first": t, "last": t, "open": True, "grew": False, "box": x})
        for c in cards:
            if c["open"] and t - c["last"] > 1.5 / fps:
                c["open"] = False
    grow = sum(1 for c in cards if c["grew"])
    on = sum(1 for t, its in timeline if its)
    big = [i for i in items if i["y1"] - i["y0"] >= TITLE]
    tgrid = np.zeros((3, 3), dtype=int)
    for i in big:
        cx, cy = (i["x0"] + i["x1"]) / 2, (i["y0"] + i["y1"]) / 2
        tgrid[min(2, int(cy * 3)), min(2, int(cx * 3))] += 1
    talpha = [c for c in "".join(i["text"] for i in big) if c.isalpha()]
    stats = {
        "titles": {"note": "text at least %.1f%% of the frame high: designed type, not UI labels" % (TITLE * 100),
                   "share_of_time": round(len({i["t"] for i in big}) / max(1, len(timeline)), 2),
                   "reads": len(big),
                   "height_share_median": round(float(np.median([i["y1"] - i["y0"] for i in big])), 3) if big else None,
                   "uppercase_share": round(sum(1 for c in talpha if c.isupper()) / max(1, len(talpha)), 2) if big else None,
                   "words_median": float(np.median([len(i["text"].split()) for i in big])) if big else None,
                   "grid": tgrid.tolist()},
        "share_of_time": round(on / max(1, len(timeline)), 2),
        "cards": len(cards),
        "cards_per_min": round(len(cards) / max(dur, 1) * 60, 1),
        "card_seconds_median": round(float(np.median([c["last"] - c["first"] + 1 / fps for c in cards])), 2),
        "words_per_card_median": float(np.median([len(c["key"].split()) for c in cards])),
        "height_share_median": round(float(np.median(hts)), 3),
        "height_share_p90": round(float(np.percentile(hts, 90)), 3),
        "uppercase_share": round(sum(1 for c in alpha if c.isupper()) / max(1, len(alpha)), 2),
        "grid_top_mid_bottom_x_left_centre_right": grid.tolist(),
        "grows_word_by_word": grow,
    }
    return stats, cards, (sw, sh)


def sheet(images, labels, cols, path, label_h=22):
    from PIL import Image, ImageDraw
    if not images:
        return
    w, h = images[0].size
    rows = (len(images) + cols - 1) // cols
    s = Image.new("RGB", (w * cols, (h + label_h) * rows), (16, 16, 20))
    d = ImageDraw.Draw(s)
    for i, (im, lb) in enumerate(zip(images, labels)):
        x, y = (i % cols) * w, (i // cols) * (h + label_h)
        s.paste(im.resize((w, h)), (x, y))
        d.text((x + 6, y + h + 5), lb, fill=(235, 235, 235))
    s.save(path, quality=86)


DUR = [None]


def grab(video, t, width):
    from PIL import Image
    if DUR[0]:
        t = min(t, DUR[0] - 0.1)      # a seek past the last frame returns nothing
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.3f" % max(0, t), "-i", video, "-frames:v", "1", "-vf",
                          "scale=%d:-2" % width, "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    return Image.open(io.BytesIO(raw)).convert("RGB")


def mmss(t):
    return "%d:%04.1f" % (t // 60, t % 60)


def main():
    import numpy as np
    from PIL import Image, ImageDraw
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--text-fps", type=float, default=2.0)
    ap.add_argument("--strips", type=int, default=8)
    ap.add_argument("--no-text", action="store_true", help="skip the OCR (not on macOS, or no text in the video)")
    ap.add_argument("--no-motion", action="store_true", help="skip the full-frame-rate motion measurement")
    ap.add_argument("--bpm", type=float, help="the music's tempo, when known: timing is then checked against its beats")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    W, H, fps, dur = probe(a.video)
    DUR[0] = dur
    tmp = tempfile.mkdtemp(prefix="style-scan-")
    print("reference: %dx%d, %.2f fps, %.1f s" % (W, H, fps, dur))

    # pacing: the kit's teardown (cuts against the local median, bursts, quiet stretches, loudness)
    td = os.path.join(a.out, "teardown")
    subprocess.run([sys.executable, TEARDOWN, "--video", a.video, "--out", td, "--every", "4"], check=True, capture_output=True)
    rep = json.load(open(os.path.join(td, "report.json")))
    cuts = [c if isinstance(c, (int, float)) else c.get("t", c.get("time", 0)) for c in rep.get("cuts", [])]
    shots = [0.0] + sorted(float(c) for c in cuts) + [dur]
    lens = [b - a_ for a_, b in zip(shots, shots[1:]) if b - a_ > 0.05]
    pacing = {"cuts_per_min": rep.get("cuts_per_min"), "mean_shot_s": rep.get("mean_shot_s"),
              "median_shot_s": round(float(np.median(lens)), 2) if lens else dur,
              "shortest_shot_s": round(min(lens), 2) if lens else dur, "longest_shot_s": round(max(lens), 2) if lens else dur,
              "bursts_per_min": rep.get("bursts_per_min"), "quiet_stretches": len(rep.get("quiet", [])),
              "audio": rep.get("audio")}
    print("pacing: %s cuts/min, median shot %.2f s" % (pacing["cuts_per_min"], pacing["median_shot_s"]))

    pal, tone = palette(a.video, W, H)
    print("palette: " + " ".join("%s %d%%%s" % (p["hex"], p["share"] * 100, " (" + p["role"] + ")" if p["role"] else "") for p in pal))

    # one frame per shot
    mids = [(s0 + s1) / 2 for s0, s1 in zip(shots, shots[1:]) if s1 - s0 > 0.05]
    if len(mids) > 48:
        mids = [mids[int(i * len(mids) / 48)] for i in range(48)]
    ims = [grab(a.video, t, 320) for t in mids]
    starts = [max(s for s in shots if s <= t) for t in mids]
    sheet(ims, ["%s  %.1fs" % (mmss(s0), next(b for b in shots if b > s0) - s0) for s0 in starts], 6, os.path.join(a.out, "shots.jpg"))

    # the busiest moments that are not cuts: strips of 8 frames over ~0.7 s
    g = frames(a.video, 12, 64, 36, fmt="gray").astype("float32")
    diff = np.abs(np.diff(g, axis=0)).mean((1, 2))
    t_of = lambda i: (i + 1) / 12
    score = diff.copy()
    for c in cuts:
        i = int(float(c) * 12)
        score[max(0, i - 3): i + 3] = 0
    picks = []
    for i in np.argsort(-score):
        if score[i] <= 0 or len(picks) >= a.strips:
            break
        if all(abs(t_of(i) - p) > 2.5 for p in picks):
            picks.append(t_of(i))
    picks.sort()
    strip_imgs, strip_lbls = [], []
    for p in picks:
        for k in range(8):
            t = p - 0.35 + k * 0.1
            strip_imgs.append(grab(a.video, t, 240)); strip_lbls.append(mmss(max(0.0, t)))
    sheet(strip_imgs, strip_lbls, 8, os.path.join(a.out, "motion.jpg"))
    motion = {"busiest_moments": [round(p, 2) for p in picks],
              "mean_change": round(float(diff.mean()), 2), "share_of_time_moving": round(float((diff > 2.0).mean()), 2)}
    measured = None
    if not a.no_motion:                       # how things move, at the full frame rate: eases, lengths, timing
        sys.path.insert(0, HERE)
        import motion as mo
        measured = mo.analyse(a.video, bpm=a.bpm)
        mo.write(measured, a.out)
        motion["measured"] = measured["summary"]
        motion["staggers"] = measured["staggers"]; motion["cut_rhythm"] = measured.get("cut_rhythm")
        motion["beat"] = measured.get("beat")
        print("motion: %d moves, eases %s" % (measured["summary"]["moves"], measured["summary"]["families"]))

    # on-screen text
    text, cards = {"share_of_time": None}, []
    if not a.no_text and sys.platform == "darwin":
        text, cards, (sw, sh) = text_scan(a.video, W, H, a.text_fps, dur, tmp)
        big = sorted(cards, key=lambda c: -(c["box"]["y1"] - c["box"]["y0"]))[:12]
        crops, lbls = [], []
        for c in sorted(big, key=lambda c: c["first"]):
            b = c["box"]; im = grab(a.video, c["first"] + 0.25, sw)
            px, py = 0.25 * (b["x1"] - b["x0"]) + 20, 0.6 * (b["y1"] - b["y0"]) + 12
            crop = im.crop((max(0, b["x0"] - px), max(0, b["y0"] - py), min(sw, b["x1"] + px), min(sh, b["y1"] + py)))
            box = Image.new("RGB", (480, 160), (16, 16, 20))
            crop.thumbnail((480, 160)); box.paste(crop, ((480 - crop.width) // 2, (160 - crop.height) // 2))
            crops.append(box); lbls.append("%s  %s" % (mmss(c["first"]), c["key"][:40]))
        sheet(crops, lbls, 3, os.path.join(a.out, "text.jpg"))
        print("text: on screen %d%% of the time, %d cards, median height %.1f%% of the frame, %d%% upper case"
              % (text["share_of_time"] * 100, text["cards"], (text.get("height_share_median") or 0) * 100, (text.get("uppercase_share") or 0) * 100))

    # palette swatches
    sw_im = Image.new("RGB", (120 * len(pal), 150), (255, 255, 255)); d = ImageDraw.Draw(sw_im)
    for i, p in enumerate(pal):
        d.rectangle([i * 120, 0, i * 120 + 119, 110], fill=p["hex"])
        d.text((i * 120 + 6, 116), "%s %d%%" % (p["hex"], p["share"] * 100), fill=(20, 20, 20))
        if p["role"]:
            d.text((i * 120 + 6, 132), p["role"], fill=(90, 90, 90))
    sw_im.save(os.path.join(a.out, "palette.png"))

    scan = {"video": os.path.abspath(a.video), "size": [W, H], "fps": round(fps, 3), "duration": round(dur, 2),
            "pacing": pacing, "palette": pal, "tone": tone, "motion": motion, "text": text}
    json.dump(scan, open(os.path.join(a.out, "scan.json"), "w"), indent=1)
    md = ["# Style scan: %s" % os.path.basename(a.video), "",
          "- %dx%d, %.1f s. %s cuts a minute, median shot %.2f s (%.2f-%.2f s); %s bursts a minute."
          % (W, H, dur, pacing["cuts_per_min"], pacing["median_shot_s"], pacing["shortest_shot_s"], pacing["longest_shot_s"], pacing["bursts_per_min"]),
          "- Palette: " + ", ".join("%s %d%%%s" % (p["hex"], p["share"] * 100, " " + p["role"] if p["role"] else "") for p in pal) + ".",
          "- Tone: saturation %.2f, lightness %.2f; moving %d%% of the time." % (tone["mean_saturation"], tone["mean_lightness"], motion["share_of_time_moving"] * 100)]
    if text.get("titles", {}).get("reads"):
        tt = text["titles"]
        md.append("- Titles (designed type, %d reads): on screen %d%% of the time, height %.1f%% of the frame, %d%% upper case, "
                  "%g words a line; where: %s." % (tt["reads"], tt["share_of_time"] * 100, tt["height_share_median"] * 100,
                  tt["uppercase_share"] * 100, tt["words_median"], tt["grid"]))
    if text.get("cards"):
        md.append("- All text, UI labels included: on screen %d%% of the time, %s cards a minute, %.1f s each, %g words a card, height %.1f%% of the frame "
                  "(largest %.1f%%), %d%% upper case, %d lines grew word by word. Where (rows top/middle/bottom, columns "
                  "left/centre/right): %s." % (text["share_of_time"] * 100, text["cards_per_min"], text["card_seconds_median"],
                  text["words_per_card_median"], text["height_share_median"] * 100, text["height_share_p90"] * 100,
                  text["uppercase_share"] * 100, text["grows_word_by_word"], text["grid_top_mid_bottom_x_left_centre_right"]))
    if measured:
        md += [""] + [l for l in mo.words(measured).splitlines() if l.startswith("- ")]
    md += ["", "Sheets: shots.jpg (a frame a shot), motion.jpg (the busiest moments, 8 frames each), curves.png (the measured "
           "eases), text.jpg, palette.png. Every move: motion.json."]
    open(os.path.join(a.out, "SCAN.md"), "w").write("\n".join(md) + "\n")
    print("wrote %s/scan.json, SCAN.md, shots.jpg, motion.jpg%s%s, palette.png" % (
        a.out, ", motion.json, MOTION.md, curves.png" if measured else "", ", text.jpg" if text.get("cards") else ""))


if __name__ == "__main__":
    main()
