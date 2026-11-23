---
name: mascot-story
description: A two-scene mascot animation joined by the Slice transition. In scene A the character holds a phone and scrolls an endless feed; it lets go, winds up and slices straight through the phone along a glowing cut; the scene splits onto scene B, where it lands and a shopping bag pops into its hand. Any character image (a brand mascot, a logo character), the colours of any look, 16:9, 9:16 or 1:1, rendered to MP4 and GIF. Use for "mascot slice", "the scroll to shop animation", "mascot holding a phone", "mascot with a shopping bag", "make the mascot cut into the next scene", "endless scrolling to shopping".
---

# Mascot story

Run from the project folder with `MS=".claude/skills/mascot-story/scripts"`. Everything is asked and shown in the chat.

1. **Ask, in one message:** the character image (a cut-out PNG; a company mascot stays in the video's folder or the
   company's local styles, never in this repo), the look, the size, and the two lines (scene A, e.g. "Endless
   scrolling"; scene B, e.g. "Shop what you love").
2. **Write `videos/<project>/story.json`:**

   ```json
   {"character": "img/mascot.png", "size": [1920, 1080], "look": "brand",
    "a": {"title": "Endless scrolling", "prop": "phone"},
    "b": {"title": "Shop what|you love", "prop": "bag"},
    "out": "render/scroll-to-shop.mp4"}
   ```
   `"colors": {"dark", "light", "accent", "accent2", "warm"}` instead of `look` sets the colours directly. `|` breaks a line.
3. **Render:** `python3 $MS/mascot_story.py --config videos/<project>/story.json` writes the MP4 and a GIF next to
   `out` (about a minute). Send the GIF with SendUserFile.

## The beats (6.2 s)

| Time | Beat |
|---|---|
| 0.1-2.6 s | The character slides in and holds the phone (little hands on its sides); four thumb flicks, the feed flies up and settles, the body sways. The feed ends where it began, so it reads as endless. |
| 2.75 s | It lets go (the phone stays, floating on the cut line) and backs off |
| 3.2 s | Wind-up: leans back 16°, squashes |
| 3.44 s | The slice: 3 frames along the cut, three afterimages, then flash, shake and sparks (`TextFX.transition(..., "slice")`) |
| 3.73 s | The scene, phone included, splits along the cut; the halves fly apart onto scene B |
| 4.0-6.2 s | It lands, the bag pops into its hand and swings, the character bobs; scene B's line blurs in |

## Growing it

Scene B props live in `PROPS_B` in `mascot_story.py` (`bag` so far). New ideas for the bag frame (other props, poses,
products flying into the bag) go there as new entries, each with its own pop-in, and a line in this file. Keep the
timings above unless the creator asks: they follow the Slice transition's measured beats.

## Rules

- A company's mascot and colours stay on the company's Mac (`videos/`, local styles); the skill and its examples stay
  generic.
- The cut, split, flash and sparks are the library's Slice transition; change them there (`text-fx.js`), not here.
