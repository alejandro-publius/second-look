# Voice script: 3:45 at about 150 words a minute

This supersedes the speech column of `docs/video_script.md` (the draft of Sep 20). Shots and routes follow that file and UPDATE_14 section 7. Read it with `docs/video/teleprompter.html`.

Rules for the words: plain, one idea per sentence, no number that is not in `results/` or the README. A slot in square brackets like `[SLOT: ...]` is a number that does not exist yet. Read it off the named file on the day you record, or cut the sentence. Never guess it.

Spoken words, slots counted as one word each: 559. Target 520 to 580.

| # | Time | Screen | Words |
|---|---|---|---|
| 1 | 0:00 | `/` landing: the two creek photos side by side, full screen. Hold 4 seconds before speaking. | Look at these two creeks. Which one is healthier? Take a second. Most people pick the tidy, green one. It has concrete banks and a pretty plant that does not belong there. The plain, messy one is doing better. |
| 2 | 0:15 | Strawberry Creek B-roll: a concrete bank, then a pipe in the bank. | Volunteers who check creeks make this mistake all the time. OneAquaHealth's project lead told us so. People catch smell, foam and colour. They walk past built banks, a channel that was dug out, and plants that do not belong. |
| 3 | 0:30 | The River Habitat Survey manual line on screen, from `docs/notes/sources.md`. | Professional river surveyors fixed this long ago. In the UK, a survey only counts if the surveyor passed a test. Volunteers have never had that. So a city cannot tell a careful observer from a hopeful one. |
| 4 | 0:45 | `/demo?script=1`: consent, then one lesson card with its marks. | Second Look is that test, in two minutes, on a phone. First, a short lesson on the four things people miss. Each card shows a real photo and marks the part that matters. A built bank. A dug-out channel. An invasive plant. A pipe running in dry weather. |
| 5 | 1:05 | `/demo?script=1`: three test items, Yes, No, Can't tell. | Then sixteen photos. For each one you answer yes, no, or can't tell. There are four photos for each of the four features. No camera needed. You can take it right now at the link below, on any phone or laptop. It takes about as long as making a cup of tea. |
| 6 | 1:25 | The end screen with the score per feature. | At the end you get a score for each feature, like four of four on built banks. Not a grade. Not a probability. Just how many you got right, and the date. |
| 7 | 1:40 | README results table, AI row by row. | We gave the same sixteen photos to AI models, with the same words, three times each. [SLOT: models that passed at least one feature, from results/model_pass_table.json] passed at least one feature. To pass a feature, a model has to get all four photos right in at least two of three runs. A model may only speak about a feature it passed. |
| 8 | 2:00 | `/how-we-know`, then `core/gate.py` in the editor for 2 seconds. | And even then, it never decides. The volunteer always answers first. The AI can only raise one follow-up question, and code chooses it. A test proves that the stored answers are always the human answers, whatever the model says. The AI is a second look, never the first. |
| 9 | 2:20 | `/check` at the creek on the phone, one question per screen, then the dry pipe follow-up card. | At the creek, the check asks one question at a time. It follows the official OneAquaHealth app. When it has not rained for days, it asks: is anything coming out of that pipe? Water in a pipe with no rain can mean sewage. That is worth a lab test. |
| 10 | 2:40 | `/spot?id=`: an answer beside "4 of 4 on built banks", then View as FHIR with the validation badge. | Every answer is saved beside the score of the person who gave it. The record is FHIR, under OneAquaHealth's own profiles. Our last validation run checked twelve files with zero errors. A city that already reads OneAquaHealth records can read ours. |
| 11 | 2:55 | `/two`: the lab Observation from their sandbox next to ours. | Here is a lab result from their sandbox, next to a volunteer's answer, in the same viewer. Both now carry a mark of how far to trust them. |
| 12 | 3:05 | `/city?creek=strawberry-creek`, then the health card on `/spot`. | For a city analyst, this means seeing who answered, not just what they answered. The creek page lists what it needs, in OneAquaHealth's own restoration measures. And the health card gives one action for you, one for your dog, and one for your city. |
| 13 | 3:25 | README Feasibility section, then `/poster` with the QR code. | Berkeley can do this with OneAquaHealth's five steps for a follower city. So can any other city. It costs nothing to run, and every step is written down in the repository. |
| 14 | 3:35 | End card: Second Look, the live link, the repo link, "No camera needed." | Take the two-minute test yourself. Then go and look at your own creek again. It might look different now. |

## Checks before recording

- Beat 7: open `results/model_pass_table.json` from the real run (it must say `"real": true`). If no model passed any feature, say: "None of them passed a feature, so none of them may speak." That is a finding, not a failure.
- Beat 10: the file count and zero errors come from `results/fhir_validation.json` (`files`, `errors`). Re-read both on the day; if they changed, say the new ones.
- Beat 11: record only when `/two` shows the sandbox record. If their sandbox is down, cut beat 11 and say nothing about it.
- Say "audit log" if the hash chain comes up. Never "blockchain".
- Word count: `uv run python -c "import re,pathlib;t=pathlib.Path('docs/video/VOICE_SCRIPT.md').read_text();rows=[l.split('|')[4] for l in t.splitlines() if re.match(r'\| \d+ \|',l)];print(sum(len(re.sub(r'\[SLOT:[^]]*\]','X',r).split()) for r in rows))"`
