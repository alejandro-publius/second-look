# The official app's translations, checked for meaning

The creek check offers the official app's own translations (content/app_strings.json, from the
bundle named in docs/notes/app_strings.md). Before any of them reached the screen, a reviewer that
had written none of them read every translated string beside the English and asked one thing: would
a volunteer reading this answer a different question from one reading the English? Style, word
order, formality and gendered forms were not flagged. The removed answer letters and the removed
note about the app's example pictures were ignored, as they are the same edit in every language.

Checked on 2026-09-26 against bundle sha256 c5a15e8ebf91: 107 strings in each of
Portuguese, Dutch, Norwegian, French and Italian. Greek is in the bundle but carries none of the
assessment questions, so the creek check does not offer it.

What happens to a flagged string: it falls back to English in that language, with a small
"English" tag, and the reason is kept beside it in `fallback` in content/app_strings.json. The
rest of that question stays in the app's own words. When the app fixes a string, `make
app-strings-check` goes red, and the fallback can be lifted after a person reads the new words.
The organizers get the list in a short message (docs/internal/MESSAGE_TRANSLATIONS.md) for Alex
to post.

Added on 2026-09-29, same bundle: the plant list under "Which ones?" ends on a not sure answer.
It now shows the app's own words for it, the not sure answer of the app's invasive species
question, which "Which ones?" is the placeholder of. These are the five strings already read on
2026-09-26 for that question (pt "Não tenho a certeza", nl "Ik weet het niet zeker", no "Jeg er
ikke sikker", fr "Je ne suis pas sûr-e", it "Non sono sicuro"). Our English for it stays "Can't
tell". Each was read again beside "Can't tell": all five say the person is not sure, which is
the same answer. None flagged.

## Flags


| lang | item | field | translated | back-translation | English | how the meaning differs | conf. |
|---|---|---|---|---|---|---|---|
| fr | draining_pipes | text | Y a-t-il des canalisations qui déversent des eaux pluviales dans le cours d’eau ? | Are there pipes that pour rainwater (stormwater) into the watercourse? | Are there pipes draining polluted water into the stream? | Asks about rainwater pipes instead of polluted water, so a clean storm drain counts as yes. | high |
| it | draining_pipes | text | Ci sono tubi che scaricano l'acqua piovana nel fiume? | Are there pipes that discharge rainwater into the river? | Are there pipes draining polluted water into the stream? | Asks about rainwater instead of polluted water. | high |
| fr | construction | text | Y a-t-il des travaux de construction dans ou autour du cours d’eau ? | Is there any construction work in or around the watercourse? | Is there any construction/works in stream? | Widens "in stream" to "in or around", so works on a nearby road count as yes. | high |
| it | bank_type | text | I banchi del canale sono... | The shoals (bars, benches) of the channel are... | The banks of the channel are… | "Banchi" is a false friend meaning shoals or benches (the same word as the "sand banks" habitat), not river banks. | medium |
| nl | habitats | option:riffles | Geultjes, stroomversnellingen, watervallen | Small gullies (small channels), rapids, waterfalls | Riffles, rapids, falls | "Geultjes" are small gullies or channels, not riffles. | medium |
| no | habitats | option:riffles | Strømvirvler, stryk, fosser | Current eddies (whirlpools), rapids, waterfalls | Riffles, rapids, falls | "Strømvirvler" are eddies (slow swirling water), not riffles. | medium |
| it | habitats | option:riffles | Ruscellamenti, rapide, cascate | Surface runoff, rapids, waterfalls | Riffles, rapids, falls | "Ruscellamenti" is runoff over land, not riffles in the stream. | medium |
| no | vegetation_type_left | option:herbs | Ugress | Weeds | Herbs | "Ugress" means weeds (unwanted plants), not herbaceous plants as a growth form. | medium |
| no | vegetation_type_right | option:herbs | Ugress | Weeds | Herbs | Same as the left side. | medium |
| pt | vegetation_type_left | text | Que tipo de vegetação é dominante (mais de 50%) na margem esquerda (primeiros 5 metros)? | What type of vegetation is dominant (more than 50%) on the left margin (first 5 metres)? | ...in the left margin (first 5 meters from the channel banktop)? | Drops "from the channel banktop", so the 5 m will likely be counted from the water edge. | medium |
| pt | vegetation_type_right | text | Que tipo de vegetação é dominante (mais de 50%) na margem direita (primeiros 5 metros)? | What type of vegetation is dominant (more than 50%) on the right margin (first 5 metres)? | ...in the right margin (first 5 meters from the channel bank/top)? | Same as the left side. | medium |
| pt | sewage_discharge | text | Há alguma entrada ou descarga de esgotos? | Is there any inflow or discharge of sewage? | Is there any kind of water entry or discharge of sewage? | Sewage only; drops "any kind of water entry", which fr, it and no keep. The English is itself ambiguous. | medium |
| nl | sewage_discharge | text | Is er sprake van watertoevoer en -afvoer van rioolwater? | Is there inflow and outflow of sewage water? | Is there any kind of water entry or discharge of sewage? | Sewage only, and "and" instead of "or"; "afvoer" can also read as sewage carried away. | medium |
| no | feelings | option:anger | Raseri | Rage (fury) | Anger | Much stronger than anger, so a volunteer who is only angry or annoyed may not pick it. | medium |

## Untranslated

None. Three translated strings match the English exactly, but each is a real word in its own language: pt "Natural", no "Flat", it "No".

## Counts per language

- pt: 107 strings checked, 3 flagged
- nl: 107 strings checked, 2 flagged
- no: 107 strings checked, 4 flagged
- fr: 107 strings checked, 3 flagged
- it: 107 strings checked, 3 flagged
- Total: 535 strings checked, 14 flagged (3 high, 11 medium), 0 untranslated

## Looked at but not flagged (low confidence)

- fr habitats riffles "Rapides, cascades, chutes d’eau" leaves out riffles, but rapids is close enough.
- fr feelings "Sérénité / bien être" and "Anxiété / peur" add well-being and anxiety. Both are a bit broader, but they still contain the English meaning.
- fr, pt and no use the same word for the channel "banks" and the "margins" (berge, margem, kant). This matches how rivers are usually described in those languages, and the section title gives the 5-10 m zone.
- nl "linkermarge" / "rechtermarge" and "rivierzone" are odd word choices, but left and right and the 5-10 m zone are kept.
- nl construction "Worden er werkzaamheden ... uitgevoerd" covers only ongoing works. The English is ambiguous on this, and most other languages read it the same way.
- nl water_withdrawal joins collection, use and removal with "en" (and). A volunteer would most likely still answer yes to any one of them.
- no natural_debris "naturlig avfall" (natural waste) is clear once the answer options are shown.
- fr water_height_m "profondeur" (depth) is a reasonable reading of "water height".
- fr bottom_type drops "wet", pt vegetation_cuts drops "(or just one of the banks)" and pt water_withdrawal drops "use". Each omission is small, and the question is unchanged.
