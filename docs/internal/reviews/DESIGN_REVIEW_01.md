# Design review 01: the stage 1 launch path

I reviewed the eight stage 1 screenshots in `docs/screens/` (landing, consent, lesson card, test item,
end score, judge mode, the test item in dark, and the landing at 1280 by 800), the code behind those
screens, and `apps/web/styles/tokens.css` plus `apps/web/app/globals.css`, against
`docs/updates/UPDATE_06.md` sections 1 to 6 and `docs/design/DESIGN.md`. I measured the screenshots
pixel by pixel rather than eyeballing them, computed the contrast ratios from the token values, and
read every line I cite. I wrote none of this UI and changed no code. Grey photo placeholders are not
treated as findings. `/check`, `/spot`, `/two`, `/quick`, `/poster` and the README are out of scope.

## What works

- The palette decision holds: survey orange on overcast paper reads as an instrument and not as a
  nature app, and the ink on the orange measures 5.45 to 1 (screenshot 01).
- Atkinson Hyperlegible at 18px and 1.5 line height makes the consent page genuinely readable at arm's
  length, which is rare for a consent page (screenshot 03).
- Consent is short, concrete and lists exactly what is stored, and each checkbox shares one full width
  hit target with its text (`apps/web/components/Consent.tsx:41`).
- Yes, No and Can't tell are three identical buttons in a fixed order with no colour on any of them
  (`apps/web/components/AnswerButtons.tsx:19`, screenshot 05).
- The test item really is one thing per page, and the photograph really is the biggest thing on it
  (screenshot 05).
- The tokens are not decoration: every component value is a `var()`, and the meta theme colour is
  machine checked against `--bg` (`apps/web/scripts/design-check.mjs:107`).
- Icons are generated into one file from one family, so a second family cannot creep in later
  (`apps/web/components/ui/Icon.tsx:1`).
- Lesson marks come from YAML as fractions and are repeated as a numbered text list underneath, so
  Rachel can move them and a screen reader still gets them (`apps/web/components/ui/PhotoFrame.tsx:86`).
- Reduced motion is handled by putting every transition inside a `no-preference` query instead of
  trying to undo them afterwards (`apps/web/app/globals.css:908`).

## What fails, ranked

### Serious

**1. The share card is a different product.**
`apps/web/app/api/share/[score]/route.ts:26` to `:33`, visible in screenshot 06.
The card uses five colours that exist nowhere in `tokens.css` (`#fbfaf6`, `#1f3a2e`, `#14211b`,
`#d9d9d9`, `#465850`), fills its progress bar with a rounded pill (`rx="14"`, lines 30 and 31), and
sets type in `-apple-system, ..., Arial`. `DESIGN.md:23` says the palette is deliberately not leaf
green, `DESIGN.md:25` says progress is deliberately not a rounded pill, and `DESIGN.md:51` says the
font is Atkinson Hyperlegible because it was drawn for low vision readers. The card revives all three
rejected defaults at once. This matters more than any in-app screen: it is the only artefact that
leaves the product, it is what a judge sees pasted into a chat window, and it currently says the team
has no visual system.
Fix: redraw the SVG with `--surface` as the card, `--ink` for both text lines, `--flag` for the fill,
and replace the pill with sixteen square blocks 56px wide and 28px tall at a 8px gap, filled left to
right, which is the staff gauge at poster size. Embed the Atkinson woff2 as a base64 `@font-face`
inside the SVG, or render the two text lines with `font-family="var"` removed and accept the fallback
only after Alex signs it off. Import the hex values from `app/theme.ts` and extend that file rather
than typing new ones.

**2. The staff gauge fails contrast in light mode and loses its segmentation in both modes.**
`apps/web/app/globals.css:393` to `:405`, seen in screenshots 05, 06 and 08.
The orange fill against an unfilled block is 2.63 to 1 in light mode, under the 3 to 1 that WCAG 2.2
SC 1.4.11 requires of a graphical object that carries meaning. Worse, the boundary between one
unfilled block and the next is 1.16 to 1 in light and 1.11 to 1 in dark, so the striped stick stops
being striped exactly where it has not been filled yet, which is most of the test. The whole visual
idea of this product is that "5 of 16" is countable by eye before the numeral is read. In sunlight,
on the screen a stranger will use outdoors, that is not true. `design-check.mjs:146` never tests this
pair, so the machine check says the tokens are clean.
Fix: in `globals.css:393` set `.gauge-block { background: var(--surface); box-shadow: inset 0 0 0
var(--hairline) var(--line-strong); }` and remove the `--surface-sunk` fill. That gives fill against
empty at 3.05 to 1 in light and 7.05 to 1 in dark, and a block outline at 3.54 to 1 in light and 4.63
to 1 in dark, so the segments are countable. Then add `["--flag", "--surface", 3]` to the `PAIRS`
list in `design-check.mjs:146` so this cannot regress.

