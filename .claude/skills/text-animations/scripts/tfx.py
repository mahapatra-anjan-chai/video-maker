#!/usr/bin/env python3
"""tfx.py: the text-animation picker, the preview gallery, and single animated texts for a video.

  python3 tfx.py picker                      write picker.widget.html (the in-chat picker) and gallery.html (the render page)
  python3 tfx.py gallery --out DIR           render the whole library as a looping preview: DIR/text-animations.mp4 and DIR/preview.png
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
WORDS = {5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}


def catalogue():
    """TextFX.list and TextFX.categories straight from text-fx.js: counts are never typed by hand."""
    out = subprocess.run(["node", "-e", "global.window=global;global.document=undefined;require(%s);"
                          "console.log(JSON.stringify({list:TextFX.list,cats:TextFX.categories,tr:TextFX.transitions}))" % json.dumps(LIB)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def lib_source():
    """text-fx.js for an in-chat widget: minified with the project's esbuild when it is there (half the size)."""
    es = os.path.join(ROOT, "node_modules", ".bin", "esbuild")
    if os.path.exists(es):
        r = subprocess.run([es, LIB, "--minify", "--log-level=error"], capture_output=True, text=True)
        if r.returncode == 0 and len(r.stdout) > 1000:
            return r.stdout
    return open(LIB).read()


def counted(text):
    c = catalogue()
    return text.replace("__N__", str(len(c["list"]))).replace("__G__", WORDS.get(len(c["cats"]), str(len(c["cats"]))))


def fontfaces(prefix="fonts/"):
    return "".join('@font-face{font-family:"Poppins";src:url("%sPoppins-%s.woff2") format("woff2");font-weight:%s;font-display:block}\n'
                   % (prefix, w, w) for w in ("300", "400", "500", "700"))


# ------------------------------------------------------------------ picker: the dropdown with live previews
PICKER = r"""<h2 class="sr-only" style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)">Animation picker: __N__ live previews in __G__ groups (text, cards and cursors, transitions); pick the ones for this video.</h2>
<div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:0 0 1rem">
  <label for="tfx-cat" style="font-size:14px;color:var(--text-secondary)">Which kind of text animation?</label>
  <select id="tfx-cat" style="min-width:220px"><option value="">All __N__ animations</option></select>
  <span id="tfx-count" style="font-size:13px;color:var(--text-secondary)">Tap a preview to pick it</span>
</div>
<div id="tfx-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px"></div>
__BACKGROUNDS__<div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:1rem">
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
    var bgv = window.tfxBackground ? window.tfxBackground.value : "";
    if (!picked.length && !bgv) { msg.style.color = "var(--text-danger)"; msg.textContent = "Pick at least one animation first"; return; }
    var text = (picked.length ? "Text animations for this video: " + picked.map(function (a) { return pad(a.n) + " " + a.name + " (" + a.id + ")"; }).join(", ") : "") +
      (bgv ? (picked.length ? "; background: " : "Background for this video: ") + bgv : "");
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
<p class="lead">__N__ animations for product videos: text, cards and cursors, transitions. Pick the ones you want, then press the button and paste the line into Claude Code.</p>
%s
</main></body></html>
"""


