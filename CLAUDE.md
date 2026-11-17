# Video maker

My video editing system: HyperFrames (local renders) + FFmpeg + Epidemic Sound (connector) + ElevenLabs (API).

- **Any video request in this folder goes through the `youtube-edit` skill** (`.claude/skills/youtube-edit/SKILL.md`),
  starting with its "Before every video: ask first" section. The global HyperFrames skills (`hyperframes`,
  `hyperframes-core`, `media-use`, ...) are reference for composition details only; they do not replace this workflow.
- **The HyperFrames connector (cloud `compose` / `render_video`) is not the editor:** it cannot cut or transcribe my
  footage and `render_video` is paid. Edit and render locally with `npx hyperframes`.
- **Epidemic Sound connector** is the first stop for music and sound effects; the free HyperFrames sounds are in
  `videos/_shared/sfx/`; `elevenlabs.py sfx` generates anything missing (after a yes on the cost).

## Fast first
- **Footage that already shows the right thing** (a screen recording to cut, speed up, reframe or caption): the
  `fast-cut` skill. One labelled contact sheet, an automatic scan, one cut table, a draft in seconds.
- **Screens that must change** (new copy inside the UI, removed elements): the youtube-edit skill and HyperFrames.
- **Quick mode for short ads:** no separate question round when the brief has the copy and assets; state defaults
  instead of asking, and put the Personal/Office confirmation in the same message as the plan. First draft within
  ~15 minutes, then iterate on notes. Take every still in ONE `hyperframes snapshot --at a,b,c --no-end` run, never one
  run per moment. Verify only the final.

## Ask first, every video
1. Personal or office (`brief.json` `purpose`, set on the page). Office = for Glance: Glance look offered first, brand
   rules apply, and confirm the music and voice accounts are cleared for company use. Personal = no Glance branding.
2. Which look: Kit, Glance or Mine (the storyboard's `"style"`), even if `brief.json` names one.
3. Before using any Glance video as inspiration or reference: name it and wait for a yes.
4. Before any ElevenLabs generation or AI B-roll: show the plan and cost, wait for a yes.

## Where things are
- `npm run ui` → http://localhost:4500: the upload page. Inputs land in `videos/<project>/` (`raw/`, `img/`, `audio/`,
  `docs/`, `script.txt`, `brief.json`, `scenes.json` = my scene cards). Removed files go to `videos/<project>/.trash/`.
- Claude writes `scene-plan.json` (+ stills via `scenes.py snap`) and `music.json` (the Epidemic pick); the page shows
  both before rendering. "Update my video" on the page means cards changed or I picked another track.
- Finished videos: `~/Movies/YouTube Renders/<project>/<project>-v<N>-4k.mp4`, one file per version, never overwritten;
  the page lists them with Download. Each version's storyboard is kept in `videos/<project>/versions/v<N>/`.
- Looks: `.claude/skills/youtube-edit/styles/{kit,glance,mine}.json`; rules in `kit/STYLE-GUIDE.md`.
- Secrets: `.env` (`ELEVENLABS_API_KEY`). Never print it or commit it.
- `npm test` runs the skill's tests (must end `OK`); `npm run doctor` checks HyperFrames.

## Watch the disk
About 45 GB free. Hooks and short sections are fine; over ~2 minutes of 4K use the streaming / segmented render flags
in SKILL.md ("Traps that waste a render") and clear `hyperframes-extract-cache-*` in the temp folder when no render runs.
