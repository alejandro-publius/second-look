# The panel study: 80 strangers, paid by a research panel

For Alex, about 15 minutes, by Saturday Sep 26 in the evening (UPDATE_29 section 1). Everything
below goes into the panel's study form as written. Nobody is recruited by us: the panel shows the
study to its own members, pays them, and checks the completion code. The analysis plan was tagged
before any participant (`prereg-v1`), and every session that ends before the data lock,
2026-09-28T01:00:00Z, is in the one pre-registered analysis.

## The steps

1. Make an account at Prolific (https://www.prolific.com), as a researcher, and add funds: about
   450 dollars covers 80 people at the reward below plus the panel's fee, with room to spare.
2. Create a new study and fill it from the fields below.
3. The ethics question, in one minute. The panel asks whether the study has ethics approval, an
   exemption, or needs none. What is true, and what you can say in the box: it is a usability test
   of our own training tool; it is anonymous, with consent on the first screen; it stores no name,
   email, IP address, free text or other identifier; nothing about it is clinical or sensitive;
   and the analysis plan was tagged and timestamped before any participant. Pick the option that
   matches your own situation: if you run it as a team building a tool, not as university research,
   and your panel's terms allow that, say no review is required and give those reasons; if you run
   it as a student under a university whose rules call a paid study human subjects research, it
   needs that review first, so do not launch, and the analysis reports whatever arrived through the
   public link.
4. Publish it. The study runs itself. Watch it with `make panel-status`.
5. Before you approve any payment, compare the number of completion codes the panel shows as
   submitted with the completed `panel` sessions that `make panel-status` prints. The code is the
   same for everyone and is visible in the page source, where anyone can read it, so a code alone
   does not prove a finished session. The analysis counts only finished sessions. If the panel
   shows more codes than finished sessions, stop and look before you approve: the extra codes did
   not come from a finished test.

## The fields

| Field | What to put |
|---|---|
| Study title | Which creek is healthier? A two-minute photo test |
| Description for participants | You will see photos of creeks and say, for each one, whether you can see one thing: a built bank, a dug-out channel, a plant that does not belong, or a pipe. Some people get a short lesson first. After your score you are offered an optional second block of eight more photos, where a checker may ask you to look again. It takes about 8 minutes with the second block, needs no camera, and works on a phone or a laptop. The completion code to paste back here is shown after your score if you skip the second block, and at the end of the second block if you take it. The test is anonymous: we store your answers and timings, never your name, your panel id or your address. |
| Link to the study | `https://second-look-79t.pages.dev/t?src=panel` |
| Panel's own id in the link | Leave it off (on Prolific: do not add URL parameters). If it is on, the site removes it from the address before anything is stored or sent, and keeps only `src=panel`. |
| Estimated time | about 8 minutes (about 5 without the optional second look) |
| Reward | 2.40 dollars (about 18 dollars an hour at about 8 minutes, the same rate as before), which is above the minimum hourly rate the panel shows when you set a reward. If the panel's minimum is higher on the day, use the minimum. |
| Places | 80 completed sessions |
| Who may take part | Adults (18 or older), fluent in English |
| Devices | Phone, tablet or laptop: all work |
| Completion code | `SLCREEK26`, the same code in two places: after the score, for everyone, and again at the end of part 2, the second look, for those who take it. Only for this link. |

## What a participant sees

The same test as everyone, with two differences only for this link: one more sentence on the
consent screen, "You are taking part through a research panel and will be paid by the panel;
nothing that identifies you is stored here." (the wording of UPDATE_29 with one word made exact, `docs/deviations.md`), and the completion code after the score. The test itself, its
photos, its questions and its scoring do not change (`docs/deviations.md`, 2026-09-24).

After the score, one line offers part 2, the second look: "Eight more photos, two minutes, and this
time a checker may ask you to look again." It is optional. Half of those who start it, at random,
meet the checker's question when the checker disagrees with their answer; the other half answer the
same eight photos with no question (`docs/analysis_plan_v2.md`, tag `prereg-v2`). The completion
code is on the score screen already, so a person who skips part 2 has it, and it is shown again at
the end of part 2.

## What is stored

What the privacy page and the analysis plan list: a random session id, the group, the answers,
the timings, a hash of a random token the browser makes, the device class, the consent version,
and the source label `panel`. Nothing from the panel's link but `src` is stored or sent: the site
rewrites the address before anything reads it (`apps/web/lib/session.ts`, tested in
`apps/web/tests/panel.spec.ts`), and the service worker keeps a page in the phone's cache under its
path and `src` only (`apps/web/public/sw.js`). One honest limit: the browser's first request for the page carries
the whole link the panel used, so if the panel adds its own id, Cloudflare's edge sees that one
request as any host would (`docs/DATA_HANDLING.md` says what the host logs).

## Watching it

`make panel-status` prints completed sessions by source and by arm from the public counts
endpoint, `https://second-look-79t.pages.dev/api/test/counts`, which leaves test sessions out.
It also prints part 2 by arm: started, finished and declined, from
`https://second-look-79t.pages.dev/api/t2/counts`.

## After the data lock

On Sep 28, after 2026-09-28T01:00:00Z, a session runs the pre-registered analysis once, exactly as
tagged, and the README's human row reports what it shows, whatever that is. If the panel was not
launched, the row stays as it is and says so.

The same job then runs the part 2 analysis once, as tagged in `prereg-v2`, and the README's second
human row reports it, or says that too few finished part 2.
