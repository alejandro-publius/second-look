"""The content loader names each broken content file, and lists what humans still owe."""

from __future__ import annotations

import csv
import dataclasses
import hashlib
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from core.content_loader import (
    LICENSE_ALLOWLIST,
    NEEDS_ATTRIBUTION,
    Content,
    ContentError,
    Photo,
    load_content,
    placeholder_report,
)
from core.records import FEATURES

ROOT = Path(__file__).resolve().parents[2]

Rows = list[dict[str, str]]


def read_manifest(root: Path) -> tuple[Rows, list[str]]:
    with (root / "photos" / "manifest.csv").open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [dict(row) for row in reader]
        return rows, list(reader.fieldnames or [])


def write_manifest(root: Path, rows: Rows, fields: list[str]) -> None:
    with (root / "photos" / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def edit_manifest(root: Path, change: Callable[[Rows], None]) -> None:
    rows, fields = read_manifest(root)
    change(rows)
    write_manifest(root, rows, fields)


def row_of(rows: Rows, photo_id: str) -> dict[str, str]:
    return next(row for row in rows if row["id"] == photo_id)


def first_with_role(root: Path, role: str) -> dict[str, str]:
    rows, _ = read_manifest(root)
    return next(row for row in rows if row["role"] == role)


def edit_yaml(root: Path, name: str, change: Callable[[Any], None]) -> None:
    path = root / "content" / name
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    change(doc)
    path.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")


def problems(root: Path) -> list[str]:
    return load_content(root, strict=False).problems


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """The real content/ and manifest rows, with a tiny stand-in file for every photo."""
    shutil.copytree(ROOT / "content", tmp_path / "content")
    rows, fields = read_manifest(ROOT)
    for row in rows:
        data = f"stand-in for {row['id']}".encode()
        path = tmp_path / "photos" / row["file"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        row["sha256"] = hashlib.sha256(data).hexdigest()
    write_manifest(tmp_path, rows, fields)
    return tmp_path


# A tree that adds up.


def test_the_stand_in_tree_loads_strictly_with_no_problems(tree: Path) -> None:
    content = load_content(str(tree))
    assert content.problems == []
    assert content.root == tree.resolve()
    assert len(content.test_items) == 16
    assert sorted(content.lessons) == sorted(FEATURES)


def test_photo_by_id_returns_the_manifest_row_and_refuses_an_unknown_id(tree: Path) -> None:
    content = load_content(tree)
    photo = content.photo_by_id("ph-bank-01")
    assert photo.file == "bank/ph-bank-01.jpg"
    assert (photo.role, photo.feature, photo.gold_label) == ("test", "artificial_bank", "present")
    assert photo.is_placeholder is False
    with pytest.raises(KeyError):
        content.photo_by_id("ph-not-in-the-manifest")


def test_strict_mode_raises_every_problem_joined_by_newlines(tree: Path) -> None:
    edit_yaml(tree, "followups.yaml", lambda doc: doc.update(max_questions=3))
    (tree / "photos" / "bank" / "ph-bank-01.jpg").write_bytes(b"changed after hashing")
    with pytest.raises(ContentError) as caught:
        load_content(tree)
    lines = str(caught.value).split("\n")
    assert "sha256 mismatch: photos/bank/ph-bank-01.jpg" in lines
    assert "followups.yaml max_questions must be 2" in lines
    assert lines == problems(tree)


def test_content_hash_is_stable_and_moves_when_a_test_item_changes(tree: Path) -> None:
    first = load_content(tree).content_hash()
    assert first == load_content(tree).content_hash()
    assert len(first) == 16 and all(ch in "0123456789abcdef" for ch in first)

    def swap_photos(doc: Any) -> None:
        a, b = doc["items"][0], doc["items"][1]
        a["photo_id"], b["photo_id"] = b["photo_id"], a["photo_id"]

    edit_yaml(tree, "test_items.yaml", swap_photos)
    assert load_content(tree).content_hash() != first


# The photo manifest.


def test_a_missing_manifest_is_reported_and_no_photos_load(tree: Path) -> None:
    (tree / "photos" / "manifest.csv").unlink()
    content = load_content(tree, strict=False)
    assert "photos/manifest.csv missing" in content.problems
    assert content.photos == {}
    assert "test item t01 points at unknown photo 'ph-bank-01'" in content.problems


def test_a_manifest_row_whose_file_is_gone_is_reported_and_left_out(tree: Path) -> None:
    (tree / "photos" / "bank" / "ph-bank-01.jpg").unlink()
    content = load_content(tree, strict=False)
    assert "manifest row without file: photos/bank/ph-bank-01.jpg" in content.problems
    assert "ph-bank-01" not in content.photos


def test_a_photo_whose_bytes_changed_fails_the_hash_check(tree: Path) -> None:
    (tree / "photos" / "bank" / "ph-bank-01.jpg").write_bytes(b"a different picture")
    assert problems(tree) == ["sha256 mismatch: photos/bank/ph-bank-01.jpg"]


@pytest.mark.parametrize(
    "licence", ["CC-BY-NC-4.0", "CC-BY-ND-4.0", "all-rights-reserved", "cc-by-4.0", ""]
)
def test_a_licence_off_the_allowlist_is_refused(tree: Path, licence: str) -> None:
    edit_manifest(tree, lambda rows: row_of(rows, "ph-bank-01").update(license=licence))
    assert problems(tree) == [f"license not on allowlist: photos/bank/ph-bank-01.jpg ({licence})"]


@pytest.mark.parametrize("licence", ["CC-BY-2.0", "CC-BY-SA-3.0", "CC0-1.0", "public-domain"])
def test_an_older_licence_version_is_kept_exactly_as_given(tree: Path, licence: str) -> None:
    edit_manifest(tree, lambda rows: row_of(rows, "ph-bank-01").update(license=licence))
    photo = load_content(tree).photo_by_id("ph-bank-01")
    assert photo.license == licence
    assert photo.is_placeholder is False


def test_only_cc_by_licences_ask_for_attribution() -> None:
    assert NEEDS_ATTRIBUTION <= LICENSE_ALLOWLIST
    assert {"CC-BY-2.0", "CC-BY-SA-4.0", "own-CC-BY-4.0"} <= NEEDS_ATTRIBUTION
    assert not NEEDS_ATTRIBUTION & {"CC0-1.0", "public-domain", "placeholder"}


def test_a_placeholder_licence_loads_but_shows_up_as_a_missing_human_input(tree: Path) -> None:
    edit_manifest(tree, lambda rows: row_of(rows, "ph-bank-01").update(license="placeholder"))
    content = load_content(tree)
    assert content.photo_by_id("ph-bank-01").is_placeholder is True
    assert "placeholder photo in role test: ph-bank-01" in placeholder_report(content)


def test_an_unknown_role_is_refused(tree: Path) -> None:
    practice = first_with_role(tree, "practice")
    edit_manifest(tree, lambda rows: row_of(rows, practice["id"]).update(role="hero"))
    assert problems(tree) == [f"unknown role 'hero': photos/{practice['file']}"]


def test_a_test_photo_labelled_ambiguous_is_refused(tree: Path) -> None:
    edit_manifest(tree, lambda rows: row_of(rows, "ph-bank-01").update(gold_label="ambiguous"))
    assert "test photo labelled ambiguous: ph-bank-01" in problems(tree)


def test_a_lesson_photo_may_be_labelled_ambiguous(tree: Path) -> None:
    lesson = first_with_role(tree, "lesson")
    edit_manifest(tree, lambda rows: row_of(rows, lesson["id"]).update(gold_label="ambiguous"))
    assert problems(tree) == []


@pytest.mark.parametrize("flag", ["true", "TRUE", "1", "yes"])
def test_a_photo_flagged_synthetic_is_refused(tree: Path, flag: str) -> None:
    edit_manifest(tree, lambda rows: row_of(rows, "ph-bank-01").update(synthetic=flag))
    assert problems(tree) == ["synthetic image in manifest: ph-bank-01"]


@pytest.mark.parametrize("flag", ["true", "1", "yes"])
def test_a_photo_flagged_for_faces_is_refused(tree: Path, flag: str) -> None:
    edit_manifest(tree, lambda rows: row_of(rows, "ph-bank-01").update(faces=flag))
    assert problems(tree) == ["faces flagged: ph-bank-01"]


@pytest.mark.parametrize("flag", ["false", " False ", "0", ""])
def test_false_zero_and_blank_all_read_as_not_flagged(tree: Path, flag: str) -> None:
    edit_manifest(tree, lambda rows: row_of(rows, "ph-bank-01").update(synthetic=flag, faces=flag))
    assert problems(tree) == []


def test_a_repeated_photo_id_is_refused(tree: Path) -> None:
    edit_manifest(tree, lambda rows: rows.append(dict(row_of(rows, "ph-bank-01"))))
    assert problems(tree) == ["duplicate photo id: ph-bank-01"]


def test_an_image_without_a_manifest_row_is_found_in_any_folder_and_case(tree: Path) -> None:
    (tree / "photos" / "bank" / "stray.JPG").write_bytes(b"stray")
    (tree / "photos" / "new").mkdir()
    (tree / "photos" / "new" / "extra.webp").write_bytes(b"extra")
    (tree / "photos" / "notes.txt").write_text("not an image", encoding="utf-8")
    assert sorted(problems(tree)) == [
        "photo without manifest row: photos/bank/stray.JPG",
        "photo without manifest row: photos/new/extra.webp",
    ]


def test_a_manifest_without_the_second_label_column_still_loads(tree: Path) -> None:
    rows, fields = read_manifest(tree)
    for row in rows:
        del row["labeller_2"]
    write_manifest(tree, rows, [name for name in fields if name != "labeller_2"])
    content = load_content(tree)
    assert {p.labeller_2 for p in content.photos.values()} == {""}


# Lesson and practice photos stay apart from the test photos.


def test_a_lesson_photo_with_the_same_bytes_as_a_test_photo_is_refused(tree: Path) -> None:
    lesson = first_with_role(tree, "lesson")
    test_file = tree / "photos" / "bank" / "ph-bank-01.jpg"
    shutil.copyfile(test_file, tree / "photos" / lesson["file"])
    same = hashlib.sha256(test_file.read_bytes()).hexdigest()
    edit_manifest(tree, lambda rows: row_of(rows, lesson["id"]).update(sha256=same))
    assert problems(tree) == [f"lesson photo {lesson['id']} is also a test photo (same hash)"]


def test_a_practice_photo_from_a_test_photo_scene_is_refused(tree: Path) -> None:
    practice = first_with_role(tree, "practice")
    rows, _ = read_manifest(tree)
    scene = row_of(rows, "ph-bank-01")["scene_id"]
    edit_manifest(tree, lambda rows: row_of(rows, practice["id"]).update(scene_id=scene))
    assert problems(tree) == [
        f"practice photo {practice['id']} shares scene {scene} with a test photo"
    ]


# The warm-up pair.


def test_a_warm_up_with_one_photo_is_refused(tree: Path) -> None:
    edit_yaml(tree, "test_items.yaml", lambda doc: doc["warmup"].pop(0))
    assert problems(tree) == ["warm-up has 1 photos, needs 2"]


def test_a_warm_up_item_pointing_at_an_unknown_photo_is_refused(tree: Path) -> None:
    edit_yaml(tree, "test_items.yaml", lambda doc: doc["warmup"][0].update(photo_id="ph-nope"))
    assert problems(tree) == ["warm-up item w01 points at unknown photo ph-nope"]


def test_a_warm_up_item_pointing_at_a_test_photo_is_refused(tree: Path) -> None:
    edit_yaml(tree, "test_items.yaml", lambda doc: doc["warmup"][0].update(photo_id="ph-bank-01"))
    assert problems(tree) == ["warm-up item w01 points at a test photo"]


@pytest.mark.parametrize("value", ["yes", 1, None, "missing"])
def test_a_warm_up_item_needs_more_natural_as_true_or_false(tree: Path, value: object) -> None:
    def change(doc: Any) -> None:
        item = doc["warmup"][0]
        if value == "missing":
            del item["more_natural"]
        else:
            item["more_natural"] = value

    edit_yaml(tree, "test_items.yaml", change)
    assert problems(tree) == ["warm-up item w01 needs more_natural true or false"]


@pytest.mark.parametrize("flag", [True, False])
def test_exactly_one_warm_up_photo_is_the_more_natural_one(tree: Path, flag: bool) -> None:
    def change(doc: Any) -> None:
        for item in doc["warmup"]:
            item["more_natural"] = flag

    edit_yaml(tree, "test_items.yaml", change)
    n = 2 if flag else 0
    assert problems(tree) == [f"{n} warm-up photos marked more_natural, needs exactly 1"]


# The 16 test items.


def test_a_test_set_one_item_short_is_refused(tree: Path) -> None:
    edit_yaml(tree, "test_items.yaml", lambda doc: doc["items"].pop())
    assert problems(tree) == [
        "test set has 15 items, needs 16",
        "test set needs 2 absent items for pipe_running, has 1",
    ]


def test_a_repeated_test_item_id_is_refused(tree: Path) -> None:
    edit_yaml(tree, "test_items.yaml", lambda doc: doc["items"][1].update(id="t01"))
    assert problems(tree) == ["duplicate test item id t01"]


def test_a_test_item_with_an_unknown_feature_is_refused(tree: Path) -> None:
    edit_yaml(tree, "test_items.yaml", lambda doc: doc["items"][0].update(feature="concrete"))
    assert problems(tree) == [
        "test item t01 has unknown feature 'concrete'",
        "test item t01 feature concrete disagrees with manifest artificial_bank",
        "test set needs 2 present items for artificial_bank, has 1",
    ]


def test_a_test_item_gold_must_be_present_or_absent(tree: Path) -> None:
    edit_yaml(tree, "test_items.yaml", lambda doc: doc["items"][0].update(gold="maybe"))
    found = problems(tree)
    assert "test item t01 gold must be present or absent, got 'maybe'" in found
    assert "test item t01 gold maybe disagrees with manifest present" in found


def test_a_test_item_pointing_at_an_unknown_photo_is_refused(tree: Path) -> None:
    edit_yaml(tree, "test_items.yaml", lambda doc: doc["items"][0].update(photo_id="ph-nope"))
    assert problems(tree) == ["test item t01 points at unknown photo 'ph-nope'"]


def test_a_test_item_on_a_lesson_photo_is_refused(tree: Path) -> None:
    lesson = first_with_role(tree, "lesson")
    edit_yaml(tree, "test_items.yaml", lambda doc: doc["items"][0].update(photo_id=lesson["id"]))
    assert "test item t01 uses a lesson photo" in problems(tree)


def test_a_test_item_gold_that_disagrees_with_the_manifest_is_refused(tree: Path) -> None:
    edit_yaml(tree, "test_items.yaml", lambda doc: doc["items"][0].update(gold="absent"))
    assert problems(tree) == [
        "test item t01 gold absent disagrees with manifest present",
        "test set needs 2 present items for artificial_bank, has 1",
        "test set needs 2 absent items for artificial_bank, has 3",
    ]


def test_a_test_item_feature_that_disagrees_with_the_manifest_is_refused(tree: Path) -> None:
    edit_yaml(
        tree, "test_items.yaml", lambda doc: doc["items"][0].update(feature="dug_out_channel")
    )
    found = problems(tree)
    assert "test item t01 feature dug_out_channel disagrees with manifest artificial_bank" in found
    assert "test set needs 2 present items for dug_out_channel, has 3" in found


# The other content files.


def test_features_must_be_exactly_the_four_tested_features(tree: Path) -> None:
    edit_yaml(tree, "features.yaml", lambda doc: doc["features"].pop())
    ids = [fid for fid in FEATURES if fid != FEATURES[-1]]
    assert f"features.yaml ids {ids} must be exactly {list(FEATURES)}" in problems(tree)


def test_a_feature_with_an_empty_question_is_refused(tree: Path) -> None:
    edit_yaml(tree, "features.yaml", lambda doc: doc["features"][0].update(question=""))
    assert problems(tree) == ["feature artificial_bank has no test question"]


def test_a_feature_must_say_whether_it_was_verified_against_the_app(tree: Path) -> None:
    edit_yaml(tree, "features.yaml", lambda doc: doc["features"][0].pop("verified_against_app"))
    assert problems(tree) == ["feature artificial_bank lacks verified_against_app"]


def test_every_feature_needs_a_lesson_file(tree: Path) -> None:
    (tree / "content" / "lessons" / "pipe_running.yaml").unlink()
    assert problems(tree) == ["no lesson file for pipe_running"]


def test_repeated_form_item_ids_are_refused(tree: Path) -> None:
    def change(doc: Any) -> None:
        doc["items"][1]["id"] = doc["items"][0]["id"]

    edit_yaml(tree, "form.yaml", change)
    assert "duplicate form item ids: ['channel_form']" in problems(tree)


def test_a_form_item_must_say_whether_it_was_verified_against_the_app(tree: Path) -> None:
    edit_yaml(tree, "form.yaml", lambda doc: doc["items"][0].pop("verified_against_app"))
    assert problems(tree) == ["form item channel_form lacks verified_against_app"]


def test_a_followup_rule_that_needs_an_unknown_form_item_is_refused(tree: Path) -> None:
    edit_yaml(tree, "followups.yaml", lambda doc: doc["rules"][0]["needs_items"].append("nope"))
    assert problems(tree) == ["followup rule dry_pipe needs unknown item nope"]


@pytest.mark.parametrize("value", [1, 3])
def test_followups_allow_two_questions_and_no_other_number(tree: Path, value: int) -> None:
    edit_yaml(tree, "followups.yaml", lambda doc: doc.update(max_questions=value))
    assert problems(tree) == ["followups.yaml max_questions must be 2"]


def test_followups_without_max_questions_default_to_two(tree: Path) -> None:
    edit_yaml(tree, "followups.yaml", lambda doc: doc.pop("max_questions"))
    assert problems(tree) == []


@pytest.mark.parametrize("key", ["id", "audience", "text", "source", "approved"])
def test_every_approved_sentence_needs_its_five_keys(tree: Path, key: str) -> None:
    doc = yaml.safe_load((tree / "content" / "approved_sentences.yaml").read_text("utf-8"))
    sentence_id = None if key == "id" else doc["sentences"][0]["id"]
    edit_yaml(tree, "approved_sentences.yaml", lambda d: d["sentences"][0].pop(key))
    assert problems(tree) == [f"sentence {sentence_id} lacks {key}"]


def test_a_broken_region_pack_is_reported_as_a_problem(tree: Path) -> None:
    pack = {"region": "zz-broken", "creeks": [{"slug": "Bad Slug", "name": "Bad"}]}
    path = tree / "content" / "regions" / "zz-broken.yaml"
    path.write_text(yaml.safe_dump(pack), encoding="utf-8")
    content = load_content(tree, strict=False)
    assert "zz-broken" in content.regions
    assert content.problems == [
        "region zz-broken, creek 'Bad Slug': slug must be lower case letters, digits and hyphens"
    ]


@pytest.mark.xfail(
    strict=True,
    raises=TypeError,
    reason="bug: a feature with no id crashes load_content with TypeError, not a reported problem",
)
def test_a_feature_with_no_id_is_reported_not_a_crash(tree: Path) -> None:
    edit_yaml(tree, "features.yaml", lambda doc: doc["features"][0].pop("id"))
    found = problems(tree)
    assert any(p.startswith("features.yaml ids ") for p in found)


# What humans still owe before launch.


def stub_photo(photo_id: str, *, role: str = "test", licence: str = "CC-BY-4.0") -> Photo:
    return Photo(
        id=photo_id,
        file=f"bank/{photo_id}.jpg",
        sha256="0" * 64,
        license=licence,
        scene_id=f"scene-{photo_id}",
        role=role,
        feature="artificial_bank",
        gold_label="present",
        labeller_2="present",
        is_placeholder=licence == "placeholder",
    )


def ready(**changes: Any) -> Content:
    """Content with every human input in place, then the given fields swapped in."""
    base = Content(
        root=Path("."),
        features=[
            {
                "id": "artificial_bank",
                "app_item": "bank_type",
                "verified_against_app": True,
                "wording_status": "frozen",
            }
        ],
        form={"items": [{"id": "bank_type", "verified_against_app": True}]},
        test_items=[],
        followups={},
        sentences=[{"id": "s1", "approved": True}],
        locale={},
        glossary=[],
        regions={},
        lessons={"artificial_bank": {"approved": True}},
        photos={"ph-1": stub_photo("ph-1")},
    )
    return dataclasses.replace(base, **changes)


def test_content_with_every_human_input_has_nothing_to_report() -> None:
    assert placeholder_report(ready()) == []


@pytest.mark.parametrize("role", ["test", "lesson", "practice", "warmup"])
def test_a_placeholder_photo_in_a_shown_role_is_reported(role: str) -> None:
    photos = {"ph-1": stub_photo("ph-1", role=role, licence="placeholder")}
    assert placeholder_report(ready(photos=photos)) == [f"placeholder photo in role {role}: ph-1"]


def test_a_placeholder_benchmark_photo_is_not_reported() -> None:
    photos = {"ph-1": stub_photo("ph-1", role="benchmark", licence="placeholder")}
    assert placeholder_report(ready(photos=photos)) == []


def test_only_a_test_photo_needs_a_second_label() -> None:
    photos = {
        "ph-1": dataclasses.replace(stub_photo("ph-1"), labeller_2=""),
        "ph-2": dataclasses.replace(stub_photo("ph-2", role="lesson"), labeller_2=""),
    }
    assert placeholder_report(ready(photos=photos)) == ["no second label for test photo ph-1"]


def test_an_unverified_feature_is_reported_only_when_the_app_has_an_item_for_it() -> None:
    tied: dict[str, Any] = {"id": "artificial_bank", "app_item": "bank_type"}
    own: dict[str, Any] = {"id": "dug_out_channel", "app_item": None}
    for feature in (tied, own):
        feature.update(verified_against_app=False, wording_status="frozen")
    assert placeholder_report(ready(features=[tied, own])) == [
        "feature artificial_bank question not verified against the app"
    ]


@pytest.mark.parametrize("status", ["draft", None])
def test_a_feature_question_not_frozen_is_reported(status: str | None) -> None:
    feature = {"id": "artificial_bank", "verified_against_app": True, "wording_status": status}
    assert placeholder_report(ready(features=[feature])) == [
        "feature artificial_bank question wording not frozen"
    ]


def test_an_unverified_form_item_is_reported() -> None:
    form = {"items": [{"id": "bank_type", "verified_against_app": False}, {"id": "habitats"}]}
    assert placeholder_report(ready(form=form)) == [
        "form item bank_type not verified against the app",
        "form item habitats not verified against the app",
    ]


def test_an_unapproved_lesson_is_reported() -> None:
    lessons = {"artificial_bank": {"approved": False}, "pipe_running": {}}
    assert placeholder_report(ready(lessons=lessons)) == [
        "lesson artificial_bank not approved",
        "lesson pipe_running not approved",
    ]


def test_an_unapproved_sentence_is_reported() -> None:
    sentences = [{"id": "s1", "approved": False}, {"id": "s2"}, {"id": "s3", "approved": True}]
    assert placeholder_report(ready(sentences=sentences)) == [
        "sentence s1 not approved",
        "sentence s2 not approved",
    ]
