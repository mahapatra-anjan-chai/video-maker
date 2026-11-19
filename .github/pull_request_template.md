## What this adds or changes

<!-- One or two sentences: what the skill does, and when Claude should use it. -->

## Checklist

- [ ] Everything new is inside `.claude/skills/<name>/` (a new skill also gets one line in `NOTICE.md` and one row in the README's skills table)
- [ ] `SKILL.md` starts with `name:` (the folder's name) and `description:` (what it does and when to use it)
- [ ] Scripts have tests in `scripts/tests/`, and `npm test` ends `OK`
- [ ] `python3 .claude/skills/share-skill/scripts/share.py check <name>` says "ready to share"
- [ ] No footage, music, sound effects, voiceovers, keys, company or brand material, or `/Users/<name>/` paths
- [ ] Images and fonts are credited in the skill's `CREDITS.md` (source, and a licence that allows sharing)
- [ ] It works from the chat: questions with AskUserQuestion, results with SendUserFile, no web pages or servers
- [ ] I'm sharing this under the repo's MIT licence

<!-- Made with the share-skill skill? It fills this in for you. -->
