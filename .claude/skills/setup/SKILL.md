---
name: setup
description: Set up Video maker on a Mac for someone who is not technical, entirely in the chat. Gets the code, installs every tool inside the project folder (no Homebrew, no admin password, no Terminal), walks them through a free ElevenLabs account for voiceovers, renders the demo as proof, and tells them how to start their first video. Use for "set up Video maker", "install this", "get me started", "it doesn't work after cloning", "first run", or when a tool (python3 with Pillow, ffmpeg, npx) is missing in this folder.
---

# Setup, in the chat

The person is a product marketer, not a developer. Everything happens in this chat: plain words, one question at a
time (AskUserQuestion), progress in short lines, files they should look at sent with SendUserFile. Never send them to a
web page you host, a local server, a Terminal window or a settings file, and never ask them to type a command.

## 1. Get the code (skip when the session is already inside the project)

Put it in `~/Documents/Video maker` unless they named a place.

- With git: `git clone https://github.com/mahapatra-anjan-chai/video-maker.git ~/Documents/"Video maker"`
- If `git` is missing (on a new Mac it pops up an "install developer tools" window instead of running), use the zip:
  `cd ~/Documents && curl -fsSL -o video-maker.zip https://github.com/mahapatra-anjan-chai/video-maker/archive/refs/heads/main.zip && unzip -q video-maker.zip && mv video-maker-main "Video maker" && rm video-maker.zip`
- Already there: `git -C ~/Documents/"Video maker" pull` (or leave it as it is when it is not a git copy).

## 2. Install everything: `bash setup.sh --json`

Run it from the project folder. The first run takes 3 to 8 minutes. Say so, in one line ("Installing the video tools
into your project folder, about five minutes; nothing needs your password"). It is safe to run again.

What it does, so you can explain it if asked:
- uses FFmpeg 7+, Node 22+ and Python 3.10+ with Pillow and numpy when the Mac already has them;
- otherwise downloads pinned, checksum-verified copies into `.tools/` (FFmpeg, Node, uv) and `.venv/` (Python 3.12);
- installs HyperFrames, its render browser and the speech-to-text model, the free sound effects, GSAP and a font;
- writes `.tools/env.sh`, which puts those tools first; and runs every skill's self-test.

Its last line is JSON: `{"ready": true|false, "done": [...], "missing": [{"what", "why"}]}`. Relay it in plain words:
what is ready, what is optional, what failed. When something failed, run it again once (most failures are a dropped
download), then tell them the one thing that is wrong.

## 3. Voiceovers (optional): a free ElevenLabs account

Ask with AskUserQuestion: "Do you want AI voiceovers in your videos?" (Yes, set it up / Not now).

On yes, walk them through it, one step per message:
1. Make a **free** account at elevenlabs.io (Sign up). The free plan gives 10,000 credits a month. On a free account
   the project uses the Flash voice model (half the credits), so that is about 20 minutes of narration a month.
2. In ElevenLabs: profile icon (bottom left) → **API Keys** → **Create API Key**. Name it "Video maker". Under
   permissions turn on **Text to Speech** and **User: Read** (so you can show the credits left), leave the rest off.
   Copy the key.
3. Run `open -e .env`. TextEdit opens a small file: paste the key right after `ELEVENLABS_API_KEY=`, press ⌘S, close it.
   **The key goes in that file, never in the chat.** If they paste it into the chat anyway, do not repeat it: write it
   into `.env` yourself and suggest they make a new key later, since the chat keeps a copy.
4. Check it without printing it: `python3 .claude/skills/youtube-edit/scripts/elevenlabs.py balance` and tell them the
   credits left.

Say once, plainly: the free plan is for personal use. Videos their company publishes need ElevenLabs' Starter plan
($6 a month, 30,000 credits, commercial licence). Never suggest buying anything beyond stating that.

## 4. Music (optional)

Free sound effects are already in the project. For licensed music: "In the Claude app, open Settings → Connectors and
connect Epidemic Sound (needs your own Epidemic account). Without it, videos use free music and sounds."

## 5. Proof: the demo

Run `python3 docs/demo/make-demo.py` (about 15 seconds). Send `docs/demo/work/render/shopwise-demo.mp4` and
`docs/demo/work/review/overview.png` with SendUserFile: "This was made on your Mac just now from a pretend app's
recording. Yours will look like this."

## 6. Into the project folder, then the first video

Settings and the tool PATH load when a chat starts in the project folder. If this chat is somewhere else, tell them:
"Start a new chat: Code tab → New session → choose the **Video maker** folder in Documents." (When the app gives you a
tool to change the session's folder, use it instead.)

Then, in one message, how a video starts: "Drag a screen recording into the chat (or tell me where it is) and say what
the feature is for. I'll ask a few questions here, show you the plan, and send the draft back in this chat."

## Rules for every chat in this project

- When `python3 -c 'import PIL'`, `ffmpeg` or `npx` is missing, load the project's tools first:
  `. .tools/env.sh 2>/dev/null; <command>`. If `.tools/env.sh` does not exist yet, run `bash setup.sh --json`.
- Voiceover credits: show the full script, get a yes, generate once. The model follows their plan (Flash on free
  accounts, half the credits; Multilingual v2 on paid ones). Show the plan, the cost and the credits left, and wait for
  a yes. Never generate voice samples to choose a voice: they listen free on elevenlabs.io → Voices. `--draft` (the
  Mac's own voice, free) only when they want to hear the timing before approving the script.
