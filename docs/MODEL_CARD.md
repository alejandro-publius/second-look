# Model card: the checker

The checker is the only place a vision model touches Second Look. It is `core/checker.py`, and
every answer it gets goes through `core/gate.py`. This card says what the checker may do, what
it may not, which models passed which features, how big the test behind that is, how it fails,
what it cost, and how the gate holds it. Every number is read from a file in `results/` and
checked by `make verify-claims`.

## The models and how they are asked

We train nothing. The checker calls four vision models from Anthropic's API, unchanged: Claude
Haiku 4.5 (`claude-haiku-4-5-20251001`), Claude Sonnet 5 (`claude-sonnet-5`), Claude Opus 5.5
(`claude-opus-5-5`) and Claude Fable 5.1 (`claude-fable-5-1`), as listed in `evals/models.yaml`.

- **One photo, one question.** The photo is resized to
  <!--v:results/model_sweep_20260924T054756Z.json#/settings/resize_long_side_px-->1092<!--/v--> pixels on its
  long side. The question is the frozen wording a volunteer reads, from `content/features.yaml`.
- **The instruction,** word for word: "You are looking at one photo of a stream taken by a
  volunteer. Answer one question about what is visible in the photo. If the photo does not show a
  stream, or you cannot tell, answer cant_tell. Do not guess."
- **The answer** is forced into yes, no or can't tell, with a note of at most 160 characters
  (`force_answer` in `core/checker.py`). Anything else becomes can't tell and counts as
  malformed, so a bad answer can never count as a right one.
- **Settings** are stored with each run: temperature 0 where a model accepts it, and
  <!--v:results/model_sweep_20260924T054756Z.json#/runs-->3<!--/v--> runs of every photo.

## What it may do

- Answer one feature question about one photo.
- Raise at most one flag, and only on a feature that model passed on the same 16-photo test the
  volunteers take, and only after the person has answered.
- Make one follow-up question eligible with that flag, and only for a feature the creek check
  asks about (an item in `content/form.yaml`), so a flag on a dug-out channel asks nothing. Code
  picks the questions (`core/followups.py`): two at most, the model's at most one.
