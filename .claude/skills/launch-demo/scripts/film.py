#!/usr/bin/env python3
"""film.py: a 16:9 launch film built from the scene plan. Each scene's line plays with its text animation (any of the
library's), the transitions picked in the planner land on the music's beats, the background is the look's halftone
(light or dark) or plain, and logo and lockup cards carry the name and, when the look has one, its icon.

  python3 film.py --scenes W/film.json --out W/public

Writes W/public/index.html with everything it needs next to it (GSAP, text-fx.js, fonts, media, the background loop),
and writes each scene's timing back into film.json (at, lands, end, tr_cover) for the storyboard. The plan fields
(text, parts, anim, tr, background) are never changed here: they come from the scene planner.

film.json, besides the planner's fields: "look", "size" ("1920x1080"), "bpm" and "offset" (beats.py: the music's tempo
and its first beat in film time), "duration", "hit" (the music's final note, for the lockup), "fade" (seconds), "name"
(the product's name for logo and lockup cards), "custom" ({"css", "js", "media": [...]}, paths next to film.json).
Per scene: "beats" (its length on the music's grid; or "dur" in seconds), "kind" (text | logo | lockup | custom),
"lines" (more lines after the first, each blurring into the next; "line_beats" places them), "size" (font px at 1920),
"name", "logo" (an image instead of the name), "icon" (false hides the look's icon; a path uses another), "html" (custom).
"""
import argparse, html, json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
SKILLS = os.path.dirname(SKILL)
ROOT = os.path.dirname(os.path.dirname(SKILLS))
STYLES = os.path.join(SKILLS, "youtube-edit", "styles")
sys.path.insert(0, os.path.join(SKILLS, "text-animations", "scripts"))
import tfx  # noqa: E402  (the library catalogue and the look's colours, shared with the planner)

FPS = 30
KINDS = ("text", "logo", "lockup", "custom")
BACKGROUNDS = ("halftone-light", "halftone-dark", "plain")
CARD_GROUPS = ("Cards and cursors", "Video and UI")


def snap(t):
    return round(round(t * FPS) / FPS, 3)


def timing(plan):
    """Each scene's at / end on the beat grid (or by seconds), lands just before it leaves, lines spread inside it."""
    scenes = plan["scenes"]
    spb = 60.0 / plan["bpm"] if plan.get("bpm") else None
    off = float(plan.get("offset", 0))
    beat, at = 0.0, 0.0
    for i, sc in enumerate(scenes):
        if spb and "beats" in sc:
            beat += float(sc["beats"]); end = off + beat * spb
        elif "dur" in sc:
            end = at + float(sc["dur"])
            if spb:
                beat = (end - off) / spb
        else:
            raise ValueError("scene %s needs \"beats\" (with a bpm) or \"dur\"" % sc.get("id", i + 1))
        if i == len(scenes) - 1 and plan.get("duration"):
            end = float(plan["duration"])
        if end <= at + 0.5:
            raise ValueError("scene %s is too short (%.2f s)" % (sc.get("id", i + 1), end - at))
        sc["at"], sc["end"] = snap(at), snap(end)
        last = i == len(scenes) - 1
        sc["lands"] = snap(max(at + 0.5, end - 0.6 - (float(plan.get("fade", 0)) + 0.4 if last and plan.get("fade") else 0)))
        if i < len(scenes) - 1:
            sc["tr_cover"] = snap(end)
        else:
            sc.pop("tr_cover", None)
        lines = sc.get("lines") or []
        if lines:
            if sc.get("line_beats") and spb:
                sc["line_at"] = [snap(at + float(b) * spb) for b in sc["line_beats"]]
            else:
                sc["line_at"] = [snap(at + (n + 1) * (end - at) / (len(lines) + 1)) for n in range(len(lines))]
        else:
            sc.pop("line_at", None)
        at = end
    return snap(at)


def sizes(W, H):
    k = W / 1920.0 if W >= H else W / 1080.0 * 0.8
    return k, {"head": round(62 * k), "line": round(84 * k), "card": round(100 * k), "mark": round(150 * k), "mark_line": round(56 * k)}


def box(x, y, w, h):
    return "left:%dpx;top:%dpx;width:%dpx;height:%dpx" % (x, y, w, h)


def look_json(look):
    p = os.path.join(STYLES, look + ".json")
    if not os.path.exists(p):
        raise ValueError("no look named %r in youtube-edit/styles" % look)
    return json.load(open(p))


