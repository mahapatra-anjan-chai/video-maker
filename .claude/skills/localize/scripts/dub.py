#!/usr/bin/env python3
"""Voice a translated script line by line on ElevenLabs and lay each line on the original's timeline.

  python3 dub.py plan  --script W/script-ja.json --cast W/cast.json
  python3 dub.py voice --script W/script-ja.json --cast W/cast.json --out W/audio/vo-ja.wav --length 150.04 [--yes]
                       [--match W/work/stems/.../vocals.wav]

script: {"lines": [{"id", "at", "end", "who", "vo", ...}]}; `at` is where the original line starts, `end` the latest
it may run to. cast: {"who": "<voice_id>", ...} plus optional "model", "speed" and "gain" ({"who": dB}, on top of the matched level). Lines are cached in
videos/_shared/tts-cache by voice + model + speed + text, so a re-run only pays for changed lines. A line longer than
its slot is sped up to fit (at most --max-tempo); --match sets each line's level to the original voice's level in the
same slot. Nothing is generated without --yes: plan prints lines, voices, characters and credits first.
"""
import argparse, hashlib, json, os, subprocess, sys, urllib.request, urllib.error

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
CACHE = os.path.join(ROOT, "videos", "_shared", "tts-cache")
RATE = 44100
# broadcast-style voice compression: finished ads master their voices dense, raw TTS is peaky, and matching the
# original's level without this sends the TTS peaks 4-8 dB over full scale into the final limiter
COMP = ",acompressor=threshold=0.1:ratio=4:attack=5:release=90:knee=4,alimiter=limit=0.7:level=disabled:attack=2:release=40"


def key_of(voice, model, speed, text):
    return hashlib.sha1(("%s|%s|%s|%s" % (voice, model, speed, text)).encode()).hexdigest()[:16]


def api_key():
    k = os.environ.get("ELEVENLABS_API_KEY")
    if not k and os.path.exists(os.path.join(ROOT, ".env")):
        for line in open(os.path.join(ROOT, ".env")):
            if line.startswith("ELEVENLABS_API_KEY="):
                k = line.split("=", 1)[1].strip().strip('"')
    if not k:
        sys.exit("ELEVENLABS_API_KEY is not set (.env)")
    return k


def tts(voice, model, speed, text, path):
    body = {"text": text, "model_id": model}
    if speed:
        body["voice_settings"] = {"speed": speed}
    req = urllib.request.Request("https://api.elevenlabs.io/v1/text-to-speech/%s?output_format=mp3_44100_128" % voice,
                                 data=json.dumps(body).encode(), method="POST",
                                 headers={"xi-api-key": api_key(), "Content-Type": "application/json"})
    try:
        open(path, "wb").write(urllib.request.urlopen(req, timeout=120).read())
    except urllib.error.HTTPError as e:
        sys.exit("ElevenLabs refused voice %s: %s %s" % (voice, e.code, e.read()[:300].decode("utf8", "replace")))


def pcm(path, filters=None):
    import numpy as np
    cmd = ["ffmpeg", "-v", "error", "-i", path] + (["-af", filters] if filters else []) + ["-ac", "1", "-ar", str(RATE), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, dtype="float32").copy()


