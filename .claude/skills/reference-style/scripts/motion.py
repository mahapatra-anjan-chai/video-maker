#!/usr/bin/env python3
"""How things move in a video, measured at its full frame rate: every move's start, length, kind (slide, pan, zoom,
fade, reveal), direction and ease (the GSAP ease that fits best and its family), where its speed peaks, overshoot,
staggers, how soon after a cut things start moving, how long things hold, and whether cuts and moves land on the beat.

  python3 motion.py --video V --out DIR [--start S --end E] [--width 256]

Writes motion.json, MOTION.md and curves.png (each move's measured progress with the fitted ease drawn over it).
style-scan.py runs it on every reference. numpy only.

What it tells apart reliably: the family (linear, in, out, inOut, overshoot, elastic) and the length to a frame or two.
A GSAP name (power3.out, expo.out, ...) only for moves of 10 frames or more: shorter, those curves look alike. Frame-by-
frame repeats (animation on twos, 24 fps in a 30 fps file) are dropped before speeds are measured. Footage that moves
by itself (people, screen recordings playing) shows as unstructured motion and stays out of the ease counts.
"""
import argparse, json, math, os, subprocess, sys

import numpy as np

CELL = 8                       # activity grid, in analysis pixels


# ---- eases (GSAP's definitions) ----------------------------------------------------------------------------------
def _pin(p): return lambda u: u ** (p + 1)
def _pout(p): return lambda u: 1 - (1 - u) ** (p + 1)
def _pio(p): return lambda u: np.where(u < 0.5, (2 * u) ** (p + 1) / 2, 1 - (2 * (1 - u)) ** (p + 1) / 2)
def _back_out(c): return lambda u: 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2
def _back_in(c): return lambda u: (c + 1) * u ** 3 - c * u ** 2


EASES = {"none": (lambda u: u, "linear")}
for _p in (1, 2, 3, 4):
    EASES["power%d.in" % _p] = (_pin(_p), "in"); EASES["power%d.out" % _p] = (_pout(_p), "out")
    EASES["power%d.inOut" % _p] = (_pio(_p), "inOut")
EASES.update({
    "sine.in": (lambda u: 1 - np.cos(u * np.pi / 2), "in"), "sine.out": (lambda u: np.sin(u * np.pi / 2), "out"),
    "sine.inOut": (lambda u: -(np.cos(np.pi * u) - 1) / 2, "inOut"),
    "expo.in": (lambda u: np.where(u <= 0, 0.0, 2.0 ** (10 * u - 10)), "in"),
    "expo.out": (lambda u: np.where(u >= 1, 1.0, 1 - 2.0 ** (-10 * u)), "out"),
    "expo.inOut": (lambda u: np.where(u < 0.5, 2.0 ** (20 * u - 10) / 2, (2 - 2.0 ** (-20 * u + 10)) / 2), "inOut"),
    "circ.in": (lambda u: 1 - np.sqrt(np.clip(1 - u * u, 0, 1)), "in"),
    "circ.out": (lambda u: np.sqrt(np.clip(1 - (u - 1) ** 2, 0, 1)), "out"),
    "back.in(1.7)": (_back_in(1.70158), "in"),
    "back.out(1.7)": (_back_out(1.70158), "overshoot"), "back.out(2.5)": (_back_out(2.5), "overshoot"),
    "elastic.out(1,0.3)": (lambda u: np.where(u >= 1, 1.0, 1 + 2.0 ** (-10 * u) * np.sin((u - 0.075) * 2 * np.pi / 0.3)), "elastic"),
})
SHORT = ["none", "power2.in", "power2.out", "power2.inOut", "back.out(1.7)"]     # stand-ins for each family


PREFER = ["power", "sine", "none", "expo", "circ", "back", "elastic"]          # simpler first, on a near tie


def _rms(f, t, p, g0, gd):
    U = np.clip((t[None, :] - g0[:, None]) / gd[:, None], 0, 1)
    F = f(U)
    lo, hi = F[:, :1], F[:, -1:]
    ok = (lo[:, 0] <= 0.05) & (hi[:, 0] >= 0.95)
    rms = np.sqrt((((F - lo) / np.maximum(hi - lo, 1e-6) - p[None, :]) ** 2).mean(axis=1))
    rms[~ok] = np.inf
    return rms


def fit_ease(t, p, overshoot_ok=True, names=None):
    """Best ease for progress p (0 at the frame before the move, 1 at the frame it settles) at times t.
    The tween's own start and length are fitted too, since slow ends sit below what pixels show. On a near tie the
    shorter, simpler ease wins: it reproduces the same look."""
    t = np.asarray(t, float); p = np.asarray(p, float)
    vis = t[-1] - t[0]
    if vis <= 0 or len(t) < 3:
        return None
    lo0, hi0 = t[0] - 0.5 * vis, t[1]
    T0 = np.linspace(lo0, hi0, 14); DD = vis * np.linspace(0.6, 2.4, 28)
    st0, std = T0[1] - T0[0], DD[1] - DD[0]
    g0, gd = [x.ravel() for x in np.meshgrid(T0, DD, indexing="ij")]
    keep = g0 + gd >= t[-2] - 1e-6
    g0, gd = g0[keep], gd[keep]
    res = []
    for name in names or EASES:
        f, fam = EASES[name]
        if fam in ("overshoot", "elastic") and not overshoot_ok:
            continue
        rms = _rms(f, t, p, g0, gd)
        i = int(np.argmin(rms))
        if not np.isfinite(rms[i]):
            continue
        a0, ad = np.meshgrid(np.linspace(g0[i] - st0, g0[i] + st0, 9), np.linspace(gd[i] - std, gd[i] + std, 9), indexing="ij")
        a0, ad = a0.ravel(), np.maximum(ad.ravel(), 1e-3)
        ok = (a0 >= lo0 - st0) & (a0 <= hi0) & (a0 + ad >= t[-2] - 1e-6)
        r2 = _rms(f, t, p, a0[ok], ad[ok])
        j = int(np.argmin(r2)) if ok.any() else None
        if j is not None and r2[j] < rms[i]:
            res.append((float(r2[j]), name, fam, float(a0[ok][j]), float(ad[ok][j])))
        else:
            res.append((float(rms[i]), name, fam, float(g0[i]), float(gd[i])))
    if not res:
        return None
    best = min(r[0] for r in res)
    near = [r for r in res if r[0] <= best + max(0.004, 0.25 * best)]
    rank = lambda r: (round(r[4] / max(vis, 1e-6), 1), next(k for k, x in enumerate(PREFER) if r[1].startswith(x)), r[0])
    r = min(near, key=rank)
    return {"ease": r[1], "family": r[2], "rms": r[0], "start": r[3], "dur": r[4]}


