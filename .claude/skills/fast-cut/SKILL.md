---
name: fast-cut
description: Fast edits of a screen recording or any video the user hands over, when the footage already shows the right thing and needs cutting, not rebuilding. One labelled contact sheet, an automatic scan that finds the still stretches (loading, an AI generating, pauses) and speeds them up, a cut list (keep / trim / speed / zoom / reframe / text / image), and ONE FFmpeg render: a draft in seconds, the full-resolution final in well under a minute. Use for "cut this recording", "speed up the loading", "make this 60 seconds", "reframe for Reels / 9:16", "add a line of text here", "trim the start", "quick edit", "fast cut". Not for videos whose screens must change (new copy inside the UI, removed elements, different products): rebuild those with the youtube-edit skill and HyperFrames.
---

# Fast cut

Edit the footage, never re-create it. Nothing goes through a browser frame by frame, so a short ad takes seconds to
render. Run everything from the project folder with `FC=".claude/skills/fast-cut/scripts"` and `W="videos/<project>"`.

## The route (aim: first draft in front of the creator within ~10 minutes)

1. **Read the brief once.** The upload page's `brief.json` (purpose, shape, notes) and the files in `$W/raw/`. The
   project's standing check still applies: confirm Personal or Office in the same message as the cut list, never as a
   separate round. Ask only what blocks the edit; state every default instead of asking about it.
2. **Look once:** `python3 "$FC/contact-sheet.py" --video "$W/raw/<file>" --out "$W/analysis/sheet.png"`
   (about 24 frames, the time under each, ~1 s). At most ONE detail sheet of the moments that decide the cut
   (`--from A --to B --every 0.25`). No other frame grabs, zoom crops or strips.
3. **Scan:** `python3 "$FC/fast-cut.py" scan --video "$W/raw/<file>" --size 1080x1920 --out "$W/cut.json"` writes a
   starter cut list: 1x everywhere, every still stretch over 1.2 s at 8x (`--still`, `--speed`). With several clips,
   scan each and merge their segments in story order.
4. **Propose the cut as one table** (range, speed, zooms, text) and the defaults you chose. If the creator said "just
   do it", skip straight to the draft.
5. **Draft:** `python3 "$FC/fast-cut.py" render --cut "$W/cut.json" --out "$W/render/draft.mp4" --draft` (half size,
   seconds). Send it with SendUserFile.
6. **Notes change numbers in `cut.json`**, then another draft. Never re-derive anything.
7. **Final:** the same command without `--draft`, written straight to
   `~/Movies/YouTube Renders/<project>/<project>-v<N>-<W>x<H>.mp4` (the upload page lists it with Download). Copy
   `cut.json` to `$W/versions/v<N>/`. The tool prints size and duration; that is the check. No other verification pass.

## cut.json

```json
{
  "size": [1080, 1920], "fps": 30, "fit": "cover", "bg": "#000000", "audio": "mute",
  "segments": [ {"src": "raw/rec.mov", "from": 0, "to": 12.4, "speed": 1},
                {"src": "raw/rec.mov", "from": 25.0, "to": 32.0, "speed": 6} ],
  "zooms":  [ {"from": 3.0, "to": 5.0, "scale": 1.3, "x": 0.5, "y": 0.42, "ease": 0.3} ],
  "texts":  [ {"text": "See it on you", "from": 1.0, "to": 4.0, "y": 0.12, "size": 76, "color": "#FFFFFF",
               "box": "#1A1A2ECC", "weight": "SemiBold", "width": 0.86} ],
  "images": [ {"file": "img/logo.png", "from": 0, "to": 3, "x": 0.5, "y": 0.9, "w": 0.3} ]
}
```

- `segments` play in order; `src` paths are relative to `cut.json`. `speed` bakes the speed change in (6-8x for AI
  waits and loading; keep taps, reveals and results at 1x so cause and effect read).
- `fit`: `cover` fills the frame and crops (a phone recording into 9:16), `contain` fits inside with `bg` bars.
- `zooms`, `texts`, `images` use OUTPUT time (the timeline after cuts and speed changes). A zoom is a push to `scale`
  on the focus point `x`, `y` (0-1), easing in and out over `ease` s. Zoom 1.2-1.4 on the thing being explained.
- Text is Poppins (`weight`: Regular, Medium, SemiBold, Bold), one or two short lines, `y` = top of the text block as a
  share of the height, `box` = a rounded backing for legibility (Office videos: Glance navy `#1A1A2ECC`, white text).
- `audio`: `keep` keeps the sound of 1x segments and makes sped-up parts silent; `mute` drops it.

## When not to use it

The footage must change: different words inside the app, elements removed, other products shown. That is a rebuild
(youtube-edit skill, HyperFrames). Even then, cut the parts that stay real with fast-cut and rebuild only the rest.