**3. A participant can lose answers and never be told.**
`apps/web/components/TestFlow.tsx:67`. The POST for each answer is fired with
`.catch(() => { failed.current += 1 })`, and `failed` (declared at `:34`) is never read anywhere in
the file. No stage 1 screen has an offline state either: `offline.saved_here` exists in the locale but
`QueueWatcher` is mounted only on `/check` and `/quick`. `UPDATE_06.md:73` requires an offline state
on every screen. A person doing this test on a phone outdoors, which is the stated use, can answer
sixteen items over a weak connection and reach a score screen computed from whatever arrived. For a
study that is not a UI bug, it is a silent hole in the data, and it is the kind of thing a digital
health judge asks about first.
Fix: lift `failed` into state. When it is above zero, render the existing `.notice .notice-warn` under
the gauge with the `offline.saved_here` string, and pass the count into `api.complete` so the server
records how many answers were missing. Retry each failed POST once from `complete()` before the score
is requested.

**4. There is no Back anywhere, and an answer cannot be changed.**
`apps/web/components/TestItems.tsx:122`, `apps/web/components/Consent.tsx:30`, and every stage 1
screen. `UPDATE_06.md:58` is explicit: "Back is a plain link at the top left". The `caret-left` icon is
already generated at `Icon.tsx:11` and used nowhere. `answered.current = true` at `TestItems.tsx:106`
makes the first tap final and the flow advances at once. On top of that the entire flow is component
state with no URL (`TestFlow.tsx:32`), so a refresh or a back swipe ends the session at item 12 with
no way back in. A 60 year old holding a phone in one hand will mis-tap. Right now a mis-tap is
recorded as data and cannot be corrected, which costs the study accuracy and costs the participant
trust in the same moment.
Fix: add a `quiet` Button at the top left of `ItemScreen` and of the consent and lesson screens, label
`nav.back`, which moves `index` back by one in `TestItems` and clears `answered.current`. Post a
correction rather than a new answer when the item already has one. Separately, put the item index in
the URL with `history.replaceState` so a refresh resumes rather than restarts.

**5. On short screens the primary button is not in thumb reach, it is near the top.**
`apps/web/app/globals.css:246`. `.actions` uses `position: sticky; bottom: 0`, and sticky can only
hold an element up against the bottom edge, it can never push an element down to reach it. Measured
from the screenshots: on judge mode the button occupies 207 to 261 with 583px of empty page below it
(screenshot 07), on consent 638 to 692 with 152px below (screenshot 03), on the lesson card 600 to 654
with 190px below (screenshot 04). `UPDATE_06.md:48` says primary actions sit at the bottom of the
screen inside the safe area, in reach of a thumb. Judge mode is the first screen a judge sees and it
is a heading, one sentence, a button and half a blank page.
Fix: `main { display: flex; flex-direction: column; }`, then
`main > .stack, main > form.stack { flex: 1 1 auto; display: flex; flex-direction: column; }`, then
`.stack > .actions { margin-top: auto; }`. The last rule has two classes so it beats
`.stack > * + *` at `globals.css:255` whatever the order. `body` is already a full height flex column
with `main { flex: 1 }`, so nothing else has to change.

**6. The two landing buttons say "This one" and announce "Pick the left creek".**
`apps/web/components/LandingPick.tsx:42` and `apps/web/components/Warmup.tsx:23`, screenshot 01.
`landing.pick_this` and `warmup.left` are both "This one", and the `aria-label` replaces that with
"Pick the left creek". WCAG 2.2 SC 2.5.3 Label in Name is a level A failure: the accessible name does
not contain the visible text, so a speech control user who says "This one" hits nothing. `axe.spec.ts:8`
will not catch it because the label mismatch rule is experimental and not in the wcag tags used there.
The same sentence is also the product's opening move, and two identical visible labels give a sighted
person nothing to distinguish them either.
Fix: delete the `aria-label` on both and make the visible label carry the meaning. Change
`landing.pick_this` to two strings, "This creek, left" and "This creek, right", and pass the right one
per side. Do the same for `warmup.left` and `warmup.right`, and delete `warmup.pick_left` and
`warmup.pick_right`. Update the selectors in `tests/design.spec.ts:38` and `scripts/design-screens.mjs:42`.

### Worth fixing

**7. On the landing page the photographs are 31 percent of the screen and emptiness is 39 percent.**
Screenshot 01, driven by `apps/web/app/globals.css:861`. Measured: the heading ends at 165, the photos
run 339 to 564 and the labels to about 600, the button starts at 758. That is 174px of nothing between
the question and the photos and 158px between the photos and the button, on an 844px screen, while
each photograph is 173 by 231. `DESIGN.md:33` says the two photographs are the control, not
decoration, and `DESIGN.md:111` says to let the photograph be the biggest thing. Right now the empty
space is the biggest thing, and a person outdoors is asked to compare two creeks in a space the size
of two playing cards.
Fix: drop `justify-content: space-between` from `.landing-top` and use
`justify-content: flex-start; gap: var(--s5);` with `.landing-pick { flex: 1 1 auto; }` so the pair
takes the slack. Change `.landing-top .photo` from `aspect-ratio: 3 / 4` to `aspect-ratio: 1 / 1` and
let the height come from the free space. Target: photographs at least 300px tall on a 390 by 844
screen.

