#!/usr/bin/env python3
"""tfx.py: the text-animation picker, the preview gallery, and single animated texts for a video.

  python3 tfx.py picker                      write picker.widget.html (the in-chat picker) and gallery.html (the render page)
  python3 tfx.py gallery --out DIR           render all 51 as a looping preview: DIR/text-animations.mp4 and DIR/preview.png
  python3 tfx.py clip --id fade-up --text "Launch day, sorted" --size 1080x1920 --box 80,120,920,260 --font-size 72 \\
                      --dur 3 --out title.mov [--ink "#FFFFFF" --accent "#7DD3FC"]
                                             one animation as a transparent ProRes 4444 MOV, to lay over footage

Everything comes from text-fx.js, so the picker, the gallery and the video show the same motion.
"""
import argparse, glob, hashlib, html, json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(SKILLS))   # the project folder (node_modules has HyperFrames)
LIB = os.path.join(HERE, "text-fx.js")
GSAP = os.path.join(SKILLS, "youtube-edit", "assets", "vendor", "gsap.min.js")
FONTS = os.path.join(SKILLS, "youtube-edit", "styles", "brand", "fonts")
GSAP_CDN = "https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"
CATS = ["Entrances", "Emphasis", "Swaps and loops", "Transformations", "Video and UI", "Cards and cursors", "Transitions"]


def fontfaces(prefix="fonts/"):
    return "".join('@font-face{font-family:"Poppins";src:url("%sPoppins-%s.woff2") format("woff2");font-weight:%s;font-display:block}\n'
                   % (prefix, w, w) for w in ("300", "400", "500", "700"))


