"""share-skill on made-up skills: the rules catch what must not be published, the diff and the NOTICE/README rows are
right, and `send` builds the pull request from the repo's main with only the skill's files. GitHub is faked: no
network, no account, a few seconds."""
import base64, importlib.util, os, shutil, tempfile, unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
spec = importlib.util.spec_from_file_location("share", os.path.join(HERE, "share.py"))
share = importlib.util.module_from_spec(spec); spec.loader.exec_module(share)

UP = "up/video-maker"
NOTICE = "# What the licence covers\n\n- `.claude/skills/fast-cut/` (scripts)\n- `.claude/skills/localize/`\n\n## Third-party\n"
README = "| Folder | What it is |\n|---|---|\n| `.claude/skills/fast-cut/` | Fast edits |\n| `docs/` | Images |\n"


def write(root, rel, text, mode=None):
    p = os.path.join(root, rel) if rel else root; os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w" if isinstance(text, str) else "wb") as f:
        f.write(text)
    if mode:
        os.chmod(p, mode)


def project(skill="my-skill", scripts=True, tests_pass=True):
    root = tempfile.mkdtemp(prefix="share-")
    shutil.copy(os.path.join(REPO, ".gitignore"), os.path.join(root, ".gitignore"))
    write(root, "NOTICE.md", NOTICE); write(root, "README.md", README)
    base = ".claude/skills/%s/" % skill
    write(root, base + "SKILL.md", "---\nname: %s\ndescription: Makes a thing for product videos. Use for things.\n---\n\n# Body\n" % skill)
    if scripts:
        write(root, base + "scripts/tool.py", "print('hi')\n", 0o755)
        write(root, base + "scripts/tests/__init__.py", "from .test_tool import *  # noqa\n")
        write(root, base + "scripts/tests/test_tool.py",
              "import unittest\nclass T(unittest.TestCase):\n    def test_it(self):\n        self.assertTrue(%s)\n" % tests_pass)
    return root


class Rules(unittest.TestCase):
    def test_a_clean_skill_passes_and_its_tests_run(self):
        r = share.check(project(), "my-skill")
        self.assertTrue(r["ok"], r["blockers"])
        self.assertIn("OK", r["tests"])

    def test_failing_tests_block(self):
        r = share.check(project(tests_pass=False), "my-skill")
        self.assertFalse(r["ok"]); self.assertTrue(any("tests fail" in b for b in r["blockers"]))

    def test_what_must_not_be_published_is_blocked(self):
        root = project(); b = ".claude/skills/my-skill/"
        write(root, b + "demo.mp4", b"\0\0")
        write(root, b + "notes.md", "key: sk_" + "a1" * 20 + "\nsaved in /Users" + "/jane/Movies/x\n")
        write(root, "CLAUDE.local.md", "**My company is Acme.** Use its kit.\n")
        write(root, b + "brand.md", "The Acme look: purple.\n")
        write(root, b + "logo.png", b"\x89PNG")
        msgs = " ".join(share.check(root, "my-skill", run_tests=False)["blockers"])
        for want in ("demo.mp4", "ElevenLabs", "/Users" + "/jane/", "Acme", "logo.png"):
            self.assertIn(want, msgs)

    def test_credited_images_pass(self):
        root = project(); b = ".claude/skills/my-skill/"
        write(root, b + "logo.png", b"\x89PNG"); write(root, b + "CREDITS.md", "logo.png: drawn by me, MIT\n")
        r = share.check(root, "my-skill", run_tests=False)
        self.assertTrue(r["ok"], r["blockers"])

    def test_a_licence_file_next_to_fonts_counts_and_unchanged_files_are_skipped(self):
        root = project(); b = ".claude/skills/my-skill/"
        write(root, b + "fonts/Brand.ttf", b"\0"); write(root, b + "fonts/OFL.txt", "SIL Open Font License\n")
        write(root, b + "old/logo.png", b"\0")
        r = share.check(root, "my-skill", run_tests=False, only={b + "SKILL.md", b + "fonts/Brand.ttf"})
        self.assertTrue(r["ok"], r["blockers"])
        self.assertFalse(share.check(root, "my-skill", run_tests=False)["ok"])   # all files: logo.png has no credit

    def test_structure_rules(self):
        root = project(scripts=False)
        os.remove(os.path.join(root, ".claude/skills/my-skill/SKILL.md"))
        self.assertTrue(any("SKILL.md" in b for b in share.check(root, "my-skill")["blockers"]))
        root = project(scripts=False); write(root, ".claude/skills/my-skill/scripts/run.py", "x = 1\n")
        self.assertTrue(any("no tests" in b for b in share.check(root, "my-skill")["blockers"]))
        root = project(skill="style-vox", scripts=False)
        self.assertTrue(any("reference videos" in b for b in share.check(root, "style-vox")["blockers"]))

    def test_ignored_files_never_count(self):
        root = project(); b = ".claude/skills/my-skill/"
        write(root, b + "scripts/__pycache__/tool.cpython-312.pyc", b"\0")
        write(root, b + ".DS_Store", b"\0")
        files = share.skill_files(root, "my-skill")
        self.assertFalse([f for f in files if "__pycache__" in f or f.endswith(".DS_Store")], files)
        self.assertIn(".claude/skills/my-skill/SKILL.md", files)


