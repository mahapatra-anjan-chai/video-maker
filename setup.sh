#!/usr/bin/env bash
# Video maker setup for a Mac. Every tool goes inside this folder (.tools/ and .venv/): no Homebrew, no admin password,
# no Terminal steps. Tools the Mac already has are used when they are new enough. Safe to run again at any time.
#
#   bash setup.sh            set up (or repair) everything and say what was done
#   bash setup.sh --check    only report what is missing
#   bash setup.sh --json     the same report as JSON on the last line (for Claude to relay in the chat)
#
# Downloads are pinned and checked against SHA-256 before use: FFmpeg (martin-riedl.de static build), Node (nodejs.org),
# uv (astral.sh, GitHub release), which brings Python 3.12 and installs Pillow and numpy into .venv.
set -u
cd "$(dirname "$0")"
ROOT="$(pwd)"
MODE=install; JSON=0
for a in "$@"; do case "$a" in --check) MODE=check ;; --json) JSON=1 ;; esac; done
TOOLS="$ROOT/.tools"; BIN="$TOOLS/bin"; DL="$TOOLS/downloads"
mkdir -p "$BIN" "$DL"
export PATH="$BIN:$ROOT/.venv/bin:$PATH"
ARCH="$(uname -m)"                                   # arm64 (Apple silicon) or x86_64 (Intel)

# ---- pinned downloads -------------------------------------------------------------------------------------------
NODE_VER=22.23.5
UV_VER=0.13.9
if [ "$ARCH" = arm64 ]; then
  NODE_PKG=node-v$NODE_VER-darwin-arm64; NODE_SHA=e7131995759b61a0170b646010d2ad35a5d37b4cb0d471f3e8317eac6f742f3d
  UV_PKG=uv-aarch64-apple-darwin;         UV_SHA=5aeca67f2283f75235de40d0bd9c0a5bbc5fce23b6d48b3bf9fa1b2db08382ca
  FF_URL=https://ffmpeg.martin-riedl.de/download/macos/arm64/1789931890_9.0.2
  FF_SHA=c8ed4c4e6978a03c485edbfe4e0a5dc2380f8a30bba5150531b31b094492d924
  FP_SHA=fcbe839537485eaee7a7a8bc5cbc0f90d53617e80943e8a5b2e31cb851197ea6
else
  NODE_PKG=node-v$NODE_VER-darwin-x64;    NODE_SHA=c53383238206b9ae4db23c5d8a63645e2e753bec8ab51a49cc81939aa64e9422
  UV_PKG=uv-x86_64-apple-darwin;          UV_SHA=617a3211261b0fc739562f0071aa34e9739797c510208ede8e2977c30903d041
  FF_URL=https://ffmpeg.martin-riedl.de/download/macos/amd64/1789931006_9.0.2
  FF_SHA=7c6b4125b191cbf773832dc51f424cf2b6bb7da43007d1e066f95909e47cacd4
  FP_SHA=2322438ed2f6319a691291b247d09c69dcaa3a982460d1f269a7e1af335cfdfd
fi

DONE=(); MISSING=()
say()  { [ "$JSON" = 1 ] || printf "%s\n" "$1"; }
ok()   { DONE+=("$1"); say "  ✓ $1"; }
miss() { MISSING+=("$1|$2"); say "  ✗ $1: $2"; }

fetch() {                                            # fetch URL FILE SHA256: download once, keep only a verified file
  local url="$1" out="$DL/$2" sha="$3"
  if [ -f "$out" ] && echo "$sha  $out" | shasum -a 256 -c - >/dev/null 2>&1; then return 0; fi
  curl -fsSL --retry 3 -o "$out.part" "$url" || { rm -f "$out.part"; return 1; }
  if echo "$sha  $out.part" | shasum -a 256 -c - >/dev/null 2>&1; then mv "$out.part" "$out"; else rm -f "$out.part"; return 2; fi
}

has_ffmpeg() { command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null && \
               ffmpeg -version 2>/dev/null | head -1 | grep -qE 'version (N-|[7-9]\.|[1-9][0-9]\.)'; }