# ------------------------------------------------------------------ picker: the dropdown with live previews
PICKER = r"""<h2 class="sr-only" style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)">Animation picker: 51 live previews in seven groups (text, cards and cursors, transitions); pick the ones for this video.</h2>
<div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:0 0 1rem">
  <label for="tfx-cat" style="font-size:14px;color:var(--text-secondary)">Which kind of text animation?</label>
  <select id="tfx-cat" style="min-width:220px"><option value="">All 51 animations</option></select>
  <span id="tfx-count" style="font-size:13px;color:var(--text-secondary)">Tap a preview to pick it</span>
</div>
<div id="tfx-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px"></div>
<div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:1rem">
  <button id="tfx-use" type="button">Use the picked animations &#8599;</button>
  <span id="tfx-msg" style="font-size:13px;color:var(--text-secondary)"></span>
</div>
__LOAD__
<script>
(function () {
  var grid = document.getElementById("tfx-grid"), sel = document.getElementById("tfx-cat"), msg = document.getElementById("tfx-msg");
  var count = document.getElementById("tfx-count"), picked = [], items = [];
  TextFX.categories.forEach(function (c) {
    var n = TextFX.list.filter(function (a) { return a.category === c; }).length;
    var op = document.createElement("option"); op.value = c; op.textContent = c + " (" + n + ")"; sel.appendChild(op);
  });
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  TextFX.list.forEach(function (a) {
    var card = document.createElement("div");
    card.setAttribute("role", "button"); card.tabIndex = 0;
    card.style.cssText = "cursor:pointer;border:0.5px solid var(--border);border-radius:12px;overflow:hidden;background:var(--surface-2)";
    card.innerHTML = '<div class="tfx-st" style="height:124px;background:#fff"></div>' +
      '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;padding:8px 10px 2px;font-size:13px;color:var(--text-primary)">' +
      '<span><span style="color:var(--text-muted)">' + pad(a.n) + '</span> ' + a.name + '</span>' +
      '<span class="tfx-tag" style="visibility:hidden;font-size:11px;padding:2px 8px;border-radius:var(--radius);background:var(--bg-accent);color:var(--text-accent)">Picked</span></div>' +
      '<div style="padding:0 10px 10px;font-size:12px;line-height:1.4;color:var(--text-secondary)">' + a.use + '</div>';
    grid.appendChild(card);
    var it = { a: a, card: card, tl: null };
    items.push(it);
    function toggle() {
      var i = picked.indexOf(a);
      if (i < 0) picked.push(a); else picked.splice(i, 1);
      var on = picked.indexOf(a) >= 0;
      card.style.outline = on ? "2px solid var(--border-accent)" : "none";
      card.querySelector(".tfx-tag").style.visibility = on ? "visible" : "hidden";
      count.textContent = picked.length ? picked.length + " picked" : "Tap a preview to pick it";
      msg.textContent = "";
    }
    card.addEventListener("click", toggle);
    card.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } });
  });
  function start() {
    items.forEach(function (it) {
      var r = TextFX.build(it.card.querySelector(".tfx-st"), it.a.id, { font: "Poppins, system-ui, sans-serif" });
      it.tl = r.tl.repeat(-1).repeatDelay(0.7).play();
    });
  }
  (document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve()).then(function () { requestAnimationFrame(start); });
  sel.addEventListener("change", function () {
    items.forEach(function (it) {
      var show = !sel.value || it.a.category === sel.value;
      it.card.style.display = show ? "" : "none";
      if (it.tl) { if (show) it.tl.play(); else it.tl.pause(); }
    });
  });
  document.getElementById("tfx-use").addEventListener("click", function () {
    if (!picked.length) { msg.style.color = "var(--text-danger)"; msg.textContent = "Pick at least one animation first"; return; }
    var text = "Text animations for this video: " + picked.map(function (a) { return pad(a.n) + " " + a.name + " (" + a.id + ")"; }).join(", ");
    msg.style.color = "var(--text-secondary)";
    if (typeof sendPrompt === "function") { sendPrompt(text); msg.textContent = "Sent"; }
    else if (navigator.clipboard) { navigator.clipboard.writeText(text).then(function () { msg.textContent = "Copied: paste it to Claude"; }); }
    else { msg.textContent = text; }
  });
})();
</script>"""

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Text animations</title>
<style>
%s
:root{--text-primary:#0F172A;--text-secondary:#475569;--text-muted:#94A3B8;--text-danger:#B91C1C;--text-accent:#3730A3;--bg-accent:#E0E7FF;
--border:#E2E8F0;--border-accent:#4F46E5;--surface-2:#FFFFFF;--radius:8px}
@media (prefers-color-scheme:dark){:root{--text-primary:#F1F5F9;--text-secondary:#CBD5E1;--text-muted:#64748B;--border:#334155;--surface-2:#1E293B;
--bg-accent:#312E81;--text-accent:#E0E7FF}body{background:#0F172A}}
body{margin:0;padding:24px 16px;font-family:system-ui,sans-serif;background:#F8FAFC;color:var(--text-primary)}
main{max-width:1180px;margin:0 auto}
h1{font:600 22px/1.3 system-ui,sans-serif;margin:0 0 4px}p.lead{margin:0 0 20px;color:var(--text-secondary)}
select,button{font:inherit;font-size:14px;padding:7px 12px;border-radius:8px;border:1px solid var(--border);background:var(--surface-2);color:var(--text-primary)}
button{cursor:pointer}
</style></head>
<body><main>
<h1>Text animations</h1>
<p class="lead">51 animations for product videos: text, cards and cursors, transitions. Pick the ones you want, then press the button and paste the line into Claude Code.</p>
%s
</main></body></html>
"""


def cmd_picker(a):
    lib = open(LIB).read()
    gal = PICKER.replace("__LOAD__", '<script src="../youtube-edit/assets/vendor/gsap.min.js"></script>\n'
                         '<script>window.gsap||document.write(\'<script src="%s"><\\/script>\')</script>\n'
                         '<script src="text-fx.js"></script>' % GSAP_CDN)
    open(os.path.join(HERE, "gallery.html"), "w").write(PAGE % (fontfaces("../youtube-edit/styles/brand/fonts/"), gal))
    widget = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800;900&display=swap">\n' +
              PICKER.replace("__LOAD__", '<script src="%s"></script>\n<script>%s</script>' % (GSAP_CDN, lib)))
    open(os.path.join(HERE, "picker.widget.html"), "w").write(widget)
    print(os.path.join(HERE, "gallery.html"))
    print(os.path.join(HERE, "picker.widget.html"), "(%d KB: pass it to show_widget)" % (len(widget) // 1024))


# ------------------------------------------------------------------ HyperFrames projects
def project(dirpath, body, comp_id, W, H, dur, fps=30, bg="transparent", script=""):
    os.makedirs(os.path.join(dirpath, "fonts"), exist_ok=True)
    os.makedirs(os.path.join(dirpath, "vendor"), exist_ok=True)
    for f in glob.glob(os.path.join(FONTS, "*.woff2")):
        shutil.copy(f, os.path.join(dirpath, "fonts"))
    if not os.path.exists(GSAP):
        sys.exit("GSAP is missing (%s): run ./setup.sh" % GSAP)
    shutil.copy(GSAP, os.path.join(dirpath, "vendor", "gsap.min.js"))
    shutil.copy(LIB, os.path.join(dirpath, "text-fx.js"))
    page = """<!doctype html>
<html><head><meta charset="utf-8"><style>
%s html,body{margin:0;background:%s}
#stage{position:relative;width:%dpx;height:%dpx;overflow:hidden;background:%s;font-family:Poppins,sans-serif}
</style></head><body>
<div id="stage" data-composition-id="%s" data-start="0" data-duration="%s" data-fps="%d" data-width="%d" data-height="%d">
%s
<script src="vendor/gsap.min.js"></script>
<script src="text-fx.js"></script>
<script>
(function () {
  var master = gsap.timeline({ paused: true });
%s
  master.to({}, { duration: %s }, 0);
  window.__timelines = window.__timelines || {};
  window.__timelines["%s"] = master;
})();
</script>
</div></body></html>
""" % (fontfaces(), bg, W, H, bg, comp_id, dur, fps, W, H, body, script, dur, comp_id)
    open(os.path.join(dirpath, "index.html"), "w").write(page)


def render(dirpath, out, fmt="mp4", quiet=True):
    args = ["npx", "hyperframes", "render", os.path.abspath(dirpath), "-o", os.path.abspath(out), "--format", fmt]
    if fmt == "mp4":
        args += ["--quality", "delivery"]
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT)
    if r.returncode or not os.path.exists(out):
        sys.exit("hyperframes render failed:\n" + (r.stdout + r.stderr)[-2500:])
    return out


def cmd_gallery(a):
    a.out = os.path.abspath(a.out)
    W, cardw, cardh, gap = 1920, 280, 236, 20
    body, y, n = ['<div style="position:absolute;left:80px;top:56px;font:700 60px/1 Poppins;color:#0F172A">Text animations</div>',
                  '<div style="position:absolute;left:84px;top:132px;font:400 24px/1 Poppins;color:#475569">51 animations for product videos, in seven groups</div>'], 200, 0
    meta = json.loads(subprocess.run(["node", "-e", "global.window=global;global.document=undefined;require('%s');"
                                      "console.log(JSON.stringify(TextFX.list))" % LIB.replace("'", "\\'")],
                                     capture_output=True, text=True, check=True).stdout)
    for cat in CATS:
        body.append('<div style="position:absolute;left:84px;top:%dpx;font:700 30px/1 Poppins;color:#0F172A">%s</div>' % (y + 18, cat))
        y += 66
        group = [m for m in meta if m["category"] == cat]
        for i, m in enumerate(group):
            x = 80 + (i % 6) * (cardw + gap)
            if i and i % 6 == 0:
                y += cardh + gap
            body.append('<div style="position:absolute;left:%dpx;top:%dpx;width:%dpx;height:%dpx;border-radius:18px;background:#fff;border:1px solid #E2E8F0;overflow:hidden">'
                        '<div style="position:absolute;left:14px;top:12px;font:500 16px/1 Poppins;color:#475569;background:#F1F5F9;border-radius:99px;padding:6px 12px">'
                        '<span style="color:#94A3B8">%02d</span> %s</div>'
                        '<div class="st" data-id="%s" style="position:absolute;left:10px;right:10px;top:50px;bottom:10px;border-radius:10px;border:1px solid #EEF2F7"></div></div>'
                        % (x, y, cardw, cardh, m["n"], html.escape(m["name"]), m["id"]))
        y += cardh + gap + 10
    H = (y + 60) // 2 * 2
    dur = a.dur
    script = """  document.querySelectorAll(".st").forEach(function (st, i) {
    var r = TextFX.build(st, st.getAttribute("data-id"), {});
    r.tl.paused(false).repeat(Math.ceil(%s / (r.dur + 0.6))).repeatDelay(0.6);
    master.add(r.tl, 0.1 + (i %% 6) * 0.06);
  });""" % dur
    work = os.path.join(a.out, ".project")
    shutil.rmtree(work, ignore_errors=True)
    project(work, "\n".join(body), "text-animations", W, H, dur, bg="#F8FAFC", script=script)
    os.makedirs(a.out, exist_ok=True)
    mp4 = render(work, os.path.join(os.path.abspath(a.out), "text-animations.mp4"))
    png = os.path.join(a.out, "preview.png")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(a.still), "-i", mp4, "-frames:v", "1", png], check=True)
    print(mp4); print(png)


def cmd_clip(a):
    W, H = (int(v) for v in a.size.split("x"))
    bx, by, bw, bh = (int(float(v)) for v in a.box.split(","))
    opts = {"text": a.text, "size": a.font_size}
    for k in ("ink", "accent", "accent2", "accent3", "accent4", "paper"):
        if getattr(a, k):
            opts[k] = getattr(a, k)
    key = hashlib.sha1(json.dumps([a.id, opts, W, H, bx, by, bw, bh, a.dur, a.fps, open(LIB).read()], sort_keys=True).encode()).hexdigest()[:12]
    keyf = a.out + ".key"                        # same animation, text and box as last time: reuse the render
    if os.path.exists(a.out) and os.path.exists(keyf) and open(keyf).read() == key:
        print(a.out, "(cached)"); return
    body = '<div id="tfx" style="position:absolute;left:%dpx;top:%dpx;width:%dpx;height:%dpx"></div>' % (bx, by, bw, bh)
    script = "  var r = TextFX.build(document.getElementById('tfx'), %s, %s);\n  master.add(r.tl.paused(false), 0);" % (json.dumps(a.id), json.dumps(opts))
    work = tempfile.mkdtemp(prefix="tfx-clip-")
    project(work, body, "tfx-clip", W, H, a.dur, fps=a.fps, script=script)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    render(work, os.path.abspath(a.out), fmt="mov")
    open(a.out + ".key", "w").write(key)
    shutil.rmtree(work, ignore_errors=True)
    print(a.out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("picker")
    g = sub.add_parser("gallery"); g.add_argument("--out", required=True); g.add_argument("--dur", type=float, default=8)
    g.add_argument("--still", type=float, default=1.3)
    c = sub.add_parser("clip")
    for k, req in (("id", True), ("text", True), ("size", True), ("box", True), ("out", True)):
        c.add_argument("--" + k, required=req)
    c.add_argument("--font-size", type=float, default=None); c.add_argument("--dur", type=float, default=3); c.add_argument("--fps", type=int, default=30)
    for k in ("ink", "accent", "accent2", "accent3", "accent4", "paper"):
        c.add_argument("--" + k, default=None)
    a = ap.parse_args()
    {"picker": cmd_picker, "gallery": cmd_gallery, "clip": cmd_clip}[a.cmd](a)


if __name__ == "__main__":
    main()
