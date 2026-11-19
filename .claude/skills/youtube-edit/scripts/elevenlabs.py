#!/usr/bin/env python3
"""elevenlabs.py: voiceover from a script, and sound effects, through the ElevenLabs API.

Nothing is generated without --yes: every command first prints its plan (lines, voices, characters, estimated credits
and, when the key may read it, the credits left), so the creator can say yes before credits are spent.

Spending as few credits as possible (most creators are on the free plan, 10,000 credits a month):
  - The model follows the plan (--model auto): free accounts get Flash v2.5 (eleven_flash_v2_5, half the credits per
    character, natural sounding); paid accounts get the richer Multilingual v2. ELEVENLABS_MODEL in .env overrides it,
    and so does --model. Without the key's User: Read permission the plan is unknown, so Flash is used.
  - --draft voices the script with the Mac's built-in voice: free, offline, same files and timings shape. Only when
    someone wants to hear the timing before approving the script; the usual flow is script approved, then one
    ElevenLabs generation.
  - Lines already generated come from the cache: an edit pays only for the lines that changed.
  - Never generate samples to pick a voice: the creator listens free on elevenlabs.io (Voices).

  python3 elevenlabs.py balance                        credits used and left this month (needs the key's User: Read)
  python3 elevenlabs.py voices
  python3 elevenlabs.py voiceover --script W/script.txt --out W/voiceover [--voice Brian] [--cast "HOST=Brian,GUEST=Sarah"]
                                  [--draft] [--model eleven_flash_v2_5] [--speed 1.0] [--gap 0.25] [--para-gap 0.6] [--yes]
  python3 elevenlabs.py voiceover --text "One line to say." --out W/voiceover [--yes]
  python3 elevenlabs.py sfx --prompt "soft UI click" --out videos/_shared/sfx/ui-click.mp3 [--seconds 0.8] [--yes]

Script format: one line per take. "SPEAKER: text" picks the speaker's voice from --cast (speakers without a cast entry
get distinct built-in voices, shown in the plan); a line without a speaker uses --voice. A blank line is a paragraph
break (--para-gap of silence instead of --gap). "[pause 1.2]" inserts that many seconds. Lines starting with # are notes.

voiceover writes into --out: voiceover.wav (48 kHz mono, the narration), transcript.json (every word with start / end in
seconds and its speaker, the same shape as a Parakeet transcript, so phrase-times / beat-check / compose work on it), and
voiceover.json (lines, voices, times, credits). sfx writes the file with the lead-in silence trimmed and the peak at -3 dBFS
(the skill's Sound rules). The key comes from ELEVENLABS_API_KEY or the project's .env.
"""
import argparse, base64, hashlib, json, os, re, subprocess, sys, time, urllib.error, urllib.request, wave

API = "https://api.elevenlabs.io/v1"
SKILL = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ROOT = os.path.abspath(os.path.join(SKILL, "..", "..", ".."))
CACHE = os.path.join(ROOT, "videos", "_shared", ".voice-cache")
RATE = 48000

