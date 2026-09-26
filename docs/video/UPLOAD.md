# Uploading the video

UPDATE_30 section 4 item 4. Everything needed to put the video on YouTube as unlisted and paste its link into `docs/devpost.md` and Devpost. Each paste field is one code block, so one tap copies it. `scripts/tests/test_video_final.py` fails if the description loses a credit or the licence line, or if a field gets too long for YouTube.

## Which file

`~/second-look-media/final/second-look-final.mp4`, built by `make video-final` ([`README.md`](README.md) in this folder).

- **No voice by the end of Sep 26 Pacific:** the captions only cut is the video (UPDATE_30 section 10). Upload it as it is.
- **The voice arrived:** put it in `~/second-look-media/voice/`, run `make video-final` again, and check that `docs/video/final_cut.json` says `"voice_used": true`.

Check the file before uploading:

```
ffprobe -v error -show_entries format=duration -of csv=p=0 ~/second-look-media/final/second-look-final.mp4
uv run pytest -q scripts/tests/test_video_final.py
uv run python scripts/submit_check.py --video ~/second-look-media/final/second-look-final.mp4
```

The first prints the length in seconds, which must be under 240. The second fails if the words changed after the cut was built; then build it again. In the third, the `video_duration` row passes; `video_link` and `repo_public` stay red until the link is pasted and the repository is public.

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

This video is released under CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/), because several of the creek clips in it are CC BY-SA. The creek footage and photos are not ours. They are openly licensed files, credited here, on screen while they play, and at https://second-look-79t.pages.dev/credits

Creek footage and photos, from Wikimedia Commons:
"StrawberryCreek3" by Coro, CC BY-SA 3.0: https://commons.wikimedia.org/wiki/File:StrawberryCreek3.JPG
"North Creek (Bothell, WA) 01" by Joe Mabel, CC BY-SA 4.0: https://commons.wikimedia.org/wiki/File:North_Creek_(Bothell,_WA)_01.webm
"Sonoma Creek - January 5 2023 - Sarah Stierch" by Missvain, CC BY 4.0: https://commons.wikimedia.org/wiki/File:Sonoma_Creek_-_January_5_2023_-_Sarah_Stierch.webm
"StrawberryCreek6" by Coro, CC BY-SA 3.0: https://commons.wikimedia.org/wiki/File:StrawberryCreek6.JPG
"FlorhamParkSewerageUtilityOutfall" by Z22, CC BY-SA 4.0: https://commons.wikimedia.org/wiki/File:FlorhamParkSewerageUtilityOutfall.webm
"StrawberryCreek9" by Coro, CC BY-SA 3.0: https://commons.wikimedia.org/wiki/File:StrawberryCreek9.JPG
"StrawberryCreek10" by Coro, CC BY-SA 3.0: https://commons.wikimedia.org/wiki/File:StrawberryCreek10.JPG
"Salmon River wood jam & side channel restoration project at Wildwood" by Bureau of Land Management Oregon and Washington, Public domain: https://commons.wikimedia.org/wiki/File:Salmon_River_wood_jam_%26_side_channel_restoration_project_at_Wildwood.webm
"StrawberryCreek8" by Coro, CC BY-SA 3.0: https://commons.wikimedia.org/wiki/File:StrawberryCreek8.JPG
"StrawberryCreek12" by Coro, CC BY-SA 3.0: https://commons.wikimedia.org/wiki/File:StrawberryCreek12.JPG
"Crows and Bagmati River" by Ashma Silwal, CC BY-SA 4.0: https://commons.wikimedia.org/wiki/File:Crows_and_Bagmati_River.webm
"Vincent Creek (33841689304)" by BLM Oregon & Washington, Public domain: https://commons.wikimedia.org/wiki/File:Vincent_Creek_(33841689304).webm
"Strawberry Creek Estuary Berkeley" by Awinch1001, CC0: https://commons.wikimedia.org/wiki/File:Strawberry_Creek_Estuary_Berkeley.jpg

Inside the app screens:
"Norman Creek as concrete channel" by Gregwadley, CC BY-SA 4.0, Wikimedia Commons: https://commons.wikimedia.org/wiki/File:Norman_Creek_as_concrete_channel.jpg
"Nurton Brook meander east of Pattingham, Staffordshire - geograph.org.uk - 6107365" by Roger Kidd, CC BY-SA 2.0, Wikimedia Commons: https://commons.wikimedia.org/wiki/File:Nurton_Brook_meander_east_of_Pattingham,_Staffordshire_-_geograph.org.uk_-_6107365.jpg
"Весенний ручей, Партизанский городской округ, 2017 г." by Красота Приморского края и не только, CC BY 3.0, YouTube: https://www.youtube.com/watch?v=vN5ArGGmdUY
The photos inside the lesson and the test are credited one by one at https://second-look-79t.pages.dev/credits

