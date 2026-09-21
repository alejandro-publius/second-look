"""The marking page writes marks into the lesson YAML, and preflight holds launch until Rachel
approves them.

Every test works on a copy of content/ and photos/, never on the real lesson files.
"""

from __future__ import annotations

import json
import re
import shutil
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest
import yaml

from scripts import label_photos, preflight
from scripts.label_photos import MarkError, MarkTarget

REPO = Path(__file__).parents[2]
LESSON = "artificial_bank"
PAIR_PHOTO = "ph-bank-05"
PRACTICE_PHOTO = "ph-bank-09"
PAIR = MarkTarget(LESSON, PAIR_PHOTO, "pair", 0)
PRACTICE = MarkTarget(LESSON, PRACTICE_PHOTO, "practice", -1)


def ok_runner(argv: list[str]) -> tuple[int, str]:
    """Preflight's subprocess checks pass; git says there is no tag."""
    if argv[:2] == ["git", "tag"]:
        return 0, ""
    return 0, "ok"


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A copy of the real content and photos, so nothing here touches the repo's lessons."""
    root = tmp_path / "repo"
    root.mkdir()
    shutil.copytree(REPO / "content", root / "content")
    shutil.copytree(REPO / "photos", root / "photos")
    return root


@pytest.fixture()
def server(repo: Path) -> Iterator[str]:
    srv = label_photos.make_marks_server(repo)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def get(url: str) -> tuple[int, bytes]:
    with urlopen(url, timeout=5) as r:  # noqa: S310
        return r.status, r.read()


def save(url: str, photo_id: str, marks: list[dict[str, Any]]) -> tuple[int, str]:
    data = urlencode({"photo_id": photo_id, "marks": json.dumps(marks)}).encode()
    req = Request(url + "/marks", data=data, method="POST")  # noqa: S310
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urlopen(req, timeout=5) as r:  # noqa: S310
            return int(r.status), r.read().decode()
    except Exception as e:  # HTTPError carries the status and the message we sent back
        return int(getattr(e, "code", 0)), getattr(e, "read", lambda: b"")().decode()


def approve(url: str, photo_id: str, who: str) -> tuple[int, str]:
    data = urlencode({"photo_id": photo_id, "who": who}).encode()
    req = Request(url + "/approve", data=data, method="POST")  # noqa: S310
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urlopen(req, timeout=5) as r:  # noqa: S310
            return int(r.status), r.read().decode()
    except Exception as e:  # HTTPError carries the status and the message we sent back
        return int(getattr(e, "code", 0)), getattr(e, "read", lambda: b"")().decode()


def lesson_doc(repo: Path, feature: str = LESSON) -> dict[str, Any]:
    return label_photos.load_lesson(label_photos.lesson_path(repo, feature))


def marks_in(repo: Path, target: MarkTarget) -> list[dict[str, Any]]:
    return label_photos.read_marks(lesson_doc(repo, target.feature), target)


def unapprove_every_mark(root: Path) -> None:
    """Strip the approvals from a copy of the lessons. The real ones were approved in Update 11D,
    so a test that wants the blocking path has to put the repo back into that state itself."""
    for path in sorted((root / "content" / "lessons").glob("*.yaml")):
        doc = label_photos.load_lesson(path)
        for _, mark in label_photos.iter_marks(doc):
            for key in ("approved", "approved_by", "approved_at"):
                mark.pop(key, None)
        path.write_text(yaml.safe_dump(doc), encoding="utf-8")


def marks_check(root: Path) -> preflight.Check:
    checks = {c.name: c for c in preflight.run_checks(root, runner=ok_runner)}
    return checks["marks_approved"]


def test_the_targets_are_the_actual_photos_and_the_practice_photo(repo: Path) -> None:
    targets = label_photos.load_mark_targets(repo)
    ours = [t for t in targets if t.feature == LESSON]
    assert [t.photo_id for t in ours] == [
        "ph-bank-05",
        "ph-bank-07",
        PRACTICE_PHOTO,
    ], "marks sit on the actual photo of a pair, never on the assume photo"
    assert ours[0].where == "contrast pair 1 marks" and ours[-1].where == "practice_marks"


def test_a_label_of_six_words_is_refused() -> None:
    assert label_photos.label_problem("one two three four five") is None
    problem = label_photos.label_problem("one two three four five six")
    assert problem is not None and problem.startswith("label has 6 words")
    assert "5 words or fewer" in problem
    assert label_photos.label_problem("   ") == "a mark needs a label"


def test_a_six_word_label_never_reaches_the_lesson_file(server: str, repo: Path) -> None:
    before = label_photos.lesson_path(repo, LESSON).read_bytes()
    long_label = {"x": 0.2, "y": 0.3, "label": "the concrete wall behind the willow"}
    status, body = save(server, PAIR_PHOTO, [long_label])
    assert status == 400
    assert body.startswith("label has 6 words")
    assert label_photos.lesson_path(repo, LESSON).read_bytes() == before, "nothing was written"


