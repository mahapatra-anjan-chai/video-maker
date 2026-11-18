#!/usr/bin/env python3
"""Join the translated subtitles to the old ones: where each new line goes, what it must cover, how long it stays.

  python3 cues.py --script W/script-ja.json --subs W/work/subs-en.json --placed W/audio/vo-ja.json --out W/cues-ja.json

Each `subs` entry in the script ([start, end, text]) gets `cover`: the union of the boxes of the old subtitles it
overlaps (from find-subs.py), and `who` from its line. When the new voice runs past the old subtitle (dub.py's report,
--placed), a line's last cue stays up until the voice ends, but never past the next cue.
"""
import argparse, json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", required=True)
    ap.add_argument("--subs", required=True)
    ap.add_argument("--placed")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    lines = json.load(open(a.script))["lines"]
    old = json.load(open(a.subs))
    placed = {p["id"]: p for p in json.load(open(a.placed))} if a.placed else {}
    out = []
    for l in lines:
        for k, (s, e, text) in enumerate(l.get("subs", [])):
            ov = [o["box"] for o in old if o["start"] < e - 0.05 and o["end"] > s + 0.05]
            cover = [min(b[0] for b in ov), min(b[1] for b in ov), max(b[2] for b in ov), max(b[3] for b in ov)] if ov else None
            c = {"start": s, "end": e, "text": text, "who": l.get("who"), "line": l["id"], "cover": cover}
            if k == len(l["subs"]) - 1 and l["id"] in placed:
                p = placed[l["id"]]
                c["end"] = max(e, round(p["at"] + p["dur"] + 0.25, 2))
            out.append(c)
    out.sort(key=lambda c: c["start"])
    for i in range(len(out) - 1):
        out[i]["end"] = min(out[i]["end"], out[i + 1]["start"])
    for c in out:
        print("%7.2f-%7.2f  %-14s %s%s" % (c["start"], c["end"], c["who"] or "", c["text"], "" if c["cover"] else "   (no old subtitle under it)"))
    json.dump(out, open(a.out, "w"), indent=1, ensure_ascii=False)
    print("%d cues -> %s" % (len(out), a.out))


if __name__ == "__main__":
    main()
