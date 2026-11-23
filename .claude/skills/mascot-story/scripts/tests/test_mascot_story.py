"""mascot-story builds its page from a story.json: the character, both scenes, the phone feed, the slice and the prop,
at 16:9 and 9:16. No render, no network, a second."""
import importlib.util, json, os, tempfile, unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("ms", os.path.join(HERE, "mascot_story.py"))
ms = importlib.util.module_from_spec(spec); spec.loader.exec_module(ms)
if not os.path.exists(ms.tfx.GSAP):                       # CI has no GSAP (setup.sh --tools): the page still builds
    ms.tfx.GSAP = os.path.join(tempfile.mkdtemp(), "gsap.min.js"); open(ms.tfx.GSAP, "w").close()


def story(size):
    d = tempfile.mkdtemp()
    from PIL import Image
    Image.new("RGBA", (120, 100), (90, 60, 220, 255)).save(os.path.join(d, "char.png"))
    cfg = {"character": "char.png", "size": size, "colors": {"dark": "#101020", "accent": "#7C3AED"},
           "a": {"title": "Endless scrolling"}, "b": {"title": "Shop what|you love", "prop": "bag"}}
    return cfg, d


class Build(unittest.TestCase):
    def test_the_page_has_both_scenes_the_slice_and_the_prop(self):
        for size in ([960, 540], [540, 960]):
            cfg, d = story(size)
            with open(ms.build(cfg, d, os.path.join(d, "work"))) as f:
                page = f.read()
            for want in ('id="A"', 'id="B"', 'id="feed"', 'id="hero"', 'id="prop"', '"slice"', "Endless scrolling", "Shop what<br>you love",
                         'data-width="%d"' % size[0], "character.png"):
                self.assertIn(want, page, (size, want))
            self.assertTrue(os.path.exists(os.path.join(d, "work", "character.png")))
            self.assertTrue(os.path.exists(os.path.join(d, "work", "text-fx.js")))

    def test_the_cut_runs_through_the_phone(self):
        for W, H in ((1920, 1080), (1080, 1920), (1080, 1080)):
            L = ms.layout(W, H)
            cx, cy = L["px"] + L["pw"] / 2, L["py"] + L["ph"] / 2
            self.assertAlmostEqual(L["y_at"](cx), cy, delta=1)
            self.assertLess(L["cut"][1], L["cut"][0])             # it rises to the right

    def test_colours_come_from_a_look(self):
        c = ms.colours({"look": "brand"})
        self.assertTrue(all(v.startswith("#") for v in c.values()))


if __name__ == "__main__":
    unittest.main()
