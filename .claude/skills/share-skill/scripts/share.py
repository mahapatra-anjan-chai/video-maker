#!/usr/bin/env python3
"""Share a skill with Video maker as a pull request, from the chat. Works on git and zip installs alike: the pull
request is built on GitHub from the repo's own main branch, so nothing else in this folder (videos, .env, the brand
kit) can ride along. Only the skill's folder goes, plus its line in NOTICE.md and the README's skills table.

  python3 share.py list                      which skills here are new or changed compared with the repo
  python3 share.py check <skill> [--no-tests] [--since REF] [--json]   the rules (also run on every pull request)
  python3 share.py plan <skill>              check + exactly what would be sent, the PR title and text
  python3 share.py send <skill> --yes        fork (or branch, with push access), one commit, open the pull request

Needs `gh` signed in for plan's account line and for send (get-gh.sh installs it; see SKILL.md).
"""
import argparse, base64, fnmatch, hashlib, json, os, re, shutil, subprocess, sys, time, urllib.request

UPSTREAM = "mahapatra-anjan-chai/video-maker"
BRANCH = "main"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,48}$")
MEDIA = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv", ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".aiff"}
ASSETS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ttf", ".otf", ".woff", ".woff2", ".psd", ".ai", ".pdf"}
SECRETS = [(re.compile(r"\bsk_[A-Za-z0-9]{24,}"), "an ElevenLabs-style API key"),
           (re.compile(r"ELEVENLABS_API_KEY\s*=\s*[A-Za-z0-9_]{8,}"), "an ElevenLabs key"),
           (re.compile(r"\b(ghp|gho|ghu|ghs)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}"), "a GitHub token"),
           (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "an AWS key"),
           (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "a private key")]
HOME_PATH = re.compile(r"/Users/(?!me/|you/|name/|<|\$|USER)([A-Za-z0-9._-]+)/")
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@(?!example\.com|anthropic\.com|users\.noreply\.github\.com)[A-Za-z0-9.-]+\.[a-z]{2,}\b")


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def read_text(path, errors="strict"):
    with open(path, encoding="utf-8", errors=errors) as f:
        return f.read()


# ---- what counts as the skill's files: everything in its folder that .gitignore does not exclude ----------------
def ignore_rules(root):
    rules = []
    try:
        for line in read_text(os.path.join(root, ".gitignore")).splitlines():
            line = line.rstrip("\n").strip()
            if not line or line.startswith("#"):
                continue
            neg = line.startswith("!"); line = line[1:] if neg else line
            dir_only = line.endswith("/"); line = line.rstrip("/")
            anchored = "/" in line; line = line.lstrip("/")
            rules.append((neg, dir_only, anchored, line))
    except OSError:
        pass
    return rules + [(False, True, False, "__pycache__"), (False, False, False, "*.pyc"), (False, False, False, ".DS_Store")]


def ignored(rel, rules, is_dir=False):
    parts = rel.split("/"); out = False
    for neg, dir_only, anchored, pat in rules:
        hit = False
        for i in range(1, len(parts) + 1):
            if dir_only and i == len(parts) and not is_dir:
                continue
            target = "/".join(parts[:i]) if anchored else parts[i - 1]
            if fnmatch.fnmatchcase(target, pat):
                hit = True; break
        if hit:
            out = not neg
    return out


def skill_files(root, name):
    base = os.path.join(root, ".claude", "skills", name); rules = ignore_rules(root); files = []
    for d, dirs, fs in os.walk(base):
        reld = os.path.relpath(d, root).replace(os.sep, "/")
        dirs[:] = sorted(x for x in dirs if not ignored(reld + "/" + x, rules, is_dir=True))
        for f in sorted(fs):
            rel = reld + "/" + f
            if not ignored(rel, rules) and not os.path.islink(os.path.join(d, f)):
                files.append(rel)
    return files


def blob_sha(path):
    data = read_bytes(path)
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def company_words(root):
    try:
        txt = read_text(os.path.join(root, "CLAUDE.local.md"))
    except OSError:
        return []
    return sorted(set(m.group(1).rstrip(".-") for m in re.finditer(r"[Mm]y company is \**([A-Z][\w&.-]{2,})", txt)))


