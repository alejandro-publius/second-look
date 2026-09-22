# Design review 02: stage 2 screens and a second look at stage 1

I reviewed twelve screenshots in `docs/screens/`: 01-landing, 04-lesson-card, 05-test-item, 06-end-score,
20-check-start, 21-spot-record, 22-two, 23-quick, 24-city, 25-judges, 30-landing-desktop and
31-city-desktop. I wrote none of this UI and changed no code. Grey photo placeholders are not findings.
I read `DESIGN_REVIEW_01.md` first and do not repeat what it lists as fixed.

## Summary

The stage 1 fixes held: the answer buttons are equal, the heading focus box is gone, the lesson pair
stacks on a phone, and the desktop landing with real photographs now makes its point in one look. The
stage 2 screens are where the problems are. The city page scrolls sideways on a phone because raw
source links do not wrap, which is a WCAG 2.2 reflow failure on the screen a city judge will open. The
staff gauge draws every fifth block as a short black dash, so the test shows 13 boxes for 16 photos and
the score shows a half black block. The field screens show internal names (`dry_pipe`,
`Practitioner/sl-practitioner-1`, `2026-09-23T17:10:00Z`) where a person should see words, the 20 second
check puts three questions on one screen, and the same answer is called "Can't tell" in the test and
"Not sure" everywhere else. Most fixes below are copy or styling on screens outside the two-minute test
flow. The three that touch the test flow are labelled and should wait for a decision.

## Findings, most valuable first

### 1. The city page is wider than the phone

