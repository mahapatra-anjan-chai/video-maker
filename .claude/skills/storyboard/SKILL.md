---
name: storyboard
description: Show a HyperFrames film's frames and transitions in the chat before the full render. One snapshot run gives a storyboard sheet (every scene at the moment its text lands, numbered, with its animation and the transition out), a transitions sheet (every scene change frame by frame) and a short clip of the transitions playing. Pairs with the scene planner (pick each scene's text animation, the transitions and the background in the chat). Use for "show me the frames", "show me the transitions", "storyboard", "how will it look before you render", "preview the scenes", "plan the scenes", "which animation for each scene".
---

# Storyboard

The person sees how the film comes out before anything renders: first the plan (live, in the chat), then real frames of
the built film, then the render. Run from the project folder with `W="videos/<project>"`. Everything is shown in the
chat; never point anyone to a page, a preview server or Studio.

## The flow for a film built from scenes

1. **Plan the scenes in the chat.** Write `$W/film.json` (below) from the approved script: one scene per beat of the
   story, its line of copy, a first pick of text animation and transition. Then
   `python3 .claude/skills/text-animations/scripts/tfx.py planner --scenes $W/film.json` and pass the file it prints to
   `show_widget` (read the `interactive` module first). Each scene's own line animates in the video's colours on the
   chosen background; between scenes, the transition plays; dropdowns swap them. "Use these choices" sends back one
   line (`Scene plan: background=...; 1=accent-words; 1>2=pixel; ...`). Write it into the plan with
   `python3 .claude/skills/text-animations/scripts/tfx.py apply --scenes $W/film.json --line "<the line>"`.
2. **Build** the film: `python3 .claude/skills/launch-demo/scripts/film.py --scenes $W/film.json --out $W/public`
   (the `launch-demo` skill, "A launch film from a scene plan"). It writes each scene's timing into `film.json`.
3. **Storyboard, scenes first** (about 15 s for a whole film):
   `python3 .claude/skills/storyboard/scripts/storyboard.py --project $W/public --scenes $W/film.json --out $W/review --what scenes`
   and send `storyboard.jpg` with SendUserFile.
4. **Then the transitions** (about 20 s each, so 2 to 3 minutes for a film): `--what transitions`, send `transitions.jpg` and `transitions.mp4`.
   Or both at once without `--what`.
5. **Notes come back by scene number** ("3 lands too late", "4 > 5 should be a wipe"). Fix, then re-run with
   `--only 3,4` so only those scenes and the transitions into and out of them are taken again.
6. **Render** only when the storyboard is approved. Rebuilding something that already rendered: `--against <that MP4>`
   puts each new frame next to the same moment in the old video.

## film.json

The scene plan. `film.py` adds the music grid, the kinds of scene and the custom hook (see `launch-demo`); the part the
planner and the storyboard read looks like this:

```json
{"look": "brand", "size": "1920x1080", "background": "halftone-light",
 "scenes": [{"id": 1, "label": "The pain", "text": "Too many tabs open.", "anim": "accent-words", "tr": "pixel",
             "at": 0, "lands": 2.4, "end": 6.8, "tr_cover": 6.8},
            {"id": 2, "label": "Setup", "text": "One click to set up.", "parts": "Setup|Installed|Synced|Live",
             "anim": "stack-cards", "tr": "blur", "at": 6.8, "lands": 9.0, "end": 14.0, "tr_cover": 14.0}]}
```

- **The plan** (the planner reads and writes these): `id`, `label`, `text` (the scene's line), `parts` (for the
  multi-part animations: cards, lists, chips, cursors; `|` between parts), `anim` (a text-animation id), `tr` (the
  transition into the next scene: cut, pixel, blur, wipe, iris, whip, push, zoom, glitch), and at the top `look`,
  `size`, `background` (`halftone-light`, `halftone-dark`, `plain`).
- **The timing** (the film's builder writes these, in seconds, on the 1/30 s grid): `at` (scene starts), `lands` (its
  text has fully landed: the storyboard frame), `end`, `tr_cover` (the moment the next scene is fully in). Without
  `lands`, the storyboard takes 60% of the way through the scene.

## Rules

- Every frame comes from ONE snapshot run (each extra run costs a browser start). Snapshots always run with
  `--describe false`, so no frame leaves the Mac, and the frames are deleted once the sheets exist.
- Send the sheets, not single frames: the storyboard reads as the film at a glance.
- A red box on the storyboard means that moment did not render: check the scene's timing in `film.json`.
