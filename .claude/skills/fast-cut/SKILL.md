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
   `~/Movies/YouTube Renders/<project>/<project>-v<N>-<W>x<H>.mp4`. Copy `cut.json` to `$W/versions/v<N>/`. The tool
   prints size and duration; that is the check. No other verification pass.
8. **Review in the chat:** `python3 "$FC/review.py" --cut "$W/cut.json" --video <the delivered mp4> --out "$W/review/v<N>"`
   (~5 s) writes `headlines.png` (each headline intro frame by frame), `taps.png` (before / tap / after), `zooms.png`,
   `overview.png` (a frame every 2.5 s) and `moments.mp4` (just those moments, with sound). Send all five with
   SendUserFile next to the video; the creator gives notes by the times under the frames.

## cut.json

```json
{
  "size": [1080, 1920], "fps": 30, "fit": "contain", "bg": "#1A1A2E", "audio": "mute",
  "box": [80, 330, 920, 1520],
  "segments": [ {"color": "#1A1A2E", "dur": 2.6},
                {"src": "raw/rec.mov", "from": 0, "to": 12.4, "speed": 1},
                {"src": "raw/rec.mov", "from": 25.0, "to": 32.0, "speed": 6} ],
  "zooms":  [ {"src": "raw/rec.mov", "from": 8.0, "to": 11.0, "scale": 1.3, "x": 0.5, "y": 0.6, "ease": 0.45} ],
  "taps":   [ {"src": "raw/rec.mov", "t": 4.2, "x": 0.25, "y": 0.68, "note": "opens the product"} ],
  "texts":  [ {"text": "See it on you,\nbefore you buy", "from": 2.3, "to": 16.3, "y": 0.052, "size": 66,
               "weight": "Bold", "width": 0.88, "intro": {"size": 108, "y": 0.42, "hold": 1.45, "move": 0.65}} ],
  "images": [ {"file": "img/logo.png", "from": 0, "to": 3, "x": 0.5, "y": 0.9, "w": 0.3} ]
}
```

- `segments` play in order; `src` paths are relative to `cut.json`. `speed` bakes the speed change in (6-8x for AI
  waits and loading; keep taps, reveals and results at 1x so cause and effect read). A `{"color", "dur"}` segment is a
  plain card for a title.
- `fit`: `cover` fills the frame and crops (a phone recording into 9:16), `contain` fits inside with `bg` bars.
- `box` (optional): the footage sits in x, y, w, h (final pixels) on `bg`, leaving room for a headline above it;
  zooms push inside the box, so the headline and the margins stay still.
- **Zooms and taps** with `src` use SOURCE time and `x`, `y` as shares of the recording's own frame, read straight off
  a contact sheet; they land wherever the cut puts that moment. A tap is a ripple (purple edge, lavender ring) at the
  spot; put it on the last frame before the screen reacts (the motion spike in the scan). A zoom is a push to `scale`
  on the focus point, easing over `ease` s: 1.2-1.5 on the thing being explained, and slow the segment under it so
  it holds at least ~1 s. `python3 "$FC/fast-cut.py" times --cut "$W/cut.json"` lists each tap's output time: add a
  soft click there in the mix (`videos/_shared/sfx/click-soft.mp3` at about -8 dB).
- Without `src`, zooms and taps use OUTPUT time and shares of the box (or the frame).
- **A text with `intro`** opens big (`size`, centred at `y`) over a navy scrim at `from`, lines rising in, holds `hold` s,
  then shrinks and glides to its own `y` / `size` while the scrim lifts and the footage shows through: the section
  headline that tells viewers a new feature starts. Start it ~0.3 s before the section's first frame and give each
  headline its line break (`\n`) so the big and resting layouts match.
- `texts` and `images` use OUTPUT time (the timeline after cuts and speed changes).
- Text is Poppins (`weight`: Regular, Medium, SemiBold, Bold), one or two short lines, `y` = top of the text block as a
  share of the height, `box` = a rounded backing for legibility (work videos: the brand's dark colour at ~80%, white text).
- `audio`: `keep` keeps the sound of 1x segments and makes sped-up parts silent; `mute` drops it.

## When not to use it

The footage must change: different words inside the app, elements removed, other products shown. That is a rebuild
(youtube-edit skill, HyperFrames). Even then, cut the parts that stay real with fast-cut and rebuild only the rest.
