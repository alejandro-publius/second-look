# Sandbox evidence: the Library entry

Written by `scripts/repush_sandbox.py --library` at 2026-09-21T06:53:47Z. The ledger is
`fhir/sandbox_ledger.jsonl`; every id below is in it.

- Server: `https://sandbox.hl7europe.eu/oneaquahealth/fhir`
- Library: `Library/466` (create)
- Read back: HTTP 200
- Screenshot: `docs/screens/sandbox-library.png`
- GET it yourself: `curl -H 'Accept: application/fhir+json' https://sandbox.hl7europe.eu/oneaquahealth/fhir/Library/466`

## The Library as the sandbox returned it

```json
{
  "resourceType": "Library",
  "id": "466",
  "meta": {
    "versionId": "1",
    "lastUpdated": "2026-09-21T06:53:46.737+00:00",
    "profile": [
      "http://hl7.eu/fhir/ig/oah/StructureDefinition/library-oah"
    ],
    "tag": [
      {
        "system": "https://github.com/alejandro-publius/second-look",
        "code": "second-look"
      }
    ]
  },
  "text": {
    "status": "generated",
    "div": "<div xmlns=\"http://www.w3.org/1999/xhtml\"><p>Second Look data set: citizen creek checks from Berkeley, a follower city, with the observer's per feature test score carried on every observation. 1 visit records mirrored to this server. The repository holds the code, the FSH and the tests.</p></div>"
  },
  "extension": [
    {
      "url": "http://hl7.eu/fhir/ig/oah/StructureDefinition/library-size",
      "valueQuantity": {
        "value": 1,
        "unit": "visit records"
      }
    },
    {
      "url": "http://hl7.eu/fhir/ig/oah/StructureDefinition/library-numberOfRecords",
      "valueInteger": 1
    }
  ],
  "url": "https://github.com/alejandro-publius/second-look/fhir/Library/second-look-citizen-creek-checks",
  "identifier": [
    {
      "system": "https://github.com/alejandro-publius/second-look/fhir/library-id",
      "value": "second-look-citizen-creek-checks"
    }
  ],
  "version": "2026.09",
  "name": "SecondLookCitizenCreekChecks",
  "title": "Second Look: citizen creek checks with observer scores, Berkeley",
  "status": "active",
  "type": {
    "coding": [
      {
        "system": "http://terminology.hl7.org/CodeSystem/library-type",
        "code": "asset-collection",
        "display": "Asset Collection"
      }
    ]
  },
  "date": "2026-09-21",
  "publisher": "Second Look project",
  "description": "Second Look data set: citizen creek checks from Berkeley, a follower city, with the observer's per feature test score carried on every observation. 1 visit records mirrored to this server. The repository holds the code, the FSH and the tests.",
  "copyright": "Code MIT. Photos and copy CC BY 4.0. No personal data: observers are known only by a hash of a random token.",
  "author": [
    {
      "name": "Second Look project, Berkeley, a follower city"
    }
  ],
  "content": [
    {
      "contentType": "text/html",
      "url": "https://github.com/alejandro-publius/second-look",
      "title": "The repository: code, FSH, the emitter and every test"
    },
    {
      "contentType": "application/fhir+json",
      "url": "https://github.com/alejandro-publius/second-look/blob/main/fhir/golden/visit-strawberry-creek-1.json",
      "title": "One worked visit at Strawberry Creek as a collection Bundle"
    },
    {
      "contentType": "application/fhir+json",
      "url": "https://second-look-api.thealexschroeder.workers.dev/api/fhir/Bundle",
      "title": "Read only endpoint: one Bundle per visit, by visit id"
    },
    {
      "contentType": "application/fhir+json",
      "url": "Provenance/465",
      "title": "Provenance of one mirrored visit on this server"
    }
  ]
}
```

## The mirrored record, fetched back by our tag

Run right after the push, one request per second, user agent naming the repo:

```
GET Provenance?_tag=https://github.com/alejandro-publius/second-look|second-look
  total 1, Provenance/465, 5 targets (the five Observations of the worked visit)
GET Library?_tag=https://github.com/alejandro-publius/second-look|second-look
  total 1, Library/466, url https://github.com/alejandro-publius/second-look/fhir/Library/second-look-citizen-creek-checks
  content: the repository, the golden visit Bundle, the read only endpoint, Provenance/465
```

Before the push the same four searches (Location, Observation, Provenance, Library) all returned
total 0: nothing of ours was there. After it, 14 resources of the worked visit plus the Library are,
ids 452 to 466, every one in the ledger. Anyone can delete them; the ledger and this note stay.

## The audit line, pending

The push and the Library each append a `sandbox_push` line to the audit log. `audit/log.jsonl`
does not exist yet on either branch, and a hash chain cannot be started twice and merged, so on
`depth` both lines went to a scratch file outside the repository. When `depth` merges into `main`,
append them to the real chain with `scripts/audit_log.py`:

```
sandbox_push {"base": "https://sandbox.hl7europe.eu/oneaquahealth/fhir", "bundles": 1, "created": 14, "matched": 0}
sandbox_push {"base": "https://sandbox.hl7europe.eu/oneaquahealth/fhir", "library": "Library/466", "action": "create", "provenances": 1}
```
