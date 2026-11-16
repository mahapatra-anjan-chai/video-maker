"""scenes.py: reading the creator's "when", finding it in the transcript, and checking a scene plan (no snapshots)."""
import json, os, sys, unittest
from .helpers import run, scratch, write, load, SCRIPTS

sys.path.insert(0, SCRIPTS)
import scenes as sc  # noqa: E402

WORDS = [{"text": t, "start": i * 0.4, "end": i * 0.4 + 0.3} for i, t in enumerate(
    "Most product videos take a week to edit. This one took ten minutes, and it cost nothing to render.".split())]


class Phrase(unittest.TestCase):
    def test_quotes_and_verbs(self):
        self.assertEqual(sc.phrase_of('when I say "let\'s go"'), "let's go")
        self.assertEqual(sc.phrase_of("When the voiceover says “ten minutes”"), "ten minutes")
        self.assertEqual(sc.phrase_of("when she mentions pricing"), "pricing")
        self.assertEqual(sc.phrase_of("when she says it's free"), "it's free")
        self.assertEqual(sc.timecode("around 0:04"), 4.0)

    def test_find_exact_stemmed_and_fuzzy(self):
        toks = [(sc.norm(w["text"])[0], w["start"], w["end"]) for w in WORDS]
        hits, _ = sc.find(toks, "ten minutes")
        self.assertEqual(len(hits), 1)
        self.assertAlmostEqual(hits[0][0], WORDS[11]["start"])
        hits, _ = sc.find(toks, "it costs nothing")            # "costs" finds the spoken "cost"
        self.assertAlmostEqual(hits[0][0], WORDS[14]["start"])
        hits, fuzzy = sc.find(toks, "a whole week to edit")     # one extra word: a fuzzy hit on the right words
        self.assertFalse(hits)
        self.assertAlmostEqual(fuzzy[0][0], WORDS[4]["start"])
        self.assertEqual(sc.find(toks, "the weather"), ([], None))


class Snap(unittest.TestCase):
    def project(self, plan, beats=None):
        d = scratch(self)
        write(os.path.join(d, "transcript.json"), WORDS)
        write(os.path.join(d, "scenes.json"), [{"id": "s1", "when": "ten minutes", "what": "a chip", "files": []},
                                                {"id": "s2", "when": "the weather", "what": "a sun", "files": []}])
        write(os.path.join(d, "storyboard.json"), {"id": "t", "duration": 8.0, "beats": beats or [
            {"type": "chip", "id": "ch", "note": "s1", "text": "ten minutes", "in": 4.3, "out": 5.2, "anchor": "-"}]})
        write(os.path.join(d, "scene-plan.json"), plan)
        return d

    def test_good_plan_passes_and_stamps(self):
        d = self.project({"scenes": [
            {"note": "s1", "status": "planned", "build": "a chip on ten minutes", "in": 4.3, "out": 5.2},
            {"note": "s2", "status": "needs-info", "question": "The weather is never mentioned: where should the sun go?"}]})
        r = run("scenes.py", "snap", "--project", d, "--no-snap")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("updated", load(os.path.join(d, "scene-plan.json")))

    def test_missing_rows_and_bad_rows_fail(self):
        d = self.project({"scenes": [{"note": "s1", "status": "maybe", "in": 4.3, "out": 5.2}]})
        r = run("scenes.py", "snap", "--project", d, "--no-snap")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("s2 has no row", r.stdout)
        self.assertIn("status 'maybe'", r.stdout)

    def test_needs_info_needs_a_question_and_times_must_fit(self):
        d = self.project({"scenes": [
            {"note": "s1", "status": "planned", "build": "x", "in": 7.0, "out": 9.5},
            {"note": "s2", "status": "needs-info"}]})
        r = run("scenes.py", "snap", "--project", d, "--no-snap")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("outside the video", r.stdout)
        self.assertIn("without a question", r.stdout)

    def test_untagged_scene_warns(self):
        d = self.project({"scenes": [
            {"note": "s1", "status": "planned", "build": "x", "in": 4.3, "out": 5.2},
            {"note": "s2", "status": "custom", "build": "a sun drawn by hand", "in": 6.0, "out": 7.0}]})
        r = run("scenes.py", "snap", "--project", d, "--no-snap")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn('no storyboard beat carries "note": "s2"', r.stdout)

    def test_anchor_json(self):
        d = self.project({"scenes": []})
        r = run("scenes.py", "anchor", "--project", d, "--json")
        rows = json.loads(r.stdout)
        self.assertEqual(rows[0]["hits"][0][0], round(WORDS[11]["start"], 2))
        self.assertEqual(rows[1]["hits"], [])


if __name__ == "__main__":
    unittest.main()