def scene_markup(i, sc, W, H, sz, card, icon, logo):
    m, kind = round(W * 0.083), sc.get("kind", "text")
    first = ' style="opacity:1"' if i == 0 else ""
    head = box(m, round(H * 0.065), W - 2 * m, round(H * 0.14))
    cardbox = box(m, round(H * 0.22), W - 2 * m, H - round(H * 0.22) - round(H * 0.04))
    line = box(m, round(H * 0.33), W - 2 * m, round(H * 0.34))
    out = ['  <div class="layer" id="L%d"%s>' % (i, first)]
    if kind in ("logo", "lockup"):
        name = html.escape(sc.get("name", ""))
        inner = ('<img class="icon" src="%s" alt="">' % icon if icon else "") + \
                ('<img class="logo" src="%s" alt="%s">' % (logo, name) if logo else '<span class="word">%s</span>' % name)
        out.append('    <div class="mark" id="K%d" style="top:%dpx;font-size:%dpx">%s</div>' % (i, round(H * 0.27), sz["mark"], inner))
        out.append('    <div class="st" id="S%d" style="%s"></div>' % (i, box(m, round(H * 0.53), W - 2 * m, round(H * 0.16))))
    elif kind == "custom":
        out.append('    <div class="st" id="H%d" style="%s"></div>' % (i, head))
        out.append(sc.get("_html", ""))
    else:
        if card:
            out.append('    <div class="st" id="H%d" style="%s"></div>' % (i, head))
        out.append('    <div class="st" id="S%d" style="%s"></div>' % (i, cardbox if card else line))
        for n in range(len(sc.get("lines") or [])):
            out.append('    <div class="st" id="S%d_%d" style="%s"></div>' % (i, n, line))
    out.append("  </div>")
    return "\n".join(out)


def background(plan, look, W, H, duration, out):
    """The look's halftone as a seamless 12 s loop (made once, kept in videos/_shared/backgrounds/), looped to the film."""
    bgname = plan.get("background", "halftone-light")
    if bgname == "plain":
        return ""
    mode = "dark" if bgname == "halftone-dark" else "light"
    cache = os.path.join(ROOT, "videos", "_shared", "backgrounds", "%s-halftone%s-%dx%d.mp4" % (look, "-dark" if mode == "dark" else "", W, H))
    if not os.path.exists(cache):
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        print("making the %s halftone background once (a few minutes at full size)..." % mode)
        subprocess.run([sys.executable, os.path.join(SKILLS, "text-animations", "scripts", "halftone.py"), "--look", look, "--mode", mode,
                        "--size", "%dx%d" % (W, H), "--dur", "12", "--out", cache], check=True)
    dst = os.path.join(out, "media", "bg.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-stream_loop", "-1", "-i", cache, "-t", "%.3f" % duration, "-c", "copy",
                    "-movflags", "+faststart", dst], check=True)
    return '  <video id="bg" src="media/bg.mp4" data-start="0" data-duration="%s" muted playsinline></video>\n  <div id="veil"></div>' % duration


