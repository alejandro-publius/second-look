"""The label page writes one file and shows nobody else's; merge refuses while unsettled."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import threading
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest
from PIL import Image

from scripts import label_photos, merge_labels
from scripts.ingest_photos import MANIFEST_COLUMNS

FIXTURES = Path(__file__).parent / "fixtures"
FEATURES = ("artificial_bank", "dug_out_channel", "invasive_plant", "pipe_running")


def write_manifest(root: Path, rows: list[dict[str, str]]) -> None:
    with (root / "photos" / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS)
        w.writeheader()
        for row in rows:
            w.writerow({c: row.get(c, "") for c in MANIFEST_COLUMNS})


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A small repo: 16 test photos, 1 warmup, features.yaml, and a stranger's labels file."""
    root = tmp_path / "repo"
    (root / "photos" / "placeholders").mkdir(parents=True)
    (root / "content").mkdir()
    (root / "results").mkdir()
    rows: list[dict[str, str]] = []
    n = 0
    for feature in FEATURES:
        for gold in ("present", "present", "absent", "absent"):
            n += 1
            pid = f"ph-test-{n:02d}"
            file = root / "photos" / "placeholders" / f"{pid}.jpg"
            Image.new("RGB", (64, 48), (128, 128, 128)).save(file, "JPEG")
            rows.append(
                {
                    "id": pid,
                    "file": f"placeholders/{pid}.jpg",
                    "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                    "license": "placeholder",
                    "scene_id": f"s{n}",
                    "role": "test",
                    "feature": feature,
                    "gold_label": gold,
                    "labeller_2": "",
                    "synthetic": "false",
                    "faces": "false",
                    "notes": "SECRET-NOTE gold is " + gold,
                }
            )
    file = root / "photos" / "placeholders" / "ph-warmup-01.jpg"
    Image.new("RGB", (64, 48), (128, 128, 128)).save(file, "JPEG")
    rows.append(
        {
            "id": "ph-warmup-01",
            "file": "placeholders/ph-warmup-01.jpg",
            "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
            "license": "placeholder",
            "role": "warmup",
            "synthetic": "false",
            "faces": "false",
        }
    )
    write_manifest(root, rows)
    shutil.copy(Path(__file__).parents[2] / "content" / "features.yaml", root / "content")
    (root / "labels_stranger.csv").write_text(
        "photo_id,feature,label,labelled_at_utc\n"
        "ph-test-01,artificial_bank,absent,2026-09-22T09:00:00Z\n",
        encoding="utf-8",
    )
    return root


@pytest.fixture()
def server(repo: Path) -> Iterator[str]:
    srv = label_photos.make_server(repo, "rachel", ("test",))
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    yield base
    srv.shutdown()
    srv.server_close()


def get(url: str) -> tuple[int, bytes]:
    with urlopen(url, timeout=5) as r:  # noqa: S310
        return r.status, r.read()


