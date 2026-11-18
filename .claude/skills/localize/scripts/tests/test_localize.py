"""The localize scripts on small made-up inputs: no network, no ElevenLabs credits, a few seconds."""
import importlib.util, json, os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(os.path.dirname(HERE), "fonts", "NotoSansJP.ttf")


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def run(*args, **kw):
    return subprocess.run([sys.executable] + list(args), capture_output=True, text=True, check=True, **kw).stdout


def tone(path, secs, hz=440, rate=44100):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=%d:duration=%.3f:sample_rate=%d" % (hz, secs, rate),
                    "-ac", "1", path], check=True)


class Blocks(unittest.TestCase):
    def test_one_band_per_speaker_and_style(self):
        sb = load("subband")
        cues = [{"start": 0, "end": 1, "who": "a", "_style": "dark"}, {"start": 1, "end": 2, "who": "a", "_style": "dark"},
                {"start": 2, "end": 3, "who": "b", "_style": "dark"}, {"start": 3.1, "end": 4, "who": "b", "_style": "light"},
                {"start": 6, "end": 7, "who": "b", "_style": "light"}]
        self.assertEqual([len(b) for b in sb.blocks_of(cues, 0.45)], [2, 1, 1, 1])


class FindSubs(unittest.TestCase):
    def test_ocr_noise_counts_as_the_same_line(self):
        fs = load("find-subs")
        self.assertTrue(fs.same('"I wanna dress like Emma in Paris"', '"/ wanna dress like Emma in Paris"'))
        self.assertTrue(fs.same("Shopwise helps you explore the possibilities.", "o l Shopwise helps you explore the possibilities."))
        self.assertFalse(fs.same("Change the skirt...", "What's better- long or short?"))


class Cues(unittest.TestCase):
    def test_cover_and_run_on(self):
        d = tempfile.mkdtemp()
        script = {"lines": [{"id": 1, "who": "n", "subs": [[0.5, 2.0, "一"], [2.0, 3.0, "二"]]},
                            {"id": 2, "who": "m", "subs": [[5.0, 6.0, "三"]]}]}
        old = [{"start": 0.5, "end": 2.0, "box": [700, 960, 1200, 1010]}, {"start": 2.0, "end": 3.0, "box": [650, 965, 1250, 1015]},
               {"start": 5.0, "end": 6.0, "box": [800, 960, 1100, 1012]}]
        placed = [{"id": 1, "at": 0.5, "dur": 4.9}, {"id": 2, "at": 5.0, "dur": 0.8}]
        for n, o in (("s", script), ("o", old), ("p", placed)):
            json.dump(o, open(os.path.join(d, n + ".json"), "w"))
        run(os.path.join(HERE, "cues.py"), "--script", d + "/s.json", "--subs", d + "/o.json", "--placed", d + "/p.json", "--out", d + "/c.json")
        c = json.load(open(d + "/c.json"))
        self.assertEqual(c[0]["cover"], [700, 960, 1200, 1010])
        self.assertEqual(c[1]["end"], 5.0)            # the voice runs to 5.4 s, but the next cue starts at 5.0
        self.assertEqual(c[2]["who"], "m")