# ---- video in ------------------------------------------------------------------------------------------------------
def probe(video):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                   "stream=codec_type,width,height,avg_frame_rate,r_frame_rate:format=duration",
                                   "-of", "json", video], capture_output=True, text=True, check=True).stdout)
    v = [s for s in j["streams"] if s["codec_type"] == "video"][0]
    rate = v.get("avg_frame_rate") if v.get("avg_frame_rate", "0/0") != "0/0" else v["r_frame_rate"]
    n, d = rate.split("/")
    return {"w": v["width"], "h": v["height"], "fps": float(n) / float(d), "duration": float(j["format"]["duration"]),
            "audio": any(s["codec_type"] == "audio" for s in j["streams"])}


def decode(video, width, start=None, end=None, max_fps=60):
    info = probe(video)
    W = int(width); H = max(16, int(round(info["h"] * W / info["w"] / 2)) * 2)
    fps = info["fps"]
    vf = "scale=%d:%d:flags=area,format=gray" % (W, H)
    if fps > max_fps + 0.5:
        vf = "fps=%d," % max_fps + vf; fps = float(max_fps)
    cmd = ["ffmpeg", "-v", "error"]
    if start:
        cmd += ["-ss", "%.3f" % start]
    cmd += ["-i", video]
    if end:
        cmd += ["-t", "%.3f" % (end - (start or 0))]
    cmd += ["-vf", vf, "-fps_mode", "passthrough", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, H, W)
    times = None
    if not start and not end and fps == info["fps"]:     # the real presentation times, when they line up
        pts = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time",
                              "-of", "csv=p=0", video], capture_output=True, text=True).stdout.split()
        try:
            pts = sorted(float(x) for x in pts if x not in ("N/A", ""))
            if len(pts) == len(frames):
                times = np.array(pts) - pts[0]
        except ValueError:
            times = None
    if times is None:
        times = (start or 0) + np.arange(len(frames)) / fps
    return frames, times, fps, info


# ---- the measurements ----------------------------------------------------------------------------------------------
def phase_shift(a, b, win):
    """(dy, dx): how far b's content sits from a's, to a fraction of a pixel; and the peak's height."""
    A = np.fft.fft2((a - a.mean()) * win); B = np.fft.fft2((b - b.mean()) * win)
    R = np.conj(A) * B
    R /= np.abs(R) + 1e-3 * np.abs(R).max() + 1e-9
    r = np.real(np.fft.ifft2(R))
    iy, ix = np.unravel_index(int(np.argmax(r)), r.shape)
    def sub(c, n, get):
        l, m, rr = get((c - 1) % n), get(c), get((c + 1) % n)
        den = l - 2 * m + rr
        return c + (0.5 * (l - rr) / den if den < -1e-9 else 0.0)
    dy = sub(iy, r.shape[0], lambda k: r[k, ix]); dx = sub(ix, r.shape[1], lambda k: r[iy, k])
    if dy > r.shape[0] / 2: dy -= r.shape[0]
    if dx > r.shape[1] / 2: dx -= r.shape[1]
    return dy, dx, float(r[iy, ix])


def bilinear(img, y, x):
    h, w = img.shape
    x = np.clip(x, 0, w - 1.001); y = np.clip(y, 0, h - 1.001)
    x0 = x.astype(int); y0 = y.astype(int); fx = x - x0; fy = y - y0
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy) +
            img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)


