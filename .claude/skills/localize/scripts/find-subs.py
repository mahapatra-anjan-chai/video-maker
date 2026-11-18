#!/usr/bin/env python3
"""Find the burned-in subtitles of a video: their text, when each is on screen and where it sits.

  python3 find-subs.py --video in.mp4 --out W/work/subs-en.json [--band 0.80,0.99] [--fps 6] [--centre 90]

Reads a strip of the frame (--band, as shares of the height) --fps times a second with the macOS Vision text reader
(ocr.swift; no installs) and keeps lines centred within --centre px of the middle, which is where subtitles sit and
UI copy mostly does not. Consecutive reads of the same line become one cue with the union of their boxes (in video
pixels). Prints the cues; delete any that are on-screen UI copy rather than subtitles (they read like a subtitle but
belong to the picture).
"""
import argparse, json, os, re, shutil, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def same(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    if a == b or a[:12] == b[:12] or a[-12:] == b[-12:]:
        return True
    # OCR noise ("I wanna" / "/ wanna"): most characters shared in order
    import difflib
    return difflib.SequenceMatcher(None, a, b).ratio() > 0.8


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--band", default="0.80,0.99")
    ap.add_argument("--fps", type=float, default=6)
    ap.add_argument("--centre", type=int, default=90)
    ap.add_argument("--min-conf", type=float, default=0.3)
    ap.add_argument("--min-reads", type=int, default=2, help="drop lines seen on fewer frames (flashes of UI copy)")
    ap.add_argument("--reuse", action="store_true", help="reuse the reads from the last run")
    a = ap.parse_args()
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                      "stream=width,height", "-of", "json", a.video], capture_output=True, text=True).stdout)
    W, H = info["streams"][0]["width"], info["streams"][0]["height"]
    b0, b1 = [float(x) for x in a.band.split(",")]
    y0, h = int(H * b0) // 2 * 2, int(H * (b1 - b0)) // 2 * 2
    raw = os.path.splitext(a.out)[0] + ".ocr.json"      # every read, kept so a re-run can skip the OCR
    if not (a.reuse and os.path.exists(raw)):
        tmp = tempfile.mkdtemp(prefix="find-subs-")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-vf", "fps=%g,crop=%d:%d:0:%d" % (a.fps, W, h, y0),
                        "-q:v", "2", os.path.join(tmp, "%05d.jpg")], check=True)
        os.makedirs(os.path.dirname(os.path.abspath(raw)), exist_ok=True)
        subprocess.run(["swift", os.path.join(HERE, "ocr.swift"), tmp, raw], check=True)
        shutil.rmtree(tmp, ignore_errors=True)
    frames = json.load(open(raw))
    cues, step = [], 1.0 / a.fps
    ok = lambda x: abs((x["x0"] + x["x1"]) / 2 - W / 2) < a.centre and x["conf"] >= a.min_conf
    # subtitles sit on one baseline: keep only reads on the most common line, which drops UI copy and logos above it
    import statistics
    mids = [(x["y0"] + x["y1"]) / 2 for fr in frames for x in fr["items"] if ok(x)]
    hts = [x["y1"] - x["y0"] for fr in frames for x in fr["items"] if ok(x)]
    line_y, line_h = statistics.median(mids), statistics.median(hts)
    for fr in frames:
        t = (int(fr["file"][:5]) - 1) * step
        its = [x for x in fr["items"] if ok(x) and abs((x["y0"] + x["y1"]) / 2 - line_y) < line_h * 0.6]
        txt = " ".join(x["text"] for x in sorted(its, key=lambda x: (x["y0"], x["x0"])))
        if not txt:
            if cues:
                cues[-1]["open"] = False
            continue
        box = [min(x["x0"] for x in its), min(x["y0"] for x in its) + y0, max(x["x1"] for x in its), max(x["y1"] for x in its) + y0]
        c = cues[-1] if cues else None
        if c and c["end"] >= t - step * 2.5 and same(txt, c["reads"][-1]):
            c["end"] = t + step
            c["box"] = [min(c["box"][0], box[0]), min(c["box"][1], box[1]), max(c["box"][2], box[2]), max(c["box"][3], box[3])]
            c["reads"].append(txt)
        else:
            if c:
                c["open"] = False
            cues.append({"start": t, "end": t + step, "box": box, "reads": [txt], "open": True})
    out = []
    for c in [c for c in cues if len(c["reads"]) >= a.min_reads]:
        text = max(set(c["reads"]), key=lambda r: (c["reads"].count(r), len(r)))   # the most common read
        out.append({"start": round(c["start"], 2), "end": round(c["end"], 2), "text": text, "box": [int(v) for v in c["box"]]})
        print("%7.2f-%7.2f  %-22s %s" % (out[-1]["start"], out[-1]["end"], out[-1]["box"], text))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, "w"), indent=1, ensure_ascii=False)
    print("%d cues -> %s" % (len(out), a.out))


if __name__ == "__main__":
    main()
