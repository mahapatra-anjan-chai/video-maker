"""film.py: scene timing on the music's grid, the page it writes from the scene plan (any text animation, the picked
transitions, the background's colours, logo and lockup cards with an icon), and the timing written back for the storyboard.
No render, no background video (plain backgrounds), a second or two."""
import json, os, re, shutil, sys, tempfile, unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import film  # noqa: E402

PLAN = {"name": "Acme", "look": "brand", "size": "1920x1080", "background": "plain", "bpm": 120, "offset": 0.1, "fade": 0.8,
        "scenes": [
            {"id": 1, "label": "Open", "text": "Too many tabs.", "parts": "Your work|Docs|Mail|Chat|Calendar", "anim": "card-cloud", "tr": "pixel", "beats": 8},
            {"id": 2, "label": "Lines", "text": "It adds up.", "lines": ["Every day.", "Every week."], "anim": "fade-up", "tr": "wipe", "beats": 12},
            {"id": 3, "label": "Name", "kind": "logo", "text": "Acme, in one place.", "icon": "icon.png", "tr": "blur", "beats": 6},
            {"id": 4, "label": "Roll", "text": "Built for teams.", "parts": "Built for|teams.|launches.", "anim": "roll-list", "tr": "cut", "beats": 8},
            {"id": 5, "label": "End", "kind": "lockup", "text": "Try Acme today.", "beats": 8}]}


class Timing(unittest.TestCase):
    def test_scenes_sit_on_the_beat_grid(self):
        p = json.loads(json.dumps(PLAN))
        total = film.timing(p)
        s = p["scenes"]
        self.assertEqual(s[0]["at"], 0)
        self.assertAlmostEqual(s[0]["end"], 0.1 + 8 * 0.5, places=2)              # beat 8 at 120 BPM, after the offset
        self.assertEqual(s[1]["at"], s[0]["end"])
        self.assertEqual(s[0]["tr_cover"], s[0]["end"])                          # the transition lands on the next scene's start
        self.assertNotIn("tr_cover", s[-1])
        self.assertAlmostEqual(total, 0.1 + 42 * 0.5, places=2)
        for sc in s:
            self.assertAlmostEqual(sc["at"] * 30, round(sc["at"] * 30), places=3)   # on the 1/30 s grid
            self.assertTrue(sc["at"] < sc["lands"] < sc["end"])
        self.assertLess(s[-1]["lands"], s[-1]["end"] - 0.8)                       # the lockup's frame is taken before the fade
        self.assertEqual(len(s[1]["line_at"]), 2)
        self.assertTrue(s[1]["at"] < s[1]["line_at"][0] < s[1]["line_at"][1] < s[1]["end"])

    def test_a_scene_needs_a_length(self):
        p = {"scenes": [{"id": 1, "text": "x"}]}
        with self.assertRaises(ValueError):
            film.timing(p)


@unittest.skipUnless(shutil.which("node"), "needs node")
class Build(unittest.TestCase):
    def setUp(self):
        from PIL import Image
        self.d = tempfile.mkdtemp(); self.out = os.path.join(self.d, "public")
        Image.new("RGBA", (64, 64), (90, 52, 245, 255)).save(os.path.join(self.d, "icon.png"))
        self.scenes = os.path.join(self.d, "scenes.json")
        json.dump(PLAN, open(self.scenes, "w"))

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def page_plan(self, page):
        return json.loads(re.search(r"var P = (\{.*?\}), PAL = ", page, re.S).group(1))

    def test_the_page(self):
        page = film.build(self.scenes, self.out)
        self.assertIn('id="L0" style="opacity:1"', page)                         # the first scene shows without a set at time 0
        self.assertEqual(len(re.findall(r'class="layer" id="L\d+"', page)), 5)
        self.assertIn('id="H0"', page)                                           # a card piece gets its line as a headline
        self.assertNotIn('id="H3"', page)                                        # a one-line piece (roll list) does not
        self.assertIn('id="S1_0"', page); self.assertIn('id="S1_1"', page)       # the extra lines
        self.assertIn('src="media/icon-2.png"', page)
        self.assertTrue(os.path.exists(os.path.join(self.out, "media", "icon-2.png")))
        self.assertNotIn("<video", page)                                         # plain: no background video
        P = self.page_plan(page)
        self.assertEqual([s.get("tr") for s in P["scenes"]], ["pixel", "wipe", "blur", "cut", None])
        self.assertEqual(P["scenes"][1]["anim"], "fade-up")
        gsap = os.path.exists(os.path.join(os.path.dirname(os.path.dirname(HERE)), "youtube-edit", "assets", "vendor", "gsap.min.js"))  # from setup.sh
        for f in (["vendor/gsap.min.js"] if gsap else []) + ["vendor/text-fx.js", "hyperframes.json"]:
            self.assertTrue(os.path.exists(os.path.join(self.out, f)), f)

    def test_timing_is_written_back_and_the_plan_kept(self):
        film.build(self.scenes, self.out)
        p = json.load(open(self.scenes))
        self.assertEqual(p["scenes"][1]["anim"], "fade-up")
        self.assertEqual(p["scenes"][0]["parts"], PLAN["scenes"][0]["parts"])
        self.assertIn("lands", p["scenes"][2]); self.assertIn("tr_cover", p["scenes"][0])

    def test_the_colours_follow_the_background(self):
        import tfx
        from unittest import mock
        for bg in ("plain", "halftone-dark"):
            with open(self.scenes, "w") as f:
                json.dump(dict(PLAN, background=bg), f)
            with mock.patch.object(film, "background", lambda *a, **k: ""):       # no video in a test
                P = self.page_plan(film.build(self.scenes, self.out))
            self.assertEqual(P["palette"], tfx.palettes("brand")[bg])            # the planner's colours, from the same function
        self.assertEqual(P["palette"]["ink"], "#FFFFFF")

    def test_unknown_picks_are_refused(self):
        for bad in ({"anim": "no-such"}, {"tr": "spin"}, {"kind": "video"}):
            p = json.loads(json.dumps(PLAN)); p["scenes"][0].update(bad)
            json.dump(p, open(self.scenes, "w"))
            with self.assertRaises(ValueError, msg=str(bad)):
                film.build(self.scenes, self.out)
        with open(self.scenes) as f:
            self.assertEqual(json.load(f)["scenes"][0].get("at"), None)          # nothing written on a refusal


if __name__ == "__main__":
    unittest.main()
