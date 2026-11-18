#!/usr/bin/env python3
"""Turn the original voice into a script to translate: one entry per spoken line, with its time slot, the English
words, the old subtitles that belong to it, and hints for casting and for telling speech from singing.

  python3 draft-script.py --words W/work/vtx/transcript.json --subs W/work/subs-en.json \
                          --vocals W/work/stems/htdemucs_ft/<name>/vocals.wav --lang ja --out W/script-ja.json

--words is `npx hyperframes transcribe` run on the voice stem. Each line gets:
  at / end   where the original line starts, and the latest the new line should run to (the next line's start, or
             the end of its last subtitle, whichever comes first)
  en         what was said
  subs       [[start, end, "<English subtitle to translate>"], ...] for the old subtitles it overlaps
  pitch      median voice pitch in Hz (under ~165 usually a man, over ~180 usually a woman) and `steady`, the share of
             frames holding one note (a hint only: speech can score high too)
  who / vo   left for Claude: who speaks (name each character, reuse names), and the translation
"""
import argparse, json, subprocess


def lines_of(words, gap=0.45):
    out, cur = [], []
    for w in words:
        if cur and (w["start"] - cur[-1]["end"] > gap or cur[-1]["text"].endswith((".", "?", "!"))):
            out.append(cur); cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    return out


def pitch(path, spans, rate=16000):
    """Median pitch and how much of the line holds a steady note, per span."""
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(rate), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype="float32")
    fr, hop = int(0.04 * rate), int(0.02 * rate)
    lo, hi = int(rate / 500), int(rate / 70)
    res = []
    for a, b in spans:
        f0 = []
        for i in range(int(a * rate), int(b * rate) - fr, hop):
            seg = x[i: i + fr] * np.hanning(fr)
            if np.sqrt((seg ** 2).mean()) < 0.01:
                continue
            ac = np.correlate(seg, seg, "full")[fr - 1:]
            k = lo + int(np.argmax(ac[lo:hi]))
            if ac[k] > 0.4 * ac[0]:
                f0.append(rate / k)
        if len(f0) < 4:
            res.append((0, 0.0)); continue
        f0 = np.array(f0)
        steady = float(np.mean(np.abs(np.diff(f0)) / f0[1:] < 0.03))
        res.append((int(np.median(f0)), round(steady, 2)))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--words", required=True)
    ap.add_argument("--subs", required=True)
    ap.add_argument("--vocals")
    ap.add_argument("--lang", default="ja")
    ap.add_argument("--source", default="raw/source.mp4")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    words = json.load(open(a.words))
    subs = json.load(open(a.subs))
    groups = lines_of(words)
    spans = [(g[0]["start"], g[-1]["end"]) for g in groups]
    ph = pitch(a.vocals, spans) if a.vocals else [(0, 0.0)] * len(groups)
    lines = []
    for i, g in enumerate(groups):
        s, e = spans[i]
        mine = [c for c in subs if c["start"] < e + 0.3 and c["end"] > s - 0.3]
        nxt = spans[i + 1][0] if i + 1 < len(groups) else e + 2
        end = round(min(nxt - 0.05, max([e] + [c["end"] for c in mine])), 2)
        lines.append({"id": i + 1, "at": round(s, 2), "end": end, "who": "", "en": " ".join(w["text"] for w in g),
                      "vo": "", "subs": [[c["start"], c["end"], c["text"]] for c in mine],
                      "pitch": {"hz": ph[i][0], "steady": ph[i][1]}})
    # a subtitle that overlaps two lines belongs to the one it overlaps most
    for c in subs:
        owners = [l for l in lines if any(abs(x[0] - c["start"]) < 1e-6 for x in l["subs"])]
        if len(owners) > 1:
            best = max(owners, key=lambda l: min(l["end"], c["end"]) - max(l["at"], c["start"]))
            for l in owners:
                if l is not best:
                    l["subs"] = [x for x in l["subs"] if abs(x[0] - c["start"]) > 1e-6]
    json.dump({"source": a.source, "lang": a.lang, "lines": lines}, open(a.out, "w"), indent=1, ensure_ascii=False)
    for l in lines:
        tag = "" if l["subs"] else "   NO SUBTITLE (song, or dialogue shown as on-screen copy? look at the frame)"
        print("%3d %7.2f-%7.2f %4d Hz  %s%s" % (l["id"], l["at"], l["end"], l["pitch"]["hz"], l["en"][:60], tag))
    print("%d lines -> %s (fill in who and vo, translate subs, delete the song)" % (len(lines), a.out))


if __name__ == "__main__":
    main()
