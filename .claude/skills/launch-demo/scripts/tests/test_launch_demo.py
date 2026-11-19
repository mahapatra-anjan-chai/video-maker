"""launch-demo on made-up inputs: the page builds with its media tags, the beat reader finds a known tempo, drop and
ending, and the mix lands at its loudness. No network, no credits, a few seconds."""
import importlib.util, json, os, re, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.dirname(HERE)


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def wav(path, x, sr=22050):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "-", path], input=x.astype("float32").tobytes(), check=True)


class Build(unittest.TestCase):
    def test_example_builds_with_media_and_length(self):
        d = tempfile.mkdtemp()
        page = load("build").build(os.path.join(SKILL, "example", "demo.json"), None, os.path.join(d, "public"))
        cfg = json.load(open(os.path.join(SKILL, "example", "demo.json")))
        self.assertIn('data-duration="%s"' % cfg["duration"], page)
        for vid in ('id="ov0"', 'id="ov1"', 'id="vHook"', 'id="fv0"', 'id="fv1"'):
            self.assertIn(vid, page)
        self.assertNotIn("/*CONFIG*/", page)
        self.assertNotIn("<!--HOOK-VIDEO-->", page)
        self.assertTrue(os.path.exists(os.path.join(d, "public", "vendor", "devices.css")))
        # every <video> carries its own start and is muted
        for tag in re.findall(r"<video [^>]*>", page):
            self.assertIn("data-start=", tag); self.assertIn("muted", tag)


@unittest.skipUnless(shutil.which("ffmpeg"), "needs ffmpeg")
class Beats(unittest.TestCase):
    def test_tempo_drop_and_final_hit(self):
        import numpy as np
        sr, bpm = 22050, 120
        t = np.arange(int(sr * 30)) / sr
        x = np.zeros_like(t)
        beat = 60 / bpm
        for k in range(int(30 / beat)):                 # a click on every beat
            s = int((0.25 + k * beat) * sr)
            amp = 0.15 if k * beat < 10 else 0.8
            if 0.25 + k * beat < 25:
                x[s:s + 400] += amp * np.hanning(400)
        x += np.where((t > 10) & (t < 25), 0.25 * np.sin(2 * np.pi * 110 * t), 0.01 * np.sin(2 * np.pi * 110 * t))
        x[(t > 9) & (t < 10)] *= 0.05                    # a dip before the drop
        d = tempfile.mkdtemp(); p = os.path.join(d, "m.wav"); wav(p, x, sr)
        b = load("beats")
        a = b.analyse(*b.load(p))
        self.assertAlmostEqual(a["bpm"], 120, delta=2)
        self.assertAlmostEqual(a["drop"], 10.25, delta=0.6)
        self.assertAlmostEqual(a["final_hit"], 25.0, delta=0.6)
        plan = b.plan(a, drop_at=40.0, hit_at=60.0)
        self.assertAlmostEqual(plan["music_start"], 40.0 - a["drop"], places=3)
        self.assertIn("splice", plan)


@unittest.skipUnless(shutil.which("ffmpeg"), "needs ffmpeg")
class Mix(unittest.TestCase):
    def test_mix_lands_at_its_loudness(self):
        import numpy as np
        d = tempfile.mkdtemp(); sr = 22050
        t = np.arange(int(sr * 8)) / sr
        wav(os.path.join(d, "voice.wav"), 0.3 * np.sin(2 * np.pi * 220 * t), sr)
        wav(os.path.join(d, "music.wav"), 0.3 * np.sin(2 * np.pi * 440 * t), sr)
        wav(os.path.join(d, "pop.wav"), 0.5 * np.sin(2 * np.pi * 880 * t[:2205]), sr)
        m = {"duration": 6, "voice": [{"file": "voice.wav", "from": 0, "to": 2, "at": 1}],
             "music": {"file": "music.wav", "at": 0.5, "gain_db": -11}, "sfx": [{"file": "pop.wav", "t": 4, "db": -12}], "lufs": -14}
        json.dump(m, open(os.path.join(d, "mix.json"), "w"))
        r = subprocess.run([sys.executable, os.path.join(HERE, "mix.py"), "--mix", os.path.join(d, "mix.json"), "--out", os.path.join(d, "out.wav")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        lufs = float(re.search(r"\((-?[\d.]+) LUFS", r.stdout).group(1))
        self.assertAlmostEqual(lufs, -14, delta=1.5)


if __name__ == "__main__":
    unittest.main()
