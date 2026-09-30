# A judge's day

The exact path a judge can follow on the live site, https://second-look-79t.pages.dev, from
Oct 5 to Oct 15, with what they should see at each step. Judge mode (/demo and /t2/demo) is
shut while the second wave of the study runs, because it shows the answers to the study's photos,
and opens at that wave's lock, Oct 3 at 04:00 UTC (Fri Oct 2, 21:00 PDT); before that its page
says when it opens. The repository is public from Sat Oct 3, and the deadline is Sun Oct 4.

## In 45 seconds

1. Open https://second-look-79t.pages.dev. You see "Which creek is healthier?" above two creek
   photos: the first screen of the two-minute test a volunteer takes. Your guess is kept on the
   phone and becomes your first answer only if you agree to take part. If you go on and take the
   test, the server puts you at random in one of two groups: one sees the lesson before the 16
   photos, the other sees the photos first and is offered the lesson after its score. If the
   photos come first, that is your group, not a missing step.
2. Open https://second-look-79t.pages.dev/judges (the README's "Judges start here" link, or For
   judges on the About page). You see every door, each with how long it takes.
3. Open "How we know it works" (/how-we-know). You see which features each of four Claude models
   passed on the same 16-photo test people take, and what the gate kept and dropped on real creek
   footage, with the frames. Under "Kept" is the AI's one question as a person would meet it,
   "The checker noticed something that may be concrete walls and other built banks. Want to look
   again?", with the model's note under it. This is the one place to see that question while
   judge mode is shut.
4. Open "The AI's one question, try it" (/t2/demo), the second door on /judges, once judge mode
   is open. Answer Can't tell when asked about banks, a channel or a pipe. You see "The checker
   noticed something here. Look again?", and you keep or change your answer. It never asks about
   plants, because no model passed that feature. Nothing is stored, and no model is called while
   you answer.

That is the idea in three screens, and the fourth lets you meet the question yourself: people and
models take the same test, and a model may only ask about a feature it passed.

## In 10 minutes

The README's own path, under For judges, starts with the test itself; this one starts with judge
mode, which shows the same photos and stores nothing. While judge mode is shut, start at step 2
and take the test itself from the README's path instead: your sitting then counts in the second
wave, so answer as a volunteer would.

1. **Judge mode** (/demo): the 16 photos with "Right." or "Not this time." after each answer, then
   the score per feature. It stores nothing. About three minutes.
2. **A walk** (/walk, then a creek): a 40 second clip, then the same guided check a volunteer does at
   a creek, in the official app's own words and, if your phone is set to one of its languages, in
   that language. The clips show natural creeks, so to see what a city is told, answer Artificial
   for the bank or Yes to a pipe. It ends on the record your answers make; "View as FHIR" shows it
   as OneAquaHealth's FHIR resources. About three minutes.
3. **What a city sees**: at the end of the walk, "See this creek as a city would" lists what was
   found and what the creek needs in OneAquaHealth's own measures, each with its source. About a
   minute.
4. **A record beside a lab result** (/two): a volunteer Observation in the viewer built for
   laboratory results, with how far to trust it, beside a lab result from the OneAquaHealth
   sandbox. The lab card shows the lab's own five figures for 2020 and who measured them, and the
   page says when the copy was fetched. About a minute.
5. **The audit log** (/verify): every line of the log, checked again in your browser, with its
   Bitcoin timestamp. Under a minute.
6. **The repository** (public from Sat Oct 3): the README's "For judges" section, the technical report
   (docs/REPORT.pdf) and `make judge-check`, which runs the checks again in about five minutes with
   no key and no network, and names in its summary the AI numbers it can check only as recorded.

## If their sandbox is down again

Their sandbox's name, sandbox.hl7europe.eu, stopped resolving on Sep 23 (hl7-eu/oah issue 8),
came back on Sep 28, and has come and gone since. Nothing on the path above needs it. /two keeps
the last copy of their lab record the Mac fetched and says when that was; if no copy is stored,
our record shows alone and the page says so. The records are checked by the HL7 validator in CI
(results/fhir_validation.json, 0 errors); the screens in docs/screens/ show every page. On a day
their sandbox answers, the daily re-push job tries again: it makes any resource of ours that is
missing there and updates our Library entry, which their server refused on Sep 28 with HTTP 400.

## If something does not load

The site is watched every 10 minutes from a team member's laptop, and a failure is posted on the
team's status issue,
[issue 4 of this repository](https://github.com/alejandro-publius/second-look/issues/4). While
that laptop sleeps, nobody is told. A judge who meets a broken page can still read every screen in
docs/screens/ and run `make judge-check` from the repository.
