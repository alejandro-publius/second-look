# The video

UPDATE_30 section 4. This folder holds everything the video is made from, except the video files themselves, which never go in the repository.

| File | What it is |
|---|---|
| [`SHOTLIST.md`](SHOTLIST.md) | The 14 beats: what is on screen, the words, and which clip plays when |
| [`VOICE_SCRIPT.md`](VOICE_SCRIPT.md) and [`teleprompter.html`](teleprompter.html) | The same words, for reading aloud |
| [`footage.csv`](footage.csv), [`CREDITS.md`](CREDITS.md) | The open creek footage and photos, and their credits |
| [`rough_cut.json`](rough_cut.json) | The rough cut with title cards and a scratch voice (`make video-rough`) |
| [`final_cut.json`](final_cut.json) | The final cut: its length, size, beats, credits, the captions file's SHA-256 and whether a voice was used |
| [`UPLOAD.md`](UPLOAD.md) | The title, description, tags and thumbnail, and how to upload it to YouTube and Devpost |

## The two commands

**1. Captions only, ready now:**

```
make video-final SCREENS=~/second-look-media/screens
```

It writes `~/second-look-media/final/second-look-final.mp4`, the captions beside it as `second-look-final.srt`, the YouTube thumbnail as `thumbnail.png`, and the summary to `docs/video/final_cut.json`. It prints the file, its length and its size. The screen recordings the cut uses are in `~/second-look-media/screens/`, outside every checkout; with no `SCREENS` it reads this checkout's `docs/video/clips/`. A set of recordings from before Sep 25 has no marks files, and the cut refuses it and says so: the check's pipe question has no mark to start at.

**2. With the voice, when it arrives:** save the recording as `~/second-look-media/voice/voice.m4a` (or `voice.wav`, or `voice.mp3`; if there are several, m4a wins, then wav), then run the same command again:

```
make video-final SCREENS=~/second-look-media/screens
```

The voice takes over the timing from the captions. It fits one of two ways, and `final_cut.json` says which in `voice_fit`:

- **each beat**, when `~/second-look-media/voice/voice_beats.txt` is there too. It has one line per beat of the cut, 13 lines, each starting with the second that beat's words start in the recording. An Audacity label export works as it is: only the first number on each line is read. Each beat gets its own stretch of the voice. A beat keeps its shot list length, or grows if its words take longer. Beat 11 is left out (see below): if it was read anyway, give it a line too, 14 in all, and its stretch of the voice is dropped.
- **whole voice**, when there is no `voice_beats.txt`. The recording plays straight through from the first words, after skipping any quiet at its start. Each beat is cut to where its words should fall, by its share of the script's letters. This is the one to use if the recording is one take read at an even pace, with beat 11 skipped.

With a voice, the captions are no longer drawn on the picture. They go into the mp4 as an English subtitles track, and the `.srt` beside it is the file to upload to YouTube. If the cut with the voice would run 4:00 or longer, nothing is built and the message says by how much: trim the pauses and run it again. Take the voice file out of the folder to go back to the captions only cut.

**For a review:** `make video-frames` saves one frame every 10 seconds of the built cut, named by the second (`frame_000.png`, `frame_010.png` and so on), in `~/second-look-media/final/frames/`, or in `FRAMES=/another/folder`.

## What is in the cut

- The words of each beat from `SHOTLIST.md`, the same words as `VOICE_SCRIPT.md`, drawn as captions a sentence or two at a time, two lines at most, on a box about 90 percent solid so no page text shows through. Over footage a caption sits above the credit line; over screen recordings alone it sits lower, under the phone page. They are spread over the beat by their length. No caption asks for faster reading than 17 letters a second: a beat whose words need longer runs longer than the shot list says.
- Each screen recording starts where its marks file says its use begins, past the consent and warm-up screens, and a screen part whose From in the shot list names a mark starts there (the check's dry weather pipe question). A recording shorter than its part holds its last frame: no screen starts over. A phone recording is 886 pixels tall from the top of the frame, the same size bare or in the phone outline.
- While the caption says "the link on screen", the live link is on screen beside the phone.
- Beat 11, `/two`, is left out: the clips are recorded against the mock API, whose lab result is made up, so the recording would show the mock's lab result, not theirs, and on Sep 25 `/api/two` on the live site said `theirs_status` down as well. `LEFT_OUT` in `scripts/video_final.py` holds it, and `final_cut.json` says why under `left_out`.
- The opening shot plays with no words, as the shot list says.
- Every creek clip keeps the credit line `scripts/cut_footage.py` drew in its lower left corner: title, author, licence, Wikimedia Commons. So each credit is on screen while its footage plays.
- The end card over the last shot: Second Look, "Take the two-minute test (about four minutes with its lesson)", the live link https://second-look-79t.pages.dev, the repository, "No camera needed." and "This video is CC BY-SA 4.0".
- A credits card with every footage credit, the two landing photos and the walk clip that the screen recordings show, and where the lesson and test photos are credited.
- Silence for sound: no scratch voice and no music, so there is no music licence to worry about.

It must run under 4:00, and `scripts/submit_check.py` wants at least 3 minutes. The script refuses to build a cut that is too long, and never puts a grey "missing" card in the final cut: if a clip, a screen recording or a credit is missing, it names it and stops.

## What it needs

- `ffmpeg` and `ffprobe` (Homebrew's are in `/opt/homebrew/bin`).
- The creek clips in `~/second-look-media/clips/`, made by `scripts/fetch_footage.py` and `scripts/cut_footage.py`.
- The screen recordings, made by `make video-clips` and never committed, each with its marks file. Record them as a judge sees the live site, from a build of the deployed commit whose API address is the live site's, served on a free port such as 3217:

  ```
  cd apps/web
  NEXT_PUBLIC_API_ORIGIN=https://second-look-79t.pages.dev NEXT_PUBLIC_SITE_URL=https://second-look-79t.pages.dev npm run build
  npx next start -p 3217 -H 127.0.0.1
  ```

  then, from the repository root, `SCREENS_URL=http://127.0.0.1:3217 SCREENS_API_ORIGIN=https://second-look-79t.pages.dev CLIPS_RAW=$HOME/second-look-media/screens/raw make video-clips`. The mock answers the live address, and the recorder refuses every other request that would leave the Mac, so no recording adds anything anywhere; the curl line on the record page shows the live address. The walk page plays its clip only if `apps/web/public/walks/` holds it before the build (`uv run python scripts/build_walks.py --clips-only`).

## Tests

`uv run pytest -q scripts/tests/test_video_final.py` checks the caption timing, the credits, the 4:00 limit and which voice file is used, with no ffmpeg. When ffmpeg is on the machine it also builds a tiny cut from made-up clips, first silent and then with a short tone standing in for the voice, both ways. It never uses a real voice. Another build checks that a short phone recording starts at its mark, holds its last frame, sits at the top at its full size and has the live link beside it. Other tests hold what a judge found in the first cut and what the audit of Sep 29 found in the second: the test is two minutes and about four with its lesson wherever it is timed, no caption points below the video, the check's words say the questions are the app's own, word for word, in six languages, and never draft, beat 11 is left out with its reason, and the caption box hides the page and keeps clear of the credit line and the phone page. It also fails when `SHOTLIST.md` has changed since `final_cut.json` was written, which means the cut is out of date: run `make video-final` again. `scripts/tests/test_video_beats.py` checks that every label `record-clips.mjs` clicks is still a button the app has (the app's answer words changed on Sep 26 and the recorder had not followed), and that the recorder never sets the browser's clock past a lock, so no recording shows judge mode open while it is shut.
