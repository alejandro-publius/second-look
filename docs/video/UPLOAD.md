# Uploading the video

Everything needed to put the video voiced by ElevenLabs on YouTube as unlisted and paste its link into `docs/devpost.md` and Devpost. Each paste field is one code block, so one tap copies it. `scripts/tests/test_video_words.py` checks that the description credits every photo and clip the video shows and says the voice is an AI voice. The first video's upload page is `docs/video/v1/UPLOAD.md`.

## Which file

`~/second-look-media/eleven-final/second-look.mp4`: 4:17 (257.9 seconds), 1920 by 1080, 30 fps, captions burned in. `second-look.srt` beside it holds the same captions as text.

Check it before uploading:

```
ffprobe -v error -show_entries format=duration -of csv=p=0 ~/second-look-media/eleven-final/second-look.mp4
uv run python scripts/submit_check.py --video ~/second-look-media/eleven-final/second-look.mp4
```

The first prints the length in seconds, which must be from 180 to 300. In the second, the `video_duration` row passes; `video_link` fails until the link is pasted.

## Title

```text
Second Look: a two-minute test of how well you see a creek
```

## Description

```text
A two-minute photo test that scores volunteer creek observers, then saves each score with every observation they make, as OneAquaHealth FHIR.

Take the test, no camera needed: https://second-look-79t.pages.dev
Code: https://github.com/alejandro-publius/second-look

Made for the OneAquaHealth hackathon, Track 3, AI-Supported Assessment.

Illustrations made with ChatGPT image generation. Narration voice by ElevenLabs. The narration is an AI voice, the ElevenLabs voice Sarah, reading words the team wrote. The slides are AI illustrations; the screens are recordings of the app, and where a recording shows sample records, made up for the video, the picture says so.

This video is released under CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/), because photos in it are CC BY-SA.

Inside the app screens:
"Norman Creek as concrete channel" by Gregwadley, CC BY-SA 4.0, Wikimedia Commons: https://commons.wikimedia.org/wiki/File:Norman_Creek_as_concrete_channel.jpg
"Nurton Brook meander east of Pattingham, Staffordshire - geograph.org.uk - 6107365" by Roger Kidd, CC BY-SA 2.0, Wikimedia Commons: https://commons.wikimedia.org/wiki/File:Nurton_Brook_meander_east_of_Pattingham,_Staffordshire_-_geograph.org.uk_-_6107365.jpg
"Весенний ручей, Партизанский городской округ, 2017 г." by Красота Приморского края и не только, CC BY 3.0, YouTube: https://www.youtube.com/watch?v=vN5ArGGmdUY
The photos inside the lesson and the test are credited one by one at https://second-look-79t.pages.dev/credits

The thumbnail is the two creek photos above, by Gregwadley and Roger Kidd, and is CC BY-SA 4.0 too.
```

## Tags

```text
creek, stream, river, citizen science, volunteer monitoring, stream restoration, urban creek, OneAquaHealth, FHIR, AI evaluation, observer accuracy, open source, hackathon
```

## Steps

1. Open studio.youtube.com, choose **Create**, then **Upload videos**, and pick `~/second-look-media/eleven-final/second-look.mp4`.
2. Paste the title and the description above. For the thumbnail, choose **Upload file** and pick `~/second-look-media/final/thumbnail.png`, the two creek photos.
3. Audience: **No, it's not made for kids**.
4. **Show more**. Altered content: choose **Yes**, because the narration is a synthetic voice; it adds a small label that matches the description. Tags: paste the tags above. Language: English. Licence: **Standard YouTube License**, because YouTube offers CC BY but not CC BY-SA; the description states CC BY-SA 4.0.
5. Skip the subtitles step: the captions are already in the picture, and a second copy would sit on top of them.
6. Visibility: **Unlisted**, then **Save**. Copy the link.
7. Paste the link over `[VIDEO LINK]` in `docs/devpost.md` (two places) and into Devpost's video field.
