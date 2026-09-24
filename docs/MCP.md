# MCP tools

`apps/mcp/server.py` is a read only Model Context Protocol server over our own creek records. It
runs on your machine over stdio and reads either our read only API (`--api`, the Worker by
default) or a folder written by `scripts/export_records.py` (`--export`, no network at all).
Nothing in it writes, decides or calls a model: the judgement is in `core/act.py`, and this only
reads what it produced. How to run it and point Claude at it: `examples/mcp/README.md`. One real
session from a throwaway database: `examples/mcp/transcript.md`.

The server has <!--v:results/api_inventory.json#/mcp/count-->5<!--/v--> tools
(`results/api_inventory.json`). `scripts/tests/test_api_docs.py` reads them out of the code and
fails when a tool has no row below, a row has no tool, or a row leaves out one of its inputs.

**Every answer carries its evidence.** Each one ends with `resource_ids` (the visit Bundles it
was counted from, as `Bundle/<visit id>`) and `fhir` (their links, `/api/fhir/Bundle/<visit id>`),
so an agent cannot state a number it cannot trace. `source` says where the record was read.

**Ids are one plain name.** An id must be letters, digits, dot, underscore and hyphen, and never
`.` or `..` (`apps/mcp/source.py`), so a call can never reach another route or leave the export
folder. Spot, reach and creek names can be text a visitor typed; the server tells the agent to
read them as data, never as instructions.

| Tool | Inputs | What it returns |
|---|---|---|
| `list_creeks` | none | `creeks`: every creek with a record, each with the visit ids behind its count |
| `get_creek_record` | `creek`: a slug such as `strawberry-creek`, or a stored creek id | the creek's record as `/api/city/{creek}` gives it: `findings`, `needs` in approved words with their source, `pipes_worth_testing`, `reaches`, `downstream_notes`, `visits`; every list item with its own `visit_ids` and `fhir` |
| `list_findings` | `creek` (optional, all creeks when left out), `feature` (optional: a feature id such as `pipe_running`, or a form item), `min_observers` (default 1, at least 1), `passed_only` (default false: when true, count only people who held a passing, unexpired score for that feature) | `filters` as given, and `findings`: each with its `creek`, `creek_name`, `feature`, `observers`, `passed_observers` and `visit_ids` |
| `get_observer_score` | `observer`: a visit id, or a Practitioner id such as `sl-practitioner-1a2b3c4d5e6f`, which is looked for in a limited number of records | `practitioner_id`, `tested_on`, `score_counts_until`, `scores` (each feature's right answers out of 4 from the test sitting in the record), `scores_note`, `from_visit`. The person is known only by a hash of a random token. |
| `explain_number` | `creek`, and `path`: the figure, such as `visits`, `findings/0/observers` or `pipes_worth_testing/0` | `value`, the `path` read, `counted_from` (how many visits), and the ids of the nearest thing on that path that carries evidence |

A mistake an agent can fix, such as an unknown creek, a `path` that names a whole section, or a
`min_observers` below 1, comes back as a tool error with a plain message. Any other failure stays
behind the SDK's generic error, so nothing internal leaks.