# Premade voices on every account (this key cannot list voices: it lacks voices_read). A raw 20-character voice_id from
# the ElevenLabs dashboard (your own cloned or designed voice) works anywhere a name does.
VOICES = {
    "Brian": ("nPczCjzI2devNBz1zQrb", "deep, warm narrator (default)"),
    "Sarah": ("EXAVITQu4vr4xnSDxMaL", "soft, confident, news"),
    "Rachel": ("21m00Tcm4TlvDq8ikWAM", "calm, young"),
    "Aria": ("9BWtsMINqrJLrRacOk9x", "expressive"),
    "Roger": ("CwhRBWXzGAHq8TQ4Fs17", "confident, laid back"),
    "Laura": ("FGY2WhTYpPnrIDTdsKH5", "upbeat"),
    "Liam": ("TX3LPaxmHKxFdv7VOQHJ", "articulate, young"),
    "Daniel": ("onwK4e9ZLuTAKqWW03F9", "British, authoritative"),
    "Lily": ("pFZP5JQG7iQjIQuC4Bku", "British, warm"),
    "Bill": ("pqHfZKP75CvOlQylNhV4", "trustworthy, older"),
    "Matilda": ("XrExE9yKIg1WjnnlVkGX", "friendly, warm"),
    "Alice": ("Xb7hH8MSUJpSbSDYk0k2", "British, clear"),
    "Will": ("bIHbv24MWmeRgasZH58o", "friendly, relaxed"),
    "Jessica": ("cgSgspJ2msm6clMCkdW9", "expressive, young"),
    "Eric": ("cjVigY5qzO86Huf0OWal", "friendly, middle-aged"),
    "Chris": ("iP95p4xoKVk53GoZ742B", "casual"),
    "Callum": ("N2lVS1w4EtoT3dr4eOWO", "intense, characterful"),
    "River": ("SAz9YHcvj6GT2YYXdXww", "neutral, calm"),
    # Voice Library voices this key can use (checked 2026-10-12). Library voices can carry the owner's own rate.
    "JessicaAnne": ("lxYfHSkYm1EzQzGhdbfc", "Jessica Anne Bogart, narration: a VO pro, confident, conversational"),
    "JessicaAnne-Chatty": ("g6xIsTj2HwM6VR4iXFCw", "Jessica Anne Bogart, chatty and friendly"),
    "JessicaAnne-Character": ("flHkNRp1BlvT73UL6gyz", "Jessica Anne Bogart, character and animation"),
}
DEFAULT_VOICE = "Brian"
CAST_ORDER = ["Brian", "Sarah", "Daniel", "Matilda", "Liam", "Lily", "Eric", "Jessica"]
SFX_PRICE = "about $0.12 a sound on the API price list"


def credits_per_char(model):
    if model == DRAFT_MODEL:
        return 0.0
    return 0.5 if ("flash" in model or "turbo" in model) else 1.0


DRAFT_MODEL = "macos-say"                    # --draft: the Mac's own voice, free and offline
FREE_MODEL, PAID_MODEL = "eleven_flash_v2_5", "eleven_multilingual_v2"


def env_setting(name):
    v = os.environ.get(name, "").strip()
    env = os.path.join(ROOT, ".env")
    if not v and os.path.exists(env):
        for line in open(env):
            if line.strip().startswith(name + "="):
                v = line.split("=", 1)[1].strip().strip('"').strip("'")
    return v


def pick_model(requested):
    """--model auto: ELEVENLABS_MODEL from .env, else Multilingual v2 on a paid plan and Flash on the free plan."""
    if requested != "auto":
        return requested, "chosen"
    m = env_setting("ELEVENLABS_MODEL")
    if m:
        return m, "ELEVENLABS_MODEL in .env"
    b = balance()
    if b and b[2] and b[2].lower() != "free":
        return PAID_MODEL, "%s plan" % b[2]
    return FREE_MODEL, "free plan" if b else "plan unknown, so the cheaper model"


def say_line(text, path):
    """A draft take with macOS `say` (no credits)."""
    subprocess.run(["say", "-r", "185", "-o", path, text], check=True)


def even_words(text, dur, offset):
    """Word timings for a take without alignment (a draft): spread over the take by word length."""
    ws = text.split()
    total = sum(len(w) + 1 for w in ws) or 1
    out, t = [], offset
    for w in ws:
        d = dur * (len(w) + 1) / total
        out.append({"text": w, "start": round(t, 3), "end": round(t + d * 0.9, 3)})
        t += d
    return out


def balance():
    """(used, limit, tier) this month, or None when the key may not read it."""
    try:
        key = api_key()
    except SystemExit:                       # no key yet: the plan still shows, just without the balance
        return None
    try:
        req = urllib.request.Request(API + "/user/subscription", headers={"xi-api-key": key})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
        return d.get("character_count", 0), d.get("character_limit", 0), d.get("tier", "")
    except Exception:
        return None