has_node()   { command -v node >/dev/null && node -e 'process.exit(+process.versions.node.split(".")[0] >= 22 ? 0 : 1)' 2>/dev/null; }
has_python() { python3 -c 'import sys, PIL, numpy; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; }

say "Video maker setup ($ARCH)"

# ---- FFmpeg: cuts, renders, sound --------------------------------------------------------------------------------
if has_ffmpeg; then ok "FFmpeg ($(command -v ffmpeg))"
elif [ "$MODE" = check ]; then miss "FFmpeg" "not installed yet"
else
  say "  … downloading FFmpeg 9.0.2"
  if fetch "$FF_URL/ffmpeg.zip" ffmpeg.zip "$FF_SHA" && fetch "$FF_URL/ffprobe.zip" ffprobe.zip "$FP_SHA"; then
    unzip -oq "$DL/ffmpeg.zip" -d "$BIN" && unzip -oq "$DL/ffprobe.zip" -d "$BIN" && chmod +x "$BIN/ffmpeg" "$BIN/ffprobe"
    has_ffmpeg && ok "FFmpeg 9.0.2 (in .tools)" || miss "FFmpeg" "downloaded but does not run; run setup again"
  else miss "FFmpeg" "download failed or did not match its checksum; check the internet connection and run setup again"; fi
fi

# ---- Node: runs HyperFrames, the animation renderer --------------------------------------------------------------
if has_node; then ok "Node $(node -v)"
elif [ "$MODE" = check ]; then miss "Node" "not installed yet"
else
  say "  … downloading Node $NODE_VER"
  if fetch "https://nodejs.org/dist/v$NODE_VER/$NODE_PKG.tar.gz" "$NODE_PKG.tar.gz" "$NODE_SHA"; then
    rm -rf "$TOOLS/node" && mkdir -p "$TOOLS/node" && tar -xzf "$DL/$NODE_PKG.tar.gz" -C "$TOOLS/node" --strip-components 1
    for b in node npm npx; do ln -sf "$TOOLS/node/bin/$b" "$BIN/$b"; done
    has_node && ok "Node $NODE_VER (in .tools)" || miss "Node" "downloaded but does not run; run setup again"
  else miss "Node" "download failed or did not match its checksum; check the internet connection and run setup again"; fi
fi

# ---- Python 3.12 with Pillow and numpy: the editing scripts -----------------------------------------------------
if has_python; then ok "Python $(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])') with Pillow and numpy"
elif [ "$MODE" = check ]; then miss "Python" "Python 3.10+ with Pillow and numpy not found"
else
  if ! command -v uv >/dev/null; then
    say "  … downloading uv $UV_VER (it fetches Python)"
    if fetch "https://github.com/astral-sh/uv/releases/download/$UV_VER/$UV_PKG.tar.gz" "$UV_PKG.tar.gz" "$UV_SHA"; then
      tar -xzf "$DL/$UV_PKG.tar.gz" -C "$DL" && cp "$DL/$UV_PKG/uv" "$DL/$UV_PKG/uvx" "$BIN/" && chmod +x "$BIN/uv" "$BIN/uvx"
    fi
  fi
  if command -v uv >/dev/null; then
    say "  … installing Python 3.12, Pillow and numpy into .venv"
    uv venv --quiet --python 3.12 "$ROOT/.venv" >/dev/null 2>&1 && \
      uv pip install --quiet --python "$ROOT/.venv/bin/python" pillow numpy >/dev/null 2>&1
    hash -r
    has_python && ok "Python 3.12 with Pillow and numpy (in .venv)" || miss "Python" "could not install; run setup again"
  else miss "Python" "uv download failed or did not match its checksum; check the internet connection and run setup again"; fi
fi

# ---- HyperFrames, its browser, the speech-to-text model ---------------------------------------------------------
if [ "$MODE" = install ] && has_node; then
  say "  … installing HyperFrames (npm)"
  if npm install --silent --no-audit --no-fund >/dev/null 2>&1; then ok "HyperFrames $(npx --no-install hyperframes --version 2>/dev/null)"
  else miss "HyperFrames" "npm install failed; run setup again"; fi
  say "  … getting the render browser (Chrome for Testing, cached once per Mac)"
  npx --no-install hyperframes browser ensure </dev/null >/dev/null 2>&1 && ok "Render browser" || miss "Render browser" "could not download it; run setup again"
  say "  … getting the speech-to-text model (Parakeet, once per Mac; it can take a few minutes the first time)"
  npx --no-install hyperframes models install parakeet </dev/null >/dev/null 2>&1 && ok "Speech-to-text model" \
    || miss "Speech-to-text model" "not installed; transcripts fall back to a smaller model"
elif [ "$MODE" = check ]; then
  [ -d node_modules/hyperframes ] && ok "HyperFrames" || miss "HyperFrames" "not installed yet"
fi

# ---- small assets: sound effects, GSAP, a Japanese subtitle font ------------------------------------------------
if [ "$MODE" = install ] && has_node; then
  SFXSRC="$HOME/.claude/skills/media-use/audio/assets/sfx"
  [ -d "$SFXSRC" ] || npx --no-install hyperframes skills update media-use </dev/null >/dev/null 2>&1
  mkdir -p videos/_shared/sfx
  for f in pop click click-soft typing key-press ping notification chime; do cp "$SFXSRC/$f.mp3" videos/_shared/sfx/ 2>/dev/null; done
  [ -f videos/_shared/sfx/pop.mp3 ] && ok "Free sound effects" || miss "Sound effects" "not copied; voice and music still work"
  SK=.claude/skills/youtube-edit; mkdir -p "$SK/assets/vendor"
  [ -f "$SK/assets/vendor/gsap.min.js" ] || curl -sfL https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js -o "$SK/assets/vendor/gsap.min.js"
  [ -f "$SK/assets/vendor/gsap.min.js" ] && ok "GSAP (animation library)" || miss "GSAP" "not downloaded; renders load it online instead"
  JP=.claude/skills/localize/fonts/NotoSansJP.ttf
  [ -f "$JP" ] || curl -sfL "https://github.com/google/fonts/raw/main/ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf" -o "$JP"
  [ -f "$JP" ] && ok "Japanese subtitle font" || miss "Japanese subtitle font" "not downloaded; only needed for Japanese versions"
fi

# ---- make the tools findable in every new Claude chat in this folder -------------------------------------------
if [ "$MODE" = install ]; then
  { echo "# Written by setup.sh: puts this project's own tools first. Loaded by the SessionStart hook in .claude/settings.json."
    printf 'export PATH="%s:%s/.venv/bin:$PATH"\n' "$BIN" "$ROOT"; } > "$TOOLS/env.sh"
  [ -f .env ] || cp .env.example .env
fi

# ---- keys (optional) ---------------------------------------------------------------------------------------------
if grep -qE '^ELEVENLABS_API_KEY=.+' .env 2>/dev/null; then ok "ElevenLabs key (voiceover)"
else miss "ElevenLabs key" "optional: only for AI voiceovers"; fi

# ---- a quick self-test -------------------------------------------------------------------------------------------
if [ "$MODE" = install ] && has_python && has_ffmpeg; then
  say "  … checking everything works"
  FAILS=0
  for d in .claude/skills/youtube-edit/scripts .claude/skills/fast-cut/scripts .claude/skills/text-animations/scripts \
           .claude/skills/localize/scripts .claude/skills/reference-style/scripts .claude/skills/launch-demo/scripts; do
    ( cd "$d" && python3 -m unittest tests >/dev/null 2>&1 ) || FAILS=$((FAILS + 1))
  done
  [ "$FAILS" = 0 ] && ok "Self-test (all skills)" || miss "Self-test" "$FAILS skill test suites failed; tell Claude so it can look"
fi

# ---- the report --------------------------------------------------------------------------------------------------
READY=1
for m in "${MISSING[@]+"${MISSING[@]}"}"; do case "$m" in "ElevenLabs key|"*|"Japanese subtitle font|"*|"Sound effects|"*|"Speech-to-text model|"*) ;; *) READY=0 ;; esac; done
if [ "$JSON" = 1 ]; then
  python3 - "$READY" "${DONE[@]+"${DONE[@]}"}" "--" "${MISSING[@]+"${MISSING[@]}"}" <<'PY' 2>/dev/null || echo "{\"ready\": $READY}"
import json, sys
a = sys.argv[1:]; ready = a[0] == "1"; i = a.index("--")
print(json.dumps({"ready": ready, "done": a[1:i],
                  "missing": [dict(zip(("what", "why"), m.split("|", 1))) for m in a[i + 1:]],
                  "tools_env": ".tools/env.sh"}))
PY
else
  echo
  if [ "$READY" = 1 ]; then echo "Ready. Open a new Claude chat in this folder and say what video you want."
  else echo "Not ready yet: see the ✗ lines above, then run: bash setup.sh"; fi
fi
[ "$READY" = 1 ]
