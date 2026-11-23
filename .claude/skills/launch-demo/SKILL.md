---
name: launch-demo
description: Make a 60-90 second launch demo for a product, in the structure of Video maker's own LinkedIn demo. Real people buried in requests open it, the product's name lands with footage inside the letters, the feature plays on a real iPhone frame, a montage of text animations and transitions hits on the music's drop, and the logo locks up on the music's final hit. Square 1:1 with captions for muted autoplay, a voiceover approved as a script before any credits are spent, Epidemic music beat-matched start to end. Also a 16:9 launch film with no voice, built from a scene plan: each scene's line in the text animation picked for it in the chat, the transitions landing on the music's beats, the look's halftone background, a logo card and a lockup with the brand's icon, a storyboard before the render. Use for "make a launch demo", "a demo video like the Video maker one", "a LinkedIn launch video", "announce the feature", "product launch video", "sizzle reel", "a launch film for the website", "text and music only".
---

# Launch demo

The recipe behind Video maker's own demo, so every launch video starts from what worked. Run from the project folder
with `L=".claude/skills/launch-demo/scripts"` and `W="videos/<project>"`. Everything is asked and shown in the chat.

## The structure (about 80 s at 114 BPM; scale it to the script)

| Section | Time | What happens | Sound |
|---|---|---|---|
| 1. The pain | 0-10 s | Real people buried in work (licensed stock), request bubbles pile up with a counter | Office room tone, a ping per request, no music |
| 2. The name | 10-17 s | A wipe clears the pile; the product's name fills the frame with its footage inside the letters, then flies through a letter | Music starts as the line ends |
| 3. The feature | 17-26 s | The product on a real iPhone frame, full screen; callouts on taps and zooms; a headline opens big, then settles above the phone | Voice, music ducked |
| (your scenes) | | Anything product-specific (a workflow, a before/after), built in `custom.html/css/js` | |
| 4. The montage | on the drop | One card every two beats: text animations, each entering with a different transition | Music only, a swish per cut |
| 5. The outro | last 10 s | A short card (open source / live today), six capability tiles on six beats, they fly into the centre, the logo locks up on the music's final hit, fade | The track's real ending, an impact and a shimmer |

Captions run under every spoken line (sentence chunks, the spoken word lit). The voice says what the picture shows.

## The route

1. **Brief, one message:** product, audience, the one-line value, the CTA (link, "live today"), shape (1:1 default),
   personal or work, the look. Then the **full script** (opening lines about the pain, one line per section) for a yes,
   before anything is generated. Never carry wording, language or assets over from another project.
2. **Voice:** `python3 .claude/skills/youtube-edit/scripts/elevenlabs.py voiceover --script $W/script.txt --out $W/voiceover`
   shows the cost and the credits left; `--yes` once approved. One generation; later edits pay only for changed lines.