def frontmatter(path):
    try:
        txt = read_text(path)
    except OSError:
        return None
    m = re.match(r"---\n(.*?)\n---", txt, re.S)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1); out[k.strip()] = v.strip()
    return out


# ---- the rules -------------------------------------------------------------------------------------------------
LICENCE_FILE = re.compile(r"(CREDITS|LICEN[CS]E|NOTICE|COPYING|OFL)[^/]*$", re.I)


def check(root, name, run_tests=True, only=None):
    """The rules. `only`: the files being sent (added or changed); file rules skip the rest, which the repo already has."""
    r = {"skill": name, "blockers": [], "confirm": [], "notes": [], "files": []}
    B, C, N = r["blockers"].append, r["confirm"].append, r["notes"].append
    base = os.path.join(root, ".claude", "skills", name)
    if not NAME_RE.match(name or ""):
        B("The folder name must be lower-case letters, digits and dashes (like `my-skill`).")
    if not os.path.isdir(base):
        B("There is no skill folder `.claude/skills/%s/`." % name); r["ok"] = False; return r
    if name.startswith("style-"):
        B("Styles learned from reference videos stay on this Mac: they copy someone else's work. Share a skill you made.")
    fm = frontmatter(os.path.join(base, "SKILL.md"))
    if fm is None:
        B("`SKILL.md` is missing: every skill needs one.")
    else:
        if fm.get("name") != name:
            B("`SKILL.md` must start with front matter whose `name:` is `%s`." % name)
        if len(fm.get("description", "")) < 20:
            B("`SKILL.md` needs a `description:` that says what the skill does and when to use it.")
    files = skill_files(root, name); r["files"] = files
    credits = ""; licence_dirs = set()
    for f in files:
        if LICENCE_FILE.search(f):
            credits += read_text(os.path.join(root, f), "replace"); licence_dirs.add(os.path.dirname(f))
    words = company_words(root)
    for f in files:
        if only is not None and f not in only:
            continue
        p = os.path.join(root, f); ext = os.path.splitext(f)[1].lower(); size = os.path.getsize(p); short = f.split("/", 2)[-1]
        if os.path.basename(f) in (".env", "CLAUDE.local.md") or f.endswith(".env"):
            B("`%s` is a private file and can't be shared." % short); continue
        if ext in MEDIA:
            B("`%s` is a video or sound file: footage and music stay out of the repo." % short); continue
        if size > 5_000_000:
            B("`%s` is %.1f MB; files over 5 MB can't go in the repo." % (short, size / 1e6)); continue
        if ext in ASSETS:
            if os.path.basename(f) in credits or os.path.dirname(f) in licence_dirs:
                N("`%s`: source and licence in the skill's credits" % short)
            else:
                B("`%s` needs a line in a CREDITS.md in the skill: where it is from and its licence (it must allow sharing)." % short)
            continue
        if size > 1_000_000:
            C("`%s` is %.1f MB: is all of it needed?" % (short, size / 1e6))
        try:
            txt = read_text(p)
        except (UnicodeDecodeError, OSError):
            C("`%s` is not text: say what it is and where it is from." % short); continue
        for rx, what in SECRETS:
            if rx.search(txt):
                B("`%s` contains what looks like %s. Remove it (keys live only in `.env`)." % (short, what))
        m = HOME_PATH.search(txt)
        if m:
            B("`%s` has a path with a Mac user name (`/Users/%s/`). Use a path inside the project instead." % (short, m.group(1)))
        for e in sorted(set(EMAIL.findall(txt)))[:3]:
            C("`%s` mentions the email `%s`: is that OK to publish?" % (short, e))
        for w in words:
            if re.search(r"\b%s\b" % re.escape(w), txt):
                B("`%s` mentions %s, your company (from CLAUDE.local.md). Company names and brand rules stay on this Mac." % (short, w))
    scripts = [f for f in files if re.match(r"\.claude/skills/[^/]+/scripts/[^/]+\.(py|sh|mjs|js)$", f)]
    tests = os.path.join(base, "scripts", "tests", "__init__.py")
    if scripts and not os.path.exists(tests):
        B("The skill has scripts but no tests: add `scripts/tests/` (Claude can write them; see CONTRIBUTING.md).")
    elif os.path.exists(tests) and run_tests:
        t = subprocess.run([sys.executable, "-m", "unittest", "tests"], cwd=os.path.join(base, "scripts"),
                           capture_output=True, text=True, timeout=900)
        lines = t.stderr.strip().splitlines() or ["?"]
        last = " ".join([l for l in lines if l.startswith("Ran ")][-1:] + lines[-1:])
        if t.returncode == 0:
            r["tests"] = last; N("Tests pass (%s)." % last)
        else:
            B("The skill's tests fail: %s" % last); r["tests_output"] = t.stderr[-3000:]
    elif not scripts:
        N("No scripts, so no tests needed.")
    r["ok"] = not r["blockers"]
    return r


