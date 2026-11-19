#!/usr/bin/env python3
"""The launch demo's sound, from a mix.json: voice lines at their scenes, the music (started so its drop lands on the
montage, and spliced into its own ending for the lockup), ducked under the voice, sound effects, then loudness.

  python3 mix.py --mix W/mix.json --out W/render/mix.wav

mix.json (paths relative to it):
  {"duration": 83,
   "voice": [{"file": "voiceover/voiceover.wav", "from": 0.0, "to": 2.93, "at": 13.45}, ...],
   "music": {"file": "audio/music.wav", "at": 13.2, "gain_db": -11,
             "until": 58.404, "ending_from": 178.932, "ending_to": 189.49},      # from beats.py; without them: a 2 s fade
   "sfx":   [{"file": "audio/sfx-whoosh.wav", "t": 15.75, "db": -9}, {"file": "...typing.mp3", "t": 0.2, "db": -24, "trim": 1.6}],
   "duck":  {"threshold": 0.025, "ratio": 7},
   "lufs": -14}
"""
import argparse, json, os, re, subprocess


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mix", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    m = json.load(open(a.mix))
    base = os.path.dirname(os.path.abspath(a.mix))
    P = lambda f: f if os.path.isabs(f) else os.path.join(base, f)
    D = float(m["duration"])
    inputs, fg, n = [], [], 0

    def add(f):
        nonlocal n
        inputs.extend(["-i", P(f)]); n += 1
        return n - 1

    vo = []
    for i, v in enumerate(m.get("voice", [])):
        k = add(v["file"])
        fg.append("[%d:a]atrim=start=%.3f:end=%.3f,asetpts=PTS-STARTPTS,adelay=%d|%d[v%d]" % (k, v["from"], v["to"] + 0.08, v["at"] * 1000, v["at"] * 1000, i))
        vo.append("[v%d]" % i)
    fmt = "aresample=48000,aformat=channel_layouts=stereo"
    if vo:
        fg.append("%samix=inputs=%d:normalize=0,apad=whole_dur=%.2f,%s,loudnorm=I=-16:TP=-2:LRA=11[vo]" % ("".join(vo), len(vo), D, fmt))
    mu = m.get("music")
    if mu:
        k = add(mu["file"]); at = float(mu.get("at", 0)); g = mu.get("gain_db", -11)
        fg.append("[%d:a]%s,volume=%sdB,asplit=2[ma][mb]" % (k, fmt, g))
        if mu.get("until") is not None:
            u = float(mu["until"])
            fg.append("[ma]atrim=0:%.3f,asetpts=PTS-STARTPTS,afade=t=in:d=%.2f,afade=t=out:st=%.3f:d=0.25,adelay=%d|%d[m1]"
                      % (u + 0.25, mu.get("fade_in", 0.3), u, at * 1000, at * 1000))
            fg.append("[mb]atrim=start=%.3f:end=%.3f,asetpts=PTS-STARTPTS,afade=t=in:d=0.06,adelay=%d|%d[m2]"
                      % (mu["ending_from"], mu["ending_to"], (at + u) * 1000, (at + u) * 1000))
            fg.append("[m1][m2]amix=inputs=2:normalize=0,apad=whole_dur=%.2f[bed]" % D)
        else:
            fg.append("[ma]atrim=0:%.2f,asetpts=PTS-STARTPTS,afade=t=in:d=%.2f,afade=t=out:st=%.2f:d=2,adelay=%d|%d,apad=whole_dur=%.2f[bed]"
                      % (D - at, mu.get("fade_in", 0.3), D - at - 2, at * 1000, at * 1000, D))
            fg.append("[mb]anullsink")
    fx = []
    for i, s in enumerate(m.get("sfx", [])):
        k = add(s["file"])
        c = "[%d:a]%s" % (k, fmt)
        if s.get("trim"):
            c += ",atrim=0:%.2f,afade=t=out:st=%.2f:d=0.15" % (s["trim"], max(0, s["trim"] - 0.15))
        c += ",volume=%sdB,adelay=%d|%d[s%d]" % (s.get("db", -14), s["t"] * 1000, s["t"] * 1000, i)
        fg.append(c); fx.append("[s%d]" % i)
    if fx:
        fg.append("%samix=inputs=%d:normalize=0,apad=whole_dur=%.2f[sfx]" % ("".join(fx), len(fx), D))
    parts = []
    if vo and mu:
        d = m.get("duck", {})
        fg.append("[vo]asplit=2[v1][sc]")
        fg.append("[bed][sc]sidechaincompress=threshold=%s:ratio=%s:attack=25:release=450[duck]" % (d.get("threshold", 0.025), d.get("ratio", 7)))
        parts += ["[v1]", "[duck]"]
    else:
        parts += ["[vo]"] if vo else []
        parts += ["[bed]"] if mu else []
    parts += ["[sfx]"] if fx else []
    fg.append("%samix=inputs=%d:duration=longest:normalize=0,atrim=0:%.2f,loudnorm=I=%s:TP=-1.2:LRA=11,aresample=48000[mix]"
              % ("".join(parts), len(parts), D, m.get("lufs", -14)))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", ";".join(fg), "-map", "[mix]", "-c:a", "pcm_s16le", a.out], check=True)
    st = subprocess.run(["ffmpeg", "-nostats", "-i", a.out, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", st); peak = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", st)
    print("wrote %s (%s LUFS, peak %s dBFS)" % (a.out, lufs[-1] if lufs else "?", peak[-1] if peak else "?"))


if __name__ == "__main__":
    main()