def speech_rms(x):
    """Active speech level: the RMS of every 50 ms frame within 30 dB of the loudest, so silence does not count and
    a compressed line and a peaky one compare fairly."""
    import numpy as np
    n = int(0.05 * RATE)
    if len(x) < n:
        return float(np.sqrt((x ** 2).mean() + 1e-12))
    fr = x[: len(x) // n * n].reshape(-1, n)
    r = np.sqrt((fr ** 2).mean(1))
    act = r[r > r.max() * 0.03]
    return float(np.sqrt((act ** 2).mean() + 1e-12))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["plan", "voice"])
    ap.add_argument("--script", required=True)
    ap.add_argument("--cast", required=True)
    ap.add_argument("--out")
    ap.add_argument("--length", type=float, help="seconds of the output track (the video's length)")
    ap.add_argument("--match", help="the original voice stem: match each line's level to it")
    ap.add_argument("--max-tempo", type=float, default=1.25)
    ap.add_argument("--pause", type=float, default=0.18, help="longest pause kept inside a line (s)")
    ap.add_argument("--run-on", type=float, default=1.5, help="how far past its `end` a line may run into a gap (s)")
    ap.add_argument("--only", help="comma-separated line ids")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    s = json.load(open(a.script)); cast = json.load(open(a.cast))
    model, speed = cast.get("model", "eleven_multilingual_v2"), cast.get("speed")
    gains = cast.get("gain", {})            # dB per speaker on top of the original's level, e.g. {"narrator": 2}
    lines = [l for l in s["lines"] if l.get("vo")]
    if a.only:
        ids = {int(i) for i in a.only.split(",")}
        lines = [l for l in lines if l["id"] in ids]
    for l in lines:
        if l["who"] not in cast:
            sys.exit("no voice in the cast for %r" % l["who"])
        l["voice"] = cast[l["who"]]
        l["key"] = key_of(l["voice"], model, speed, l["vo"])
        l["cached"] = os.path.exists(os.path.join(CACHE, l["key"] + ".mp3"))
    todo = [l for l in lines if not l["cached"]]
    chars = sum(len(l["vo"]) for l in todo)
    print("PLAN  %d lines, model %s, %d voices" % (len(lines), model, len({l["voice"] for l in lines})))
    for l in lines:
        print("  %3d %6.2f  %-14s %s%s" % (l["id"], l["at"], l["who"][:14], l["vo"], "  (cached)" if l["cached"] else ""))
    print("COST  %d new characters = about %d credits (%d of %d lines cached)" % (chars, chars, len(lines) - len(todo), len(lines)))
    if a.cmd == "plan":
        return
    if todo and not a.yes:
        print("nothing generated: rerun with --yes once the creator agrees to the cost")
        return
    os.makedirs(CACHE, exist_ok=True)
    for n, l in enumerate(todo, 1):
        print("  generating %d/%d  line %d" % (n, len(todo), l["id"]), flush=True)
        tts(l["voice"], model, speed, l["vo"], os.path.join(CACHE, l["key"] + ".mp3"))

    import numpy as np
    length = a.length or max(l["end"] for l in s["lines"]) + 1
    track = np.zeros(int(length * RATE) + RATE, dtype="float32")
    ref = pcm(a.match) if a.match else None
    report = []
    # TTS voices pause longer at commas than a dub has room for: cap every pause inside a line at --pause seconds,
    # then fit. A line may run on to the next line's start (not just its own `end`); if it still does not fit at
    # --max-tempo, the next line starts a little later.
    trim = ("silenceremove=start_periods=1:start_threshold=-45dB:stop_periods=-1:stop_duration=%.2f:stop_threshold=-40dB,"
            "areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse" % a.pause)
    order = sorted(lines, key=lambda l: l["at"])
    free = 0.0
    for n, l in enumerate(order):
        src = os.path.join(CACHE, l["key"] + ".mp3")
        x = pcm(src, trim + COMP)
        start = max(l["at"], free)
        nxt = order[n + 1]["at"] - 0.06 if n + 1 < len(order) else length - 0.2
        limit = max(l["end"], nxt) if nxt - l["end"] < a.run_on else l["end"] + a.run_on
        slot = limit - start
        dur = len(x) / RATE
        tempo = 1.0
        if dur > slot:
            tempo = min(a.max_tempo, dur / slot)
            x = pcm(src, trim + ",atempo=%.4f" % tempo + COMP)
        if ref is not None:
            seg = ref[int(l["at"] * RATE): int(l["end"] * RATE)]
            x *= speech_rms(seg) / max(1e-6, speech_rms(x))
        x *= 10 ** (float(gains.get(l["who"], 0)) / 20)
        i = int(start * RATE)
        track[i: i + len(x)] += x[: len(track) - i]
        free = start + len(x) / RATE + 0.06
        over = start + len(x) / RATE - nxt
        report.append((l["id"], start, len(x) / RATE, slot, tempo, max(0, over)))
        print("  line %3d at %7.2f%s  %.2f s in a %.2f s slot%s%s" % (
            l["id"], start, " (moved %+.2f)" % (start - l["at"]) if start > l["at"] + 0.01 else "", len(x) / RATE, slot,
            "  sped up x%.2f" % tempo if tempo > 1.005 else "", "  pushes the next line %.2f s" % over if over > 0.01 else ""))
    # no normalising here: scaling the whole track down for one hot line drops every line under the original's
    # level. The track is written as float and remix.py's limiter catches the peaks.
    print("  voice track peak %.2f (%+.1f dBFS); float WAV, the mix limits it" % (float(np.abs(track).max()), 20 * np.log10(float(np.abs(track).max()) + 1e-9)))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(RATE), "-ac", "1", "-i", "-",
                    "-t", "%.3f" % length, "-c:a", "pcm_f32le", a.out], input=track.tobytes(), check=True)
    json.dump([dict(zip(["id", "at", "dur", "slot", "tempo", "over"], r)) for r in report],
              open(os.path.splitext(a.out)[0] + ".json", "w"), indent=1)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
