# The panel study: 80 strangers, paid by a research panel

For Alex, about 15 minutes, on Tuesday Sep 29, 2026, at or after 21:00 PDT (UPDATE_33 item 4;
first written for UPDATE_29 section 1). Everything below goes into the panel's study form as
written. Nobody is recruited by us: the panel shows the study to its own members, pays them, and
checks the completion code.

This is the second wave of the study (`docs/analysis_plan_v3.md`, tag `prereg-v3`). Nobody took
part before the first lock, 2026-09-28T01:00:00Z, and the deadline moved to Sunday Oct 4 at 21:00
PDT, so the same test runs a second time with the same design and the same analysis.

## The window

| What | Pacific time | UTC |
|---|---|---|
| The wave opens. Do not publish before this | Tue Sep 29, 21:00 PDT | 2026-09-30T04:00:00Z |
| Stop taking people: pause the study on the panel | Fri Oct 2, by 17:00 PDT | 2026-10-03T00:00:00Z |
| The second lock | Fri Oct 2, 21:00 PDT | 2026-10-03T04:00:00Z |
| The one analysis runs by itself | Fri Oct 2, 21:10 PDT | 2026-10-03T04:10:00Z |

A sitting counts when it started at or after the opening and before the second lock. One that
starts before the opening is left out as a dry run, and that person's browser is left out of
the wave for good, so publishing early loses people. One that starts at or after the lock is
left out too. That is why the study stops taking people four hours before the lock: nobody
should start and then find that the sitting did not count.

## Before you publish: two things must be true

1. The session lead has said that `prereg-v3` is tagged and stamped. The plan is fixed before
   any sitting of the wave, or the wave is not pre-registered. Check:
   `git -C ~/second-look-depth tag -l prereg-v3` prints `prereg-v3`.
2. Judge mode is shut on the live site. It shows the answers to the same photos. Check: open
   `https://second-look-79t.pages.dev/demo` on your phone. It must say that judge mode is shut.

If either is not true at 21:00 PDT, wait. Publishing later the same night costs nothing.

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
4. Publish it, at or after 21:00 PDT on Tue Sep 29. The study runs itself. Watch it with
   `make panel-status`.
5. Pause it on the panel by Fri Oct 2 at 17:00 PDT, full or not.
6. Before you approve any payment, compare the number of completion codes the panel shows as
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

The description says nothing about a first or a second wave, and nothing about judge mode. A
participant needs neither, and the words above are the ones the plan was written for.

The link carries the source label `src=panel`. It is how the results tell panel sittings from
those that came through the public link, and it is the only thing kept from the address.

## How many people

Ask for 80 places. It is the target of the plan, 40 in each group.

The plans' rule is that the test counts as a test only with 20 finished sittings kept in each
group. With fewer it is a description, and the README says so. Some finished sittings are
dropped by the plan's rules: a test done in under 40 seconds, a second visit from the same
browser, a sitting that started outside the window. The server gives out the two groups in turn,
in blocks of 4, so 80 places come out near 40 and 40.

- 50 places is the least that can be expected to reach the rule: about 25 in each group, which
  leaves room for 5 dropped sittings in each.
- 80 places leaves room for 20 dropped sittings in each group.
- Part 2 has the same rule, 20 kept in each of its two groups, and it is optional. With 80
  places it is reached only if more than half of the people take the second block.

If the places fill slowly, leave the study open until the pause on Friday. Do not raise the
reward in the middle: everyone is paid the same.

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

Those counts are of every sitting the site ever stored that was not one of our checks, not only
of the second wave. Before the launch they read 1 completed session, in the trained group, with
the source `other`: our own automated walk of Sep 25, which the plan's rules drop
(`docs/deviations.md`). The `panel` line starts at 0, so it counts the wave's panel sittings and
nothing else. Counts per group are all anyone looks at before the lock.

## After the second lock

On Fri Oct 2 at 21:10 PDT, which is 2026-10-03T04:10:00Z, the lock job runs the analysis of the
second wave once, as `prereg-v3` says, and the README reports what it shows in the second wave's
own rows, whatever that is. The first wave's rows stay as they are. If the panel was not
launched, the second wave's row says that nobody finished the test in its window.

The same run does part 2 for the second wave, and the README's row for it reports the result, or
says that too few finished part 2.