# ---- GitHub ----------------------------------------------------------------------------------------------------
def gh_path(root):
    local = os.path.join(root, ".tools", "bin", "gh")
    return local if os.access(local, os.X_OK) else shutil.which("gh")


class GH:
    def __init__(self, exe):
        self.exe = exe

    def __call__(self, path, method="GET", body=None, ok404=False, soft=False):
        cmd = [self.exe, "api", "-X", method, path, "-H", "Accept: application/vnd.github+json"]
        if body is not None:
            cmd += ["--input", "-"]
        p = subprocess.run(cmd, input=json.dumps(body) if body is not None else None, capture_output=True, text=True)
        if p.returncode != 0:
            if soft or (ok404 and ("404" in p.stderr or "Not Found" in p.stdout)):
                return None
            raise SystemExit("GitHub said no to %s %s: %s" % (method, path, (p.stderr or p.stdout).strip()[:300]))
        return json.loads(p.stdout) if p.stdout.strip() else {}


def upstream_tree(gh, upstream=UPSTREAM):
    path = "repos/%s/git/trees/%s?recursive=1" % (upstream, BRANCH)
    if gh is not None:
        data = gh(path)
    else:
        req = urllib.request.Request("https://api.github.com/" + path, headers={"User-Agent": "video-maker-share-skill"})
        data = json.load(urllib.request.urlopen(req, timeout=30))
    return {e["path"]: e["sha"] for e in data.get("tree", []) if e.get("type") == "blob"}


def diff(root, name, tree):
    prefix = ".claude/skills/%s/" % name
    local = {f: blob_sha(os.path.join(root, f)) for f in skill_files(root, name)}
    up = {p: s for p, s in tree.items() if p.startswith(prefix)}
    return {"added": sorted(f for f in local if f not in up),
            "changed": sorted(f for f in local if f in up and up[f] != local[f]),
            "deleted": sorted(f for f in up if f not in local),
            "new_skill": not up}


def describe(root, name):
    d = (frontmatter(os.path.join(root, ".claude", "skills", name, "SKILL.md")) or {}).get("description", "").strip("\"'")
    first = re.split(r"(?<=\.)\s", d, 1)[0]
    return (first[:157] + "...") if len(first) > 160 else first


def add_rows(notice, readme, name, desc):
    """The new skill's line in NOTICE.md's licence list and its row in the README's skills table."""
    lines = notice.split("\n"); idx = [i for i, l in enumerate(lines) if l.startswith("- `.claude/skills/")]
    if idx and ("`.claude/skills/%s/`" % name) not in notice:
        lines.insert(idx[-1] + 1, "- `.claude/skills/%s/`" % name); notice = "\n".join(lines)
    lines = readme.split("\n"); idx = [i for i, l in enumerate(lines) if l.startswith("| `.claude/skills/")]
    if idx and ("| `.claude/skills/%s/`" % name) not in readme:
        lines.insert(idx[-1] + 1, "| `.claude/skills/%s/` | %s |" % (name, desc.replace("|", "/"))); readme = "\n".join(lines)
    return notice, readme


