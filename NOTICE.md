# What the licence covers

The MIT licence in `LICENSE` covers Video maker's own work:

- `.claude/skills/fast-cut/` (scripts, tests, skill)
- `.claude/skills/text-animations/` (the animations, picker, scene planner, gallery and scripts; the list of effects follows the
  "Claude + Figma Motion: Text Animations" board curated by Shlomo Genchin, Unbore.com)
- `.claude/skills/localize/` (scripts, tests, skill and the voice list)
- `.claude/skills/reference-style/` (scripts, tests, skill and the style template)
- `.claude/skills/launch-demo/` (template, scripts, tests, skill and examples), except `vendor/devices.css` (below)
- `.claude/skills/storyboard/` (script, tests, skill)
- `.claude/skills/share-skill/` (scripts, tests, skill), except `gh`, which `get-gh.sh` downloads (GitHub's MIT licence)
- `.claude/skills/setup/` and `docs/demo/photos/CREDITS.md`
- `docs/` (the visuals, the demo and the scripts that make them)
- `setup.sh`, `tests.sh`, `README.md`, `CONTRIBUTING.md`, `CLAUDE.md`, `package.json`, `.github/`
- In `.claude/skills/youtube-edit/`: `scripts/elevenlabs.py`, `scripts/narration-video.py`, `scripts/scenes.py`,
  and the look presets in `styles/` (`brand.json`, `kit.json`, `mine.json`)

## Third-party parts, under their own terms

| Part | Where | Terms |
|---|---|---|
| WeAreNoCode YouTube Editor kit | `kit/` and the rest of `.claude/skills/youtube-edit/` | Belongs to its author. Some scripts started from an open-source starter kit under MIT (`kit/LICENSES/MIT-starter-kit.txt`); the rest is not covered by this repo's licence. Changes made here to those files are offered under MIT, but the kit's own content is not ours to license. |
| DM Sans | `.claude/skills/youtube-edit/assets/fonts/` | SIL Open Font License (`kit/LICENSES/OFL-DM-Sans.txt`) |
| devices.css 0.2.0 (the iPhone frame) | `.claude/skills/launch-demo/vendor/devices.css` | MIT, Yan Zhu (`vendor/devices-LICENSE.txt`) |
| Shopwise demo product photos | `docs/demo/photos/` | CC0 (public domain); sources in `docs/demo/photos/CREDITS.md` |
| Stock footage in the launch video's highlights | `docs/images/launch-demo.gif` (the opening shots) | Mixkit clips 25575 and 39854, Mixkit Stock Video Free License; not covered by this repo's licence |
| Noto Sans JP | `.claude/skills/localize/fonts/` (fetched by `setup.sh`, not committed) | SIL Open Font License (`OFL.txt` next to it) |
| Demucs | installed on first use by `localize/scripts/separate.sh` into its own venv | MIT (Meta) |
| Poppins | `.claude/skills/fast-cut/assets/fonts/`, `.claude/skills/youtube-edit/styles/brand/fonts/` | SIL Open Font License (`OFL.txt` next to the fonts) |
| Sound effects | `videos/_shared/sfx/` (fetched by `setup.sh`, not committed) | Pixabay Content License |
| GSAP | fetched by `setup.sh`, not committed | GSAP's standard licence |

Music from Epidemic Sound and voices from ElevenLabs are used under your own accounts and plans; none ship with this repo.
