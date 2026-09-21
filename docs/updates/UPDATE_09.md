# Second Look: mammoth prompt 9 (one person can launch, on Cloudflare)

This replaces prompt 8. Start a fresh window with `cd ~/second-look && claude`, then paste this whole text. Everything below is addressed to Claude Code.

Read `CLAUDE.md`, `PLAN.md` and `docs/HANDOFF_NEXT.md` first, and nothing else yet. Save this text as `docs/updates/UPDATE_09.md`. Where it disagrees with earlier files, this one wins. Two subagents at most. The freeze on extras and on stage 2 of the design pass stands. Work in section order. At the end write the report, copy the full file to the clipboard with `pbcopy`, print the report block, and stop.

## 1. One person can launch

Alex is building this and must be able to clear every gate himself. Rachel contributes when and where she chooses. Nothing waits on a named person any more.

- Every gate, flag and TODO that names Rachel becomes a team gate. `TODO-RACHEL` becomes `TODO-TEAM`. Any team member can approve wording, lesson copy, marks, plant lists and sentences. The approval stamps who and when.
- Labels. The gold label comes from the first team member who labels a photo. A second label is welcome and optional. If every test photo has two labels by the tag, report Cohen's kappa. If not, the plan and the README say plainly that one person set the key, and list it under Known weaknesses. Preflight no longer fails on a missing second label. It prints it as a note.
- Label evidence. Add `label_evidence` to the manifest: where the source itself supports the label, record it (a research grade species identification, a caption that says the channel is concrete lined, a category name). For plants, the species must also be on the Cal-IPC inventory, with the link.
- Question wording. Use the official app's own wording where the app asks about the feature, and our own for the dug-out channel. Alex freezes it.
- Health and ecology sentences. Any team member approves them. Each needs a source that person has opened. Nothing states a risk for a specific site. Try to fetch the two OneAquaHealth Zenodo records (10.5281/zenodo.20345207 and 10.5281/zenodo.20344421). If they open, put the definitions that matter to our sentences in `docs/notes/zenodo.md` with page references, so approving takes minutes.
- Rewrite `docs/rachel_pack.md` as `docs/team_pack.md`: what helps most, in order, for whoever has an hour. Rewrite the "needed from humans" list the same way. Regroup the preflight output by what clears it, not by who.
- Update `docs/analysis_plan.md` section 3 to match: labels are set by a team member blind to any model output; a second labeller is reported when present.

## 2. Hosting: Cloudflare, no new accounts, no payment method

Alex already has a Cloudflare account and has deployed with wrangler before. Vercel and Fly.io are dropped. Nothing in this project may need a card.

- Run `npx wrangler whoami`. If it is not logged in, build everything anyway and end the report with the one command Alex has to run.
- Web. Try a static export of the Next app to Cloudflare Pages first. It never sleeps and has no bundle limit to fight. Dynamic routes become query routes or client-rendered pages, the share card becomes a build-time image or one small function, and the security headers move to a `_headers` file with the same strict policy. If the static export costs more than 60 minutes, switch to the OpenNext adapter for Cloudflare Workers, and check the free plan's Worker size limit before going further.
- API. Keep the tested Python code. First choice: a Cloudflare Python Worker that runs our FastAPI app and `core/` as they are, with a D1 storage adapter behind the same storage interface the SQLModel code uses. D1 on the free plan. Photos from the creek check go to Workers KV after downsizing, because R2 asks for a card. Box: 90 minutes. If Python Workers fight back, port only the study endpoints (session, response, lesson-done, complete, resume, counts, export) to a small TypeScript Worker on D1, and prove it matches by running the same contract tests against both implementations. The judge-facing endpoints can follow after launch.
- The rate limit must never store an address. If that cannot be done cleanly on Workers, rely on the hidden field and the 40 second rule, and say so in `docs/DATA_HANDLING.md`.
- Cloudflare keeps its own edge logs, which we do not control. Write what they hold in `docs/DATA_HANDLING.md` and make the consent text match.
- Backups: a daily `wrangler d1 export`, from a scheduled GitHub Action with a narrowly scoped token, kept as a private artifact. Run one restore drill.
- P1's pass line is unchanged: a public URL over HTTPS that works on a phone, the first screen in under 3 seconds cold, one row written and read back. Report the URL, the cold-start number and what is logged. Then deploy the full app behind the `is_test` key and run the phone end-to-end tests against the deployed URL.
- If both API paths fail inside their boxes, stop and report exactly what broke. Do not switch to a host that needs a card.

## 3. Photos: run the search now

Do not wait for a trigger. Alex picks photos in the evenings, so he needs candidates tonight.

