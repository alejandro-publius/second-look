# Architecture

The deep version. The README has the four diagrams and the short reasons; this file says what
runs where, what is pure, what may write, and what stops what.

The loop is five verbs, and they line up with OneAquaHealth's own five pipeline stages:

| Verb | Their stage | What happens |
|---|---|---|
| TRAIN | collection | A volunteer passes a two minute photo test. AI takes the same test. |
| CHECK | collection | A guided creek check in the official app's own questions, and a three-question return check. |
| VERIFY | transformation | Code picks at most two follow-up questions from the answers, the weather and the person's own score. AI may only ask, and only where it passed. |
| RECORD | validation | Every visit becomes FHIR that validates against their guide, carries the observer's score, lands in our store and mirrors to their sandbox. |
| ACT | aggregation and publication | The creek's record turns into what the creek needs and which pipes are worth testing, and into an answer any software agent can fetch with its evidence attached. |

## The loop, in five boxes

The same five verbs as one line, drawn from [`docs/diagrams/loop.mmd`](diagrams/loop.mmd).

```mermaid
flowchart LR
  accTitle: The loop in five verbs, Train, Check, Verify, Record and Act
  accDescr: A volunteer trains and takes the photo test, and its per-feature score comes out. On a creek check they answer first, with at most two follow-up questions chosen by code. The answers, with the score, become a FHIR record checked against OneAquaHealth's guide. The records say what the creek needs, in OneAquaHealth's own measures, and which pipes are worth a lab test. A model may raise a question only on a feature it passed on the same test.
  TRAIN["TRAIN<br/>the two-minute photo test"]
  CHECK["CHECK<br/>the guided creek check"]
  VERIFY["VERIFY<br/>follow-ups and the gate"]
  RECORD["RECORD<br/>FHIR under their guide"]
  ACT["ACT<br/>what the creek needs"]
  TRAIN -- "a score<br/>per feature" --> CHECK
  CHECK -- "the person's<br/>answers" --> VERIFY
  VERIFY -- "answers,<br/>score, flags" --> RECORD
  RECORD -- "records<br/>by creek" --> ACT
```

## The whole system

Every edge says what flows along it. Where a part is a `core/` file, the live site runs its
TypeScript port in `worker/src/core/`, held equal to the Python by golden vectors. The same
diagram as an image: [`docs/diagrams/system-map.svg`](diagrams/system-map.svg), drawn from
[`docs/diagrams/system-map.mmd`](diagrams/system-map.mmd) by `make diagrams-render`.

