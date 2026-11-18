#!/bin/sh
# Split a video's soundtrack into the voice and everything else (music, effects) with Demucs, on the CPU.
#   sh separate.sh <video> <out-dir>      -> <out-dir>/htdemucs_ft/<name>/vocals.wav and no_vocals.wav (~2-3 min for 2 min)
# Demucs lives in its own venv (~/.local/venvs/demucs), made on first use (~1 GB of downloads). Never use -d mps:
# on Apple GPUs it returns stems that do not add back up to the original.
set -e
VIDEO="$1"; OUT="$2"
[ -n "$VIDEO" ] && [ -n "$OUT" ] || { echo "usage: sh separate.sh <video> <out-dir>"; exit 1; }
VENV="$HOME/.local/venvs/demucs"
if [ ! -x "$VENV/bin/python" ]; then
  PY=$(command -v python3.12 || command -v python3.11 || command -v python3)
  echo "making the Demucs venv with $PY (one time)"
  "$PY" -m venv "$VENV" && "$VENV/bin/pip" install -q demucs soundfile
fi
mkdir -p "$OUT"
NAME=$(basename "${VIDEO%.*}")
WAV="$OUT/$NAME.wav"
ffmpeg -v error -y -i "$VIDEO" -vn -c:a pcm_s16le "$WAV"
"$VENV/bin/python" -m demucs --two-stems vocals -n htdemucs_ft -d cpu --float32 -o "$OUT" "$WAV"
echo "stems in $OUT/htdemucs_ft/$NAME/"
