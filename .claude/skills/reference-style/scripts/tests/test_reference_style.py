"""reference-style on a made-up clip: known cuts, known colours, no text, no network."""
import json, os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.dirname(HERE)


def run(*args):
    return subprocess.run([sys.executable] + list(args), capture_output=True, text=True, check=True).stdout


@unittest.skipUnless(shutil.which("ffmpeg"), "needs ffmpeg")
class Scan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()
        # 2 s red, 2 s blue, 2 s white with an orange square sliding across: two hard cuts, an accent, motion
        v = os.path.join(cls.d, "ref.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y",
                        "-f", "lavfi", "-i", "color=c=0xC0392B:s=320x180:d=2:r=24",
                        "-f", "lavfi", "-i", "color=c=0x1F3A93:s=320x180:d=2:r=24",
                        "-f", "lavfi", "-i", "color=c=0xF4F1EA:s=320x180:d=2:r=24",
                        "-f", "lavfi", "-i", "color=c=0xFF8C00:s=40x40:d=2:r=24",
                        "-filter_complex", "[2:v][3:v]overlay=x='20+t*110':y=70[c];[0:v][1:v][c]concat=n=3:v=1[v]",
                        "-map", "[v]", "-pix_fmt", "yuv420p", v], check=True)
        cls.out = os.path.join(cls.d, "scan")
        run(os.path.join(HERE, "style-scan.py"), "--video", v, "--out", cls.out, "--no-text", "--strips", "2")
        cls.scan = json.load(open(os.path.join(cls.out, "scan.json")))

    def test_motion_is_measured_at_the_full_frame_rate(self):
        m = json.load(open(os.path.join(self.out, "motion.json")))
        slides = [x for x in m["moves"] if x["kind"] == "slide"]
        self.assertTrue(slides, m["moves"])
        self.assertEqual((slides[0]["direction"], slides[0]["family"]), ("right", "linear"))   # x = 20 + 110 t
        self.assertTrue(os.path.exists(os.path.join(self.out, "curves.png")))
        self.assertIn("measured", self.scan["motion"])

    def test_cuts_and_shots(self):
        p = self.scan["pacing"]
        self.assertAlmostEqual(p["median_shot_s"], 2.0, delta=0.3)
        self.assertAlmostEqual(p["cuts_per_min"], 20.0, delta=5)       # 2 cuts in 6 s

    def test_palette_finds_the_blocks_and_the_accent(self):
        hexes = [p["hex"] for p in self.scan["palette"]]

        def near(target):
            t = [int(target[i:i + 2], 16) for i in (1, 3, 5)]
            return min(sum((int(h[i:i + 2], 16) - c) ** 2 for i, c in zip((1, 3, 5), t)) for h in hexes) ** 0.5
        for c in ("#C0392B", "#1F3A93", "#F4F1EA"):
            self.assertLess(near(c), 40, c)
        self.assertLess(near("#FF8C00"), 60)

    def test_sheets(self):
        for f in ("shots.jpg", "motion.jpg", "palette.png", "SCAN.md"):
            self.assertTrue(os.path.exists(os.path.join(self.out, f)), f)


class CardAndSave(unittest.TestCase):
    def test_card_and_skill(self):
        d = tempfile.mkdtemp()
        skills = os.path.join(d, "skills"); os.makedirs(os.path.join(skills, "youtube-edit", "styles"))
        style = json.load(open(os.path.join(SKILL, "style-template.json")))
        open(os.path.join(d, "widget.html"), "w").write("<div>built for the style</div>")
        style["custom_files"] = ["widget.html"]
        json.dump(style, open(os.path.join(d, "style.json"), "w"))
        run(os.path.join(HERE, "style-card.py"), "--style", os.path.join(d, "style.json"), "--out", os.path.join(d, "card.png"))
        self.assertTrue(os.path.exists(os.path.join(d, "card.png")))
        if not shutil.which("ffmpeg"):
            return
        v = os.path.join(d, "ours.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=320x180:d=3:r=24", "-pix_fmt", "yuv420p", v], check=True)
        run(os.path.join(HERE, "style-save.py"), "skill", "--style", os.path.join(d, "style.json"), "--preview", v, "--skills-dir", skills)
        sk = os.path.join(skills, "style-collage-explainer")
        for f in ("SKILL.md", "style.json", "card.png", "preview.jpg", "components/widget.html"):
            self.assertTrue(os.path.exists(os.path.join(sk, f)), f)
        self.assertTrue(os.path.exists(os.path.join(skills, "youtube-edit", "styles", "ref-collage-explainer.json")))
        md = open(os.path.join(sk, "SKILL.md")).read()
        self.assertIn("name: style-collage-explainer", md)
        self.assertIn("grain-overlay", md)


if __name__ == "__main__":
    unittest.main()
