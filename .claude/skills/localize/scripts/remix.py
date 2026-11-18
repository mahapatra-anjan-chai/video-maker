#!/usr/bin/env python3
"""Rebuild the soundtrack with the new voice: the original music and effects stay, the original voice goes.

  python3 remix.py --original W/audio/source-44k.wav --stems W/work/stems/htdemucs_ft/source-44k \
                   --script W/script-ja.json --vo W/audio/vo-ja.wav --out W/audio/mix-ja.wav

The stems come from Demucs (`separate` in SKILL.md): no_vocals.wav is the music and effects, vocals.wav every voice,
including any singing in the music. The voice stem is muted only where an original line was spoken (each script
line's `at`..`end`) and where the new line plays, so song vocals between lines survive. Both stems are first scaled
back to the original (Demucs can rescale them), and the result is matched to the original's loudness with a -1 dBTP
ceiling.
"""
import argparse, json, os, re, subprocess

RATE = 44100
FADE = 0.06


def read(path, mono=False):
    """Stereo float samples. A mono file is copied to both sides at full level (FFmpeg's own upmix is 3 dB down)."""
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1" if mono else "2", "-ar", str(RATE), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype="float32")
    return np.stack([x, x], 1).copy() if mono else x.reshape(-1, 2).copy()


def lufs(path):
    out = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", out)[-1])


def phrases(words, gap=0.45):
    out, cur = [], []
    for w in words:
        if cur and (w["start"] - cur[-1]["end"] > gap or cur[-1]["text"].endswith((".", "?", "!"))):
            out.append(cur); cur = []
        cur.append(w)
    return out + ([cur] if cur else [])


def main():
    import numpy as np
    ap = argparse.ArgumentParser()
    ap.add_argument("--original", required=True)
    ap.add_argument("--stems", required=True)
    ap.add_argument("--script", required=True)
    ap.add_argument("--vo", required=True)
    ap.add_argument("--words", help="transcript of the voice stem (npx hyperframes transcribe): mute only real speech")
    ap.add_argument("--out", required=True)
    ap.add_argument("--vo-gain", type=float, default=0.0, help="dB on the new voice")
    a = ap.parse_args()
    o = read(a.original)
    v = read(os.path.join(a.stems, "vocals.wav"))[: len(o)]
    m = read(os.path.join(a.stems, "no_vocals.wav"))[: len(o)]
    # least-squares gains so that gv*v + gm*m ~ o
    A = np.stack([v.ravel(), m.ravel()], 1)[::7]
    gv, gm = np.linalg.lstsq(A, o.ravel()[::7], rcond=None)[0]
    v *= gv; m *= gm
    print("stem gains: voice %.3f, music %.3f; residual %.1f dB under the original"
          % (gv, gm, 20 * np.log10(np.sqrt(((o - v - m) ** 2).mean()) / np.sqrt((o ** 2).mean()))))
    # where the old voice has to go: only where it was really speaking. With --words (the voice stem's transcript),
    # each spoken phrase that belongs to a dubbed line is muted from its first word to its last; phrases that belong
    # to no line (the song) stay whole, even where a new line runs over them.
    keep = np.ones(len(o), dtype="float32")
    lines = [l for l in json.load(open(a.script))["lines"] if l.get("vo")]
    spans, kept = [], []
    if a.words:
        for g in phrases(json.load(open(a.words))):
            s, e = g[0]["start"], g[-1]["end"]
            if any(l["at"] - 0.35 <= s <= l["end"] - 0.25 for l in lines):
                spans.append((s - 0.08, e + 0.08))
            else:
                kept.append((s, e, " ".join(w["text"] for w in g)))
    else:
        spans = [(l["at"] - 0.15, l["end"] + 0.1) for l in lines]
    f = int(FADE * RATE)
    for s, e in spans:
        i, j = max(0, int(s * RATE)), min(len(o), int(e * RATE))
        keep[i:j] = 0
    # soften every edge of the mute
    ker = np.ones(f, dtype="float32") / f
    keep = np.convolve(keep, ker, mode="same")
    for s, e, text in kept:
        cut = 1 - float(keep[int(s * RATE): int(e * RATE)].mean())
        print("  kept %6.2f-%6.2f  %-40s%s" % (s, e, text[:40], "  MUTED %d%%" % (cut * 100) if cut > 0.05 else ""))
    vo = read(a.vo, mono=True)[: len(o)]
    if len(vo) < len(o):
        vo = np.pad(vo, ((0, len(o) - len(vo)), (0, 0)))
    mix = m + v * keep[:, None] + vo * (10 ** (a.vo_gain / 20))
    tmp = a.out + ".pre.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(RATE), "-ac", "2", "-i", "-", "-c:a", "pcm_f32le", tmp],
                   input=mix.astype("float32").tobytes(), check=True)
    target, now = lufs(a.original), lufs(tmp)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-af",
                    "volume=%.2fdB,alimiter=limit=0.89:level=disabled:attack=3:release=60" % (target - now),
                    "-ar", str(RATE), "-c:a", "pcm_s16le", a.out], check=True)
    os.remove(tmp)
    print("original %.1f LUFS, new mix %.1f LUFS -> %s" % (target, lufs(a.out), a.out))


if __name__ == "__main__":
    main()
