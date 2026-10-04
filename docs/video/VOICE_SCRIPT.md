# Voice script: the video voiced by ElevenLabs, 4:17

The words the ElevenLabs voice reads, one beat per row, the cover and then one beat per slide. They are the words in the "Words" column of `docs/video/SHOTLIST.md`, and `scripts/tests/test_video_words.py` fails if the two files ever differ, if a number in them stops matching the file it comes from, or if a word says what a pipe means. Alex wrote the words on Oct 4 and changed two the same day: beat 9 says "a good rating", as the app's best rating is "Good quality", and beat 13 says "Coming back takes a few taps." The first video, read by Alex, is kept in `docs/video/v1/`.

## How it is voiced

- Voice: Sarah (`EXAVITQu4vr4xnSDxMaL`), model `eleven_multilingual_v2`, stability 0.5, similarity 0.75, style 0.1: calm, warm and unhurried, with low style so it does not perform.
- Spoken forms only; the captions keep the written forms: FHIR is said "fire", OneAquaHealth "One Aqua Health", UK "U K". Numbers are written as words.
- Pauses: 1 second after both "Which creek is healthier?", half a second after "She gives it five stars.", 0.7 seconds before "Nobody checked whether they could see.", 0.8 seconds before "And look again." Each pause is silence between two separately voiced parts, so it is exact.
- Checked by machine: the voiced track was transcribed back to text with ElevenLabs speech to text and matched the words on 657 of 658 words, the one difference being "U K" heard as "UK"; beats 9 and 13, voiced again after their words changed, were transcribed again and match. A person listens to the whole cut before it is uploaded.

| # | Time | Slide | Words |
|---|---|---|---|
| 0 | 0:00 | Cover | This is Second Look. |
| 1 | 0:03 | Slide 1 | Picture a volunteer, Maya, at a creek in a city park. Joggers, benches, water catching the sun. She gives it five stars. She also walked straight past a concrete bank, and a pipe draining into the water. |
| 2 | 0:16 | Slide 2 | Now look at these two. The tidy one is a concrete channel. The messy one, with the fallen branches and the heron, is in a far more natural state. Tidy isn't the same as natural, but we judge creeks the way we judge parks. |
| 3 | 0:32 | Slide 3 | OneAquaHealth's project lead named these blind spots in the very first workshop: built banks, dug-out channels, pretty plants that don't belong. In the UK, a river surveyor's data doesn't count until they pass a test. A volunteer's always counted. Nobody checked whether they could see. |
| 4 | 0:52 | Slide 4 | So Second Look starts with one question. Which creek is healthier? No account. No name. No email. |
| 5 | 1:01 | Slide 5 | Then a two-minute lesson on the four things people miss. Concrete hiding under ivy. A channel dug straight and even. Plants that don't belong. A pipe in the bank. |
| 6 | 1:12 | Slide 6 | Then sixteen real photos with known answers. Yes, no, or can't tell. Pick, then press next. |
| 7 | 1:20 | Slide 7 | The score is per feature, not one grade. Maya caught every pipe, and missed half the invasive plants. That's worth knowing, for her and for anyone reading her reports. It travels with everything she sends for ninety days. |
| 8 | 1:34 | Slide 8 | At the creek, she gets the official OneAquaHealth app's own questions, word for word, in six languages, even with no signal. In this demo, the creek is real footage from an open video, checked from a desk. |
| 9 | 1:48 | Slide 9 | Then code, not AI, decides what to ask next. Nine days without rain, and she saw a pipe? Is anything coming out of it? A good rating, beside a concrete bank? Keep that rating? Two follow-ups, at most. |
| 10 | 2:03 | Slide 10 | And the AI? It sat the same sixteen-photo test as everyone else. Four models, three times each. Where a model failed a feature, it stays quiet. Where it passed, it may ask one question, and only after you've answered. It can ask you to look again. It can never answer for you. On real creek footage, the gate stopped twenty-nine of sixty-four flags. |
| 11 | 2:28 | Slide 11 | Every check becomes a FHIR record in OneAquaHealth's own data standard, with zero validation errors. And every answer carries the score of the person who gave it. A lab result never travels without its calibration. Now a volunteer's answer doesn't either. |
| 12 | 2:45 | Slide 12 | For the city, the records become a short list. What this creek needs, in OneAquaHealth's own restoration measures. And which pipes are worth testing: a pipe makes that list only when two contributors who passed the pipe questions saw it running in dry weather. The lab result coming back is an example of how that loop closes. |
| 13 | 3:04 | Slide 13 | Coming back takes a few taps. One visit is a snapshot. Repeated visits make a story, and a report upstream shows up on the stretch below it. |
| 14 | 3:14 | Slide 14 | Any OneAquaHealth system can read these records, and so can an AI assistant, with the evidence attached. Along the way, we found fourteen places where the app's own translations ask something different from the English. The Italian pipe question asks about rainwater. We wrote them all up for the organizers. |
| 15 | 3:34 | Slide 15 | None of this rests on our word. The study plan was locked and timestamped before anyone took the test. Every number you've seen is checked by code. And when our own idea for weighting votes failed in simulation, we cut it, and said so. |
| 16 | 3:49 | Slide 16 | Any city can run it. It's free to host, works offline, and follows OneAquaHealth's own steps for bringing on a new city. |
| 17 | 3:58 | Slide 17 | Second Look isn't a better way to collect observations. It's a way to know which ones to believe. Which creek is healthier? Take the two-minute test. And look again. |

## Where each number comes from

The test reads each of these files and fails if the number in the words stops matching it.

- sixteen photos: `content/test_items.yaml`, its items.
- ninety days: `core/records.py`, `SCORE_VALID_DAYS`.
- six languages: `content/app_strings.json`, `languages`.
- two follow-ups, at most: `core/followups.py`, `DEFAULT_MAX_QUESTIONS`.
- four models, three times each: `results/model_pass_table.json`, its models and their runs.
- twenty-nine of sixty-four flags: `results/footage_latest.json`, `gate.dropped` and `gate.candidates`.
- zero validation errors: `results/fhir_validation.json`, `errors`.
- two contributors who passed: `core/act.py`, `PIPE_OBSERVERS_NEEDED`.
- fourteen places: `content/app_strings.json`, the entries under `fallback`; the Italian pipe question is `fallback.it["draining_pipes.text"]`.

## Words no file stands behind

- "Nine days without rain" is an example. The follow-up on screen in beat 9 is recorded with nine dry days so the two agree.
