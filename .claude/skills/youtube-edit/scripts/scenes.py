#!/usr/bin/env python3
"""scenes.py: the creator's scene cards (written on the upload page) -> anchored moments -> a checked scene plan with stills.

  python3 scenes.py anchor --project W [--json]     where each card's "when" is said in W/transcript.json
  python3 scenes.py snap --project W [--no-snap]    check W/scene-plan.json against the cards and storyboard, take a still
                                                    of every scene, write the still paths back (the page shows them)

W/scenes.json (the page writes it): [{"id": "s1", "when": "when I say pricing", "what": "our pricing page in a browser,
scroll to Pro and circle it", "files": ["img/pricing.png"], "edited": "<iso>"}]

W/scene-plan.json (Claude writes it, then runs `snap`):
{"scenes": [{"note": "s1", "status": "planned|custom|needs-info|built", "build": "what will be on screen, in plain words",
             "format": "3D floating browser (4c)", "in": 12.4, "out": 16.0, "anchor": "pricing",
             "snap_at": [13.4, 15.2], "question": "", "conflict": ""}]}
Every planned / custom / built scene needs a time and at least one storyboard beat with "note": "<id>" (or "raw": true when
it lives in raw_html). "snap_at" is optional: by default one still 1 s after "in" (capped at the scene's middle).
"""
import argparse, datetime, glob, json, os, re, shutil, subprocess, sys

STATUSES = ("planned", "custom", "needs-info", "built")
QUOTED = r'"([^"]{2,})"|“([^”]{2,})”|«([^»]{2,})»|‘([^’]{2,})’'   # real quote pairs only: an apostrophe is not a quote


def load(p, default=None):
    try:
        return json.load(open(p))
    except (OSError, ValueError):
        return default


def norm(s):
    """Lower-case words without punctuation, light stemming so "costs" finds "cost" and "it's" finds "it's"."""
    out = []
    for w in re.sub(r"[^a-z0-9' ]", " ", s.lower().replace("’", "'")).split():
        w = w.strip("'")
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        if len(w) > 5 and w.endswith("ing"):
            w = w[:-3]
        out.append(w)
    return out


def words(project):
    t = load(os.path.join(project, "transcript.json"))
    if t is None:
        return None
    t = t["words"] if isinstance(t, dict) else t
    out = []
    for w in t:
        toks = norm(w["text"])
        out.append((toks[0] if toks else "", float(w["start"]), float(w["end"])))
    return out


def phrase_of(when):
    """The words to look for: quoted text first, then what follows say / says / mention / talk about, else all of it."""
    q = [g for m in re.findall(QUOTED, when) for g in m if g]
    if q:
        return max(q, key=len).strip()
    m = re.search(r"\b(?:says?|said|saying|mentions?|mentioning|talks? about|talking about|gets? to|reaches|hear)\b\s+(.+)", when, re.I)
    if m:
        return m.group(1).strip(" .,:;!?")
    return re.sub(r"^\s*(?:when|at|during|after|before)\b\s*", "", when, flags=re.I).strip(" .,:;!?")


def find(toks, phrase):
    """Exact hits of the phrase as (start, end); else the best fuzzy window (share of phrase words present, >= 0.6)."""
    p = norm(phrase)
    if not p or not toks:
        return [], None
    hits = []
    for i in range(len(toks) - len(p) + 1):
        if all(toks[i + k][0] == p[k] for k in range(len(p))):
            hits.append((toks[i][1], toks[i + len(p) - 1][2]))
    if hits:
        return hits, None
    best, key = None, (0.0, 0.0)
    n, want = len(p), set(p)
    for i in range(len(toks)):
        if toks[i][0] not in want:          # a window starts on a phrase word, so the moment is the phrase, not before it
            continue
        win = toks[i:i + n + 2]
        idx = [k for k, t in enumerate(win) if t[0] in want]
        got = len(set(win[k][0] for k in idx) & want)
        span = (win[idx[0]][1], win[idx[-1]][2])
        k = (got / float(n), -(span[1] - span[0]))   # most phrase words first, then the tightest span
        if k > key:
            best, key = span, k
    return ([], (best, round(key[0], 2))) if key[0] >= 0.6 else ([], None)


def timecode(when):
    m = re.search(r"\b(\d{1,2}):(\d{2}(?:\.\d+)?)\b", when)
    return int(m.group(1)) * 60 + float(m.group(2)) if m else None


def cmd_anchor(a):
    scenes = load(os.path.join(a.project, "scenes.json"), [])
    toks = words(a.project)
    if not scenes:
        print("no scene cards in %s/scenes.json" % a.project)
        return
    if toks is None:
        print("note: no transcript.json yet: anchor after the cut (or the voiceover), when the words have times")
    rows = []
    for s in scenes:
        when = (s.get("when") or "").strip()
        tc = timecode(when)
        ph = phrase_of(when) if when else ""
        hits, fuzzy = find(toks or [], ph) if ph else ([], None)
        rows.append({"id": s["id"], "when": when, "phrase": ph, "timecode": tc,
                     "hits": [[round(x, 2), round(y, 2)] for x, y in hits], "fuzzy": fuzzy,
                     "what": s.get("what", ""), "files": s.get("files", [])})
    if a.json:
        print(json.dumps(rows, indent=1))
        return
    for r in rows:
        print("%s  when: %s" % (r["id"], r["when"] or "(not given: place it where the 'what' fits)"))
        print("    what: %s" % (r["what"] or "(empty: ask)"))
        if r["files"]:
            print("    files: %s" % ", ".join(r["files"]))
        if r["timecode"] is not None:
            print("    at %.2f s (timecode in the note)" % r["timecode"])
        elif r["hits"]:
            print("    \"%s\" said at %s" % (r["phrase"], "   ".join("%.2f-%.2f" % tuple(h) for h in r["hits"][:4])))
        elif r["fuzzy"]:
            print("    \"%s\" not said exactly; closest %.2f-%.2f (%.0f%% of the words): confirm" % (r["phrase"], r["fuzzy"][0][0], r["fuzzy"][0][1], r["fuzzy"][1] * 100))
        elif r["phrase"] and toks is not None:
            print("    \"%s\" NOT FOUND in the transcript: ask, or place it by meaning" % r["phrase"])


