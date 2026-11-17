"""compose.py style presets: kit stays the kit, brand swaps palette and font everywhere, mine refuses until set up."""
import os, re, unittest
from .helpers import run, scratch, write, read

BEATS = [{"type": "line", "id": "l1", "text": "You clicked on a thumbnail", "em": [3], "in": 1.0, "out": 3.0, "anchor": "-"},
         {"type": "chip", "id": "ch", "text": "let's be honest", "em": [0, 1, 2], "in": 4.0, "out": 6.0, "anchor": "-"},
         {"type": "stats", "id": "st", "layout": "row", "pos": "tl", "title": "The numbers", "em": [1], "in": 7.0, "out": 10.0,
          "anchor": "-", "items": [{"value": 250, "suffix": "+", "label": "Videos", "at": 7.5}]}]
KIT = ["#0AF0F0", "#0005EE", "#CD00EE", "#FFB904", "rgba(10,240,240", "rgba(205,0,238"]


def board(**extra):
    return dict({"id": "t", "duration": 12.0, "beats": BEATS}, **extra)


class Styles(unittest.TestCase):
    def build(self, spec):
        d = scratch(self)
        r = run("compose.py", "--spec", write(os.path.join(d, "storyboard.json"), spec), "--out", os.path.join(d, "public"))
        page = read(os.path.join(d, "public", "index.html")) if r.returncode == 0 else ""
        return r, page, d

    def test_default_is_kit_and_says_so(self):
        r, page, _ = self.build(board())
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("no \"style\" in the storyboard", r.stdout)
        self.assertIn("#0AF0F0", page)
        self.assertIn('"DM Sans"', page)

    def test_kit_is_unchanged(self):
        r0, plain, _ = self.build(board())
        r1, kit, _ = self.build(board(style="kit"))
        self.assertEqual(r1.returncode, 0, r1.stderr)
        self.assertEqual(plain, kit)

    def test_brand_swaps_palette_and_font(self):
        r, page, d = self.build(board(style="brand"))
        self.assertEqual(r.returncode, 0, r.stderr)
        for old in KIT:
            self.assertNotIn(old.lower(), page.lower(), old)
        self.assertIn("--cyan:#7DD3FC", page)
        self.assertIn("rgba(125,211,252,", page)
        self.assertNotIn("DM Sans", page)
        self.assertEqual(len(re.findall(r'@font-face \{ font-family: "Poppins"', page)), 4)
        for w in (300, 400, 500, 700):
            self.assertTrue(os.path.exists(os.path.join(d, "public", "fonts", "Poppins-%d.woff2" % w)))

    def test_brand_covers_every_format(self):
        from .test_compose_drafts import WORLD, DOC
        beats = [WORLD, DOC] + BEATS[:2] + [
            {"type": "chat", "id": "cf", "frame": "float", "pos": "tr", "in": 12.2, "out": 14.0, "anchor": "-",
             "messages": [["me", "Which agents can touch it?", 12.4], ["them", "Two of them.", 13.0]]},
            {"type": "pills", "id": "pl", "layout": "row", "in": 14.2, "out": 15.0, "anchor": "-",
             "items": [["Read access", 14.3], {"text": "Wrong price", "at": 14.5, "tone": "amber", "mark": "x", "icon": "alert"}]},
            {"type": "list", "id": "ls", "items": [["Candles", 15.3], ["Soap", 15.5]], "marker": "check", "in": 15.2, "out": 16.0, "pos": "tl", "anchor": "-"},
            {"type": "scene", "id": "mo", "kind": "money", "steps": {"drop": 16.3}, "label": "Hundreds of dollars", "label_em": [0],
             "label_color": "amber", "label_at": 16.3, "in": 16.1, "out": 17.0, "anchor": "-"},
            {"type": "growth", "id": "gr", "pos": "tr", "eyebrow": "Weekly views", "value": 248, "prefix": "+", "suffix": "%", "sub": "since",
             "bars": [20, 34, 52, 70, 100], "count_at": 17.2, "bars_at": 17.2, "in": 17.1, "out": 18.0, "anchor": "-"},
            {"type": "bars", "id": "br", "title": "Hours to ship", "em": [2], "in": 18.1, "out": 19.0, "anchor": "-",
             "rows": [{"label": "Editor", "value": 6.5, "text": "6.5 hrs", "at": 18.2}, {"label": "Claude", "value": 0.3, "text": "20 min", "hi": True, "at": 18.4}]},
            {"type": "pipeline", "id": "pp", "title": "", "in": 19.1, "out": 20.0, "anchor": "-",
             "steps": [{"label": "Idea", "icon": "chat", "at": 19.2}, {"label": "Paid", "icon": "money", "at": 19.5, "payoff": True}]},
            {"type": "equation", "id": "eq", "pos": "bottom", "in": 20.1, "out": 21.0, "anchor": "-",
             "terms": [["Skills", 20.2], ["+", 20.3], ["Workflows", 20.4], ["=", 20.5], ["40 hrs saved", 20.6, "em"]]},
            {"type": "popout", "id": "po", "title": "What you need", "items": [["A camera", 21.2]], "marker": "check", "in": 21.1, "out": 22.0, "anchor": "-"}]
        r, page, _ = self.build({"id": "t", "duration": 24.0, "style": "brand", "beats": beats,
                                 "tag": {"n": 1, "of": 5, "label": "Thumbnails", "in": 0.2, "out": 5.3, "pos": "tr"}})
        self.assertEqual(r.returncode, 0, r.stderr)
        flat = re.sub(r"\s+", "", page.lower())
        for leak in ["#0af0f0", "#0005ee", "#cd00ee", "#ffb904", "#04161a", "#1a1200",
                     "rgb(10,240,240", "rgba(10,240,240", "rgb(205,0,238", "rgba(205,0,238", "rgb(255,185,4", "rgba(255,185,4",
                     "rgb(0,5,238", "rgba(0,5,238", "dmsans"]:
            self.assertNotIn(leak, flat, leak)

    def test_mine_refuses_until_ready(self):
        r, page, _ = self.build(board(style="mine"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not set up yet", r.stdout + r.stderr)

    def test_unknown_style_lists_presets(self):
        r, _, _ = self.build(board(style="nope"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("brand", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
