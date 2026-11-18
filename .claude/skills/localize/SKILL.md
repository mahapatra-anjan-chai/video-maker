---
name: localize
description: Localise a finished video into another language without touching the picture. The new voice goes on ElevenLabs, line by line, in each line's original slot, with a separate voice per character. The original voice is taken out of the soundtrack while the music, effects and song vocals stay. The burned-in subtitles are covered by a frosted band carrying the translated ones. Use for "make a Japanese version", "dub this into Hindi", "replace the English VO and subtitles with X", "localise this ad", "translate the voiceover and subtitles". Not for changing on-screen copy or UI text inside the picture (that is a rebuild with youtube-edit and HyperFrames).
---

# Localize

The picture stays exactly as delivered: same cut, size and frame rate, with on-screen copy and UI text left in the
original language. Three things change: the voice, the subtitles, and nothing else in the sound. Run from the
project folder with `L=".claude/skills/localize/scripts"` and `W="videos/<project>"` (put the source in `$W/raw/`,
a hard link is fine for big files).

## The route (first full render in ~30 minutes for a 2-minute film)

1. **Look once:** `python3 .claude/skills/fast-cut/scripts/contact-sheet.py --video $W/raw/<src> --out $W/review/sheet.jpg --every 5`.
   It shows where the subtitles sit, who is on screen, and which lines are chat bubbles or other UI copy.
2. **In parallel (both in the background):**
   - `sh $L/separate.sh $W/raw/<src> $W/work/stems`: Demucs on the CPU, about 2-3 minutes. It gives
     `S=$W/work/stems/htdemucs_ft/<name>` with `vocals.wav` (every voice, song vocals included) and `no_vocals.wav`
     (music and effects), and the original soundtrack as `$W/work/stems/<name>.wav`.
   - `python3 $L/find-subs.py --video $W/raw/<src> --out $W/work/subs-en.json`: the old subtitles, with times and
     boxes, read by the macOS Vision OCR, about 1.5 minutes. If they sit higher than the bottom fifth, pass
     `--band 0.7,0.9`. Rerun with `--reuse` to skip the OCR.
3. **Transcribe the voice stem, not the mix:** `npx hyperframes transcribe $S/vocals.wav --json -d $W/work/vtx`.
   The mix hides words under the music.
