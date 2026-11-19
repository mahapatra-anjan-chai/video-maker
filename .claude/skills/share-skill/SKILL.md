---
name: share-skill
description: Send a skill made in this folder (or an improvement to an existing one) to the Video maker repo as a pull request, all from the chat. It checks the skill against the repo's rules (no footage, sounds, keys, Mac user names or company names; credits for images and fonts; tests for scripts), shows exactly what would be published, and opens the pull request only after a yes. Works for git and zip installs. Use for "share my skill", "send my skill to Video maker", "contribute this skill", "open a pull request", "add my skill to the repo".
---

# Share a skill

Everything happens in the chat. Run from the project folder with `S=".claude/skills/share-skill/scripts"`. The pull
request is built on GitHub from the repo's own main branch: only the skill's folder goes (plus one line in NOTICE.md and
one row in the README's skills table for a new skill), never anything else in this folder.

## 1. Which skill

`python3 $S/share.py list` says which skills here are **new** or **changed** compared with the repo. Offer those with
AskUserQuestion. `style-*` skills are listed as private: they are styles learned from other people's videos and stay on
this Mac; say so if asked, and never share one.

## 2. Check it

`python3 $S/share.py check <skill>` runs the rules and the skill's tests.
- **✗ items must be fixed before anything is sent.** Offer to fix each one and do it after a yes: write the missing
  tests (`scripts/tests/__init__.py` importing `test_*.py`, `skipUnless` for FFmpeg or Node, no network, no credits),
  add a `CREDITS.md` line for an image or font (where it is from and its licence; ask the person, never guess a
  licence), remove a company name or a `/Users/<name>/` path, take out a video or sound file. Then check again.
- **? items:** ask the person (an email address in the files, a large file).
- The skill becomes public under the repo's MIT licence. Say so plainly.

## 3. GitHub account and the gh tool

- Ask whether they have a GitHub account. If not: they make a free one at github.com/signup themselves (their email,
  their password); wait until they say it's done. Never create an account or type a password for them.
- `command -v gh || ls .tools/bin/gh`: if neither exists, `bash $S/get-gh.sh` (GitHub's own tool, about 15 MB, pinned
  and checksum-checked, into `.tools/bin`). Use `.tools/bin/gh` when `gh` is not on the PATH.

## 4. Sign in to GitHub (once per Mac)

`gh auth status` (exit 0 = signed in; skip this step). Otherwise, this is the one time a web page opens:
1. Run in the background (Bash `run_in_background`):
   `gh auth login --web --clipboard --hostname github.com --git-protocol https </dev/null`
2. Read its output file for the line `First copy your one-time code: XXXX-XXXX`, then `open https://github.com/login/device`.
3. Tell them: "A GitHub page opened. Paste the code XXXX-XXXX (it's already copied), sign in if asked, and click
   Authorize." Wait for the background command to finish (exit 0 = signed in).
The sign-in stays in the Mac's keychain. Never ask for a password or token in the chat.

## 5. Show the plan, get a yes

`python3 $S/share.py plan <skill>` gives the file list, the pull request's title and text, the GitHub account, and
whether a fork is needed (`"fork": true` for everyone without push access to the repo). Show it in the chat in plain
words: "This makes a public copy of Video maker under your GitHub account (`<account>`), adds these N files, and asks
the owner to merge them. The skill will be public under the MIT licence." Then AskUserQuestion: send / not yet.
`"nothing_to_send": true` means the repo already has it exactly; say so and stop.

## 6. Send

Only after the yes: `python3 $S/share.py send <skill> --yes`. It forks (or branches, with push access), makes one
commit from the repo's main, and opens the pull request. Give them the link from `url`, and say:
- the owner reviews it and may ask for changes in the pull request's comments;
- GitHub runs every skill's tests on it once the owner allows the run (needed for first-time contributors);
- to send changes later, fix them here and share again: it opens a new pull request, and they can close the old one
  on its page.

## Rules

- Nothing goes to GitHub without the yes in step 5; `send` refuses without `--yes` and refuses while the check fails.
- Never share `style-*` skills, anything from `videos/`, `.env`, `CLAUDE.local.md` or the company's brand files.
- The person's GitHub sign-in is theirs: never sign out, change settings or act on other repos.
