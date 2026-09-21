# Second Look: mammoth prompt 6 (the design pass)

Start a fresh window with `cd ~/second-look && claude`, then paste this whole text. Everything below is addressed to Claude Code.

Read `CLAUDE.md`, `PLAN.md` and `docs/HANDOFF_NEXT.md` first, and nothing else yet. An earlier message parked the design pass. That is lifted for this session, for Stage 1 only (section 7).

## 0. What this is

Alex has a set of design skills installed in his Claude chats: an anti-slop frontend skill, Anthropic's frontend design skill, Vercel's web interface guidelines, a collection of DESIGN.md reference systems, and skills for UX copy, accessibility review and design critique. The planner read all of them and distilled what applies to this product into this text. Save it as `docs/updates/UPDATE_06.md`. Where it disagrees with earlier files on how things look, read or feel, this file wins. It changes no rule about privacy, the gate, the analysis or FHIR.

If any skill with one of these names is available in this terminal, use it as well: `design-taste-frontend`, `frontend-design`, `web-design-guidelines`, `awesome-design-md`, `ux-copy`, `accessibility-review`, `design-critique`. If none is, this text is enough.

Two open sources you can fetch yourself, both MIT licensed. Record them in `docs/THIRD_PARTY.md` as references:

- Vercel's Web Interface Guidelines: `https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md`. Fetch it and audit `apps/web` against every rule, with findings as `file:line`.
- VoltAgent's DESIGN.md collection: `https://github.com/VoltAgent/awesome-design-md`. Read the Airbnb file for how a product lets photographs lead, and the Wise file for how forms stay clear and friendly. Borrow structure and restraint. Take no brand colours, names, logos or fonts.

Also create `docs/CONTEXT_LEDGER.md`, 30 lines at most, project facts only, so any future session can pick them up: the design skills named above exist on the planning side; Figma is connected on the planning side; Alex is a native Spanish speaker and checks every Spanish string himself; Rachel owns ecology copy and labels; the repo stays private until submission day.

## 1. Design read

Reading this as: a phone-first field tool and a two-minute test for ordinary adults standing outdoors, judged by ecologists, digital health people and standards engineers, with a trust-first, plain, photograph-led language, built on Tailwind v4 with accessible primitives and our own tokens.

Dials: layout variance 3, motion 2, density 4. This is a public-interest tool, not a marketing site. Calm beats clever on every screen except one: the opening question.

Spend the boldness in one place. The memorable thing is the staff gauge, the striped measuring stick that surveyors stand in a stream. It is our progress bar in the test ("5 of 16") and our score mark on every record ("4 of 4"). It says measurement without a word. Everything around it stays quiet.

## 2. Tokens

Put these in `apps/web/styles/tokens.css` as CSS custom properties and map them into the Tailwind theme. No colour, size or radius appears in a component as a raw value.

Colour. The obvious palette for a nature app is leaf green and water blue, which is why we do not use it. The palette comes from survey gear: overcast paper, deep ink, and the orange of a survey flag, which is also the easiest colour to find in sunlight. Contrast ratios below were computed by the planner.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#F4F6F5` | `#0F1715` | page |
| `--surface` | `#FFFFFF` | `#16211E` | sheets, cards |
| `--ink` | `#14211E` | `#E8EEEB` | text, focus rings. 15 to 1 on the page |
| `--ink-soft` | `#4B5B57` | `#A9B8B3` | secondary text. 7 to 1 on white |
| `--line` | `#D5DCD9` | `#2A3733` | hairlines. Control borders use a darker step that reaches 3 to 1 |
| `--flag` | `#F26B1D` | `#FF8A3D` | the one accent: primary button, gauge fill, selected state |
| `--ok` `--warn` `--bad` | `#1F7A4D` `#9A4A06` `#B42318` | lighter steps | state only, always with an icon and words, never colour alone |

Text on the orange is always `--ink` (5.4 to 1). White on the orange fails and is banned. One accent for the whole product. No gradients. No pure black. Shadows, where a sheet needs one, are tinted with the ink colour.

