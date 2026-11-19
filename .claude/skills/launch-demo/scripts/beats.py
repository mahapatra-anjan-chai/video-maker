#!/usr/bin/env python3
"""Read a music track for a launch demo: tempo, beat grid, the drop, the final hit, and where to start and splice it.

  python3 beats.py --music W/audio/music.wav [--bpm 114] [--drop-at 33.67] [--hit-at 80.0] [--ending-beats 16] [--json]

  --drop-at   video time the montage starts: the music then starts at drop-at minus the drop's time in the track
  --hit-at    video time the logo lockup lands: the track's own ending is spliced in, beat-matched, so its final hit lands
              there (the video ends on the music's real ending, not a fade)

Prints the beat grid in video time too, so section starts can sit on beats. Loudness is read in 0.25 s steps: the drop
is the biggest jump after a dip (8 s or later), the final hit is where the last loud stretch falls away for good.
"""
import argparse, json, subprocess


def load(path, sr=22050):
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype="float32"), sr


def analyse(x, sr, bpm=None, ending_beats=16):
    import numpy as np
    fr = 512
    e = np.sqrt(np.convolve(x ** 2, np.ones(fr) / fr, mode="valid")[::fr])
    on = np.maximum(0, np.diff(e))
    fps = sr / fr
    def grid(b):                                       # (mean onset on the best-aligned grid, its phase)
        best = (-1, 0.0)
        for ph in np.arange(0, b, 0.01):
            idx = (np.arange(ph, len(x) / sr, b) * fps).astype(int)
            idx = idx[idx < len(on)]
            m = on[idx].mean()
            if m > best[0]:
                best = (m, ph)
        return best
    if not bpm:   # the autocorrelation peak, then its 2:3, 3:2, 1:2 and 2:1 relatives: keep the one whose beats land on onsets
        o = on - on.mean()
        ac = np.correlate(o, o, "full")[len(o) - 1:]
        lags = np.arange(int(fps * 60 / 180), int(fps * 60 / 70))
        b0 = 60 * fps / lags[np.argmax(ac[lags])]
        cands = [c for c in (b0, b0 * 1.5, b0 * 2, b0 / 1.5, b0 / 2) if 80 <= c <= 170]
        bpm = max(cands, key=lambda c: grid(60.0 / c)[0])
        # the autocorrelation lag is coarse (512-sample frames): refine within 3% in 0.1 BPM steps
        bpm = max(np.arange(bpm * 0.97, bpm * 1.03, 0.1), key=lambda c: grid(60.0 / c)[0])
        bpm = round(float(bpm), 1)
    beat = 60.0 / bpm
    phase = float(grid(beat)[1])
    hop = int(sr * 0.25)
    db = np.array([20 * np.log10(np.sqrt((x[i:i + hop] ** 2).mean()) + 1e-9) for i in range(0, len(x) - hop, hop)])
    snap = lambda t: phase + round((t - phase) / beat) * beat
    # the drop: biggest rise from the quietest 1 s before to the next 2 s, 8 s or later
    best = (0, None)
    for i in range(32, len(db) - 8):
        rise = db[i:i + 8].mean() - db[i - 4:i].min()
        if rise > best[0]:
            best = (rise, i)
    drop = snap(best[1] * 0.25) if best[1] is not None and best[0] >= 6 else None
    # the final hit: the last fall of 15 dB or more within 0.5 s that never comes back
    loud = db.max() - 12
    hit = None
    for i in range(len(db) - 3, 8, -1):
        if db[i - 1] > loud and db[i + 1] < db[i - 1] - 15 and db[i + 1:].max() < db[i - 1] - 10:
            hit = snap(i * 0.25)
            break
    dur = len(x) / sr
    return {"bpm": round(float(bpm), 2), "beat": round(beat, 4), "phase": round(phase, 3), "duration": round(dur, 2),
            "drop": round(drop, 3) if drop is not None else None, "final_hit": round(hit, 3) if hit is not None else None,
            "ending_from": round(hit - ending_beats * beat, 3) if hit is not None else None}


def plan(a, drop_at=None, hit_at=None, ending_beats=16):
    out = dict(a)
    if drop_at is not None and a["drop"] is not None:
        out["music_start"] = round(drop_at - a["drop"], 3)
    if hit_at is not None and a["final_hit"] is not None and "music_start" in out:
        b = a["beat"]
        # keep the lockup on the beat grid the montage set
        k = round((hit_at - drop_at) / b)
        hit = drop_at + k * b
        splice_video = hit - ending_beats * b
        out["hit_at"] = round(hit, 3)
        out["splice"] = {"main_until": round(splice_video - out["music_start"], 3), "at": round(splice_video, 3),
                         "ending_from": a["ending_from"], "ending_to": a["duration"]}
    if "music_start" in out:
        s, b = out["music_start"], a["beat"]
        first = s + a["phase"]
        out["beats_video"] = [round(first + i * b, 3) for i in range(0, int(150 / b)) if first + i * b >= 0][:240]
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--music", required=True)
    ap.add_argument("--bpm", type=float)
    ap.add_argument("--drop-at", type=float)
    ap.add_argument("--hit-at", type=float)
    ap.add_argument("--ending-beats", type=int, default=16)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    x, sr = load(a.music)
    p = plan(analyse(x, sr, a.bpm, a.ending_beats), a.drop_at, a.hit_at, a.ending_beats)
    if a.json:
        print(json.dumps(p))
    else:
        print("%.1f BPM, beat %.3f s, first beat at %.2f s; %.1f s long" % (p["bpm"], p["beat"], p["phase"], p["duration"]))
        print("drop at %s s in the track; final hit at %s s (ending from %s s)" % (p["drop"], p["final_hit"], p["ending_from"]))
        if "music_start" in p:
            print("start the music at %.2f s of the video so the drop lands at %.2f s" % (p["music_start"], a.drop_at))
        if "splice" in p:
            sp = p["splice"]
            print("lockup on the final hit at %.2f s: play the track to %.3f s, then its ending from %.3f s (spliced at %.2f s of the video)"
                  % (p["hit_at"], sp["main_until"], sp["ending_from"], sp["at"]))
