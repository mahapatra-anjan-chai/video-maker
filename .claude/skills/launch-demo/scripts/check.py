#!/usr/bin/env python3
"""Check the voice in the final mix: transcribe it and compare with the script(s). Under --min (90%) it fails.

  python3 check.py --mix W/render/mix.wav --script W/script-intro.txt --script W/script.txt [--drop "Link in the comments."]

Spelling differences ("42" for "forty-two", "11 labs" for "ElevenLabs") show in the diff but barely move the score.
"""
import argparse, difflib, json, os, re, subprocess, tempfile


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower().replace("-", " ")).split()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mix", required=True)
    ap.add_argument("--script", action="append", required=True)
    ap.add_argument("--drop", action="append", default=[], help="words cut from the script on purpose")
    ap.add_argument("--min", type=float, default=90.0)
    a = ap.parse_args()
    ref = " ".join(open(p).read() for p in a.script).replace("\n", " ")
    for d in a.drop:
        ref = ref.replace(d, "")
    tmp = tempfile.mkdtemp(prefix="check-")
    wav = os.path.join(tmp, "mix-16k.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.mix, "-ac", "1", "-ar", "16000", wav], check=True)
    subprocess.run(["npx", "hyperframes", "transcribe", wav, "--json", "-d", tmp], capture_output=True)
    words = json.load(open(os.path.join(tmp, "transcript.json")))
    got = " ".join(w["text"] for w in words)
    x, y = norm(ref), norm(got)
    sm = difflib.SequenceMatcher(None, x, y)
    score = sm.ratio() * 100
    print("voice matches the script: %.0f%%" % score)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != "equal":
            print("  %-7s %s  ->  %s" % (op, " ".join(x[i1:i2]) or "-", " ".join(y[j1:j2]) or "-"))
    raise SystemExit(0 if score >= a.min else 1)


if __name__ == "__main__":
    main()
