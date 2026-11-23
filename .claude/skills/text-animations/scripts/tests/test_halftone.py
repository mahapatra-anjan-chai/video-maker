"""halftone.py makes a seamless loop at the asked size, coloured from a look or from given colours. A second each."""
import os, shutil, subprocess, sys, tempfile, unittest

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(HERE, "halftone.py")


def frames(path, w, h):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3).astype(np.float32)


@unittest.skipUnless(shutil.which("ffmpeg"), "needs ffmpeg")
class Halftone(unittest.TestCase):
    def test_a_seamless_loop_in_the_given_colours(self):
        d = tempfile.mkdtemp(); out = os.path.join(d, "bg.mp4")
        subprocess.run([sys.executable, GEN, "--colors", "#FFFFFF,#BBDDFF,#0033CC,#3366FF", "--size", "192x108", "--dur", "2",
                        "--fps", "12", "--out", out], check=True, capture_output=True)
        f = frames(out, 192, 108)
        self.assertEqual(len(f), 24)
        step = np.abs(f[1] - f[0]).mean(); seam = np.abs(f[0] - f[-1]).mean()
        self.assertGreater(step, 0.2)                       # it moves
        self.assertLess(seam, 2.5 * step + 1)               # and the last frame leads back into the first
        blue = (f[..., 2] > f[..., 0] + 60).mean()          # the dots are the given blue, the paper stays light
        self.assertGreater(blue, 0.02)
        self.assertGreater(f.mean(), 150)

    def test_a_look_gives_the_colours(self):
        d = tempfile.mkdtemp(); png = os.path.join(d, "bg.png")
        r = subprocess.run([sys.executable, GEN, "--look", "brand", "--size", "160x90", "--still", png], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.getsize(png) > 1000)
        r = subprocess.run([sys.executable, GEN, "--look", "no-such-look", "--still", png], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
