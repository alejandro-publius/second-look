# A judge's day

The exact path a judge can follow on the live site, https://second-look-79t.pages.dev, from
Oct 1 to Oct 15, with what they should see at each step. Judge mode opens on Sep 28
(2026-09-28T01:00:00Z); before that its page says when it opens.

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
   footage, with the frames.

That is the idea in three screens: people and models take the same test, and a model may only ask
about a feature it passed.

## In 10 minutes

1. **Judge mode** (/demo): the 16 photos with "Right." or "Not this time." after each answer, then
   the score per feature. It stores nothing. About three minutes.
2. **A walk** (/walk, then a creek): a 40 second clip, then the same guided check a volunteer does at
   a creek. The clips show natural creeks, so to see what a city is told, answer Artificial for the
   bank or Yes to a pipe. It ends on the record your answers make; "View as FHIR" shows it as
   OneAquaHealth's FHIR resources. About three minutes.
3. **What a city sees**: at the end of the walk, "See this creek as a city would" lists what was
   found and what the creek needs in OneAquaHealth's own measures, each with its source. About a
   minute.
4. **A record beside a lab result** (/two): a volunteer Observation in the viewer built for
   laboratory results, with how far to trust it. About a minute.
5. **The audit log** (/verify): every line of the log, checked again in your browser, with its
   Bitcoin timestamp. Under a minute.
6. **The repository** (public from Sep 30): the README's "For judges" section, the technical report
   (docs/REPORT.pdf) and `make judge-check`, which runs the checks again in about five minutes with
   no key and no network.

## If their sandbox is still down

Their sandbox's name stopped resolving on Sep 23 (hl7-eu/oah issue 8). Nothing on the path above
needs it. /two shows our record alone and says so; the records are checked by the HL7 validator in
CI (results/fhir_validation.json, 0 errors); the screens in docs/screens/ show every page. When
their sandbox answers again, the daily job pushes our Library entry and the golden visit, and /two
shows their laboratory record beside ours.

## If something does not load

The site is watched every 10 minutes from the team's Mac, and a failure is posted on the status
issue. A judge who meets a broken page can still read every screen in docs/screens/ and run
`make judge-check` from the repository.
