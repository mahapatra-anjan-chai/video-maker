---
name: text-animations
description: 57 animations for product videos: 45 for text (fade up, typewriter, mask reveal, text scramble, highlight, hand-drawn circle, shimmer, word carousel, accent words, roll list, typed prompt, marquee, 3D extrude, zoom through, karaoke captions, chat bubbles, counter and more), cards and cursors (card cloud, notification stack, chips into a card, a labelled cursor tour), eight transitions between scenes (pixel dissolve, blur swap, wipe, iris, whip pan, push, zoom, glitch) and an animated halftone background in any look's colours, with a live picker shown before a video starts so the creator chooses the motion by sight, and a scene planner that plays each scene's own line with its animation, the transition into the next scene and the background, in the video's colours, so the creator picks per scene in the chat. Use whenever a video gets headlines, titles, captions, callouts, on-screen copy, product UI moments or scene changes; when the creator asks for "text animation", "animated text", "kinetic type", "make the headline pop", "which animations"; "which transition", "plan the scenes"; and at the start of every video (the picker or planner step). Works in fast-cut cut lists ("anim") and in HyperFrames compositions (text-fx.js).
---

# Text animations

One library, `text-fx.js`, drives everything: the picker, the preview gallery and the renders. Each animation is a GSAP
timeline that is paused, deterministic and seek-safe (no Math.random, CSS animations or timers), so what the creator picks
in the preview is exactly what HyperFrames renders. Run commands from the project folder with
`TA=".claude/skills/text-animations"`.

## Before every video: show the picker

Right after the Personal / Work and look questions, before any cut list or storyboard:

1. **If the `show_widget` tool is available** (Claude desktop and web): call `read_me` (module `interactive`) once,
   then `show_widget` with the contents of `$TA/picker.widget.html` as `widget_code` (title `text_animation_picker`).
   It shows a dropdown of the seven groups ("Which kind of text animation?") over live, looping previews of all 57, and
   below them the backgrounds (halftone light, halftone dark, plain, drawn live); the creator taps the ones they want
   and presses "Use the picked animations", which sends you a line like
   `Text animations for this video: 01 Fade up (fade-up), 13 Highlight (highlight); background: halftone-light`.
   Regenerate the file with `python3 $TA/scripts/tfx.py picker` whenever `text-fx.js` changed.
2. **Otherwise** (no in-chat widget): send `$TA/preview/preview.png` and `$TA/preview/text-animations.mp4` with SendUserFile
   (the numbered gallery; refresh it with `python3 $TA/scripts/tfx.py gallery --out $TA/preview`), then ask with
   AskUserQuestion, multi-select, "Which text animation style for this video?":
   - **Clean** (fade up, mask reveal, accent words, roll list, highlight, blur swap): launches, B2B, most product explainers
   - **Playful** (pop in, drop in, squash and stretch, wave, float): consumer apps, social
   - **Bold** (stamp, tracking in, marquee, oversized crop, 3D extrude): announcements, events, ads
   - **Product UI** (typed prompt, cursor tour, card cloud, notification stack, chat bubbles, counter, pixel dissolve):
     demos, AI and data features
   "Other" lets them name numbers from the gallery.
3. Write the answer into `brief.json` as `"text_animations": ["fade-up", "highlight"]` and use only those (plus plain
   fades) for the video's copy. Say which line gets which animation in the cut table or storyboard.

## Once the script has scenes: the scene planner

A film built from scenes (a launch film, an explainer) gets the planner instead of, or after, the picker: one row per
scene with that scene's real line animating in the video's own colours on the chosen background, a dropdown to swap its
animation, and between rows the transition into the next scene, playing, with its own dropdown.

1. Write `videos/<project>/film.json` from the approved script (the `storyboard` skill has the format): per scene
   `id`, `label`, `text`, `parts` for the card, list and cursor pieces, a first `anim` and `tr`; at the top `look` and
   `background`.
2. `python3 $TA/scripts/tfx.py planner --scenes videos/<project>/film.json` writes `review/planner.widget.html` next
   to it; pass its contents to `show_widget` (title `<project>_scene_planner`).