def pr_text(name, desc, d, chk, login):
    verb = "Add" if d["new_skill"] else "Update"
    title = "%s the %s skill" % (verb, name)
    tests = chk.get("tests") and "pass (%s)" % chk["tests"] or "no scripts, so none needed"
    assets = [n for n in chk["notes"] if n.startswith("`")]
    body = "\n".join([
        "**What it does:** %s" % (desc or "(see SKILL.md)"), "",
        "Sent from Video maker's `share-skill` by @%s." % login if login else "Sent from Video maker's `share-skill`.", "",
        "### Files", ""] + ["- added `%s`" % f for f in d["added"]] + ["- changed `%s`" % f for f in d["changed"]] +
        ["- deleted `%s`" % f for f in d["deleted"]] +
        (["- NOTICE.md and README.md: one line each for the new skill"] if d["new_skill"] else []) + [
        "", "### Checklist", "",
        "- [x] Everything is inside `.claude/skills/%s/`" % name,
        "- [x] `SKILL.md` has a name and a description",
        "- [x] Tests: %s" % tests,
        "- [x] No videos, sounds, keys, Mac user names or company names (checked by `share.py check`)",
        "- [x] Images, fonts and other files from elsewhere: %s" % ("; ".join(assets) if assets else "none"),
        "- [x] Shared under the repo's MIT licence"])
    return title, body


def plan(root, name, gh=None, upstream=UPSTREAM, run_tests=True):
    tree = upstream_tree(gh, upstream)
    d = diff(root, name, tree)
    chk = check(root, name, run_tests=run_tests, only=set(d["added"] + d["changed"]))
    out = {"check": chk, "upstream": upstream, "diff": d}
    if not chk["ok"]:
        return out
    if not (d["added"] or d["changed"] or d["deleted"]):
        out["nothing_to_send"] = True; return out
    login = gh("user")["login"] if gh else None
    out["account"] = login
    if gh:
        out["fork"] = not gh("repos/" + upstream).get("permissions", {}).get("push", False)
    desc = describe(root, name)
    out["title"], out["body"] = pr_text(name, desc, d, chk, login)
    return out


def send(root, name, gh, upstream=UPSTREAM, wait=2.0):
    p = plan(root, name, gh, upstream)
    if not p["check"]["ok"]:
        raise SystemExit("Not sent: the check found things to fix first.\n" + "\n".join(p["check"]["blockers"]))
    if p.get("nothing_to_send"):
        raise SystemExit("Nothing to send: the repo already has this skill exactly as it is here.")
    d, login = p["diff"], p["account"]
    target = upstream
    if p["fork"]:
        target = gh("repos/%s/forks" % upstream, "POST", {"default_branch_only": True})["full_name"]
        for _ in range(30):
            if gh("repos/%s/git/ref/heads/%s" % (target, BRANCH), soft=True):
                break
            time.sleep(wait)
        gh("repos/%s/merge-upstream" % target, "POST", {"branch": BRANCH}, soft=True)   # bring an older fork up to date
    head = gh("repos/%s/git/ref/heads/%s" % (upstream, BRANCH))["object"]["sha"]
    base_tree = gh("repos/%s/git/commits/%s" % (upstream, head))["tree"]["sha"]
    entries = []
    for f in d["added"] + d["changed"]:
        full = os.path.join(root, f)
        blob = gh("repos/%s/git/blobs" % target, "POST",
                  {"content": base64.b64encode(read_bytes(full)).decode(), "encoding": "base64"})
        entries.append({"path": f, "mode": "100755" if os.access(full, os.X_OK) else "100644", "type": "blob", "sha": blob["sha"]})
    for f in d["deleted"]:
        entries.append({"path": f, "mode": "100644", "type": "blob", "sha": None})
    if d["new_skill"]:
        texts = {}
        for f in ("NOTICE.md", "README.md"):
            got = gh("repos/%s/contents/%s?ref=%s" % (upstream, f, head))
            texts[f] = base64.b64decode(got["content"]).decode("utf-8")
        notice, readme = add_rows(texts["NOTICE.md"], texts["README.md"], name, describe(root, name))
        for f, t in (("NOTICE.md", notice), ("README.md", readme)):
            if t != texts[f]:
                entries.append({"path": f, "mode": "100644", "type": "blob", "content": t})
    tree = gh("repos/%s/git/trees" % target, "POST", {"base_tree": base_tree, "tree": entries})["sha"]
    commit = gh("repos/%s/git/commits" % target, "POST", {"message": p["title"], "tree": tree, "parents": [head]})["sha"]
    branch = "skill/%s" % name
    for n in range(2, 50):
        if not gh("repos/%s/git/ref/heads/%s" % (target, branch), ok404=True):
            break
        branch = "skill/%s-%d" % (name, n)
    gh("repos/%s/git/refs" % target, "POST", {"ref": "refs/heads/" + branch, "sha": commit})
    pr = {"title": p["title"], "body": p["body"], "base": BRANCH,
          "head": ("%s:%s" % (login, branch)) if p["fork"] else branch}
    if p["fork"]:
        pr["maintainer_can_modify"] = True
    made = gh("repos/%s/pulls" % upstream, "POST", pr)
    return {"url": made.get("html_url"), "branch": branch, "repo": target, "files": len(entries)}


