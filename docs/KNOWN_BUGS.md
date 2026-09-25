# Known bugs, kept as failing tests

`uv run pytest` and `make judge-check` report some tests as xfailed. Each one is a known bug in
our own code, found by the hardening tests of Sep 22 (8d7ca47). Its test says what the code should
do, and fails today. It is marked as a strict expected failure (`xfail(strict=True)`), so pytest
counts it apart instead of hiding it, and the whole run goes red the day the code is fixed and the
mark is left in: a mark cannot outlive its bug. `uv run pytest -rx` prints each one with its
reason.

`scripts/tests/test_known_bugs.py` fails when a test in this repository is marked as an expected
failure and is not on this page, or when this page names a test that is not marked.

| Where | The bug | Who could meet it | The test |
|---|---|---|---|
| The gate, `core/gate.py` | A whole number too big for a float, in a flag's confidence, its region or its feature, raises inside the gate. The gate catches it and still never raises, but it drops every flag in that answer, the good ones too, not only the bad one. One test, three cases. | A model reply with a number hundreds of digits long. The checker is off on the live site, so no volunteer has met it. | `core/tests/test_harden_gate_properties.py::test_a_huge_number_drops_only_its_own_flag` |
| The FHIR writer, `core/fhir_emit.py`, and its Worker port | A creek check with no answer that maps to an Observation (in the test, only an overall rating) gets a Provenance with an empty target list, which FHIR R4 does not allow. Our own check of the Bundle passes it; the step that sends a Bundle to their sandbox refuses it. | A person who sends a check with only such answers. No real check has been sent yet. | `core/tests/test_harden_fhir_emit.py::test_a_visit_with_no_mapped_answer_does_not_pass_with_an_empty_provenance` |
| The referral check, `check_referral_bundle` in `core/fhir_referral.py` | Our own check of a referral Bundle passes three shapes it should refuse: a reason that points at something other than an Observation, a reason given by its full URL, which is never checked for a pipe reported present, and a reason with no reference at all. | Nobody through the site: both servers build a referral's reasons as references to its Observations, and the check is used by the tests of those referrals. A Bundle made or edited another way would slip through it. | `core/tests/test_harden_fhir_referral.py::test_check_referral_rejects_a_reason_that_points_at_a_location`, `core/tests/test_harden_fhir_referral.py::test_check_referral_rejects_an_absent_pipe_reached_by_its_full_url`, `core/tests/test_harden_fhir_referral.py::test_check_referral_rejects_a_reason_with_no_reference` |
| The follow-up picker, `core/followups.py` | When two flags have the same confidence, the first one in the list wins, so the order of the list, not the flags, picks which note the checker's question shows. | A visit with two kept flags of equal confidence. The checker is off on the live site, so no volunteer has met it. | `core/tests/test_harden_followups_properties.py::test_two_flags_with_the_same_confidence_give_the_same_question_in_either_order` |
| The content loader, `core/content_loader.py` | A feature in `content/features.yaml` with no id crashes the loader with a TypeError instead of a problem it reports. | A person who edits the content files. The build stops either way, with a less clear message. | `core/tests/test_harden_content_loader.py::test_a_feature_with_no_id_is_reported_not_a_crash` |

None of them changes a stored answer, a score or the pass table, and none lets a model decide
anything: the gate's own promise, that it never raises and keeps a flag only for a feature the
model passed, holds in each (`docs/THREAT_MODEL.md`, A model).
