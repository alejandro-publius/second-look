# Video script

Superseded by `docs/video/SHOTLIST.md`, which is the one to follow. Nobody films at a creek any more: the creek shots are open footage from Wikimedia Commons (`docs/video/CREDITS.md`), and the person on camera became the check in a drawn phone frame (UPDATE_22 section 6).

DRAFT, written 2026-09-20 from the beats in the team's working notes (UPDATE 02) section 13. Target 3:45 (the organizers allow 3 to 5 minutes). One line of speech and one shot per beat, tied to real routes. Every number spoken on camera is read off the results file at recording time, never from this script. Record the sandbox beat (2:40) the day `/two` first works, because anyone can delete records there. No faces without a signed `docs/release_form.md`.

| Time | Speech (one line) | Shot | Route or source |
|---|---|---|---|
| 0:00 | "Which one is healthier?" (five seconds of quiet) | The two warm-up photos side by side, full screen. Then the answer appears under them. | `/` (landing, hook pair) |
| 0:20 | "Professional river surveyors must pass a test before their data counts. Some volunteer programs certify people for a method; none we know of measures how well each volunteer sees each feature and keeps it with every observation." | Screen capture of the River Habitat Survey manual line: only surveys from accredited surveyors are entered on the database. Cut to a volunteer's phone at a creek. | RHS manual page 20 (docs/notes/sources.md); B-roll from Strawberry Creek |
| 0:40 | "This is the two-minute version. Four things people miss, then sixteen photos." | Over the shoulder of a real person at Strawberry Creek taking the lesson and the first test items on a phone. Their hands and the phone; face only with a release. | `/t` (consent, warm-up, lesson, test) |
| 1:30 | "Untrained people, trained people and each model on the same sixteen photos. The counting rules were published before anyone took it." | The results table from the README, then the analysis plan with its tag and hash. Read the numbers off the screen. | README results table; `/how-we-know`; results/usability_<stamp>.json |
| 2:10 | "At the creek, the check asks one question at a time. And when it has not rained: is anything coming out of that pipe?" | The guided check on the phone, one question per screen, then the follow-up card: "It has not rained here for N days. Is anything coming out of that pipe?" | `/check` (form and follow-up) |
| 2:40 | "Every answer is stored beside the score of the person who gave it. As FHIR. Validated. Next to a lab result from their own sandbox." | The record: an answer beside "4 of 4 on built banks", the View as FHIR toggle with the validation badge, then the two-observer screen with the lab Observation and ours. | `/spot/[id]`, then `/two` |
| 3:10 | "This is what the score buys a city: an analyst sees who answered, not just what they answered." | The analyst's view of one spot. Each answer with its observer score beside it, then the toggle that keeps only people who passed that feature, then the follow-up the code asked when a low scorer answered No: a request for a photo. | /spot?id=example |
| 3:30 | "Any city can do this in OneAquaHealth's five steps for a follower city; we set them up for Berkeley, where no volunteer has taken the test yet. Take the test yourself." | The five steps on the README, then the landing page with the demo link, then the poster QR. | README, Feasibility section; `/`; `/poster` |
| 3:45 | (end card) | Project name, demo URL, repo URL, "No camera needed." | `/demo` |

## Recording notes

- Use `/demo?script=1` for any screen capture of the test flow. It runs a fixed, seeded path with the same photos every time, so retakes match shot for shot.
- The official app records foam and colour but has no smell item. Our quick check may ask about smell; the app does not. Do not say the app asks about smell.
- Say "audit log" if the hash chain comes up. Never "blockchain".
- If the lesson shows no effect, beat 1:30 says so in the same calm voice, and beat 3:10 shows whatever the chart shows.
- Sandbox line at 2:40 must stay true on the day: if the sandbox is down, the screen says so and shows ours alone. Say that instead.
