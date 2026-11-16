#!/usr/bin/env python3
"""narration-video.py: a voiceover (no camera) -> public/input-video.mp4, so a narrated or faceless video runs the same
Pipeline as a flat cut: the narration is the footage's audio, the picture is a plain plate the cards and cutaways sit on.

  python3 narration-video.py --audio W/voiceover/voiceover.wav --out W/public/input-video.mp4 [--bg "#1A1A2E"]
  python3 narration-video.py --audio ... --out ... --bg W/raw/screen.mp4     # a screen recording or B-roll, looped, muted
  python3 narration-video.py --audio ... --out ... --bg W/raw/still.png      # a still, scaled to fill

--bg is a colour (#RRGGBB), an image or a video; the default is the style's navy. The encode matches the Pipeline's step 2
(30 fps, a keyframe every 30 frames, CRF 16, BT.709, AAC 256k at 48 kHz) so the render seeks cleanly. Then copy the
voiceover's transcript.json to W/transcript.json and go on with the storyboard.
"""
import argparse, os, re, subprocess

ap = argparse.ArgumentParser()
ap.add_argument("--audio", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--bg", default="#1A1A2E")
ap.add_argument("--size", default="1920x1080")
ap.add_argument("--fps", type=int, default=30)
ap.add_argument("--tail", type=float, default=0.5, help="seconds of picture after the last word")
a = ap.parse_args()

W, H = (int(x) for x in a.size.split("x"))
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.audio],
                           capture_output=True, text=True, check=True).stdout.strip()) + a.tail
fill = "scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,setsar=1,fps=%d" % (W, H, W, H, a.fps)
if re.fullmatch(r"#[0-9A-Fa-f]{6}", a.bg):
    pic = ["-f", "lavfi", "-i", "color=c=0x%s:s=%dx%d:r=%d:d=%.3f" % (a.bg[1:], W, H, a.fps, dur)]
    vf = "setsar=1"
elif a.bg.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
    pic = ["-loop", "1", "-framerate", str(a.fps), "-t", "%.3f" % dur, "-i", a.bg]
    vf = fill
else:
    pic = ["-stream_loop", "-1", "-t", "%.3f" % dur, "-i", a.bg]
    vf = fill
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
subprocess.run(["ffmpeg", "-y", "-v", "error"] + pic + ["-i", a.audio,
                "-map", "0:v:0", "-map", "1:a:0", "-vf", vf, "-t", "%.3f" % dur,
                "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-r", str(a.fps), "-g", str(a.fps), "-keyint_min", str(a.fps),
                "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
                "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-af", "apad", "-movflags", "+faststart", a.out], check=True)
print("wrote %s (%.2f s, %dx%d at %d fps, picture: %s)" % (a.out, dur, W, H, a.fps, a.bg))