3. "Use these choices" sends `Scene plan: background=halftone-light; 1=accent-words; 1>2=pixel; 2=stack-cards; ...`.
   Write it into the plan with `python3 $TA/scripts/tfx.py apply --scenes videos/<project>/film.json --line "<line>"`
   (it checks every id and writes nothing if one is wrong). Then build (`launch-demo`'s `film.py`) and show the
   `storyboard` before rendering.

The card and cursor previews show each piece's style on sample screens (a dashboard, a stack of cards); the film's own
screens appear in the storyboard.

Taste rules: two or three animation types per video, one entrance for every headline, emphasis only on the phrase that
carries the value. Entrances take 0.5 to 1 s; leave the text still for at least 1.5 s after it lands.

## The 57

| # | id | Name | Group | Best for | Text |
|---|---|---|---|---|---|
| 01 | `fade-up` | Fade up | Entrances | Calm opener for a headline or a value line | one line |
| 02 | `typewriter` | Typewriter | Entrances | Prompts, search, anything typed | one line |
| 03 | `pop-in` | Pop in | Entrances | Short punchy words, feature names | one line |
| 04 | `mask-reveal` | Mask reveal | Entrances | Premium headline reveal, section titles | `line|line` (up to 4 words stay on one line) |
| 05 | `blur-in` | Blur in | Entrances | Soft, elegant openers; AI and clarity themes | one line |
| 06 | `scramble` | Text scramble | Entrances | Tech and AI features, data, codes | one line |
| 07 | `write-on` | Write on | Entrances | Sign-off, handwritten notes, a personal touch | one line |
| 08 | `scatter-in` | Scatter in | Entrances | Things coming together: integrations, teams | one line |
| 09 | `stamp` | Stamp | Entrances | Verdicts: approved, sold out, done | one line |
| 10 | `drop-in` | Drop in | Entrances | Playful openers, uploads, drag and drop | one line |
| 11 | `tilt-reveal` | Tilt reveal | Entrances | Section changes, chapter titles | one line |
| 12 | `behind-subject` | Text behind subject | Entrances | A big word behind a person or product | one line |
| 13 | `highlight` | Highlight | Emphasis | Mark the one phrase that matters | one line |
| 14 | `tracking-out` | Tracking out | Emphasis | Space, calm, premium | one line |
| 15 | `strikethrough` | Strikethrough | Emphasis | Before and after: old way vs new way | `old|new` |
| 16 | `hand-circle` | Hand-drawn circle | Emphasis | Point at a word like a marker on a slide | one line |
| 17 | `shimmer` | Shimmer | Emphasis | AI, premium, new-feature sparkle | one line |
| 18 | `squash-stretch` | Squash and stretch | Emphasis | Playful brands, fun moments | one line |
| 19 | `wave` | Wave | Emphasis | Music, rhythm, light-hearted emphasis | one line |
| 20 | `variable-weight` | Variable weight | Emphasis | Turning something up: volume, impact, growth | one line |
| 21 | `whip-in` | Whip in | Emphasis | Speed claims, quick transitions | one line |
| 22 | `bouncing-dot` | Bouncing dot | Emphasis | Steps, a process, a list read aloud | one line |
| 23 | `float` | Float | Emphasis | Brand attributes, a cloud of benefits | `word|word|...` |
| 24 | `tracking-in` | Tracking in | Emphasis | Pulling attention in, concentration | one line |
| 25 | `text-flip` | Text flip | Swaps and loops | One sentence, many audiences or uses | `lead|option|option|...` |
| 26 | `word-carousel` | Word carousel | Swaps and loops | Rotating benefits after a fixed lead-in | `lead|word|word|...` |
| 27 | `color-shift` | Color shift | Swaps and loops | Brand colours, energy, a logo-like word | one line |
| 28 | `marquee` | Marquee | Swaps and loops | Loud announcements, end cards, events | `row|row` |
| 29 | `oversized-crop` | Oversized crop | Swaps and loops | Bold brand moments, cover frames | one line |
| 30 | `text-path` | Text on a path | Swaps and loops | Journeys, flows, a path to value | one line |
| 31 | `shape-morph` | Shape morph | Transformations | A dot becomes the CTA button | one line |
| 32 | `extrude-3d` | 3D extrude | Transformations | Big claims, numbers, chunky emphasis | one line |
| 33 | `zoom-through` | Zoom through | Transformations | Diving into a feature, scene change | `big word|next word` |
| 34 | `invert` | Invert | Transformations | Contrast, before and after, dark mode | one line |
| 35 | `reflection` | Reflection | Transformations | Polished, glossy product moments | one line |
| 36 | `repeater` | Repeater | Transformations | Repetition, automation, every time | one line |
| 37 | `inline-images` | Inline images | Video and UI | Show the things the words name | `word|word|word` |
| 38 | `tracked-callout` | Tracked callout | Video and UI | Label something that moves in the recording | one line |
| 39 | `karaoke` | Karaoke captions | Video and UI | Captions for a voiceover | one line |
| 40 | `text-mask` | Text mask | Video and UI | Footage or colour inside big letters | one line |
| 41 | `chat-bubbles` | Chat bubbles | Video and UI | Conversations, support, AI chat features | `message|reply|message` |
| 42 | `counter` | Counter | Video and UI | Metrics, growth, results | `label|48.2|$#K` |
| 43 | `accent-words` | Accent words | Entrances | A line built word by word, the newest word in the accent colour | one line |
| 44 | `roll-list` | Roll list | Swaps and loops | One lead word, the ending rolls through a list | `lead|word|word|word` |
| 45 | `prompt-type` | Typed prompt | Video and UI | Typing into a prompt bar, then a click on send | `prompt|cursor label` |
| 46 | `card-cloud` | Card cloud | Cards and cursors | Everything your product does, gathered round one idea | `centre|card|card|...` |
| 47 | `stack-cards` | Notification stack | Cards and cursors | Things happening on their own: syncs, updates, alerts | `title|first|second|...` |
| 48 | `chips-to-card` | Chips into a card | Cards and cursors | Many sources becoming one list: leads, tickets, feedback | `title|name|source|name|source...` |
| 49 | `cursor-tour` | Cursor tour | Cards and cursors | A labelled cursor points, rings, explains and clicks | `cursor label|tooltip|second cursor` |
| 50 | `pixel-dissolve` | Pixel dissolve | Transitions | A scene change in blocks of the brand colours | `before|after` |
| 51 | `blur-swap` | Blur swap | Transitions | A soft scene change: one line blurs out, the next sharpens in | `before|after` |
| 52 | `wipe-cut` | Wipe | Transitions | The next scene wipes in from the left | `before|after` |
| 53 | `iris-cut` | Iris | Transitions | The next scene opens from the centre in a circle | `before|after` |
| 54 | `whip-pan` | Whip pan | Transitions | A fast, blurred slide sideways into the next scene | `before|after` |
| 55 | `push-cut` | Push | Transitions | The next scene pushes the last one up and out | `before|after` |
| 56 | `zoom-cut` | Zoom | Transitions | The scene rushes past the camera; the next settles in | `before|after` |
| 57 | `glitch-cut` | Glitch | Transitions | A stepped jitter with a colour shift: tech, AI, energy | `before|after` |

43-51 and the background below follow the motion measured frame by frame in a reference launch video (the style,
never its copy, colours or assets): words land in about 0.1 s and blur in from soft to sharp; lists roll in 0.3 s
and hold about a second; cards arrive every 0.15 s with a soft shadow; cursors travel on eased curves, ring what they
point at and click with a 0.4 s ripple; the pixel dissolve grows from a point in 0.4 s and clears sideways in 0.35 s.

Text with `|` splits into parts as shown (e.g. `"Weeks|Minutes"` strikes Weeks and brings in Minutes). Line breaks are
ignored: the animation lays the words out.

## In a fast-cut video

Give a text an `"anim"` with an id; fast-cut renders it once through HyperFrames as a transparent MOV (cached in
`.tfx-cache/` next to `cut.json`) and lays it over the footage at `from`, fading out at `to`:

```json
{"text": "Know your size first", "anim": "highlight", "from": 3.3, "to": 6.0, "y": 0.05, "size": 64,
 "color": "#FFFFFF", "accent": "#7DD3FC", "accent2": "#4F46E5"}
```

- The animation sits in a band at the text's `y` and `width`; `"anim_box": [x, y, w, h]` (final pixels) places it
  anywhere, which is what the full-panel ones need (behind subject, marquee, tracking in, invert, oversized crop).
- `color` is the ink (white over dark footage), `accent` the key colour, `accent2` the second (highlight bars,
  panels). Work videos: the brand look's colours.
- Each new animation costs one HyperFrames render (about 10 to 20 s); the cache makes re-renders free.
- **Text mask (40) with footage:** add `"fill"` and the letters become windows onto the recordings (rendered in FFmpeg, no
  HyperFrames). The word settles in, plays the fill clips in order, then flies through one letter until the footage fills
  the frame: a strong opener that introduces a product with its own screens.

  ```json
  {"text": "Shopwise", "anim": "text-mask", "from": 0.45, "to": 2.6, "y": 0.52, "size": 260, "weight": "Bold",
   "through": "i", "grow": {"at": 1.35, "scale": 60, "ease": 1.5},
   "fill": [{"src": "raw/a.mov", "from": 55.2, "to": 55.75, "focus": [0.42, 0.55], "zoom": 1.25},
            {"src": "raw/b.mov", "from": 7.0, "to": 7.9, "focus": [0.5, 0.45]}]}
  ```
  `y` is the word's centre. `focus` is the point of the recording (shares of its frame) that sits behind the letters:
  aim it at bright photos, never dark UI, or the word sinks into a dark background. `grow.at` is seconds after `from`;
  `through` is the letter to fly into (a thick stem such as l, I or H fills the frame fastest). End on the footage the
  next section opens with, and start the next headline as the fly-through fills the frame.

## In a HyperFrames composition

Copy `text-fx.js` next to `index.html`, load it after GSAP, and add each animation to the master timeline:

```html
<div id="title" style="position:absolute;left:120px;top:140px;width:1680px;height:260px"></div>
<script src="vendor/gsap.min.js"></script><script src="text-fx.js"></script>
<script>
  var master = gsap.timeline({ paused: true });
  master.add(TextFX.build(document.getElementById("title"), "mask-reveal",
    { text: "Meet the new app", size: 120, ink: "#FFFFFF", accent: "#7DD3FC" }).tl.paused(false), 1.2);
  window.__timelines = { "my-video": master };
</script>
```

Options: `text`, `size` (px; default fits the box), `ink`, `accent`, `accent2`, `accent3`, `accent4`, `paper`,
`font` (default Poppins), `weight`, `hold` (seconds held at the end). `TextFX.list` has every id, name, group and use.
Cards and cursors size themselves from the box; give them a box at least a third of the frame.

**Transitions between any two scenes** (seek-safe, colours from the look). One call for all nine kinds:

```js
// kind: cut | pixel | blur | wipe | iris | whip | push | zoom | glitch. Returns {cover, end}: the next scene is fully in at cover.
TextFX.transition(master, "wipe", sceneA, sceneB, at, { manage: true, W: 1920, H: 1080, container: fxLayer, colors: [accent, accent2] });
// manage: shows sceneB and hides sceneA at the right moments. clearFrom: also takes sceneA away as sceneB arrives, for
// see-through scenes over one shared background. To land a transition on a beat: at = beat - TextFX.transitionCover[kind].
```

The two building blocks, for hand-built pages:

```js
// blocks grow from `origin` for 0.4 s, cover the container at px.cover (swap the scenes there), clear sideways in 0.35 s
const px = TextFX.pixel(master, document.getElementById("stage"), { at: 4.0, colors: [accent, accent2], origin: [0.6, 0.5] });
master.set("#sceneA", { opacity: 0 }, px.cover); master.set("#sceneB", { opacity: 1 }, px.cover);
// the outgoing scene blurs out in 0.15 s while the next sharpens in over 0.3 s
TextFX.blurSwap(master, document.getElementById("sceneB"), document.getElementById("sceneC"), 8.0);
```

In the launch-demo templates these are `"tr"` on a montage card or a scene; the scene planner previews each one between
the scene's real lines.

## Animated halftone background

`scripts/halftone.py` draws pale blobs that drift and morph, ringed by halftone dots that are biggest just outside
each blob and fade into the paper: a seamless loop at any size, coloured from a look.

```bash
python3 $TA/scripts/halftone.py --look brand --size 1920x1080 --out videos/<project>/img/bg.mp4      # light, 12 s loop
python3 $TA/scripts/halftone.py --look brand --mode dark --size 1080x1920 --out videos/<project>/img/bg-dark.mp4
python3 $TA/scripts/halftone.py --look brand --still videos/<project>/img/bg.png                     # one frame, for the chat
```

`--look` reads any look in `youtube-edit/styles/` (a company look kept on this Mac works the same way, and its colours
never enter the repo); `--colors paper,blob,dots,dots2` sets them directly; `--speed 1-3` the drift. Show a still first.
In HyperFrames, lay the MP4 in an untimed layer as a muted `<video>` with its own `data-start`; in fast-cut, use it as
a segment's footage. Keep text on it dark on the pale blobs or on a card.

## Files

| File | What it is |
|---|---|
| `text-fx.js` | The 57 animations, `TextFX.transition` (nine kinds) and its building blocks `TextFX.pixel` / `TextFX.blurSwap` |
| `scripts/halftone.py` | The animated halftone background, in any look's colours |
| `scripts/tfx.py` | `picker` (writes the picker files), `planner` / `apply` (the scene planner and its sent line), `gallery` (renders the preview), `clip` (one transparent MOV) |
| `picker.widget.html` | The in-chat picker, with the backgrounds (generated) |
| `gallery.html` | The page `tfx.py gallery` renders the preview video from (never shown to the creator) |
| `preview/` | `preview.png` and `text-animations.mp4`: all 57, numbered, in motion |

The catalogue follows the "Claude + Figma Motion: Text Animations" board curated by Shlomo Genchin (Unbore.com); the
code and sample copy here are original.
