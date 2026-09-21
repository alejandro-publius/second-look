# The Second Look MCP server

A read only server over our own creek records, for any software agent that speaks the Model
Context Protocol. It runs on your machine over stdio, the way agents use one, and needs no hosting.
It reads either our read only API or a local export, and calls nothing else.

**Every answer carries the resource ids behind it.** A number without its `resource_ids` and
`fhir` links does not leave this server, so an agent cannot state a figure it cannot trace.

## Tools

| Tool | What it answers | Arguments |
|---|---|---|
| `list_creeks` | every creek with a record, each with its visit ids | none |
| `get_creek_record` | one creek: findings, what it needs in approved words, pipes worth testing, reaches, downstream notes | `creek`: a slug such as `strawberry-creek` or a stored creek id |
| `list_findings` | findings across creeks, filtered | `creek?`, `feature?`, `min_observers` (default 1), `passed_only` (default false) |
| `get_observer_score` | an observer's dated qualification and per feature k of 4, as the record carries it | `observer`: a Practitioner id or a visit id |
| `explain_number` | the ids behind one figure on a creek's record | `creek`, `path` such as `visits` or `pipes_worth_testing/0/observers` |

## Run it

Against the live read only API:

```
uv run python -m apps.mcp.server --api https://second-look-api.thealexschroeder.workers.dev
```

Against a local export, with no network at all:

```
make export-records        # writes data/export from the local database
make mcp                   # serves it over stdio
```

## Point Claude at it

Claude Desktop, in `claude_desktop_config.json`, or Claude Code, in `.mcp.json` at the project
root:

```json
{
  "mcpServers": {
    "second-look": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/second-look", "python", "-m", "apps.mcp.server", "--export", "data/export"]
    }
  }
}
```

Then ask: "Which pipes on Strawberry Creek are worth testing, and which records say so?"

## What it will not do

- Write anything. There is no tool that creates, changes or deletes a record.
- Decide anything. The lists are computed by `core/act.py` from what people reported; this
  server only reads them.
- State a health risk. The only sentences with health or ecology meaning are approved ones from
  `content/approved_sentences.yaml`, carried through unchanged.

## Proof

- `apps/mcp/tests/test_server.py`: the five tools, every answer with its ids, both sources
  reading the same app, and one real run over stdio the way an agent starts it.
- `transcript.md` in this folder: one session, written by `scripts/mcp_transcript.py` from real
  code and a throwaway database.
