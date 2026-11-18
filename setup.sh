#!/usr/bin/env bash
# One-time setup after cloning: checks the tools, installs what can be installed without admin rights,
# fetches the free sound effects and GSAP, creates .env, and runs the skill's tests.
set -u
cd "$(dirname "$0")"
SK=".claude/skills/youtube-edit"
ok() { printf "  \033[32m✓\033[0m %s\n" "$1"; }
no() { printf "  \033[31m✗\033[0m %s\n      %s\n" "$1" "$2"; MISSING=1; }
MISSING=0

echo "Checking tools"
node -e 'process.exit(+process.versions.node.split(".")[0] >= 22 ? 0 : 1)' 2>/dev/null && ok "Node $(node -v)" || no "Node.js 22 or newer" "brew install node"
command -v ffmpeg >/dev/null && ok "FFmpeg" || no "FFmpeg" "brew install ffmpeg"
python3 -c "import numpy" 2>/dev/null && ok "Python 3 with numpy" || no "Python 3 with numpy" "brew install numpy"
python3 -c "import PIL" 2>/dev/null && ok "Python 3 with Pillow" || no "Python 3 with Pillow" "brew install pillow"
command -v auto-editor >/dev/null && ok "auto-editor" || no "auto-editor" "brew install auto-editor"
[ -d "/Applications/Google Chrome.app" ] && ok "Google Chrome" || no "Google Chrome" "https://www.google.com/chrome/"

echo "Installing HyperFrames and the Parakeet transcriber"
npm install --silent && ok "npm packages (HyperFrames $(npx hyperframes --version 2>/dev/null))"
npx hyperframes models install parakeet </dev/null >/dev/null 2>&1 && ok "Parakeet model" || no "Parakeet model" "npx hyperframes models install parakeet"

echo "Free sound effects (HyperFrames library, Pixabay licence)"
npx hyperframes skills update media-use </dev/null >/dev/null 2>&1
SFX="$HOME/.claude/skills/media-use/audio/assets/sfx"
mkdir -p videos/_shared/sfx
if [ -d "$SFX" ]; then
  for f in pop click click-soft typing key-press ping notification chime; do cp "$SFX/$f.mp3" videos/_shared/sfx/ 2>/dev/null; done
  ok "sound effects in videos/_shared/sfx"
else
  no "sound effects" "npx hyperframes skills update media-use, then copy from $SFX"
fi

echo "GSAP (animation library the composer uses; renders work offline with a local copy)"
mkdir -p "$SK/assets/vendor"
curl -sfL https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js -o "$SK/assets/vendor/gsap.min.js" && ok "GSAP 3.14.2" || no "GSAP" "the page falls back to the CDN"

echo "Noto Sans JP (subtitles for Japanese versions, SIL Open Font License)"
JP=".claude/skills/localize/fonts/NotoSansJP.ttf"
[ -f "$JP" ] || curl -sfL "https://github.com/google/fonts/raw/main/ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf" -o "$JP"
[ -f "$JP" ] && ok "Noto Sans JP" || no "Noto Sans JP" "download NotoSansJP[wght].ttf from Google Fonts into $JP"
echo "  (the localize skill makes its Demucs voice separator venv on first use, ~1 GB)"

echo "Keys"
[ -f .env ] || cp .env.example .env
grep -qE '^ELEVENLABS_API_KEY=.+' .env && ok ".env has an ElevenLabs key" || no "ElevenLabs key" "put ELEVENLABS_API_KEY=... in .env (voiceover and sound effects need it)"

echo "Running the skills' tests"
( cd "$SK/scripts" && python3 -m unittest tests 2>&1 | tail -1 )
( cd ".claude/skills/fast-cut/scripts" && python3 -m unittest tests 2>&1 | tail -1 )
( cd ".claude/skills/localize/scripts" && python3 -m unittest tests 2>&1 | tail -1 )

echo
[ "$MISSING" = 0 ] && echo "All set. Put your recording in videos/<name>/raw/ and tell Claude Code: Edit my video \"<name>\"" \
                   || echo "Install the items marked ✗, then run ./setup.sh again."
echo "In Claude, connect the Epidemic Sound connector for music (optional), and open Claude Code in this folder."
