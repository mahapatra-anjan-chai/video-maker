#!/usr/bin/env python3
"""A mascot story in two scenes, joined by the Slice transition: in scene A the character holds a phone and scrolls an
endless feed; it lets go, winds up and slices through the phone along a glowing cut; the scene splits onto scene B,
where it lands and a prop (a shopping bag) pops into its hand. Any character image, any look, any size.

  python3 mascot_story.py --config story.json            renders story.mp4 and story.gif next to --out
  python3 mascot_story.py --config story.json --page-only    builds the HyperFrames page without rendering

story.json (paths relative to it):
  {"character": "img/mascot.png",          the character, a cut-out PNG (keep a company mascot in videos/, not the repo)
   "size": [1920, 1080],                   16:9, or [1080, 1920] for 9:16, or [1080, 1080]
   "look": "brand",                        colours from .claude/skills/youtube-edit/styles/<look>.json, or
   "colors": {"dark": "#1A1A2E", "light": "#CCABFF", "accent": "#A049D0", "accent2": "#5A34F5", "warm": "#FFB5A1"},
   "a": {"title": "Endless scrolling", "prop": "phone"},
   "b": {"title": "Shop what|you love", "prop": "bag"},     "|" breaks the line
   "out": "render/story.mp4"}

Scene B props: "bag" (a shopping bag pops into its hand and swings). New props and poses go in PROPS_B.
Deterministic: every move is on one GSAP timeline, rendered by HyperFrames frame by frame.
"""
import argparse, importlib.util, json, math, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(HERE))
spec = importlib.util.spec_from_file_location("tfx", os.path.join(SKILLS, "text-animations", "scripts", "tfx.py"))
tfx = importlib.util.module_from_spec(spec); spec.loader.exec_module(tfx)


def colours(cfg):
    if cfg.get("colors"):
        return dict({"dark": "#1A1A2E", "light": "#CCABFF", "accent": "#A049D0", "accent2": "#5A34F5", "warm": "#FFB5A1"}, **cfg["colors"])
    with open(os.path.join(SKILLS, "youtube-edit", "styles", cfg.get("look", "brand") + ".json")) as f:
        j = json.load(f)
    c = j.get("colors", {}); dark = list((j.get("extra_colors") or {}).values())
    return {"dark": dark[0] if dark else "#0F172A", "light": c.get("cyan", "#A5B4FC"), "accent": c.get("magenta", "#DB2777"),
            "accent2": c.get("blue", "#4F46E5"), "warm": c.get("amber", "#FBBF24")}


def layout(W, H):
    u = min(W, H); portrait = H > W * 1.2
    ph, pw = 0.54 * u * (1.25 if portrait else 1), 0.28 * u * (1.25 if portrait else 1)
    cx, cy = W * 0.505, H * (0.52 if portrait else 0.5) + 0.02 * u
    ang = -22 if portrait else -12.05                      # the cut: a diagonal through the phone's centre
    s = math.tan(math.radians(ang)); y_at = lambda x: cy + s * (x - cx)
    m = 0.28 * u                                           # the character's width
    return {"u": u, "portrait": portrait, "pw": pw, "ph": ph, "px": cx - pw / 2, "py": cy - ph / 2, "ang": ang, "s": s,
            "cut": [y_at(0) / H, y_at(W) / H], "y_at": y_at, "m": m,
            "sx": W * (0.05 if portrait else 0.11), "ex": W * (0.66 if portrait else 0.79),
            "land": (W * 0.3, H * 0.6) if portrait else (W * 0.625, H * 0.555)}


