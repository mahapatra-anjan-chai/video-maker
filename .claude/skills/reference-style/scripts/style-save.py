#!/usr/bin/env python3
"""Turn a style into something the next video can pick: a look for the look question, and, after a delivery, a skill.

  python3 style-save.py look  --style W/refs/style.json
      writes .claude/skills/youtube-edit/styles/ref-<slug>.json (compose.py's look format), so "ref-<slug>" can be the
      storyboard's "style" and is offered at the look question

  python3 style-save.py skill --style W/refs/style.json --preview "<delivered mp4>" [--skills-dir .claude/skills]
      after the video is delivered, with the style.json as tuned on that video: writes
      .claude/skills/style-<slug>/ with SKILL.md (triggers on "make it in the <name> style"), style.json, card.png,
      preview.jpg (frames of OUR video, never the reference) and components/ (every file in style.json
      "custom_files": what was built for this style, so the next video starts from it)

Saved styles and ref-* looks are gitignored: they come from someone else's video. Publish one only when the creator
asks, after checking it names no brand and copies nothing but the grammar.
"""
import argparse, json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(HERE))


def write_look(s, skills):
    look = dict(s.get("look") or {})
    if not look.get("colors"):
        sys.exit("style.json has no look.colors")
    look.setdefault("name", s.get("name", s["slug"]))
    look.setdefault("ready", True)
    look.setdefault("description", s.get("summary", ""))
    path = os.path.join(skills, "youtube-edit", "styles", "ref-%s.json" % s["slug"])
    json.dump(look, open(path, "w"), indent=2, ensure_ascii=False)
    return path


def preview(video, out, n=6):
    from PIL import Image
    import io
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                             capture_output=True, text=True, check=True).stdout)
    ims = []
    for i in range(n):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.2f" % (d * (i + 0.5) / n), "-i", video, "-frames:v", "1",
                              "-vf", "scale=-2:360", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
        ims.append(Image.open(io.BytesIO(raw)).convert("RGB"))
    w = sum(i.width for i in ims) + 8 * (n - 1)
    strip = Image.new("RGB", (w, 360), (16, 16, 20))
    x = 0
    for im in ims:
        strip.paste(im, (x, 0)); x += im.width + 8
    strip.save(out, quality=86)


def skill_md(s):
    tech = s.get("techniques", []) + s.get("transitions", [])
    rows = []
    for t in tech:
        m = t.get("maps_to", {})
        k = m.get("kind")
        how = {"text-animation": "text animation `%s`" % m.get("id"),
               "fast-cut": "fast-cut `%s` %s" % (m.get("feature"), json.dumps(m.get("params", {}))),
               "registry": "HyperFrames block `%s` (`npx hyperframes add %s`)" % (m.get("item"), m.get("item")),
               "custom": "built for this style: %s" % (m.get("file") or m.get("plan", ""))}.get(k, str(m))
        rows.append("| %s | %s |" % (t.get("name", ""), how))
    p = s.get("pacing", {})
    lines = [
        "---",
        "name: style-%s" % s["slug"],
        "description: Make a video in the %s style. %s Use when the creator asks for the %s style, picks ref-%s at the look question, or wants the next video to look like %s." % (
            s.get("name"), s.get("summary", "").split(". ")[0].rstrip(".") + ".", s.get("name"), s["slug"],
            "the last one in this style"),
        "---",
        "",
        "# %s" % s.get("name"),
        "",
        s.get("summary", ""),
        "",
        "Saved from a delivered video by the `reference-style` skill. `style.json` holds every value; `card.png` shows it;",
        "`preview.jpg` is our video in this style. The look question offers it as `ref-%s` (compose.py), and" % s["slug"],
        "`text_animations` goes into `brief.json`.",
        "",
        "## Use it",
        "",
        "- **Look:** storyboard `\"style\": \"ref-%s\"` (palette, font, rules in `youtube-edit/styles/ref-%s.json`;" % (s["slug"], s["slug"]),
        "  `python3 .claude/skills/reference-style/scripts/style-save.py look --style .claude/skills/style-%s/style.json`" % s["slug"],
        "  rewrites it if it is missing).",
        "- **Pacing:** median shot %s s, %s cuts a minute. %s" % (p.get("median_shot_s"), p.get("cuts_per_min"), p.get("rhythm", "")),
        "- **Text animations:** %s." % ", ".join(s.get("text_animations", []) or ["none"]),
        "- **Texture:** %s" % s.get("texture", "none"),
        "- **Sound:** %s" % "; ".join("%s: %s" % kv for kv in s.get("sound", {}).items()),
        "",
        "| Technique | How we make it |",
        "|---|---|",
    ] + rows + [
        "",
        "Files built for this style are in `components/`; start from them, do not rebuild.",
        "",
        "## Do",
        "",
    ] + ["- %s" % d for d in s.get("do", [])] + [
        "",
        "## Never copy",
        "",
    ] + ["- %s" % d for d in s.get("dont_copy", [])] + [""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["look", "skill"])
    ap.add_argument("--style", required=True)
    ap.add_argument("--preview", help="the delivered video in this style")
    ap.add_argument("--skills-dir", default=SKILLS)
    a = ap.parse_args()
    s = json.load(open(a.style))
    if not s.get("slug"):
        sys.exit("style.json needs a slug (lower-case, hyphens, no brand names)")
    look = write_look(s, a.skills_dir)
    print("look ->", look)
    if a.cmd == "look":
        return
    if not a.preview:
        sys.exit("skill needs --preview: the delivered video in this style")
    d = os.path.join(a.skills_dir, "style-%s" % s["slug"])
    os.makedirs(os.path.join(d, "components"), exist_ok=True)
    base = os.path.dirname(os.path.abspath(a.style))
    kept = []
    for f in s.get("custom_files", []):
        src = f if os.path.isabs(f) else os.path.join(base, f)
        if not os.path.exists(src):
            src = os.path.join(os.getcwd(), f)
        if os.path.exists(src):
            dst = os.path.join(d, "components", os.path.basename(src))
            (shutil.copytree if os.path.isdir(src) else shutil.copy2)(src, dst)
            kept.append("components/" + os.path.basename(src))
        else:
            print("  missing custom file, skipped:", f)
    s2 = dict(s, custom_files=kept)
    json.dump(s2, open(os.path.join(d, "style.json"), "w"), indent=2, ensure_ascii=False)
    subprocess.run([sys.executable, os.path.join(HERE, "style-card.py"), "--style", os.path.join(d, "style.json"),
                    "--out", os.path.join(d, "card.png")], check=True, capture_output=True)
    preview(a.preview, os.path.join(d, "preview.jpg"))
    open(os.path.join(d, "SKILL.md"), "w").write(skill_md(s2))
    print("skill -> %s (SKILL.md, style.json, card.png, preview.jpg, %d components)" % (d, len(kept)))


if __name__ == "__main__":
    main()