- Ask the person to look again, and nothing more. They tap "I looked again" or "Skip" (Yes, No or
  Can't tell in the creek check), and no stored answer changes.
- Show its note to the person, labelled "the checker noticed", cut to 160 characters.

Where it runs today: on the live site the checker is off (`CHECKER_ENABLED`), so both servers
pass no flags and no model is called. The video walks send the footage run's answers through the
same gate when they are built, and today
<!--v:results/footage_pool.json#/walks_with_a_checker_question-->0<!--/v--> of the
<!--v:results/footage_pool.json#/walks-->3<!--/v--> walks carries a checker question: the gate kept no flag
on the frames the walks use (`content/walks.yaml`). Everywhere else the models are only
measured: on the 16 test photos and on frames from open creek footage.

## What it may not do

| It may not | What stops it | The test that fails if it breaks |
|---|---|---|
| Decide anything stored | `build_record` in `core/gate.py` takes human inputs only, with no parameter for a flag, a model id or model text | `core/tests/test_gate.py::test_build_record_signature_carries_human_inputs_only`, `core/tests/test_gate.py::test_fuzz_model_output_never_reaches_answers_or_labels` |
| Speak on a feature it did not pass | the checker does not even ask, and the gate drops the flag | `core/tests/test_checker.py::test_unpassed_feature_returns_nothing_even_when_the_model_is_confident`, `core/tests/test_harden_gate_properties.py::test_every_kept_flag_is_licensed_for_that_exact_model` |
| Speak on a made-up pass table | a table without `"real": true` licenses nothing | `core/tests/test_checker.py::test_synthetic_pass_table_never_licenses_a_flag_by_default` |
| Speak on a pass table edited by hand | each `passed` cell is graded again from the runs stored beside it | `evals/tests/test_committed_pass_table.py::test_every_passed_cell_follows_from_its_own_runs` |
| Ask first, or ask more than one question | follow-up selection is a pure function of the answers, the rain, the scores and the flags, with no model call inside it | `core/tests/test_harden_followups_properties.py::test_the_content_table_never_asks_more_than_two_questions_for_any_input`, `core/tests/test_harden_followups_properties.py::test_the_selector_runs_with_http_and_the_model_client_patched_to_raise` |
| Put markup, line breaks or text direction tricks in front of a person | the gate drops such a note | `core/tests/test_gate.py::test_note_with_markup_or_a_direction_control_is_dropped` |
| Flood the gate | more than 50 candidate flags at once drops them all | `core/tests/test_gate.py::test_a_flood_of_flags_drops_everything` |
| Say anything about health or risk | every health or ecology sentence a person reads comes from `content/approved_sentences.yaml` with a source | `core/tests/test_healthcard.py`, `core/tests/test_act.py` |
| Write a file | the checker returns flags and nothing else | `core/tests/test_checker.py::test_checker_writes_nothing_in_the_working_directory` |

## The pass table

The rule, fixed in `docs/analysis_plan.md` item 8 before any model ran: a model passes a feature
only if it gets all 4 photos of that feature right in at least 2 of its 3 runs. The committed
table is `results/model_pass_table.json`; the gate and the checker read it and nothing else.

| Model | Built bank | Dug-out channel | Invasive plant | Pipe running |
|---|---|---|---|---|
| Claude Haiku 4.5 | <!--v:results/model_pass_table.json#/models/claude-haiku-4-5-20251001/artificial_bank/passed-->passed<!--/v--> | <!--v:results/model_pass_table.json#/models/claude-haiku-4-5-20251001/dug_out_channel/passed-->passed<!--/v--> | <!--v:results/model_pass_table.json#/models/claude-haiku-4-5-20251001/invasive_plant/passed-->did not pass<!--/v--> | <!--v:results/model_pass_table.json#/models/claude-haiku-4-5-20251001/pipe_running/passed-->did not pass<!--/v--> |
| Claude Sonnet 5 | <!--v:results/model_pass_table.json#/models/claude-sonnet-5/artificial_bank/passed-->passed<!--/v--> | <!--v:results/model_pass_table.json#/models/claude-sonnet-5/dug_out_channel/passed-->passed<!--/v--> | <!--v:results/model_pass_table.json#/models/claude-sonnet-5/invasive_plant/passed-->did not pass<!--/v--> | <!--v:results/model_pass_table.json#/models/claude-sonnet-5/pipe_running/passed-->did not pass<!--/v--> |
| Claude Opus 5.5 | <!--v:results/model_pass_table.json#/models/claude-opus-5-5/artificial_bank/passed-->passed<!--/v--> | <!--v:results/model_pass_table.json#/models/claude-opus-5-5/dug_out_channel/passed-->passed<!--/v--> | <!--v:results/model_pass_table.json#/models/claude-opus-5-5/invasive_plant/passed-->did not pass<!--/v--> | <!--v:results/model_pass_table.json#/models/claude-opus-5-5/pipe_running/passed-->passed<!--/v--> |
| Claude Fable 5.1 | <!--v:results/model_pass_table.json#/models/claude-fable-5-1/artificial_bank/passed-->passed<!--/v--> | <!--v:results/model_pass_table.json#/models/claude-fable-5-1/dug_out_channel/passed-->did not pass<!--/v--> | <!--v:results/model_pass_table.json#/models/claude-fable-5-1/invasive_plant/passed-->did not pass<!--/v--> | <!--v:results/model_pass_table.json#/models/claude-fable-5-1/pipe_running/passed-->passed<!--/v--> |

A pass is thin evidence: four photos, three runs. It licenses a model to ask one question about
that feature, never to answer it.

## The benchmark and its size

The same <!--v:results/model_card.json#/benchmark/photos-->16<!--/v--> photos, 4 per feature (2 with the
feature, 2 without), run <!--v:results/model_card.json#/benchmark/runs-->3<!--/v--> times more by
`evals/benchmark.py`, a second set of calls from the ones that wrote the pass table. Each cell is
right answers of all answers, with the Wilson 95 percent interval in percent. Can't tell counts
as wrong. The file is <!--v:results/model_card.json#/benchmark/file-->results/benchmark_20260924T054939Z.json<!--/v-->.

