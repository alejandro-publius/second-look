# Record at the creek

Thirty minutes at Strawberry Creek on the UC Berkeley campus, with a phone. Three beats of `docs/video/SHOTLIST.md` need creek footage: 0:15 (`02-creek-broll.mp4`), 2:20 (`09-check-at-creek.mp4`) and 3:35 (`14-end-card.mp4`, the shot behind the end card). Film more than the video uses, so the edit has a choice. This file takes in `docs/video/CREEK_30_MIN.md` from pull request #5: its places, its shots and its real creek check.

## Release form

Anyone who appears on camera, even only their hands, signs the release form first: `docs/release_form.md`. Print it and bring a pen. Follow every box they tick. If they tick "hands, the phone and the creek, and not my face", keep their face out of every frame. Keep the signed paper safe and out of the repo, because it has their name and signature on it. If you film alone, only your own hands, no form is needed.

## Before you go (at home, 2 minutes)

- Pick a day with no rain, so the pipe shot matches the dry weather question.
- Phone charged, storage free, lens wiped, Do Not Disturb on, airplane mode off (the check reads rainfall from Open-Meteo).
- Film sideways (landscape), 1080p, 30 frames a second, to match the screen clips. The app screen recording is upright.
- Open https://second-look-79t.pages.dev/check once, so the app is cached.
- Go in daylight, ideally mid-morning on a weekday, when fewer people are on the paths.

## Where to stand

Stay on paths and bridges. Do not step into the channel or onto planted banks: the restoration is fragile. In our region pack these are the reaches "South Fork, central campus" and "North Fork, campus".

- Faculty Glade, on the South Fork by the Faculty Club: open banks and rock, good light, easy for the calm shots.
- The Grinnell Natural Area and the Eucalyptus Grove, on the west side of campus near the Valley Life Sciences Building: built walls and channel sections that show a built bank.
- The west edge near Oxford Street, where the creek goes into a culvert: the strongest built channel on campus.

If a spot is closed or busy, move on. Any concrete wall, pipe outlet or straightened stretch you can film from a path will do.

## The shots

| # | Minutes | What to film | How | Clip file | For |
|---|---|---|---|---|---|
| 1 | 3 | A concrete or rock wall bank, slow pan along it | One slow pan, 10 seconds, then hold 5 | `02-creek-broll.mp4` | 0:15 |
| 2 | 3 | A pipe or outlet in the bank, from a bridge or path | Hold 10 seconds, camera still | `02-creek-broll.mp4` (second half) | 0:15 |
| 3 | 10 | One real creek check in the app, start to finish (below) | Screen recording on the phone; if someone is with you, they film your hands and the phone from over the shoulder | `09-check-at-creek.mp4` | 2:20 |
| 4 | 2 | The phone held up with the creek behind it, the check on screen | Hands only, 10 seconds | `09-check-at-creek.mp4` (cutaway) | 2:20 |
| 5 | 3 | Wide shot of the creek looking upstream, water moving, no people | Elbows braced on a rail, 15 seconds still, no zoom | `14-end-card.mp4` | 3:35 |
| 6 | 2 | Quiet water, close | 10 seconds, still | spare | any creek beat |
| 7 | 3 | The culvert near Oxford Street | Wide, 10 seconds, then a slow walk in | spare | any creek beat |
| | 4 | Play back every shot once. Redo anything that shook, or that shows a face, a plate or a house number | | | |

## The real creek check (shot 3)

1. Start the phone's screen recording, then open https://second-look-79t.pages.dev/check.
2. Place the pin yourself where you stand, so the location is exact and you chose it.
3. Answer every question from what you actually see. Do not stage anything. If the dry pipe follow-up appears, answer it truthfully.
4. At the end, open the record and tap View as FHIR once, so the badge is on the recording.
5. Stop the recording. Write down the record id from the address bar (`/spot?id=...`). The next session swaps this visit into the README's "See it work" table in place of the worked example.

## Rules at the creek

- No face of anyone who has not signed the release form. If people walk past, wait until they have gone, or point the camera away.
- No readable car plate (on the service roads and at the Oxford Street edge), house number, building number or door sign.
- No student ID cards, laptop screens or phone notifications in frame, including on your own screen recording.
- No AI filters, no beauty mode, no generated fill. Real footage only (hard rule 6).
- Stay on the path and the bank. Do not step into the water.
- Say nothing on camera about what is in the water or what comes out of a pipe. We never state a risk for a specific site.

## After (at home, 5 minutes)

- Copy the files to the laptop and rename them to the clip names above. They go in `docs/video/clips/`, which git ignores: a video file is never committed, whatever its size.
- Put the record id and the clip names in the status issue. The next session builds the cut.
