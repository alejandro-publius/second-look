# Second Look: mammoth prompt 3 (the proofs, the kill tests, the decision points)

Recovered and saved on 2026-09-21 from docs/updates/UPDATE_07.md section 5, because prompt 3 was
never pasted into this terminal. Only the still-relevant parts are here, word for word.

Its old rule about building nothing before the proofs is void: the build exists.

### Proofs (P1, P2, P3)

**P1. A walking skeleton on the real host. Box: 60 minutes.** One static page, one API route that writes a row to the production database, one row read back. Deployed on the host you recommended. Report the URL, the time to first screen on a cold start, and what the host logs about visitors. Pass: it works over HTTPS on a phone and the first screen paints in under 3 seconds cold. Fail: pick another host now, before any screens exist.

**P2. Will their profiles accept a citizen record with an observer score? Box: 90 minutes.** This is the riskiest technical belief in the project, and so far only the FHIR Shorthand compiler has checked it, which checks structure and nothing else.
- Build their guide from the pinned commit with SUSHI 3.20.1.
- Write the smallest set of instances that carries the idea: the three nested Locations, the pseudonymous Practitioner with one qualification, one test QuestionnaireResponse with per-feature scores, one visit QuestionnaireResponse, two Observations under their Observation profile, one Provenance that links an Observation to both responses.
- Run the HL7 validator jar against our instances with their package loaded. If the terminology server cannot be reached, rerun with terminology checks off and say so.
- Report every error and warning on our instances word for word, grouped by resource.
- Pass: zero errors on our instances, or only errors we can fix on our side without inventing extensions. Fail: their profile itself rejects a citizen record (a required element we cannot honestly fill, a required binding our codes cannot meet, a performer type we cannot be). On fail, stop. Do not work around it. Write what blocks a citizen record in `docs/ig_gap_report.md`. That report becomes a contribution in its own right, and we take fallback F2.
- If the toolchain itself eats more than 45 minutes, stop and report what broke.

**P3. How do the models do on early photos? Box: 30 minutes and 1 dollar.** As soon as at least 8 labelled candidate photos sit in `photos/probe/` (Alex will drop them there, from his creek trip or openly licensed), ask each of the three models the feature question once per photo through the normal API. Print accuracy per feature and the notes they gave. This is a probe. It is never reported as the pre-specified test, and its photos are marked `role=probe` in the manifest. It tells us early which way the AI story leans: see F4.

### Tests Alex and Rachel run, no credits (K1 to K9)

For Alex. Type each result into the terminal in one line so it gets logged.

| Id | What it tests | How | Pass | Fail, and what we do |
|---|---|---|---|---|
| K1 | The opening hook | Send the two warm-up candidate photos to at least 10 people who do not study ecology and ask which creek is healthier. No hints. 10 minutes. | At most 6 of 10 pick the healthy one | 8 or more get it right: the pair is too easy. Find a harder pair. If three pairs fail, the hook becomes one photo and the question "what is wrong with this creek?" |
| K2 | The premise, roughly | 8 photos, one present and one absent per feature, in a free form tool. 6 to 10 friends. Every second person reads a one-page lesson first. 1 to 2 hours. These friends never take the real test. | People without the lesson average between 40 and 80 percent | Above 85 percent: the photos are too easy, get harder ones. Lesson readers no better at all, or confused by a question: rewrite that lesson or question before its screens are built. With this few people only a gross failure shows. Treat it as a smoke alarm, not a result. |
| K3 | Can each feature be photographed clearly | Today's creek trip. Try for 2 clear present and 2 clear absent per feature. | All four features | A feature with no clear photos by Monday night is filled from openly licensed photos or dropped. Dropping one means 12 test items, 4 per feature, written into the plan before the tag. |
| K4 | Can two people agree on the labels | Monday. Rachel and Alex label 12 candidate photos blind, 3 per feature, with `scripts/label_photos.py`. 30 minutes. | They agree on at least 10 of 12, and on at least 2 of 3 in every feature | A feature where they split is kept only with obvious cases, or dropped. The dug-out channel is the likeliest to fail: even trained surveyors find it hard to call. |
| K5 | Is the idea already taken | Today. Alex opens the OneAquaHealth Community training materials and watches their ten-minute AI image model video. 25 minutes. | They do not test volunteers, and their model does not already flag our four features in the app | They already test volunteers: the headline moves to the score travelling with the data and AI taking the same test. Their model already flags these features: our checker uses theirs as one more observer on the same test, if it can be reached, and says so. |
| K6 | Can we write to their sandbox | `scripts/sandbox_write_test.sh`. 2 minutes. | HTTP 201 | 401 or 403: fallback F2's display path (our own read-only endpoint, the validator output, the proposal page). |
| K7 | Rachel's hours | One message today: can she deliver photos and blind labels by Tuesday noon. | Yes | No: Alex shoots today, openly licensed photos fill the gaps, Rachel only labels and checks copy (about 2 hours). |
| K8 | Can we reach enough strangers | Post the K1 question as a poll in two or three group chats. Count replies after 24 hours. | 25 or more replies | Fewer: before Wednesday add posters, class announcements and creek groups, or accept that the result will be a description, not a test. |
| K9 | Does a stranger get it | Say the one sentence to three people outside tech and ask them to say back what it does. 5 minutes. | All three can | Rewrite the sentence until they can. The README and the video open with the version that passed. |

### Decision points

- **Launch decision, Tuesday Sep 22 at 22:00 PDT.** Go if P1 passed, K3 and K4 passed for at least three features, and `make preflight` is green. Otherwise do not launch a test we cannot stand behind. Take F1 and keep building the record.
- **Reach check, Thursday Sep 24 at 22:00 PDT.** Fewer than 20 completed sessions means the headline switches to F1 now, while collection continues to data lock. The switch is a change of emphasis in the README and video, never a change to the analysis plan.
- **Spend checks.** API spend above 150 dollars by Sep 23 or 350 dollars by Sep 26 means routine sessions drop to the cheaper model and nothing tagged COULD is built. If Alex reports his weekly usage limit above 90 percent before it resets, stop COULD and SHOULD work and ask him whether to move this terminal to API billing on the capped workspace.
- **Freeze, Saturday Sep 26 at night.** Whatever is not green is cut from the story, not patched on Sunday.

### Fallbacks

- **F1. The lesson shows no clear effect, or too few people came.** The headline becomes: the score travels with every observation, AI took the same test, and a citizen record sits validated in their own format. The test is reported exactly as it came out, small and honest. Track 3 still holds if the model run shipped. Nothing already built is wasted.
- **F2. Their profiles reject a citizen record, or the sandbox refuses writes.** The headline becomes the lesson and the test on strangers, entered in Track 1. The FHIR work ships as plain valid R4 plus `docs/ig_gap_report.md`, which tells the guide's authors exactly what stands between their profiles and the citizen parity they describe.
- **F3. A feature cannot be photographed or labelled reliably.** Three features, 12 items, written into the plan before the tag.
- **F4. The models ace the early photos.** The checker is described as a second pair of eyes that earned its place on the same test. The person still goes to the creek, because a model cannot smell the water, see the pipe behind the bush, or know that it has not rained. If the models fail everything, the README says where AI should stay quiet, which is also an answer the track asked for.
- **F5. The hook pair is too easy.** One photo and "what is wrong with this creek?".
