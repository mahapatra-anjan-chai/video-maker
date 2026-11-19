# Contributing to Video maker

New skills, fixes and ideas are welcome. Everything is reviewed by the repo's owner before it goes in: nothing you
send changes the repo until it is merged.

## Share a skill from the chat (no code needed)

Made a skill in your copy of Video maker, or improved one? Open a session in the **Video maker** folder and say
**"share my skill"**. Claude (the `share-skill` skill):

1. lists which skills in your folder are new or changed;
2. checks the one you pick against the rules below, and offers to fix anything that doesn't pass (it can write the
   tests for you);
3. helps you sign in to GitHub once (you need a free GitHub account; using Video maker itself doesn't need one);
4. shows exactly what would be published, and waits for your yes;
5. opens the pull request and gives you its link.

Only the skill's folder is sent, built from the repo's own copy, so your videos, keys and company files can't come along.

## By hand (developers)

Fork the repo, make a branch, add your skill, run `npm test` and
`python3 .claude/skills/share-skill/scripts/share.py check <name>`, then open a pull request. The checklist in the
pull request form is the same as the rules here.

## What a skill looks like

```
.claude/skills/<name>/
  SKILL.md              front matter (name, description), then the steps Claude follows
  scripts/              optional: the skill's Python or shell scripts
    tests/__init__.py   imports the test modules: from .test_<name> import *
    tests/test_<name>.py
  CREDITS.md            needed when the skill ships images, fonts or other files you didn't make
```

- **`SKILL.md`** starts with front matter: `name:` (the same as the folder, lower case with dashes) and `description:`
  (what it does, then "Use for ..." with the phrases people will say). Claude reads the description to pick the skill.
- **Everything happens in the chat.** The people using this are product marketers: ask questions with
  AskUserQuestion, show stills and drafts with SendUserFile. No web pages, local servers, Terminal steps or settings
  files. Any paid step (ElevenLabs credits, a paid render) shows its cost and waits for a yes.
- **Tests** for every script: `npm test` finds `scripts/tests/` in every skill on its own and runs
  `python3 -m unittest tests` from `scripts/`. Make the inputs inside the test (tiny generated clips, made-up files),
  use `@unittest.skipUnless(shutil.which("ffmpeg"), ...)` (or `"node"`) for tests that need those tools, and never call
  the network or spend credits. A suite should finish in seconds.
- If the skill should be picked for certain requests, you can suggest a line for `CLAUDE.md`'s "Fast first" list in
  the pull request.

## What can't go in

- Footage, screen recordings, music, sound effects or voiceovers (they belong in `videos/`, which is never committed).
- Keys or tokens of any kind (they live only in `.env`).
- Company names, brand kits or anything from `CLAUDE.local.md`; unreleased product material.
- Styles learned from reference videos (`style-*` skills): they copy someone else's work and stay on your Mac.
- Paths with your Mac user name (`/Users/<name>/...`); use paths inside the project.
- Files over 5 MB.

## Credits and licence

Contributions are shared under the repo's [MIT licence](LICENSE). Anything you didn't make (an image, a font, a
library) needs a line in the skill's `CREDITS.md`: where it is from and its licence, which must allow sharing. A new
skill gets a line in `NOTICE.md` under "What the licence covers" and a row in the README's skills table (the
`share-skill` adds both).

## After you send it

GitHub runs every skill's tests and the sharing check on the pull request. For a first-time contributor the run waits
until the owner allows it. The owner then reviews it and merges it, or asks for changes in the pull request's comments.

Bugs and ideas without code: [open an issue](https://github.com/mahapatra-anjan-chai/video-maker/issues) with what
you were making and what got in the way. Never attach footage you can't share publicly.