Type. Atkinson Hyperlegible Next for everything, self-hosted through `next/font` so no request leaves our origin. It was drawn for low-vision readers and holds up in sunlight, which is the point. Its mono cut is allowed only inside the View as FHIR sheet. Body is 18px on phones, 1.5 line height, lines under 65 characters. Headings 24, 30 and 38. Sentence case everywhere. No all-caps labels, no small labels above headings, no single word in a headline set in italic or colour for effect.

Shape and space. One radius, 12px, for photos, sheets, buttons and inputs. The gauge has square ends. A 4px spacing grid. Tap targets 48px or more. Primary actions sit at the bottom of the screen inside the safe area, in reach of a thumb.

Icons. Phosphor, regular weight, one family. No emoji. No hand-drawn SVG icons.

Motion. 150 to 200ms ease-out on presses and sheets. One orchestrated moment in the whole product: the answer to the opening question. With reduced motion set, everything is instant.

Dark mode follows the system, uses the dark tokens, and is tested on every screen. Photos are never tinted.

## 3. Patterns, screen by screen

Test and form screens follow the public-service pattern of one thing per page: the question is the page heading, the choices are large buttons, Back is a plain link at the top left, progress is words plus the gauge.

- `/` landing. On a phone, above the fold: the two creek photos, the heading "Which creek is healthier?", and one button, "Find out in two minutes". A small wordmark and an About link. Nothing else. Tapping a photo counts as the person's guess. It is kept in the browser and stored as the warm-up answer only after consent. Add that sentence to `docs/analysis_plan.md` before the tag: "The warm-up choice is made on the landing page and stored only after consent."
- Consent. Short paragraphs, the two checkboxes, one button, "I agree, start". The hidden bot field is invisible to people and to screen readers.
- Test item. The photo fills the top of the screen and can be enlarged. Under it the question as the heading, then three buttons of equal weight stacked in a fixed order: Yes, No, Can't tell. Never colour them green and red. The gauge and "5 of 16" sit at the top. A dotted underline on the one technical word opens a bottom sheet with one plain sentence. The next photo is preloaded. On desktop, Y, N and C work as keys.
- Lesson card. Photo first. Tap to reveal numbered marks on the photo, each with a label of five words or fewer ("Concrete under the ivy"). Marks come from the lesson YAML as x and y fractions plus a label, so Rachel places them without code. The rule of thumb is the card's heading, 12 words or fewer. The practice photo gives feedback at once, names the cue and marks where it is. The alt text lists the same marks in words.
- End screen. Four gauges, one per feature, with "Built banks: 4 of 4". One sentence on what the score is for: it is saved with every creek check the person makes for the next 90 days. Then the share card. No confetti.
- `/demo`. The same screens, with feedback after each answer, ending on the lessons the judge needs.
- `/check`. One question per page, a camera button that leads to a preview with "Use this photo" and "Retake", answers saved as they go, a "Check your answers" page with a Change link per row, then a confirmation page that says what happens next and shows the health card. A follow-up question arrives under a quiet heading, "One more look", with its reason in one line: "It has not rained here for 9 days."
- Offline. A small persistent line: "Saved on this phone. It will send when you are back online."
- `/spot/[id]`. A timeline of visits. Each answer is a row: the question, the answer, and at the right a small gauge with "4 of 4" and the test date. An expired score is a hollow gauge. One toggle filters to people who passed that feature. View as FHIR opens a sheet.
- `/two`. One row component used twice: "Lab result, Almyros" beside "Volunteer answer, Strawberry Creek". Side by side on a wide screen, stacked on a phone.
- `/poster`. The question in very large type, the two photos, a QR code with its quiet zone, one orange band, the gauge along one edge. It must still read when printed in grey.
- README. Real screenshots taken by Playwright at phone size. No fake screens built from boxes. One architecture diagram in Mermaid.

Every screen has four states designed, not only the happy one: loading (a skeleton in the shape of what is coming, never a spinner), empty (what this is, why it is empty, how to start), error (what happened, why, how to fix it, no apology), offline.

## 4. Words on screens

- A button says what it does, starts with a verb, and keeps the same name through the flow: "Start the test", "Use this photo", "Send my check".
- An error says what happened, why, and what to do next.
- Name things the way a visitor would. They "check a creek". They do not "submit an assessment".
- No arrows stuck on the end of button labels. No strings joined with middle dots. No "Step 1, Step 2" labels: the step's own verb is the label.
- Spanish moves from COULD to SHOULD. Draft `es` strings, mark the file unverified, and keep it out of the build until Alex signs it with his name and the date.
- Read every string aloud in your head. If it could sit in any app, make it specific or cut it.

