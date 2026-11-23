"""storyboard.py: the times it asks for, matching snapshot files to them, and the sheets and clip it makes. Made-up frames, no
HyperFrames run, a second or two."""
import json, os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import storyboard as sb  # noqa: E402

PLAN = {"scenes": [
    {"id": 1, "label": "Opening", "anim": "card-cloud", "tr": "pixel", "at": 0, "lands": 2.5, "end": 4, "tr_cover": 4.0},
    {"id": 2, "label": "The line", "anim": "accent-words", "tr": "cut", "at": 4, "end": 7},
    {"id": 3, "label": "Lockup", "anim": "accent-words", "tr": "blur", "at": 7, "lands": 8, "end": 10, "tr_cover": 10.0},
    {"id": 4, "label": "End", "anim": "fade-up", "at": 10, "lands": 11, "end": 12}]}


def fake_frames(folder, times, size=(320, 180)):
    from PIL import Image
    for k, t in enumerate(times):
        Image.new("RGB", size, (20 + k * 3 % 200, 80, 160)).save(os.path.join(folder, "frame-%02d-at-%ss.png" % (k, ("%.3f" % t).rstrip("0").rstrip("."))))


class Times(unittest.TestCase):
    def test_heroes_and_transition_windows(self):
        heroes, trs = sb.plan_times(PLAN)
        self.assertEqual([t for _, t in heroes], [2.5, 5.8, 8.0, 11.0])          # scene 2 has no `lands`: 60% in
        self.assertEqual([(a["id"], b["id"], k) for a, b, k, _, _ in trs], [(1, 2, "pixel"), (3, 4, "blur")])   # cuts have no window
        ts = trs[0][4]
        self.assertEqual(len(ts), 16)
        self.assertAlmostEqual(ts[0], 3.6); self.assertAlmostEqual(ts[-1], 4.6)
        self.assertIn(4.0, ts)                                                    # the cover itself is a frame

    def test_only_keeps_the_scene_and_its_transitions(self):
        heroes, trs = sb.plan_times(PLAN, ["2"])
        self.assertEqual([sc["id"] for sc, _ in heroes], [2])
        self.assertEqual([(a["id"], b["id"]) for a, b, _, _, _ in trs], [(1, 2)])
        times = sb.all_times(heroes, trs)
        self.assertEqual(times, sorted(set(times)))


class Files(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); self.out = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True); shutil.rmtree(self.out, ignore_errors=True)

    def test_frames_are_matched_by_the_time_in_their_name(self):
        fake_frames(self.d, [2.5, 3.6, 4.0])
        got = sb.frames_by_time(self.d, [2.5, 3.6, 4.0, 9.0])
        self.assertEqual(sorted(got), [2.5, 3.6, 4.0])                          # 9.0 was never taken: missing, not guessed
        self.assertTrue(got[4.0].endswith("at-4s.png"))

    def test_the_sheets(self):
        from PIL import Image
        heroes, trs = sb.plan_times(PLAN)
        times = sb.all_times(heroes, trs)
        fake_frames(self.d, times)
        frames = sb.frames_by_time(self.d, times)
        s1 = sb.storyboard_sheet(heroes, frames, os.path.join(self.out, "storyboard.jpg"))
        s2 = sb.transitions_sheet(trs, frames, os.path.join(self.out, "transitions.jpg"))
        with Image.open(s1) as a, Image.open(s2) as b:
            self.assertGreater(a.width, 3 * 500); self.assertGreater(a.height, 2 * 300)   # 4 scenes: 3 across, 2 rows
            self.assertGreater(b.height, 2 * 150)                                         # one row per transition

    @unittest.skipUnless(shutil.which("ffmpeg"), "needs ffmpeg")
    def test_the_clip(self):
        heroes, trs = sb.plan_times(PLAN)
        times = sb.all_times(heroes, trs)
        fake_frames(self.d, times)
        out = sb.transitions_clip(trs, sb.frames_by_time(self.d, times), os.path.join(self.out, "t.mp4"), width=320)
        n = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames",
                            "-of", "csv=p=0", out], capture_output=True, text=True).stdout.strip()
        self.assertEqual(int(n), 2 * (16 + 6))                                   # two transitions, each held 0.4 s


if __name__ == "__main__":
    unittest.main()
