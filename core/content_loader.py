"""Load and check every content file and the photo manifest. Fails loudly (master brief section 6).

Read-only. Returns plain dataclasses the API, the evals and preflight all use.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from core.records import FEATURES, ITEMS_PER_FEATURE
from core.regions import RegionError, creeks_from_regions

# Every licence here is one we may show with attribution. The version matters and is recorded as
# given, never rounded to 4.0: Wikimedia and iNaturalist carry a lot of 2.0 and 3.0, and refusing
# those halved the pool of usable creek photos for no gain to anyone.
LICENSE_ALLOWLIST = {
    "CC0-1.0",
    "CC-BY-2.0",
    "CC-BY-3.0",
    "CC-BY-4.0",
    "CC-BY-SA-2.0",
    "CC-BY-SA-3.0",
    "CC-BY-SA-4.0",
    "public-domain",
    "own-CC-BY-4.0",
    "placeholder",
}
# The licences that ask us to name the author wherever the photo appears. /credits does that.
NEEDS_ATTRIBUTION = {lic for lic in LICENSE_ALLOWLIST if lic.startswith(("CC-BY", "own-CC-BY"))}
REAL_LICENSES = LICENSE_ALLOWLIST - {"placeholder"}
ROLES = {"warmup", "lesson", "practice", "test", "benchmark"}
TEST_SIZE = 16
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


class ContentError(Exception):
    """Raised with every problem found, joined by newlines."""


@dataclass(frozen=True)
class Photo:
    id: str
    file: str
    sha256: str
    license: str
    scene_id: str
    role: str
    feature: str
    gold_label: str
    labeller_2: str
    is_placeholder: bool


@dataclass
class Content:
    root: Path
    features: list[dict[str, Any]]
    form: dict[str, Any]
    test_items: list[dict[str, Any]]
    followups: dict[str, Any]
    sentences: list[dict[str, Any]]
    locale: dict[str, str]
    glossary: list[dict[str, Any]]
    regions: dict[str, dict[str, Any]]
    lessons: dict[str, dict[str, Any]]
    photos: dict[str, Photo]
    problems: list[str] = field(default_factory=list)

    def content_hash(self) -> str:
        h = hashlib.sha256()
        for name in ("features", "form", "test_items", "followups", "locale", "lessons"):
            h.update(json.dumps(getattr(self, name), sort_keys=True, default=str).encode())
        return h.hexdigest()[:16]

    def photo_by_id(self, photo_id: str) -> Photo:
        return self.photos[photo_id]


def _yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _flag_false(value: str) -> bool:
    return value.strip().lower() in {"false", "0", ""}


def _load_manifest(root: Path, problems: list[str]) -> dict[str, Photo]:
    manifest = root / "photos" / "manifest.csv"
    photos: dict[str, Photo] = {}
    if not manifest.exists():
        problems.append("photos/manifest.csv missing")
        return photos
    with manifest.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        path = root / "photos" / row["file"]
        if not path.exists():
            problems.append(f"manifest row without file: photos/{row['file']}")
            continue
        if _sha256(path) != row["sha256"]:
            problems.append(f"sha256 mismatch: photos/{row['file']}")
        if row["license"] not in LICENSE_ALLOWLIST:
            problems.append(f"license not on allowlist: photos/{row['file']} ({row['license']})")
        if row["role"] not in ROLES:
            problems.append(f"unknown role {row['role']!r}: photos/{row['file']}")
        if row["role"] == "test" and row["gold_label"] == "ambiguous":
            problems.append(f"test photo labelled ambiguous: {row['id']}")
        if not _flag_false(row["synthetic"]):
            problems.append(f"synthetic image in manifest: {row['id']}")
        if not _flag_false(row["faces"]):
            problems.append(f"faces flagged: {row['id']}")
        if row["id"] in photos:
            problems.append(f"duplicate photo id: {row['id']}")
        photos[row["id"]] = Photo(
            id=row["id"],
            file=row["file"],
            sha256=row["sha256"],
            license=row["license"],
            scene_id=row["scene_id"],
            role=row["role"],
            feature=row["feature"],
            gold_label=row["gold_label"],
            labeller_2=row.get("labeller_2", ""),
            is_placeholder=row["license"] == "placeholder",
        )
    images = [p for p in (root / "photos").rglob("*") if p.suffix.lower() in IMAGE_SUFFIXES]
    listed = {str((root / "photos" / p.file).resolve()) for p in photos.values()}
    for img in images:
        if str(img.resolve()) not in listed:
            problems.append(f"photo without manifest row: {img.relative_to(root)}")
    return photos


def _check_disjoint(photos: dict[str, Photo], problems: list[str]) -> None:
    test = [p for p in photos.values() if p.role == "test"]
    test_hashes = {p.sha256 for p in test}
    test_scenes = {p.scene_id for p in test}
    for p in photos.values():
        if p.role in {"lesson", "practice"}:
            if p.sha256 in test_hashes:
                problems.append(f"{p.role} photo {p.id} is also a test photo (same hash)")
            if p.scene_id in test_scenes:
                problems.append(
                    f"{p.role} photo {p.id} shares scene {p.scene_id} with a test photo"
                )


def _check_test_items(
    items: list[dict[str, Any]], photos: dict[str, Photo], problems: list[str]
) -> None:
    if len(items) != TEST_SIZE:
        problems.append(f"test set has {len(items)} items, needs {TEST_SIZE}")
    for item_id, n in Counter(i.get("id") for i in items).items():
        if n > 1:
            problems.append(f"duplicate test item id {item_id}")
    per_feature: Counter[tuple[str, str]] = Counter()
    for item in items:
        iid, feature, gold, photo_id = (
            item.get("id"),
            item.get("feature"),
            item.get("gold"),
            item.get("photo_id"),
        )
        if feature not in FEATURES:
            problems.append(f"test item {iid} has unknown feature {feature!r}")
        if gold not in {"present", "absent"}:
            problems.append(f"test item {iid} gold must be present or absent, got {gold!r}")
        photo = photos.get(str(photo_id))
        if photo is None:
            problems.append(f"test item {iid} points at unknown photo {photo_id!r}")
        else:
            if photo.role != "test":
                problems.append(f"test item {iid} uses a {photo.role} photo")
            if photo.gold_label != gold:
                problems.append(
                    f"test item {iid} gold {gold} disagrees with manifest {photo.gold_label}"
                )
            if photo.feature != feature:
                problems.append(
                    f"test item {iid} feature {feature} disagrees with manifest {photo.feature}"
                )
        per_feature[(str(feature), str(gold))] += 1
    for feature in FEATURES:
        for gold in ("present", "absent"):
            n = per_feature[(feature, gold)]
            if n != ITEMS_PER_FEATURE // 2:
                problems.append(f"test set needs 2 {gold} items for {feature}, has {n}")


def load_content(root: Path | str = ".", *, strict: bool = True) -> Content:
    root = Path(root).resolve()
    problems: list[str] = []
    c = root / "content"
    features = _yaml(c / "features.yaml").get("features", [])
    form = _yaml(c / "form.yaml")
    test_items = _yaml(c / "test_items.yaml").get("items", [])
    followups = _yaml(c / "followups.yaml")
    sentences = _yaml(c / "approved_sentences.yaml").get("sentences", [])
    locale = json.loads((c / "locales" / "en.json").read_text(encoding="utf-8"))
    glossary = _yaml(c / "glossary.yaml").get("terms", [])
    regions = {p.stem: _yaml(p) for p in sorted((c / "regions").glob("*.yaml"))}
    lessons = {p.stem: _yaml(p) for p in sorted((c / "lessons").glob("*.yaml"))}
    photos = _load_manifest(root, problems)

    feature_ids = [f.get("id") for f in features]
    if sorted(feature_ids) != sorted(FEATURES):
        problems.append(f"features.yaml ids {feature_ids} must be exactly {list(FEATURES)}")
    for f in features:
        if not f.get("question"):
            problems.append(f"feature {f.get('id')} has no test question")
        if "verified_against_app" not in f:
            problems.append(f"feature {f.get('id')} lacks verified_against_app")
    for fid in FEATURES:
        if fid not in lessons:
            problems.append(f"no lesson file for {fid}")
    item_ids = [i.get("id") for i in form.get("items", [])]
    dup = [k for k, n in Counter(item_ids).items() if n > 1]
    if dup:
        problems.append(f"duplicate form item ids: {dup}")
    for item in form.get("items", []):
        if "verified_against_app" not in item:
            problems.append(f"form item {item.get('id')} lacks verified_against_app")
    for rule in followups.get("rules", []):
        for ref in rule.get("needs_items", []):
            if ref not in item_ids:
                problems.append(f"followup rule {rule.get('id')} needs unknown item {ref}")
    if int(followups.get("max_questions", 2)) != 2:
        problems.append("followups.yaml max_questions must be 2")
    for s in sentences:
        for key in ("id", "audience", "text", "source", "approved"):
            if key not in s:
                problems.append(f"sentence {s.get('id')} lacks {key}")
    try:
        creeks_from_regions(regions)
    except RegionError as exc:
        problems.append(str(exc))
    _check_disjoint(photos, problems)
    _check_test_items(test_items, photos, problems)

    content = Content(
        root=root,
        features=features,
        form=form,
        test_items=test_items,
        followups=followups,
        sentences=sentences,
        locale=locale,
        glossary=glossary,
        regions=regions,
        lessons=lessons,
        photos=photos,
        problems=problems,
    )
    if strict and problems:
        raise ContentError("\n".join(problems))
    return content


def placeholder_report(content: Content) -> list[str]:
    """Human inputs still missing. Preflight prints these and fails."""
    out: list[str] = []
    for p in content.photos.values():
        if p.is_placeholder and p.role in {"test", "lesson", "practice", "warmup"}:
            out.append(f"placeholder photo in role {p.role}: {p.id}")
        if p.role == "test" and not p.labeller_2:
            out.append(f"no second label for test photo {p.id}")
    for f in content.features:
        if not f.get("verified_against_app") and f.get("app_item"):
            out.append(f"feature {f['id']} question not verified against the app")
        if f.get("wording_status") != "frozen":
            out.append(f"feature {f['id']} question wording not frozen")
    for item in content.form.get("items", []):
        if not item.get("verified_against_app"):
            out.append(f"form item {item['id']} not verified against the app")
    for fid, lesson in content.lessons.items():
        if not lesson.get("approved"):
            out.append(f"lesson {fid} not approved")
    for s in content.sentences:
        if not s.get("approved"):
            out.append(f"sentence {s['id']} not approved")
    return out
