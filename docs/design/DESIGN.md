# Second Look: design

Source of truth for how this product looks and reads. It follows docs/updates/UPDATE_06.md, which wins
over every earlier file on look, reading and feel. It changes no rule about privacy, the gate, the
analysis or FHIR. Stage 1 covers `/`, consent, the test item, the lesson card, the end screen and
`/demo`. Everything else is spec, not yet built.

## 1. The read

A phone-first field tool and a two minute test, used by ordinary adults standing outdoors in daylight,
and read by ecologists, digital health people and standards engineers. Trust first, plain, led by
photographs. Dials: layout variance 3, motion 2, density 4. Calm beats clever on every screen except
the opening question.

The boldness is spent in one place: the staff gauge, the striped measuring stick a surveyor stands in a
stream. It is the progress bar in the test and the score mark on every record. It says measurement
without a word. Everything around it stays quiet.

## 2. What I changed away from the obvious version

Six places where the first thing I would draw for any app was wrong for this one.

1. A nature app defaults to leaf green and water blue. This one takes its palette from survey gear:
   overcast paper, deep ink, and the orange of a survey flag, the easiest colour to find in sunlight.
2. Progress defaults to a rounded pill that fills. Ours is segmented, one block per item, square ends,
   so "5 of 16" is countable by eye before the numeral is read. The shape carries the number.
3. A score screen defaults to four donut charts. Ours reuses the same gauge at small size, so the
   progress bar and the score mark are literally one object doing two jobs.
4. Yes and No default to green and red. Here they are three buttons of equal weight in a fixed order,
   because colouring them tells the person what the safe answer is and that would bend the study.
5. A rule of thumb defaults to a callout box with a lightbulb. Here the rule is the heading of the
   lesson card and the photograph comes first, because the photograph is the evidence.
6. A landing page defaults to a centred headline over a washed background. Here the two photographs
   are the control, not decoration: tapping one is the person's answer.

## 3. Tokens

All in `apps/web/styles/tokens.css`. No colour, size or radius appears in a component as a raw value.
`apps/web/scripts/design-check.mjs` fails the build if one does.

Colour, light then dark: `--bg` #F4F6F5 / #0F1715 for the page. `--surface` #FFFFFF / #16211E for sheets
and cards. `--ink` #14211E / #E8EEEB for text and focus rings. `--ink-soft` #4B5B57 / #A9B8B3 for
secondary text. `--line` #D5DCD9 / #2A3733 for hairlines, with `--line-strong` for control borders so
they reach 3 to 1. `--flag` #F26B1D / #FF8A3D is the one accent: primary button, gauge fill, selected
state. `--ok` #1F7A4D, `--warn` #9A4A06, `--bad` #B42318, lighter steps in dark, state only, always with
an icon and words, never colour alone.

Text on the orange is always `--ink`. White on the orange fails and is banned. One accent for the whole
product. No gradients. No pure black. A sheet's shadow is tinted with the ink colour.

Type. Atkinson Hyperlegible Next, variable, self hosted through `next/font/local`, so no request leaves
our origin. It was drawn for low vision readers and holds up in sunlight. Atkinson Hyperlegible Mono is
allowed only inside the View as FHIR sheet. Body 18px on phones, line height 1.5, measure under 65
characters. Headings 24, 30 and 38. Sentence case everywhere. No all caps labels, no small label above a
heading, no single word in a headline set in colour or italic for effect. Counts use tabular figures.

Shape and space. One radius, 12px, on photos, sheets, buttons and inputs. The gauge has square ends and
is the only square thing, which is how it reads as an instrument. A 4px spacing grid. Tap targets 48px
or more. Primary actions sit at the bottom of the screen inside the safe area, in thumb reach.

Icons. Phosphor regular, one family, generated into `components/ui/Icon.tsx` from `@phosphor-icons/core`
so there is no icon runtime and no second family can creep in. No emoji. No hand drawn SVG.

Motion. 150 to 200ms ease out on presses and sheets, on transform and opacity only. One orchestrated
moment in the product: the answer to the opening question. Under reduced motion everything is instant.

Dark mode follows the system and uses the dark tokens. Photographs are never tinted.

## 4. The six components

All in `apps/web/components/ui/`. Nothing else may style a button, a choice or a photo.

- **Button.** Three kinds: `primary` (flag fill, ink text), `secondary` (surface, ink border),
  `quiet` (underlined text). Always 48px tall, always a verb, never an arrow in the label. Full width
  inside a flow. `busy` keeps it enabled until the request starts and then shows its own label.
- **ChoiceList.** The one thing per page pattern. Large stacked buttons of equal weight, fixed order,
  one hit target each with no dead zone. Used for Yes, No, Can't tell, and for radio choices.
- **PhotoFrame.** A photograph at one radius with an optional numbered mark layer. Marks come from the
  lesson YAML as `x` and `y` fractions plus a label of five words or fewer, so Rachel places them
  without code. Marks are hidden until asked for, and the same marks are listed in words underneath so
  a screen reader gets them. An enlarge control opens the photo in the Sheet.
- **Gauge.** The staff gauge. `total` blocks, `value` filled in `--flag`, square ends, a heavier tick
  every fifth block. Two sizes: `bar` across the top of a test screen, `mark` inline on a score row.
  Always paired with words, never the only signal. `hollow` renders an expired score.
- **Sheet.** A bottom sheet for the glossary word, an enlarged photo and, later, View as FHIR. Focus is
  trapped, Escape closes, `overscroll-behavior: contain`, the trigger gets focus back on close.
- **Row.** A label, a value and an optional gauge at the right. One component for a score line, a
  lesson mark list and, in stage 2, the record timeline and the two observer screen.

## 5. Screens, stage 1

- `/` The two creek photographs, the heading "Which creek is healthier?", one button. Tapping a photo is
  the guess. It is kept in the browser and stored as the warm up answer only after consent.
- Consent. Short paragraphs, two checkboxes, one button, "I agree, start". The bot trap is invisible to
  people and to screen readers.
- Test item. Photo at the top, enlargeable. The question is the page heading. Three buttons stacked.
  Gauge and "5 of 16" at the top. A dotted underline on the one technical word opens the Sheet. The next
  photo is preloaded. On a keyboard, Y, N and C answer.
- Lesson card. Photograph first, tap to reveal the numbered marks, the rule of thumb is the heading. The
  practice photo answers at once, names the cue and marks where it is.
- End screen. Four gauges, one per feature, "Built banks: 4 of 4". One sentence on what the score is
  for. Then the share card. No confetti.
- `/demo` The same screens with feedback after every answer.

Every screen has four states built, not only the happy one: loading is a skeleton in the shape of what
is coming and never a spinner, empty says what this is and how to start, error says what happened and
what to do next and does not apologise, offline says the work is safe on this phone.

## 6. Do and do not

Do: one thing per page. Let the photograph be the biggest thing. Put the primary action in thumb reach.
Say what a button does with a verb and keep that name through the flow. Pair every state colour with an
icon and words. Use tabular figures for counts. Keep the measure under 65 characters.

Do not: colour Yes and No. Put more than one accent on a screen. Use an arrow or a middle dot in a
label. Set a small all caps label above a heading. Put three equal cards in a row. Add a carousel, a
custom cursor, a scroll cue or a version label. Tint a photograph. Use a spinner. Write an error that
says sorry. Ship a screenshot built from boxes.
