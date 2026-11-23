#!/usr/bin/env python3
"""storyboard.py: see a HyperFrames film before it renders. One snapshot run, three files to send in the chat:

  storyboard.jpg     every scene at the moment its text has landed, numbered, with its animation and the transition out
  transitions.jpg    every transition frame by frame: a row per scene change, from 0.4 s before to 0.6 s after
  transitions.mp4    those transitions playing at 15 fps, back to back, labelled (a few seconds, small)

  python3 storyboard.py --project W/public --scenes W/film.json --out W/review
  python3 storyboard.py --project W/public --scenes W/film.json --out W/review --only 3,4     just those scenes
  python3 storyboard.py ... --against "<an earlier render>.mp4"     each scene next to the same moment in that video
  python3 storyboard.py ... --what scenes                            the storyboard alone, in a few seconds

film.json is the film's plan (see the storyboard SKILL.md): per scene `id`, `label`, `anim`, `tr` (into the next
scene), and the timing the film was built with: `at`, `lands`, `end`, `tr_cover` (when the next scene is fully in).
Snapshots never call an online service (`--describe false`); the frames are deleted after the sheets are made.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
FONTS = os.path.join(ROOT, ".claude", "skills", "fast-cut", "assets", "fonts")
BEFORE, AFTER, FPS = 0.4, 0.6, 15
TR_NAMES = {"cut": "Cut", "pixel": "Pixel dissolve", "blur": "Blur swap", "wipe": "Wipe", "iris": "Iris", "whip": "Whip pan",
            "push": "Push", "zoom": "Zoom", "glitch": "Glitch"}


def clock(t):
    return "%d:%04.1f" % (int(t // 60), t % 60)


def font(size, bold=False):
    from PIL import ImageFont
    path = os.path.join(FONTS, "Poppins-SemiBold.ttf" if bold else "Poppins-Medium.ttf")
    return ImageFont.truetype(path, size) if os.path.exists(path) else ImageFont.load_default()


def plan_times(plan, only=None):
    """(heroes, transitions): heroes [(scene, t)], transitions [(scene, next, kind, cover, [t...])]. Times to 1 ms."""
    scenes = plan["scenes"]
    keep = set(str(x) for x in only) if only else None
    heroes, trs = [], []
    for i, sc in enumerate(scenes):
        sid = str(sc.get("id", i + 1))
        nxt = scenes[i + 1] if i + 1 < len(scenes) else None
        if keep and sid not in keep and not (nxt and str(nxt.get("id", i + 2)) in keep):
            continue
        if not keep or sid in keep:
            at, end = float(sc.get("at", 0)), float(sc.get("end", sc.get("at", 0) + 3))
            heroes.append((sc, round(float(sc["lands"]) if "lands" in sc else at + 0.6 * (end - at), 3)))
        kind = sc.get("tr", "cut")
        if nxt and kind != "cut":
            cover = float(sc.get("tr_cover", sc.get("end", nxt.get("at", 0))))
            n = int(round((BEFORE + AFTER) * FPS)) + 1
            trs.append((sc, nxt, kind, cover, [round(cover - BEFORE + k / FPS, 3) for k in range(n)]))
    return heroes, trs


def all_times(heroes, trs):
    return sorted(set([t for _, t in heroes] + [t for tr in trs for t in tr[4]]))


def snapshot(project, times, outdir):
    """ONE HyperFrames snapshot run for every time; returns the folder of PNGs."""
    npx = shutil.which("npx") or os.path.join(ROOT, ".tools", "node", "bin", "npx")
    if not os.path.exists(npx):
        sys.exit("npx not found: run the setup skill (bash setup.sh) first")
    cmd = [npx, "hyperframes", "snapshot", os.path.abspath(project), "--at", ",".join("%.3f" % t for t in times),
           "--no-end", "--describe", "false", "-o", outdir]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("snapshot failed:\n" + (r.stderr or r.stdout)[-2000:])
    return outdir


def frames_by_time(folder, wanted, tol=0.02):
    """Snapshot PNGs are named ...-at-<t>s.png: {wanted t: path}, matched to the nearest within tol."""
    found = []
    for root, _, files in os.walk(folder):
        for f in files:
            m = re.search(r"at-(\d+(?:\.\d+)?)s\.png$", f)
            if m:
                found.append((float(m.group(1)), os.path.join(root, f)))
    out = {}
    for t in wanted:
        best = min(found, key=lambda x: abs(x[0] - t), default=None)
        if best and abs(best[0] - t) <= tol:
            out[t] = best[1]
    return out


def thumb(path, w):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    return im.resize((w, int(round(w * im.height / im.width))), Image.LANCZOS)


def reference_frame(video, t, w):
    from PIL import Image
    import io
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.3f" % t, "-i", video, "-frames:v", "1", "-f", "image2pipe",
                          "-vcodec", "png", "-"], capture_output=True).stdout
    if not raw:
        return None
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    return im.resize((w, int(round(w * im.height / im.width))), Image.LANCZOS)


def storyboard_sheet(heroes, frames, out, against=None, cols=3, tw=560):
    from PIL import Image, ImageDraw
    if not heroes:
        return None
    sample = thumb(frames[heroes[0][1]], tw) if heroes[0][1] in frames else None
    th = sample.height if sample else int(tw * 9 / 16)
    pair = 2 if against else 1
    cw, ch, pad, cap = tw * pair + 8 * (pair - 1), th, 18, 64
    rows = (len(heroes) + cols - 1) // cols
    W, H = cols * cw + (cols + 1) * pad, rows * (ch + cap) + (rows + 1) * pad
    sheet = Image.new("RGB", (W, H), (246, 246, 248)); d = ImageDraw.Draw(sheet)
    f1, f2 = font(19, True), font(15)
    for k, (sc, t) in enumerate(heroes):
        x = pad + (k % cols) * (cw + pad); y = pad + (k // cols) * (ch + cap + pad)
        if t in frames:
            sheet.paste(thumb(frames[t], tw), (x, y))
        else:
            d.rectangle([x, y, x + tw, y + th], outline=(200, 60, 60), width=3); d.text((x + 12, y + 12), "no frame", font=f2, fill=(200, 60, 60))
        if against:
            ref = reference_frame(against, t, tw)
            if ref:
                sheet.paste(ref, (x + tw + 8, y))
            d.text((x + 8, y + 6), "new", font=f2, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
            d.text((x + tw + 16, y + 6), "before", font=f2, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
        title = "%s  %s" % (sc.get("id", k + 1), sc.get("label", ""))
        while d.textlength(title, font=f1) > cw and len(title) > 8:
            title = title[:-2].rstrip() + "…" if not title.endswith("…") else title[:-3] + "…"
        d.text((x, y + ch + 8), title, font=f1, fill=(20, 20, 30))
        tr = sc.get("tr", "cut")
        d.text((x, y + ch + 36), "%s   %s   then %s" % (clock(t), sc.get("anim", ""), TR_NAMES.get(tr, tr).lower()), font=f2, fill=(90, 90, 105))
    sheet.save(out, quality=86)
    return out


PICKS = (0, 3, 6, 8, 11, 15)          # of the 16 frames: -0.4, -0.2, the cover, +0.13, +0.33, +0.6 s


def transitions_sheet(trs, frames, out, tw=300):
    from PIL import Image, ImageDraw
    if not trs:
        return None
    first = next((frames[t] for tr in trs for t in tr[4] if t in frames), None)
    th = thumb(first, tw).height if first else int(tw * 9 / 16)
    lw, pad, cap = 230, 14, 26
    picks = [p for p in PICKS if p < len(trs[0][4])]
    W, H = lw + len(picks) * (tw + pad) + pad, len(trs) * (th + cap + pad) + pad
    sheet = Image.new("RGB", (W, H), (246, 246, 248)); d = ImageDraw.Draw(sheet)
    f1, f2, f3 = font(20, True), font(15), font(13)
    for r, (sc, nxt, kind, cover, ts) in enumerate(trs):
        y = pad + r * (th + cap + pad)
        d.text((pad, y + 8), "%s > %s" % (sc.get("id", r + 1), nxt.get("id", r + 2)), font=f1, fill=(20, 20, 30))
        d.text((pad, y + 40), TR_NAMES.get(kind, kind), font=f2, fill=(60, 60, 75))
        d.text((pad, y + 64), "covered at " + clock(cover), font=f3, fill=(110, 110, 125))
        for c, p in enumerate(picks):
            x = lw + c * (tw + pad); t = ts[p]
            if t in frames:
                sheet.paste(thumb(frames[t], tw), (x, y))
            off = t - cover
            d.text((x, y + th + 4), "cover" if abs(off) < 1e-3 else "%+.2f s" % off, font=f3, fill=(90, 90, 105))
    sheet.save(out, quality=86)
    return out


def transitions_clip(trs, frames, out, width=960):
    """Every transition at 15 fps with its label, a short hold after each: plays in the chat."""
    from PIL import Image, ImageDraw
    if not trs:
        return None
    first = next((frames[t] for tr in trs for t in tr[4] if t in frames), None)
    if not first:
        return None
    with Image.open(first) as im0:
        h = int(round(width * im0.height / im0.width / 2)) * 2
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (width, h), "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-crf", "23", "-preset", "medium", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out],
                         stdin=subprocess.PIPE)
    f = font(22, True)
    for sc, nxt, kind, cover, ts in trs:
        label = "%s > %s   %s" % (sc.get("id", ""), nxt.get("id", ""), TR_NAMES.get(kind, kind))
        last = None
        for t in ts:
            if t not in frames:
                continue
            im = Image.open(frames[t]).convert("RGB").resize((width, h), Image.LANCZOS)
            d = ImageDraw.Draw(im); d.rounded_rectangle([14, 14, 30 + d.textlength(label, font=f), 56], 10, fill=(20, 20, 30))
            d.text((22, 20), label, font=f, fill=(255, 255, 255))
            last = im.tobytes(); p.stdin.write(last)
        for _ in range(int(FPS * 0.4)):
            if last:
                p.stdin.write(last)
    p.stdin.close(); p.wait()
    return out if p.returncode == 0 else None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--project", required=True, help="the HyperFrames project folder (W/public)")
    ap.add_argument("--scenes", required=True, help="the film's film.json, with its timing")
    ap.add_argument("--out", required=True, help="where the sheets go (W/review)")
    ap.add_argument("--only", help="scene ids, comma separated: just these scenes and the transitions into and out of them")
    ap.add_argument("--against", help="an earlier render: each storyboard frame next to the same moment in it")
    ap.add_argument("--what", choices=["all", "scenes", "transitions"], default="all",
                    help="scenes = the storyboard alone (about 2 s a frame, so a quick first look); transitions = the other two")
    a = ap.parse_args()
    plan = json.load(open(a.scenes))
    heroes, trs = plan_times(plan, a.only.split(",") if a.only else None)
    if a.what == "scenes":
        trs = []
    elif a.what == "transitions":
        heroes = []
    times = all_times(heroes, trs)
    if not times:
        sys.exit("no scenes with timing in %s (each scene needs at/lands/end; see SKILL.md)" % a.scenes)
    os.makedirs(a.out, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="storyboard-")
    try:
        frames = frames_by_time(snapshot(a.project, times, tmp), times)
        missing = [t for t in times if t not in frames]
        made = [storyboard_sheet(heroes, frames, os.path.join(a.out, "storyboard.jpg"), a.against),
                transitions_sheet(trs, frames, os.path.join(a.out, "transitions.jpg")),
                transitions_clip(trs, frames, os.path.join(a.out, "transitions.mp4"))]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for m in made:
        if m:
            print(m)
    print("%d frames from one snapshot run; %d scenes, %d transitions%s" % (len(frames), len(heroes), len(trs),
          "; MISSING %d (see the red boxes)" % len(missing) if missing else ""))


if __name__ == "__main__":
    main()