4. **Draft the script:** `python3 $L/draft-script.py --words $W/work/vtx/transcript.json --subs $W/work/subs-en.json --vocals $S/vocals.wav --lang ja --out $W/script-ja.json`.
   It writes one entry per spoken line with `at`, `end`, `en`, the old subtitles it owns and its pitch. Then fill it in:
   - **Delete the song.** If a line has no subtitle and its words are lyrics (a repeated hook, half-heard words that
     fit the music's tune), it is the music and stays. A line with no subtitle whose words appear in a chat bubble on
     screen is dialogue, so dub it, but add no subtitle.
   - **`who`:** name each character from the contact sheet (`narrator`, `gym-man`, ...). Pitch under ~165 Hz is
     usually a man, over ~180 Hz a woman. Every character gets their own voice.
   - **`vo`:** the line to speak. Write brand names the way they are said (Shopwise as ショップワイズ), and numbers in kana
     if the reading matters. Keep it within the slot: a TTS voice says about 7-8 morae a second, so cut words before
     you reach for speed.
   - **`subs`:** translate each old subtitle in place, keeping its times. Write brand names as the brand writes them
     (Shopwise, not ショップワイズ). For dialogue use the language's own quote marks (「」 for Japanese) instead of italics.
5. **Cast and cost (always ask first):** write `$W/cast.json`
   (`{"model": "eleven_multilingual_v2", "<who>": "<voice id>", ...}`) from `voices/<lang>.json`, preferring voices
   marked `tested`. `python3 $L/dub.py plan --script $W/script-ja.json --cast $W/cast.json` prints every line and
   the credits (1 per character). Show the cast and the cost and wait for a yes.
6. **Voice:** `python3 $L/dub.py voice --script ... --cast ... --out $W/audio/vo-ja.wav --length <video s> --match $S/vocals.wav --yes`.
   Lines are cached in `videos/_shared/tts-cache`, so a rerun only pays for changed lines. Each line goes at its
   original start, with pauses capped at 0.18 s (`--pause`). A line may run on into the gap before the next one, and
   is sped up at most 1.25x (`--max-tempo`). Its level matches the original line's. The report says which lines were
   sped up or moved. A line that still pushes the next one by more than ~0.3 s needs fewer words, not more speed.
7. **Soundtrack:** `python3 $L/remix.py --original $W/work/stems/<name>.wav --stems $S --script $W/script-ja.json --vo $W/audio/vo-ja.wav --words $W/work/vtx/transcript.json --out $W/audio/mix-ja.wav`.
   The music is kept whole. With `--words`, the voice stem is muted only from the first to the last word of each
   original phrase that is being dubbed, so song phrases survive even where a new line runs over them; it prints
   every kept phrase and flags any that got muted. Loudness is matched to the original, with a -1 dBTP ceiling.
   **Then check the voice level per speaker** against the original voice stem (LUFS over each speaker's lines). The
   per-line match lands 1-4 dB off, so set `"gain": {"<who>": dB}` in `cast.json` and rerun steps 6-7; both are free
   once the lines are cached. On a brand film the original voices sit at about the music's level or above. v1 here
   went out ~9 dB too quiet and the creator heard it at once.
8. **Subtitles and render:** `python3 $L/cues.py --script ... --subs $W/work/subs-en.json --placed $W/audio/vo-ja.json --out $W/cues-ja.json`,
   then `python3 $L/subband.py --video $W/raw/<src> --cues $W/cues-ja.json --audio $W/audio/mix-ja.wav --out "~/Movies/YouTube Renders/<project>/<project>-v1-<W>x<H>.mp4"`.
   This is one FFmpeg pass, about 2 minutes for 2.5 minutes of 1080p. Each band blurs and tints the picture under
   it: dark, or light on bright frames. It starts 0.3 s before the old subtitle, because old subtitles fade in before
   OCR sees them, and covers its box with room to spare. Bands are shared by consecutive cues of one speaker. The
   font is Noto Sans JP from `fonts/` (`setup.sh` fetches it). For another script, pass `--font` with that
   language's Noto Sans.
9. **Check, then send:**
   - `python3 $L/review-subs.py --video <out> --cues $W/cues-ja.json --out $W/review/v1/subs.jpg`: every cue, plus
     the frames just before and after each band, where an old subtitle could peek through.
   - Transcribe the bed (`remix.py ... --vo-gain -120 --out $W/work/bed.wav`) in the source language. Only song
     words may come back.
   - Send `subs.jpg` and a 720p preview with SendUserFile. The full file stays in Movies.

## Rules

- Office work: the company's ElevenLabs account is cleared for this (`CLAUDE.local.md`), and the video never leaves
  this Mac.
- Never re-voice, cover or translate on-screen copy unless asked. The creator asked for the voice and the subtitles.
- Lip sync is not attempted. Dubbed lines on camera will not match the mouths, which is normal for dubbed ads; say so
  once.
- Keep `script-<lang>.json`, `cast.json` and `cues-<lang>.json` in `$W/versions/v<N>/` for each delivery.

## Traps

- `demucs -d mps` (Apple GPU) returns stems that do not add back up to the original. `separate.sh` uses the CPU.
- ElevenLabs Japanese voices read slowly. On the first pass the narrator ran 30-90% long, so `--pause` and run-on
  into the gaps are what make it fit. Before paying for retakes, shorten the text.
- This API key cannot list voices (`/shared-voices` returns 401). Use `voices/<lang>.json`; a wrong id fails at no
  cost.
- Old subtitles can fade in about 0.2 s before OCR reads them. Keep `LEAD` in `subband.py` at 0.3 s or more.
- FFmpeg's own mono-to-stereo upmix is 3 dB down, and normalising the whole voice track for one hot line drops
  every line. `remix.py` copies mono to both sides at full level, and `dub.py` writes float with no normalising.
- FFmpeg 7+ dropped `-filter_complex_script`. `subband.py` uses `-/filter_complex <file>`.
