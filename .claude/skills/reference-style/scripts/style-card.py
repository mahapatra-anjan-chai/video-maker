#!/usr/bin/env python3
"""One image of a style, to confirm it with the creator before it is applied: palette and roles, the type set in the
mapped font, pacing, every technique with what it maps to, and what is not copied.

  python3 style-card.py --style videos/<p>/refs/style.json --out videos/<p>/refs/card.png

Never puts a frame of the reference on the card (the card may end up in a saved, shareable skill); send the scan's
sheets next to it when the creator should compare.
"""
import argparse, json, os, textwrap

SKILLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_BOLD = os.path.join(SKILLS, "fast-cut", "assets", "fonts", "Poppins-Bold.ttf")
DEFAULT_REG = os.path.join(SKILLS, "fast-cut", "assets", "fonts", "Poppins-Regular.ttf")
KIND = {"text-animation": (91, 52, 245), "fast-cut": (14, 138, 98), "registry": (2, 132, 199), "custom": (217, 119, 6)}


def font(path, size):
    from PIL import ImageFont
    for p in (path, DEFAULT_REG):
        if p and os.path.exists(p) and not p.endswith((".woff", ".woff2")):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def lum(hexc):
    r, g, b = (int(hexc[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def main():
    from PIL import Image, ImageDraw
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    s = json.load(open(a.style))
    look = s.get("look", {})
    head = s.get("type", {}).get("headline", {})
    hfile = os.path.join(SKILLS, head["font_file"]) if head.get("font_file") else DEFAULT_BOLD
    W, H = 1600, 1000
    im = Image.new("RGB", (W, H), (248, 247, 244))
    d = ImageDraw.Draw(im)
    f_t, f_h, f_b, f_s = font(DEFAULT_BOLD, 46), font(DEFAULT_BOLD, 24), font(DEFAULT_REG, 20), font(DEFAULT_REG, 16)
    d.text((48, 36), s.get("name", "Style"), font=f_t, fill=(20, 20, 24))
    y = 100
    for line in textwrap.wrap(s.get("summary", ""), 120)[:3]:
        d.text((48, y), line, font=f_b, fill=(70, 70, 80)); y += 28
    # palette
    y = 200
    d.text((48, y), "Palette", font=f_h, fill=(20, 20, 24)); y += 38
    colors = look.get("colors", {})
    roles = look.get("roles", {})
    for i, (name, hx) in enumerate(list(colors.items())[:6]):
        x = 48 + i * 122
        d.rounded_rectangle([x, y, x + 110, y + 90], radius=12, fill=hx, outline=(210, 210, 210))
        d.text((x + 8, y + 64), hx, font=f_s, fill=(255, 255, 255) if lum(hx) < 140 else (20, 20, 24))
        d.text((x, y + 98), name[:13], font=f_s, fill=(40, 40, 48))
        for k, line in enumerate(textwrap.wrap(roles.get(name, ""), 12)[:3]):
            d.text((x, y + 118 + k * 18), line, font=f_s, fill=(110, 110, 120))
    # type
    y = 420
    d.text((48, y), "Type", font=f_h, fill=(20, 20, 24))
    sample = "Headline in this style" if head.get("case", "sentence") != "upper" else "HEADLINE IN THIS STYLE"
    d.text((48, y + 40), sample, font=font(hfile, 56), fill=(20, 20, 24))
    lab = s.get("type", {}).get("label", {})
    lfile = os.path.join(SKILLS, lab["font_file"]) if lab.get("font_file") else DEFAULT_REG
    d.text((48, y + 120), "A LABEL" if lab.get("case") == "upper" else "A label", font=font(lfile, 28), fill=(80, 80, 90))
    fam = look.get("font", {}).get("family", "")
    d.text((48, y + 166), "%s  ·  headline %s, %s, %.0f%% of the frame high, %s" % (
        fam, head.get("weight", ""), head.get("case", ""), 100 * float(head.get("size_share", 0) or 0), head.get("position", "")),
        font=f_s, fill=(110, 110, 120))
    # pacing
    p = s.get("pacing", {})
    y = 640
    d.text((48, y), "Pacing", font=f_h, fill=(20, 20, 24))
    d.text((48, y + 36), "median shot %s s  ·  %s cuts a minute" % (p.get("median_shot_s", "?"), p.get("cuts_per_min", "?")), font=f_b, fill=(40, 40, 48))
    for k, line in enumerate(textwrap.wrap(p.get("rhythm", ""), 64)[:3]):
        d.text((48, y + 66 + k * 24), line, font=f_s, fill=(110, 110, 120))
    tx = s.get("text_animations", [])
    if tx:
        d.text((48, y + 150), "Text animations: " + ", ".join(tx), font=f_b, fill=(91, 52, 245))
    # techniques
    x0, y = 860, 200
    d.text((x0, y), "Techniques and what makes them here", font=f_h, fill=(20, 20, 24)); y += 40
    for t in (s.get("techniques", []) + s.get("transitions", []))[:12]:
        m = t.get("maps_to", {})
        kind = m.get("kind", "custom")
        tag = {"text-animation": "text " + str(m.get("id", "")), "fast-cut": "fast-cut " + str(m.get("feature", "")),
               "registry": "block " + str(m.get("item", "")), "custom": "build"}.get(kind, kind)
        tw = d.textlength(tag, font=f_s) + 18
        d.rounded_rectangle([x0, y + 2, x0 + tw, y + 26], radius=12, fill=KIND.get(kind, (120, 120, 120)))
        d.text((x0 + 9, y + 5), tag, font=f_s, fill=(255, 255, 255))
        for k, line in enumerate(textwrap.wrap(t.get("name", ""), 44)[:2]):
            d.text((x0 + tw + 12, y + 3 + k * 22), line, font=f_s, fill=(40, 40, 48))
        y += 52
    # not copied
    dc = s.get("dont_copy", [])
    if dc:
        y = max(y + 10, 840)
        for k, line in enumerate(textwrap.wrap("Not copied: " + "; ".join(dc), 72)[:5]):
            d.text((x0, y + k * 22), line, font=f_s, fill=(160, 60, 50))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    im.save(a.out)
    print("card ->", a.out)


if __name__ == "__main__":
    main()