| Model | All 16 photos | Built bank | Dug-out channel | Invasive plant | Pipe running | Can't tell |
|---|---|---|---|---|---|---|
| Claude Haiku 4.5 | <!--v:results/model_card.json#/benchmark/models/claude-haiku-4-5-20251001/all/correct-->31<!--/v--> of <!--v:results/model_card.json#/benchmark/models/claude-haiku-4-5-20251001/all/n-->48<!--/v--> (<!--v:results/model_card.json#/benchmark/models/claude-haiku-4-5-20251001/all/low_pct-->50<!--/v--> to <!--v:results/model_card.json#/benchmark/models/claude-haiku-4-5-20251001/all/high_pct-->77<!--/v-->) | <!--v:results/model_card.json#/benchmark/models/claude-haiku-4-5-20251001/artificial_bank/correct-->12<!--/v--> of <!--v:results/model_card.json#/benchmark/models/claude-haiku-4-5-20251001/artificial_bank/n-->12<!--/v--> (<!--v:results/model_card.json#/benchmark/models/claude-haiku-4-5-20251001/artificial_bank/low_pct-->76<!--/v--> to <!--v:results/model_card.json#/benchmark/models/claude-haiku-4-5-20251001/artificial_bank/high_pct-->100<!--/v-->) | <!--v:results/model_card.json#/benchmark/models/claude-haiku-4-5-20251001/dug_out_channel/correct-->10<!--/v--> of <!--v:results/model_card.json#/benchmark/models/claude-haiku-4-5-20251001/dug_out_channel/n-->12<!--/v--> (<!--v:results/model_card.json#/benchmark/models/claude-haiku-4-5-20251001/dug_out_channel/low_pct-->55<!--/v--> to <!--v:results/model_card.json#/benchmark/models/claude-haiku-4-5-20251001/dug_out_channel/high_pct-->95<!--/v-->) | <!--v:results/model_card.json#/benchmark/models/claude-haiku-4-5-20251001/invasive_plant/correct-->0<!--/v--> of <!--v:results/model_card.json#/benchmark/models/claude-haiku-4-5-20251001/invasive_plant/n-->12<!--/v--> (<!--v:results/model_card.json#/benchmark/models/claude-haiku-4-5-20251001/invasive_plant/low_pct-->0<!--/v--> to <!--v:results/model_card.json#/benchmark/models/claude-haiku-4-5-20251001/invasive_plant/high_pct-->24<!--/v-->) | <!--v:results/model_card.json#/benchmark/models/claude-haiku-4-5-20251001/pipe_running/correct-->9<!--/v--> of <!--v:results/model_card.json#/benchmark/models/claude-haiku-4-5-20251001/pipe_running/n-->12<!--/v--> (<!--v:results/model_card.json#/benchmark/models/claude-haiku-4-5-20251001/pipe_running/low_pct-->47<!--/v--> to <!--v:results/model_card.json#/benchmark/models/claude-haiku-4-5-20251001/pipe_running/high_pct-->91<!--/v-->) | <!--v:results/model_card.json#/benchmark/models/claude-haiku-4-5-20251001/cant_tell_pct-->35<!--/v--> percent |
| Claude Sonnet 5 | <!--v:results/model_card.json#/benchmark/models/claude-sonnet-5/all/correct-->33<!--/v--> of <!--v:results/model_card.json#/benchmark/models/claude-sonnet-5/all/n-->48<!--/v--> (<!--v:results/model_card.json#/benchmark/models/claude-sonnet-5/all/low_pct-->55<!--/v--> to <!--v:results/model_card.json#/benchmark/models/claude-sonnet-5/all/high_pct-->80<!--/v-->) | <!--v:results/model_card.json#/benchmark/models/claude-sonnet-5/artificial_bank/correct-->12<!--/v--> of <!--v:results/model_card.json#/benchmark/models/claude-sonnet-5/artificial_bank/n-->12<!--/v--> (<!--v:results/model_card.json#/benchmark/models/claude-sonnet-5/artificial_bank/low_pct-->76<!--/v--> to <!--v:results/model_card.json#/benchmark/models/claude-sonnet-5/artificial_bank/high_pct-->100<!--/v-->) | <!--v:results/model_card.json#/benchmark/models/claude-sonnet-5/dug_out_channel/correct-->12<!--/v--> of <!--v:results/model_card.json#/benchmark/models/claude-sonnet-5/dug_out_channel/n-->12<!--/v--> (<!--v:results/model_card.json#/benchmark/models/claude-sonnet-5/dug_out_channel/low_pct-->76<!--/v--> to <!--v:results/model_card.json#/benchmark/models/claude-sonnet-5/dug_out_channel/high_pct-->100<!--/v-->) | <!--v:results/model_card.json#/benchmark/models/claude-sonnet-5/invasive_plant/correct-->0<!--/v--> of <!--v:results/model_card.json#/benchmark/models/claude-sonnet-5/invasive_plant/n-->12<!--/v--> (<!--v:results/model_card.json#/benchmark/models/claude-sonnet-5/invasive_plant/low_pct-->0<!--/v--> to <!--v:results/model_card.json#/benchmark/models/claude-sonnet-5/invasive_plant/high_pct-->24<!--/v-->) | <!--v:results/model_card.json#/benchmark/models/claude-sonnet-5/pipe_running/correct-->9<!--/v--> of <!--v:results/model_card.json#/benchmark/models/claude-sonnet-5/pipe_running/n-->12<!--/v--> (<!--v:results/model_card.json#/benchmark/models/claude-sonnet-5/pipe_running/low_pct-->47<!--/v--> to <!--v:results/model_card.json#/benchmark/models/claude-sonnet-5/pipe_running/high_pct-->91<!--/v-->) | <!--v:results/model_card.json#/benchmark/models/claude-sonnet-5/cant_tell_pct-->27<!--/v--> percent |
| Claude Opus 5.5 | <!--v:results/model_card.json#/benchmark/models/claude-opus-5-5/all/correct-->33<!--/v--> of <!--v:results/model_card.json#/benchmark/models/claude-opus-5-5/all/n-->48<!--/v--> (<!--v:results/model_card.json#/benchmark/models/claude-opus-5-5/all/low_pct-->55<!--/v--> to <!--v:results/model_card.json#/benchmark/models/claude-opus-5-5/all/high_pct-->80<!--/v-->) | <!--v:results/model_card.json#/benchmark/models/claude-opus-5-5/artificial_bank/correct-->12<!--/v--> of <!--v:results/model_card.json#/benchmark/models/claude-opus-5-5/artificial_bank/n-->12<!--/v--> (<!--v:results/model_card.json#/benchmark/models/claude-opus-5-5/artificial_bank/low_pct-->76<!--/v--> to <!--v:results/model_card.json#/benchmark/models/claude-opus-5-5/artificial_bank/high_pct-->100<!--/v-->) | <!--v:results/model_card.json#/benchmark/models/claude-opus-5-5/dug_out_channel/correct-->9<!--/v--> of <!--v:results/model_card.json#/benchmark/models/claude-opus-5-5/dug_out_channel/n-->12<!--/v--> (<!--v:results/model_card.json#/benchmark/models/claude-opus-5-5/dug_out_channel/low_pct-->47<!--/v--> to <!--v:results/model_card.json#/benchmark/models/claude-opus-5-5/dug_out_channel/high_pct-->91<!--/v-->) | <!--v:results/model_card.json#/benchmark/models/claude-opus-5-5/invasive_plant/correct-->0<!--/v--> of <!--v:results/model_card.json#/benchmark/models/claude-opus-5-5/invasive_plant/n-->12<!--/v--> (<!--v:results/model_card.json#/benchmark/models/claude-opus-5-5/invasive_plant/low_pct-->0<!--/v--> to <!--v:results/model_card.json#/benchmark/models/claude-opus-5-5/invasive_plant/high_pct-->24<!--/v-->) | <!--v:results/model_card.json#/benchmark/models/claude-opus-5-5/pipe_running/correct-->12<!--/v--> of <!--v:results/model_card.json#/benchmark/models/claude-opus-5-5/pipe_running/n-->12<!--/v--> (<!--v:results/model_card.json#/benchmark/models/claude-opus-5-5/pipe_running/low_pct-->76<!--/v--> to <!--v:results/model_card.json#/benchmark/models/claude-opus-5-5/pipe_running/high_pct-->100<!--/v-->) | <!--v:results/model_card.json#/benchmark/models/claude-opus-5-5/cant_tell_pct-->31<!--/v--> percent |
| Claude Fable 5.1 | <!--v:results/model_card.json#/benchmark/models/claude-fable-5-1/all/correct-->34<!--/v--> of <!--v:results/model_card.json#/benchmark/models/claude-fable-5-1/all/n-->48<!--/v--> (<!--v:results/model_card.json#/benchmark/models/claude-fable-5-1/all/low_pct-->57<!--/v--> to <!--v:results/model_card.json#/benchmark/models/claude-fable-5-1/all/high_pct-->82<!--/v-->) | <!--v:results/model_card.json#/benchmark/models/claude-fable-5-1/artificial_bank/correct-->12<!--/v--> of <!--v:results/model_card.json#/benchmark/models/claude-fable-5-1/artificial_bank/n-->12<!--/v--> (<!--v:results/model_card.json#/benchmark/models/claude-fable-5-1/artificial_bank/low_pct-->76<!--/v--> to <!--v:results/model_card.json#/benchmark/models/claude-fable-5-1/artificial_bank/high_pct-->100<!--/v-->) | <!--v:results/model_card.json#/benchmark/models/claude-fable-5-1/dug_out_channel/correct-->10<!--/v--> of <!--v:results/model_card.json#/benchmark/models/claude-fable-5-1/dug_out_channel/n-->12<!--/v--> (<!--v:results/model_card.json#/benchmark/models/claude-fable-5-1/dug_out_channel/low_pct-->55<!--/v--> to <!--v:results/model_card.json#/benchmark/models/claude-fable-5-1/dug_out_channel/high_pct-->95<!--/v-->) | <!--v:results/model_card.json#/benchmark/models/claude-fable-5-1/invasive_plant/correct-->0<!--/v--> of <!--v:results/model_card.json#/benchmark/models/claude-fable-5-1/invasive_plant/n-->12<!--/v--> (<!--v:results/model_card.json#/benchmark/models/claude-fable-5-1/invasive_plant/low_pct-->0<!--/v--> to <!--v:results/model_card.json#/benchmark/models/claude-fable-5-1/invasive_plant/high_pct-->24<!--/v-->) | <!--v:results/model_card.json#/benchmark/models/claude-fable-5-1/pipe_running/correct-->12<!--/v--> of <!--v:results/model_card.json#/benchmark/models/claude-fable-5-1/pipe_running/n-->12<!--/v--> (<!--v:results/model_card.json#/benchmark/models/claude-fable-5-1/pipe_running/low_pct-->76<!--/v--> to <!--v:results/model_card.json#/benchmark/models/claude-fable-5-1/pipe_running/high_pct-->100<!--/v-->) | <!--v:results/model_card.json#/benchmark/models/claude-fable-5-1/cant_tell_pct-->27<!--/v--> percent |

