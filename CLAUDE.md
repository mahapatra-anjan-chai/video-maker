# Video maker

A video editing system for product marketing: HyperFrames (local renders) + FFmpeg + Epidemic Sound (connector) +
ElevenLabs (API), driven from Claude Code.

**First, if `CLAUDE.local.md` exists, read it:** it names the creator's company, its brand kit and any local rules.
It is never committed.

**New here, or a tool is missing?** Use the `setup` skill (`.claude/skills/setup/SKILL.md`): it installs everything
inside this folder with `bash setup.sh` (no Homebrew, no admin password) and walks the person through it in the chat.
When `python3` lacks Pillow, or `ffmpeg` / `npx` is not found, prefix the command with `. .tools/env.sh 2>/dev/null;`.

**Everything happens in this chat.** The people using this are product marketers, not developers: ask with
AskUserQuestion, show stills, sheets and drafts with SendUserFile, use the in-chat text-animation picker and scene
planner, and for a film built from scenes, a storyboard before the render. Never open or point them to a web page, a
local server, `hyperframes preview` / Studio, a Terminal window or a settings file, and never ask them to type a command.

- **Any video request in this folder goes through the `youtube-edit` skill** (`.claude/skills/youtube-edit/SKILL.md`),
  starting with its "Before every video: ask first" section. The global HyperFrames skills (`hyperframes`,
  `hyperframes-core`, `media-use`, ...) are reference for composition details only; they do not replace this workflow.
- **The HyperFrames connector (cloud `compose` / `render_video`) is not the editor:** it cannot cut or transcribe the
  footage and `render_video` is paid. Edit and render locally with `npx hyperframes`.
- **Epidemic Sound connector** is the first stop for music and sound effects; the free sounds are in
  `videos/_shared/sfx/` (`setup.sh` fetches them); `elevenlabs.py sfx` generates anything missing (after a yes on the cost).

## Fast first
- **Footage that already shows the right thing** (a screen recording to cut, speed up, reframe or caption): the
  `fast-cut` skill. One labelled contact sheet, an automatic scan, one cut table, a draft in seconds. It also adds tap
  ripples (with a click in the mix), zooms on the feature being explained, and section headlines that open full screen
  and glide to the top.
- **Screens that must change** (new copy inside the UI, removed elements): the youtube-edit skill and HyperFrames.
- **A launch demo** (a 60-90 s announcement: the pain, the product's name, the feature on an iPhone, a montage on the
  music's drop, a logo lockup on the music's final hit): the `launch-demo` skill. It is the recipe of Video maker's own
  demo, so launch videos look the same whoever makes them. A 16:9 launch film of text and music (no voice) is its
  `film.py`: built from a scene plan, each scene's line in its own animation, transitions on the music's beats.
- **See a film before it renders:** the `storyboard` skill, for films built from a scene plan (`film.json`, with the
  timing `film.py` writes). One snapshot pass gives a sheet of every scene as it lands, a
  sheet of every transition frame by frame and a short clip of them playing, sent in the chat in seconds to minutes;
  notes come back by scene number and only those scenes are taken again.
- **A finished video in another language** (new voiceover and subtitles, same picture): the `localize` skill.
  The voice is separated out of the mix so the music stays, every line is dubbed into its original slot with a voice
  per character, and a frosted band covers the burned-in subtitles with the translated ones. Ask yes on the
  ElevenLabs cost; on-screen copy stays as is.
