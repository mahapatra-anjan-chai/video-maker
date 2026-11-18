"""text-fx.js lists the 42 animations once each, in five groups, and the picker files carry all of them."""
import json, os, shutil, subprocess, sys, unittest

SKILL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIB = os.path.join(SKILL, "text-fx.js")


@unittest.skipUnless(shutil.which("node"), "needs node")
class TextFX(unittest.TestCase):
    def catalogue(self):
        r = subprocess.run(["node", "-e", "global.window=global;require(%s);console.log(JSON.stringify({list:TextFX.list,cats:TextFX.categories,"
                            "ids:TextFX.ids}))" % json.dumps(LIB)], capture_output=True, text=True, check=True)
        return json.loads(r.stdout)

    def test_42_unique_in_five_groups(self):
        c = self.catalogue()
        self.assertEqual(len(c["list"]), 42)
        self.assertEqual(len(set(c["ids"])), 42)
        counts = {g: sum(1 for a in c["list"] if a["category"] == g) for g in c["cats"]}
        self.assertEqual(counts, {"Entrances": 12, "Emphasis": 12, "Swaps and loops": 6, "Transformations": 6, "Video and UI": 6})

    def test_every_animation_has_a_builder(self):
        src = open(LIB).read()
        for a in self.catalogue()["list"]:
            self.assertIn('B["%s"]' % a["id"], src, a["id"])

    def test_no_randomness_or_timers(self):
        import re
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", open(LIB).read(), flags=re.S)    # comments may name what the code avoids
        for bad in ("Math.random", "setTimeout", "setInterval", "requestAnimationFrame", "@keyframes"):
            self.assertFalse(bad in code, "%s is in text-fx.js: renders must be deterministic" % bad)

    def test_picker_files(self):
        r = subprocess.run([sys.executable, os.path.join(SKILL, "scripts", "tfx.py"), "picker"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        widget = open(os.path.join(SKILL, "picker.widget.html")).read()
        self.assertIn("sendPrompt", widget)
        self.assertIn("tfx-cat", widget)
        self.assertNotIn("<html", widget)            # a fragment for the chat widget
        self.assertIn("text-fx.js", open(os.path.join(SKILL, "gallery.html")).read())


if __name__ == "__main__":
    unittest.main()