def scale_between(a, b, grid=np.exp(np.linspace(np.log(0.94), np.log(1.06), 25))):
    """s such that b looks like a zoomed by s about the centre (s > 1: pushing in)."""
    h, w = a.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx = (h - 1) / 2, (w - 1) / 2
    m = (np.abs(yy - cy) < h * 0.3) & (np.abs(xx - cx) < w * 0.3)
    errs = []
    for s in grid:
        z = bilinear(a, cy + (yy[m] - cy) / s, cx + (xx[m] - cx) / s)
        errs.append(float(((z - b[m]) ** 2).mean()))
    i = int(np.argmin(errs)); ls = np.log(grid)
    if 0 < i < len(grid) - 1:
        l, c, r = errs[i - 1], errs[i], errs[i + 1]
        den = l - 2 * c + r
        off = 0.5 * (l - r) / den if den > 1e-9 else 0.0
        return float(np.exp(ls[i] + off * (ls[1] - ls[0]))), errs[len(grid) // 2], c
    return float(grid[i]), errs[len(grid) // 2], errs[i]


def components(mask):
    """8-connected regions of a small boolean grid."""
    lab = np.zeros(mask.shape, int); n = 0
    for y, x in zip(*np.nonzero(mask)):
        if lab[y, x]:
            continue
        n += 1; stack = [(y, x)]; lab[y, x] = n
        while stack:
            cy, cx = stack.pop()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = cy + dy, cx + dx
                    if 0 <= yy < mask.shape[0] and 0 <= xx < mask.shape[1] and mask[yy, xx] and not lab[yy, xx]:
                        lab[yy, xx] = n; stack.append((yy, xx))
    return [lab == k for k in range(1, n + 1)]


def repeats(steps):
    """Indexes (into steps) of repeated frames: a near-still step between two real ones."""
    return {k for k in range(1, len(steps) - 1)
            if steps[k] < 0.2 * min(steps[k - 1], steps[k + 1]) and steps[k] < 1.0}


def finish(base, t, p, overshoot_ok, straight=1.0):
    """Fit the ease and fill in family, length, overshoot and where the speed peaks."""
    m = dict(base); p = np.asarray(p, float)
    fit = fit_ease(t, p, overshoot_ok, None if len(t) >= 11 else SHORT) if len(t) >= 5 else None
    vel = np.abs(np.diff(p)) / np.maximum(np.diff(t), 1e-6)
    peak = float((t[1:][int(np.argmax(vel))] - (t[0] + t[1]) / 2) / max(t[-1] - t[0], 1e-6)) if len(vel) else None
    over = bool(overshoot_ok and len(p) >= 5 and p.max() > 1.04 and p.argmax() < len(p) - 1)
    rev = 0
    if overshoot_ok and len(p) > 3:
        dv = np.diff(p); sgn = np.sign(dv[np.abs(dv) > 0.02])
        rev = int((np.diff(sgn) != 0).sum())
    if fit:
        good = fit["rms"] < 0.09
        m["dur"] = round(fit["dur"], 3)
        m["family"] = fit["family"] if good else "unclear"
        m["ease"] = fit["ease"] if good and len(t) >= 11 else None
        m["fit_rms"] = round(fit["rms"], 3)
        if rev >= 2 and over:
            m["family"] = "elastic"
        elif over and m["family"] in ("out", "inOut"):
            m["family"] = "overshoot"
    else:
        m["dur"] = m["visible"]; m["family"] = "too short" if len(t) < 5 else "unclear"; m["ease"] = None
    m["overshoot"] = over
    m["peak_at"] = round(peak, 2) if peak is not None and len(t) >= 5 else None
    if m["kind"] in ("slide", "pan") and (straight < 0.8 or m["family"] == "unclear") and m["visible"] > 1.5:
        m["kind"] = "footage"                                     # wandering, unfittable motion: content, not design
    m["_t"] = [round(float(x - t[0]), 4) for x in t]; m["_p"] = [round(float(x), 4) for x in p]
    if fit:
        m["_fit"] = [fit["ease"], round(fit["start"] - float(t[0]), 4), round(fit["dur"], 4)]
    return m


def camera_track(frames, times, cuts, shot_of, share):
    """Moves of the whole frame (pans, zooms, whips): four quarters of the frame shifting together, read as a
    translation plus a zoom, with the frame's outer edge changing too (a recording scrolling inside a phone leaves the
    edge still: not a camera move). Back-to-back moves split where the speed dips or zoom turns into travel."""
    N, H, W = frames.shape
    h2, w2 = H // 2, W // 2
    win = np.outer(np.hanning(h2), np.hanning(w2)).astype(np.float32) + 1e-3
    q = [(0, 0), (0, w2), (h2, 0), (h2, w2)]                  # TL, TR, BL, BR
    tx, ty, ls, ok, weak = np.zeros(N), np.zeros(N), np.zeros(N), np.zeros(N, bool), np.zeros(N, bool)
    step = np.zeros(N)
    cutset = set(cuts)
    for i in range(1, N):
        if i in cutset:
            continue
        a = frames[i - 1].astype(np.float32); b = frames[i].astype(np.float32)
        step[i] = np.abs(a - b).mean()
        if step[i] < 0.4:
            continue
        r = [phase_shift(a[y:y + h2, x:x + w2], b[y:y + h2, x:x + w2], win) for y, x in q]
        dy = np.array([v[0] for v in r]); dx = np.array([v[1] for v in r]); pk = min(v[2] for v in r)
        div = (((dx[1] + dx[3]) - (dx[0] + dx[2])) / 2 / w2 + ((dy[2] + dy[3]) - (dy[0] + dy[1])) / 2 / h2) / 2
        mx, my = dx.mean(), dy.mean()
        pred_x = mx + div * np.array([-w2, w2, -w2, w2]) / 2; pred_y = my + div * np.array([-h2, -h2, h2, h2]) / 2
        resid = float(np.max(np.hypot(dx - pred_x, dy - pred_y)))
        if pk > 0.004 and resid < 1.5 + 0.15 * np.hypot(mx, my) and share[i] > 0.02:
            tx[i], ty[i], ls[i] = mx, my, div
            ok[i] = np.hypot(mx, my) > 0.35 or abs(div) > 0.002
            weak[i] = np.hypot(mx, my) > 0.08 or abs(div) > 0.0004
    moves, used = [], np.zeros(N, bool)
    i = 1
    while i < N:
        if not ok[i]:
            i += 1; continue
        j = i
        while j + 1 < N and (j + 1) not in cutset and (ok[j + 1] or (j + 2 < N and ok[j + 2] and (j + 2) not in cutset)):
            j += 1
        while not ok[j]:
            j -= 1
        if j - i + 1 >= 4:                        # stretch out over the slow ends, while it keeps the same way
            dirv = np.array([ty[i:j + 1].sum(), tx[i:j + 1].sum()]); dl = ls[i:j + 1].sum()
            same = lambda k: weak[k] and k not in cutset and (np.dot([ty[k], tx[k]], dirv) > 0 or ls[k] * dl > 0)
            while i - 1 >= 1 and same(i - 1):
                i -= 1
            while j + 1 < N and same(j + 1):
                j += 1
            for (si, sj) in split_at_dips(tx, ty, ls, i, j, W):
                mv = camera_move(times, tx, ty, ls, step, si, sj, shot_of, W)
                if mv:
                    moves.append(mv)
                    if mv["kind"] != "footage":
                        used[si - 1:sj + 1] = True
        i = j + 1
    return moves, used


def split_at_dips(tx, ty, ls, i, j, W):
    v = np.hypot(tx[i:j + 1], ty[i:j + 1]) / (W / 2) + np.abs(ls[i:j + 1])
    v = np.convolve(v, np.ones(3) / 3, mode="same")
    cuts_, k = [], 2
    while k < len(v) - 2:
        if v[k] <= v[k - 1] and v[k] <= v[k + 1] and v[k] < 0.2 * min(v[:k].max(), v[k:].max()):
            cuts_.append(k); k += 3
        else:
            k += 1
    z = np.abs(ls[i:j + 1]) > np.hypot(tx[i:j + 1], ty[i:j + 1]) / (W / 2)      # zooming more than travelling
    z = np.convolve(z.astype(float), np.ones(7) / 7, mode="same") > 0.5
    for k in range(6, len(z) - 6):
        if z[k] != z[k - 1] and z[k - 6:k].all() == z[k - 1] and (z[k:k + 6] == z[k]).all() and (z[k - 6:k] == z[k - 1]).all():
            if all(abs(k - c) > 3 for c in cuts_):
                cuts_.append(k)
    edges = [0] + sorted(cuts_) + [len(v)]
    return [(i + a, i + b - 1) for a, b in zip(edges[:-1], edges[1:]) if b - a >= 4]


def camera_move(times, tx, ty, ls, step, i, j, shot_of, W):
    """One camera move between frames i and j: a zoom when the scale change outweighs the travel, else a pan."""
    idx = list(range(i - 1, j + 1))
    rep = repeats(step[i:j + 1])
    keep = [idx[0]] + [x for k, x in enumerate(idx[1:]) if k not in rep]
    t = np.array([times[x] for x in keep])
    X = np.cumsum([[ty[x], tx[x]] if x != idx[0] else [0.0, 0.0] for x in keep], axis=0)
    L = np.cumsum([ls[x] if x != idx[0] else 0.0 for x in keep])
    dist = float(np.hypot(*X[-1])); path = float(sum(np.hypot(ty[x], tx[x]) for x in keep[1:]))
    base = {"start": round(float(times[i - 1]), 3), "end": round(float(times[j]), 3),
            "visible": round(float(times[j] - times[i - 1]), 3), "frames": len(keep) - 1,
            "repeats_dropped": len(idx) - len(keep), "box": [0.0, 0.0, 1.0, 1.0],
            "after_cut": round(float(times[i - 1] - times[shot_of[i]]), 3) if shot_of[i] > 0 else None}
    steps_ = np.array([ls[x] for x in keep[1:]])
    steady = (np.sign(steps_) == np.sign(L[-1])).mean() if len(steps_) else 0     # a zoom keeps one direction
    if abs(L[-1]) > 0.04 and steady >= 0.7 and abs(L[-1]) > 1.0 * dist / W:
        base.update(kind="zoom", scale=round(float(math.exp(L[-1])), 3))
        return finish(base, t, L / L[-1], True)
    if dist >= 3.0:
        u = X[-1] / dist; dyv, dxv = float(X[-1][0]), float(X[-1][1])
        base.update(kind="pan", distance=round(dist / W, 3),
                    direction=("right" if dxv > 0 else "left") if abs(dxv) >= abs(dyv) else ("down" if dyv > 0 else "up"))
        return finish(base, t, (X @ u) / dist, True, dist / path if path > 0 else 0)
    return None


def stagger_of(els, staggers):
    st = sorted(e["start"] for e in els)
    gaps = np.diff(st)
    if len(st) >= 3 and gaps.min() > 0 and gaps.std() / gaps.mean() < 0.4:
        kinds = [e["kind"] for e in els]
        staggers.append({"t": round(st[0], 3), "count": len(st), "every": round(float(np.median(gaps)), 3),
                         "kind": max(set(kinds), key=kinds.count)})
        return True
    return False


def blobs(el, moving, runs):
    """Space-time pieces of motion: each frame's active regions, linked to the next frames' where they overlap.
    Things moving at different times stay apart even in the same run; things touching while they move join."""
    out = []
    for (a, b, shot0) in runs:
        still = 1 - moving[a:b + 1].mean()
        cadence = 3 if still > 0.6 else 2 if still > 0.35 else 1         # animation drawn on twos or threes
        parts, parent = [], []
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]; x = parent[x]
            return x
        prev = []                                  # (frame, part index) of the last few frames
        for i in range(a, b + 1):
            if not el[i].any():
                continue
            cur = []
            for c in components(el[i]):
                n = len(parts); parts.append((i, c)); parent.append(n); cur.append(n)
                grow = c.copy(); grow[1:] |= c[:-1]; grow[:-1] |= c[1:]; grow[:, 1:] |= grow[:, :-1].copy(); grow[:, :-1] |= grow[:, 1:].copy()
                for (fi, pj) in prev:
                    if i - fi <= cadence + 1 and (parts[pj][1] & grow).any():
                        parent[find(n)] = find(pj)
            prev = [(fi, pj) for (fi, pj) in prev if i - fi <= cadence] + [(i, n) for n in cur]
        groups = {}
        for n in range(len(parts)):
            groups.setdefault(find(n), []).append(n)
        for g in groups.values():
            fr = [parts[n][0] for n in g]
            cells = np.zeros_like(parts[g[0]][1])
            for n in g:
                cells |= parts[n][1]
            if cells.sum() >= 2:
                out.append({"a": min(fr), "b": max(fr), "cells": cells, "shot0": shot0, "cadence": cadence})
    return out


def cut_rhythm(cut_times):
    """Stretches of four or more cuts at a steady interval (montages cut to music): from the picture alone."""
    out, k = [], 0
    while k < len(cut_times) - 3:
        e = k + 1
        while e + 1 < len(cut_times):
            g = np.diff(cut_times[k:e + 2])
            if g.min() < 0.2 or g.std() / g.mean() > 0.12:
                break
            e += 1
        if e - k >= 3:
            g = np.diff(cut_times[k:e + 1])
            out.append({"from": round(cut_times[k], 2), "to": round(cut_times[e], 2), "cuts": e - k + 1,
                        "every": round(float(np.median(g)), 3)})
            k = e
        else:
            k += 1
    return out


def analyse(video, width=256, start=None, end=None, beats=True, bpm=None):
    frames, times, fps, info = decode(video, width, start, end)
    N, H, W = frames.shape
    f32 = lambda i: frames[i].astype(np.float32)
    gh, gw = H // CELL, W // CELL
    d = np.zeros(N); cellchg = np.zeros((N, gh, gw), np.float32)
    for i in range(1, N):
        diff = np.abs(f32(i) - f32(i - 1))
        d[i] = diff.mean()
        cellchg[i] = diff[:gh * CELL, :gw * CELL].reshape(gh, CELL, gw, CELL).mean(axis=(1, 3))
    cuts = []                                     # a change far above its neighbours; one cut per 3 frames at most
    for i in range(1, N):
        nb = np.r_[d[max(1, i - 4):i], d[i + 1:i + 5]]
        if d[i] > 18 and d[i] > 3.5 * (np.median(nb) if len(nb) else 0) + 2 and (not cuts or i - cuts[-1] > 2):
            cuts.append(i)
    shot_of = np.zeros(N, int)
    for c in cuts:
        shot_of[c:] = c
    noise = float(np.percentile(cellchg[1:], 50)) if N > 1 else 0.0
    active = cellchg > max(1.2, 3.0 * noise)
    for c in cuts:
        active[c] = False
    # footage: cells changing most of a 3 s window (video playing inside the frame, people moving)
    w = max(3, int(round(3 * fps)))
    cs = np.concatenate([np.zeros((1, gh, gw), np.float32), np.cumsum(active, axis=0, dtype=np.float32)])
    lo = np.clip(np.arange(N) - w // 2, 0, N); hi = np.clip(np.arange(N) + w // 2 + 1, 0, N)
    busy = (cs[hi] - cs[lo]) / (hi - lo)[:, None, None] > 0.6
    r_ = max(2, gh // 8); ring = np.zeros((gh, gw), bool)
    ring[:r_] = ring[-r_:] = True; ring[:, :r_] = ring[:, -r_:] = True
    edge = active[:, ring].mean(axis=1)
    pad = np.pad(edge, 3, mode="edge")
    edge = np.max([pad[k:k + len(edge)] for k in range(7)], axis=0)        # a few frames either side
    cam, camused = camera_track(frames, times, cuts, shot_of, edge)
    el = active & ~busy
    near = camused.copy()                         # a camera move's own edges are not element moves
    for k in range(1, 4):
        near[k:] |= camused[:-k]; near[:-k] |= camused[k:]
    el[near] = False
    moving = el.any(axis=(1, 2)); moving[0] = False
    runs = []                                     # runs of motion inside a shot; gaps of up to 2 frames are bridged
    bounds = [0] + cuts + [N]
    for s0, s1 in zip(bounds[:-1], bounds[1:]):
        i = s0 + 1
        while i < s1:
            if moving[i]:
                j = i
                while j + 1 < s1 and (moving[j + 1] or (j + 2 < s1 and moving[j + 2]) or (j + 3 < s1 and moving[j + 3])):
                    j += 1
                while not moving[j]:
                    j -= 1
                if j - i + 1 >= 2:
                    runs.append((i, j, s0))
                i = j + 1
            else:
                i += 1
    moves, staggers = list(cam), []
    for blob in blobs(el, moving, runs):
        a, b, shot0, cadence = blob["a"], blob["b"], blob["shot0"], blob["cadence"]
        act = el[a:b + 1] & blob["cells"][None]
        comp = blob["cells"]
        onset = np.where(comp, np.argmax(act, axis=0), -1)
        groups = [comp]
        u = np.unique(onset[comp])
        if len(u) >= 3:                           # a stagger: onsets in clusters with clean gaps between them
            cl = [[u[0]]]
            for v in u[1:]:
                (cl[-1].append(v) if v - cl[-1][-1] <= cadence else cl.append([v]))
            if len(cl) >= 3:
                sub = [comp & np.isin(onset, c) for c in cl]
                size = [x.sum() for x in sub]
                big = [x for x, n in zip(sub, size) if n >= 0.4 * max(size)]
                cen = [np.argwhere(x).mean(axis=0) for x in big]
                for x, n in zip(sub, size):               # a sliver that starts late (an element rising into new
                    if n < 0.4 * max(size):              # cells) belongs to the nearest real element
                        k = int(np.argmin([np.hypot(*(np.argwhere(x).mean(axis=0) - c)) for c in cen]))
                        big[k] = big[k] | x
                if len(big) >= 3:
                    groups = big
        firsts = []
        for g in groups:
            ga = act[:, g].any(axis=1)
            if not ga.any():
                continue
            ia = a + int(np.argmax(ga)); ib = a + len(ga) - 1 - int(np.argmax(ga[::-1]))
            m = measure(frames, times, ia, ib, g, shot0, busy[ia:ib + 1].any(axis=0))
            if m:
                moves.append(m); firsts.append(m)
        if len(groups) >= 3:
            stagger_of(firsts, staggers)
    # staggers across separate elements too: three or more alike, starting at a steady beat, close in time
    area = lambda m: m["box"][2] * m["box"][3]
    alike = sorted([m for m in moves if m["kind"] in ("slide", "fade", "reveal") and m["visible"] < 1.2 and m["frames"] >= 4],
                   key=lambda m: m["start"])
    k = 0
    while k < len(alike):
        grp = [alike[k]]
        for m in alike[k + 1:]:
            if m["start"] - grp[-1]["start"] > 0.6:
                break
            lined = abs(m["box"][1] - grp[0]["box"][1]) < 0.06 or abs(m["box"][0] - grp[0]["box"][0]) < 0.06
            if (m["kind"] == grp[0]["kind"] and 0.6 < m["visible"] / max(grp[0]["visible"], 1e-3) < 1.6 and lined
                    and 0.5 < area(m) / max(area(grp[0]), 1e-6) < 2 and m["start"] > grp[-1]["start"]):
                grp.append(m)
        if len(grp) >= 3 and not any(abs(x["t"] - grp[0]["start"]) < 0.05 for x in staggers):
            if stagger_of(grp, staggers):
                k += len(grp); continue
        k += 1
    moves.sort(key=lambda m: m["start"])
    cut_times = [float(times[c]) for c in cuts]
    out = {"video": os.path.abspath(video), "size": [info["w"], info["h"]], "fps": round(fps, 3),
           "frames": int(N), "duration": round(float(times[-1] - times[0] + 1 / fps), 3),
           "cuts": [round(c, 3) for c in cut_times], "moves": moves, "staggers": staggers,
           "moving_share": round(float((active.any(axis=(1, 2))).mean()), 3),
           "footage_share": round(float(busy.any(axis=(1, 2)).mean()), 3)}
    out["summary"] = summarise(out, runs, times)
    out["cut_rhythm"] = cut_rhythm(cut_times)
    if beats and info["audio"]:
        out["beat"] = beat_sync(video, cut_times, [m["start"] for m in moves if m["kind"] != "footage"], fps, start, end, bpm)
    return out


def measure(frames, times, ia, ib, cells, shot0, busy=None):
    """One element's move between frames ia and ib: kind, direction, distance, length, ease. Cells where footage
    plays (`busy`) are left out of the measurements."""
    N, H, W = frames.shape
    ys, xs = np.nonzero(cells)
    y0, y1 = max(0, (ys.min() - 1) * CELL), min(H, (ys.max() + 2) * CELL)
    x0, x1 = max(0, (xs.min() - 1) * CELL), min(W, (xs.max() + 2) * CELL)
    pre, post = ia - 1, ib
    crop = lambda i: frames[i, y0:y1, x0:x1].astype(np.float32)
    idx = list(range(pre, post + 1))
    steps = np.array([np.abs(crop(i) - crop(i - 1)).mean() for i in idx[1:]])
    rep = repeats(steps)
    keep = [pre] + [i for k, i in enumerate(idx[1:]) if k not in rep or i == post]
    t = np.array([times[i] for i in keep])
    C = [crop(i) for i in keep]
    hh, ww = C[0].shape
    full = (hh * ww) / float(H * W) > 0.5
    win = np.outer(np.hanning(hh), np.hanning(ww)).astype(np.float32) + 1e-3
    quiet = np.ones((hh, ww), np.float32)
    if busy is not None and busy.any():
        b = np.kron(busy, np.ones((CELL, CELL), np.float32))
        b = np.pad(b, ((0, max(0, H - b.shape[0])), (0, max(0, W - b.shape[1]))))[y0:y1, x0:x1]
        quiet = 1 - 0.97 * b[:hh, :ww]
        win = win * quiet
        C = [c * quiet + c[quiet > 0.5].mean() * (1 - quiet) if (quiet > 0.5).any() else c for c in C]
    sh = [(0.0, 0.0, 1.0)] + [phase_shift(C[k - 1], C[k], win) for k in range(1, len(C))]
    X = np.cumsum([[v[0], v[1]] for v in sh], axis=0)                     # (y, x) displacement so far
    Tv = X[-1]; dist = float(np.hypot(*Tv)); path = float(sum(np.hypot(v[0], v[1]) for v in sh))
    straight = dist / path if path > 1e-6 else 0.0
    base = {"start": round(float(times[pre]), 3), "end": round(float(times[post]), 3),
            "visible": round(float(times[post] - times[pre]), 3), "frames": len(keep) - 1,
            "repeats_dropped": len(idx) - len(keep),
            "box": [round(x0 / W, 3), round(y0 / H, 3), round((x1 - x0) / W, 3), round((y1 - y0) / H, 3)],
            "after_cut": round(float(times[pre] - times[shot0]), 3) if shot0 > 0 else None}
    if full and len(C) >= 3:
        L = np.cumsum([0.0] + [math.log(scale_between(C[k - 1], C[k])[0]) for k in range(1, len(C))])
        if abs(L[-1]) > 0.05 and abs(L[-1]) > 2.0 * dist / max(hh, ww):
            base.update(kind="zoom", scale=round(float(math.exp(L[-1])), 3))
            return finish(base, t, L / L[-1], True)
    if dist >= 3.0 and straight >= 0.6:
        dy, dx = float(Tv[0]), float(Tv[1])
        base.update(kind="pan" if full else "slide", distance=round(dist / W, 3),
                    direction=("right" if dx > 0 else "left") if abs(dx) >= abs(dy) else ("down" if dy > 0 else "up"))
        return finish(base, t, (X @ (Tv / dist)) / dist, True, straight)
    F = C[-1] - C[0]; nF = float((F * F).sum())
    if nF < 1e-3 * F.size:
        return None                                            # it moved and came back: a pulse, nothing to fit
    amp = np.array([float(((c - C[0]) * F).sum()) / nF for c in C])
    thrA = max(6.0, 0.1 * np.abs(F).max())
    mF = np.abs(F) > thrA
    area = np.array([float((np.abs(c - C[0])[mF] > thrA).mean()) if mF.any() else 0.0 for c in C])
    if float(np.mean(area - amp)) > 0.2:
        base["kind"] = "fade"; return finish(base, t, amp, False)
    base["kind"] = "reveal"; return finish(base, t, area, False)


def summarise(out, runs, times):
    instant = [m for m in out["moves"] if m["family"] == "too short"]
    mv = [m for m in out["moves"] if m["kind"] != "footage" and m["family"] != "too short"]
    dur = out["duration"] or 1
    fam = {}
    for m in mv:
        fam[m["family"]] = fam.get(m["family"], 0) + 1
    names = {}
    for m in mv:
        if m.get("ease"):
            names[m["ease"]] = names.get(m["ease"], 0) + 1
    by_kind = {}
    for m in mv:
        by_kind.setdefault(m["kind"], []).append(m["dur"])
    holds = [float(times[r2[0]] - times[r1[1]]) for r1, r2 in zip(runs[:-1], runs[1:]) if r1[2] == r2[2]]
    first = {}
    for m in mv:
        if m["after_cut"] is not None:
            k = round(m["start"] - m["after_cut"], 3)
            first[k] = min(first.get(k, 9e9), m["after_cut"])
    known = [m for m in mv if m["family"] != "unclear"]
    s = {"moves": len(mv), "per_minute": round(len(mv) / dur * 60, 1), "instant_changes": len(instant),
         "footage_moves": sum(m["kind"] == "footage" for m in out["moves"]),
         "families": dict(sorted(fam.items(), key=lambda x: -x[1])),
         "eases": dict(sorted(names.items(), key=lambda x: -x[1])[:6]),
         "median_dur": {k: round(float(np.median(v)), 3) for k, v in by_kind.items()},
         "overshoot_share": round(sum(m["overshoot"] for m in known) / len(known), 2) if known else None,
         "peak_at_median": round(float(np.median([m["peak_at"] for m in known if m["peak_at"] is not None])), 2) if known else None,
         "stagger_every": round(float(np.median([x["every"] for x in out["staggers"]])), 3) if out["staggers"] else None,
         "first_move_after_cut": round(float(np.median(list(first.values()))), 3) if first else None,
         "hold_median": round(float(np.median(holds)), 3) if holds else None,
         "cuts_per_minute": round(len(out["cuts"]) / dur * 60, 1),
         "drifts": [{"start": m["start"], "dur": m["dur"], "kind": m["kind"], "ease": m.get("ease") or m["family"]}
                    for m in mv if m["dur"] >= 2.0]}
    return s


def beat_sync(video, cut_times, move_starts, fps, start=None, end=None, bpm=None):
    """The music's tempo from the bass (under 120 Hz, so a voice doesn't fool it), only where three or more
    overlapping 15 s windows (2.5 s apart) agree; then the share of cuts and move starts on a beat inside that stretch."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                    "launch-demo", "scripts"))
    try:
        import beats
    except ImportError:
        return None
    sr = 22050
    cmd = (["ffmpeg", "-v", "error"] + (["-ss", "%.3f" % start] if start else []) + ["-i", video] +
           (["-t", "%.3f" % (end - (start or 0))] if end else []) +
           ["-ac", "1", "-ar", str(sr), "-af", "lowpass=f=120,highpass=f=35", "-f", "f32le", "-"])
    x = np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.float32)
    off0 = start or 0
    if len(x) < sr * 15:
        return {"note": "under 15 s of audio: no tempo"}
    est = []
    for s0 in ([] if bpm else np.arange(0, len(x) / sr - 15 + 1e-6, 2.5)):
        y = x[int(s0 * sr):int((s0 + 15) * sr)]
        guess = None
        if float(np.sqrt((y ** 2).mean())) >= 2e-3:
            try:
                guess = beats.analyse(y, sr)["bpm"]
            except Exception:
                guess = None
        est.append((float(s0), guess))
    vals = [(s0, b) for s0, b in est if b is not None]   # the tempo most windows agree on (within 1.5 BPM)
    if bpm:
        best = []
    else:
        support = [[w for w in vals if abs(w[1] - b) <= 1.5] for _, b in vals]
        best = max(support, key=len) if support else []
        if len(best) < max(3, 0.5 * len(vals)):
            return {"note": "no tempo everyone would agree on (a voice or effects over the music); give it with --bpm"}
    t0, t1 = (best[0][0], best[-1][0] + 15) if best else (0.0, len(x) / sr)
    a = beats.analyse(x[int(t0 * sr):int(t1 * sr)], sr, bpm=bpm)
    beat, ph = a["beat"], a["phase"] + t0 + off0
    tol = max(0.05, 1.5 / fps)
    off = lambda t: abs((t - ph + beat / 2) % beat - beat / 2)
    inside = lambda ts: [t for t in ts if t0 + off0 <= t <= t1 + off0]
    share = lambda ts: round(sum(off(t) <= tol for t in ts) / len(ts), 2) if ts else None
    return {"bpm": a["bpm"], "from": round(t0 + off0, 2), "to": round(t1 + off0, 2), "tolerance": round(tol, 3),
            "cuts_on_beat": share(inside(cut_times)), "moves_on_beat": share(inside(move_starts)),
            "chance": round(min(1.0, 2 * tol / beat), 2)}


# ---- out -----------------------------------------------------------------------------------------------------------
def curves_sheet(moves, path, n=12):
    from PIL import Image, ImageDraw
    pick = sorted([m for m in moves if m["kind"] != "footage" and m.get("_fit")],
                  key=lambda m: (m["family"] == "unclear", -m["frames"]))[:n]             # clear fits first
    pick.sort(key=lambda m: m["start"])
    if not pick:
        return False
    cw, ch, cols = 300, 210, 4
    rows = (len(pick) + cols - 1) // cols
    img = Image.new("RGB", (cw * cols, ch * rows), (248, 250, 252)); d = ImageDraw.Draw(img)
    for i, m in enumerate(pick):
        ox, oy = (i % cols) * cw, (i // cols) * ch
        px, py, pw, ph_ = ox + 30, oy + 46, cw - 50, ch - 76
        d.rectangle([px, py, px + pw, py + ph_], outline=(203, 213, 225))
        t = np.array(m["_t"]); p = np.array(m["_p"])
        name, s0, du = m["_fit"]
        T = max(t[-1], s0 + du, 1e-3); lo = min(0.0, s0)
        X = lambda v: px + (v - lo) / (T - lo) * pw
        Y = lambda v: py + ph_ - (v + 0.1) / 1.3 * ph_
        d.line([px, Y(1), px + pw, Y(1)], fill=(226, 232, 240)); d.line([px, Y(0), px + pw, Y(0)], fill=(226, 232, 240))
        f = EASES[name][0]; us = np.linspace(0, 1, 60)
        fv = f(np.clip((t - s0) / du, 0, 1)); flo, fhi = fv[0], fv[-1]
        pts = [(X(s0 + u * du), Y((f(np.array([u]))[0] - flo) / max(fhi - flo, 1e-6))) for u in us]
        d.line(pts, fill=(79, 70, 229), width=2)
        for tv, pv in zip(t, p):
            d.ellipse([X(tv) - 3, Y(pv) - 3, X(tv) + 3, Y(pv) + 3], fill=(219, 39, 119))
        lab = "%s  %s%s  %.2f s" % (fmt(m["start"]), m["kind"], (" " + m["direction"]) if m.get("direction") else "", m["dur"])
        d.text((ox + 10, oy + 8), lab, fill=(15, 23, 42))
        d.text((ox + 10, oy + 24), "%s (%s)%s fit %.2f" % (m.get("ease") or "-", m["family"], "  overshoot" if m["overshoot"] else "",
                                                          m.get("fit_rms", 0)), fill=(71, 85, 105))
    img.save(path)
    return True


def fmt(t):
    return "%d:%04.1f" % (int(t // 60), t % 60)


def words(r):
    s = r["summary"]; L = ["# Motion", ""]
    L.append("- %d designed moves in %.0f s (%.0f a minute); %d instant changes of 1-3 frames (caption highlights, colour "
             "flips) and %d stretches of footage moving by itself left out; something moves %d%% of the time." % (
                 s["moves"], r["duration"], s["per_minute"], s["instant_changes"], s["footage_moves"], r["moving_share"] * 100))
    if s["families"]:
        L.append("- Eases: " + ", ".join("%s %d" % (k, v) for k, v in s["families"].items()) +
                 (". Named fits (10+ frames): " + ", ".join("%s %d" % (k, v) for k, v in s["eases"].items()) if s["eases"] else "") + ".")
    if s["median_dur"]:
        L.append("- Typical lengths: " + ", ".join("%s %.2f s" % (k, v) for k, v in s["median_dur"].items()) + ".")
    if s["overshoot_share"] is not None:
        L.append("- Overshoot in %d%% of moves; speed peaks %d%% of the way through a move (median)." %
                 (s["overshoot_share"] * 100, (s["peak_at_median"] or 0) * 100))
    if r["staggers"]:
        L.append("- Staggers: %d, one element every %.2f s (median)." % (len(r["staggers"]), s["stagger_every"]))
    if s["first_move_after_cut"] is not None:
        L.append("- After a cut, the first move starts %.2f s in (median)." % s["first_move_after_cut"])
    if s["hold_median"] is not None:
        L.append("- Holds between moves: %.2f s (median)." % s["hold_median"])
    for c in r.get("cut_rhythm") or []:
        fits = ["%s at %.0f BPM" % (w, n * 60 / c["every"]) for n, w in ((1, "every beat"), (2, "every 2 beats"), (4, "every bar"))
                if 70 <= n * 60 / c["every"] <= 180]
        L.append("- Steady cutting: a cut every %.2f s from %s to %s (%d cuts%s)." % (
            c["every"], fmt(c["from"]), fmt(c["to"]), c["cuts"], "; to music: " + " or ".join(fits) if fits else ""))
    if s["drifts"]:
        L.append("- Long moves (2 s or more): " + "; ".join("%s %s %.1f s %s" % (fmt(x["start"]), x["kind"], x["dur"], x["ease"]) for x in s["drifts"][:6]) + ".")
    b = r.get("beat")
    if b and "note" in b:
        L.append("- Music: %s." % b["note"])
    if b and "bpm" in b:
        L.append("- Music at %s BPM from %s to %s: %s of cuts and %s of move starts there land on a beat (by chance: %d%%)." % (
            b["bpm"], fmt(b["from"]), fmt(b["to"]), "%d%%" % (b["cuts_on_beat"] * 100) if b["cuts_on_beat"] is not None else "none",
            "%d%%" % (b["moves_on_beat"] * 100) if b["moves_on_beat"] is not None else "none", b["chance"] * 100))
    L += ["", "Use: GSAP eases and lengths as measured in custom code; a text animation's speed with `tl.timeScale(its "
          "length / the measured length)`; fast-cut zoom `ease` = the zoom's length in s, intro `move` = a glide's length."]
    return "\n".join(L) + "\n"


def write(r, out):
    os.makedirs(out, exist_ok=True)
    curves = curves_sheet(r["moves"], os.path.join(out, "curves.png"))
    clean = dict(r); clean["moves"] = [{k: v for k, v in m.items() if not k.startswith("_")} for m in r["moves"]]
    json.dump(clean, open(os.path.join(out, "motion.json"), "w"), indent=1)
    open(os.path.join(out, "MOTION.md"), "w").write(words(r))
    return curves


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--start", type=float)
    ap.add_argument("--end", type=float)
    ap.add_argument("--width", type=int, default=256)
    ap.add_argument("--bpm", type=float, help="the music's tempo when you know it (a voice over the music hides it)")
    a = ap.parse_args()
    r = analyse(a.video, a.width, a.start, a.end, bpm=a.bpm)
    curves = write(r, a.out)
    print(words(r))
    print("wrote %s/motion.json, MOTION.md%s" % (a.out, ", curves.png" if curves else ""))


if __name__ == "__main__":
    main()