Twelve answers per feature is small. An interval such as
<!--v:results/model_card.json#/benchmark/models/claude-fable-5-1/dug_out_channel/low_pct-->55<!--/v--> to
<!--v:results/model_card.json#/benchmark/models/claude-fable-5-1/dug_out_channel/high_pct-->95<!--/v-->
percent means the test cannot tell a good model from a very good one. Read the intervals, not the
point numbers.

**On creek footage.** The four models also answered every feature question on
<!--v:results/footage_latest.json#/pool/frames-->46<!--/v--> frames from
<!--v:results/footage_latest.json#/pool/videos-->5<!--/v--> openly licensed videos in
<!--v:results/footage_latest.json#/pool/countries-->3<!--/v--> countries. No frame has a label
(<!--v:results/footage_latest.json#/pool/labelled_frames-->0<!--/v--> labelled), so this measures agreement
between models, not accuracy. The pair that agreed least, Haiku 4.5 and Fable 5.1, gave the same
answer on
<!--v:results/footage_latest.json#/agreement/dug_out_channel/pairs/claude-haiku-4-5-20251001 vs claude-fable-5-1/agree-->15<!--/v-->
of <!--v:results/footage_latest.json#/agreement/dug_out_channel/frames-->46<!--/v--> frames for a dug-out
channel. Four frames drawn by code, a white one, a black one, a room made of flat rectangles and a
screenshot of text (`evals/fixtures/__init__.py`), got can't tell as each model's majority answer
over three runs, on every feature (`results/footage_latest.json`, under `adversarial`; the run kept
the majority answers, not each reply).

## Known failure modes

- **A run once measured our config instead of the models.** The first paid sweep sent an answer
  tool whose allowed values came from YAML, where an unquoted yes and no are booleans. The models
  were told to answer `true` or `false`, and
  <!--v:results/model_sweep_20260924T030451Z.json#/counts/malformed-->73<!--/v--> of
  <!--v:results/model_sweep_20260924T030451Z.json#/counts/answers-->144<!--/v--> answers were malformed. The
  values are now quoted and pinned by
  `evals/tests/test_model_sweep.py::test_the_answer_tool_allows_exactly_the_three_words_as_strings`;
  the run done again had <!--v:results/model_sweep_20260924T031128Z.json#/counts/malformed-->0<!--/v-->
  malformed. Both runs stay in `results/`.
- **No model passes invasive plants.** In the sweep behind the pass table,
  <!--v:results/model_card.json#/by_feature/invasive_plant/cant_tell-->47<!--/v--> of the
  <!--v:results/model_card.json#/by_feature/invasive_plant/answers-->48<!--/v--> answers on the plant photos
  were can't tell. The plant photos are close views of a plant with no water in them, and the instruction
  says to answer can't tell when the photo does not show a stream. The notes show it: several name
  the plant, for example "possibly invasive Himalayan blackberry, but no stream is visible", and
  still answer can't tell. So this result measures our photos and our instruction as much as the
  models. The photos and the question wording are frozen with the tagged analysis plan, so
  changing them would be a deviation. The instruction is not in the plan: it is ours, in
  `evals/models.yaml`, and changing it would need a new paid run and a new pass table.
- **Can't tell is common.** Answers per feature in that sweep, all four models together:

  | Feature | Answers | Yes | No | Can't tell | Right |
  |---|---|---|---|---|---|
  | Built bank | <!--v:results/model_card.json#/by_feature/artificial_bank/answers-->48<!--/v--> | <!--v:results/model_card.json#/by_feature/artificial_bank/yes-->24<!--/v--> | <!--v:results/model_card.json#/by_feature/artificial_bank/no-->24<!--/v--> | <!--v:results/model_card.json#/by_feature/artificial_bank/cant_tell-->0<!--/v--> | <!--v:results/model_card.json#/by_feature/artificial_bank/correct-->48<!--/v--> |
  | Dug-out channel | <!--v:results/model_card.json#/by_feature/dug_out_channel/answers-->48<!--/v--> | <!--v:results/model_card.json#/by_feature/dug_out_channel/yes-->20<!--/v--> | <!--v:results/model_card.json#/by_feature/dug_out_channel/no-->24<!--/v--> | <!--v:results/model_card.json#/by_feature/dug_out_channel/cant_tell-->4<!--/v--> | <!--v:results/model_card.json#/by_feature/dug_out_channel/correct-->42<!--/v--> |
  | Invasive plant | <!--v:results/model_card.json#/by_feature/invasive_plant/answers-->48<!--/v--> | <!--v:results/model_card.json#/by_feature/invasive_plant/yes-->1<!--/v--> | <!--v:results/model_card.json#/by_feature/invasive_plant/no-->0<!--/v--> | <!--v:results/model_card.json#/by_feature/invasive_plant/cant_tell-->47<!--/v--> | <!--v:results/model_card.json#/by_feature/invasive_plant/correct-->1<!--/v--> |
  | Pipe running | <!--v:results/model_card.json#/by_feature/pipe_running/answers-->48<!--/v--> | <!--v:results/model_card.json#/by_feature/pipe_running/yes-->22<!--/v--> | <!--v:results/model_card.json#/by_feature/pipe_running/no-->23<!--/v--> | <!--v:results/model_card.json#/by_feature/pipe_running/cant_tell-->3<!--/v--> | <!--v:results/model_card.json#/by_feature/pipe_running/correct-->43<!--/v--> |

- **Models disagree on footage.** On the same frames, Haiku 4.5 answered yes for a dug-out
  channel on a share of
  <!--v:results/footage_latest.json#/agreement/dug_out_channel/yes_share/claude-haiku-4-5-20251001-->0.2<!--/v-->
  of them and Opus 5.5 on a share of
  <!--v:results/footage_latest.json#/agreement/dug_out_channel/yes_share/claude-opus-5-5-->0.0<!--/v-->.
  Without labels we cannot say which is right.
- **A pass can be luck.** Four photos, three runs. A pass on a feature says the model got these
  four photos right, not that it sees that feature in general.
- **The note is checked for form, not for truth.** The gate refuses markup, control characters and
  long notes, but a note that is wrong in plain words gets through. That is why a flag can only ask
  the person to look again, and the person's answer is what is stored.

## Cost

Every paid call is one line in `results/cost_log.jsonl`, with its tokens and its price; the fake
runs spend nothing. All paid calls together:
<!--v:results/model_card.json#/cost/real_calls-->5017<!--/v--> calls for
<!--v:results/model_card.json#/cost/real_usd-->41.1<!--/v--> USD, of which footage
<!--v:results/model_card.json#/cost/real_usd_by_purpose/footage-->34.2<!--/v--> USD, the sweeps
<!--v:results/model_card.json#/cost/real_usd_by_purpose/model_sweep-->3.7<!--/v--> USD and the benchmarks
<!--v:results/model_card.json#/cost/real_usd_by_purpose/benchmark-->3.2<!--/v--> USD. That includes the run
that measured our config and the three-model run before Opus 5.5 and Fable 5.1 joined.

- The four-model run: the sweep
  <!--v:results/model_sweep_20260924T054756Z.json#/counts/cost_usd-->2.2<!--/v--> USD, the benchmark
  <!--v:results/benchmark_20260924T054939Z.json#/cost_usd-->2.2<!--/v--> USD and the footage
  <!--v:results/footage_latest.json#/cost/usd-->23.6<!--/v--> USD.
- Per 100 footage frames, four models, direct calls at the full price:
  <!--v:results/footage_latest.json#/cost/per_100_frames_usd-->51.3<!--/v--> USD. The batch interface costs
  half as much, but a batch once waited three hours in the queue.
- The live site calls no model, so a volunteer's check costs nothing in model calls.

## The gate

`parse_flags` in `core/gate.py` takes any model output and returns flags or reasons, never an
error. A flag survives only if it names a known feature that this model passed, with a
confidence between 0 and 1 and a short plain note. Everything else is dropped with a reason in
plain words. On the footage run the gate saw
<!--v:results/footage_latest.json#/gate/candidates-->64<!--/v--> candidate flags, kept
<!--v:results/footage_latest.json#/gate/kept-->35<!--/v--> and dropped
<!--v:results/footage_latest.json#/gate/dropped-->29<!--/v-->, every one of those for a feature the model had
not passed: Haiku 4.5 on pipes
<!--v:results/footage_latest.json#/gate/drop_reasons/feature pipe_running not passed by model claude-haiku-4-5-20251001-->24<!--/v-->
times, Fable 5.1 on dug-out channels
<!--v:results/footage_latest.json#/gate/drop_reasons/feature dug_out_channel not passed by model claude-fable-5-1-->3<!--/v-->
and Haiku 4.5 on plants
<!--v:results/footage_latest.json#/gate/drop_reasons/feature invasive_plant not passed by model claude-haiku-4-5-20251001-->2<!--/v-->.

The kept flags by feature, counted again from the run's raw answers (`results/model_card.json`):
built banks <!--v:results/model_card.json#/footage_kept/by_feature/artificial_bank-->3<!--/v-->, dug-out channel
<!--v:results/model_card.json#/footage_kept/by_feature/dug_out_channel-->32<!--/v-->, plants
<!--v:results/model_card.json#/footage_kept/by_feature/invasive_plant-->0<!--/v--> and pipes
<!--v:results/model_card.json#/footage_kept/by_feature/pipe_running-->0<!--/v-->; the check has no question for a dug-out
channel, so a flag there asks nothing.

The gate's own tests throw arbitrary output at it, including huge numbers, deep nesting, a
million candidates and every Unicode direction control
(`core/tests/test_harden_gate_properties.py::test_the_gate_never_raises_and_leaves_its_inputs_as_they_were`,
`core/tests/test_harden_gate_properties.py::test_a_note_with_any_unicode_direction_control_is_dropped`,
`core/tests/test_harden_gate_properties.py::test_a_flood_of_a_million_drops_everything`). How the
whole path works, step by step, is in the README under "The gate, the heart of it".

## Check it yourself

- `uv run pytest -q core/tests/test_gate.py core/tests/test_checker.py evals/tests/test_committed_pass_table.py evals/tests/test_model_card.py`
- `make verify-claims`: every number on this page against `results/`.
- `uv run python evals/model_card.py --check`: the answer counts, the intervals and the cost
  against the sweep, the benchmark and the cost log.
