# What the licence covers

The MIT licence in `LICENSE` covers Video maker's own work:

- `.claude/skills/fast-cut/` (scripts, tests, skill)
- `.claude/skills/text-animations/` (the animations, picker, gallery and scripts; the list of effects follows the
  "Claude + Figma Motion: Text Animations" board curated by Shlomo Genchin, Unbore.com)
- `.claude/skills/localize/` (scripts, tests, skill and the voice list)
- `.claude/skills/reference-style/` (scripts, tests, skill and the style template)
- `docs/` (the visuals, the demo and the scripts that make them)
- `setup.sh`, `README.md`, `CLAUDE.md`, `package.json`
- In `.claude/skills/youtube-edit/`: `scripts/elevenlabs.py`, `scripts/narration-video.py`, `scripts/scenes.py`,
  and the look presets in `styles/` (`brand.json`, `kit.json`, `mine.json`)

## Third-party parts, under their own terms

| Part | Where | Terms |
|---|---|---|
| WeAreNoCode YouTube Editor kit | `kit/` and the rest of `.claude/skills/youtube-edit/` | Belongs to its author. Some scripts started from an open-source starter kit under MIT (`kit/LICENSES/MIT-starter-kit.txt`); the rest is not covered by this repo's licence. Changes made here to those files are offered under MIT, but the kit's own content is not ours to license. |
| DM Sans | `.claude/skills/youtube-edit/assets/fonts/` | SIL Open Font License (`kit/LICENSES/OFL-DM-Sans.txt`) |
| Noto Sans JP | `.claude/skills/localize/fonts/` (fetched by `setup.sh`, not committed) | SIL Open Font License (`OFL.txt` next to it) |
| Demucs | installed on first use by `localize/scripts/separate.sh` into its own venv | MIT (Meta) |
| Poppins | `.claude/skills/fast-cut/assets/fonts/`, `.claude/skills/youtube-edit/styles/brand/fonts/` | SIL Open Font License (`OFL.txt` next to the fonts) |
| Sound effects | `videos/_shared/sfx/` (fetched by `setup.sh`, not committed) | Pixabay Content License |
| GSAP | fetched by `setup.sh`, not committed | GSAP's standard licence |

Music from Epidemic Sound and voices from ElevenLabs are used under your own accounts and plans; none ship with this repo.
