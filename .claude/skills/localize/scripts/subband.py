#!/usr/bin/env python3
"""Cover burned-in subtitles with a frosted band and set new ones on it, in ONE FFmpeg pass.

  python3 subband.py --video in.mp4 --cues cues.json --out out.mp4 [--audio mix.wav] [--font F.ttf]
                     [--size 40] [--style auto|dark|light] [--crf 15]

cues.json: [{"start": 6.17, "end": 8.17, "text": "「この髪型、似合うかな？」", "cover": [663, 959, 1267, 1018]}, ...]
`cover` is the old subtitle's box in video pixels (from find-subs.py); the band always covers it with room to spare.
Cues less than --join seconds apart share one band (one fade in, one fade out, the width of the widest line), and only
the text changes inside it. Each band blurs the picture under it, tints it (dark, or light on bright frames with
--style auto) and carries the new line, so no trace of the old subtitle shows.
"""
import argparse, json, os, subprocess, sys, tempfile

FADE = 0.12      # band fade in / out
XFADE = 0.08     # text change inside a band
LEAD = 0.30      # band starts this much before the old subtitle: old subtitles fade in before the reader sees them
TAIL = 0.20      # and ends this much after it


def font(path, size, weight):
    from PIL import ImageFont
    f = ImageFont.truetype(path, size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def blocks_of(cues, join):
    """Cues that follow each other closely, said by the same speaker and in the same band style, share a band."""
    out = []
    for c in sorted(cues, key=lambda c: c["start"]):
        p = out[-1][-1] if out else None
        if p and c["start"] - p["end"] < join and c.get("who") == p.get("who") and c["_style"] == p["_style"]:
            out[-1].append(c)
        else:
            out.append([c])
    return out


def luma(video, t, box, H):
    """Background brightness around a subtitle: the median of a strip three times its height, so the old (white)
    letters do not count."""
    x0, y0, x1, y1 = box
    h = y1 - y0
    y0, y1 = max(0, y0 - h), min(H, y1 + h)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.3f" % t, "-i", video, "-frames:v", "1",
                          "-vf", "crop=%d:%d:%d:%d,scale=96:24,format=gray" % (x1 - x0, y1 - y0, x0, y0),
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    return sorted(raw)[len(raw) // 2] / 255.0 if raw else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--cues", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--audio", help="replace the soundtrack with this file")
    ap.add_argument("--font", default=os.path.join(os.path.dirname(__file__), "..", "fonts", "NotoSansJP.ttf"))
    ap.add_argument("--size", type=int, default=40)
    ap.add_argument("--weight", type=int, default=500)
    ap.add_argument("--style", default="auto", choices=["auto", "dark", "light"])
    ap.add_argument("--join", type=float, default=0.45)
    ap.add_argument("--crf", type=int, default=15)
    ap.add_argument("--preset", default="medium")
    a = ap.parse_args()
    from PIL import Image, ImageDraw, ImageFilter

    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                      "stream=width,height", "-of", "json", a.video], capture_output=True, text=True).stdout)
    W, H = info["streams"][0]["width"], info["streams"][0]["height"]
    cues = [c for c in json.load(open(a.cues)) if c.get("text")]
    f = font(a.font, a.size, a.weight)
    padx, bandh = int(a.size * 1.2), int(a.size * 2.1)
    tmp = tempfile.mkdtemp(prefix="subband-")
    inputs, chains, last = [], [], "[0:v]"
    for c in cues:
        c["_style"] = a.style
        if a.style == "auto":
            x0, y0, x1, y1 = c.get("cover") or (W // 4, int(H * 0.87), W * 3 // 4, int(H * 0.96))
            c["_style"] = "light" if luma(a.video, (c["start"] + c["end"]) / 2, (x0, y0, x1, y1), H) > 0.62 else "dark"
    blocks = blocks_of(cues, a.join)
    # band times: LEAD before and after, but two bands that meet cross-fade at the cue boundary instead of overlapping
    spans = [[max(0.0, b[0]["start"] - LEAD), b[-1]["end"] + TAIL] for b in blocks]
    for i in range(len(spans) - 1):
        if spans[i][1] > spans[i + 1][0]:
            mid = (blocks[i][-1]["end"] + blocks[i + 1][0]["start"]) / 2
            spans[i][1], spans[i + 1][0] = mid + FADE / 2, mid - FADE / 2
    chains.append("[0:v]split=%d%s" % (len(blocks) + 1, "".join("[s%d]" % i for i in range(len(blocks) + 1))))
    last = "[s%d]" % len(blocks)
    n_in = 1
    for bi, blk in enumerate(blocks):
        covers = [c["cover"] for c in blk if c.get("cover")]
        need = max(f.getlength(c["text"]) + 2 * padx for c in blk)
        if covers:
            need = max(need, max(c[2] - c[0] for c in covers) + 2 * padx)
            cy = sum((c[1] + c[3]) / 2 for c in covers) / len(covers)
            need_h = max(c[3] - c[1] for c in covers) + int(a.size * 0.9)
        else:
            cy, need_h = H * 0.917, 0
        bw = int(min(W - 40, need) // 2 * 2)
        bh = int(max(bandh, need_h) // 2 * 2)
        bx, by = (W - bw) // 2, int(cy - bh / 2) // 2 * 2
        t0, t1 = spans[bi]
        style = blk[0]["_style"]
        tint = (250, 248, 255, 150) if style == "light" else (12, 10, 22, 128)
        ink = (26, 26, 46, 255) if style == "light" else (255, 255, 255, 255)
        rad = int(bh * 0.28)
        # rounded matte for the blurred picture, and the tint card
        matte = Image.new("L", (bw, bh), 0)
        ImageDraw.Draw(matte).rounded_rectangle([0, 0, bw - 1, bh - 1], radius=rad, fill=255)
        mpath = os.path.join(tmp, "m%d.png" % bi); matte.save(mpath)
        card = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        ImageDraw.Draw(card).rounded_rectangle([0, 0, bw - 1, bh - 1], radius=rad, fill=tint)
        cpath = os.path.join(tmp, "c%d.png" % bi); card.save(cpath)
        dur = t1 - t0
        inputs += ["-loop", "1", "-t", "%.3f" % dur, "-i", mpath, "-loop", "1", "-t", "%.3f" % dur, "-i", cpath]
        mi, ci = n_in, n_in + 1; n_in += 2
        fade = "fade=t=in:st=0:d=%.2f:alpha=1,fade=t=out:st=%.3f:d=%.2f:alpha=1" % (FADE, dur - FADE, FADE)
        chains.append("[s%d]trim=start=%.3f:end=%.3f,setpts=PTS-STARTPTS,crop=%d:%d:%d:%d,gblur=sigma=%d,format=yuva420p[bl%d]"
                      % (bi, t0, t1, bw, bh, bx, by, max(14, a.size // 2), bi))
        chains.append("[%d:v]format=gray,scale=%d:%d[mm%d]" % (mi, bw, bh, bi))
        chains.append("[bl%d][mm%d]alphamerge,%s,setpts=PTS+%.3f/TB[b%d]" % (bi, bi, fade, t0, bi))
        chains.append("[%d:v]format=rgba,%s,setpts=PTS+%.3f/TB[c%d]" % (ci, fade, t0, bi))
        chains.append("%s[b%d]overlay=%d:%d:eof_action=pass[vb%d]" % (last, bi, bx, by, bi))
        chains.append("[vb%d][c%d]overlay=%d:%d:eof_action=pass[vc%d]" % (bi, bi, bx, by, bi))
        last = "[vc%d]" % bi
        # the lines, each fading in and out inside the band
        for li, c in enumerate(blk):
            img = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            tw = f.getlength(c["text"])
            asc, desc = f.getmetrics()
            ty = (bh - (asc + desc)) / 2 + a.size * 0.04
            if style == "dark":
                sh = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
                ImageDraw.Draw(sh).text(((bw - tw) / 2, ty + 2), c["text"], font=f, fill=(0, 0, 0, 150))
                img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(3)))
                d = ImageDraw.Draw(img)
            d.text(((bw - tw) / 2, ty), c["text"], font=f, fill=ink)
            tpath = os.path.join(tmp, "t%d_%d.png" % (bi, li)); img.save(tpath)
            s = t0 if li == 0 else c["start"]
            e = t1 if li == len(blk) - 1 else blk[li + 1]["start"]
            fi = FADE if li == 0 else XFADE
            fo = FADE if li == len(blk) - 1 else XFADE
            ld = e - s
            inputs += ["-loop", "1", "-t", "%.3f" % ld, "-i", tpath]
            ti = n_in; n_in += 1
            chains.append("[%d:v]format=rgba,fade=t=in:st=0:d=%.2f:alpha=1,fade=t=out:st=%.3f:d=%.2f:alpha=1,setpts=PTS+%.3f/TB[t%d_%d]"
                          % (ti, fi, ld - fo, fo, s, bi, li))
            chains.append("%s[t%d_%d]overlay=%d:%d:eof_action=pass[vt%d_%d]" % (last, bi, li, bx, by, bi, li))
            last = "[vt%d_%d]" % (bi, li)
        print("band %2d  %7.2f-%7.2f  %dx%d at y %d  %s  %s" % (bi + 1, t0, t1, bw, bh, by, style,
                                                             " / ".join(c["text"] for c in blk)))
    graph = ";\n".join(chains) + ";\n%sformat=yuv420p[vout]" % last
    gpath = os.path.join(tmp, "graph.txt"); open(gpath, "w").write(graph)
    cmd = ["ffmpeg", "-v", "error", "-stats", "-y", "-i", a.video] + inputs
    amap = ["-map", "0:a?", "-c:a", "copy"]
    if a.audio:
        cmd += ["-i", a.audio]
        amap = ["-map", "%d:a" % n_in, "-c:a", "aac", "-b:a", "320k", "-shortest"]
    cmd += ["-/filter_complex", gpath, "-map", "[vout]"] + amap + [
        "-c:v", "libx264", "-preset", a.preset, "-crf", str(a.crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    r = subprocess.run(cmd)
    if r.returncode:
        sys.exit("ffmpeg failed (graph in %s)" % gpath)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
