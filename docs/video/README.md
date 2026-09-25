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
make video-final
```

It writes `~/second-look-media/final/second-look-final.mp4`, the captions beside it as `second-look-final.srt`, the YouTube thumbnail as `thumbnail.png`, and the summary to `docs/video/final_cut.json`. It prints the file, its length and its size. If the screen recordings are in another checkout, say where: `make video-final SCREENS=~/second-look-depth/docs/video/clips`.

**2. With the voice, when it arrives:** save the recording as `~/second-look-media/voice/voice.m4a` (or `voice.wav`, or `voice.mp3`; if there are several, m4a wins, then wav), then run the same command again:

```
make video-final
```

The voice takes over the timing from the captions. It fits one of two ways, and `final_cut.json` says which in `voice_fit`:

- **each beat**, when `~/second-look-media/voice/voice_beats.txt` is there too. It has one line per beat, 14 lines, each starting with the second that beat's words start in the recording. An Audacity label export works as it is: only the first number on each line is read. Each beat gets its own stretch of the voice. A beat keeps its shot list length, or grows if its words take longer.
- **whole voice**, when there is no `voice_beats.txt`. The recording plays straight through from the first words, after skipping any quiet at its start. Each beat is cut to where its words should fall, by its share of the script's letters. This is the one to use if the recording is one take read at an even pace.

With a voice, the captions are no longer drawn on the picture. They go into the mp4 as an English subtitles track, and the `.srt` beside it is the file to upload to YouTube. If the cut with the voice would run 4:00 or longer, nothing is built and the message says by how much: trim the pauses and run it again. Take the voice file out of the folder to go back to the captions only cut.

**For a review:** `make video-frames` saves one frame every 10 seconds of the built cut, named by the second (`frame_000.png`, `frame_010.png` and so on), in `~/second-look-media/final/frames/`, or in `FRAMES=/another/folder`.

## What is in the cut

- The words of each beat from `SHOTLIST.md`, the same words as `VOICE_SCRIPT.md`, drawn as captions a sentence or two at a time, two lines at most, above the footage credit. They are spread over the beat by their length. No caption asks for faster reading than 17 letters a second: a beat whose words need longer runs longer than the shot list says.
- The opening shot plays with no words, as the shot list says.
- Every creek clip keeps the credit line `scripts/cut_footage.py` drew in its lower left corner: title, author, licence, Wikimedia Commons. So each credit is on screen while its footage plays.
- The end card over the last shot: Second Look, the live link https://second-look-79t.pages.dev, the repository, "No camera needed." and "This video is CC BY-SA 4.0".
- A credits card with every footage credit, the two landing photos and the walk clip that the screen recordings show, and where the lesson and test photos are credited.
- Silence for sound: no scratch voice and no music, so there is no music licence to worry about.

It must run under 4:00, and `scripts/submit_check.py` wants at least 3 minutes. The script refuses to build a cut that is too long, and never puts a grey "missing" card in the final cut: if a clip, a screen recording or a credit is missing, it names it and stops.

## What it needs

- `ffmpeg` and `ffprobe` (Homebrew's are in `/opt/homebrew/bin`).
- The creek clips in `~/second-look-media/clips/`, made by `scripts/fetch_footage.py` and `scripts/cut_footage.py`.
- The screen recordings in `docs/video/clips/`, made by `make video-clips`. They are not committed.

## Tests

`uv run pytest -q scripts/tests/test_video_final.py` checks the caption timing, the credits, the 4:00 limit and which voice file is used, with no ffmpeg. When ffmpeg is on the machine it also builds a tiny cut from made-up clips, first silent and then with a short tone standing in for the voice, both ways. It never uses a real voice. It also fails when `SHOTLIST.md` has changed since `final_cut.json` was written, which means the cut is out of date: run `make video-final` again.