**Screenshot:** 24-city.png (and the same cards in 21-spot-record.png)
**What is wrong:** The page renders 1611 pixels wide at 3x, so 537 CSS pixels on a 390 pixel phone. The
header stops at 390 and the cards run off the right edge. The cause is the full source URL
(`https://www.oneaquahealth.eu/app/uploads/2026/05/OneAquaHealth-Policy-Brief.pdf`) printed as one
unbreakable word under each measure.
**Why it matters:** WCAG 2.2 SC 1.4.10 Reflow is level AA: content must fit 320 CSS pixels without
sideways scrolling. This is the screen that shows a city what the product is for, and on a phone it
wobbles sideways under the thumb.
**Fix:** Stop printing the URL. Make the source title the link text ("OneAquaHealth Policy Brief (2026),
page 9") and keep the URL in `href`. As a guard, add `overflow-wrap: anywhere` to the source line class.
**Label:** safe

### 2. The staff gauge replaces every fifth block with a dash

**Screenshot:** 05-test-item.png, 06-end-score.png
**What is wrong:** The "heavier tick every fifth block" (`is-fifth` in `components/ui/Gauge.tsx`) is drawn
as a short black bar instead of a box. On the first test item the gauge shows 13 boxes and three dashes,
not 16 boxes. On the score screen block 5 is orange on top and black underneath, so "8 of 16" looks like
eight and a half. The share card gauge on the same screen has 16 plain blocks and no ticks.
**Why it matters:** The whole idea of the gauge is that a count can be read by eye before the numeral.
Right now the count by eye is wrong, and a half filled block reads as half a point.
**Fix:** Keep every block a full box. Draw the fifth block tick as a heavier left border or a small mark
under the gauge, never inside the block. Use the same rule on the share card.
**Label:** test flow, do not touch

### 3. The 20 second check puts three questions on one screen

**Screenshot:** 23-quick.png
**What is wrong:** Water colour, smell, "Is the pipe running?" and a photo sit on one long page, 11 choice
buttons deep, with Send at the bottom. "Foam" is listed as a colour. "0 photo(s) ready" is not plain
English.
**Why it matters:** The brief asks for one question per screen, and the rest of the app follows it.
Outdoors, one-handed, a person has to scroll to check they answered all three before they can send.
**Fix:** Show one fieldset per screen, moving on when a choice is tapped, as the test does, with Send on
the last screen. Rename the colour options to "Clear", "Muddy", "Odd colour", and move "Foam" to its own
Yes or No question, or drop it. Change the count to "No photo yet" and "1 photo ready".
**Label:** safe

### 4. The side by side shows raw FHIR, not a comparison

**Screenshot:** 22-two.png
**What is wrong:** Both cards show `2026-09-23T17:10:00Z`, `Organization/almyros-lab`,
`Practitioner/sl-practitioner-1`, "Method: none" and "Status: final". Both say "Present". Nothing on the
screen says what the reader should notice.
**Why it matters:** This is the screen a standards judge came for, and it looks like a debug view. The
point, that only the volunteer record carries a trust score, is in one grey line near the bottom of the
second card.
**Fix:** Format the time as "Sep 23, 2026, 5:10 PM", show the performer as "A lab" and "A volunteer",
hide "Method: none" and "Status", and leave the raw values to View as FHIR. Add one sentence under the
heading: "Same creek, same answer. Only the volunteer record says how much to trust it." Put a highlight
on the Observer score row.
**Label:** safe

### 5. The spot record shows internal names and two equal buttons

**Screenshot:** 21-spot-record.png
**What is wrong:** "Checks that ran" lists `dry_pipe` and `rating_check` in bold, then "Answer: changed".
The orange "20 second return check" wraps to two lines beside "Full check", and the checkbox "Only people
who passed this feature" does not say what it filters or which feature.
**Why it matters:** Code names at reading age 12 are noise, and "changed" does not say what it changed
to. The checkbox is the trust filter, the main idea of the product, and a reader cannot tell that.
**Fix:** Use human titles: "Pipe after dry days" and "Rating check", and write the outcome as "You changed
your rating from good to moderate". Shorten the orange button to "Quick check". Relabel the checkbox
"Only show answers from people who passed the test for that feature".
**Label:** safe

### 6. The same answer has two names, and the check has four

**Screenshot:** 05-test-item.png against 21-spot-record.png and 23-quick.png; 20-check-start.png against
25-judges.png
**What is wrong:** The test says "Can't tell". The check, quick check and record say "Not sure"
(`check.not_sure`, `quick.colour_cant_tell`, `quick.smell_cant_tell` in `content/locales/en.json`). The
field check is "Creek check" on 20, "Check a creek" on 25 and "Full check" on 21. The short one is
"20 second check" on 23 and "20 second return check" on 21.
**Why it matters:** A volunteer who learned "Can't tell" in the test meets a different word in the field
and may think it means something else. Judges see four names and wonder whether they are four tools.
**Fix:** Change the three "Not sure" strings to "Can't tell" (the test keeps its string). Pick "Creek
check" and "Quick check" and use them on every screen and link.
**Label:** safe

### 7. The judges page hides its point at the bottom and leads with the wrong link

**Screenshot:** 25-judges.png
**What is wrong:** The one sentence that explains the product ("Your score travels with every
observation you make, so a city knows how much to trust it") is small grey text under the list. The
first link is the real test, which "count[s] as a session" in the study; Judge mode, which is built for
judges, is second.
**Why it matters:** A judge with two minutes reads the heading, the first paragraph and the first link.
None of those says what the product does, and the first click adds a judge to the study data.
**Fix:** Move the grey sentence up to be the first paragraph, in body size and ink. Put "Judge mode,
feedback after every answer" first and the real test second.
**Label:** safe

### 8. The landing labels break mid phrase, and the band stays empty

**Screenshot:** 01-landing.png, 30-landing-desktop.png
**What is wrong:** On a phone each label breaks as "This creek, on the" then "left". Below the labels is
a blank band of about 280 CSS pixels, and "No camera needed." is cut by the bottom edge. On desktop the
wordmark sits at x 16 while the content starts at x 80, and a 110 pixel band is left above the button.
**Why it matters:** The labels are the control names (they carry Label in Name), so an odd break makes the
one tap on the page harder to read. The band pushes the one reason line out of view.
**Fix:** Shorten the labels to "Left creek" and "Right creek", which fit on one line, and update the two
spec selectors. Replace "No camera needed." with the reason line "Two minutes. No camera needed." and
let the button sit directly under the labels on desktop. Align the header padding with `main`.
**Label:** safe

### 9. The city page repeats its heading and gets plurals wrong

**Screenshot:** 24-city.png, 31-city-desktop.png
**What is wrong:** The page title and the first section are both "What this creek needs". The copy says
"5 visits at 1 spots", "0 visits at 0 spots" and "1 spots sit on this creek". A demo pin named "test
spot" is shown with "the name reads like a test". "Open the records" appears five times.
**Why it matters:** A repeated heading makes the outline useless for a screen reader. Plural errors read
as unfinished to a city official, and five identical link names are hard to tell apart in a links list.
**Fix:** Rename the section "What OneAquaHealth says to do". Use `Intl.PluralRules` for `city.visits`,
`city.reach_counts` and `city.unplaced`. Keep the "Pins to look at" block out of the demo data. Add the
item name to each link as visually hidden text, for example "Open the records for Pipes and sewage signs".
**Label:** safe

### 10. The creek check start screen leaves its button mid page and names no app

**Screenshot:** 20-check-start.png
**What is wrong:** "Start the check" sits at the middle of the screen with an empty half below it, so the
review 01 thumb reach fix did not reach `/check`. The body says "in the order of the official app" and
"Question wording marked as draft has not yet been checked against the official app" without naming it.
**Why it matters:** The primary action is out of thumb reach on the first field screen. "The official
app" means nothing to a new volunteer or a judge.
**Fix:** Give this screen the same `.stack > .actions { margin-top: auto }` layout as the test screens.
Name the app once: "in the same order as the OneAquaHealth app". Shorten the draft note to "Some
questions are drafts. We have not checked them against that app yet."
**Label:** safe

### 11. The score says 8 of 16 but not what that means

**Screenshot:** 06-end-score.png
**What is wrong:** The score, four rows of "2 of 4", and a share card. Nothing says whether 8 of 16 is
good, what guessing would get, or what the person should do next. The next action is below the fold,
and the share card text ("I spotted 8 of 16.") is in a different typeface from every other screen.
**Why it matters:** Review 01 asked for one honest sentence on what the score does and does not prove.
Without it, a participant and a judge cannot read the number.
**Fix:** Add one approved sentence under the gauge, from `content/approved_sentences.yaml`, with any
number taken from `results/` rather than typed in. Embed the font in the share card, which review 01
left as the next step.
**Label:** test flow, do not touch

### 12. The help link uses a harder word than the question

**Screenshot:** 05-test-item.png
**What is wrong:** The question is "Are there pipes draining polluted water into the stream?" and the
help link under it is "What counts as outfall?". "Outfall" appears nowhere else on the screen. The
screenshot is also scrolled 32 CSS pixels, so the bottom of "Can't tell" sits at about 839 of 844 at
load, under the iPhone home bar.
**Why it matters:** The help link should use the words the person just read, at reading age 12. An answer
button under the home bar is hard to tap.
**Fix:** Change the link to "What counts as a pipe?". Make the Enlarge button a small icon button on the
photo corner to win back the height it took.
**Label:** test flow, do not touch