3. **Music:** search Epidemic for 105-125 BPM, instrumental, a clear drop and a hard ending ("upbeat modern tech product
   launch"). Offer three, download the pick (WAV). Then
   `python3 $L/beats.py --music $W/audio/music.wav --bpm <Epidemic's bpm> --drop-at <montage start> --hit-at <lockup>`:
   it says when the music starts, the beat grid in video time, and the splice into the track's own ending.
   Put every section start, the montage cards and the outro tiles on beats from that grid.
4. **Footage:**
   - **The pain:** stock clips of people, licensed for commercial use. Mixkit: check each clip's page says
     "Stock Video Free License"; skip "Restricted" (personal use only). Name the clip, source and size and wait for a yes
     before downloading. Never use real company footage you were not given.
   - **The name:** `fast-cut` with a `text-mask` text (two stacked words, footage of the product inside, `grow` through a
     thick letter); see `fast-cut/SKILL.md`.
   - **The feature:** a full-bleed render of the screen recording at the phone's own size (`fast-cut`, `"size": [780,
     1688]`, `"fit": "cover"`, taps and zooms, no texts). The headline is the page's, not the render's.
   - **Product images** in made-up demos: CC0 only (Wikimedia Commons, Rawpixel public domain, StockSnap), each licence
     checked on its source page, credited in a CREDITS.md. Never real retailers' catalog photos.
5. **Build:** copy `example/demo.json` to `$W/demo.json` and fill it in (times, copy, clips, colours from the look).
   Captions: write `$W/work/words.json` from the voiceover's `transcript.json` placed at each line's time
   (`[{"t","e","w","line"}]`). Then `python3 $L/build.py --config $W/demo.json --words $W/work/words.json --out $W/public`,
   `npx hyperframes lint` in `$W/public`, and ONE `npx hyperframes snapshot --at <a moment per section> --no-end` to check.
6. **Render:** `npx hyperframes render --format mp4 --output ../render/video-only.mp4` in `$W/public` (under a minute).
7. **Sound:** copy `example/mix.json` to `$W/mix.json`, fill in the voice lines, the music start and splice from
   `beats.py`, and the sound effects (Epidemic: room tone, swishes, whooshes, an impact, a shimmer;
   `videos/_shared/sfx/` for pops, pings, typing). `python3 $L/mix.py --mix $W/mix.json --out $W/render/mix.wav`.
8. **Check the voice:** `python3 $L/check.py --mix $W/render/mix.wav --script $W/script.txt` must say 90% or more.
9. **Deliver:** mux (`ffmpeg -i render/video-only.mp4 -i render/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k
   -shortest -movflags +faststart`) to `~/Movies/YouTube Renders/<project>/<project>-v<N>-1080x1080.mp4`, send it, say the
   preview may start muted. Keep `demo.json`, `mix.json` and the scripts in `$W/versions/v<N>/`.

## A launch film from a scene plan (16:9, text and music)

For a website or YouTube launch film with no voiceover: scenes of on-screen copy over the look's moving halftone, cut on
the music. `example/film.json` is a whole one (Video maker's own copy, the Brand look).

1. **Brief and script** as above, then the scenes: one line of copy each, the story's beats (the pain, the idea, the
   name, the product, what it's for, the lockup). Write `$W/film.json` (fields below).
2. **Music** as above (Epidemic, a clear ending). `beats.py` gives the `bpm` and the first beat (`offset`); give each
   scene a length in `beats`, and set `duration` and `hit` (the final note) for the lockup.
3. **Plan in the chat:** the scene planner (`text-animations`, "the scene planner") shows each scene's line in its
   animation, the transitions and the background; the creator's picks come back as one line, written in with
   `tfx.py apply`.
4. **Build:** `python3 $L/film.py --scenes $W/film.json --out $W/public` (it makes the look's halftone loop once, about a
   minute, and keeps it in `videos/_shared/backgrounds/`), then `npx hyperframes lint` in `$W/public`.
5. **Storyboard before the render** (`storyboard` skill): the scenes, then the transitions, sent in the chat. Notes
   come back by scene number; change `film.json`, rebuild, re-take only those scenes (`--only`).
6. **Render, mix, deliver** as above (steps 6, 7 and 9; no voice to check). Name the file `-1920x1080`.

film.json: the planner's fields (`text`, `parts`, `anim`, `tr`, `background`: halftone-light | halftone-dark | plain)
plus `look`, `size`, `bpm`, `offset`, `duration`, `hit`, `fade`, `name` (the product's name on the logo and lockup
cards), `custom` (`css`, `js`, `media`). Per scene: `beats` (or `dur` in seconds), `kind`:
- `text` (default): the line in its animation. Cards, cursors and UI pieces get the line as a headline above them;
  `lines` adds more lines in the same scene, each blurring into the next (`line_beats` places them).
- `logo`: the name (or a `logo` image) with the look's icon, if it has one (`icon: false` hides it), then the line.
- `lockup`: the same, landing on the music's `hit`; `fade` ends the film.
- `custom`: the product's own scene, an `html` fragment with `custom.css` / `custom.js` (the script gets `root`, `SC[id]`
  with the scene's `at` and `end`, `PAL` and `fx(el, anim, opts, at)`). For a storefront, an app screen, a try-on.

The builder writes each scene's `at`, `lands`, `end` and `tr_cover` back into `film.json` for the storyboard; the plan
fields are only ever changed by the planner or by hand.

## demo.json

`duration`; `palette` (`bg`, `panel`, `line`, `a1`-`a4`); `tags` (`[time, number, label, hide-at]`);
`opening` (`to`, `counter`, `clips` [`src`, `start`, `dur`, `media`, `pos`], `requests` [`t`, `who`, `init`, `color`,
`text`, `file`]); `hook` (`src`, `start`, `dur`); `feature` (`from`, `to`, `phoneIn`, `poster`, `clips`, `callouts`
[`t`, `label`, `color`, `y`], `headline` [`t`, `lines`, `glide`]); `montage` (`t0`, `bpm`, `beats`, `cards` [`fx` from the
57, `text`, `bg`, `ink`, `accent`, `tr` = wipe | iris | glitch | whip | push | zoom | pixel | blur, `label`, `size`]); `outro` (`from`,
`card` [`t`, `out`, `icon`, `big`, `sub`, `url`], `title` [`t`, `html`], `tiles` [`t`, `label`, `icon`, `color`],
`converge`, `hit`, `lockup` [`name`, `tagline`, `cta`, `url`, `credits`], `fade`); `custom` (`html`, `css`, `js` files).
Icons: scissors, zoom, type, sparkle, palette, music, bolt, chat, chart, shield, globe, check, clock, phone, star.

## Traps (each one cost a render)

- Media sits in untimed layers with its own `data-start`; `build.py` writes the `<video>` tags into the page because
  HyperFrames reads media and the length before scripts run. Never a `<video>` inside a timed wrapper.
- A `fromTo` renders its start values at once: a flash or overlay that starts visible needs `set` + `to`.
- A child set `visibility: visible` beats a hidden parent: hide the cards themselves at the end of the montage.
- Text that changes over time (typing, counters) uses one `set` per step, never `onUpdate`: renders seek frames.
- Animate `x`/`y`/`scale`, never `left`/`top` (lint fails it; it stutters).
- A preview player can start muted; the file has sound. Say so when sending.
- Scenes are placed layers: text-fx makes a stage `position: relative`, so placed stages need `position: absolute
  !important` (film.html does this), or they stack under each other.
- The first scene is visible through its own CSS (`style="opacity:1"`), never through a `set` at time 0: two sets on
  one element at 0 can be dropped, and the film opens on an empty frame.
- Anything that starts hidden and comes in with a `fromTo` needs `immediateRender: false`, or its start values show at
  time 0 too (ripples, rings, panels appearing early).
- One `<img>` per image file: the same source in two places fails lint. Copy it (`icon-3.png`, `icon-10.png`).
