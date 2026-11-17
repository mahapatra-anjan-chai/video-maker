"""fast-cut.py: the scan finds a frozen stretch, and a render honours segments, speed, text and zoom."""
import json, os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FC = os.path.join(HERE, "fast-cut.py")


def ff(*a):
    subprocess.run(["ffmpeg", "-y", "-v", "error"] + list(a), check=True)


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True, check=True).stdout)


@unittest.skipUnless(shutil.which("ffmpeg"), "needs ffmpeg")
class FastCut(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="fastcut-test-"); self.addCleanup(shutil.rmtree, self.d, True)
        self.v = os.path.join(self.d, "rec.mp4")
        # 2 s of motion, then 3 s frozen (a "loading" stretch), then 2 s of motion
        a, b = os.path.join(self.d, "a.mp4"), os.path.join(self.d, "b.mp4")
        ff("-f", "lavfi", "-i", "testsrc2=s=320x568:r=30:d=2", "-vf", "tpad=stop_mode=clone:stop_duration=3", "-pix_fmt", "yuv420p", a)
        ff("-f", "lavfi", "-i", "testsrc2=s=320x568:r=30:d=2", "-pix_fmt", "yuv420p", b)
        ff("-i", a, "-i", b, "-filter_complex", "[0][1]concat=n=2:v=1", "-pix_fmt", "yuv420p", self.v)

    def run_fc(self, *a):
        r = subprocess.run([sys.executable, FC] + list(a), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_scan_speeds_up_the_frozen_stretch(self):
        cut = os.path.join(self.d, "cut.json")
        self.run_fc("scan", "--video", self.v, "--out", cut, "--speed", "6")
        segs = json.load(open(cut))["segments"]
        still = [s for s in segs if s.get("note") == "still"]
        self.assertEqual(len(still), 1, segs)
        self.assertAlmostEqual(still[0]["from"], 2.15, delta=0.3)
        self.assertAlmostEqual(still[0]["to"], 4.85, delta=0.3)
        self.assertEqual(still[0]["speed"], 6)

    def test_render_segments_speed_text_zoom(self):
        cut = os.path.join(self.d, "cut.json")
        json.dump({"size": [360, 640], "fps": 30, "fit": "cover", "audio": "mute",
                   "segments": [{"src": "rec.mp4", "from": 0, "to": 2, "speed": 1}, {"src": "rec.mp4", "from": 2, "to": 6, "speed": 4}],
                   "zooms": [{"from": 0.3, "to": 1.5, "scale": 1.4, "x": 0.5, "y": 0.4}],
                   "texts": [{"text": "Hello there", "from": 0.2, "to": 2.5, "y": 0.1, "size": 40, "box": "#000000AA"}]},
                  open(cut, "w"))
        out = os.path.join(self.d, "out.mp4")
        self.run_fc("render", "--cut", cut, "--out", out)
        self.assertAlmostEqual(dur(out), 3.0, delta=0.1)                       # 2 s + 4 s at 4x
        draft = os.path.join(self.d, "draft.mp4")
        self.run_fc("render", "--cut", cut, "--out", draft, "--draft")
        wh = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0", draft],
                            capture_output=True, text=True).stdout.strip()
        self.assertEqual(wh, "180,320")


if __name__ == "__main__":
    unittest.main()