@unittest.skipUnless(shutil.which("ffmpeg"), "needs ffmpeg")
class Dub(unittest.TestCase):
    def test_plan_spends_nothing_and_long_lines_fit(self):
        dub = load("dub")
        d = tempfile.mkdtemp()
        dub.CACHE = d
        script = {"lines": [{"id": 1, "at": 0.5, "end": 1.5, "who": "n", "vo": "あ"},
                            {"id": 2, "at": 2.0, "end": 3.0, "who": "n", "vo": "い"}]}
        cast = {"n": "voice123"}
        json.dump(script, open(d + "/s.json", "w")); json.dump(cast, open(d + "/c.json", "w"))
        # line 1 is 1.9 s of speech for a slot that ends where line 2 starts: it must speed up and push line 2 a little
        tone(os.path.join(d, dub.key_of("voice123", "eleven_multilingual_v2", None, "あ") + ".mp3"), 1.9)
        tone(os.path.join(d, dub.key_of("voice123", "eleven_multilingual_v2", None, "い") + ".mp3"), 0.6)
        sys.argv = ["dub.py", "voice", "--script", d + "/s.json", "--cast", d + "/c.json", "--out", d + "/vo.wav", "--length", "4", "--yes"]
        dub.main()
        rep = {r["id"]: r for r in json.load(open(d + "/vo.json"))}
        self.assertGreater(rep[1]["tempo"], 1.0)
        self.assertLessEqual(rep[1]["tempo"], 1.25)
        self.assertGreaterEqual(rep[2]["at"], rep[1]["at"] + rep[1]["dur"])      # never on top of each other
        self.assertTrue(os.path.exists(d + "/vo.wav"))


@unittest.skipUnless(shutil.which("ffmpeg"), "needs ffmpeg")
class Remix(unittest.TestCase):
    def test_voice_goes_music_stays(self):
        import numpy as np
        d = tempfile.mkdtemp(); st = os.path.join(d, "stems"); os.makedirs(st)
        tone(st + "/no_vocals.wav", 4, 220); tone(st + "/vocals.wav", 4, 880)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", st + "/no_vocals.wav", "-i", st + "/vocals.wav", "-filter_complex",
                        "amix=inputs=2:normalize=0", d + "/orig.wav"], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "4", d + "/vo.wav"], check=True)
        json.dump({"lines": [{"id": 1, "at": 1.0, "end": 2.0, "vo": "x"}]}, open(d + "/s.json", "w"))
        with open(d + "/vo.json", "w") as fh:
            json.dump([], fh)
        run(os.path.join(HERE, "remix.py"), "--original", d + "/orig.wav", "--stems", st, "--script", d + "/s.json",
            "--vo", d + "/vo.wav", "--out", d + "/mix.wav")
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", d + "/mix.wav", "-ac", "1", "-f", "f32le", "-"], capture_output=True).stdout
        x = np.frombuffer(raw, dtype="float32")

        def band(a, b, hz):
            seg = x[int(a * 44100): int(b * 44100)]
            f = np.abs(np.fft.rfft(seg)); fr = np.fft.rfftfreq(len(seg), 1 / 44100)
            return f[(fr > hz - 20) & (fr < hz + 20)].max()
        self.assertLess(band(1.2, 1.8, 880), band(2.6, 3.4, 880) * 0.05)    # the old voice is gone inside its line
        self.assertGreater(band(1.2, 1.8, 220), band(2.6, 3.4, 220) * 0.5)  # the music is not


@unittest.skipUnless(shutil.which("ffmpeg") and os.path.exists(FONT), "needs ffmpeg and fonts/NotoSansJP.ttf (setup.sh)")
class Band(unittest.TestCase):
    def test_band_covers_the_old_line(self):
        d = tempfile.mkdtemp()
        # a grey frame with a white bar where an old subtitle would be
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x404040:s=640x360:d=2:r=24",
                        "-vf", "drawbox=x=220:y=320:w=200:h=14:color=white:t=fill", "-pix_fmt", "yuv420p", d + "/in.mp4"], check=True)
        json.dump([{"start": 0.5, "end": 1.5, "text": "テスト", "cover": [220, 320, 420, 334]}], open(d + "/c.json", "w"))
        run(os.path.join(HERE, "subband.py"), "--video", d + "/in.mp4", "--cues", d + "/c.json", "--out", d + "/out.mp4",
            "--size", "20", "--preset", "ultrafast")
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", "1.0", "-i", d + "/out.mp4", "-frames:v", "1",
                              "-vf", "crop=50:14:222:320,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
        self.assertLess(max(raw), 200)      # the left end of the old bar, clear of the new text, is no longer white


if __name__ == "__main__":
    unittest.main()