def list_skills(root, gh=None, upstream=UPSTREAM):
    tree = upstream_tree(gh, upstream); out = []
    for name in sorted(os.listdir(os.path.join(root, ".claude", "skills"))):
        if not os.path.isdir(os.path.join(root, ".claude", "skills", name)):
            continue
        if name.startswith("style-"):
            out.append({"skill": name, "status": "private (a style learned from reference videos)"}); continue
        d = diff(root, name, tree)
        status = "new" if d["new_skill"] else ("changed (%d files)" % (len(d["added"]) + len(d["changed"]) + len(d["deleted"]))
                                               if d["added"] or d["changed"] or d["deleted"] else "same as the repo")
        out.append({"skill": name, "status": status})
    return out


def logged_in_gh(root):
    exe = gh_path(root)
    if not exe:
        return None
    return GH(exe) if subprocess.run([exe, "auth", "status"], capture_output=True).returncode == 0 else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["list", "check", "plan", "send"])
    ap.add_argument("skill", nargs="?")
    ap.add_argument("--no-tests", action="store_true")
    ap.add_argument("--since", help="check: only files added or changed since this git ref (the GitHub test run)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--yes", action="store_true", help="send: the person said yes to the plan in the chat")
    ap.add_argument("--upstream", default=UPSTREAM)
    ap.add_argument("--root", default=ROOT)
    a = ap.parse_args()
    if a.cmd != "list" and not a.skill:
        ap.error("name the skill folder, e.g. share.py %s my-skill" % a.cmd)
    if a.cmd == "check":
        only = None
        if a.since:
            g = subprocess.run(["git", "diff", "--name-only", "--diff-filter=AM", a.since + "...HEAD", "--",
                                ".claude/skills/%s/" % a.skill], cwd=a.root, capture_output=True, text=True, check=True)
            only = set(g.stdout.split("\n")) - {""}
        r = check(a.root, a.skill, run_tests=not a.no_tests, only=only)
        if a.json:
            print(json.dumps(r, indent=1))
        else:
            print("%s: %s" % (a.skill, "ready to share" if r["ok"] else "fix these first"))
            for k, label in (("blockers", "  ✗ "), ("confirm", "  ? "), ("notes", "  ✓ ")):
                for line in r[k]:
                    print(label + line)
        raise SystemExit(0 if r["ok"] else 1)
    gh = logged_in_gh(a.root)
    if a.cmd == "list":
        print(json.dumps(list_skills(a.root, gh, a.upstream), indent=1)); return
    if a.cmd == "plan":
        print(json.dumps(plan(a.root, a.skill, gh, a.upstream, run_tests=not a.no_tests), indent=1)); return
    if not a.yes:
        raise SystemExit("send needs --yes: show the plan in the chat and get a yes first.")
    if gh is None:
        raise SystemExit("GitHub isn't signed in here yet: follow 'Sign in to GitHub' in SKILL.md.")
    print(json.dumps(send(a.root, a.skill, gh, a.upstream), indent=1))


if __name__ == "__main__":
    main()