def snapshots(project, jobs):
    """jobs: [(t, dst)]. ONE snapshot run for all of them (one Chrome); returns the dsts written."""
    if not jobs:
        return set()
    pub = os.path.join(project, "public")
    env = dict(os.environ, PRODUCER_BROWSER_GPU_MODE="hardware")
    subprocess.run(["npx", "hyperframes", "snapshot", pub, "--no-end", "--at", ",".join("%.2f" % t for t, _ in jobs)], env=env, capture_output=True)
    c = sorted(glob.glob(os.path.join(pub, "snapshots", "frame-*-at-*.png")), key=lambda f: int(os.path.basename(f).split("-")[1]))
    done = set()
    for (t, dst), src in zip(jobs, c):
        shutil.copy(src, dst); done.add(dst)
    return done


def cmd_snap(a):
    P = a.project
    scenes = load(os.path.join(P, "scenes.json"), [])
    plan = load(os.path.join(P, "scene-plan.json"))
    if plan is None:
        sys.exit("no %s/scene-plan.json: write it first (see this script's docstring)" % P)
    sb = load(os.path.join(P, "storyboard.json"), {})
    dur = float(sb.get("duration", 0) or 0)
    tagged = {}
    for b in sb.get("beats", []):
        if b.get("note"):
            tagged.setdefault(b["note"], []).append(b.get("id", "?"))
    rows = {r.get("note"): r for r in plan.get("scenes", [])}
    errors, warns = [], []
    for s in scenes:
        if s["id"] not in rows:
            errors.append("%s has no row in the plan" % s["id"])
    for nid, r in rows.items():
        st = r.get("status")
        if st not in STATUSES:
            errors.append("%s: status %r (use %s)" % (nid, st, " | ".join(STATUSES)))
            continue
        if nid not in {s["id"] for s in scenes}:
            warns.append("%s is in the plan but no longer on the page (the card was removed)" % nid)
        if st == "needs-info":
            if not r.get("question"):
                errors.append("%s: needs-info without a question for the creator" % nid)
            continue
        if not isinstance(r.get("in"), (int, float)) or not isinstance(r.get("out"), (int, float)) or r["out"] <= r["in"]:
            errors.append("%s: needs numeric in < out" % nid)
            continue
        if dur and (r["in"] < 0 or r["out"] > dur + 0.05):
            errors.append("%s: %.2f-%.2f is outside the video (0-%.2f)" % (nid, r["in"], r["out"], dur))
        if not r.get("build"):
            errors.append("%s: say what will be on screen in \"build\"" % nid)
        if nid not in tagged and not r.get("raw"):
            warns.append("%s: no storyboard beat carries \"note\": \"%s\" (fine only before compose, or set \"raw\": true)" % (nid, nid))
    for e in errors:
        print("ERROR", e)
    for w in warns:
        print("warn ", w)
    if errors:
        sys.exit(1)
    snapdir = os.path.join(P, "snaps")
    os.makedirs(snapdir, exist_ok=True)
    for old in glob.glob(os.path.join(snapdir, "scene-*.png")):
        os.remove(old)
    jobs, wanted = [], {}
    for nid, r in rows.items():
        r.pop("snaps", None)
        if r.get("status") == "needs-info" or a.no_snap:
            continue
        ats = r.get("snap_at") or [min(r["in"] + 1.0, (r["in"] + r["out"]) / 2.0)]
        ats = [ats] if isinstance(ats, (int, float)) else ats
        for k, t in enumerate(ats, 1):
            t = max(0.0, min(float(t), (dur or float(t) + 1) - 0.05))
            dst = os.path.join(snapdir, "scene-%s-%d.png" % (nid, k))
            jobs.append((t, dst)); wanted.setdefault(nid, []).append(dst)
    done = snapshots(P, jobs)
    for nid, r in rows.items():
        got = ["snaps/" + os.path.basename(d) for d in wanted.get(nid, []) if d in done]
        if wanted.get(nid):
            r["snaps"] = got
        print("%s  %-10s %s  %s" % (nid, r.get("status"), ", ".join(got) or "(no still)", r.get("build", "")[:60]))
    plan["updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    json.dump(plan, open(os.path.join(P, "scene-plan.json"), "w"), indent=2)
    print("plan checked: %d scenes, %d tagged beats; the upload page shows it under each card" % (len(rows), sum(map(len, tagged.values()))))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    an = sub.add_parser("anchor"); an.add_argument("--project", required=True); an.add_argument("--json", action="store_true")
    sn = sub.add_parser("snap"); sn.add_argument("--project", required=True); sn.add_argument("--no-snap", action="store_true")
    a = ap.parse_args()
    {"anchor": cmd_anchor, "snap": cmd_snap}[a.cmd](a)


if __name__ == "__main__":
    main()