def voice_id(v):
    if v in VOICES:
        return VOICES[v][0]
    for name, (vid, _) in VOICES.items():
        if name.lower() == v.lower():
            return vid
    if re.fullmatch(r"[A-Za-z0-9]{20}", v):
        return v
    raise SystemExit("unknown voice %r: use a name from `elevenlabs.py voices` or a 20-character voice_id" % v)


def parse_script(text, default_voice, cast):
    """Script text -> items: {"kind": "line", "speaker", "voice", "text"} | {"kind": "pause", "seconds"} | {"kind": "para"}."""
    items, auto = [], {}
    used = set(cast.values()) | {default_voice}
    free = [v for v in CAST_ORDER if v not in used]
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            if items and items[-1]["kind"] == "line":
                items.append({"kind": "para"})
            continue
        if s.startswith("#"):
            continue
        m = re.fullmatch(r"\[pause\s+([0-9.]+)\s*s?\]", s, re.I)
        if m:
            items.append({"kind": "pause", "seconds": float(m.group(1))})
            continue
        m = re.match(r"^([A-Z][A-Z0-9 _'-]{0,30}):\s+(.+)$", s)
        if m:
            spk, body = m.group(1).strip(), m.group(2).strip()
            if spk not in cast and spk not in auto:
                auto[spk] = free.pop(0) if free else default_voice
            voice = cast.get(spk) or auto[spk]
        else:
            spk, body, voice = "", s, default_voice
        items.append({"kind": "line", "speaker": spk, "voice": voice, "text": body})
    while items and items[-1]["kind"] == "para":
        items.pop()
    return items, auto


def cache_key(vid, model, speed, text):
    return hashlib.sha256(json.dumps([vid, model, speed, text]).encode()).hexdigest()[:24]


def words_from_alignment(al, offset=0.0):
    """ElevenLabs character alignment -> [{"text", "start", "end"}], split on whitespace, punctuation kept on the word."""
    words, cur, st, en = [], "", None, None
    for ch, a, b in zip(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]):
        if ch.isspace():
            if cur:
                words.append({"text": cur, "start": round(st + offset, 3), "end": round(en + offset, 3)})
            cur, st = "", None
            continue
        if st is None:
            st = a
        cur += ch
        en = b
    if cur:
        words.append({"text": cur, "start": round(st + offset, 3), "end": round(en + offset, 3)})
    return words


def api_key():
    k = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    env = os.path.join(ROOT, ".env")
    if not k and os.path.exists(env):
        for line in open(env):
            if line.strip().startswith("ELEVENLABS_API_KEY="):
                k = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not k:
        raise SystemExit("no ElevenLabs key: put ELEVENLABS_API_KEY=... in %s" % env)
    return k


def post(path, body, want_json=True):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"xi-api-key": api_key(), "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = r.read()
                return json.loads(data) if want_json else data
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")
            try:
                d = json.loads(msg).get("detail", msg)
                msg = "%s: %s" % (d.get("status", ""), d.get("message", "")) if isinstance(d, dict) else str(d)
            except Exception:
                pass
            if e.code in (429, 500, 502, 503) and attempt < 2:
                time.sleep(4 * (attempt + 1))
                continue
            hint = " (the key is missing that permission: add it on elevenlabs.io > API keys)" if "missing_permissions" in msg else ""
            raise SystemExit("ElevenLabs %s on %s: %s%s" % (e.code, path, msg[:300], hint))


def decode_pcm(path):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(RATE), "-"],
                       capture_output=True, check=True)
    return r.stdout


def cmd_voices(_):
    for name, (vid, desc) in VOICES.items():
        print("%-8s %s  %s" % (name, vid, desc))
    print("\nAny 20-character voice_id from your ElevenLabs dashboard also works (your own cloned or designed voice).")


def cmd_balance(_):
    b = balance()
    if not b:
        raise SystemExit("can't read the balance: give the key the 'User: Read' permission on elevenlabs.io > API keys")
    print("%d of %d credits left this month (%s plan, %d used)" % (b[1] - b[0], b[1], b[2], b[0]))