**8. Tapping a photograph moves both photographs about 70px.**
`apps/web/components/LandingPick.tsx:48` with `globals.css:861`. The status paragraph is inserted as a
fourth flex child of a `space-between` column, so the free space is redivided from two gaps into
three. With the 332px of free space measured above, the pair jumps up by roughly 70px at the instant
of the tap. `UPDATE_06.md:52` calls this the one orchestrated moment in the product. It currently
throws the thing you just touched out from under your finger.
Fix: reserve the line. Render the paragraph always, with the text swapped in on pick, or give it
`min-height: var(--s6)` and animate only its opacity. Finding 7's `flex-start` layout fixes this too.

**9. The heading is wrapped in a black focus box on first paint.**
`apps/web/components/FocusHeading.tsx:9` with `globals.css:73`, clearly visible in screenshots 03 and
07 and not in 04, 05 or 06. On a fresh page load, with no prior pointer event, Chrome matches
`:focus-visible` on the programmatically focused `h1`, so "Before you start" and "Judge mode" each
open inside a 3px ink outline the full width of the measure. It reads as an error state or an empty
text field, which is exactly the wrong first impression on a consent page and on the judge's first
screen.
Fix: add `h1[tabindex="-1"]:focus-visible, h2[tabindex="-1"]:focus-visible { outline: none; }` after
`globals.css:77`. Keep the programmatic focus, since that is what moves a screen reader to the new
screen, and keep the ring on `main` and on every interactive element.

**10. The sticky action bar sits on top of the share card.**
`globals.css:246` with `apps/web/components/ScoreScreen.tsx:58`, screenshot 06. The share card starts
at 619 and is 188px tall at its 1200 by 630 ratio, so it ends at about 807, while the opaque
`.actions` bar starts at 777. The bottom third of the card is covered, including the wordmark line,
and the bar keeps covering it while the page scrolls because more content follows it. The card is the
thing the button is asking the person to share, and they cannot see all of it.
Fix: once finding 5 lands, `.actions` no longer needs to be sticky on screens that scroll. Either drop
`position: sticky` and rely on `margin-top: auto`, or add
`.stack > .actions:not(:last-child) { position: static; }` so a bar that has content after it stops
floating.

**11. The contrast pair is the evidence, and on a phone it is 173 by 126.**
`apps/web/components/Lesson.tsx:73` with `globals.css:274`, screenshot 04. `.pair` is two equal
columns at every width, so the assume photograph and the actual photograph are each 173px wide on a
390px screen. The numbered marks are worse: `PhotoFrame.tsx:61` draws `r="15"` in a 400 by 300 viewBox,
which scales to a 13px dot, and `globals.css:334` puts an 18px numeral inside that 13px dot. An
ecologist judging whether the teaching is real is being shown the cue at a size where the cue is not
visible.
Fix: add `@media (max-width: 599px) { .pair { grid-template-columns: 1fr; } }`. Keep the two up layout
from 600px. The side by side comparison is worth less than a photograph you can actually read, and the
captions already say which is which.

**12. Missing content renders a blank white page.**
`apps/web/components/TestItems.tsx:29`, `apps/web/components/Lesson.tsx:42` and `:45`. All three
`return null`. `UPDATE_06.md:73` requires an empty state on every screen that says what this is, why
it is empty, and how to start. A judge who opens the app while a content file is mid edit gets a page
with a header and nothing under it, and no way to tell whether the app is broken or still loading.
Fix: replace each `return null` with the existing `.notice .notice-bad` block used at
`TestItems.tsx:96`, with a new string that names what is missing and offers a link back to `/`.

**13. Every phone participant is told to press a key.**
`apps/web/components/TestItems.tsx:147`. "On a keyboard, press Y, N or C." renders unconditionally,
directly under the answer buttons, on a screen designed for a phone held in one hand. It is the last
thing a person reads before answering, and it does not apply to them.
Fix: gate it on a pointer query. Render it only when `window.matchMedia("(hover: hover) and
(pointer: fine)").matches`, computed in an effect so the server render stays stable.

