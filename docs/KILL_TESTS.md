# Kill tests

Tests whose failure would sink the project. Each gets a result line with a date and a pointer to the evidence.

| Id | Test | Result | Evidence |
|---|---|---|---|
| K6 | The shared sandbox accepts one tagged Location by conditional create, returns it, and deletes it by id | PASS 2026-09-20 21:37Z: create 201 (id 451), read 200, delete 200, read after delete 410 | docs/notes/sandbox_write_test.txt, fhir/sandbox_ledger.jsonl |

K1 to K5 were defined in Update 03, which was not pasted into this terminal. Add them here when it arrives.