- `scripts/find_open_photos.py <feature>` queries the Wikimedia Commons API and the iNaturalist API (research grade, photo licence CC0, CC BY or CC BY-SA, California first for plants) with a named user agent and one request per second. It writes `photos/candidates/<feature>.html`: a local contact sheet with a thumbnail, the source link, the author, the licence, and the source's own caption or identification. Nothing is downloaded into the repo and the sheets are never deployed.
- Run it for all four features and for the warm-up pair. Aim for at least 40 candidates per feature, present and absent, including the look-alikes from the shot list. Search terms are yours to choose. Start from: concrete lined channel, channelized stream, retaining wall creek, riprap, natural stream bank; straightened channel, trapezoidal channel, meandering stream, riffle pool; Arundo donax, Hedera helix, Rubus armeniacus, Vinca major, Cortaderia, and native willow and alder for the absent side; storm drain outfall, culvert outfall, dry outfall, seep.
- `scripts/fetch_open_photo.py <url> --feature <id> --role <role>` downloads one chosen photo, runs it through ingest, and writes the manifest row with the author, the licence, the source and the label evidence.
- You do not open images and you do not label them. People pick and people label.
- Team photos from a creek trip go through the same ingest whenever they arrive. Both sources can mix, as long as no lesson photo shares a scene with a test photo.

## 4. Decisions carried over from the three reports

1. **Alex's kill tests, in order:** K5, then K9, tonight. K3 and K4 as soon as photos are picked. K1 and K8 once the warm-up pair exists. K2 is folded into the dry run with three friends. K7 is closed: the team works in parallel and nothing waits on it. Update `docs/KILL_TESTS.md`.
2. **Marks** are approved once per lesson photo by any team member, on one review page in the marking tool: the photo with its marks drawn on it, Approve or drag to move. Changing a mark later resets that photo's approval. Lesson content freezes at the `prereg-v1` tag with the test key. A change after the tag is a deviation.
3. **Laid stone counts as a built bank.** The River Habitat Survey treats it as reinforcement. No laid stone photo goes into the test set, because the official app gives it a category of its own. The form keeps the app's three bank types and calls none of them natural. Mark it `TODO-TEAM-CONFIRM`.
4. **The consensus claim leaves the headline.** The planner simulated it. The rule in Update 02 is biased on a set this small: a person with 3 of 4 correct gets a low weight on the three they got right and the highest weight on the one they got wrong. With that fixed by scoring on one half of the photos and voting on the other, four photos per feature is still too coarse, and a plain majority beat every weighted scheme across five skill patterns. The only thing that helped was setting aside people who score near chance overall, and only when about a third of people tap at random. So:
   - Replace the section "Consensus with and without scores" in `docs/analysis_plan.md` with this, word for word:

   > Exploratory, run after lock, reported as description only, and kept off the README's first screen and out of the video: does leaving out low scorers change what a group gets right? The 16 items are split at random into two halves with two items of each feature in each half (seed 20260920, 200 splits). A person passes a half with 6 or more of its 8 items correct. For random groups of 5 within an arm (2,000 draws), the group answers each item of the other half by plain majority, once using everyone and once using only the people who passed the first half. When nobody passed, or the passers tie, the group falls back to everyone. We report the share of items each version gets right. Our own simulation before launch says four photos per feature is too coarse to weight votes by feature, and that this filter helps only when a fair share of people answer at random. We publish what we find.

   - Change `evals/consensus.py` to that method, with synthetic tests: the filter helps when a third of people answer at random, does not help with equal skill, and falls back when nobody passes.
   - Take the consensus beat out of `docs/video_script.md`. In its place: the analyst's view, answers beside scores, the toggle, and the request for a photo when a low scorer answers No.
   - Remove any sentence that says scores improve a group's answer. Under Known weaknesses add: "Four photos per feature is a coarse measure. It is enough to show a person what to practise and to flag an answer worth a second look. It is too coarse to weight votes with, and our own simulation says so. The score sharpens each time a person retakes the test on new photos."
5. **Judge mode teaches the answers, so it stays shut until lock.** `/demo` gives feedback on the same sixteen photos. Until the lock constant passes it shows one plain page, "Judge mode opens on Sep 28", and loads no photos. After lock it runs as built. Test both sides of the lock.
6. **Two front doors.** `/` is for participants: the wordmark, About, and nothing else in the navigation. `/judges` is for judges: take the test, check a creek, a sample record with View as FHIR, the two observer screen, how we know it works, the repo. The README and the Devpost page link to `/judges`.
7. **Small things.** Lead `docs/ig_proposal.md` with your two caveats, because they are the proposal: their guide has no profile for the person or for the trail from an answer to whoever gave it, and we used a pseudonymous Practitioner because Observation.performer has no better fit for a citizen. Ask its authors plainly which resource should stand for a citizen observer. Before any paid model run, fetch the current models and pricing pages and write the ids, prices and date checked into `docs/notes/model_ids.md`. Add to Known weaknesses that every photo comes from one season or from open collections.

## 5. Report

Include: which hosting path won and why, the P1 numbers or exactly what blocked them, the contact sheet paths with how many candidates each holds, the regrouped preflight count, the new consensus test results on synthetic data, proof that `/demo` is shut before lock and open after, and the `make check` line.