def cmd_picker(a):
    lib = lib_source()
    gal = PICKER.replace("__BACKGROUNDS__", "").replace("__LOAD__", '<script src="../youtube-edit/assets/vendor/gsap.min.js"></script>\n'
                         '<script>window.gsap||document.write(\'<script src="%s"><\\/script>\')</script>\n'
                         '<script src="text-fx.js"></script>' % GSAP_CDN)
    open(os.path.join(HERE, "gallery.html"), "w").write(counted(PAGE % (fontfaces("../youtube-edit/styles/brand/fonts/"), gal)))
    widget = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800;900&display=swap">\n' +
              PICKER.replace("__BACKGROUNDS__", BACKGROUNDS.replace("__HALFTONE__", HALFTONE).replace("__BGLOOK__", json.dumps(look_colours("brand"))))
              .replace("__LOAD__", '<script src="%s"></script>\n<script>%s</script>' % (GSAP_CDN, lib)))
    widget = counted(widget)
    open(os.path.join(HERE, "picker.widget.html"), "w").write(widget)
    print(os.path.join(HERE, "gallery.html"))
    print(os.path.join(HERE, "picker.widget.html"), "(%d KB: pass it to show_widget)" % (len(widget) // 1024))


# ------------------------------------------------------------------ the scene planner (one video's scenes, in the chat)
BACKGROUNDS = r"""<div style="font-size:14px;color:var(--text-secondary);margin:1.2rem 0 .6rem">Background, drawn in the video's own colours (optional)</div>
<div id="tfx-bg" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px"></div>
__HALFTONE__<script>
(function () {
  var LOOK = __BGLOOK__, box = document.getElementById("tfx-bg"), cards = {}, render = tfxHalftone(LOOK, 150, 84, 60);
  window.tfxBackground = { value: "" };
  [["halftone-light", "Halftone, light"], ["halftone-dark", "Halftone, dark"], ["plain", "Plain"]].forEach(function (b) {
    var card = document.createElement("div"); card.setAttribute("role", "button"); card.tabIndex = 0;
    card.style.cssText = "cursor:pointer;border-radius:10px;overflow:hidden;border:0.5px solid var(--border);font-size:13px;color:var(--text-primary);background:var(--surface-2)";
    var cv = document.createElement("canvas"); cv.width = 150; cv.height = 84; cv.style.cssText = "display:block;width:100%;height:84px;background:#fff";
    var nm = document.createElement("div"); nm.style.cssText = "padding:6px 8px"; nm.textContent = b[1];
    card.appendChild(cv); card.appendChild(nm); box.appendChild(card);
    if (b[0] !== "plain") cards[b[0]] = cv;
    var pick = function () {
      var on = window.tfxBackground.value !== b[0]; window.tfxBackground.value = on ? b[0] : "";
      Array.from(box.children).forEach(function (c) { c.style.outline = "none"; });
      if (on) card.style.outline = "2px solid var(--border-accent)";
    };
    card.addEventListener("click", pick); card.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
  });
  var t0 = performance.now(), last = 0;
  (function tick(now) {
    if (now - last > 80) { last = now; var th = 2 * Math.PI * ((now - t0) / 12000 % 1);
      Object.keys(cards).forEach(function (m) { cards[m].getContext("2d").drawImage(render(m, th), 0, 0); }); }
    requestAnimationFrame(tick);
  })(performance.now());
})();
</script>
"""


HALFTONE = r"""<script>
function tfxHalftone(LOOK, W, H, COLS) {      // the halftone background (halftone.py's field), live on a canvas
  function hex(h) { h = h.replace("#", ""); return [0, 2, 4].map(function (i) { return parseInt(h.substr(i, 2), 16); }); }
  function mix(a, b, t) { return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]; }
  var WHITE = [255, 255, 255], HI = hex(LOOK.accent3), ANCHOR = hex(LOOK.accent), PUNCH = hex(LOOK.accent2), DARK = hex(LOOK.dark);
  var PAL = { "halftone-light": [mix(WHITE, HI, .07), mix(WHITE, HI, .55), PUNCH, ANCHOR],
              "halftone-dark": [DARK, mix(DARK, ANCHOR, .55), HI, PUNCH] };
  var BL = [[.2, .3, .16, .14, 1, 2, 0, .17], [.8, .22, .14, .16, 2, 1, 1.7, .15], [.55, .8, .2, .12, 1, 1, 3.1, .19], [.08, .86, .12, .14, 2, 3, 4.4, .13],
            [.93, .72, .1, .18, 3, 2, 5.2, .14], [.45, .08, .22, .1, 1, 2, 2.3, .12], [.62, .45, .18, .2, 2, 1, .8, .1]];
  function field(x, y, th) {
    var P = 2 * Math.PI, wx = x + .06 * Math.sin(P * 1.6 * y + th) + .03 * Math.sin(P * 3.4 * y - 2 * th),
        wy = y + .06 * Math.cos(P * 1.3 * x + 2 * th) + .03 * Math.cos(P * 2.9 * x + th), g = 0;
    BL.forEach(function (b) { var bx = b[0] + b[2] * Math.cos(b[4] * th + b[6]), by = b[1] + b[3] * Math.sin(b[5] * th + b[6] * .7), rr = b[7] * (1 + .18 * Math.sin(th + b[6]));
      g += Math.exp(-((wx - bx) * (wx - bx) * (W / H) * (W / H) + (wy - by) * (wy - by)) / (2 * rr * rr)); });
    return 1 - Math.exp(-1.5 * g);
  }
  var CELL = W / COLS, ROWS = Math.ceil(H / CELL), SRC = {};
  return function render(mode, th) {
    var p = PAL[mode], c = SRC[mode] || (SRC[mode] = { cv: document.createElement("canvas"), lo: document.createElement("canvas") });
    c.cv.width = W; c.cv.height = H; c.lo.width = COLS; c.lo.height = ROWS;
    var lx = c.lo.getContext("2d"), img = lx.createImageData(COLS, ROWS), dots = [];
    for (var j = 0; j < ROWS; j++) for (var i = 0; i < COLS; i++) {
      var gx = (i + .5) / COLS, gy = (j + .5) * CELL / H, f = field(gx, gy, th);
      var v = f < .36 ? Math.exp(-Math.pow((.36 - f) / .3, 2)) : Math.exp(-Math.pow((f - .36) / .1, 2)), inside = Math.min(1, Math.max(0, (f - .42) / .3));
      var col = mix(mix(p[0], p[1], Math.pow(v, 1.2) * .75), p[1], inside * .22), k = (j * COLS + i) * 4;
      img.data[k] = col[0]; img.data[k + 1] = col[1]; img.data[k + 2] = col[2]; img.data[k + 3] = 255;
      var r = .46 * CELL * Math.pow(v, 1.6);
      if (r > .4) { var M = .5 + .5 * Math.sin(2 * Math.PI * (gx * 1.3 - gy * .9) + th); dots.push([(i + .5) * CELL, (j + .5) * CELL, r, mix(mix(p[2], p[3], M * .5), p[1], .15)]); }
    }
    lx.putImageData(img, 0, 0);
    var x = c.cv.getContext("2d"); x.imageSmoothingEnabled = true; x.drawImage(c.lo, 0, 0, W, H); x.globalAlpha = .9;
    dots.forEach(function (d) { x.fillStyle = "rgb(" + d[3].map(Math.round).join(",") + ")"; x.beginPath(); x.arc(d[0], d[1], d[2], 0, 2 * Math.PI); x.fill(); });
    x.globalAlpha = 1; return c.cv;
  };
}
</script>
"""


PLANNER = r"""<h2 class="sr-only" style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)">Scene planner: each scene's line animating live, the transition between scenes and the background; pick, then send the plan back.</h2>
<div style="font-size:14px;color:var(--text-secondary);margin:0 0 .6rem">Background</div>
<div id="pl-bg" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin:0 0 1.2rem"></div>
<div id="pl-rows" style="display:flex;flex-direction:column;gap:8px"></div>
<div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:1rem">
  <button id="pl-use" type="button">Use these choices &#8599;</button>
  <span id="pl-msg" style="font-size:13px;color:var(--text-secondary)"></span>
</div>
__LOAD__
__HALFTONE__<script>
(function () {
  var PLAN = __PLAN__, LOOK = __LOOK__, PALS = __PALS__;
  var rows = document.getElementById("pl-rows"), bgBox = document.getElementById("pl-bg"), msg = document.getElementById("pl-msg");
  var textIds = TextFX.list.filter(function (a) { return a.category !== "Transitions"; }), byId = {};
  TextFX.list.forEach(function (a) { byId[a.id] = a; });
  function previewText(sc) { var a = byId[sc.anim] || {}; return (a.sample || "").indexOf("|") >= 0 ? (sc.parts || sc.text) : sc.text; }
  var bg = PLAN.background || "halftone-light", stages = [], W = 280, H = 158;
  var render = tfxHalftone(LOOK, W, H, 96);
  var t0 = performance.now(), last = 0, cards = {};
  function tick(now) {
    if (now - last > 66) {
      last = now; var th = 2 * Math.PI * ((now - t0) / 12000 % 1);
      ["halftone-light", "halftone-dark"].forEach(function (m) {
        var src = render(m, th);
        if (cards[m]) cards[m].getContext("2d").drawImage(src, 0, 0, cards[m].width, cards[m].height);
        if (m === bg) stages.forEach(function (st) { st.cv.getContext("2d").drawImage(src, 0, 0, st.cv.width, st.cv.height); });
      });
    }
    requestAnimationFrame(tick);
  }
  function colours() { return PALS[bg]; }
  function play(st) {
    if (st.tl) st.tl.kill();
    var c = colours(); st.cv.style.display = bg === "plain" ? "none" : "block"; st.el.style.background = c.bg;
    if (st.kind === "scene") {
      if (st.nameEl) st.nameEl.style.color = c.ink;
      var own = st.scene.kind === "custom";            // the product's own scene: its line is a headline over its screens
      var r = TextFX.build(st.inner, own ? "accent-words" : st.scene.anim, Object.assign({}, c, { text: own ? st.scene.text : previewText(st.scene), font: "Poppins, system-ui, sans-serif" }));
      st.tl = r.tl.repeat(-1).repeatDelay(0.8).play();
    } else {
      st.inner.innerHTML = ""; var tl = gsap.timeline({ paused: true, repeat: -1, repeatDelay: 0.6 });
      var mk = function (t) { var d = document.createElement("div"); d.style.cssText = "position:absolute;inset:0;display:flex;align-items:center;justify-content:center;" +
        "padding:0 10px;text-align:center;font:600 15px/1.2 Poppins,sans-serif;color:" + c.ink; d.textContent = t; st.inner.appendChild(d); return d; };
      var a = mk(st.from.text), z = mk(st.to.text), k = st.from.tr || "cut", at = 0.9;
      tl.set(z, { opacity: 0 }, 0);
      if (k === "cut") { tl.set(a, { opacity: 0 }, at); tl.set(z, { opacity: 1 }, at); }
      else TextFX.transition(tl, k, a, z, at, { manage: true, W: st.w, H: st.h, container: st.inner, colors: [c.accent, c.accent2], cols: 14, seed: 5 });
      tl.to({}, { duration: 1.4 }, at + 0.5);
      st.tl = tl.play();
    }
  }
  function select(opts, val, on) {
    var s = document.createElement("select"); s.style.cssText = "max-width:100%";
    opts.forEach(function (o) { var op = document.createElement("option"); op.value = o[0]; op.textContent = o[1]; if (o[0] === val) op.selected = true; s.appendChild(op); });
    s.addEventListener("change", function () { on(s.value); }); return s;
  }
  function stage(w, h, extra) {
    var el = document.createElement("div"); el.style.cssText = "position:relative;flex:none;width:" + w + "px;height:" + h + "px;border-radius:10px;overflow:hidden;border:0.5px solid var(--border)";
    var cv = document.createElement("canvas"); cv.width = w; cv.height = h; cv.style.cssText = "position:absolute;inset:0;width:100%;height:100%";
    var inner = document.createElement("div"); inner.style.cssText = "position:absolute;inset:0"; el.appendChild(cv); el.appendChild(inner);
    var st = Object.assign({ el: el, cv: cv, inner: inner, w: w, h: h }, extra); stages.push(st); return st;
  }
  ["halftone-light", "halftone-dark", "plain"].forEach(function (k) {
    var card = document.createElement("div"); card.setAttribute("role", "button"); card.tabIndex = 0;
    card.style.cssText = "cursor:pointer;border-radius:10px;overflow:hidden;border:0.5px solid var(--border);font-size:13px;color:var(--text-primary)";
    var sw = document.createElement("canvas"); sw.width = 150; sw.height = 84; sw.style.cssText = "display:block;width:100%;height:84px;background:" + LOOK.paper;
    if (k !== "plain") cards[k] = sw;
    var name = document.createElement("div"); name.style.cssText = "padding:6px 8px"; name.textContent = { "halftone-light": "Halftone, light", "halftone-dark": "Halftone, dark", "plain": "Plain" }[k];
    card.appendChild(sw); card.appendChild(name);
    var pick = function () { bg = k; Array.from(bgBox.children).forEach(function (c) { c.style.outline = "none"; }); card.style.outline = "2px solid var(--border-accent)"; stages.forEach(play); };
    card.addEventListener("click", pick); card.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
    if (k === bg) card.style.outline = "2px solid var(--border-accent)";
    bgBox.appendChild(card);
  });
  PLAN.scenes.forEach(function (sc, i) {
    var row = document.createElement("div"); row.style.cssText = "display:flex;gap:14px;align-items:center;flex-wrap:wrap;padding:10px;border-radius:12px;border:0.5px solid var(--border);background:var(--surface-2)";
    var st = stage(W, H, { kind: "scene", scene: sc }); row.appendChild(st.el);
    var side = document.createElement("div"); side.style.cssText = "flex:1;min-width:200px;display:flex;flex-direction:column;gap:6px;font-size:13px;color:var(--text-primary)";
    var l1 = document.createElement("div"), l2 = document.createElement("div"); l1.textContent = sc.id + "  " + (sc.label || ""); l2.textContent = sc.text; l2.style.color = "var(--text-secondary)";
    side.appendChild(l1); side.appendChild(l2);
    var kind = sc.kind || "text";
    if (kind === "custom") {
      var own = document.createElement("div"); own.style.cssText = "color:var(--text-muted)";
      own.textContent = "Your product's own scene: its screens are built for this film and show in the storyboard"; side.appendChild(own);
    } else {
      if (kind === "logo" || kind === "lockup") {
        var nm = document.createElement("div"); nm.style.cssText = "position:absolute;left:0;right:0;top:16%;text-align:center;font:700 22px Poppins,sans-serif;z-index:2";
        nm.textContent = sc.name || PLAN.name || ""; st.el.appendChild(nm); st.nameEl = nm;
        var cap = document.createElement("div"); cap.style.cssText = "color:var(--text-muted)"; cap.textContent = "The line under the name:"; side.appendChild(cap);
      }
      side.appendChild(select(textIds.map(function (a) { return [a.id, a.name + " (" + a.category + ")"]; }), sc.anim, function (v) { sc.anim = v; play(st); }));
    }
    row.appendChild(side); rows.appendChild(row);
    if (i < PLAN.scenes.length - 1) {
      var tr = document.createElement("div"); tr.style.cssText = "display:flex;gap:14px;align-items:center;flex-wrap:wrap;padding:4px 10px 4px 40px";
      var ts = stage(220, 124, { kind: "tr", from: sc, to: PLAN.scenes[i + 1] }); tr.appendChild(ts.el);
      var lab = document.createElement("div"); lab.style.cssText = "font-size:13px;color:var(--text-secondary);display:flex;flex-direction:column;gap:6px";
      var l3 = document.createElement("div"); l3.textContent = "Into scene " + PLAN.scenes[i + 1].id; lab.appendChild(l3);
      lab.appendChild(select(TextFX.transitions.map(function (t) { return [t.id, t.name]; }), sc.tr || "cut", function (v) { sc.tr = v; play(ts); }));
      tr.appendChild(lab); rows.appendChild(tr);
    }
  });
  (document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve()).then(function () { stages.forEach(play); requestAnimationFrame(tick); });
  document.getElementById("pl-use").addEventListener("click", function () {
    var parts = ["background=" + bg];
    PLAN.scenes.forEach(function (sc, i) { if (sc.kind !== "custom") parts.push(sc.id + "=" + sc.anim); if (i < PLAN.scenes.length - 1) parts.push(sc.id + ">" + PLAN.scenes[i + 1].id + "=" + (sc.tr || "cut")); });
    var text = "Scene plan: " + parts.join("; ");
    if (typeof sendPrompt === "function") { sendPrompt(text); msg.textContent = "Sent"; }
    else if (navigator.clipboard) { navigator.clipboard.writeText(text).then(function () { msg.textContent = "Copied: paste it to Claude"; }); }
    else { msg.textContent = text; }
  });
})();
</script>"""


def look_colours(look):
    """A look's role colours as TextFX options (youtube-edit/styles/<look>.json)."""
    path = os.path.join(SKILLS, "youtube-edit", "styles", look + ".json")
    if not os.path.exists(path):
        sys.exit("no look named %r in youtube-edit/styles" % look)
    j = json.load(open(path)); c = j.get("colors") or {}
    dark = [v for v in (j.get("extra_colors") or {}).values() if isinstance(v, str) and v.startswith("#")]
    return {"ink": dark[0] if dark else "#0F172A", "dark": dark[0] if dark else "#0F172A", "accent": c.get("blue", "#4F46E5"),
            "accent2": c.get("magenta", "#DB2777"), "accent3": c.get("cyan", "#7DD3FC"), "accent4": c.get("amber", "#FBBF24"), "paper": "#FFFFFF"}


def palettes(look):
    """The text colours for each background, in ONE place: the planner previews and the film builder both read this."""
    c = look_colours(look)
    mixed = lambda a, b, t: "#%02X%02X%02X" % tuple(round(int(a[i:i + 2], 16) * (1 - t) + int(b[i:i + 2], 16) * t) for i in (1, 3, 5))
    light = {"ink": c["ink"], "accent": c["accent"], "accent2": c["accent2"], "accent3": c["accent3"], "accent4": c["accent4"],
             "paper": c["paper"], "bg": mixed("#FFFFFF", c["accent3"], 0.07)}
    dark = dict(light, ink="#FFFFFF", accent=c["accent3"], paper=c["dark"], bg=c["dark"])
    return {"halftone-light": light, "halftone-dark": dark, "plain": dict(light, bg=c["paper"])}


def cmd_planner(a):
    plan = json.load(open(a.scenes))
    look = a.look or plan.get("look") or "brand"
    for k, sc in enumerate(plan["scenes"]):
        sc.setdefault("id", k + 1); sc.setdefault("anim", "accent-words"); sc.setdefault("tr", "cut")
    keep = {"background": plan.get("background", "halftone-light"), "name": plan.get("name", ""),
            "scenes": [{k: sc[k] for k in ("id", "label", "kind", "name", "text", "parts", "anim", "tr") if k in sc} for sc in plan["scenes"]]}
    widget = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800;900&display=swap">\n' +
              PLANNER.replace("__LOAD__", '<script src="%s"></script>\n<script>%s</script>' % (GSAP_CDN, lib_source()))
              .replace("__PLAN__", json.dumps(keep, ensure_ascii=False)).replace("__LOOK__", json.dumps(look_colours(look))).replace("__PALS__", json.dumps(palettes(look))).replace("__HALFTONE__", HALFTONE))
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.scenes)), "review", "planner.widget.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w").write(widget)
    print("%s (%d KB: pass it to show_widget)" % (out, len(widget) // 1024))


def apply_line(plan, line):
    """Write a 'Scene plan: background=...; 1=accent-words; 1>2=pixel; ...' line back into the plan (film.json)."""
    ids = {str(sc.get("id", k + 1)): sc for k, sc in enumerate(plan["scenes"])}
    tr_ids = set(t["id"] for t in catalogue()["tr"]); anim_ids = set(x["id"] for x in catalogue()["list"])
    body = line.split(":", 1)[1] if line.strip().lower().startswith("scene plan") else line
    changed = []
    for part in [p.strip() for p in body.split(";") if p.strip()]:
        key, _, val = part.partition("=")
        key, val = key.strip(), val.strip()
        if key == "background":
            if val not in ("halftone-light", "halftone-dark", "plain"):
                raise ValueError("unknown background %r" % val)
            plan["background"] = val; changed.append(part)
        elif ">" in key:
            frm = key.split(">")[0].strip()
            if frm not in ids or val not in tr_ids:
                raise ValueError("bad transition %r" % part)
            ids[frm]["tr"] = val; changed.append(part)
        elif key in ids:
            if val not in anim_ids:
                raise ValueError("unknown animation %r" % val)
            ids[key]["anim"] = val; changed.append(part)
        else:
            raise ValueError("no scene %r" % key)
    return changed


def cmd_apply(a):
    plan = json.load(open(a.scenes))
    try:
        changed = apply_line(plan, a.line)
    except ValueError as e:
        sys.exit("nothing written: %s" % e)
    json.dump(plan, open(a.scenes, "w"), indent=1, ensure_ascii=False)
    print("applied %d choices to %s" % (len(changed), a.scenes))


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
                  '<div style="position:absolute;left:84px;top:132px;font:400 24px/1 Poppins;color:#475569">__N__ animations for product videos, in __G__ groups</div>'], 200, 0
    cat_ = catalogue(); meta = cat_["list"]
    body[1] = counted(body[1])
    for cat in cat_["cats"]:
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
    shutil.rmtree(work, ignore_errors=True)                  # the render's work folder is never shipped
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
    pl = sub.add_parser("planner"); pl.add_argument("--scenes", required=True); pl.add_argument("--look"); pl.add_argument("--out")
    ap_ = sub.add_parser("apply"); ap_.add_argument("--scenes", required=True); ap_.add_argument("--line", required=True)
    g = sub.add_parser("gallery"); g.add_argument("--out", required=True); g.add_argument("--dur", type=float, default=8)
    g.add_argument("--still", type=float, default=1.3)
    c = sub.add_parser("clip")
    for k, req in (("id", True), ("text", True), ("size", True), ("box", True), ("out", True)):
        c.add_argument("--" + k, required=req)
    c.add_argument("--font-size", type=float, default=None); c.add_argument("--dur", type=float, default=3); c.add_argument("--fps", type=int, default=30)
    for k in ("ink", "accent", "accent2", "accent3", "accent4", "paper"):
        c.add_argument("--" + k, default=None)
    a = ap.parse_args()
    {"picker": cmd_picker, "planner": cmd_planner, "apply": cmd_apply, "gallery": cmd_gallery, "clip": cmd_clip}[a.cmd](a)


if __name__ == "__main__":
    main()
