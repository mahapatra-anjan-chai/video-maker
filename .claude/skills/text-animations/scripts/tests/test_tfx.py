"""text-fx.js lists the 57 animations once each, in seven groups; the picker carries all of them; the scene planner shows a
video's scenes and its sent line writes back into scenes.json."""
import json, os, shutil, subprocess, sys, unittest

SKILL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIB = os.path.join(SKILL, "text-fx.js")


@unittest.skipUnless(shutil.which("node"), "needs node")
class TextFX(unittest.TestCase):
    def catalogue(self):
        r = subprocess.run(["node", "-e", "global.window=global;require(%s);console.log(JSON.stringify({list:TextFX.list,cats:TextFX.categories,"
                            "ids:TextFX.ids}))" % json.dumps(LIB)], capture_output=True, text=True, check=True)
        return json.loads(r.stdout)

    def test_57_unique_in_seven_groups(self):
        c = self.catalogue()
        self.assertEqual(len(c["list"]), 57)
        self.assertEqual(len(set(c["ids"])), 57)
        counts = {g: sum(1 for a in c["list"] if a["category"] == g) for g in c["cats"]}
        self.assertEqual(counts, {"Entrances": 13, "Emphasis": 12, "Swaps and loops": 7, "Transformations": 6, "Video and UI": 7,
                                  "Cards and cursors": 4, "Transitions": 8})

    def test_transitions_are_exported(self):
        r = subprocess.run(["node", "-e", "global.window=global;require(%s);console.log(typeof TextFX.pixel, typeof TextFX.blurSwap, "
                            "typeof TextFX.transition, TextFX.transitions.map(function(t){return t.id}).join(','))" % json.dumps(LIB)],
                           capture_output=True, text=True, check=True)
        self.assertEqual(r.stdout.split(), ["function", "function", "function", "cut,pixel,blur,wipe,iris,whip,push,zoom,glitch"])
        ids = set(a["id"] for a in self.catalogue()["list"])
        r = subprocess.run(["node", "-e", "global.window=global;require(%s);console.log(JSON.stringify(TextFX.transitions))" % json.dumps(LIB)],
                           capture_output=True, text=True, check=True)
        for t in json.loads(r.stdout)[1:]:
            self.assertIn(t["preview"], ids, t["id"])          # every transition has its own card in the picker

    def test_the_cover_table_matches_the_transitions(self):
        """film.html starts each transition at (scene start - TextFX.transitionCover[kind]): the table must be what transition() does."""
        js = ("global.window=global;global.document={createElement:function(){return {style:{},appendChild:function(){},setAttribute:function(){}}}};"
              "require(%s);var tl={set:function(){return tl},to:function(){return tl},fromTo:function(){return tl}};"
              "var box={appendChild:function(){},clientWidth:100,clientHeight:100},out={};TextFX.transitions.forEach(function(t){"
              "var r=TextFX.transition(tl,t.id,{parentNode:box},{parentNode:box},10,{W:100,H:100,container:box,manage:true,clearFrom:true});"
              "out[t.id]=[+(r.cover-10).toFixed(3),TextFX.transitionCover[t.id]]});console.log(JSON.stringify(out))" % json.dumps(LIB))
        out = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
        self.assertEqual(len(out), 9)
        for k, (got, table) in out.items():
            self.assertAlmostEqual(got, table, places=3, msg=k)

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
        self.assertIn("tfxBackground", widget)                # the backgrounds, sent with the picks
        self.assertNotIn("__", widget.replace("__timelines", "").replace("__proto__", ""))   # every placeholder filled
        self.assertIn("text-fx.js", open(os.path.join(SKILL, "gallery.html")).read())
        self.assertNotIn("tfx-bg", open(os.path.join(SKILL, "gallery.html")).read())



PLAN = {"look": "brand", "background": "halftone-light", "scenes": [
    {"id": 1, "label": "Open", "text": "Too many tabs open.", "anim": "accent-words", "tr": "pixel", "at": 0, "end": 4},
    {"id": 2, "label": "Setup", "text": "One click.", "parts": "Setup|Installed|Live", "anim": "stack-cards", "tr": "blur"},
    {"id": 3, "label": "Screens", "kind": "custom", "text": "Our own screens."},
    {"id": 4, "label": "End", "kind": "lockup", "text": "Try it today.", "anim": "fade-up"}]}


@unittest.skipUnless(shutil.which("node"), "needs node")
class Planner(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.d = tempfile.mkdtemp(); self.scenes = os.path.join(self.d, "scenes.json")
        json.dump(PLAN, open(self.scenes, "w"))

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_the_planner_widget(self):
        out = os.path.join(self.d, "planner.widget.html")
        r = subprocess.run([sys.executable, os.path.join(SKILL, "scripts", "tfx.py"), "planner", "--scenes", self.scenes, "--out", out],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        w = open(out).read()
        self.assertNotIn("<html", w)
        self.assertIn("Too many tabs open.", w)              # the scene's own line, not the library's sample
        self.assertIn("sendPrompt", w)
        self.assertNotIn('"at":', w)                          # the plan only: timing stays out of the widget
        self.assertLess(len(w), 150 * 1024)
        self.assertIn('"kind": "custom"', w)                 # the product's own scene: no dropdown, left out of the sent line
        self.assertIn("Your product's own scene", w)
        self.assertIn('if (sc.kind !== "custom") parts.push', w)

    def test_a_sent_line_is_written_back(self):
        sys.path.insert(0, os.path.join(SKILL, "scripts"))
        import tfx
        plan = json.loads(json.dumps(PLAN))
        changed = tfx.apply_line(plan, "Scene plan: background=halftone-dark; 1=fade-up; 1>2=wipe; 2>3=cut")
        self.assertEqual(len(changed), 4)
        self.assertEqual((plan["background"], plan["scenes"][0]["anim"], plan["scenes"][0]["tr"], plan["scenes"][1]["tr"]),
                         ("halftone-dark", "fade-up", "wipe", "cut"))
        self.assertEqual(plan["scenes"][0]["at"], 0)          # timing untouched
        for bad in ("1=no-such-animation", "9=fade-up", "1>2=spin", "background=neon"):
            with self.assertRaises(ValueError, msg=bad):
                tfx.apply_line(json.loads(json.dumps(PLAN)), "Scene plan: " + bad)

    def test_a_bad_line_writes_nothing(self):
        before = open(self.scenes).read()
        r = subprocess.run([sys.executable, os.path.join(SKILL, "scripts", "tfx.py"), "apply", "--scenes", self.scenes, "--line",
                            "Scene plan: 1=fade-up; 2=nope"], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(open(self.scenes).read(), before)


if __name__ == "__main__":
    unittest.main()
