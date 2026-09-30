# The official app's own words

The creek check quotes the OneAquaHealth Citizen Science App word for word. The app ships its
translations to any browser in a public JavaScript chunk; nothing here needed a login, and none was
used. The words belong to the OneAquaHealth project, not to us, and are not covered by this
repository's MIT licence. The creek check credits them to the OneAquaHealth Citizen Science App on
its first screen, and `content/app_strings.json` and `content/form.yaml` credit them where they
are kept. A FHIR record names each item by the app's short name, such as Water Flow, without a
credit line of its own.

| | |
|---|---|
| Bundle URL | https://apps.oneaquahealth.eu/_nuxt/i18n.config.bcYbKmN2.js |
| Fetched | 2026-09-26 |
| SHA-256 | `c5a15e8ebf913c49e03ec6d71716361126301187407d4a12cd6bf4c8bd9eff51` |
| Languages in the bundle | Greek, English, French, Italian, Dutch, Norwegian, Portuguese |
| Languages with the assessment questions | English, Portuguese, Dutch, Norwegian, French, Italian |

The bundle itself is never committed. `scripts/app_strings.py write` fetches it, reads its object
literal as data (a small parser; no code from the bundle runs), and keeps only the strings the
creek check quotes, each with the app key it came from, in `content/app_strings.json`. `make
app-strings-check` fetches it again and fails if any quoted string has changed; it needs the
network, so it is its own line in the done list rather than part of `make check`.

## What is quoted

Every item of `content/form.yaml`: the question the app shows (`questiontext`, or for the two
pick-several items the app's own yes or no line, `questiontextshow`), the app's short name for it
(`question`, used as the FHIR Observation's code text), every answer, the three overall ratings with
their descriptions, the four feelings, and the section titles "What do you see from where you
stand" and "In the margins/riparian zone". The plant list under "Which ones?" ends on the not
sure answer of the app's invasive species question. The yes or no answers are the app's per item. Each item
is marked `verified_against_app: true` with `source: app public bundle, c5a15e8ebf91, 2026-09-26`,
and a test (`scripts/tests/test_app_strings.py`) holds the form's English to the quoted English.

Six buttons and labels are quoted too, in the five other languages: Back (the app's Previous),
Next, Send (the app's Submit), Latitude, Longitude and the name of the spot (the app's Site
Name). In English these six stay our own words. The app's English is kept in the file so the
check can see it change, but it is never shown: its longitude label reads "Logitude".

Three edits, the same in every language, all made by `tidy()` in the script:

1. The answer letters, such as "(A)", are dropped. They point at the app's example pictures,
   which we do not show.
2. The barriers question drops "(see some examples in images provided)", for the same reason.
3. A typographic dash inside a quoted string becomes a plain hyphen (one Norwegian title), since
   the repository has none (CLAUDE.md rule 18).

The app's own spelling is kept, including "Layed stones" and "recent cuts if vegetation"; both are
in the note to the organizers.

## What stays ours

The words around the questions, apart from the six above: the other buttons (Skip, None of
these, Finish, Start the check, Add a photo), the follow-up questions, the health card and the
notes. They have no checked translation yet, so in another language they show in English: a
question, note or follow-up carries a small "English" tag, and a button in English carries
`lang="en"` for screen readers. Three of our five section titles are ours as well; in another
language they are left out, since an English line right above a translated question read as
the question shown twice. The four test questions in `content/features.yaml` belong to the frozen two-minute
test and are unchanged; the dug-out channel question there is ours by design, as the app has no
matching item, and the creek check has no dug-out item.

## Translations

The creek check and the walks offer every language above. With no language picked yet, they
open in the first of the browser's own languages that the app has, else in English. Before any
translation reached the screen it was read beside the English for meaning; 14 strings differ
and fall back to English in their language. See `docs/notes/app_translations.md`. A record
reads the answers back in the language they were given in, and says which one in the
`language` of its QuestionnaireResponse.

## History: the Sep 20 check of the four test questions


| Our feature | Our question | App item | Verbatim? |
|---|---|---|---|
| `invasive_plant` | Do you see any non-native or invasive plant species? | `invasive_species` | **Yes, word for word** |
| `pipe_running` | Are there pipes draining polluted water into the stream? | `draining_pipes` | **Yes, word for word** |
| `artificial_bank` | Are the banks artificial, such as concrete or stones set in concrete? | `bank_type` | **No.** See below |
| `dug_out_channel` | Does this channel look dug out or straightened? | none | Ours by design |

Two of the three are exact, so they are marked `verified_against_app: true` with this date.

**`artificial_bank` is not, and it cannot be.** The app does not ask a yes or no question about
banks. It makes a statement, "The banks of the channel are...", and offers Natural (A) or
Artificial (concrete or stones with concrete) (B). Our test needs a yes or no, so our wording
turns their option into a question and keeps their own words for what artificial means: "concrete
or stones with concrete". That is as close as a yes or no question can get to their text.

This needs one decision from a person, and it is left open on purpose:

- **Keep ours**, "Are the banks artificial, such as concrete or stones set in concrete?", and say
  in the plan that it is derived from the app's `bank_type` option text rather than quoted from a
  question. Nothing else changes.
- **Or match their shape**, "The banks of the channel are artificial, with concrete or stones set
  in concrete", answered Yes, No, Can't tell. Closer to their text, reads less like a question.

Until that is settled, `artificial_bank` stays `verified_against_app: false`, which is honest:
there is no app question to have verified it against.

## The one that is ours

`dug_out_channel` has no app item. Their `channel_form` asks for Flat, U or V shape, which is a
different thing from whether a channel was dug out or straightened. Update 09 section 1 says to
use our own wording here, and we do.

## Laid stone

Their bank options offer only Natural or Artificial (concrete or stones with concrete). Their own
Field Sampling Protocols, page 13, are finer: Earth/soil, Layed Stones, Gabion, concrete. Laid
stone is a category of its own there, which is why no laid stone photo goes into the test set.
See `docs/notes/zenodo.md`.
