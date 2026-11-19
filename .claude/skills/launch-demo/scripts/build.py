#!/usr/bin/env python3
"""Build a launch-demo HyperFrames page from a demo.json: the template, the config, the caption words and the media.

  python3 build.py --config W/demo.json [--words W/work/words.json] --out W/public

Writes W/public/index.html and copies what the page needs next to it (GSAP, text-fx.js, the iPhone frame CSS and its
MIT licence, Poppins, hyperframes.json). Media paths in demo.json are relative to W/public (put clips in public/img/).
The <video> tags are written into the page here, not by its script: HyperFrames reads media and the length before
scripts run. Optional "custom": {"html", "css", "js"} files (relative to demo.json) add the product's own scenes.
"""
import argparse, html, json, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
SKILLS = os.path.dirname(SKILL)


def vid(v, extra_style=""):
    a = ['id="%s"' % v["id"], 'src="%s"' % html.escape(v["src"]), 'data-start="%s"' % v["start"], 'data-duration="%s"' % v["dur"]]
    if v.get("media"):
        a.append('data-media-start="%s"' % v["media"])
    style = extra_style + ("object-position:%s;" % v["pos"] if v.get("pos") else "")
    if style:
        a.append('style="%s"' % style)
    return "<video %s muted playsinline></video>" % " ".join(a)


def build(config, words, out):
    c = json.load(open(config))
    base = os.path.dirname(os.path.abspath(config))
    page = open(os.path.join(SKILL, "template", "index.html")).read()
    o, h, f = c.get("opening") or {}, c.get("hook"), c.get("feature") or {}
    page = page.replace("<!--OPEN-VIDEOS-->", "".join(vid(dict(v, id="ov%d" % i)) for i, v in enumerate(o.get("clips", []))))
    page = page.replace("<!--HOOK-VIDEO-->", vid(dict(h, id="vHook"), "position:absolute;left:0;top:0;width:1080px;height:1080px;") if h else "")
    media = ('<img src="%s" alt="">' % html.escape(f["poster"]) if f.get("poster") else "") + \
        "".join(vid(dict(v, id="fv%d" % i)) for i, v in enumerate(f.get("clips", [])))
    page = page.replace("<!--FEATURE-MEDIA-->", media)
    cu = c.get("custom") or {}
    read = lambda k: open(os.path.join(base, cu[k])).read() if cu.get(k) else ""
    page = page.replace("<!--CUSTOM-HTML-->", read("html")).replace("/*CUSTOM-CSS*/", read("css")).replace("/*CUSTOM-JS*/", read("js"))
    page = page.replace("/*DURATION*/", str(c["duration"]))
    page = page.replace("/*CONFIG*/{}/*END*/", json.dumps(c, ensure_ascii=False))
    page = page.replace("/*WORDS*/[]/*END*/", json.dumps(json.load(open(words)) if words else []))
    os.makedirs(os.path.join(out, "vendor"), exist_ok=True)
    os.makedirs(os.path.join(out, "fonts"), exist_ok=True)
    open(os.path.join(out, "index.html"), "w").write(page)
    copies = [(os.path.join(SKILLS, "youtube-edit", "assets", "vendor", "gsap.min.js"), "vendor/gsap.min.js"),
              (os.path.join(SKILLS, "text-animations", "text-fx.js"), "vendor/text-fx.js"),
              (os.path.join(SKILL, "vendor", "devices.css"), "vendor/devices.css"),
              (os.path.join(SKILL, "vendor", "devices-LICENSE.txt"), "vendor/devices-LICENSE.txt")]
    fonts = os.path.join(SKILLS, "youtube-edit", "styles", "brand", "fonts")
    copies += [(os.path.join(fonts, n), "fonts/" + n) for n in os.listdir(fonts) if n.endswith(".woff2")]
    missing = []
    for src, dst in copies:
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(out, dst))
        else:
            missing.append(src)
    hf = os.path.join(out, "hyperframes.json")
    if not os.path.exists(hf):
        json.dump({"$schema": "https://hyperframes.heygen.com/schema/hyperframes.json", "media": {"autoProxy": True}}, open(hf, "w"), indent=2)
    absent = [p for p in [v["src"] for v in o.get("clips", [])] + ([h["src"]] if h else []) +
              [v["src"] for v in f.get("clips", [])] + ([f["poster"]] if f.get("poster") else []) if not os.path.exists(os.path.join(out, p))]
    print("wrote %s (%s s)" % (os.path.join(out, "index.html"), c["duration"]))
    for m in missing:
        print("  missing (run setup.sh): %s" % m)
    for m in absent:
        print("  media not in public/ yet: %s" % m)
    return page


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--words")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    build(a.config, a.words, a.out)