def test_a_written_mark_carries_approved_false(server: str, repo: Path) -> None:
    status, body = save(server, PAIR_PHOTO, [{"x": 0.25, "y": 0.75, "label": "the built edge"}])
    assert status == 200 and "1 wait for someone to approve" in body
    marks = marks_in(repo, PAIR)
    assert marks == [{"x": 0.25, "y": 0.75, "label": "the built edge", "approved": False}]
    text = label_photos.lesson_path(repo, LESSON).read_text()
    assert '- { x: 0.25, y: 0.75, label: "the built edge", approved: false }' in text


def test_the_practice_photo_writes_to_practice_marks(server: str, repo: Path) -> None:
    status, _ = save(server, PRACTICE_PHOTO, [{"x": 0.1, "y": 0.9, "label": "the pipe"}])
    assert status == 200
    assert marks_in(repo, PRACTICE) == [
        {"x": 0.1, "y": 0.9, "label": "the pipe", "approved": False}
    ]
    assert marks_in(repo, PAIR)[0]["label"] == "Concrete wall, not soil", "the pair is untouched"


def test_an_existing_approved_mark_is_preserved(server: str, repo: Path) -> None:
    path = label_photos.lesson_path(repo, LESSON)
    approved = {"x": 0.4, "y": 0.6, "label": "the built edge", "approved": True}
    label_photos.write_marks(path, PAIR, [approved])
    text = path.read_text().replace(
        'label: "the built edge", approved: false',
        'label: "the built edge", approved: true',
    )
    path.write_text(text)
    assert marks_in(repo, PAIR) == [approved], "Rachel has approved this one"

    status, body = save(
        server,
        PAIR_PHOTO,
        [
            {"x": 0.4, "y": 0.6, "label": "the built edge"},
            {"x": 0.8, "y": 0.2, "label": "the new mark"},
        ],
    )
    assert status == 200 and "1 wait for someone to approve" in body
    assert marks_in(repo, PAIR) == [
        approved,
        {"x": 0.8, "y": 0.2, "label": "the new mark", "approved": False},
    ]


def test_a_moved_or_renamed_mark_goes_back_to_unapproved(repo: Path) -> None:
    path = label_photos.lesson_path(repo, LESSON)
    old = [{"x": 0.4, "y": 0.6, "label": "the built edge", "approved": True}]
    moved = label_photos.merge_approved(old, [{"x": 0.41, "y": 0.6, "label": "the built edge"}])
    renamed = label_photos.merge_approved(old, [{"x": 0.4, "y": 0.6, "label": "the built wall"}])
    assert moved[0]["approved"] is False and renamed[0]["approved"] is False
    assert path.exists()


def test_a_mark_can_be_removed_before_saving(server: str, repo: Path) -> None:
    two = [{"x": 0.1, "y": 0.1, "label": "one"}, {"x": 0.2, "y": 0.2, "label": "two"}]
    assert save(server, PAIR_PHOTO, two)[0] == 200
    assert [m["label"] for m in marks_in(repo, PAIR)] == ["one", "two"]
    assert save(server, PAIR_PHOTO, two[:1])[0] == 200
    assert [m["label"] for m in marks_in(repo, PAIR)] == ["one"]
    assert save(server, PAIR_PHOTO, [])[0] == 200
    assert marks_in(repo, PAIR) == []
    assert "marks: []" in label_photos.lesson_path(repo, LESSON).read_text()


def test_the_write_keeps_the_comments_and_the_rest_of_the_file(repo: Path) -> None:
    path = label_photos.lesson_path(repo, LESSON)
    before_lines = path.read_text().splitlines()
    before_doc = yaml.safe_load(path.read_text())
    said: list[str] = []
    label_photos.write_marks(
        path, PAIR, [{"x": 0.3, "y": 0.3, "label": "the built edge"}], say=said.append
    )
    after_lines = path.read_text().splitlines()
    after_doc = yaml.safe_load(path.read_text())
    comments = [ln for ln in before_lines if ln.lstrip().startswith("#")]
    assert comments and comments == [ln for ln in after_lines if ln.lstrip().startswith("#")]
    assert said == [], "no comment was dropped, so the tool had nothing to warn about"
    before_doc["contrast_pairs"][0].pop("marks")
    after_doc["contrast_pairs"][0].pop("marks")
    assert before_doc == after_doc, "only that pair's marks changed"


def test_the_tool_says_so_when_a_write_would_drop_a_comment(repo: Path) -> None:
    path = label_photos.lesson_path(repo, LESSON)
    # Put a comment above the first mark, whatever that mark happens to say today.
    lines = path.read_text().splitlines()
    first = next(i for i, line in enumerate(lines) if line.lstrip().startswith("- { x:"))
    lines.insert(first, "      # Rachel: keep this one on the far bank")
    path.write_text("\n".join(lines) + "\n")
    said: list[str] = []
    label_photos.write_marks(
        path, PAIR, [{"x": 0.3, "y": 0.3, "label": "the built edge"}], say=said.append
    )
    assert said == [
        "warning: this write drops a comment from artificial_bank.yaml: "
        "# Rachel: keep this one on the far bank"
    ]
    assert "keep this one on the far bank" not in path.read_text()