The thumbnail is the two creek photos above, by Gregwadley and Roger Kidd, and is CC BY-SA 4.0 too.
No music. No image or clip in this video was made by AI.
```

## Tags

```text
creek, stream, river, citizen science, volunteer monitoring, river habitat survey, stream restoration, urban creek, Strawberry Creek, Berkeley, OneAquaHealth, FHIR, AI evaluation, observer accuracy, open source, hackathon
```

## Thumbnail

[`docs/video/thumbnail.png`](thumbnail.png), a committed copy of `~/second-look-media/final/thumbnail.png`: 1280 by 720 and under 2 MB (642 KB), as YouTube asks. `make video-final` makes it from the two creek photos on the landing page, [`photos/warmup/ph-warmup-03.jpg`](../../photos/warmup/ph-warmup-03.jpg) (Norman Creek, by Gregwadley, CC BY-SA 4.0) on the left and [`photos/warmup/ph-warmup-04.jpg`](../../photos/warmup/ph-warmup-04.jpg) (Nurton Brook, by Roger Kidd, CC BY-SA 2.0) on the right, with the question "Which creek is healthier?" across the top and both credits along the bottom. It does not give the answer away.

YouTube only takes your own thumbnail from an account that is verified with a phone number (https://www.youtube.com/verify, one text message). If the account is not verified, pick the frame YouTube offers that shows the two creek photos on the phone.

## Upload to YouTube, unlisted

1. Open https://studio.youtube.com, signed in to the channel the video should live on.
2. Top right: **Create**, then **Upload videos**, then **Select files**. In the file window press Cmd+Shift+G, paste `~/second-look-media/final/second-look-final.mp4`, and press Return twice.
3. **Details**: paste the title and the description above. Under **Thumbnail**, **Upload file**, then Cmd+Shift+G and `~/second-look-media/final/thumbnail.png` (the same picture as `docs/video/thumbnail.png` in the repository). Under **Audience**, choose **No, it's not made for kids**.
4. Still on Details, **Show more**:
   - **Altered content**: **No**. Nothing in it is made or changed by AI to look real.
   - **Tags**: paste the tags above.
   - **Language**: English.
   - **License**: keep **Standard YouTube License**. Do not choose "Creative Commons - Attribution": that is CC BY, and this video must stay CC BY-SA 4.0 because of its CC BY-SA clips. The description carries the licence.
   - **Allow embedding**: ticked, so Devpost can show the video.
   - **Category**: Science & Technology.
5. **Next** past Video elements. On **Checks**, wait until it says no issues were found. The sound is silence or our own voice, so there is no music to be claimed.
6. **Next** to **Visibility**: choose **Unlisted**, not Private. A private video does not play for judges and fails the link check in `make done-check`. Copy the **Video link** shown there, `https://youtu.be/` and 11 letters. Press **Save**.
7. Only for the cut with a voice: in Studio's left menu, **Subtitles**, the video, **Add language**, English, then **Add** under Subtitles, **Upload file**, **With timing**, and `~/second-look-media/final/second-look-final.srt`. **Publish**. Skip this for the captions only cut: its captions are already on the picture, and a second set would sit on top of them.
8. Open the link in a private window (Safari: File, New Private Window), not signed in. It plays, the captions show, and it ends on the credits card. The 1080p version can take a few minutes after upload to appear under the gear icon.

## Paste the link

1. In `docs/devpost.md`, put the link in two places: the line that starts `Video: [VIDEO LINK]`, in place of `[VIDEO LINK]`, and the block under "Video link", in place of `[VIDEO LINK: paste the upload URL here on the day]`. Change that block's character count line to the link's length.
2. In `README.md`, add the video line under the live link, as the session report proposes.
3. Run `make submit-check`. The `video_link` row now passes. Then `uv run python scripts/done_items.py video-link`, which asks YouTube whether the video is really there.
4. Commit on `depth` with a message such as "The video's link, unlisted on YouTube".
5. On Devpost, open the project, **Edit project**, and paste the same link into the video demo link field. **Save**. Open the project page and check that the video shows and plays there.