```mermaid
flowchart TB
  accTitle: The system map, by the five verbs Train, Check, Verify, Record and Act
  accDescr: A volunteer takes the photo test on /t and the Worker keeps the per-feature score in D1. Vision models take the same test, and the pass table says which features each may flag. On /check the Worker hands the answers, the dry days and the person's score to the follow-up selector, which returns at most two questions. The finished visit becomes a record of human answers only, then a FHIR Bundle stored in D1, checked by the HL7 validator in CI and mirrored to their sandbox. From the stored visits, core/act.py works out what the creek needs and which pipes are worth testing, a pipe becomes a ServiceRequest, and the read only MCP server hands any agent the same records with their ids.
  subgraph TRAIN["TRAIN: collection"]
    TPAGE["/t, the photo test<br/>apps/web/app/t"]
    SWEEP["Vision models take the same test<br/>evals/model_sweep.py"]
    PASS["Pass table<br/>results/model_pass_table.json"]
  end
  subgraph CHECK["CHECK: collection"]
    CPAGE["/check, the guided creek check<br/>apps/web/app/check"]
    QPAGE["/quick, the return check<br/>apps/web/app/quick"]
    WPAGE["/walk, a creek from your desk<br/>apps/web/app/walk"]
  end
  WORKER["The Worker, every /api route<br/>worker/src/index.ts on Cloudflare"]
  D1[("D1 database<br/>sessions, observers, visits, Bundles")]
  KV[("KV<br/>uploaded photos")]
  METEO["Open-Meteo"]
  subgraph VERIFY["VERIFY: transformation"]
    RAIN["Dry days<br/>core/rainfall.py"]
    FOLLOW["Follow-up selector, pure<br/>core/followups.py"]
    GATE["The gate<br/>core/gate.py"]
    CHECKER["Vision checker, off on the live site<br/>core/checker.py"]
    WALKS["Walk builder<br/>scripts/build_walks.py"]
  end
  subgraph RECORD["RECORD: validation"]
    BUILD["Record builder<br/>build_record in core/gate.py"]
    EMIT["FHIR emitter<br/>core/fhir_emit.py"]
    VALID["HL7 validator, their guide at b907cf0<br/>scripts/fhir_validate.py in CI"]
    LIB["Our Library entry<br/>core/fhir_library.py"]
    MIRROR["Sandbox mirror<br/>scripts/repush_sandbox.py"]
  end
  SANDBOX["Their sandbox<br/>OneAquaHealth FHIR server"]
  subgraph ACT["ACT: aggregation and publication"]
    REGIONS["Creek and reach of each spot<br/>core/regions.py"]
    ACTF["What the creek needs, pipes worth testing<br/>core/act.py"]
    REFER["Referral<br/>core/fhir_referral.py"]
    VIEWS["/spot, /city and /two<br/>apps/web/app"]
    MCP["Read only MCP server<br/>apps/mcp"]
  end
  CLIENT["An agent or a city's software"]
  TPAGE -- "each answer,<br/>then keep my score" --> WORKER
  WORKER -- "sessions, answers,<br/>the score if kept" --> D1
  SWEEP -- "passed or not,<br/>per model and feature" --> PASS
  PASS -- "which features<br/>a model may flag" --> GATE
  PASS -- "which features<br/>it may ask about" --> CHECKER
  CPAGE -- "answers, the spot,<br/>then follow-up answers" --> WORKER
  QPAGE -- "colour, smell, pipe" --> WORKER
  WORKER -- "photos, metadata cut out,<br/>deleted after 30 days" --> KV
  METEO -- "rain at the spot" --> RAIN
  RAIN -- "dry, wet or unknown" --> FOLLOW
  WORKER <-- "answers and the score in,<br/>at most two questions out" --> FOLLOW
  CHECKER -- "a clean yes,<br/>as a candidate flag" --> GATE
  GATE -. "a flag makes one<br/>question eligible,<br/>none on the live check" .-> FOLLOW
  WALKS -- "the footage run's<br/>yes answers" --> GATE
  GATE -- "flags or drop reasons" --> WALKS
  WALKS -- "the clip and at most<br/>one question, in<br/>content/walks.yaml" --> WPAGE
  WORKER -- "human answers,<br/>ratings, follow-up answers" --> BUILD
  BUILD -- "a visit record" --> EMIT
  EMIT -- "one Bundle per visit" --> D1
  WPAGE -- "answers, as a demo Bundle<br/>on the phone, never sent" --> EMIT
  EMIT -- "sample Bundles from<br/>both emitters" --> VALID
  EMIT -- "visit Bundles as<br/>conditional creates" --> MIRROR
  LIB -- "what our data set is<br/>and where it lives" --> MIRROR
  MIRROR -- "our tag on every resource,<br/>ids kept in a ledger" --> SANDBOX
  SANDBOX -- "one lab Observation<br/>of theirs, read once<br/>a day from the Mac" --> D1
  D1 -- "stored visits and<br/>follow-up answers" --> ACTF
  REGIONS -- "creek and reach<br/>of each spot" --> ACTF
  ACTF -- "a pipe two people<br/>who passed saw running<br/>after dry days" --> REFER
  ACTF -- "needs, pipes worth testing,<br/>downstream notes" --> VIEWS
  REFER -- "a ServiceRequest Bundle" --> VIEWS
  D1 -- "the record, its Bundle,<br/>their cached record" --> VIEWS
  WORKER -- "creeks, city views,<br/>records, Bundles" --> MCP
  MCP -- "answers with their<br/>visit ids and Bundle links" --> CLIENT
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
- **The score travels with the observation.** It is not a badge on a profile page. The test
  sitting, with each feature's score, is a `QuestionnaireResponse` in the record, the
  `Practitioner` carries a dated `qualification` for the test, and the `Provenance` on every
  `Observation` names the test sitting as a source, so an analyst who receives one observation
  receives the trust mark with it.
- **Validation is a gate, not a report.** `make check` fails if any emitted resource does not
  validate against the OneAquaHealth guide at the pinned commit. A record that their systems
  could not read never leaves this repository.
- **Every number has one road.** `evals/` write `results/`, `scripts/verify_claims.py` checks
  every number in the README against `results/`, and CI runs it. A number cannot be typed by hand.
- **Two runtimes, one reference.** Python is the reference implementation and the toolchain.
  The Worker's TypeScript reproduces it, and `make check` fails when it does not, so the edge
  is the same function twice rather than a second opinion.

## The FHIR resources, and how they point at each other

Every arrow is a link in the emitted JSON, labelled with the element that holds it. The links in
the visit and the referral were read off `fhir/golden/visit-strawberry-creek-1.json` and
`fhir/golden/referral-strawberry-creek-1.json`. The Library's `content` lists each mirrored
Provenance by its address on their server, as `fhir/golden/library-second-look.json` shows.
The Practitioner's qualification carries the test and its dates; the numbers of the score sit in
the test sitting's QuestionnaireResponse, which the Provenance names as a source of every
Observation. The image: [`docs/diagrams/fhir-graph.svg`](diagrams/fhir-graph.svg).

```mermaid
flowchart TB
  accTitle: The FHIR resources of one creek visit, and how they point at each other
  accDescr: One creek visit is emitted as a collection Bundle by core/fhir_emit.py. Its Observations sit on the spot, which is part of a reach, which is part of a creek. Each Observation names the volunteer as performer and the creek check answers as its source. The volunteer is a pseudonymous Practitioner whose dated qualification is issued by Second Look, and the test sitting with the per-feature score is authored by the same Practitioner. One Provenance ties every Observation to the volunteer, the software and both sets of answers. A pipe worth testing becomes a ServiceRequest made on request by core/fhir_referral.py, and our Library entry on their sandbox lists the mirrored Provenance.
  subgraph VISIT["Bundle, type collection: one creek visit, from core/fhir_emit.py"]
    ORG["Organization<br/>Second Look"]
    DEV["Device<br/>the Second Look web app"]
    PRAC["Practitioner, the volunteer<br/>known by a hash of a random token<br/>qualification: the Second Look test,<br/>from the test day until it lapses"]
    QRT["QuestionnaireResponse<br/>the test sitting: each feature's score"]
    QRV["QuestionnaireResponse<br/>the creek check: every answer"]
    OBS["Observation, one per answered item<br/>profile ObservationIndicatorsOah<br/>value: a coded answer or a quantity"]
    PROV["Provenance<br/>one per visit"]
    subgraph NEST["Location nest, profile LocationOah"]
      SPOT["Location: the spot"]
      REACH["Location: the reach"]
      CREEK["Location: the creek"]
    end
  end
  subgraph REFER["Referral, core/fhir_referral.py"]
    SR["ServiceRequest, intent proposal<br/>test the water coming out of this pipe<br/>made on request, never stored"]
  end
  subgraph SANDBOX["Their sandbox, our copies sent by scripts/repush_sandbox.py"]
    LIB["Library, profile LibraryOah<br/>our data set, from core/fhir_library.py"]
  end
  SPOT -- "partOf" --> REACH
  REACH -- "partOf" --> CREEK
  PRAC -- "qualification.issuer" --> ORG
  QRT -- "author" --> PRAC
  QRV -- "author" --> PRAC
  OBS -- "subject" --> SPOT
  OBS -- "performer" --> PRAC
  OBS -- "derivedFrom" --> QRV
  PROV -- "target: every Observation" --> OBS
  PROV -- "agent, author" --> PRAC
  PROV -- "agent, assembler" --> DEV
  PROV -- "entity, source: the answers" --> QRV
  PROV -- "entity, source: the score" --> QRT
  SR -- "subject: the pipe's spot" --> SPOT
  SR -- "reasonReference:<br/>the pipe Observations" --> OBS
  SR -- "requester" --> ORG
  LIB -- "content: each mirrored<br/>Provenance, by its id there" --> PROV
