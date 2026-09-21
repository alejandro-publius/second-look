# The official app's own question wording

Pulled on 2026-09-20 from the Citizen Science app's public i18n bundle, `chunk_i18n.config`,
served by https://apps.oneaquahealth.eu . No login and no API were used: this is the text the app
ships to any browser that loads the page. Saved locally at
`~/scratch/oah-research/chunk_i18n.config.bcYbKmN2.js`.

Quoted exactly, keys as the bundle names them.

| App item | question | questiontext | answers |
|---|---|---|---|
| `bank_type` | Bank Type | The banks of the channel are... | Natural (A); Artificial (concrete or stones with concrete) (B); I am not sure |
| `bottom_type` | Bottom Type | The bottom of the wet channel is... | Natural (A); Artificial (concrete or stones with concrete) (B); I am not sure |
| `channel_form` | Channel Form | The channel form is... | Flat (A); U Shape (B); V Shape (C); I am not sure |
| `invasive_species` | Invasive Species | Do you see any non-native or invasive plant species? | Yes; No; I am not sure. Free text: "Which ones?" |
| `draining_pipes` | Draining Pipes | Are there pipes draining polluted water into the stream? | Yes; No; I am not sure |
| `sewage_discharge` | Sewage discharge | Is there any kind of water entry or discharge of sewage? | Yes; No; I am not sure |

## How our four questions line up

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