**14. The same gauge means two different things two screens apart.**
`apps/web/components/Lesson.tsx:60` shows a four block gauge one block full with the words "Built
banks" beside it (screenshot 04). `apps/web/components/ScoreScreen.tsx:52` shows a four block gauge two
blocks full with the words "Built banks, 2 of 4" beside it (screenshot 06). On the lesson the fill
means "feature 1 of 4 in this lesson". On the score it means "you got 2 of 4 right". The count is only
in the screen reader text at `Lesson.tsx:60`, so a sighted person sees a score where there is none.
`DESIGN.md:27` claims this is one object doing two jobs, which only works if the label always says
which job it is doing.
Fix: put the count in `countText` on the lesson too, as "Built banks, part 1 of 4", and pass
`srText` only for the extra context. Or drop the gauge from the lesson head and use the plain feature
name, since lesson progress is not a measurement.

**15. The desktop landing is the phone page with half the screen unused.**
Screenshot 09, from `globals.css:141`. `main` is capped at 40rem, so at 1280 the page is a 640px
column with 320px of empty page on each side and the photographs at 314 by 419. Judges will open this
on a laptop. Nothing about the layout says it was considered at that width.
Fix: `@media (min-width: 900px) { body:has(.landing-hero) main { max-width: 64rem; }
.landing-top .photo { aspect-ratio: 4 / 3; } }`. That alone puts two 500px wide creek photographs side
by side, which is the only thing the wide screen is good for.

**16. The landing page sends its first click into stage 2.**
`apps/web/app/page.tsx:31` to `:33`. Below the fold the landing offers Judge mode, Creek check, How we
know and Two observers, and the header offers About and Privacy. `UPDATE_06.md:60` allows a small
wordmark and an About link, nothing else. Three of those four links lead to screens that were
deliberately not restyled in this pass, so the first click a judge makes off the landing page can land
on unfinished work.
Fix: keep Judge mode and How we know, remove Creek check and Two observers from the landing nav until
stage 2 lands, and move Privacy into the footer with About.

**17. The published screenshots show Can't tell caught mid hover.**
`apps/web/scripts/design-screens.mjs:28`, visible in screenshots 05 and 08. `page.screenshot({ path })`
is called with no `animations: "disabled"`, and `walk()` leaves the mouse wherever the last click
landed, which is on top of the third choice. Measured in `05-test-item.png`: the Yes and No buttons
have a `#7e8b87` border on white, the Can't tell button has a `#43504d` border on `#f5f6f7`, which is
the 150ms hover transition frozen part way. In a study whose stated point is that the three answers
carry equal weight, the screenshot that proves it shows one of them looking different.
Fix: in `shot()`, call `await page.mouse.move(0, 0)` and pass `{ path, animations: "disabled" }`, then
retake 05 and 08.

**18. The installed app is green.**
`apps/web/app/manifest.ts:13` and `:14` set `background_color: "#fbfaf6"` and `theme_color: "#1f3a2e"`,
the same off palette cream and green as the share card, while `app/theme.ts:4` and `layout.tsx:21`
declare the real `#f4f6f5`. Android trusts the manifest, so the installed splash screen and title bar
are a colour that appears nowhere in the product.
Fix: import `THEME_LIGHT` from `app/theme.ts` into `manifest.ts` and use it for both, then add a
manifest check to the `theme.ts` mirror test at `design-check.mjs:107`.

**19. `make design-check` does not look where the off palette colour actually is.**
`apps/web/scripts/design-check.mjs:94` filters the raw colour scan to `cssFiles` and `tsxFiles`, so
`.ts` files are collected at line 43 and then skipped, which is why five raw hex values in
`app/api/share/[score]/route.ts` and two in `app/manifest.ts` pass a check whose banner says it fails
the build on a raw hex colour. Line 100 checks raw radius but nothing checks raw size, so
`globals.css:74` (`outline: 3px`), `:329` (`stroke-width: 2`), `:334` (`font-size: 18px`) and `:769`
(`text-decoration-thickness: 2px`) sit outside `tokens.css` against `UPDATE_06.md:30`. A guard that is
narrower than the rule it advertises is worse than no guard, because the next session will trust it.
Fix: change line 94 to iterate `[...cssFiles, ...tsxFiles, ...code.filter(f => f.endsWith(".ts"))]`
with `TOKENS` and `THEME` still excluded, add a rule for `font-size|stroke-width|outline-width|
border-width|letter-spacing:` followed by a raw unit, then break one value on purpose and confirm the
check goes red before you trust it.

### Minor

**20. No press feedback anywhere except the primary button.**
`globals.css:22` turns `-webkit-tap-highlight-color` off for the whole app, and only `.btn` has an
`:active` rule (`:195`). `.choice`, `.landing-pick`, `.sheet-close` and `.glossary-btn` show nothing at
all when a finger lands on them. On the test item that means tapping Yes gives no acknowledgement
until the screen changes.
Fix: add `.choice:active, .landing-pick:active { transform: scale(0.99); background: var(--surface-sunk); }`
next to the existing `.btn:active`.

