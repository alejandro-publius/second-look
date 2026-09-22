# Architecture

The deep version. The README has the three diagrams and the short reasons; this file says what
runs where, what is pure, what may write, and what stops what.

The loop is five verbs, and they line up with OneAquaHealth's own five pipeline stages:

| Verb | Their stage | What happens |
|---|---|---|
| TRAIN | collection | A volunteer passes a two minute photo test. AI takes the same test. |
| CHECK | collection | A guided creek check in the official app's own questions, and a 20 second return check. |
| VERIFY | transformation | Code picks at most two follow-up questions from the answers, the weather and the person's own score. AI may only ask, and only where it passed. |
| RECORD | validation | Every visit becomes FHIR that validates against their guide, carries the observer's score, lands in our store and mirrors to their sandbox. |
| ACT | aggregation and publication | The creek's record turns into what the creek needs and which pipes are worth testing, and into an answer any software agent can fetch with its evidence attached. |

## The whole system

```mermaid
flowchart TB
  subgraph TRAIN["TRAIN: collection"]
    L["Two minute photo lesson<br/>content/lessons.yaml"]
    T["16 item test<br/>core/scoring.py"]
    M["The same 16 items, three models<br/>evals/model_sweep.py"]
    P["Pass table<br/>results/model_pass_table.json"]
    L --> T
    M --> P
  end
  subgraph CHECK["CHECK: collection"]
    F["Guided creek check<br/>content/form.yaml"]
    Q["20 second return check<br/>core/quick.py"]
    W["A walk from your desk<br/>content/walks.yaml"]
    U["Photo upload, metadata cut out<br/>worker/src/uploads.ts"]
  end
  subgraph VERIFY["VERIFY: transformation"]
    R["Rainfall, Open-Meteo<br/>core/rainfall.py"]
    S["Follow-up selector, pure<br/>core/followups.py"]
    G["The gate<br/>core/gate.py"]
    C["Vision checker<br/>core/checker.py"]
    C --> G
    P --> G
    G --> S
    R --> S
  end
  subgraph RECORD["RECORD: validation"]
    E["FHIR emitter<br/>core/fhir_emit.py"]
    V["HL7 validator, their guide at b907cf0<br/>scripts/fhir_validate.py"]
    O["Our store<br/>data/fhir_store"]
    X["Their sandbox, conditional creates<br/>scripts/repush_sandbox.py"]
    E --> V --> O --> X
  end
  subgraph ACT["ACT: aggregation and publication"]
    A["What the creek needs, pipes worth testing<br/>core/act.py"]
    D["Downstream note by reach<br/>core/regions.py"]
    Y["Referral as a ServiceRequest<br/>core/fhir_referral.py"]
    Z["Read only MCP server<br/>apps/mcp"]
  end
  T --> SC["The person's per-feature score"]
  SC --> S
  SC --> E
  F --> S
  Q --> S
  W --> S
  U --> E
  S --> E
  O --> A
  A --> D
  A --> Y
  O --> Z
```

### Why this architecture matters

- **The model is never on the write path.** Its output becomes a `Flag` through `core/gate.py`
  or it is thrown away. A flag can make at most one follow-up question eligible, and only on a
  feature that model passed on the same test the volunteers took. Nothing a model says is ever
  stored as an answer.
- **The parts that decide are pure functions.** `core/followups.py`, `core/gate.py`,
  `core/scoring.py`, `core/act.py` and `core/regions.py` take values and return values. They
  have no database, no clock and no network, so a test can pin every branch, and the same
  functions run in TypeScript on the edge against golden vectors written by the Python.
- **The score travels with the observation.** It is not a badge on a profile page. It is a dated
  `Practitioner.qualification` in the record and a `Provenance` link on every `Observation`, so
  an analyst who receives one observation receives the trust mark with it.
- **Validation is a gate, not a report.** `make check` fails if any emitted resource does not
  validate against the OneAquaHealth guide at the pinned commit. A record that their systems
  could not read never leaves this repository.
- **Every number has one road.** `evals/` write `results/`, `scripts/verify_claims.py` checks
  every number in the README against `results/`, and CI runs it. A number cannot be typed by hand.
- **Two runtimes, one reference.** Python is the reference implementation and the toolchain.
  The Worker's TypeScript reproduces it, and `make check` fails when it does not, so the edge
  is the same function twice rather than a second opinion.

## The FHIR resources, and how they point at each other

