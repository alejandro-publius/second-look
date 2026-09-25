"""Write the content the API Worker needs into worker/src/content.json.

The gold key lives here. It never reaches the browser: apps/web/scripts/build-content.mjs strips
it, and this file is bundled into the Worker only. One source, content/, two consumers.

Update 10 answer A3 widened it: the Worker's TypeScript ports of core/ read their tables from
here rather than carrying copies, so the form items, the follow-up table, the code system
displays, the approved sentences, the creeks of the region packs and the locale strings the
ports need all come from the same files Python reads. What Python wrote, TypeScript reads.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apps.api import content
from core.act import MEASURE_FOR_FEATURE, PIPE_OBSERVERS_NEEDED, SAME_SPOT_METRES, TEST_NAME_WORDS
from core.fhir_emit import (
    OAH_DISPLAYS,
    OAH_LOCATION_PROFILE,
    OAH_OBSERVATION_PROFILE,
    OAH_SYSTEM,
    REPO_URL,
    SL_DISPLAYS,
    SL_SYSTEM,
    UCUM_DISPLAYS,
)
from core.followups import LOW_SCORE_MAX_CORRECT, PIPE_ITEMS, RATING_ISSUE_ITEMS
from core.labels import HUMAN_PASS_MIN
from core.records import FEATURES, ITEMS_PER_FEATURE, SCORE_VALID_DAYS
from core.regions import creeks_from_regions

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "worker" / "src" / "content.json"
# What the pure ports in worker/src/core read, and nothing else. The web app imports those ports
# for the video walks, so this file ships to browsers: it must never hold the gold key.
CORE_OUT = ROOT / "worker" / "src" / "core" / "core_content.json"
CORE_KEYS = ("creeks", "fhir", "followups", "form_items", "rules", "sentences")


def core_doc(doc: dict[str, Any]) -> dict[str, Any]:
    core = {k: doc[k] for k in CORE_KEYS}
    text = json.dumps(core)
    if '"gold"' in text or "test_items" in text:
        raise SystemExit("build-worker-content: the gold key would reach core_content.json")
    return core


# The locale strings the ports fill: follow-up questions, labels and the yes/no words.
LOCALE_PREFIXES = ("followup.", "label.", "test.yes", "test.no", "test.cant_tell", "error.")


def build() -> dict[str, Any]:
    loaded = content.get_content()
    items = [
        {"id": item["id"], "feature": item["feature"], "gold": item["gold"]}
        for item in loaded.test_items
    ]
    creeks = [
        {
            "slug": c.slug,
            "name": c.name,
            "source": c.source,
            "reaches": [
                {
                    "slug": r.slug,
                    "name": r.name,
                    "flows_into": r.flows_into,
                    "bbox": list(r.bbox) if r.bbox else None,
                }
                for r in c.reaches
            ],
        }
        for c in creeks_from_regions(loaded.regions)
    ]
    return {
        "content_hash": loaded.content_hash(),
        "features": sorted({item["feature"] for item in items}),
        "test_items": items,
        "warmup_ids": sorted(content.warmup_ids()),
        # Update 10 answer A3: the tables the TypeScript ports read.
        "feature_list": [
            {
                "id": f["id"],
                "name": f.get("name", f["id"]),
                "plain": f.get("plain", ""),
                "question": f.get("question", ""),
            }
            for f in loaded.features
        ],
        "form_items": [dict(item) for item in loaded.form.get("items", [])],
        "followups": loaded.followups,
        "sentences": list(loaded.sentences),
        "locale": {k: v for k, v in loaded.locale.items() if k.startswith(LOCALE_PREFIXES)},
        "creeks": creeks,
        "region_plants": sorted(content.region_plant_names()),
        # The walks a finished walk may name when the phone stores its record (UPDATE_30 section
        # 1 item 3): the id and the two names the record carries, nothing about the clip.
        "walks": [dict(w) for w in content.walks()],
        # The validator verdict is not copied here: worker/src/index.ts imports
        # results/fhir_validation.json itself, so there is one file and no stale copy.
        "fhir": {
            "repo_url": REPO_URL,
            "sl_system": SL_SYSTEM,
            "oah_system": OAH_SYSTEM,
            "oah_location_profile": OAH_LOCATION_PROFILE,
            "oah_observation_profile": OAH_OBSERVATION_PROFILE,
            "sl_displays": SL_DISPLAYS,
            "oah_displays": OAH_DISPLAYS,
            "ucum_displays": UCUM_DISPLAYS,
        },
        "rules": {
            "features_in_order": list(FEATURES),
            "items_per_feature": ITEMS_PER_FEATURE,
            "score_valid_days": SCORE_VALID_DAYS,
            "human_pass_min": HUMAN_PASS_MIN,
            "pipe_observers_needed": PIPE_OBSERVERS_NEEDED,
            "same_spot_metres": SAME_SPOT_METRES,
            "test_name_words": sorted(TEST_NAME_WORDS),
            "measure_for_feature": {k: list(v) for k, v in MEASURE_FOR_FEATURE.items()},
            "pipe_items": list(PIPE_ITEMS),
            "rating_issue_items": list(RATING_ISSUE_ITEMS),
            "low_score_max_correct": LOW_SCORE_MAX_CORRECT,
        },
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="fail if the committed file is stale")
    args = parser.parse_args(argv)
    doc = build()
    text = json.dumps(doc, indent=2, sort_keys=True) + "\n"
    core_text = json.dumps(core_doc(doc), indent=2, sort_keys=True) + "\n"
    if args.check:
        for path, want in ((OUT, text), (CORE_OUT, core_text)):
            if not path.exists() or path.read_text(encoding="utf-8") != want:
                print(f"build-worker-content: {path.relative_to(ROOT)} is stale; run this script")
                return 1
        print("build-worker-content: worker/src/content.json and core_content.json are current")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    CORE_OUT.write_text(core_text, encoding="utf-8")
    print(
        f"build-worker-content: {len(doc['test_items'])} test items, {len(doc['form_items'])} "
        f"form items, {len(doc['creeks'])} creeks into {OUT.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