def post(url: str, data: dict[str, str]) -> int:
    req = Request(url, data=urlencode(data).encode(), method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urlopen(req, timeout=5) as r:  # noqa: S310
            return int(r.status)
    except Exception as e:  # HTTPError carries the status
        return int(getattr(e, "code", 0))


def test_page_binds_to_localhost_on_a_random_port(repo: Path) -> None:
    srv = label_photos.make_server(repo, "rachel", ("test",))
    try:
        host, port = srv.server_address[0], srv.server_address[1]
        assert host == "127.0.0.1" and port > 1024
    finally:
        srv.server_close()


def test_page_shows_question_and_never_gold_or_other_labels(server: str, repo: Path) -> None:
    status, body = get(f"{server}/")
    page = body.decode()
    assert status == 200
    assert "Labelling as rachel" in page
    assert "0 of 16 labelled" in page
    assert "Are the banks artificial" in page, "feature question from features.yaml"
    assert "ph-test-01" in page
    for word in ("SECRET-NOTE", "gold", "stranger", "labeller_2", "scene"):
        assert word not in page, f"{word!r} leaked into the labelling page"
    assert "present</button>" in page and "absent</button>" in page and "ambiguous</button>" in page
    assert "ph-test-01" in page and "absent,2026" not in page


def test_photo_route_serves_only_manifest_photos(server: str) -> None:
    status, body = get(f"{server}/photo/ph-test-01")
    assert status == 200 and body[:2] == b"\xff\xd8"
    assert post(f"{server}/photo/../../manifest.csv", {}) in {400, 404}
    try:
        get(f"{server}/photo/ph-warmup-01")
    except Exception as e:
        assert getattr(e, "code", 0) == 404, "warmup has no feature, so it is not in the queue"
    else:
        raise AssertionError("warmup photo should not be served")


def test_post_writes_only_own_file_and_advances(server: str, repo: Path) -> None:
    stranger_before = (repo / "labels_stranger.csv").read_bytes()
    assert post(f"{server}/label", {"photo_id": "ph-test-01", "label": "present"}) == 200
    assert post(f"{server}/label", {"photo_id": "ph-test-02", "label": "ambiguous"}) == 200
    assert post(f"{server}/label", {"photo_id": "ph-test-01", "label": "absent"}) == 200
    own = repo / "labels_rachel.csv"
    with own.open(newline="", encoding="utf-8") as f:
        rows = {r["photo_id"]: r for r in csv.DictReader(f)}
    assert rows["ph-test-01"]["label"] == "absent", "relabelling overwrites"
    assert rows["ph-test-02"]["label"] == "ambiguous"
    assert rows["ph-test-01"]["feature"] == "artificial_bank"
    assert set(rows) == {"ph-test-01", "ph-test-02"}
    assert (repo / "labels_stranger.csv").read_bytes() == stranger_before
    assert sorted(p.name for p in repo.glob("labels_*.csv")) == [
        "labels_rachel.csv",
        "labels_stranger.csv",
    ]
    _, body = get(f"{server}/")
    page = body.decode()
    assert "2 of 16 labelled" in page and "ph-test-03" in page
    assert "Does this channel look dug out" not in page, "still on artificial_bank photos"


def test_post_rejects_unknown_photo_or_label(server: str, repo: Path) -> None:
    assert post(f"{server}/label", {"photo_id": "ph-nope", "label": "present"}) == 400
    assert post(f"{server}/label", {"photo_id": "ph-test-01", "label": "maybe"}) == 400
    assert not (repo / "labels_rachel.csv").exists()


def test_bad_name_is_refused(repo: Path) -> None:
    with pytest.raises(SystemExit):
        label_photos.make_server(repo, "../etc", ("test",))


def test_kappa_arithmetic() -> None:
    assert merge_labels.cohen_kappa([]) is None
    same = [("present", "present"), ("absent", "absent")] * 4
    assert merge_labels.cohen_kappa(same) == 1.0
    assert merge_labels.cohen_kappa([("present", "present")] * 5) == 1.0, "one category, agreed"
    assert merge_labels.cohen_kappa([("present", "absent")] * 5) == 0.0, "one category each, wrong"
    # Textbook check: a=[p,p,a,a,p,a,p,a], b=[p,a,a,a,p,a,p,p]: po=6/8, pe=0.5, kappa=0.5
    pairs = list(zip("ppaapapa", "paaapapp", strict=True))
    assert merge_labels.cohen_kappa(pairs) == 0.5
    chance = [
        ("present", "present"),
        ("present", "absent"),
        ("absent", "present"),
        ("absent", "absent"),
    ]
    assert merge_labels.cohen_kappa(chance) == 0.0


def test_merge_reports_agreement_and_applies(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    a, b = FIXTURES / "labels_rachel.csv", FIXTURES / "labels_alex.csv"
    code = merge_labels.main([str(a), str(b), "--apply", "--root", str(repo)])
    out = capsys.readouterr().out
    assert code == 0
    assert not [line for line in out.splitlines() if line.startswith("disagree ")]
    assert "applied 16 labels" in out
    result = json.loads((repo / "results" / "key_agreement.json").read_text())
    assert result["labellers"] == ["rachel", "alex"]
    assert result["synthetic"] is False and result["script"] == "scripts/merge_labels.py"
    assert set(result["per_feature"]) == set(FEATURES)
    assert all(result["per_feature"][f]["kappa"] == 1.0 for f in FEATURES)
    assert result["overall"] == {"n": 16, "agree": 16, "kappa": 1.0}
    assert result["disagreements"] == [] and result["ambiguous"] == [] and result["applied"] == 16
    with (repo / "photos" / "manifest.csv").open(newline="", encoding="utf-8") as f:
        rows = {r["id"]: r for r in csv.DictReader(f)}
    assert rows["ph-test-01"]["labeller_2"] == "present"
    assert (
        rows["ph-test-03"]["labeller_2"] == "absent"
        and rows["ph-test-03"]["gold_label"] == "absent"
    )
    assert rows["ph-warmup-01"]["labeller_2"] == "", "untouched rows stay as they were"
    assert rows["ph-test-01"]["notes"].startswith("SECRET-NOTE"), "other columns untouched"


def test_merge_lists_disagreements_and_refuses_to_apply(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = (repo / "photos" / "manifest.csv").read_bytes()
    a, b = FIXTURES / "labels_rachel.csv", FIXTURES / "labels_alex_disagree.csv"
    code = merge_labels.main([str(a), str(b), "--apply", "--root", str(repo)])
    out = capsys.readouterr().out
    assert code == 1
    assert "disagree   ph-test-02  artificial_bank  rachel=present  alex_disagree=absent" in out
    assert "disagree   ph-test-10  invasive_plant  rachel=present  alex_disagree=ambiguous" in out
    assert "disagree   ph-test-15  pipe_running  rachel=absent  alex_disagree=present" in out
    assert "refusing to apply: 3 disagreements and 1 ambiguous labels remain" in out
    assert (repo / "photos" / "manifest.csv").read_bytes() == before
    result = json.loads((repo / "results" / "key_agreement.json").read_text())
    assert [d["photo_id"] for d in result["disagreements"]] == [
        "ph-test-02",
        "ph-test-10",
        "ph-test-15",
    ]
    assert [d["photo_id"] for d in result["ambiguous"]] == ["ph-test-10"]
    assert result["per_feature"]["dug_out_channel"]["kappa"] == 1.0
    assert result["per_feature"]["artificial_bank"]["kappa"] < 1.0
    assert result["applied"] == 0


def test_merge_without_apply_reports_and_exits_0(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    a, b = FIXTURES / "labels_rachel.csv", FIXTURES / "labels_alex_disagree.csv"
    assert merge_labels.main([str(a), str(b), "--root", str(repo)]) == 0
    assert "3 disagreements, 1 ambiguous" in capsys.readouterr().out


def test_merge_refuses_bad_files(
    repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "labels_bad.csv"
    bad.write_text("photo_id,feature,label\nph-test-01,artificial_bank,maybe\n", encoding="utf-8")
    code = merge_labels.main([str(FIXTURES / "labels_rachel.csv"), str(bad), "--root", str(repo)])
    assert code == 1 and "label 'maybe'" in capsys.readouterr().out
    code = merge_labels.main([str(FIXTURES / "labels_rachel.csv"), str(tmp_path / "nope.csv")])
    assert code == 1 and "not found" in capsys.readouterr().out