```mermaid
flowchart LR
  PR["Practitioner<br/>the volunteer, pseudonymous<br/>qualification = per-feature score"]
  PRL["PractitionerRole"]
  ORG["Organization<br/>Second Look"]
  QR["QuestionnaireResponse<br/>the creek check, their form"]
  QN["Questionnaire<br/>mirrors the official app"]
  OBS["Observation<br/>one per feature<br/>ObservationIndicatorsOah"]
  LOC["Location<br/>the spot, LocationOah<br/>nested: reach, creek, city"]
  PROV["Provenance<br/>who, when, with what score"]
  SR["ServiceRequest<br/>this pipe is worth testing"]
  SPEC["Specimen, SpecimenOah<br/>EXAMPLE only"]
  LIB["Library<br/>our entry on their sandbox"]
  BUN["Bundle<br/>one visit, one transaction"]
  PR --> PRL --> ORG
  QR --> QN
  QR --> LOC
  OBS --> LOC
  OBS --> PR
  PROV --> OBS
  PROV --> QR
  PROV --> PR
  SR --> LOC
  SR --> OBS
  SPEC --> SR
  BUN --> QR
  BUN --> OBS
  BUN --> LOC
  BUN --> PROV
  LIB --> PROV
```

Their profiles are used where they exist and ours only where they do not. Feature answers are
`CodeableConcept`, never booleans, because their `Observation` profile allows only
`CodeableConcept` or `Quantity`. Their `TemporaryOahSystem` codes `present` and `absent` carry
the values. `docs/fhir_mapping.md` has every field.

## The AI gate, step by step

```mermaid
sequenceDiagram
  participant Person
  participant App as Web app
  participant Checker as core/checker.py
  participant Model as Vision model
  participant Gate as core/gate.py
  participant Follow as core/followups.py
  participant Store as FHIR store
  Person->>App: Files a creek check, or opens a walk
  App->>Checker: Photo or frame, and the features to look at
  Checker->>Checker: Refuse any feature this model did not pass
  Checker->>Model: One photo, one question, forced answer
  Model-->>Checker: yes, no or cant_tell, and a note
  Checker->>Gate: Proposed flag
  Gate->>Gate: Shape, feature, pass table, note length, one flag per feature
  Gate-->>Follow: At most one eligible question, or nothing
  Follow->>Follow: Answers, weather and the person's score decide. No model call here.
  Follow-->>App: At most two questions, the model's at most one of them
  App->>Person: "One more look", with the reason in one line
  Person-->>App: The person answers. The model's note is shown as "the checker noticed".
  App->>Store: The record, built from human answers only
  Note over Model,Store: The model never reaches the store. It has no path to it.
```

Three rules hold that shape in place, and each has a test in the same commit as the code:

1. `core/gate.py` turns model output into a `Flag` or rejects it. There is no third outcome.
2. `core/checker.py` returns no flags unless `results/model_pass_table.json` says `real: true`,
   so a synthetic pass table can never license a flag in production.
3. `core/followups.py` is a pure function of answers, site context, scores and flags, with a cap
   of two questions and no model call inside it.

## Where things run

| Piece | Runtime | Notes |
|---|---|---|
| Web app | Static export on Cloudflare Pages | Next.js App Router, no server, strict CSP written by `apps/web/security-headers.mjs` |
| Study and judge API | TypeScript Worker on D1 and KV | `worker/src`, ported from the Python and held to golden vectors |
| Reference API | FastAPI on SQLModel | `apps/api`, the local and test runtime, and the reference for the port |
| Pure logic | Python, mirrored in TypeScript | `core/`, `worker/src/core/` |
| Evals | Python, Batch API | `evals/`, writes `results/`, never called from the app |
| FHIR toolchain | SUSHI 3.20.1 and the HL7 validator in Docker or CI | `fhir/`, pinned in `fhir/ig.lock` |
| MCP server | Python over stdio | `apps/mcp`, read only, five tools |

## What is deliberately not here

- No account, no login and no email anywhere in the product.
- No third party origin in the study flow. The map tile server in the creek check is declared in
  `docs/DATA_HANDLING.md` and is the only exception.
- No rate limit on the deployed Worker, because a Worker has no shared memory and every other way
  to count a visitor means holding something that identifies them. The hidden field, the 40 second
  rule, one arm per browser and Cloudflare's own edge protection stand in its place.
- No model call in the request path of the creek check. The checker runs on the photos a person
  uploads, and its flags reach the person only through the gate.
