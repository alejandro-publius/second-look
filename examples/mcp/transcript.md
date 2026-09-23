# One session with the Second Look MCP server

Written by `scripts/mcp_transcript.py` on 2026-09-21. Real code, a
throwaway database: two people who passed the pipe feature reported a pipe running
after dry weather at the Faculty Glade pin on Strawberry Creek, and one anonymous visit
in Strawberry Creek Park, three reaches below, reported nothing. Export: {'creeks': 1, 'spots': 2, 'bundles': 3}.

Start the server the way an agent would:

```
uv run python -m apps.mcp.server --export data/export
```

Every answer ends with `resource_ids` and `fhir`: the visit Bundles it was counted from.

## list_creeks()

```json
{
  "source": "local export at <temp>/export",
  "creeks": [
    {
      "creek": "strawberry-creek",
      "creek_slug": "strawberry-creek",
      "fhir": [
        "/api/fhir/Bundle/visit-3e6a2683e60e2028",
        "/api/fhir/Bundle/visit-7a2922cd3b32a277",
        "/api/fhir/Bundle/visit-6e58a45cd7e27644"
      ],
      "name": "Strawberry Creek",
      "record": "/api/city/strawberry-creek",
      "spots": 2,
      "visit_ids": [
        "visit-3e6a2683e60e2028",
        "visit-7a2922cd3b32a277",
        "visit-6e58a45cd7e27644"
      ],
      "visits": 3
    }
  ],
  "resource_ids": [
    "Bundle/visit-3e6a2683e60e2028",
    "Bundle/visit-7a2922cd3b32a277",
    "Bundle/visit-6e58a45cd7e27644"
  ],
  "fhir": [
    "/api/fhir/Bundle/visit-3e6a2683e60e2028",
    "/api/fhir/Bundle/visit-7a2922cd3b32a277",
    "/api/fhir/Bundle/visit-6e58a45cd7e27644"
  ]
}
```

## list_findings("feature": "pipe_running", "min_observers": 2, "passed_only": true)

```json
{
  "source": "local export at <temp>/export",
  "filters": {
    "creek": null,
    "feature": "pipe_running",
    "min_observers": 2,
    "passed_only": true
  },
  "findings": [
    {
      "creek": "strawberry-creek",
      "creek_name": "Strawberry Creek",
      "feature": "pipe_running",
      "feature_name": "Pipes and sewage signs",
      "fhir": [
        "/api/fhir/Bundle/visit-3e6a2683e60e2028",
        "/api/fhir/Bundle/visit-7a2922cd3b32a277"
      ],
      "first_seen": "2026-09-25",
      "last_seen": "2026-09-25",
      "observers": 2,
      "passed_observers": 2,
      "spot_id": "spot-441ccd16c903",
      "spot_name": "Faculty Glade bridge",
      "visit_ids": [
        "visit-3e6a2683e60e2028",
        "visit-7a2922cd3b32a277"
      ],
      "resource_ids": [
        "Bundle/visit-3e6a2683e60e2028",
        "Bundle/visit-7a2922cd3b32a277"
      ]
    }
  ],
  "resource_ids": [
    "Bundle/visit-3e6a2683e60e2028",
    "Bundle/visit-7a2922cd3b32a277"
  ],
  "fhir": [
    "/api/fhir/Bundle/visit-3e6a2683e60e2028",
    "/api/fhir/Bundle/visit-7a2922cd3b32a277"
  ]
}
```

## explain_number("creek": "strawberry-creek", "path": "pipes_worth_testing/0/observers")

```json
{
  "source": "local export at <temp>/export",
  "creek": "strawberry-creek",
  "path": "pipes_worth_testing/0/observers",
  "value": 2,
  "counted_from": 2,
  "resource_ids": [
    "Bundle/visit-3e6a2683e60e2028",
    "Bundle/visit-7a2922cd3b32a277"
  ],
  "fhir": [
    "/api/fhir/Bundle/visit-3e6a2683e60e2028",
    "/api/fhir/Bundle/visit-7a2922cd3b32a277"
  ]
}
```

## get_observer_score("observer": "visit-3e6a2683e60e2028")

```json
{
  "source": "local export at <temp>/export",
  "practitioner_id": "sl-practitioner-a842087c27cb",
  "tested_on": "2026-09-25",
  "score_counts_until": "2026-12-24",
  "scores": [
    {
      "feature": "artificial_bank",
      "correct": 4,
      "total": 4
    },
    {
      "feature": "dug_out_channel",
      "correct": 4,
      "total": 4
    },
    {
      "feature": "invasive_plant",
      "correct": 4,
      "total": 4
    },
    {
      "feature": "pipe_running",
      "correct": 4,
      "total": 4
    }
  ],
  "scores_note": "k of 4 per feature, from the test sitting in this record",
  "from_visit": "visit-3e6a2683e60e2028",
  "resource_ids": [
    "Bundle/visit-3e6a2683e60e2028"
  ],
  "fhir": [
    "/api/fhir/Bundle/visit-3e6a2683e60e2028"
  ]
}
```

## get_creek_record("creek": "strawberry-creek")

```json
{
  "source": "local export at <temp>/export",
  "creek_id": "strawberry-creek",
  "creek_name": "Strawberry Creek",
  "creek_slug": "strawberry-creek",
  "downstream_notes": [
    {
      "feature": "artificial_bank",
      "feature_name": "Built banks",
      "fhir": [
        "/api/fhir/Bundle/visit-3e6a2683e60e2028",
        "/api/fhir/Bundle/visit-7a2922cd3b32a277"
      ],
      "from_reach_name": "South Fork, central campus",
      "from_reach_slug": "south-fork-campus",
      "line": "Upstream of here, 2 people reported built banks on Sep 25.",
      "observers": 2,
      "reach_name": "Below the forks, west campus",
      "reach_slug": "campus-west",
      "visit_ids": [
        "visit-3e6a2683e60e2028",
        "visit-7a2922cd3b32a277"
      ]
    },
    {
      "feature": "artificial_bank",
      "feature_name": "Built banks",
      "fhir": [
        "/api/fhir/Bundle/visit-3e6a2683e60e2028",
        "/api/fhir/Bundle/visit-7a2922cd3b32a277"
      ],
      "from_reach_name": "South Fork, central campus",
      "from_reach_slug": "south-fork-campus",
      "line": "Upstream of here, 2 people reported built banks on Sep 25.",
      "observers": 2,
      "reach_name": "Downtown culvert",
      "reach_slug": "downtown-culvert",
      "visit_ids": [
        "visit-3e6a2683e60e2028",
        "visit-7a2922cd3b32a277"
      ]
    },
    {
      "feature": "artificial_bank",
      "feature_name": "Built banks",
      "fhir": [
        "/api/fhir/Bundle/visit-3e6a2683e60e2028",
        "/api/fhir/Bundle/visit-7a2922cd3b32a277"
      ],
      "from_reach_name": "South Fork, central campus",
      "from_reach_slug": "south-fork-campus",
      "line": "Upstream of here, 2 people reported built banks on Sep 25.",
      "observers": 2,
      "reach_name": "Strawberry Creek Park",
      "reach_slug": "strawberry-creek-park",
      "visit_ids": [
        "visit-3e6a2683e60e2028",
        "visit-7a2922cd3b32a277"
      ]
    },
... 386 more lines
```

## explain_number("creek": "strawberry-creek", "path": "findings")

```json
{
  "error": "Error executing tool explain_number: 'findings' is a whole section, not one figure; name a field in it"
}
```