def build(scenes_path, out):
    plan = json.load(open(scenes_path))
    base = os.path.dirname(os.path.abspath(scenes_path))
    look = plan.get("look", "brand")
    lj = look_json(look)
    W, H = (int(v) for v in plan.get("size", "1920x1080").lower().split("x"))
    bgname = plan.get("background", "halftone-light")
    if bgname not in BACKGROUNDS:
        raise ValueError("background must be one of %s" % ", ".join(BACKGROUNDS))
    pal = tfx.palettes(look)[bgname]
    cat = {a["id"]: a for a in tfx.catalogue()["list"]}
    trs = set(t["id"] for t in tfx.catalogue()["tr"])
    for i, sc in enumerate(plan["scenes"]):
        sc.setdefault("id", i + 1)
        kind = sc.get("kind", "text")
        if kind not in KINDS:
            raise ValueError("scene %s: kind must be one of %s" % (sc["id"], ", ".join(KINDS)))
        if sc.get("anim") and sc["anim"] not in cat:
            raise ValueError("scene %s: no text animation %r" % (sc["id"], sc["anim"]))
        if sc.get("tr", "cut") not in trs:
            raise ValueError("scene %s: no transition %r" % (sc["id"], sc["tr"]))
    duration = timing(plan)
    json.dump(plan, open(scenes_path, "w"), indent=1, ensure_ascii=False)      # the timing, for the storyboard

    for d in ("vendor", "fonts", "media"):
        os.makedirs(os.path.join(out, d), exist_ok=True)
    k, sz = sizes(W, H)
    icon_src = None
    if isinstance(lj.get("icon"), dict) and lj["icon"].get("file"):
        icon_src = os.path.join(STYLES, lj["icon"]["file"])
    layers, page_scenes = [], []
    for i, sc in enumerate(plan["scenes"]):
        kind = sc.get("kind", "text")
        a_ = cat.get(sc.get("anim", "accent-words"), {})
        multi = "|" in a_.get("sample", "")                               # reads the scene's parts
        card = a_.get("category") in CARD_GROUPS                          # a UI piece: the line goes above it as a headline
        icon = logo = None
        if kind in ("logo", "lockup"):
            src = sc["icon"] if isinstance(sc.get("icon"), str) else (icon_src if sc.get("icon", True) else None)
            if src:
                src = src if os.path.isabs(src) else (os.path.join(base, src) if not src.startswith(STYLES) else src)
                if os.path.exists(src):
                    icon = "media/icon-%d%s" % (i, os.path.splitext(src)[1]); shutil.copy2(src, os.path.join(out, icon))
            if sc.get("logo"):
                src = os.path.join(base, sc["logo"]); logo = "media/logo-%d%s" % (i, os.path.splitext(src)[1])
                shutil.copy2(src, os.path.join(out, logo))
            sc.setdefault("name", plan.get("name", ""))
        if kind == "custom":
            sc["_html"] = open(os.path.join(base, sc["html"])).read() if sc.get("html") else ""
        layers.append(scene_markup(i, sc, W, H, sz, card, icon, logo))
        ps = {key: sc[key] for key in ("id", "kind", "text", "parts", "anim", "tr", "at", "end", "lands", "lines", "line_at", "line_anim",
                                       "head_anim", "name") if key in sc}
        if sc.get("size"):
            ps["size"] = round(sc["size"] * k)
        ps["multi"], ps["card"] = multi, card
        page_scenes.append(ps)
        sc.pop("_html", None)

    cu = plan.get("custom") or {}
    read = lambda key: open(os.path.join(base, cu[key])).read() if cu.get(key) else ""
    for m in cu.get("media", []):
        shutil.copy2(os.path.join(base, m), os.path.join(out, "media", os.path.basename(m)))

    fam = (lj.get("font") or {}).get("family", "Poppins")
    faces = []
    for w, rel in sorted(((lj.get("font") or {}).get("files") or {}).items()):
        src = os.path.join(STYLES, rel)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(out, "fonts", os.path.basename(rel)))
            faces.append('  @font-face { font-family: "%s"; src: url("fonts/%s") format("woff2"); font-weight: %s; font-display: block; }'
                         % (fam, os.path.basename(rel), w))
    if bgname == "halftone-dark":
        veil = ("rgba(%d,%d,%d,.62)" % tuple(int(pal["bg"][j:j + 2], 16) for j in (1, 3, 5)), "rgba(%d,%d,%d,.35)" % tuple(int(pal["bg"][j:j + 2], 16) for j in (1, 3, 5)))
    else:
        veil = ("rgba(255,255,255,.82)", "rgba(255,255,255,.55)")
    page_plan = {"W": W, "H": H, "boxW": W - 2 * round(W * 0.083), "duration": duration, "palette": pal, "pixel2": pal["accent3"] if bgname != "halftone-dark" else pal["accent2"],
                 "sizes": sz, "hit": plan.get("hit"), "fade": plan.get("fade", 0), "scenes": page_scenes}
    page = open(os.path.join(SKILL, "template", "film.html")).read()
    rep = {"/*TITLE*/": html.escape(plan.get("title", plan.get("name") or "Film")), "/*FONTS*/": "\n".join(faces), "/*W*/": str(W), "/*H*/": str(H),
           "/*BG*/": pal["bg"], "/*INK*/": pal["ink"], "/*FAMILY*/": '"%s"' % fam, "/*VEIL*/": veil[0], "/*VEIL2*/": veil[1],
           "/*DURATION*/": str(duration), "/*CUSTOM-CSS*/": read("css"), "/*CUSTOM-JS*/": read("js"),
           "<!--BG-->": background(plan, look, W, H, duration, out), "<!--SCENES-->": "\n".join(layers),
           "/*PLAN*/{}/*END*/": json.dumps(page_plan, ensure_ascii=False)}
    for a, b in rep.items():
        page = page.replace(a, b)
    open(os.path.join(out, "index.html"), "w").write(page)
    for src, dst in ((os.path.join(SKILLS, "youtube-edit", "assets", "vendor", "gsap.min.js"), "vendor/gsap.min.js"),
                     (os.path.join(SKILLS, "text-animations", "text-fx.js"), "vendor/text-fx.js")):
        shutil.copy2(src, os.path.join(out, dst))
    hf = os.path.join(out, "hyperframes.json")
    if not os.path.exists(hf):
        json.dump({"$schema": "https://hyperframes.heygen.com/schema/hyperframes.json", "media": {"autoProxy": True}}, open(hf, "w"), indent=2)
    print("wrote %s: %d scenes, %.2f s, %s, %s" % (os.path.join(out, "index.html"), len(plan["scenes"]), duration, look, bgname))
    return page


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    try:
        build(a.scenes, a.out)
    except ValueError as e:
        sys.exit("nothing built: %s" % e)


if __name__ == "__main__":
    main()
