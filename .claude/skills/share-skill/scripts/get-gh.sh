#!/usr/bin/env bash
# GitHub's own command-line tool (gh), only for sharing skills: into this project's .tools/bin, pinned and checked
# against SHA-256 like everything setup.sh installs. No Homebrew, no password. Does nothing if gh is already there.
set -eu
cd "$(dirname "$0")/../../../.."
VER=2.103.3
if [ "$(uname -m)" = arm64 ]; then PKG=gh_${VER}_macOS_arm64; SHA=d700207eae9ae98fe2b89535c2c087c07823d4628c56364695a5a07ef311c062
else PKG=gh_${VER}_macOS_amd64; SHA=a2f86418f4350ae6e9ec60d5000bdf7665728436946a97fc27fe50e6ae752682; fi
if command -v gh >/dev/null || [ -x .tools/bin/gh ]; then echo "gh is already installed"; exit 0; fi
mkdir -p .tools/bin .tools/downloads
OUT=.tools/downloads/$PKG.zip
curl -fsSL --retry 3 -o "$OUT.part" "https://github.com/cli/cli/releases/download/v$VER/$PKG.zip"
echo "$SHA  $OUT.part" | shasum -a 256 -c - >/dev/null || { rm -f "$OUT.part"; echo "the download did not match its checksum"; exit 2; }
mv "$OUT.part" "$OUT"
unzip -oq "$OUT" "$PKG/bin/gh" -d .tools/downloads && mv ".tools/downloads/$PKG/bin/gh" .tools/bin/gh && chmod +x .tools/bin/gh
.tools/bin/gh --version | head -1