def test_a_bad_number_is_refused(repo: Path) -> None:
    with pytest.raises(MarkError, match="between 0 and 1"):
        label_photos.clean_marks([{"x": 1.5, "y": 0.5, "label": "off the photo"}])
    with pytest.raises(MarkError, match="number x"):
        label_photos.clean_marks([{"y": 0.5, "label": "no x"}])


def test_the_page_shows_one_photo_with_its_marks_and_the_word_limit(server: str) -> None:
    status, body = get(server + "/")
    page = body.decode()
    assert status == 200
    assert "Place marks: artificial_bank" in page
    assert f"src='/photo/{PAIR_PHOTO}'" in page
    assert "contrast pair 1 marks" in page
    assert "Concrete wall, not soil" in page
    assert '"max_words": 5' in page
    assert "ph-bank-07" not in page.split("Photos:")[0], "one photo at a time"
    _, other = get(server + f"/?photo={PRACTICE_PHOTO}")
    assert "practice_marks" in other.decode()


def test_the_photo_route_serves_only_lesson_photos(server: str) -> None:
    status, body = get(server + f"/photo/{PAIR_PHOTO}")
    assert status == 200 and body[:2] == b"\xff\xd8"
    for path in ("/photo/ph-bank-01", "/photo/ph-bank-06", "/photo/nope"):
        with pytest.raises(Exception) as caught:
            get(server + path)
        assert getattr(caught.value, "code", 0) == 404
    assert save(server, "ph-bank-01", [])[0] == 400


def test_preflight_fails_while_a_mark_is_unapproved_and_passes_once_it_is(repo: Path) -> None:
    assert marks_check(repo).passed, "the real lessons ship approved (Update 11D)"
    unapprove_every_mark(repo)
    check = marks_check(repo)
    assert check.owner == "HUMAN" and not check.passed
    assert (
        'lesson artificial_bank pair 1: mark "Concrete wall, not soil" '
        "is not approved yet" in check.reasons
    )
    assert any("practice" in r for r in check.reasons)
    assert len(check.reasons) == 24, "two marks on each of the twelve lesson photos"

    for path in sorted((repo / "content" / "lessons").glob("*.yaml")):
        doc = label_photos.load_lesson(path)
        for _, mark in label_photos.iter_marks(doc):
            mark["approved"] = True
        path.write_text(yaml.safe_dump(doc), encoding="utf-8")
    assert marks_check(repo).passed, "every mark approved, so the gate opens"

    doc = label_photos.load_lesson(label_photos.lesson_path(repo, LESSON))
    doc["practice_marks"][0]["approved"] = False
    label_photos.lesson_path(repo, LESSON).write_text(yaml.safe_dump(doc), encoding="utf-8")
    back = marks_check(repo)
    assert not back.passed and len(back.reasons) == 1
    assert "practice" in back.reasons[0] and "artificial_bank" in back.reasons[0]


def test_the_printed_line_names_the_lesson_and_the_label(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    unapprove_every_mark(repo)
    preflight.report([marks_check(repo)])
    out = capsys.readouterr().out
    assert 'HUMAN  marks_approved: lesson artificial_bank pair 1: mark "Concrete' in out


def test_marks_mode_needs_no_name(repo: Path) -> None:
    with pytest.raises(SystemExit):
        label_photos.main(["--root", str(repo)])  # neither --name nor --marks
    targets = label_photos.load_mark_targets(repo)
    assert len(targets) == 12, "four lessons, two pairs and one practice photo each"


def test_approving_stamps_who_and_when_and_a_change_undoes_it(server: str, repo: Path) -> None:
    """Update 09 sections 1 and 4.2: any team member approves, and the stamp is the record."""
    save(server, PAIR_PHOTO, [{"x": 0.25, "y": 0.75, "label": "the built edge"}])
    status, body = approve(server, PAIR_PHOTO, "alex")
    assert status == 200, body
    assert "signed alex" in body
    marks = marks_in(repo, PAIR)
    assert marks[0]["approved"] is True
    assert marks[0]["approved_by"] == "alex"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", marks[0]["approved_at"])

    # Moving the mark is new work, so the approval and its stamp go away again.
    save(server, PAIR_PHOTO, [{"x": 0.30, "y": 0.75, "label": "the built edge"}])
    moved = marks_in(repo, PAIR)
    assert moved[0]["approved"] is False
    assert "approved_by" not in moved[0]


def test_approving_without_a_name_is_refused(server: str, repo: Path) -> None:
    save(server, PAIR_PHOTO, [{"x": 0.25, "y": 0.75, "label": "the built edge"}])
    status, body = approve(server, PAIR_PHOTO, "   ")
    assert status == 400
    assert "say who is approving" in body
    assert marks_in(repo, PAIR)[0]["approved"] is False
