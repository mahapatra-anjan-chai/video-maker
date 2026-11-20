"""motion.py on tiny made-up clips whose motion is known: a slide that eases out, one that overshoots, a fade, a
pan, a zoom, a stagger, the same slide drawn on twos, a cut, and cuts on a 120 BPM click. A few seconds each."""
import importlib.util, os, shutil, subprocess, tempfile, unittest

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("motion", os.path.join(HERE, "motion.py"))
motion = importlib.util.module_from_spec(spec); spec.loader.exec_module(motion)
E = lambda name: motion.EASES[name][0]
W, H, FPS = 320, 180, 30
rng = np.random.default_rng(7)
BLOCK = rng.integers(150, 256, (24, 56)).astype(np.float32)          # a textured "word"
TEX = np.kron(rng.integers(30, 230, (60, 110)), np.ones((6, 6))).astype(np.float32)   # chunky texture, 360x660


def clip(fn, seconds, audio=None):
    d = tempfile.mkdtemp(prefix="motion-"); p = os.path.join(d, "c.mp4")
    n = int(round(seconds * FPS))
    frames = np.stack([np.clip(fn(i / FPS), 0, 255) for i in range(n)]).astype(np.uint8)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", "%dx%d" % (W, H), "-r", str(FPS), "-i", "-"]
    if audio is not None:
        wav = os.path.join(d, "a.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", "22050", "-ac", "1", "-i", "-", wav],
                       input=audio.astype(np.float32).tobytes(), check=True)
        cmd += ["-i", wav, "-c:a", "aac", "-shortest"]
    cmd += ["-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", p]
    subprocess.run(cmd, input=frames.tobytes(), check=True)
    return p


def put(img, block, x, y, alpha=1.0):
    h, w = block.shape; x, y = int(round(x)), int(round(y))
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 > x0 and y1 > y0:
        img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - alpha) + block[y0 - y:y1 - y, x0 - x:x1 - x] * alpha
    return img


def slide(ease, t0=0.5, dur=0.5, twos=False, bg=30.0):
    def fn(t):
        if twos:
            t = np.floor(t * FPS / 2) * 2 / FPS
        u = np.clip((t - t0) / dur, 0, 1)
        return put(np.full((H, W), bg, np.float32), BLOCK, 40 + 170 * float(E(ease)(np.array(u))), 78)
    return fn


def moves(r, kind=None):
    return [m for m in r["moves"] if kind is None or m["kind"] == kind]