def phone_html(L, c):
    cols = [c["light"], c["warm"], c["accent"], c["accent2"], c["warm"], c["light"]]
    k = L["pw"] / 150.0                                    # the feed is drawn for a 150 px phone, then scaled
    card = ('<div style="height:62px;margin:0 0 8px;border-radius:10px;background:#24203D;display:flex;gap:8px;padding:8px;box-sizing:border-box">'
            '<div style="width:46px;height:46px;border-radius:8px;background:%s"></div><div style="flex:1;display:flex;flex-direction:column;gap:7px;'
            'padding-top:6px"><div style="height:8px;width:82%%;border-radius:4px;background:%s66"></div><div style="height:8px;width:56%%;'
            'border-radius:4px;background:%s3A"></div></div></div>')
    cards = "".join(card % (x, c["light"], c["light"]) for _ in range(4) for x in cols)
    return ('<div id="phone" style="position:absolute;left:%.0fpx;top:%.0fpx;width:150px;height:%.0fpx;transform-origin:0 0;transform:scale(%.4f);'
            'border-radius:26px;background:#0E0C1A;box-shadow:0 0 0 3px #3A3360,0 0 46px %s66"><div style="position:absolute;left:9px;top:12px;right:9px;'
            'bottom:12px;border-radius:18px;overflow:hidden;background:#141226"><div id="feed" style="position:absolute;left:7px;right:7px;top:7px">%s</div>'
            '</div><div style="position:absolute;left:50%%;top:6px;width:40px;height:5px;margin-left:-20px;border-radius:3px;background:#2E2A4A"></div></div>'
            % (L["px"], L["py"], L["ph"] / k, k, c["accent"], cards))


def bag_svg(c, w):
    return ('<svg viewBox="0 0 80 92" width="%.0f" height="%.0f"><path d="M26 26 Q26 6 40 6 Q54 6 54 26" fill="none" stroke="#FFFFFF" stroke-width="5" '
            'stroke-linecap="round"/><path d="M10 24 H70 L74 82 Q74 88 68 88 H12 Q6 88 6 82 Z" fill="%s"/><path d="M10 24 H70 L71 34 H9 Z" fill="%s" '
            'opacity=".55"/><circle cx="40" cy="58" r="9" fill="#FFFFFF" opacity=".85"/></svg>' % (w, w * 92 / 80, c["warm"], c["accent"]))


PROPS_B = {"bag": bag_svg}


