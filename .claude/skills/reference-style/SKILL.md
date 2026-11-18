---
name: reference-style
description: Learn a style from reference videos the creator uploads (an explainer channel they admire, an ad they like) and make the new video in it. Measures pacing, palette and on-screen type, lays out the moments where things move, writes a style card that maps every technique to the 42 text animations, fast-cut features, HyperFrames registry blocks or a component to build. After delivery, it saves the tuned style as its own skill so the next video can say "in the <name> style". Use when the creator shares a reference video, says "make it look like this", "in the style of", "use this as inspiration", or picks a saved style. The ask-first round asks for references on every new video.
---

# Reference style

Take the grammar, never the material: pacing, palette feel, type treatment and motion vocabulary carry over. The
reference's footage, logos, mascots, illustrations, characters, music, sound logo, typeface and frame-for-frame layouts
never do. Run from the project folder with `R=".claude/skills/reference-style/scripts"` and `W="videos/<project>"`.

## When

- **Every new video (not localisations):** the ask-first round includes "Any reference videos whose style you
  want? Drop them in `videos/<project>/refs/`". Saved styles (`.claude/skills/style-*/`) are offered at the look
  question as `ref-<slug>`.
- The creator uploads the file. When they give only a link, ask before downloading (name the file, the source and
  the size), and do not force a download a site refuses.
- **Company videos as references** still follow the inspiration rule in CLAUDE.md. An explicit upload as a reference
  is the yes; say so when you use it.

## The route (adds ~5 minutes before the plan)

1. **Scan each reference:** `python3 $R/style-scan.py --video $W/refs/<ref>.mp4 --out $W/refs/<ref>/`. It takes
   about 10 s per minute of reference and writes the following:
   - `scan.json` and `SCAN.md`:
     - pacing from the kit's `teardown.py`: cuts a minute, shot lengths, bursts, quiet stretches, loudness;
     - the palette, with background and accents;
     - on-screen type: titles separated from small UI text, then size, case, position and words per line.
   - `shots.jpg`: a frame for each shot.
   - `motion.jpg`: 8-frame strips of the busiest moments that are not cuts.
   - `text.jpg`: the biggest type, cropped.
   - `palette.png`.
2. **Look at `motion.jpg` and `shots.jpg`.** Name every technique you see: how titles enter, how emphasis lands,
   camera moves, transitions, textures, overlays and annotation, and what comes in with each new beat. Count them
   from the sheets; no classifier does this better than your eyes. Never claim to have heard the audio from the
   numbers.
3. **Map each technique** (`maps_to` in `style.json`), in this order of preference:
   - `text-animation`: one of the 42 (`text-animations/SKILL.md`);
   - `fast-cut`: a feature and its numbers (zoom scale and ease, headline `intro` with `entrance`, `mark`, text-mask,
     taps);
   - `registry`: a HyperFrames block or component. Search before calling anything custom:
     `npx hyperframes catalog "<what it is>" --json` (grain, paper texture, light leak, highlighter, circle annotation,
     map zoom, wipes);
   - `custom`: a component to build in this video. Write the plan, and once it is built add its file to
     `custom_files` so the saved style keeps it.
4. **Write `$W/refs/style.json`** from `style-template.json`:
   - name, slug and summary;
   - pacing;
   - a `look` block in compose.py's format: colours with roles, and an open-licence font that resembles the
     reference's (Poppins and DM Sans are on hand; pick from Google Fonts otherwise);
   - type: `font_file` paths relative to `.claude/skills/`;
   - techniques and transitions;
   - texture and sound;
   - `text_animations`;
   - `do` and `dont_copy`.

   The slug is descriptive (`collage-explainer`, `bold-kinetic-type`), never a channel or brand name.
5. **Confirm, in the same message as the rest of the plan:**
   - make the card with `python3 $R/style-card.py --style $W/refs/style.json --out $W/refs/card.png`;
   - send it with SendUserFile, together with `motion.jpg`, so the creator can compare;
   - ask one question: "This is the style I'll use; anything to change?".

   Then run `python3 $R/style-save.py look --style $W/refs/style.json`, which makes `ref-<slug>` a look, and write
   `brief.json` `"style_ref": "<slug>"` and `text_animations`.
6. **Make the video** with the usual route (fast-cut or youtube-edit), with:
   - the look `ref-<slug>`;
   - the mapped techniques: install registry items with `npx hyperframes add <item>`, and build custom ones as
     planned;
   - pacing near the reference's median shot length.

   Keep every number tuned on notes in `style.json`, not only in the cut.
7. **After delivery, save the style as a skill:**
   `python3 $R/style-save.py skill --style $W/refs/style.json --preview "<delivered mp4>"`. It writes
   `.claude/skills/style-<slug>/` with SKILL.md, the tuned `style.json`, `card.png`, a `preview.jpg` of OUR video and
   `components/`. Tell the creator its name and that the next video can start with "make it in the <name> style".

## Rules

- References and their sheets stay in `videos/` (gitignored). Saved `style-*` skills and `ref-*` looks are
  gitignored too. Publish one only when the creator asks, after checking that it names no brand and holds no
  reference frames.
- The style card never shows reference frames. The scan sheets are for the creator's eyes in the chat only.
- With two or more references, scan each one. Keep what they share, and say which reference each technique came
  from.
- A reference sets the style, not the content: the brief, the footage and the brand rules still decide what is said
  and shown. For work videos, brand rules beat the reference where they clash (colours, logo, type).