- **Watching a video from a link** (what a reference or a competitor's video says and shows): the Watch plugin
  (`/watch`), if installed on this Mac (it is not part of this repo). Always `--engine local` for anything in
  `videos/`, work projects or company material; its Gemini engine uploads the video to Google, so only for a public
  link the person picked. Its keys go in `~/.config/watch/.env`, opened with `open -t`, never in the chat. It looks at 2
  frames a second at most, so it cannot see easing: motion timing comes from `reference-style`'s `motion.py`.
- **A mascot moment** (a character scrolling an endless feed on a phone, slicing through it and landing in the next
  scene with a shopping bag): the `mascot-story` skill. One `story.json`, one command, an MP4 and a GIF in about a minute.
- **Sharing a skill with the repo** ("share my skill", "send this to Video maker"): the `share-skill` skill. It checks
  the skill, shows what would be published, and opens a pull request only after a yes. Never push to the repo for them.
- **Quick mode for short ads:** no separate question round when the brief has the copy and assets; state defaults
  instead of asking, and put the Personal/Work confirmation in the same message as the plan. First draft within
  ~15 minutes, then iterate on notes. Take every still in ONE `hyperframes snapshot --at a,b,c --no-end` run, never one
  run per moment. Verify only the final.
- **Review in the chat:** after a render, send the `fast-cut/scripts/review.py` sheets (headlines, taps, zooms,
  overview) and the moments clip with SendUserFile. Notes come back as timestamps.

## Ask first, every video
1. Personal or work (`brief.json` `purpose`: `personal` | `office`). Work = for the company: its look offered first,
   brand rules apply, confirm the music and voice accounts are cleared for company use, and unreleased product footage
   never leaves this machine. Personal = no company branding.
2. Any reference videos whose style they want? (Ask in the same first message; skip it for localisations.) They drop
   them in `videos/<project>/refs/`, and the `reference-style` skill (pacing, palette, type, and every move's ease
   and length measured at the full frame rate) turns them into a style card and a look
   (`ref-<slug>`) before the plan. Saved styles (`.claude/skills/style-*/`) are offered as looks.
   Which look: Kit, Brand (or the company kit named in `CLAUDE.local.md`), Mine, or a saved `ref-<slug>` style (the
   storyboard's `"style"`). After delivering a video made from a reference, save its style as a skill
   (`reference-style`, step 7).
3. Before using any of the company's own videos as inspiration or reference: name it and wait for a yes.
4. Before any ElevenLabs generation or AI B-roll: show the plan and cost, wait for a yes. Spend as few credits as
   possible (most people are on the free plan, 10,000 credits a month). The flow is the same for everyone: show the
   full script, get a yes, generate once. The model follows the plan (`--model auto`): Flash on free accounts (half the
   credits), the richer Multilingual v2 on paid ones (`ELEVENLABS_MODEL` in `.env` overrides). Only changed lines are paid
   for again; never generate samples to pick a voice (they listen free on elevenlabs.io → Voices); show the credits
   left (`elevenlabs.py balance`). `--draft` (the Mac's own voice, free) only when someone wants to hear the timing
   before approving the script.
5. Which text animations: show the `text-animations` picker (live previews of all 58 and the backgrounds, a dropdown
   by group) and save the pick in `brief.json` `text_animations`. A film built from scenes gets the scene planner
   instead: each scene's own line in its animation, the transition into the next scene and the background, in the
   video's colours; the picks come back as one line for `film.json`. Then a storyboard of the built film before any
   render.

## Where things are
- One folder per video: `videos/<project>/` with `raw/` (clips, screen recordings), `refs/` (reference videos for the
  style), `img/`, `audio/`, `docs/`,
  `script.txt` (voiceover), `brief.json` (purpose, look, shape, notes) and `scenes.json` (moments to animate); a film
  built from scenes has `film.json` (its scene plan and timing) and `review/` (planner, storyboard, transitions).
  Claude writes `cut.json` / `storyboard.json`, `scene-plan.json` and `music.json` there.
- Finished videos: `~/Movies/YouTube Renders/<project>/<project>-v<N>-<size>.mp4`, one file per version, never
  overwritten; each version's cut or storyboard is kept in `videos/<project>/versions/v<N>/`.
- Looks: `.claude/skills/youtube-edit/styles/{kit,brand,mine}.json`; rules in `kit/STYLE-GUIDE.md`.
- Secrets: `.env` (`ELEVENLABS_API_KEY`). Never print it or commit it. Reading it is blocked in `.claude/settings.json`
  (so Edit can't open it either); change a line (like `ELEVENLABS_MODEL=`) with a one-line Python write through Bash that
  never prints the file.
- `npm test` runs every skill's tests (`tests.sh` finds them; must end `OK`); `npm run doctor` checks HyperFrames.
  New skills follow `CONTRIBUTING.md` (SKILL.md front matter, `scripts/tests/`, credits, nothing private).

## Watch the disk
Hooks and short sections are fine; over ~2 minutes of 4K use the streaming / segmented render flags in SKILL.md
("Traps that waste a render") and clear `hyperframes-extract-cache-*` in the temp folder when no render runs.