class Diff(unittest.TestCase):
    def test_blob_sha_is_gits(self):
        p = os.path.join(tempfile.mkdtemp(), "h"); write(p, "", "hello\n")
        self.assertEqual(share.blob_sha(p), "ce013625030ba8dba906f756967f9e9ca394464a")

    def test_new_changed_deleted(self):
        root = project()
        same = share.blob_sha(os.path.join(root, ".claude/skills/my-skill/SKILL.md"))
        tree = {".claude/skills/my-skill/SKILL.md": same, ".claude/skills/my-skill/scripts/tool.py": "0" * 40,
                ".claude/skills/my-skill/old.md": "1" * 40, "README.md": "2" * 40}
        d = share.diff(root, "my-skill", tree)
        self.assertFalse(d["new_skill"])
        self.assertEqual(d["changed"], [".claude/skills/my-skill/scripts/tool.py"])
        self.assertEqual(d["deleted"], [".claude/skills/my-skill/old.md"])
        self.assertIn(".claude/skills/my-skill/scripts/tests/test_tool.py", d["added"])
        self.assertTrue(share.diff(root, "my-skill", {})["new_skill"])

    def test_rows_land_in_the_lists(self):
        n, r = share.add_rows(NOTICE, README, "my-skill", "Makes a thing.")
        self.assertIn("- `.claude/skills/localize/`\n- `.claude/skills/my-skill/`\n", n)
        self.assertIn("| `.claude/skills/fast-cut/` | Fast edits |\n| `.claude/skills/my-skill/` | Makes a thing. |\n", r)
        self.assertEqual(share.add_rows(n, r, "my-skill", "x"), (n, r))      # never twice


class FakeGH:
    """Answers the GitHub calls send() makes, and records them."""
    def __init__(self, push=False):
        self.calls, self.push = [], push

    def __call__(self, path, method="GET", body=None, ok404=False, soft=False):
        self.calls.append((method, path, body))
        me = UP if self.push else "pmm/video-maker"
        if path.startswith("repos/%s/git/trees/main" % UP): return {"tree": [{"path": "README.md", "type": "blob", "sha": "r"}]}
        if path == "user": return {"login": "pmm"}
        if path == "repos/" + UP: return {"permissions": {"push": self.push}}
        if path == "repos/%s/forks" % UP: return {"full_name": me}
        if "/git/ref/heads/skill/" in path: return None
        if path.endswith("/git/ref/heads/main"): return {"object": {"sha": "head"}}
        if path.endswith("/merge-upstream"): return {}
        if path == "repos/%s/git/commits/head" % UP: return {"tree": {"sha": "basetree"}}
        if path.endswith("/git/blobs"): return {"sha": "blob%d" % len(self.calls)}
        if "/contents/NOTICE.md" in path: return {"content": base64.b64encode(NOTICE.encode()).decode()}
        if "/contents/README.md" in path: return {"content": base64.b64encode(README.encode()).decode()}
        if path.endswith("/git/trees"): return {"sha": "newtree"}
        if path.endswith("/git/commits"): return {"sha": "newcommit"}
        if path.endswith("/git/refs"): return {}
        if path.endswith("/pulls"): return {"html_url": "https://github.com/%s/pull/7" % UP}
        raise AssertionError("unexpected call %s %s" % (method, path))


class Send(unittest.TestCase):
    def test_a_fork_and_a_pull_request_with_only_the_skill(self):
        gh = FakeGH(); out = share.send(project(), "my-skill", gh, UP, wait=0)
        self.assertEqual(out["url"], "https://github.com/%s/pull/7" % UP)
        posts = {p: b for m, p, b in gh.calls if m == "POST"}
        self.assertIn("repos/%s/forks" % UP, posts)
        tree = posts["repos/pmm/video-maker/git/trees"]
        self.assertEqual(tree["base_tree"], "basetree")
        paths = sorted(e["path"] for e in tree["tree"])
        self.assertTrue(all(p.startswith(".claude/skills/my-skill/") or p in ("NOTICE.md", "README.md") for p in paths), paths)
        readme = [e for e in tree["tree"] if e["path"] == "README.md"][0]["content"]
        self.assertIn("| `.claude/skills/my-skill/` | Makes a thing for product videos. |", readme)
        tool = [e for e in tree["tree"] if e["path"].endswith("scripts/tool.py")][0]
        self.assertEqual(tool["mode"], "100755")
        self.assertEqual(posts["repos/pmm/video-maker/git/commits"]["parents"], ["head"])
        pr = posts["repos/%s/pulls" % UP]
        self.assertEqual((pr["head"], pr["base"], pr["title"]), ("pmm:skill/my-skill", "main", "Add the my-skill skill"))
        self.assertIn("- [x] Tests: pass", pr["body"])

    def test_with_push_access_it_branches_instead_of_forking(self):
        gh = FakeGH(push=True); share.send(project(), "my-skill", gh, UP, wait=0)
        self.assertFalse([p for m, p, b in gh.calls if p.endswith("/forks")])
        pr = [b for m, p, b in gh.calls if p.endswith("/pulls")][0]
        self.assertEqual(pr["head"], "skill/my-skill")

    def test_nothing_is_sent_when_the_check_fails(self):
        root = project(); write(root, ".claude/skills/my-skill/clip.mov", b"\0")
        gh = FakeGH()
        with self.assertRaises(SystemExit):
            share.send(root, "my-skill", gh, UP, wait=0)
        self.assertFalse([c for c in gh.calls if c[0] == "POST"])


if __name__ == "__main__":
    unittest.main()