**21. The one remaining progress label uses the banned wording.**
`apps/web/components/Progress.tsx:5` defaults `labelKey` to `progress.step`, which renders "Step 1 of
4". `UPDATE_06.md:80` bans "Step 1, Step 2" labels. Only stage 2 calls it today, so this is cheap to
fix before it spreads.
Fix: delete the default and make `labelKey` required.

**22. The landing CTA is hand rolled.**
`apps/web/components/LandingPick.tsx:53` writes `className="btn btn-block"` on a `Link` instead of
using `ButtonLink`, which exists at `Button.tsx:37` for exactly this. `DESIGN.md:71` says nothing
outside `components/ui` may style a button. The same line carries `id="cta"`, which nothing in the
repo references.
Fix: `<ButtonLink href={href} block>{cta}</ButtonLink>` and drop the id.

**23. Long feature names push the gauge out of line.**
`apps/web/components/ui/Row.tsx:5` with `globals.css:441`. "Plants that do not belong" wraps to two
lines in screenshot 06, so its count and gauge sit at a different height from the three rows above.
Fix: add `text-wrap: balance` to `.row-label` and give `.row` `align-items: flex-start` with the
`.row-end` pinned by `padding-top: var(--s1)`, so the gauges line up whatever the label does.

**24. The draft badge is a second orange.**
`apps/web/components/Lesson.tsx:62` with `globals.css:596`. In screenshot 04 the `--warn` badge sits
14px above the `--flag` heading area and reads as the same accent at a glance, which undercuts
`DESIGN.md:48`. It also sits above the heading, which is the position `UPDATE_06.md:46` reserves for
nothing at all.
Fix: move the badge below the rule of thumb and give it the `.notice` treatment with the warning icon
and no fill, so the only orange on the screen stays the accent.

**25. Loading text does not end with an ellipsis.**
`apps/web/components/TestFlow.tsx:100` and `:152` pass "Setting up your test" and "Scoring your
answers" into `Skeleton`. The Vercel guidelines ask that loading states end with an ellipsis, and
without it the words read as a finished statement rather than something in progress.
Fix: add the ellipsis character to `loading.test` and `loading.score` in `content/locales/en.json`.

**26. The contributor token will be mangled by auto translation.**
`apps/web/components/ScoreScreen.tsx:67`. The token is the one string a person must copy exactly, and
Chrome's page translation will happily rewrite it.
Fix: `<p className="token" translate="no" ...>`. Do the same for the wordmark at `layout.tsx:35`.

**27. A failed copy says nothing.**
`apps/web/components/ScoreScreen.tsx:41`. When `navigator.clipboard.writeText` throws, the catch sets
the state back to "none" and the person sees the button label not change. `UPDATE_06.md:78` says an
error says what happened, why, and what to do next.
Fix: add a third state and render a `.notice .notice-warn` with `role="status"` saying the copy did
not work and that the token can be selected by hand.

**28. `make check` is red today, and the guard that breaks it is the dash guard.**
`apps/web/scripts/design-check.mjs:53` and `:54` test for an em dash and an en dash by writing those
two characters as literals, so `apps/web/scripts/check-dashes.mjs` finds them and exits 1. Running
`node apps/web/scripts/check-dashes.mjs` prints those two paths and `dash-check: 2 hit(s)`, and
`dash-check` is a prerequisite of `check` in the Makefile at line 16. Hard rule 18 says no em or en
dash anywhere in the repo, and the file enforcing it is the only file breaking it.
Fix: in `design-check.mjs:53` and `:54`, compare against `String.fromCharCode(0x2014)` and
`String.fromCharCode(0x2013)`, which is what `check-dashes.mjs:9` already does.

**29. The progress count is never announced.**
`apps/web/components/ui/Gauge.tsx:35` puts `aria-live="polite"` on a span that is created along with
the rest of the screen, because `TestItems.tsx:32` keys `ItemScreen` on the item id and remounts the
whole subtree. A live region inserted with its page does not announce. The count is in the visible
text and `FocusHeading` moves focus, so nothing is lost, but the attribute is doing nothing and will
be read as coverage that exists.
Fix: hoist the gauge above the keyed `ItemScreen` in `TestItems.tsx` so the same node updates, or drop
the `live` prop and rely on the heading move.

## Vercel Web Interface Guidelines audit

### apps/web/styles/tokens.css

✓ pass

### apps/web/app/globals.css

apps/web/app/globals.css:22 - tap highlight removed globally with no replacement; only `.btn` has `:active` (:195)
apps/web/app/globals.css:44 - `overflow-wrap: anywhere` on h1 to h3 and p breaks words mid word, use `break-word`
apps/web/app/globals.css:103 - `.site-header` has no `env(safe-area-inset-top)`, app is `appleWebApp.capable` (layout.tsx:13)
apps/web/app/globals.css:246 - sticky footer covers following content (share card, ScoreScreen.tsx:58)
apps/web/app/globals.css:393 - gauge fill 2.63 to 1 against the empty block in light, under SC 1.4.11's 3 to 1
apps/web/app/globals.css:459 - `.sheet-scrim` is fixed full screen, only `.sheet-panel` (:476) contains overscroll; body scrolls behind on iOS
apps/web/app/globals.css:762 - `.glossary-btn` missing `touch-action: manipulation`
apps/web/app/globals.css:878 - `.landing-pick` missing `touch-action: manipulation` on the main landing control

