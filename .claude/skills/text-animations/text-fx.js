/* text-fx.js: 42 text animations as GSAP timelines (needs gsap 3 on the page).
 *
 *   const { tl, dur } = TextFX.build(stageEl, "fade-up", { text: "Launch day, sorted", size: 64 });
 *   master.add(tl.play(), 2.0);          // in a HyperFrames composition: place it at 2 s
 *   tl.repeat(-1).repeatDelay(0.6).play(); // in a preview: loop it
 *
 * Every timeline is paused, deterministic and seek-safe: no Math.random, no CSS animations, no timers, so HyperFrames
 * can render any frame in any order. The stage is any sized element; the animation fills it, centred.
 * Options: text ("a|b" for parts), size (px), ink (text colour), accent, accent2, accent3, accent4, paper, font, weight, hold.
 */
(function (root) {
  "use strict";
  var LIST = [
    ["fade-up", "Fade up", "Entrances", "Launch day, sorted", "Calm opener for a headline or a value line"],
    ["typewriter", "Typewriter", "Entrances", "Type what you need", "Prompts, search, anything typed"],
    ["pop-in", "Pop in", "Entrances", "New. Fast. Yours.", "Short punchy words, feature names"],
    ["mask-reveal", "Mask reveal", "Entrances", "Meet the|new app", "Premium headline reveal, section titles"],
    ["blur-in", "Blur in", "Entrances", "Clearer every day", "Soft, elegant openers; AI and clarity themes"],
    ["scramble", "Text scramble", "Entrances", "AI-powered search", "Tech and AI features, data, codes"],
    ["write-on", "Write on", "Entrances", "Approved", "Sign-off, handwritten notes, a personal touch"],
    ["scatter-in", "Scatter in", "Entrances", "All together now", "Things coming together: integrations, teams"],
    ["stamp", "Stamp", "Entrances", "SHIPPED", "Verdicts: approved, sold out, done"],
    ["drop-in", "Drop in", "Entrances", "Drop it in", "Playful openers, uploads, drag and drop"],
    ["tilt-reveal", "Tilt reveal", "Entrances", "Turn the page", "Section changes, chapter titles"],
    ["behind-subject", "Text behind subject", "Entrances", "BOLD", "A big word behind a person or product"],
    ["highlight", "Highlight", "Emphasis", "Built for busy teams", "Mark the one phrase that matters"],
    ["tracking-out", "Tracking out", "Emphasis", "Room to breathe", "Space, calm, premium"],
    ["strikethrough", "Strikethrough", "Emphasis", "Weeks|Minutes", "Before and after: old way vs new way"],
    ["hand-circle", "Hand-drawn circle", "Emphasis", "Only one click", "Point at a word like a marker on a slide"],
    ["shimmer", "Shimmer", "Emphasis", "AI prompts", "AI, premium, new-feature sparkle"],
    ["squash-stretch", "Squash and stretch", "Emphasis", "Bouncy", "Playful brands, fun moments"],
    ["wave", "Wave", "Emphasis", "Catchy", "Music, rhythm, light-hearted emphasis"],
    ["variable-weight", "Variable weight", "Emphasis", "Louder", "Turning something up: volume, impact, growth"],
    ["whip-in", "Whip in", "Emphasis", "Faster", "Speed claims, quick transitions"],
    ["bouncing-dot", "Bouncing dot", "Emphasis", "Plan Build Ship", "Steps, a process, a list read aloud"],
    ["float", "Float", "Emphasis", "smart|simple|fast|fun|human|bold", "Brand attributes, a cloud of benefits"],
    ["tracking-in", "Tracking in", "Emphasis", "FOCUS", "Pulling attention in, concentration"],
    ["text-flip", "Text flip", "Swaps and loops", "Videos for|Launches|Demos|Ads", "One sentence, many audiences or uses"],
    ["word-carousel", "Word carousel", "Swaps and loops", "Better|hooks|CTAs|demos|headlines", "Rotating benefits after a fixed lead-in"],
    ["color-shift", "Color shift", "Swaps and loops", "SHIP IT", "Brand colours, energy, a logo-like word"],
    ["marquee", "Marquee", "Swaps and loops", "LAUNCH|NOW LIVE", "Loud announcements, end cards, events"],
    ["oversized-crop", "Oversized crop", "Swaps and loops", "SHIP", "Bold brand moments, cover frames"],
    ["text-path", "Text on a path", "Swaps and loops", "from idea to launch to growth", "Journeys, flows, a path to value"],
    ["shape-morph", "Shape morph", "Transformations", "Get started", "A dot becomes the CTA button"],
    ["extrude-3d", "3D extrude", "Transformations", "BOLD", "Big claims, numbers, chunky emphasis"],
    ["zoom-through", "Zoom through", "Transformations", "ZOOM|in", "Diving into a feature, scene change"],
    ["invert", "Invert", "Transformations", "Dark mode", "Contrast, before and after, dark mode"],
    ["reflection", "Reflection", "Transformations", "Reflect", "Polished, glossy product moments"],
    ["repeater", "Repeater", "Transformations", "Again", "Repetition, automation, every time"],
    ["inline-images", "Inline images", "Video and UI", "Shoes|Bags|Lamps", "Show the things the words name"],
    ["tracked-callout", "Tracked callout", "Video and UI", "Size M fits you", "Label something that moves in the recording"],
    ["karaoke", "Karaoke captions", "Video and UI", "Notes in plain words get a new version", "Captions for a voiceover"],
    ["text-mask", "Text mask", "Video and UI", "PLAY", "Footage or colour inside big letters"],
    ["chat-bubbles", "Chat bubbles", "Video and UI", "Can it do vertical?|Yes, and 16:9.|Ship it.", "Conversations, support, AI chat features"],
    ["counter", "Counter", "Video and UI", "Monthly revenue|48.2", "Metrics, growth, results"]
  ];
  var CATS = ["Entrances", "Emphasis", "Swaps and loops", "Transformations", "Video and UI"];

  function seeded(seed) {                       // the same "random" numbers on every render
    var s = (seed >>> 0) || 1;
    return function () { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 4294967296; };
  }
  function css() {
    if (document.getElementById("tfx-css")) return;
    var st = document.createElement("style"); st.id = "tfx-css";
    st.textContent = ".tfx-stage{position:relative;overflow:hidden}.tfx-box{position:absolute;inset:0;display:flex;" +
      "align-items:center;justify-content:center;flex-direction:column;text-align:center;line-height:1.12}" +
      ".tfx-i{display:inline-block;white-space:pre;will-change:transform}.tfx-line{display:block;overflow:hidden;padding:0 .08em}";
    document.head.appendChild(st);
  }
  function E(tag, style, html, cls) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (style) e.style.cssText = style;
    if (html != null) e.innerHTML = html;
    return e;
  }
  function chars(parent, text) {
    return text.split("").map(function (c) { var s = E("span", "", c === " " ? " " : c, "tfx-i"); parent.appendChild(s); return s; });
  }
  function words(parent, text, gap) {
    return text.split(" ").map(function (w, i, a) {
      var s = E("span", "", w, "tfx-i"); parent.appendChild(s);
      if (i < a.length - 1) parent.appendChild(document.createTextNode(gap || " "));
      return s;
    });
  }
  function hold(tl, d) { tl.to({}, { duration: d == null ? 0.9 : d }); return tl; }

  var B = {};                                    // builders: (box, o, tl) -> nothing; they add to tl

  B["fade-up"] = function (b, o, tl) {
    var w = words(E("div", "", null), o.text); var line = w[0].parentNode; b.appendChild(line);
    tl.from(w, { y: o.fs * 0.6, opacity: 0, duration: 0.7, ease: "power3.out", stagger: 0.09 });
  };
  B["typewriter"] = function (b, o, tl) {
    var wrap = E("div", "position:relative;font-weight:500;white-space:nowrap"); b.appendChild(wrap);
    wrap.appendChild(E("span", "visibility:hidden", o.text + "\u2003"));
    var line = E("div", "position:absolute;left:0;top:0;white-space:nowrap"); wrap.appendChild(line);
    var c = chars(line, o.text);
    var caret = E("span", "display:inline-block;width:.08em;height:1em;margin-left:.04em;vertical-align:-0.12em;background:" + o.accent);
    line.appendChild(caret);
    tl.set(c, { display: "none" });
    tl.to(c, { display: "inline-block", duration: 0.001, stagger: 0.07 }, 0.2);
    tl.to(caret, { opacity: 0, duration: 0.01, repeat: 5, yoyo: true, repeatDelay: 0.35 });
  };
  B["pop-in"] = function (b, o, tl) {
    var w = words(E("div"), o.text); b.appendChild(w[0].parentNode);
    w.forEach(function (x, i) { if (i === 1) x.style.color = o.accent; });
    tl.from(w, { scale: 0, opacity: 0, duration: 0.55, ease: "back.out(2.6)", stagger: 0.16 });
  };
  B["mask-reveal"] = function (b, o, tl) {
    var parts = o.text.split(" "), mid = Math.ceil(parts.length / 2), inner = [];   // "a|b" sets the lines; short copy stays on one
    var lines = o.text.indexOf("|") >= 0 ? o.text.split("|").filter(Boolean) : parts.length <= 4 ? [o.text] : [parts.slice(0, mid).join(" "), parts.slice(mid).join(" ")];
    lines.forEach(function (t) {
      var l = E("span", "", null, "tfx-line"), i = E("span", "", t, "tfx-i"); l.appendChild(i); b.appendChild(l); inner.push(i);
    });
    tl.from(inner, { yPercent: 115, duration: 0.8, ease: "power4.out", stagger: 0.14 });
  };
  B["blur-in"] = function (b, o, tl) {
    var line = E("div", "font-weight:600"); b.appendChild(line);
    var c = chars(line, o.text);
    tl.from(c, { opacity: 0, filter: "blur(" + Math.round(o.fs * 0.3) + "px)", scale: 1.25, duration: 0.8, ease: "power2.out", stagger: 0.035 });
  };
  B["scramble"] = function (b, o, tl) {
    var line = E("div", "font-family:ui-monospace,Menlo,monospace;font-weight:700;color:" + o.accent); b.appendChild(line);
    var finalT = o.text, glyphs = "#&$%@*!?<>/=+", r = seeded(7), table = [];
    for (var k = 0; k < 600; k++) table.push(glyphs[Math.floor(r() * glyphs.length)]);
    var p = { v: 0 };
    tl.to(p, { v: 1, duration: 1.6, ease: "none", onUpdate: function () {
      var step = Math.floor(p.v * 30), out = "";
      for (var i = 0; i < finalT.length; i++) {
        var done = p.v >= (i + 1) / finalT.length * 0.92 + 0.08;
        out += finalT[i] === " " ? " " : done ? finalT[i] : table[(step * 13 + i * 7) % table.length];
      }
      line.textContent = out;
    } });
  };
  B["write-on"] = function (b, o, tl) {
    var w = o.W * 0.86, h = o.fs * 2.2;
    var svg = '<svg width="' + w + '" height="' + h + '" viewBox="0 0 ' + w + " " + h + '" style="overflow:visible">' +
      '<text x="50%" y="' + (h * 0.62) + '" text-anchor="middle" style="font:italic 600 ' + Math.round(o.fs * 1.1) + 'px Georgia,serif" ' +
      'fill="' + o.ink + '" fill-opacity="0" stroke="' + o.ink + '" stroke-width="1.6" stroke-dasharray="900" stroke-dashoffset="900">' + o.text + '</text>' +
      '<line x1="4%" x2="96%" y1="' + (h * 0.86) + '" y2="' + (h * 0.86) + '" stroke="' + o.ink + '" stroke-opacity=".35" stroke-width="1.5"/>' +
      '<text x="3%" y="' + (h * 0.8) + '" style="font:500 ' + Math.round(o.fs * 0.35) + 'px sans-serif" fill="' + o.ink + '" fill-opacity=".5">x</text></svg>';
    b.innerHTML = svg;
    var t = b.querySelector("text");
    tl.to(t, { attr: { "stroke-dashoffset": 0 }, duration: 1.6, ease: "power1.inOut" });
    tl.to(t, { attr: { "fill-opacity": 1, "stroke-opacity": 0 }, duration: 0.4 }, "-=0.2");
  };
  B["scatter-in"] = function (b, o, tl) {
    var line = E("div"); b.appendChild(line);
    var c = chars(line, o.text), r = seeded(11);
    c.forEach(function (x, i) { if (i % 4 === 1) x.style.color = o.accent; });
    tl.from(c, { x: function () { return (r() - 0.5) * o.W * 0.9; }, y: function () { return (r() - 0.5) * o.H * 0.9; },
      rotation: function () { return (r() - 0.5) * 140; }, opacity: 0, duration: 1.0, ease: "power3.out", stagger: 0.03 });
  };
  B["stamp"] = function (b, o, tl) {
    var s = E("div", "padding:.12em .4em;border:" + Math.max(3, o.fs * 0.07) + "px solid " + o.accent + ";color:" + o.accent +
      ";border-radius:.12em;font-weight:800;letter-spacing:.06em;transform:rotate(-8deg)", o.text);
    b.appendChild(s);
    tl.from(s, { scale: 3, opacity: 0, duration: 0.32, ease: "power4.in" });
    tl.to(s, { x: 5, duration: 0.04, repeat: 5, yoyo: true, ease: "none" });
    tl.to(s, { x: 0, duration: 0.04 });
  };
  B["drop-in"] = function (b, o, tl) {
    var line = E("div"); b.appendChild(line);
    var c = chars(line, o.text);
    tl.from(c, { y: -o.H * 0.75, opacity: 0, duration: 0.9, ease: "bounce.out", stagger: 0.06 });
  };
  B["tilt-reveal"] = function (b, o, tl) {
    var w = words(E("div", "perspective:" + (o.fs * 8) + "px"), o.text); b.appendChild(w[0].parentNode);
    tl.from(w, { rotationX: -95, opacity: 0, transformOrigin: "50% 100%", duration: 0.8, ease: "power3.out", stagger: 0.14 });
  };
  B["behind-subject"] = function (b, o, tl) {
    b.style.background = o.accent2;
    var big = E("div", "position:absolute;left:0;right:0;top:12%;font-weight:900;font-size:" + (o.fs * 2.6) + "px;color:" + o.ink + ";letter-spacing:-.02em", o.text);
    var person = E("div", "position:absolute;left:50%;bottom:0;width:" + (o.H * 0.5) + "px;height:" + (o.H * 0.66) + "px;transform:translateX(-50%)",
      '<svg viewBox="0 0 100 130" width="100%" height="100%"><circle cx="50" cy="34" r="22" fill="' + o.accent + '"/>' +
      '<path d="M8 130 C8 82 26 64 50 64 C74 64 92 82 92 130 Z" fill="' + o.accent + '"/></svg>');
    b.appendChild(big); b.appendChild(person);
    tl.from(person, { yPercent: 40, opacity: 0, duration: 0.6, ease: "power3.out" });
    tl.from(big, { yPercent: 70, duration: 0.9, ease: "power4.out" }, 0.25);
  };
  B["highlight"] = function (b, o, tl) {
    var parts = o.text.split(" "), last = parts.splice(-2).join(" ");
    var line = E("div", "", parts.join(" ") + " "); b.appendChild(line);
    var mark = E("span", "position:relative;display:inline-block;padding:0 .1em");
    var bar = E("span", "position:absolute;left:0;right:0;top:.18em;bottom:.02em;background:" + o.accent2 + ";transform-origin:0 50%;z-index:0");
    var t = E("span", "position:relative;z-index:1", last);
    mark.appendChild(bar); mark.appendChild(t); line.appendChild(mark);
    tl.from(line, { opacity: 0, y: o.fs * 0.3, duration: 0.5, ease: "power2.out" });
    tl.from(bar, { scaleX: 0, duration: 0.6, ease: "power2.inOut" }, "+=0.15");
  };
  B["tracking-out"] = function (b, o, tl) {
    var t = E("div", "font-weight:600;white-space:nowrap;font-size:" + (o.fs * 0.85) + "px", o.text); b.appendChild(t);
    tl.fromTo(t, { letterSpacing: "-0.06em", opacity: 0 }, { letterSpacing: "0.1em", opacity: 1, duration: 1.6, ease: "power2.out" });
  };
  B["strikethrough"] = function (b, o, tl) {
    var p = o.text.split("|");
    var line = E("div", "white-space:nowrap"); b.appendChild(line);
    var old = E("span", "position:relative;display:inline-block;color:" + o.ink, p[0]);
    var strike = E("span", "position:absolute;left:-4%;right:-4%;top:52%;height:.09em;background:" + o.accent + ";transform-origin:0 50%");
    old.appendChild(strike);
    var nu = E("span", "display:inline-block;margin-left:.3em;color:" + o.accent, p[1]);
    line.appendChild(old); line.appendChild(nu);
    tl.from(old, { opacity: 0, duration: 0.3 });
    tl.from(strike, { scaleX: 0, duration: 0.45, ease: "power2.inOut" }, "+=0.3");
    tl.to(old, { opacity: 0.45, duration: 0.3 });
    tl.from(nu, { y: o.fs * 0.6, opacity: 0, duration: 0.5, ease: "back.out(2)" }, "-=0.1");
  };
  B["hand-circle"] = function (b, o, tl) {
    var parts = o.text.split(" "), key = parts.pop();
    var line = E("div", "white-space:nowrap", parts.join(" ") + " "); b.appendChild(line);
    var k = E("span", "position:relative;display:inline-block;padding:0 .15em", key);
    k.insertAdjacentHTML("beforeend", '<svg viewBox="0 0 100 50" preserveAspectRatio="none" style="position:absolute;left:-14%;top:-30%;width:128%;height:160%;overflow:visible">' +
      '<path pathLength="1" d="M70 6 C40 0 6 8 5 26 C4 44 40 49 66 46 C92 43 99 30 94 17 C89 6 62 2 44 6" fill="none" stroke="' + o.accent +
      '" stroke-width="3.2" stroke-linecap="round" stroke-dasharray="1" stroke-dashoffset="1" vector-effect="non-scaling-stroke"/></svg>');
    line.appendChild(k);
    tl.from(line, { opacity: 0, duration: 0.4 });
    tl.to(k.querySelector("path"), { attr: { "stroke-dashoffset": 0 }, duration: 0.9, ease: "power2.inOut" }, "+=0.2");
  };
  B["shimmer"] = function (b, o, tl) {
    var t = E("div", "font-weight:700;background:linear-gradient(100deg," + o.ink + " 40%," + o.accent2 + " 50%," + o.ink +
      " 60%);background-size:300% 100%;-webkit-background-clip:text;background-clip:text;color:transparent", o.text);
    b.appendChild(t);
    tl.from(t, { opacity: 0, duration: 0.4 });
    tl.fromTo(t, { backgroundPosition: "100% 0" }, { backgroundPosition: "0% 0", duration: 1.3, ease: "power1.inOut", repeat: 1 });
  };
  B["squash-stretch"] = function (b, o, tl) {
    var line = E("div"); b.appendChild(line);
    var c = chars(line, o.text);
    c.forEach(function (x) { x.style.transformOrigin = "50% 100%"; });
    c.forEach(function (x, i) {
      var t0 = i * 0.08;
      tl.fromTo(x, { y: -o.fs * 1.4, scaleY: 1.35, scaleX: 0.8, opacity: 0 }, { y: 0, opacity: 1, duration: 0.42, ease: "power2.in" }, t0);
      tl.to(x, { scaleY: 0.65, scaleX: 1.3, duration: 0.09, ease: "power1.out" }, t0 + 0.42);
      tl.to(x, { scaleY: 1, scaleX: 1, duration: 0.35, ease: "elastic.out(1,0.4)" }, t0 + 0.51);
    });
  };
  B["wave"] = function (b, o, tl) {
    var line = E("div"); b.appendChild(line);
    var c = chars(line, o.text), p = { t: 0 };
    tl.from(line, { opacity: 0, duration: 0.3 }, 0);
    tl.to(p, { t: Math.PI * 4, duration: 2.4, ease: "none", onUpdate: function () {
      c.forEach(function (x, i) { x.style.transform = "translateY(" + (Math.sin(p.t - i * 0.7) * o.fs * 0.22).toFixed(2) + "px)"; });
    } }, 0);
  };
  B["variable-weight"] = function (b, o, tl) {
    var t = E("div", "font-weight:300;color:" + o.ink + ";-webkit-text-stroke:0px " + o.ink, o.text); b.appendChild(t);
    var track = E("div", "position:relative;width:46%;height:3px;margin-top:.5em;background:" + o.ink + "22;border-radius:2px");
    var dot = E("div", "position:absolute;left:0;top:-5px;width:13px;height:13px;margin-left:-6px;border-radius:50%;background:" + o.ink);
    track.appendChild(dot); b.appendChild(track);
    tl.from([t, track], { opacity: 0, duration: 0.3 });
    tl.to(t, { webkitTextStroke: (o.fs * 0.075).toFixed(1) + "px " + o.ink, scale: 1.06, duration: 1.4, ease: "power2.inOut" });
    tl.to(dot, { left: "100%", duration: 1.4, ease: "power2.inOut" }, "<");
  };
  B["whip-in"] = function (b, o, tl) {
    var t = E("div", "font-weight:800;font-style:italic;color:" + o.accent, o.text); b.appendChild(t);
    tl.from(t, { x: -o.W, skewX: 40, filter: "blur(10px)", duration: 0.5, ease: "expo.out" });
    tl.to(t, { skewX: -8, duration: 0.12, ease: "power1.out" }, 0.35).to(t, { skewX: 0, duration: 0.3, ease: "elastic.out(1,0.5)" });
  };
  B["bouncing-dot"] = function (b, o, tl) {
    var line = E("div", "position:relative;white-space:nowrap"); b.appendChild(line);
    var w = words(line, o.text, " ");
    var dot = E("div", "position:absolute;left:0;top:0;width:" + (o.fs * 0.26) + "px;height:" + (o.fs * 0.26) + "px;border-radius:50%;background:" + o.accent);
    line.appendChild(dot);
    var cx = function (i) { return function () { return w[i].offsetLeft + w[i].offsetWidth / 2 - o.fs * 0.13; }; };
    tl.set(dot, { x: cx(0), y: -o.fs * 1.6 });
    w.forEach(function (x, i) {
      var t0 = 0.15 + i * 0.6;
      tl.to(dot, { x: cx(i), duration: 0.5, ease: "none" }, t0);
      tl.to(dot, { y: -o.fs * 0.55, duration: 0.25, ease: "power2.in" }, t0 + 0.25);
      if (i < w.length - 1) tl.to(dot, { y: -o.fs * 1.4, duration: 0.3, ease: "power2.out" }, t0 + 0.5);
      tl.to(x, { color: o.accent, duration: 0.15 }, t0 + 0.47);
    });
  };
  B["float"] = function (b, o, tl) {
    var list = o.text.split("|"), pos = [[22, 26], [70, 22], [48, 50], [18, 74], [76, 70], [52, 84]];
    list.forEach(function (wd, i) {
      var p = pos[i % pos.length];
      var s = E("div", "position:absolute;left:" + p[0] + "%;top:" + p[1] + "%;transform:translate(-50%,-50%);font-size:" + (o.fs * (i % 3 === 2 ? 0.8 : 0.62)) +
        "px;font-weight:" + (i % 2 ? 800 : 600) + ";color:" + (i % 3 === 0 ? o.accent : o.ink), wd);
      b.appendChild(s);
      tl.from(s, { opacity: 0, scale: 0.6, duration: 0.5, ease: "back.out(2)" }, i * 0.09);
      tl.to(s, { y: (i % 2 ? -1 : 1) * o.fs * 0.18, rotation: (i % 2 ? 4 : -4), duration: 1.1 + i * 0.12, yoyo: true, repeat: 1, ease: "sine.inOut" }, 0.5);
    });
  };
  B["tracking-in"] = function (b, o, tl) {
    b.style.background = o.accent2;
    var t = E("div", "font-weight:800;white-space:nowrap;color:" + o.ink, o.text); b.appendChild(t);
    tl.fromTo(t, { letterSpacing: "1.1em", opacity: 0, filter: "blur(6px)" }, { letterSpacing: "0.02em", opacity: 1, filter: "blur(0px)", duration: 1.3, ease: "power3.out" });
  };
  B["text-flip"] = function (b, o, tl) {
    var p = o.text.split("|"), lead = p.shift();
    var line = E("div", "font-weight:600;display:flex;flex-direction:column;align-items:center;gap:.25em", lead); b.appendChild(line);
    var box = E("div", "position:relative;width:" + (o.W * 0.6) + "px;height:1.35em;perspective:" + (o.fs * 6) + "px;border:2px dashed " + o.accent +
      ";border-radius:.18em;color:" + o.accent);
    line.appendChild(box);
    var items = p.map(function (t) { var s = E("div", "position:absolute;inset:0;display:flex;align-items:center;justify-content:center;backface-visibility:hidden", t); box.appendChild(s); return s; });
    tl.set(items.slice(1), { rotationX: -90, opacity: 0 });
    tl.from(line, { opacity: 0, y: o.fs * 0.3, duration: 0.4 });
    for (var i = 0; i < items.length - 1; i++) {
      var at = 0.9 + i * 0.95;
      tl.to(items[i], { rotationX: 90, opacity: 0, duration: 0.35, ease: "power2.in" }, at);
      tl.to(items[i + 1], { rotationX: 0, opacity: 1, duration: 0.35, ease: "power2.out" }, at + 0.25);
    }
  };
  B["word-carousel"] = function (b, o, tl) {
    var p = o.text.split("|"), lead = p.shift(), lh = o.fs * 1.25;
    var row = E("div", "display:flex;align-items:center;gap:.3em;font-weight:600"); b.appendChild(row);
    row.appendChild(E("span", "", lead));
    var win = E("div", "position:relative;height:" + (lh * 3) + "px;overflow:hidden;text-align:left;-webkit-mask-image:linear-gradient(transparent,#000 30%,#000 70%,transparent)");
    var col = E("div", "position:relative;top:" + lh + "px");
    var items = p.map(function (t) { var s = E("div", "height:" + lh + "px;line-height:" + lh + "px;color:" + o.ink + ";opacity:.35", t); col.appendChild(s); return s; });
    win.appendChild(col); row.appendChild(win);
    tl.set(items[0], { color: o.accent, opacity: 1 });
    for (var i = 1; i < items.length; i++) {
      var at = 0.6 + (i - 1) * 0.75;
      tl.to(col, { y: -lh * i, duration: 0.45, ease: "power3.inOut" }, at);
      tl.to(items[i - 1], { color: o.ink, opacity: 0.35, duration: 0.3 }, at);
      tl.to(items[i], { color: o.accent, opacity: 1, duration: 0.3 }, at + 0.15);
    }
  };
  B["color-shift"] = function (b, o, tl) {
    var line = E("div", "font-weight:900;letter-spacing:.02em"); b.appendChild(line);
    var c = chars(line, o.text), pal = [o.accent, o.accent2, o.accent3, o.accent4];
    c.forEach(function (x, i) { x.style.color = pal[i % pal.length]; });
    tl.from(c, { opacity: 0, y: o.fs * 0.3, duration: 0.4, stagger: 0.04 });
    for (var k = 1; k <= 4; k++) {
      (function (k) { tl.to(c, { color: function (i) { return pal[(i + k) % pal.length]; }, duration: 0.25, stagger: 0.04 }, 0.4 + k * 0.45); })(k);
    }
  };
  B["marquee"] = function (b, o, tl) {
    var p = o.text.split("|"); b.style.justifyContent = "space-evenly";
    for (var r = 0; r < 4; r++) {
      var light = r % 2 === 0, t = (p[r % p.length] + "  ").repeat(6);
      var row = E("div", "white-space:pre;font-weight:900;font-size:" + (o.H * 0.2) + "px;line-height:1;padding:.02em 0;width:max-content;background:" +
        (light ? o.accent2 : o.ink) + ";color:" + (light ? o.ink : o.paper), t);
      b.appendChild(row);
      tl.fromTo(row, { xPercent: r % 2 ? -50 : 0 }, { xPercent: r % 2 ? 0 : -50, duration: 6, ease: "none" }, 0);
    }
  };
  B["oversized-crop"] = function (b, o, tl) {
    var t = E("div", "position:absolute;left:0;top:50%;white-space:nowrap;font-weight:900;line-height:.8;font-size:" + (o.H * 1.05) +
      "px;color:" + o.ink + ";transform:translateY(-50%)", o.text);
    b.appendChild(t);
    tl.fromTo(t, { x: o.W * 0.15 }, { x: function () { return -(t.offsetWidth - o.W * 0.85); }, duration: 3, ease: "power1.inOut" });
  };
  B["text-path"] = function (b, o, tl) {
    var id = "tfx-p" + Math.floor(o.uid * 1e6);
    b.innerHTML = '<svg viewBox="0 0 300 140" width="92%" height="92%" style="overflow:visible"><path id="' + id + '" d="M10 120 C 80 10, 220 10, 290 120" fill="none" stroke="' +
      o.accent2 + '" stroke-width="2"/><text style="font:600 17px ' + o.font + '" fill="' + o.ink + '"><textPath href="#' + id + '" startOffset="100%">' + o.text + '</textPath></text></svg>';
    tl.fromTo(b.querySelector("textPath"), { attr: { startOffset: "100%" } }, { attr: { startOffset: "4%" }, duration: 2.6, ease: "power2.out" });
    tl.from(b.querySelector("path"), { opacity: 0, duration: 0.4 }, 0);
  };
  B["shape-morph"] = function (b, o, tl) {
    var s = E("div", "display:flex;align-items:center;justify-content:center;width:" + (o.fs * 1.2) + "px;height:" + (o.fs * 1.2) +
      "px;border-radius:50%;background:" + o.accent + ";color:" + o.paper + ";font-weight:600;font-size:" + (o.fs * 0.6) + "px;overflow:hidden;white-space:nowrap");
    var t = E("span", "opacity:0", o.text); s.appendChild(t); b.appendChild(s);
    tl.from(s, { scale: 0, duration: 0.4, ease: "back.out(2)" });
    tl.to(s, { y: -o.fs * 0.5, duration: 0.25, ease: "power2.out" }).to(s, { y: 0, duration: 0.3, ease: "bounce.out" });
    tl.to(s, { width: o.W * 0.62, height: o.fs * 1.15, borderRadius: o.fs * 0.6, duration: 0.6, ease: "power3.inOut" });
    tl.to(t, { opacity: 1, duration: 0.3 }, "-=0.15");
  };
  B["extrude-3d"] = function (b, o, tl) {
    var t = E("div", "font-weight:900;color:" + o.accent + ";letter-spacing:.02em", o.text); b.appendChild(t);
    var p = { d: 0 }, dark = o.ink;
    tl.from(t, { scale: 0.7, opacity: 0, duration: 0.4, ease: "back.out(2)" });
    tl.to(p, { d: Math.round(o.fs * 0.16), duration: 0.9, ease: "power2.out", onUpdate: function () {
      var s = []; for (var i = 1; i <= Math.round(p.d); i++) s.push(i + "px " + i + "px 0 " + dark);
      t.style.textShadow = s.join(","); t.style.transform = "translate(" + (-p.d / 2) + "px," + (-p.d / 2) + "px)";
    } });
  };
  B["zoom-through"] = function (b, o, tl) {
    var p = o.text.split("|");
    var a = E("div", "font-weight:900;color:" + o.accent + ";transform-origin:58% 52%", p[0]);
    var c = E("div", "position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-weight:800;color:" + o.paper, p[1]);
    b.appendChild(a); b.appendChild(c);
    tl.set(c, { opacity: 0, scale: 0.6 });
    tl.from(a, { opacity: 0, duration: 0.3 });
    tl.to(a, { scale: 36, duration: 1.1, ease: "power3.in" }, "+=0.35");
    tl.to(b, { backgroundColor: o.accent, duration: 0.25 }, "-=0.3");
    tl.to(c, { opacity: 1, scale: 1, duration: 0.45, ease: "power2.out" }, "-=0.2");
  };
  B["invert"] = function (b, o, tl) {
    b.style.background = o.paper;
    var t = E("div", "font-weight:800;color:" + o.ink, o.text); b.appendChild(t);
    var circ = E("div", "position:absolute;left:12%;top:50%;width:" + (o.H * 0.5) + "px;height:" + (o.H * 0.5) + "px;margin:-" + (o.H * 0.25) + "px 0 0 -" + (o.H * 0.25) +
      "px;border-radius:50%;background:#fff;mix-blend-mode:difference");
    b.appendChild(circ);
    tl.from(circ, { scale: 0, duration: 0.4, ease: "back.out(2)" });
    tl.to(circ, { left: "88%", duration: 1.2, ease: "power2.inOut" });
    tl.to(circ, { scale: 5, duration: 0.6, ease: "power2.in" });
  };
  B["reflection"] = function (b, o, tl) {
    var wrap = E("div", "position:relative");
    var t = E("div", "font-weight:800;color:" + o.ink, o.text);
    var r = E("div", "position:absolute;left:0;right:0;top:100%;font-weight:800;color:" + o.ink + ";transform:scaleY(-1);transform-origin:50% 0;opacity:.32;" +
      "-webkit-mask-image:linear-gradient(to top,#000,transparent 70%);mask-image:linear-gradient(to top,#000,transparent 70%)", o.text);
    wrap.appendChild(t); wrap.appendChild(r); b.appendChild(wrap);
    tl.from(t, { yPercent: 60, opacity: 0, duration: 0.8, ease: "power3.out" });
    tl.from(r, { yPercent: -60, opacity: 0, duration: 0.8, ease: "power3.out" }, 0);
  };
  B["repeater"] = function (b, o, tl) {
    var n = 6, items = [];
    for (var i = n - 1; i >= 0; i--) {
      var last = i === 0;
      var s = E("div", "position:absolute;font-weight:900;color:" + (last ? o.accent : "transparent") + ";-webkit-text-stroke:" + (last ? 0 : 1.4) + "px " + o.accent +
        ";opacity:" + (last ? 1 : 0.85 - i * 0.12), o.text);
      b.appendChild(s); items[i] = s;
    }
    tl.from(items[0], { scale: 0.6, opacity: 0, duration: 0.4, ease: "back.out(2)" });
    tl.fromTo(items.slice(1), { y: 0, opacity: 0 }, { y: function (i) { return -(i + 1) * o.fs * 0.32; }, opacity: function (i) { return 0.8 - i * 0.13; }, duration: 0.7, ease: "power3.out", stagger: 0.05 });
    tl.to(items.slice(1), { y: function (i) { return (i + 1) * o.fs * 0.32; }, duration: 0.9, ease: "sine.inOut", stagger: 0.04 }, "+=0.2");
  };
  B["inline-images"] = function (b, o, tl) {
    var p = o.text.split("|"), line = E("div", "display:flex;align-items:center;gap:.25em;font-weight:700;flex-wrap:nowrap;font-size:" + (o.fs * 0.7) + "px"); b.appendChild(line);
    var pics = [], icons = ['<rect x="6" y="18" width="28" height="10" rx="4"/><rect x="6" y="10" width="14" height="12" rx="4"/>',
      '<rect x="7" y="13" width="26" height="20" rx="4"/><path d="M14 13 a6 6 0 0 1 12 0" fill="none" stroke="currentColor" stroke-width="3"/>',
      '<path d="M12 22 L28 22 L24 10 L16 10 Z"/><rect x="19" y="22" width="2" height="9"/><rect x="13" y="31" width="14" height="3" rx="1"/>'];
    p.forEach(function (w, i) {
      var word = E("span", "", w, "tfx-i"); line.appendChild(word);
      var pic = E("span", "display:inline-flex;align-items:center;justify-content:center;width:1em;height:.9em;border-radius:.22em;background:" +
        [o.accent2, o.accent3, o.accent4][i % 3] + ";color:" + o.ink, '<svg viewBox="0 0 40 40" width="70%" height="70%" fill="currentColor">' + icons[i % 3] + "</svg>");
      line.appendChild(pic); pics.push([word, pic]);
    });
    pics.forEach(function (wp, i) {
      tl.from(wp[0], { opacity: 0, y: o.fs * 0.3, duration: 0.35 }, i * 0.4);
      tl.from(wp[1], { scale: 0, rotation: -20, duration: 0.45, ease: "back.out(2.5)" }, i * 0.4 + 0.2);
    });
  };
  B["tracked-callout"] = function (b, o, tl) {
    b.style.background = o.paper;
    var subj = E("div", "position:absolute;left:0;top:0;width:" + (o.H * 0.24) + "px;height:" + (o.H * 0.24) + "px;margin:-" + (o.H * 0.12) + "px;border-radius:50%;background:" + o.ink + "44;border:3px solid " + o.accent);
    var line = E("div", "position:absolute;left:0;top:0;width:" + (o.W * 0.12) + "px;height:2px;background:" + o.accent + ";transform-origin:0 50%;transform:rotate(-30deg)");
    var tag = E("div", "position:absolute;left:0;top:0;padding:.25em .6em;border-radius:.4em;white-space:nowrap;font-weight:600;font-size:" + (o.fs * 0.42) + "px;background:" + o.accent + ";color:" + o.paper, o.text);
    b.appendChild(subj); b.appendChild(line); b.appendChild(tag);
    var path = [[0.18, 0.72], [0.34, 0.56], [0.46, 0.74], [0.28, 0.8]], p = { t: 0 };
    function at(t) {
      var seg = Math.min(path.length - 2, Math.floor(t * (path.length - 1))), u = t * (path.length - 1) - seg;
      return [path[seg][0] + (path[seg + 1][0] - path[seg][0]) * u, path[seg][1] + (path[seg + 1][1] - path[seg][1]) * u];
    }
    function place() {
      var q = at(p.t), x = q[0] * o.W, y = q[1] * o.H;
      subj.style.transform = "translate(" + x + "px," + y + "px)";
      line.style.left = (x + o.H * 0.1) + "px"; line.style.top = (y - o.H * 0.06) + "px";
      tag.style.transform = "translate(" + (x + o.H * 0.1 + o.W * 0.1) + "px," + (y - o.H * 0.06 - o.W * 0.06 - o.fs * 0.6) + "px)";
    }
    place();
    tl.from([subj, line, tag], { opacity: 0, duration: 0.3, stagger: 0.12 });
    tl.to(p, { t: 1, duration: 2.4, ease: "sine.inOut", onUpdate: place }, 0.2);
  };
  B["karaoke"] = function (b, o, tl) {
    var line = E("div", "max-width:90%;font-weight:700;line-height:1.25;padding:.2em .4em;border-radius:.3em;background:" + o.ink + "E6;color:#ffffff66;font-size:" + (o.base * 0.62) + "px"); b.appendChild(line);
    var w = words(line, o.text);
    tl.from(line, { opacity: 0, y: o.fs * 0.3, duration: 0.3 });
    w.forEach(function (x, i) { tl.to(x, { color: i % 4 === 3 ? o.accent2 : "#ffffff", duration: 0.08 }, 0.35 + i * 0.28); });
  };
  B["text-mask"] = function (b, o, tl) {
    var t = E("div", "font-weight:900;line-height:.9;font-size:" + (o.fs * 2.2) + "px;background:repeating-linear-gradient(115deg," + o.accent + " 0 18px," +
      o.accent2 + " 18px 36px," + o.accent3 + " 36px 54px);background-size:200% 200%;-webkit-background-clip:text;background-clip:text;color:transparent", o.text);
    b.appendChild(t);
    tl.from(t, { scale: 0.85, opacity: 0, duration: 0.5, ease: "power2.out" });
    tl.fromTo(t, { backgroundPosition: "0% 0%" }, { backgroundPosition: "100% 100%", duration: 2.4, ease: "none" }, 0);
  };
  B["chat-bubbles"] = function (b, o, tl) {
    var p = o.text.split("|"), col = E("div", "width:86%;display:flex;flex-direction:column;gap:.35em;font-size:" + (o.base * 0.5) + "px;font-weight:500"); b.appendChild(col);
    p.forEach(function (m, i) {
      var me = i % 2 === 0;
      var bub = E("div", "align-self:" + (me ? "flex-end" : "flex-start") + ";padding:.45em .8em;border-radius:1em;" + (me ? "border-bottom-right-radius:.25em;" : "border-bottom-left-radius:.25em;") +
        "background:" + (me ? o.accent : o.ink + "14") + ";color:" + (me ? o.paper : o.ink) + ";transform-origin:" + (me ? "100% 100%" : "0 100%"), m);
      col.appendChild(bub);
      tl.from(bub, { scale: 0, opacity: 0, duration: 0.4, ease: "back.out(2)" }, i * 0.85 + 0.35);
    });
  };
  B["counter"] = function (b, o, tl) {
    var p = o.text.split("|"), goal = parseFloat(p[1]), fmt = p[2] || "$#K";   // "label|48.2|$#K": # is the number
    var dec = (String(p[1]).split(".")[1] || "").length;
    function show(x) { return fmt.replace("#", x.toFixed(dec)); }
    b.appendChild(E("div", "font-size:" + (o.fs * 0.32) + "px;font-weight:500;color:" + o.ink + "99;letter-spacing:.04em", p[0]));
    var n = E("div", "font-weight:800;font-variant-numeric:tabular-nums;color:" + o.ink, show(0)); b.appendChild(n);
    var bar = E("div", "width:56%;height:.14em;margin-top:.25em;border-radius:1em;background:" + o.accent + ";transform-origin:0 50%"); b.appendChild(bar);
    var v = { x: 0 };
    tl.from(b.children, { opacity: 0, y: o.fs * 0.2, duration: 0.3, stagger: 0.08 });
    tl.to(v, { x: goal, duration: 1.6, ease: "power2.out", onUpdate: function () { n.textContent = show(v.x); } }, 0.2);
    tl.from(bar, { scaleX: 0, duration: 1.6, ease: "power2.out" }, 0.2);
  };

  var uid = 0;
  function build(stage, id, opts) {
    if (!root.gsap) throw new Error("text-fx.js needs GSAP on the page");
    if (!B[id]) throw new Error("unknown text animation: " + id);
    css();
    var meta = LIST.filter(function (x) { return x[0] === id; })[0];
    var W = stage.clientWidth || 300, H = stage.clientHeight || 200;
    var o = Object.assign({ text: meta[3], ink: "#0F172A", accent: "#4F46E5", accent2: "#7DD3FC", accent3: "#F9A8D4", accent4: "#FBBF24",
      paper: "#FFFFFF", font: "Poppins, system-ui, sans-serif", weight: 700 }, opts || {});
    o.W = W; o.H = H; o.uid = ++uid / 1000 + 0.0001;
    var longest = String(o.text).split(/[|\n]/).reduce(function (m, x) { return Math.max(m, x.length); }, 1);
    o.base = o.size || Math.round(Math.min(W * 0.1, H * 0.22));         // for copy that wraps (captions, chat)
    o.fs = o.size || Math.min(o.base, Math.round(W * 0.88 / (longest * 0.6)));   // one line that must fit
    stage.innerHTML = ""; stage.classList.add("tfx-stage");
    var box = E("div", "font-family:" + o.font + ";font-weight:" + o.weight + ";font-size:" + o.fs + "px;color:" + o.ink, null, "tfx-box");
    stage.appendChild(box);
    var tl = root.gsap.timeline({ paused: true });
    B[id](box, o, tl);
    hold(tl, o.hold);
    return { tl: tl, dur: tl.duration() };
  }
  root.TextFX = {
    build: build,
    ids: LIST.map(function (x) { return x[0]; }),
    list: LIST.map(function (x, i) { return { n: i + 1, id: x[0], name: x[1], category: x[2], sample: x[3], use: x[4] }; }),
    categories: CATS
  };
})(typeof window !== "undefined" ? window : this);
