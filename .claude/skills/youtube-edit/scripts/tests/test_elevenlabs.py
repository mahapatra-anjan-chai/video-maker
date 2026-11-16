"""elevenlabs.py without the network: script parsing, the plan gate, word timings, and a stitched voiceover from the cache."""
import json, os, sys, unittest, wave
from .helpers import run, scratch, write, load, ffmpeg, needs_ffmpeg, probe, SCRIPTS

sys.path.insert(0, SCRIPTS)
import elevenlabs as el  # noqa: E402

SCRIPT = """# a note, ignored
HOST: Welcome back to the channel.
GUEST: Thanks for having me.

Plain line in the narrator voice.
[pause 1.0]
HOST: Let's go.
"""


def alignment(text, per=0.05):
    return {"characters": list(text), "character_start_times_seconds": [i * per for i in range(len(text))],
            "character_end_times_seconds": [(i + 1) * per for i in range(len(text))]}


class Parse(unittest.TestCase):
    def test_speakers_cast_pause_para(self):
        items, auto = el.parse_script(SCRIPT, "Brian", {"HOST": "Daniel"})
        kinds = [i["kind"] for i in items]
        self.assertEqual(kinds, ["line", "line", "para", "line", "pause", "line"])
        self.assertEqual(items[0]["voice"], "Daniel")
        self.assertEqual(items[1]["speaker"], "GUEST")
        self.assertNotIn(items[1]["voice"], ("Daniel", "Brian"))     # an uncast speaker gets its own voice
        self.assertEqual(items[3]["voice"], "Brian")                 # no speaker: the default voice
        self.assertEqual(items[4]["seconds"], 1.0)
        self.assertEqual(list(auto), ["GUEST"])

    def test_words_from_alignment(self):
        w = el.words_from_alignment(alignment("Hi there, you."), offset=2.0)
        self.assertEqual([x["text"] for x in w], ["Hi", "there,", "you."])
        self.assertAlmostEqual(w[0]["start"], 2.0)
        self.assertAlmostEqual(w[1]["start"], 2.15)
        self.assertAlmostEqual(w[2]["end"], 2.7)

    def test_voice_names_and_ids(self):
        self.assertEqual(el.voice_id("brian"), el.VOICES["Brian"][0])
        self.assertEqual(el.voice_id("A" * 20), "A" * 20)
        with self.assertRaises(SystemExit):
            el.voice_id("Nobody")

    def test_flash_costs_half(self):
        self.assertEqual(el.credits_per_char("eleven_flash_v2_5"), 0.5)
        self.assertEqual(el.credits_per_char("eleven_multilingual_v2"), 1.0)


class Gate(unittest.TestCase):
    def test_plan_without_yes_generates_nothing(self):
        d = scratch(self)
        sp = write(os.path.join(d, "script.txt"), SCRIPT)
        r = run("elevenlabs.py", "voiceover", "--script", sp, "--out", os.path.join(d, "vo"), "--cache", os.path.join(d, "cache"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("COST", r.stdout)
        self.assertIn("nothing generated", r.stdout)
        self.assertFalse(os.path.exists(os.path.join(d, "vo")))
        self.assertFalse(os.path.exists(os.path.join(d, "cache")))

    def test_sfx_plan_without_yes(self):
        d = scratch(self)
        r = run("elevenlabs.py", "sfx", "--prompt", "soft click", "--out", os.path.join(d, "click.mp3"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("nothing generated", r.stdout)
        self.assertFalse(os.path.exists(os.path.join(d, "click.mp3")))


@needs_ffmpeg
class Stitch(unittest.TestCase):
    def test_cached_lines_stitch_with_gaps_and_times(self):
        d = scratch(self)
        cache = os.path.join(d, "cache")
        os.makedirs(cache)
        items, _ = el.parse_script(SCRIPT, "Brian", {"HOST": "Daniel"})
        for it in (i for i in items if i["kind"] == "line"):
            key = el.cache_key(el.voice_id(it["voice"]), "eleven_multilingual_v2", None, it["text"])
            ffmpeg("-f", "lavfi", "-i", "sine=f=440:d=1.0", "-ar", "44100", "-b:a", "128k", os.path.join(cache, key + ".mp3"))
            write(os.path.join(cache, key + ".json"), {"text": it["text"], "alignment": alignment(it["text"], per=1.0 / len(it["text"]))})
        sp = write(os.path.join(d, "script.txt"), SCRIPT)
        r = run("elevenlabs.py", "voiceover", "--script", sp, "--out", os.path.join(d, "vo"), "--cache", cache, "--cast", "HOST=Daniel")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("4 of 4 lines cached", r.stdout)
        meta = load(os.path.join(d, "vo", "voiceover.json"))
        starts = [l["start"] for l in meta["lines"]]
        # 1 s lines: 0 | +0.25 gap | +0.6 paragraph gap | +1.0 pause (no gap after a pause)
        for got, want in zip(starts, [0.0, 1.25, 2.85, 4.85]):
            self.assertAlmostEqual(got, want, delta=0.06)
        words = load(os.path.join(d, "vo", "transcript.json"))
        self.assertEqual(words[0]["text"], "Welcome")
        self.assertEqual(words[0]["speaker"], "HOST")
        last_line_first_word = [w for w in words if w["text"] == "Let's"][0]
        self.assertAlmostEqual(last_line_first_word["start"], starts[-1], delta=0.06)
        self.assertLessEqual(words[-1]["end"], meta["duration"] + 0.01)
        with wave.open(os.path.join(d, "vo", "voiceover.wav")) as wf:
            self.assertEqual(wf.getframerate(), 48000)
            self.assertAlmostEqual(wf.getnframes() / 48000.0, meta["duration"], delta=0.01)

    def test_narration_video_from_colour(self):
        d = scratch(self)
        wav = os.path.join(d, "vo.wav")
        ffmpeg("-f", "lavfi", "-i", "sine=f=300:d=2.0", "-ar", "48000", "-ac", "1", wav)
        out = os.path.join(d, "public", "input-video.mp4")
        r = run("narration-video.py", "--audio", wav, "--out", out, "--bg", "#1A1A2E", "--size", "640x360")
        self.assertEqual(r.returncode, 0, r.stderr)
        streams, total = probe(out)
        self.assertIn("video", streams)
        self.assertIn("audio", streams)
        self.assertAlmostEqual(total, 2.5, delta=0.15)


if __name__ == "__main__":
    unittest.main()