### apps/web/app/layout.tsx

apps/web/app/layout.tsx:13 - standalone capable with no safe area padding (see globals.css:103)
apps/web/app/layout.tsx:35 - brand wordmark not `translate="no"`
apps/web/app/layout.tsx:40 - no `<footer>` landmark anywhere; the only footer markup is a `<nav>` (page.tsx:31)

### apps/web/app/page.tsx

apps/web/app/page.tsx:23 - landing LCP image is `loading="eager"` (Photo.tsx:18) with no `fetchPriority="high"`
apps/web/app/page.tsx:31 - `<nav className="site-footer">` inside `<main>`, footer styling on a nav landmark

### apps/web/app/t/page.tsx

✓ pass

### apps/web/app/demo/page.tsx

✓ pass

### apps/web/components/ui/Button.tsx

✓ pass

### apps/web/components/ui/ChoiceList.tsx

apps/web/components/ui/ChoiceList.tsx:36 - `aria-pressed` on a single select group; for the radio use documented at :11 use `role="radiogroup"` and `aria-checked`
apps/web/components/ui/ChoiceList.tsx:35 - all three choices drop to `opacity: .55` (globals.css:556) for the length of the POST, a dimmed flash after every answer

### apps/web/components/ui/PhotoFrame.tsx

apps/web/components/ui/PhotoFrame.tsx:54 - `priority` sets `loading="eager"` but never `fetchPriority="high"`
apps/web/components/ui/PhotoFrame.tsx:74 - `aria-expanded` without `aria-controls` on the marks toggle
apps/web/components/ui/PhotoFrame.tsx:98 - enlarged image has no `loading` attribute

### apps/web/components/ui/Gauge.tsx

apps/web/components/ui/Gauge.tsx:35 - `aria-live` region is created with its screen (TestItems.tsx:32 remounts on key), so it never announces

### apps/web/components/ui/Sheet.tsx

apps/web/components/ui/Sheet.tsx:54 - click and keydown handlers on a `<div>`; Escape works only while focus is inside the scrim
apps/web/components/ui/Sheet.tsx:55 - page behind the dialog is not `inert` or `aria-hidden`, a virtual cursor can reach it
apps/web/components/ui/Sheet.tsx:19 - no body scroll lock, only the panel contains overscroll

### apps/web/components/ui/Row.tsx

apps/web/components/ui/Row.tsx:9 - `<br>` used for layout inside the label
apps/web/components/ui/Row.tsx:5 - no truncation or balance, a long label wraps and pushes the gauge out of line

### apps/web/components/ui/Skeleton.tsx

apps/web/components/ui/Skeleton.tsx:9 - loading text does not end with an ellipsis (callers at TestFlow.tsx:100 and :152)

### apps/web/components/ui/Icon.tsx

✓ pass

### apps/web/components/LandingPick.tsx

apps/web/components/LandingPick.tsx:42 - `aria-label` replaces the visible "This one", SC 2.5.3 Label in Name
apps/web/components/LandingPick.tsx:53 - raw `className="btn btn-block"` on a Link instead of `ButtonLink`
apps/web/components/LandingPick.tsx:53 - `id="cta"` referenced nowhere
apps/web/components/LandingPick.tsx:22 - CTA href patched in an effect, a tap before hydration loses `?src=`

### apps/web/components/Consent.tsx

apps/web/components/Consent.tsx:49 - error renders at the foot of the form, not inline by the field, and focus does not move to the first unchecked box

### apps/web/components/Warmup.tsx

apps/web/components/Warmup.tsx:23 - `aria-label` replaces the visible "This one", SC 2.5.3 Label in Name

### apps/web/components/TestFlow.tsx

apps/web/components/TestFlow.tsx:32 - whole flow is component state with no URL, refresh or a back swipe drops the session
apps/web/components/TestFlow.tsx:67 - a failed answer POST is counted into `failed` (:34) and never read or shown
apps/web/components/TestFlow.tsx:100 - loading label without an ellipsis
apps/web/components/TestFlow.tsx:152 - loading label without an ellipsis

### apps/web/components/TestItems.tsx

apps/web/components/TestItems.tsx:29 - `return null` on empty input, a blank page
apps/web/components/TestItems.tsx:87 - key handler locates a button with `document.querySelector` and calls `.click()` instead of calling `answer()`
apps/web/components/TestItems.tsx:125 - `<link rel="preload" as="image">` with no `fetchPriority="low"`, the next photo competes with the current one
apps/web/components/TestItems.tsx:147 - keyboard hint rendered on touch devices