def cmd_voiceover(a):
    text = open(a.script).read() if a.script else (a.text or "")
    cast = {}
    for pair in filter(None, (a.cast or "").split(",")):
        k, _, v = pair.partition("=")
        cast[k.strip()] = v.strip()
    items, auto = parse_script(text, a.voice, cast)
    lines = [it for it in items if it["kind"] == "line"]
    if not lines:
        raise SystemExit("nothing to say: the script has no lines")
    for it in lines:
        it["voice_id"] = voice_id(it["voice"])
        it["key"] = cache_key(it["voice_id"], a.model, a.speed, it["text"])
        it["cached"] = os.path.exists(os.path.join(a.cache, it["key"] + ".json"))
    todo = [it for it in lines if not it["cached"]]
    chars = sum(len(it["text"]) for it in todo)
    est = int(round(chars * credits_per_char(a.model)))
    if a.draft:
        print("DRAFT the Mac's own voice: free, for timing; generate on ElevenLabs once the script is approved")

    print("PLAN  %d lines, model %s%s" % (len(lines), a.model, ", speed %.2f" % a.speed if a.speed else ""))
    for spk, v in sorted(auto.items()):
        print("      %s has no --cast entry: voice %s (%s)" % (spk, v, VOICES.get(v, ("", "custom"))[1]))
    for i, it in enumerate(lines, 1):
        print("  %2d. %-9s %-8s %s%s" % (i, (it["speaker"] or "-")[:9], it["voice"][:8], it["text"][:70] + ("..." if len(it["text"]) > 70 else ""),
                                       "   (cached)" if it["cached"] else ""))
    print("COST  %d new characters = about %d credits; %d of %d lines cached (free)" % (chars, est, len(lines) - len(todo), len(lines)))
    if todo and not a.draft:
        b = balance()
        if b:
            left = b[1] - b[0]
            print("LEFT  %d of %d credits this month (%s plan)%s" % (left, b[1], b[2],
                  "  NOT ENOUGH: shorten the script or wait for the monthly reset" if est > left else ""))
    if todo and not a.yes and not a.draft:
        print("nothing generated: rerun with --yes once the creator agrees to the cost")
        return

    os.makedirs(a.cache, exist_ok=True)
    for n, it in enumerate(todo, 1):
        print("  generating %d/%d ..." % (n, len(todo)), flush=True)
        if a.draft:
            say_line(it["text"], os.path.join(a.cache, it["key"] + ".aiff"))
            json.dump({"text": it["text"], "voice_id": it["voice_id"], "model": a.model, "alignment": None},
                      open(os.path.join(a.cache, it["key"] + ".json"), "w"))
            continue
        body = {"text": it["text"], "model_id": a.model}
        if a.speed:
            body["voice_settings"] = {"speed": a.speed}
        r = post("/text-to-speech/%s/with-timestamps?output_format=mp3_44100_128" % it["voice_id"], body)
        open(os.path.join(a.cache, it["key"] + ".mp3"), "wb").write(base64.b64decode(r["audio_base64"]))
        json.dump({"text": it["text"], "voice_id": it["voice_id"], "model": a.model, "alignment": r.get("alignment")},
                  open(os.path.join(a.cache, it["key"] + ".json"), "w"))

    os.makedirs(a.out, exist_ok=True)
    pcm, t, words, out_lines = bytearray(), 0.0, [], []
    silence = lambda s: b"\x00\x00" * int(round(s * RATE))
    prev = None
    for it in items:
        if it["kind"] == "pause":
            pcm += silence(it["seconds"]); t += it["seconds"]; prev = "pause"; continue
        if it["kind"] == "para":
            prev = "para"; continue
        if prev is not None and prev != "pause":
            gap = a.para_gap if prev == "para" else a.gap
            pcm += silence(gap); t += gap
        meta = json.load(open(os.path.join(a.cache, it["key"] + ".json")))
        take = os.path.join(a.cache, it["key"] + ".mp3")
        audio = decode_pcm(take if os.path.exists(take) else os.path.join(a.cache, it["key"] + ".aiff"))
        dur = len(audio) / 2.0 / RATE
        for w in words_from_alignment(meta["alignment"], t) if meta.get("alignment") else even_words(it["text"], dur, t):
            w["speaker"] = it["speaker"]
            words.append(w)
        out_lines.append({"speaker": it["speaker"], "voice": it["voice"], "voice_id": it["voice_id"], "text": it["text"],
                          "start": round(t, 3), "end": round(t + dur, 3), "cache": it["key"]})
        pcm += audio; t += dur; prev = "line"
    for i, w in enumerate(words):
        w["id"] = "w%d" % i
    with wave.open(os.path.join(a.out, "voiceover.wav"), "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(RATE); wf.writeframes(bytes(pcm))
    json.dump([{"id": w["id"], "text": w["text"], "start": w["start"], "end": w["end"], "speaker": w["speaker"]} for w in words],
              open(os.path.join(a.out, "transcript.json"), "w"), indent=1)
    json.dump({"model": a.model, "speed": a.speed, "duration": round(t, 3), "credits_estimate": est, "lines": out_lines},
              open(os.path.join(a.out, "voiceover.json"), "w"), indent=2)
    print("wrote %s/voiceover.wav (%.2f s), transcript.json (%d words), voiceover.json" % (a.out, t, len(words)))


def cmd_sfx(a):
    print("PLAN  one sound effect: %r, %s, prompt influence %.2f" % (a.prompt, "%.1f s" % a.seconds if a.seconds else "length chosen by the model", a.influence))
    print("COST  1 generation (%s; this key cannot read the balance, check elevenlabs.io usage)" % SFX_PRICE)
    if not a.yes:
        print("nothing generated: rerun with --yes once the creator agrees to the cost")
        return
    body = {"text": a.prompt, "prompt_influence": a.influence}
    if a.seconds:
        body["duration_seconds"] = a.seconds
    raw = post("/sound-generation?output_format=mp3_44100_128", body, want_json=False)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    tmp = a.out + ".raw.mp3"
    open(tmp, "wb").write(raw)
    # trim the silence before the transient, then peak-normalise to -3 dBFS (SKILL.md, Sound)
    trimmed = a.out + ".trim.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-af", "silenceremove=start_periods=1:start_threshold=-40dB", trimmed], check=True)
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", trimmed, "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"max_volume:\s*(-?[0-9.]+) dB", r.stderr)
    gain = -3.0 - float(m.group(1)) if m else 0.0
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", trimmed, "-af", "volume=%.2fdB" % gain, "-b:a", "192k", a.out], check=True)
    for f in (tmp, trimmed):
        os.remove(f)
    print("wrote %s (peak at -3 dBFS, gain %+.1f dB)" % (a.out, gain))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("voices")
    sub.add_parser("balance")
    v = sub.add_parser("voiceover")
    src = v.add_mutually_exclusive_group(required=True)
    src.add_argument("--script"); src.add_argument("--text")
    v.add_argument("--out", required=True)
    v.add_argument("--voice", default=DEFAULT_VOICE)
    v.add_argument("--cast", default="")
    v.add_argument("--model", default="auto", help="auto (by plan), eleven_flash_v2_5 or eleven_multilingual_v2")
    v.add_argument("--draft", action="store_true", help="the Mac's built-in voice: free, for drafts")
    v.add_argument("--speed", type=float, default=None)
    v.add_argument("--gap", type=float, default=0.25)
    v.add_argument("--para-gap", type=float, default=0.6)
    v.add_argument("--cache", default=CACHE)
    v.add_argument("--yes", action="store_true")
    s = sub.add_parser("sfx")
    s.add_argument("--prompt", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--seconds", type=float, default=None)
    s.add_argument("--influence", type=float, default=0.3)
    s.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
    if getattr(a, "draft", False):
        a.model = DRAFT_MODEL
    elif a.cmd == "voiceover":
        a.model, why = pick_model(a.model)
        print("MODEL %s (%s)" % (a.model, why))
    {"voices": cmd_voices, "voiceover": cmd_voiceover, "sfx": cmd_sfx, "balance": cmd_balance}[a.cmd](a)


if __name__ == "__main__":
    main()
