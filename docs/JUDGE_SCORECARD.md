# Our own scorecard, against the judges' rubric

We marked ourselves against each line of the rubric, with the weak spots written in. The marks are
words, not numbers, because they are our judgment and not a measurement. Every claim in the
"why" column points at something you can open or run.

| Rubric line (weight) | Our mark | Why | What pulls it down |
|---|---|---|---|
| Impact and alignment with the OneAquaHealth mission (30%) | strong | Every volunteer observation carries its observer's per-feature score, in their own FHIR profiles, validated against their guide at b907cf0 with 0 errors (`results/fhir_validation.json`). The city view speaks only in their own restoration measures from the Policy Brief, page 9. | No real creek visit has gone through the loop yet; the worked Strawberry Creek visit is an example. No recruited study, so no measured effect on volunteers. |
| Innovation and creativity (20%) | strong | A two-minute test, per feature, whose result travels with the data. The AI takes the same test as the people and may only raise a question where it passed; code, not the model, picks every question. Video walks let anyone run the full loop from a desk. | The idea of testing observers is old in professional surveys (the River Habitat Survey). What is new is doing it in two minutes, inside the flow, and storing it. |
| Technical implementation (20%) | strong | Python reference and a TypeScript Worker proved equal by golden vectors; the HL7 validator runs in CI on both; a hash-chained audit log; a read only MCP server; `make judge-check` runs offline with no key. See `docs/ACCEPTANCE.md`. | The AI results come from a model run that needs a key; until it runs, every AI number on the site says so. Footage labels come from video descriptions, and few descriptions name a feature. |
| Usability and user experience (15%) | partial | One question per screen, plain words at a reading age of about 12 (`make readability`), WCAG 2.2 AA checks and 44 px tap targets (`make design-check`), works offline and queues the check. | English only; the Spanish draft is unverified and out of the build. The form items are marked unverified against the official app until Alex checks screenshots. |
| Feasibility and scalability (15%) | strong | Runs on Cloudflare's free plan with no card. `make new-city` scaffolds a follower city in seconds (`docs/cities/TIMES.md`). A city that reads OneAquaHealth records reads ours, because they use its profiles. | The sandbox is shared and anyone can delete there, so the mirror is re-pushed on a schedule. One region pack (the Bay Area) is filled by hand. |

## The five things the organizers asked every submission to show

| What they asked for | Where it is |
|---|---|
| The problem | README, "The problem" |
| How the solution aligns with OneAquaHealth | README, "How OneAquaHealth is used" |
| Innovation and practical value | README, "Why trust a volunteer, and the AI?" |
| Effective use of data, technology, AI, APIs and standards | README, "Architecture" and "Evals" |
| A clear demonstration of what was built | README, "See it work", and `/judges` on the live site |

## The weaknesses, in full

They are listed once, in the README under "Known weaknesses", so this file and the README cannot
disagree.