def build(cfg, base, out_dir):
    W, H = cfg.get("size", [1920, 1080]); c = colours(cfg); L = layout(W, H); m = L["m"]
    ta = cfg.get("a", {}).get("title", "Endless scrolling"); tb = cfg.get("b", {}).get("title", "Shop what|you love").replace("|", "<br>")
    prop = cfg.get("b", {}).get("prop", "bag")
    hand = lambda i: ('<div id="%s" style="position:absolute;left:0;top:0;width:%.0fpx;height:%.0fpx;border-radius:50%%;background:radial-gradient(circle at '
                      '35%% 30%%,%s,%s);box-shadow:0 2px 6px #0006"></div>' % (i, m * 0.19, m * 0.16, c["light"], c["accent2"]))
    img = '<img src="character.png" style="width:%.0fpx;display:block">' % m
    fs = 0.096 * L["u"]
    body = f'''
<div id="stage" style="position:absolute;inset:0;overflow:hidden">
  <div id="B" style="position:absolute;inset:0;background:linear-gradient(135deg,{c["accent"]},{c["accent2"]});opacity:0">
    <div id="tB" style="position:absolute;left:0;right:0;top:{H * (0.14 if L["portrait"] else 0.17):.0f}px;text-align:center;font:800 {fs * 1.19:.0f}px/1.05 Poppins;color:#FFFFFF">{tb}</div>
  </div>
  <div id="A" style="position:absolute;inset:0;background:{c["dark"]}">
    <div id="tA" style="position:absolute;left:0;right:0;top:{H * (0.1 if L["portrait"] else 0.07):.0f}px;text-align:center;font:700 {fs:.0f}px/1.05 Poppins;color:{c["light"]}">{ta}</div>
    {phone_html(L, c)}
  </div>
  <div style="position:absolute;inset:0;z-index:70;pointer-events:none">
    {"".join('<div class="gh" style="position:absolute;left:0;top:0;opacity:0">%s</div>' % img for _ in range(3))}
    <div id="hero" style="position:absolute;left:0;top:0;width:{m:.0f}px;transform-origin:50% 100%">{img}</div>
    {hand("hL")}{hand("hR")}
    <div id="prop" style="position:absolute;left:0;top:0;transform-origin:50% 8%;opacity:0">{PROPS_B[prop](c, m * 0.56)}</div>
    {hand("hB")}
  </div>
</div>'''
    px, py, pw, ph = L["px"], L["py"], L["pw"], L["ph"]
    hx, hy = px - m * 0.79, py + ph * 0.36 - m * 0.45     # holding: the body overlaps the phone's left edge
    sx, ex = L["sx"], L["ex"]; half = m * 0.45
    sy, ey = L["y_at"](sx + m / 2) - half, L["y_at"](ex + m / 2) - half
    lx, ly = L["land"]; step = 70 * pw / 150
    script = f'''
  var m = master, empty = document.createElement("div"), S = {L["s"]:.5f}, CY = {L["y_at"](0):.1f};
  m.from("#tA", {{ opacity: 0, y: 24, duration: 0.5, ease: "power3.out" }}, 0.05);
  m.fromTo("#hero", {{ x: {hx - m:.0f}, y: {hy:.0f}, opacity: 0 }}, {{ x: {hx:.0f}, y: {hy:.0f}, opacity: 1, duration: 0.45, ease: "power3.out" }}, 0.1);
  m.fromTo("#hL", {{ x: {px - m * 0.09:.0f}, y: {py + ph * 0.6:.0f}, scale: 0 }}, {{ x: {px - m * 0.09:.0f}, y: {py + ph * 0.6:.0f}, scale: 1, duration: 0.25, ease: "back.out(2)" }}, 0.4);
  m.fromTo("#hR", {{ x: {px + pw - m * 0.09:.0f}, y: {py + ph * 0.52:.0f}, scale: 0 }}, {{ x: {px + pw - m * 0.09:.0f}, y: {py + ph * 0.52:.0f}, scale: 1, duration: 0.25, ease: "back.out(2)" }}, 0.45);
  m.set(["#prop", "#hB"], {{ opacity: 0 }}, 0);
  [0.7, 1.2, 1.7, 2.2].forEach(function (t, i) {{                // four thumb flicks of 1.5 cards: one full set, seamless
    m.to("#hR", {{ y: {py + ph * 0.52 - m * 0.17:.0f}, duration: 0.1, ease: "power2.out", yoyo: true, repeat: 1 }}, t - 0.08);
    m.to("#feed", {{ y: -105 * (i + 1), duration: 0.46, ease: "power3.out" }}, t);
    m.to("#hero", {{ rotation: i % 2 ? -3 : 3, duration: 0.24, ease: "sine.inOut", yoyo: true, repeat: 1 }}, t);
  }});
  m.to(["#hL", "#hR"], {{ scale: 0, duration: 0.15, ease: "power2.in" }}, 2.75);
  m.to("#hero", {{ scaleY: 1.12, scaleX: 0.92, duration: 0.1, yoyo: true, repeat: 1 }}, 2.75);
  m.to("#hero", {{ x: {sx:.0f}, y: {sy:.0f}, rotation: 0, duration: 0.3, ease: "power2.out" }}, 2.92);
  m.to("#hero", {{ x: {sx - m * 0.16:.0f}, rotation: -16, scaleX: 1.14, scaleY: 0.86, duration: 0.24, ease: "power2.out" }}, 3.2);
  m.set("#hero", {{ scaleX: 1.25, scaleY: 0.8, rotation: {L["ang"]}, filter: "blur({m * 0.027:.0f}px)" }}, 3.44);
  m.to("#hero", {{ x: {ex:.0f}, y: {ey:.0f}, duration: 0.09, ease: "expo.in" }}, 3.44);
  m.set("#hero", {{ filter: "blur(0px)" }}, 3.55);
  document.querySelectorAll(".gh").forEach(function (g, i) {{
    var gx = {sx:.0f} + ({ex:.0f} - {sx:.0f}) * [0.3, 0.55, 0.8][i];
    m.set(g, {{ x: gx, y: CY + (gx + {m / 2:.0f}) * S - {half:.0f}, rotation: {L["ang"]}, scaleX: 1.25, scaleY: 0.8, opacity: [0.4, 0.28, 0.16][i] }}, 3.48);
    m.to(g, {{ opacity: 0, duration: 0.14 }}, 3.55);
  }});
  TextFX.transition(m, "slice", document.getElementById("A"), document.getElementById("B"), 3.73, {{ manage: true, W: {W}, H: {H},
    container: document.getElementById("stage"), colors: ["{c["accent"]}", "{c["light"]}"], sprite: empty, size: {m:.0f}, cut: [{L["cut"][0]:.4f}, {L["cut"][1]:.4f}] }});
  m.to("#hero", {{ x: {ex + m * 0.21:.0f}, scaleX: 1, scaleY: 1, rotation: 8, duration: 0.14, ease: "power2.out" }}, 3.55);
  m.to("#hero", {{ x: {lx:.0f}, y: {ly:.0f}, rotation: 0, duration: 0.3, ease: "power2.in" }}, 3.73);
  m.to("#hero", {{ scaleX: 1.08, scaleY: 0.92, duration: 0.1, yoyo: true, repeat: 1 }}, 4.03);
  m.fromTo("#prop", {{ x: {lx + m * 0.84:.0f}, y: {ly + m * 0.23:.0f}, opacity: 0, scale: 0, rotation: -20 }}, {{ x: {lx + m * 0.84:.0f}, y: {ly + m * 0.23:.0f}, opacity: 1, scale: 1, rotation: 0, duration: 0.45, ease: "back.out(2.2)", immediateRender: false }}, 4.15);
  m.fromTo("#hB", {{ x: {lx + m * 1.03:.0f}, y: {ly + m * 0.2:.0f}, opacity: 0, scale: 0 }}, {{ x: {lx + m * 1.03:.0f}, y: {ly + m * 0.2:.0f}, opacity: 1, scale: 1, duration: 0.25, ease: "back.out(2)", immediateRender: false }}, 4.22);
  m.to("#prop", {{ rotation: 7, duration: 0.45, ease: "sine.inOut", yoyo: true, repeat: 3 }}, 4.6);
  m.to("#hero", {{ y: {ly - m * 0.067:.0f}, duration: 0.5, ease: "sine.inOut", yoyo: true, repeat: 3 }}, 4.4);
  m.from("#tB", {{ opacity: 0, scale: 0.86, filter: "blur(10px)", duration: 0.5, ease: "back.out(1.7)" }}, 4.0);
'''
    shutil.rmtree(out_dir, ignore_errors=True)
    tfx.project(out_dir, body, "mascot-story", W, H, 6.2, bg=c["dark"], script=script)
    ch = cfg.get("character")
    if ch:
        shutil.copy(ch if os.path.isabs(ch) else os.path.join(base, ch), os.path.join(out_dir, "character.png"))
    return os.path.join(out_dir, "index.html")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True); ap.add_argument("--page-only", action="store_true")
    a = ap.parse_args()
    with open(a.config) as f:
        cfg = json.load(f)
    base = os.path.dirname(os.path.abspath(a.config))
    out = cfg.get("out", "render/story.mp4"); out = out if os.path.isabs(out) else os.path.join(base, out)
    page = build(cfg, base, os.path.join(os.path.dirname(out), ".mascot-story"))
    if a.page_only:
        print(page); return
    mp4 = tfx.render(os.path.dirname(page), out)
    gif = os.path.splitext(out)[0] + ".gif"
    W = min(720, cfg.get("size", [1920, 1080])[0])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp4, "-vf", "fps=24,scale=%d:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=160:"
                    "stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" % W, "-loop", "0", gif], check=True)
    print(mp4); print(gif)


if __name__ == "__main__":
    main()