@unittest.skipUnless(shutil.which("ffmpeg"), "needs ffmpeg")
class Moves(unittest.TestCase):
    def test_a_slide_that_eases_out(self):
        r = motion.analyse(clip(slide("power3.out"), 1.6), beats=False)
        m = moves(r, "slide")
        self.assertEqual(len(m), 1, r["moves"]); m = m[0]
        self.assertEqual((m["direction"], m["family"], m["overshoot"]), ("right", "out", False))
        self.assertAlmostEqual(m["start"], 0.5, delta=1.5 / FPS)
        self.assertAlmostEqual(m["dur"], 0.5, delta=0.1)
        self.assertLess(m["peak_at"], 0.35)

    def test_an_overshoot(self):
        m = moves(motion.analyse(clip(slide("back.out(2.5)"), 1.6), beats=False), "slide")[0]
        self.assertTrue(m["overshoot"]); self.assertEqual(m["family"], "overshoot")

    def test_ease_in_and_in_out(self):
        m = moves(motion.analyse(clip(slide("power2.in", dur=0.6), 1.6), beats=False), "slide")[0]
        self.assertEqual(m["family"], "in"); self.assertGreater(m["peak_at"], 0.6)
        m = moves(motion.analyse(clip(slide("power3.inOut", dur=0.7), 1.6), beats=False), "slide")[0]
        self.assertEqual(m["family"], "inOut")

    def test_a_fade(self):
        def fn(t):
            a = float(E("sine.inOut")(np.array(np.clip((t - 0.5) / 0.6, 0, 1))))
            return put(np.full((H, W), 30, np.float32), BLOCK, 130, 78, a)
        m = moves(motion.analyse(clip(fn, 1.6), beats=False))
        self.assertEqual(len(m), 1, m); m = m[0]
        self.assertEqual((m["kind"], m["family"]), ("fade", "inOut"))
        self.assertAlmostEqual(m["dur"], 0.6, delta=0.12)

    def test_a_pan_and_a_zoom(self):
        def pan(t):
            u = float(E("power2.inOut")(np.array(np.clip((t - 0.4) / 1.0, 0, 1))))
            x = int(round(100 * u))
            return TEX[90:90 + H, 100 + x:100 + x + W].copy()
        m = moves(motion.analyse(clip(pan, 1.8), beats=False))
        self.assertEqual(len(m), 1, m); m = m[0]
        self.assertEqual((m["kind"], m["direction"], m["family"]), ("pan", "left", "inOut"))
        self.assertAlmostEqual(m["dur"], 1.0, delta=0.15)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        def zoom(t):
            s = 1 + 0.3 * float(E("power2.inOut")(np.array(np.clip((t - 0.4) / 1.0, 0, 1))))
            return motion.bilinear(TEX, 180 + (yy - H / 2) / s, 330 + (xx - W / 2) / s)
        m = moves(motion.analyse(clip(zoom, 1.8), beats=False))
        self.assertTrue(m and m[0]["kind"] == "zoom", m)
        self.assertAlmostEqual(m[0]["scale"], 1.3, delta=0.06)

    def test_a_stagger(self):
        def fn(t):
            img = np.full((H, W), 30, np.float32)
            for k in range(3):
                u = float(E("power2.out")(np.array(np.clip((t - 0.5 - 0.1 * k) / 0.3, 0, 1))))
                put(img, BLOCK, 30 + k * 60, 90 - 14 * u, u)
            return img
        r = motion.analyse(clip(fn, 1.6), beats=False)
        self.assertTrue(r["staggers"], r["moves"])
        self.assertEqual(r["staggers"][0]["count"], 3)
        self.assertAlmostEqual(r["staggers"][0]["every"], 0.1, delta=1.2 / FPS)

    def test_drawn_on_twos_reads_the_same(self):
        r = motion.analyse(clip(slide("power3.out", twos=True), 1.6), beats=False)
        m = moves(r, "slide")[0]
        self.assertEqual(m["family"], "out"); self.assertGreater(m["repeats_dropped"], 3)
        self.assertAlmostEqual(m["dur"], 0.5, delta=0.12)


@unittest.skipUnless(shutil.which("ffmpeg"), "needs ffmpeg")
class Timing(unittest.TestCase):
    def test_cut_and_the_first_move_after_it(self):
        a, b = slide("power3.out", t0=9), slide("power3.out", t0=1.3, bg=120.0)
        r = motion.analyse(clip(lambda t: a(t) if t < 1.0 else b(t), 2.2), beats=False)
        self.assertEqual(len(r["cuts"]), 1); self.assertAlmostEqual(r["cuts"][0], 1.0, delta=1.5 / FPS)
        m = moves(r, "slide")[0]
        self.assertAlmostEqual(m["after_cut"], 0.3, delta=0.06)

    def test_cuts_on_the_beat(self):
        sr = 22050; x = np.zeros(int(sr * 20.0), np.float32)
        kick = 0.8 * np.sin(2 * np.pi * 60 * np.arange(2205) / sr) * np.exp(-np.arange(2205) / sr / 0.03)
        for k in range(39):                                   # a 120 BPM kick from 0.5 s
            s = int((0.5 + 0.5 * k) * sr); x[s:s + 2205] += kick
        bgs = [40, 140, 70, 200, 90, 160]
        fn = lambda t: np.full((H, W), bgs[int(max(0, t - 0.5)) % 6], np.float32) + (TEX[:H, :W] * 0.1)
        r = motion.analyse(clip(fn, 20.0, audio=x))                # a cut every second, on the beat
        self.assertGreaterEqual(len(r["cuts"]), 15)
        self.assertAlmostEqual(r["beat"]["bpm"], 120, delta=3)
        self.assertGreaterEqual(r["beat"]["cuts_on_beat"], 0.8)


class Eases(unittest.TestCase):
    def test_the_fit_finds_the_family_from_clean_samples(self):
        t = np.arange(0, 16) / 30.0
        for name, fam in (("power3.out", "out"), ("power2.in", "in"), ("sine.inOut", "inOut"), ("none", "linear"),
                          ("back.out(1.7)", "overshoot")):
            f = E(name)(np.clip(t / t[-1], 0, 1)); p = (f - f[0]) / (f[-1] - f[0])
            self.assertEqual(motion.fit_ease(t, p)["family"], fam, name)


if __name__ == "__main__":
    unittest.main()