### apps/web/components/Lesson.tsx

apps/web/components/Lesson.tsx:42 - `return null` on missing content, a blank page
apps/web/components/Lesson.tsx:45 - `return null` on missing content, a blank page
apps/web/components/Lesson.tsx:60 - gauge with no count in its visible label while the same component carries one at ScoreScreen.tsx:52

### apps/web/components/ScoreScreen.tsx

apps/web/components/ScoreScreen.tsx:41 - clipboard failure is silent, no message and no next step
apps/web/components/ScoreScreen.tsx:58 - below the fold image with no `loading="lazy"`
apps/web/components/ScoreScreen.tsx:67 - contributor token needs `translate="no"`

### apps/web/components/DemoFlow.tsx

✓ pass

### apps/web/components/Glossary.tsx

✓ pass

### apps/web/components/Progress.tsx

✓ pass

### apps/web/components/AnswerButtons.tsx

apps/web/components/AnswerButtons.tsx:14 - wraps the choices in the sticky `.actions`, so the hint at TestItems.tsx:147 can slide under the bar

### apps/web/components/FocusHeading.tsx

apps/web/components/FocusHeading.tsx:9 - programmatic focus triggers the global `:focus-visible` ring (globals.css:73) on the h1 at first paint, screenshots 03 and 07

## Three questions, answered by name

**Would a stream ecologist trust this?**
Partly. The question wording, the assume against actual pairing, and the line "one visit is a snapshot,
repeated visits make a story" all read like someone who has stood in a creek, and the refusal to colour
Yes and No is the sort of restraint a methods person notices. What loses them is the evidence itself:
on a phone the lesson photographs are 173 by 126 with 13px marks (finding 11), and the score screen
reports 8 of 16 with no sense of which items were hard or how two observers would compare. What would
change my answer: the contrast pair stacked full width on a phone, and one honest sentence on the score
screen about what the sixteen items sample and what the score does not prove.

**Could a 60 year old use it one-handed in sunlight?**
On the test item, nearly. The type is 18px, the answers are three 56px buttons in a fixed order, and
all three fit inside 390 by 844 with 16px to spare. Everywhere else, no: on consent and judge mode the
button sits in the top half with a blank screen under it (finding 5), there is no Back so a mis-tap is
permanent (finding 4), and nothing acknowledges a touch because the tap highlight is off and only the
primary button has a pressed state (finding 20). Sunlight makes it worse, since the gauge stripes are
1.16 to 1 apart and will simply vanish (finding 2). What would change my answer: findings 2, 4, 5 and
20 fixed, then ten minutes outdoors with a real phone at full brightness.

**Does any screen look like a template?**
No screen looks like a starter kit, and the landing page could not be mistaken for another product:
the question as the headline with two photographs as the control is a real idea, and Atkinson plus
survey orange is a real choice. Two things do look generic. The share card is a stock green and cream
social image with a rounded progress pill and a system font, which is not this product at all
(finding 1). Judge mode's intro is a heading, one sentence, a button and 583px of nothing, which is
what any half finished app looks like (finding 5). What would change my answer: rebuild the share card
out of the staff gauge in the real palette and font, and give the judge mode intro something worth
looking at, such as the first creek photograph at full width.

## What the implementer did with this review, 2026-09-20

Every line number above refers to the code as the reviewer read it. The fixes below moved many of
them. `make check` is green with `make design-check` inside it, 30 Playwright tests pass and axe
reports no serious or critical violations on nine screens.

### Fixed

1. **Share card.** Redrawn in `app/api/share/[score]/route.ts` on the tokens, through new mirrored
   constants in `app/theme.ts`, with the staff gauge at poster size: sixteen square blocks, filled
   left to right, `--flag` on `--surface` with a `--line-strong` edge. The rounded pill and the five
   off palette colours are gone. The font is named, not embedded: an SVG served as an image cannot
   load a font from us, so it names Atkinson Hyperlegible Next and falls back. Embedding the woff2
   as base64 is the next step if Alex wants the card pixel true off our machines.
2. **Gauge contrast and segmentation.** An empty block is now `--surface` with an inset
   `--line-strong` hairline, so every block has an edge and the stripes survive where nothing is
   filled. `["--flag", "--surface", 3]` is in the `PAIRS` list in `design-check.mjs`, and breaking
   `--ok-bg` on purpose proved the contrast rule fires rather than passing silently.
5 and 10. **Thumb reach.** `position: sticky` is gone. `main` is a flex column, the flow is a flex
   column inside it, and `.stack > .actions { margin-top: auto }` pushes the bar to the bottom.
   Two classes, so it beats `.stack > * + *` whatever the order. Because the bar is no longer
   sticky it cannot cover the share card.
