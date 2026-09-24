"""The Library entry: one FHIR resource that describes our data set and points at the repository.

OneAquaHealth registers each data set in their sandbox as a Library under their LibraryOah
profile, with a size, a record count and a content list. That is their FAIR pattern: the data is
findable through the Library, and the Library says where the rest lives. Ours does the same for
the citizen creek checks: it names the repository, the read only FHIR endpoint, one worked visit,
and every Provenance we have mirrored to their sandbox, so a reader who finds the Library can walk
from it to a record and from the record to the score of the person who made it.

Pure. No file or network I/O. The caller passes the date and the ids.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any

from core.fhir_emit import FHIR_BASE, REPO_URL, _identifier, _narrative

OAH_LIBRARY_PROFILE = "http://hl7.eu/fhir/ig/oah/StructureDefinition/library-oah"
EXT_SIZE = "http://hl7.eu/fhir/ig/oah/StructureDefinition/library-size"
EXT_RECORDS = "http://hl7.eu/fhir/ig/oah/StructureDefinition/library-numberOfRecords"
LIBRARY_TYPE_SYSTEM = "http://terminology.hl7.org/CodeSystem/library-type"
LIBRARY_ID = "second-look-citizen-creek-checks"
LIBRARY_URL = f"{FHIR_BASE}/Library/{LIBRARY_ID}"
ID_SYSTEM_LIBRARY = f"{FHIR_BASE}/library-id"
FHIR_JSON = "application/fhir+json"
GOLDEN_VISIT_URL = f"{REPO_URL}/blob/main/fhir/golden/visit-strawberry-creek-1.json"
API_BUNDLE_URL = "https://second-look-api.thealexschroeder.workers.dev/api/fhir/Bundle"


def library_entry(
    *,
    today: date,
    n_records: int,
    provenance_refs: Sequence[str] = (),
    version: str | None = None,
) -> dict[str, Any]:
    """The Library resource. `provenance_refs` are the sandbox's own ids of our mirrored
    Provenances, as "Provenance/123", so the content list points at records on the same server.
    `n_records` is the number of visits mirrored, which is the number of Provenances."""
    if n_records < 0:
        raise ValueError("n_records cannot be negative")
    content: list[dict[str, Any]] = [
        {
            "contentType": "text/html",
            "url": REPO_URL,
            "title": "The repository: code, FSH, the emitter and every test",
        },
        {
            "contentType": FHIR_JSON,
            "url": GOLDEN_VISIT_URL,
            "title": "One worked visit at Strawberry Creek as a collection Bundle",
        },
        {
            "contentType": FHIR_JSON,
            "url": API_BUNDLE_URL,
            "title": "Read only endpoint: one Bundle per visit, by visit id",
        },
    ]
    for ref in provenance_refs:
        content.append(
            {
                "contentType": FHIR_JSON,
                "url": ref,
                "title": "Provenance of one mirrored visit on this server",
            }
        )
    # Berkeley has not adopted the method: the project runs it there the way a follower city
    # would (critic round 01, C04). The worked visit it mirrors is made by hand, and says so.
    example = (
        " The worked visit at Strawberry Creek among them is a hand-made example."
        if n_records
        else ""
    )
    words = (
        f"Second Look data set: creek checks from Berkeley, run the way a follower city would, "
        f"with the observer's per feature test score carried on every observation. {n_records} "
        f"visit records mirrored to this server.{example} The repository holds the code, the FSH "
        f"and the tests."
    )
    return {
        "resourceType": "Library",
        "id": LIBRARY_ID,
        "meta": {"profile": [OAH_LIBRARY_PROFILE]},
        "text": _narrative(words),
        "extension": [
            {"url": EXT_SIZE, "valueQuantity": {"value": n_records, "unit": "visit records"}},
            {"url": EXT_RECORDS, "valueInteger": n_records},
        ],
        "url": LIBRARY_URL,
        "identifier": [_identifier(ID_SYSTEM_LIBRARY, LIBRARY_ID)],
        "version": version or f"{today:%Y.%m}",
        "name": "SecondLookCitizenCreekChecks",
        "title": "Second Look: citizen creek checks with observer scores, Berkeley",
        "status": "active",
        "type": {
            "coding": [
                {
                    "system": LIBRARY_TYPE_SYSTEM,
                    "code": "asset-collection",
                    "display": "Asset Collection",
                }
            ]
        },
        "date": today.isoformat(),
        "publisher": "Second Look project",
        "author": [{"name": "Second Look project, Berkeley"}],
        "description": words,
        "copyright": "Code MIT. Photos and copy CC BY 4.0. No personal data: observers are "
        "known only by a hash of a random token.",
        "content": content,
    }


def check_library(library: dict[str, Any]) -> list[str]:
    """What their profile asks for, checked here so a broken entry never reaches the sandbox."""
    problems: list[str] = []
    if library.get("resourceType") != "Library":
        return ["not a Library"]
    for field in ("url", "title", "status", "type", "date"):
        if not library.get(field):
            problems.append(f"missing {field}")
    if OAH_LIBRARY_PROFILE not in library.get("meta", {}).get("profile", []):
        problems.append("not under their LibraryOah profile")
    urls = {e.get("url") for e in library.get("extension", [])}
    if EXT_SIZE not in urls or EXT_RECORDS not in urls:
        problems.append("missing the size or numberOfRecords extension")
    if not any(c.get("url") == REPO_URL for c in library.get("content", [])):
        problems.append("does not point at the repository")
    return problems