## 5. Accessibility and speed

- WCAG 2.2 AA. Visible focus rings in `--ink`. A logical focus order. Landmarks. Labels above inputs, never placeholder text as a label. Layout holds at 200 percent zoom. Do one VoiceOver pass on the test flow and write what it announced in `docs/reviews/VOICEOVER.md`.
- A photo test cannot be fully accessible to someone who cannot see the photos. Say so plainly on `/about`, and make sure everything around the photos works with a screen reader.
- Budgets on a throttled 4G profile with a 4x slower CPU: the landing page's largest paint under 2.5 seconds, layout shift under 0.05, and no more than 25 KB compressed of OUR code on the landing route, measured as the chunks the landing loads that Next's own not found page does not. The framework baseline has its own ceiling, because a client import can land in a shared chunk every page loads. The landing page renders fully with the API asleep. Photos served as AVIF or WebP at several widths, with a tiny blurred preview made at ingest. **Superseded by docs/updates/UPDATE_07.md section 1: the flat 90 KB total is gone, because the App Router floor alone is above it and the front door is not being rebuilt nine days out.** The check is `make budget`.

## 6. Banned, and checked by machine

Add `make design-check` to `make check`. It fails on any of these in `apps/web` or `content/`:

- an em dash or en dash, an emoji, a middle dot used as a separator, an arrow inside a button label
- `uppercase` together with wide letter spacing (the small label above a heading)
- `lucide-react`, more than one icon family, an inline hand-drawn icon
- Inter or any font loaded from another origin
- `#000`, a CSS gradient, a glow, a raw hex colour or pixel radius outside `tokens.css`
- an input without a label, a control whose text and background tokens fall under 4.5 to 1 (compute it from the tokens), a tap target under 44px measured by Playwright on the phone viewport
- three equal cards in a row, a carousel, a custom cursor, a scroll cue, a version label, a fake screenshot built from boxes

## 7. How to run this pass, and what it may cost

The pass runs in two stages so tokens go where people will look first.

- **Stage 1, this session: the launch path.** Steps 1 and 2 below, then restyle only `/`, consent, the test item, the lesson card, the end screen and `/demo`. These are the screens strangers see on Wednesday and judges see first. Screenshots and the critic cover these screens only, 8 screenshots at most. `make design-check` goes into `make check` now, with the tap-target measurement limited to these screens.
- **Stage 2, parked until Alex says the features are frozen:** `/check`, `/spot`, `/two`, `/quick`, `/poster`, the README screenshots, dark mode beyond the test flow, the VoiceOver write-up and the Spanish draft. Section 3 is still the spec for them. Do not start them in this session.

1. Write `docs/design/DESIGN.md` first: the design read, the tokens, the components, do and do not, in under 150 lines. Check it against this text. Where it looks like what you would make for any app, change it and say what you changed.
2. Build the tokens and the six shared components: button, choice list, photo frame with marks, gauge, bottom sheet, row. Then restyle the screens in the order of section 3.
3. Take Playwright screenshots of the Stage 1 screens at 390 by 844 in light mode into `docs/screens/`, plus the test item in dark mode and `/` on desktop.
4. One critic subagent that wrote none of the UI looks at no more than 8 screenshots, runs the Vercel guidelines audit over the code, and writes `docs/reviews/DESIGN_REVIEW_01.md`: what works, what fails, ranked, each with a fix. It answers three questions by name: would a stream ecologist trust this, could a 60 year old use it one-handed in sunlight, and does any screen look like a template.
5. Fix the ranked list from the top. Retake only the screenshots that changed.
6. Two subagents at most. Do not open image files you do not need to look at. Rely on the machine checks for the rest.

## 8. Report

Write the report file, copy it to the clipboard with `pbcopy`, and print only the report block. Include the output of `make design-check`, the three budget numbers, the top five findings of the design review with what you did about each, the path to the screenshots, and what is left for Stage 2. Then stop and tell Alex it is a good moment to close the window.