6. **Label in Name.** Both `aria-label` attributes are deleted. The visible labels are now "This
   creek, on the left" and "This creek, on the right" on the landing page and on the warm up
   fallback. `warmup.pick_left`, `warmup.pick_right` and `landing.pick_this` are removed from the
   locale, and the selectors in the specs and both screenshot scripts follow.
8. **The jump on pick.** The answer line is always in the layout with a reserved height, so tapping
   a photograph no longer moves it.
9. **The focus box on the heading.** `h1[tabindex="-1"]:focus-visible` and the h2 form have no
   outline. The programmatic focus stays, because that is what moves a screen reader to a new
   screen; the ring stays on every interactive element.
11. **The contrast pair.** `.lesson-pair` stacks to one column under 600px. Two up returns at 600.
12. **Blank pages.** A `Nothing` component in `TestItems.tsx` says what happened and offers the way
    back. It replaces all three `return null` cases in the lesson and the item list.
13. **The keyboard hint** renders only when `(hover: hover) and (pointer: fine)` matches, computed
    in an effect so the server render stays stable.
14. **One gauge, two jobs.** The lesson gauge count now reads "Built banks, part 1 of 4", so the
    label always says which job the gauge is doing.
15. **Desktop.** From 900px the landing page gets a 64rem measure and a 4 by 3 crop, which is the
    one thing a wide screen is good for here.
17. **Frozen hover in the published screenshots.** `shot()` moves the pointer to 0,0 and passes
    `animations: "disabled"`. All nine screenshots were retaken.
18. **The installed app.** `manifest.ts` imports `THEME_LIGHT` for both colours, and the generated
    home screen icon in `build-content.mjs` uses `--ink` and `--bg`.
19. **The guard was narrower than the rule.** `design-check.mjs` now scans `.ts` as well as `.css`
    and `.tsx`, catches a raw `font-size`, `stroke-width`, `outline-width`, `border-width`,
    `letter-spacing` or `text-decoration-thickness`, and checks nine mirrored constants in
    `theme.ts` rather than two. Three raw sizes in `globals.css` fell out and are tokens now. Every
    rule was mutation tested: a raw hex, a raw size, a gradient, uppercase with tracking, three
    equal cards, a drifted mirror, a contrast pair under its floor, a raw hex in a plain `.ts`
    file, and a choice button shrunk to 20px each turned the check red, and the check went clean
    again on restore.
20. **Press feedback** on `.choice`, `.landing-pick`, `.sheet-close` and `.glossary-btn`.
21. **`progress.step`** is no longer a default; `labelKey` is required.
22. **The CTA** uses `ButtonLink` and the dead `id="cta"` is gone.
23. **Row alignment**: labels balance and the gauges pin to the top, so a wrapped name keeps its
    gauge in line.
24. **The draft badge** is a warning notice with the icon, below the rule of thumb, so the only
    orange on the lesson card is the accent.
25. **Loading strings** end with an ellipsis.
26. **`translate="no"`** on the contributor token and on the wordmark.
27. **A failed copy** renders a warning notice that says to select the text by hand.
28. **The live region** is hoisted out of the keyed item subtree in `TestItems.tsx`, so the same
    node updates and the count can actually be announced.

### Partly fixed, with the reason

3. **Answers that do not send.** `failed` is state now, every response gets one retry, and a
   warning line with the offline icon sits above the items for the rest of the run. The count is
   NOT sent to the server: `api.complete` has no field for it and `docs/CONTRACTS.md` is the
   agreement with the API workstream. That is a planner question, not a design change.
4. **Back.** Back is a plain link at the top left of the consent screen and inside the lesson.
   There is deliberately no Back on a test item. Reaction time per item is a pre-registered
   outcome in `docs/analysis_plan.md` item 4, and letting a person revise an answer would change
   what is being measured and would need a response correction in the API and a dated deviation in
   the plan. The URL state for resume is not done either; it is a real gap and it is bigger than a
   design pass.
7. **The landing band.** The slack is now collected in one place above the button instead of split
   into two gaps, the photographs keep a sane crop rather than stretching, and the crop ratio is a
   token, `--landing-photo-ratio`, so it can be retuned the day Rachel's real photographs land. A
   quiet band remains. Two photographs side by side on a 390px phone can only be about 170px wide,
   and the brief says nothing but the question, the photographs and one button may sit above the
   fold. The band is the price of that rule, and grey placeholders read emptier than photographs
   will.

### Disagreed, and why

16. **The landing links.** The part of this that the brief actually requires is done: above the
    fold there is now a wordmark and an About link and nothing else, because Privacy moved to the
    bottom navigation. The four product links stay. Removing Creek check and Two observers would
    hide the field tool and the side by side with their own lab result, which is the FHIR
    interoperability story a standards judge came to see. Unfinished styling on a parked screen
    costs less than a judge never finding the screen.
