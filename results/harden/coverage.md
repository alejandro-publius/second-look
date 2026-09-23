# Coverage

Measured 2026-09-23T04:37:55Z at commit 92fa280 by `uv run python scripts/harden_coverage.py`. Before is commit 92fa280, the last commit without the harden tests. Line and branch coverage together, over the whole Python suite, with test files left out of the totals.

- Suite before: 656 passed, 2 skipped in 87.23s (0:01:27)
- Suite after: 1023 passed, 1 skipped, 11 xfailed in 112.20s (0:01:52)

## Python packages

| Package | Before, percent | After, percent |
|---|---|---|
| core/ | 91.2 (1858 statements, 127 missed; 800 branches, 107 missed) | 99.7 (1858 statements, 4 missed; 800 branches, 5 missed) |
| apps/api/ | 91.1 (1606 statements, 103 missed; 382 branches, 73 missed) | 91.1 (1606 statements, 103 missed; 382 branches, 73 missed) |

## Core functions that were under 90 percent

34 functions in core/ were under the bar before; 0 are under it after.

| Function | Before | After |
|---|---|---|
| `core/allocator.py::block_contents` | 88.9 | 100.0 |
| `core/checker.py::_gate_parse_flags` | 50.0 | 100.0 |
| `core/checker.py::feature_passed` | 87.5 | 100.0 |
| `core/content_loader.py::Content.photo_by_id` | 0.0 | 100.0 |
| `core/content_loader.py::_check_disjoint` | 76.5 | 100.0 |
| `core/content_loader.py::_check_test_items` | 69.8 | 100.0 |
| `core/content_loader.py::_check_warmup` | 60.0 | 100.0 |
| `core/content_loader.py::_load_manifest` | 61.4 | 100.0 |
| `core/content_loader.py::load_content` | 75.0 | 100.0 |
| `core/content_loader.py::placeholder_report` | 77.8 | 100.0 |
| `core/fhir_emit.py::_if_none_exist` | 73.9 | 100.0 |
| `core/fhir_emit.py::_item_code` | 80.0 | 100.0 |
| `core/fhir_emit.py::_qr_answers` | 89.5 | 100.0 |
| `core/fhir_emit.py::_test_response` | 85.7 | 100.0 |
| `core/fhir_emit.py::check_bundle` | 83.1 | 100.0 |
| `core/fhir_emit.py::code_for_answer` | 85.7 | 100.0 |
| `core/fhir_referral.py::_example_observation` | 78.9 | 100.0 |
| `core/fhir_referral.py::_identifier_value` | 83.3 | 100.0 |
| `core/fhir_referral.py::check_example_bundle` | 76.1 | 100.0 |
| `core/fhir_referral.py::check_referral_bundle` | 78.8 | 100.0 |
| `core/fhir_referral.py::example_lab_result` | 88.2 | 100.0 |
| `core/fhir_referral.py::is_example` | 87.5 | 100.0 |
| `core/fhir_referral.py::referral_bundle` | 89.7 | 100.0 |
| `core/followups.py::_issue_label` | 23.1 | 100.0 |
| `core/followups.py::_item_by_id` | 75.0 | 100.0 |
| `core/followups.py::_rules_in_priority` | 71.4 | 100.0 |
| `core/gate.py::Flag._finite_confidence` | 60.0 | 100.0 |
| `core/gate.py::parse_flags` | 50.0 | 100.0 |
| `core/rainfall.py::_default_fetch` | 0.0 | 100.0 |
| `core/regions.py::Creek.contains` | 71.4 | 100.0 |
| `core/regions.py::Creek.reach` | 75.0 | 100.0 |
| `core/regions.py::_bbox` | 88.2 | 100.0 |
| `core/regions.py::creeks_from_regions` | 88.4 | 100.0 |
| `core/regions.py::reaches_below` | 89.5 | 100.0 |

## apps/api files

| File | Before | After |
|---|---|---|
| apps/api/__init__.py | 100.0 | 100.0 |
| apps/api/check.py | 89.3 | 89.3 |
| apps/api/city.py | 95.8 | 95.8 |
| apps/api/content.py | 83.3 | 83.3 |
| apps/api/core_calls.py | 69.3 | 69.3 |
| apps/api/db.py | 84.4 | 84.4 |
| apps/api/deps.py | 100.0 | 100.0 |
| apps/api/fhir_routes.py | 89.6 | 89.6 |
| apps/api/fhir_store.py | 100.0 | 100.0 |
| apps/api/main.py | 96.6 | 96.6 |
| apps/api/migrations/env.py | 77.1 | 77.1 |
| apps/api/migrations/versions/0001_initial_tables.py | 100.0 | 100.0 |
| apps/api/migrations/versions/0002_resume_and_confirm.py | 100.0 | 100.0 |
| apps/api/models.py | 100.0 | 100.0 |
| apps/api/routes_check.py | 100.0 | 100.0 |
| apps/api/routes_study.py | 100.0 | 100.0 |
| apps/api/security.py | 94.1 | 94.1 |
| apps/api/settings.py | 100.0 | 100.0 |
| apps/api/study.py | 90.7 | 90.7 |

## worker/src

The golden tests, run under c8 with source maps: tests 9, pass 9. The harden run added no Worker test, so before and after are the same. Files marked not loaded are reached only by `make worker-e2e`, which drives wrangler dev over HTTP and is not instrumented.

| File | Lines | Branches | Functions |
|---|---|---|---|
| worker/src/check.ts | not loaded | not loaded | not loaded |
| worker/src/city.ts | not loaded | not loaded | not loaded |
| worker/src/core/act.ts | 100 | 96.03 | 100 |
| worker/src/core/fhir_emit.ts | 98.22 | 78.2 | 100 |
| worker/src/core/fhir_referral.ts | 100 | 70.68 | 100 |
| worker/src/core/followups.ts | 92.16 | 73.33 | 100 |
| worker/src/core/healthcard.ts | 100 | 84.21 | 100 |
| worker/src/core/labels.ts | 100 | 90 | 100 |
| worker/src/core/pyround.ts | 100 | 80 | 100 |
| worker/src/core/rainfall.ts | not loaded | not loaded | not loaded |
| worker/src/core/regions.ts | 95.78 | 86.04 | 100 |
| worker/src/core/sha256.ts | 100 | 90 | 100 |
| worker/src/core/types.ts | 98.24 | 75 | 100 |
| worker/src/index.ts | not loaded | not loaded | not loaded |
| worker/src/two.ts | not loaded | not loaded | not loaded |
| worker/src/uploads.ts | not loaded | not loaded | not loaded |
