# Video maker

Drop in your footage, Claude does the edit. Runs on this Mac: HyperFrames renders, FFmpeg cuts, Epidemic Sound for
music, ElevenLabs for voiceovers and sound effects.

## Set up (after cloning)

You need a Mac with Homebrew, Google Chrome and Claude Code.

```bash
git clone https://github.com/mahapatra-anjan-chai/video-maker.git
```

```bash
cd video-maker && ./setup.sh
```

`setup.sh` checks Node 22+, FFmpeg, Python with numpy and auto-editor (it prints the `brew` command for anything
missing), installs HyperFrames and its Parakeet transcriber, fetches the free sound effects and GSAP, creates `.env`
from `.env.example`, and runs the tests. Put your ElevenLabs key in `.env`. For music, connect the Epidemic Sound
connector in Claude (optional; without it Claude uses the free sound library).

## Make a video

1. Open the upload page:

   ```bash
   npm run ui
   ```

   then go to http://localhost:4500 (dark workspace in Glance colours; the earlier light page is at http://localhost:4500/light).
2. Name the video, drop in your files (clips, screen recordings, images, music, documents), paste a voiceover script if
   you want one, pick a look and a shape, add notes, and add a scene card for each animation you want ("when I say
   pricing" → "show our pricing page in a browser"). Click **Save project** (or ⌘S); it also saves as you type.
3. Open Claude Code in this folder and say what the page tells you, for example: `Edit my video "glance-launch"`.
4. Claude asks which look to use, then puts its plan back on the page: under each scene card what it will build, with
   stills, and in Background music the Epidemic Sound track it picked, why it fits, a preview and two alternatives.
   Change a card or pick another track, and the page tells you to say `Update my video "…"`.
5. After you approve, Claude renders. Every version appears on the page with a **Download** button (newest marked
   Latest) and in `~/Movies/YouTube Renders/`.
6. Give notes in plain words ("at 0:22 the text is too small"). Say **"save this to the skill"** to make a note stick.

## Fast cuts

When a recording only needs cutting (trim, speed up the loading, reframe to 9:16, add a line of text), Claude uses the
`fast-cut` skill: one contact sheet, an automatic scan that speeds up the still stretches, a cut list, and a draft in
seconds. Say "fast cut this" with the file.

## The parts

| Folder | What it is |
|---|---|
| `.claude/skills/youtube-edit/` | The editing skill (from the WeAreNoCode kit), plus style presets, ElevenLabs and narration scripts |
| `.claude/skills/fast-cut/` | Fast edits of recordings: contact sheet, still-stretch scan, cut list, one-pass FFmpeg render |
| `ui/` | The upload page (Node, no packages) |
| `videos/` | One folder per video; `_shared/sfx` holds reusable sounds (your videos are never committed) |
| `kit/` | The kit's style guide, prompts and licences |
| `setup.sh` | One-time setup after cloning |

Every video starts with one check: **Personal or Office**. Office videos are made for Glance, so the Glance look and
brand rules apply and Claude confirms the music and voice accounts are cleared for company use.

## Credits

The editing skill comes from the WeAreNoCode YouTube Editor kit (`kit/README.md`); parts of its scripts are under the
MIT licence in `kit/LICENSES/`. Fonts: DM Sans and Poppins (SIL Open Font License). The Glance colours, rules and logo
images in `.claude/skills/youtube-edit/styles/glance/` belong to Glance.
