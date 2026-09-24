<!--
The source of docs/REPORT.pdf. make report-pdf reads this file, puts in each section it names
from the README and the docs, fills each {{claim:...}} from results/, and prints the result with
pandoc and Chromium. Edit the words here or in the named sections, never the PDF. A line that is
only {{section:FILE#Heading}} is replaced by the text under that heading, up to the next heading
of any level.
-->

## Abstract

Citizen observations of creeks are uneven. People notice smell, foam and colour and walk past
concrete banks, dug-out channels, plants that do not belong and pipes. Second Look measures that,
per person and per feature, with a two-minute test on
{{claim:results/model_card.json#/benchmark/photos}} real photos, and stores the score with every
observation the person later makes, in OneAquaHealth's own FHIR profiles. Vision models take the
same test. A model may only ask a volunteer to look again, on a feature it passed, after the person
has answered; code, never the model, writes the record. Four Claude models took the test three
times each. Every model passed built banks, and no model passed plants that do not belong, where
almost every answer was "can't tell": the plant photos show no water, and the instruction says to
answer can't tell when no stream is in view. On
{{claim:results/footage_pool.json#/frames_kept}} frames of open creek footage the gate dropped
{{claim:results/footage_latest.json#/gate/dropped}} of
{{claim:results/footage_latest.json#/gate/candidates}} candidate flags, each on a feature that model
had not passed. The HL7 validator found {{claim:results/fhir_validation.json#/errors}} errors in
{{claim:results/fhir_validation.json#/files_validated}} records checked against OneAquaHealth's
guide. No person has taken the test yet, and this report makes no claim about people; a paid research panel may add sessions before the lock, and they would be reported once, after it.

## 1. The problem

{{section:README.md#Why trust a volunteer, and the AI?}}

## 2. Method

{{figure:docs/diagrams/ai-gate.svg|How a model's answer becomes a flag, or nothing}}

### 2.1 The test

Sixteen photos, four per feature, two with the feature and two without, in a new random order for
each person. The answers are Yes, No and Can't tell, and Can't tell counts as wrong. The score is
kept per feature, out of 4, and stored in the record of the test sitting; a dated qualification
for the test and a Provenance link carry it to every Observation the person makes. The question
wording and the analysis were written into `docs/analysis_plan.md` and tagged `prereg-v1`, and
the key was frozen as a hash in `results/key_hash.json`, on Sep 21, the day the test opened, before
the first paid model run on Sep 23. The dates here are Pacific time.

### 2.2 The gate

{{section:README.md#The gate, the heart of it}}

In the build measured here, {{claim:results/footage_pool.json#/walks_with_a_checker_question}} of
the {{claim:results/footage_pool.json#/walks}} walks carries a checker question: the gate kept no
flag on the frames the walks use (`content/walks.yaml`). So today no model flag reaches a person,
in the walks or on the live site.

### 2.3 What the AI cannot do

{{section:README.md#What the AI cannot do}}

## 3. Evidence

All numbers below come from files in `results/`, written by the scripts in `evals/` and checked
against the text by `scripts/verify_claims.py` in CI. Failed runs stay in `results/` too.

### 3.1 The models on the test and on footage

{{section:README.md#The AI, on the same 16 photos and on real creek footage}}

### 3.2 The benchmark and its size

{{section:docs/MODEL_CARD.md#The benchmark and its size}}

### 3.3 How the models fail

{{section:docs/MODEL_CARD.md#Known failure modes}}

### 3.4 Cost

{{section:docs/MODEL_CARD.md#Cost}}

## 4. The FHIR mapping

{{figure:docs/diagrams/fhir-graph.svg|The records one visit makes, and how the score reaches every Observation}}

{{section:README.md#How OneAquaHealth is used}}

One creek visit becomes these resources (`docs/fhir_mapping.md`):

{{section:docs/fhir_mapping.md#What one visit produces}}

{{section:docs/fhir_mapping.md#Codes: theirs where they exist, ours where they do not}}

## 5. Limitations

{{section:README.md#Known weaknesses}}

The labels have a limit of their own. The test key came from the photo picks, with one labeller,
and no blind second label exists yet (`docs/DATA_CARD.md`). Until one does, read every accuracy
figure here as agreement with this key.

## 6. Contributions

1. **A measured observer, carried in the record.** A two-minute test gives each volunteer a score
   per feature, and OneAquaHealth's own profiles carry it, through a qualification and Provenance,
   to every Observation that person makes. A city analyst reads each answer beside how well its
   observer sees.
2. **A model that may ask and never decide.** A model is licensed feature by feature by the same
   test people take, from a committed pass table. Its output becomes a flag through one gate or is
   dropped, and the record is built from human inputs only.
3. **Measurement that shows its failures.** The pass table, the benchmark with its intervals, the
   run that measured our own config, and the plant photos that no model could judge are all in
   `results/`, with the cost of every call.
4. **Open work, and work given back.** The code is MIT. What we contributed back, as the README lists it:

{{section:README.md#Contributed back}}

## 7. How to check this report

- `make judge-check` runs the tests with no key and no network.
- `make verify-claims` checks every number in the README and the docs against `results/`.
- `make report-pdf` builds this file again from its sources; a test fails when the PDF is older
  than the README sections and results it was built from.
- The model card, the data card and the threat model are `docs/MODEL_CARD.md`,
  `docs/DATA_CARD.md` and `docs/THREAT_MODEL.md`.

AI coding tools wrote most of the code and the text, from written briefs, and every change was
checked by `make check` before it was committed. The people set the direction and made every
decision that needs a person, as the README says under "How this was built".
