# Shot list: the video voiced by ElevenLabs, 4:19

What is on screen under each beat of `docs/video/VOICE_SCRIPT.md`. The "Words" column is the same words, and `scripts/tests/test_video_words.py` fails if they differ. The first video, read by Alex over open creek footage, is kept in `docs/video/v1/` with its own shot list.

## How it is built

- Slides 01 to 17 are the team's, trimmed of their white borders. Each holds 8 to 12 seconds with a slow push in; a beat that runs longer goes on to a recording of the app. Slides 13 to 17 are wide strips, panned panel by panel.
- The recordings come from `apps/web/scripts/record-eleven.mjs`, at a human pace, against a local build of `main` and the mocked API, so no recording stores a sitting, a visit or a check anywhere. The build is made with `NEXT_PUBLIC_API_ORIGIN` set to the live site, so a curl line on screen shows the live address, and the mock answers that address.
- Each recording shows what its words say: the score screen has every pipe caught and half the invasive plants missed; the check is answered with an artificial bank, a Good rating and a pipe, so both follow-ups the words name appear.
- The record and the city page show the mock's sample records, so a note on screen says "Sample records, made up for this video." The live city page stays empty until the first real check.
- Beside a phone recording: "Try it now: second-look-79t.pages.dev". Captions are burned in, in the written forms, a sentence at a time, and `second-look.srt` is written beside the video.
- One file, 1920 by 1080, 30 fps, 4:19: the cover, the 17 beats and a credits card.

| Time | Slide | Then on screen | Words |
|---|---|---|---|
| 0:00 | Cover |  | This is Second Look. |
| 0:03 | Slide 1 |  | Picture a volunteer, Maya, at a creek in a city park. Joggers, benches, water catching the sun. She gives it five stars. She also walked straight past a concrete bank, and a pipe draining into the water. |
| 0:16 | Slide 2 | From 0:09 into the beat, for 6 seconds: `/`: the two creek photos and the question, then a tap on one. | Now look at these two. The tidy one is a concrete channel. The messy one, with the fallen branches and the heron, is in a far more natural state. Tidy isn't the same as natural, but we judge creeks the way we judge parks. |
| 0:32 | Slide 3 | From 0:09 into the beat, for 10 seconds: `/t`: the first lesson cards, each a real photo with the part that matters marked. | OneAquaHealth's project lead named these blind spots in the very first workshop: built banks, dug-out channels, pretty plants that don't belong. In the UK, a river surveyor's data doesn't count until they pass a test. A volunteer's always counted. Nobody checked whether they could see. |
| 0:52 | Slide 4 |  | So Second Look starts with one question. Which creek is healthier? No account. No name. No email. |
| 1:01 | Slide 5 |  | Then a two-minute lesson on the four things people miss. Concrete hiding under ivy. A channel dug straight and even. Plants that don't belong. A pipe in the bank. |
| 1:12 | Slide 6 |  | Then sixteen real photos with known answers. Yes, no, or can't tell. Pick, then press next. |
| 1:20 | Slide 7 | From 0:08 into the beat, for 6 seconds: `/t`: the end screen, 4 of 4 on pipes and 2 of 4 on plants that do not belong, with the score kept for the next 90 days. | The score is per feature, not one grade. Maya caught every pipe, and missed half the invasive plants. That's worth knowing, for her and for anyone reading her reports. It travels with everything she sends for ninety days. |
| 1:34 | Slide 8 | From 0:08 into the beat, for 6 seconds: `/walk/v02`: a video walk on open footage of a creek in Russia, its credit under the clip, then the first question in the app's own words. | At the creek, she gets the official OneAquaHealth app's own questions, word for word, in six languages, even with no signal. In this demo, the creek is real footage from an open video, checked from a desk. |
| 1:48 | Slide 9 | From 0:08 into the beat, for 6 seconds: `/check`: the two follow-ups after Send. No rain for 9 days and a pipe reported, answered Yes; then a Good rating beside artificial banks, answered Keep my rating. | Then code, not AI, decides what to ask next. Nine days without rain, and she saw a pipe? Is anything coming out of it? A very good rating, beside a concrete bank? Keep that rating? Two follow-ups, at most. |
| 2:04 | Slide 10 | From 0:10 into the beat, for 14 seconds: `/how-we-know`: down through "AI on the same test", the pass table and the gate on real footage. | And the AI? It sat the same sixteen-photo test as everyone else. Four models, three times each. Where a model failed a feature, it stays quiet. Where it passed, it may ask one question, and only after you've answered. It can ask you to look again. It can never answer for you. On real creek footage, the gate stopped twenty-nine of sixty-four flags. |
| 2:28 | Slide 11 | From 0:08 into the beat, for 10 seconds: `/spot?id=example`: View as FHIR, the validator badge and the curl line with the live address. A note on screen: "Sample records, made up for this video." | Every check becomes a FHIR record in OneAquaHealth's own data standard, with zero validation errors. And every answer carries the score of the person who gave it. A lab result never travels without its calibration. Now a volunteer's answer doesn't either. |
| 2:46 | Slide 12 | From 0:08 into the beat, for 11 seconds: `/city?creek=strawberry-creek`: Pipes worth testing, then Show how a result would come back, which the page marks as an example. A note on screen: "Sample records, made up for this video." | For the city, the records become a short list. What this creek needs, in OneAquaHealth's own restoration measures. And which pipes are worth testing: a pipe makes that list only when two contributors who passed the pipe questions saw it running in dry weather. The lab result coming back is an example of how that loop closes. |
| 3:05 | Slide 13, a wide strip, panned panel by panel |  | Coming back takes twenty seconds. One visit is a snapshot. Repeated visits make a story, and a report upstream shows up on the stretch below it. |
| 3:15 | Slide 14, a wide strip, panned panel by panel |  | Any OneAquaHealth system can read these records, and so can an AI assistant, with the evidence attached. Along the way, we found fourteen places where the app's own translations ask something different from the English. The Italian pipe question asks about rainwater. We wrote them all up for the organizers. |
| 3:35 | Slide 15, a wide strip, panned panel by panel |  | None of this rests on our word. The study plan was locked and timestamped before anyone took the test. Every number you've seen is checked by code. And when our own idea for weighting votes failed in simulation, we cut it, and said so. |
| 3:50 | Slide 16, a wide strip, panned panel by panel |  | Any city can run it. It's free to host, works offline, and follows OneAquaHealth's own steps for bringing on a new city. |
| 3:59 | Slide 17, a wide strip, panned panel by panel |  | Second Look isn't a better way to collect observations. It's a way to know which ones to believe. Which creek is healthier? Take the two-minute test. And look again. |
| 4:12 | Credits card | The live link, the code link, every credit below, the voice, and "This video is CC BY-SA 4.0." | |

## Credits: what the video shows that is not ours

- "Norman Creek as concrete channel" by Gregwadley, CC BY-SA 4.0, and "Nurton Brook meander east of Pattingham, Staffordshire" by Roger Kidd, CC BY-SA 2.0, both from Wikimedia Commons: the two creek photos on the landing page and the score screen.
- The creek walk clip: "Весенний ручей, Партизанский городской округ, 2017 г." by Красота Приморского края и не только, CC BY 3.0, from YouTube, as `content/walks.yaml` records it.
- The photos inside the lesson and the test: credited one by one at second-look-79t.pages.dev/credits.
- The narration: the ElevenLabs voice Sarah, reading the team's words.