```

Their profiles are used where they exist and ours only where they do not. Feature answers are
`CodeableConcept`, never booleans, because their `Observation` profile allows only
`CodeableConcept` or `Quantity`. Their `TemporaryOahSystem` codes `present` and `absent` carry
the values. `docs/fhir_mapping.md` has every field.

## The AI gate, step by step

Every arrow between the parts of the code is a call, its return, or a read of the pass table in
`core/checker.py`, `core/gate.py` or `core/followups.py`. The arrows to and from the volunteer
are the app's screens. On the live creek check the checker is off: `apps/api/settings.py` has
`checker_enabled` false and the Worker passes no flags, so no model is in that request path.
The walks run the same gate at build time in `scripts/build_walks.py` and ask their one question
after the person has answered. The image: [`docs/diagrams/ai-gate.svg`](diagrams/ai-gate.svg).

```mermaid
sequenceDiagram
  accTitle: The AI gate, step by step
  accDescr: The volunteer answers every question first. Only then may a vision model answer one question about one photo, and only for a feature it passed on the same test the volunteers take. The gate turns that answer into a flag or drops it. A flag can make one follow-up question eligible. The follow-up selector, which calls no model, picks at most two questions. The person answers them, and the record is built from the person's answers alone.
  autonumber
  actor V as Volunteer
  participant App as The app and its API
  participant C as core/checker.py
  participant P as Pass table<br/>results/model_pass_table.json
  participant M as Vision model
  participant G as core/gate.py
  participant F as core/followups.py
  participant R as build_record<br/>core/gate.py
  V->>App: Answers every question in the creek check first
  App->>C: check_photo: one photo, one feature
  C->>P: feature_passed: is the table from a real run, and did this model pass this feature?
  alt The checker is off, or the answer is no
    C-->>App: No flag. The model is never asked.
  else Yes
    C->>M: The feature's question, from content/features.yaml
    M-->>C: yes, no or cant_tell, and a note
    C->>C: force_answer: anything but a clean yes stops here
    C->>G: parse_flags: the yes as a candidate flag
    G->>P: Reads the table again: real run, feature passed by this model
    G->>G: Checks the feature, the confidence and a short plain note
    G-->>C: A Flag, or a reason it was dropped
    C-->>App: At most one Flag
  end
  App->>F: select_followups: answers, dry days, the person's score, flags
  F->>F: Rules in order: dry pipe, rating check, checker flag, low score
  Note over F: A flag can make only the checker flag question eligible. No model call in here.
  F-->>App: At most two questions, and at most one of them from a flag
  App->>V: Look again? The model's note is shown as "the checker noticed"
  V->>App: The person's own answer
  App->>R: Answers, ratings, follow-up answers and photo ids
  Note over R: No parameter takes a flag, a model id or model text
  R-->>App: The visit record, human answers only
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
