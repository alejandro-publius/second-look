"""ACT: turning a creek's record into what the creek needs, and which pipes are worth testing.

Pure. No file or network I/O, no database, no model call. Everything here is a function of the
visits that were already stored, so a number on /city can always be traced back to the
Observations behind it.

Three rules this module exists to keep:

1. Every number carries its evidence. A Need and a PipeCase both hold the visit ids and the
   observer tokens they were counted from, so /city can show the resources behind a figure and
   scripts/verify_claims.py can check one.
2. No sentence is invented. A measure is only ever text from content/approved_sentences.yaml
   with approved true, so hard rule 5 holds by construction: if nobody has approved a sentence,
   /city says nothing rather than saying something we made up.
3. Nothing states a risk for a specific site. A measure says what to do to a stream, never what
   the water will do to a person who visits this one.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from datetime import date

from pydantic import Field

from core.labels import HUMAN_PASS_MIN
from core.records import FEATURES, Frozen, Spot, VisitRecord
from core.regions import Creek, Reach, reaches_below

# The four measures OneAquaHealth's own decision tool returns, and which finding points at each.
# Source for every sentence is in content/approved_sentences.yaml; this only says which finding
# asks for which, and the mapping is the project's own, from the Policy Brief page 9.
#
# A key here is a finding key, not always one of the four tested features. Three of them are
# tested features and `barriers` is a creek check form item, because a barrier is something a
# person reports on the form and nobody is scored on. invasive_plant is deliberately absent: the
# decision tool's four measures do not include one for it, and inventing a fifth is not ours.
MEASURE_FOR_FEATURE: dict[str, tuple[str, ...]] = {
    "artificial_bank": ("city_replant_margins", "city_remove_concrete"),
    "pipe_running": ("city_fix_sewers",),
    "dug_out_channel": ("city_reconnect_floodplain",),
    "barriers": ("city_remove_barriers",),
}

# What a finding can be about: every tested feature, plants included, and every form item a
# measure asks for. Only the measures read MEASURE_FOR_FEATURE, so a plant is still something
# people reported, and it simply asks the city for nothing (review CRITIC_06 H01).
FINDING_KEYS: frozenset[str] = frozenset(FEATURES) | frozenset(MEASURE_FOR_FEATURE)

DRY_PIPE_RULE = "dry_pipe"
# Two different people, so one person cannot put a pipe on the list on their own.
PIPE_OBSERVERS_NEEDED = 2
# A new pin this close to an existing spot is almost certainly the same spot.
SAME_SPOT_METRES = 30.0
EARTH_RADIUS_M = 6_371_000.0

# Names that read like someone testing the form rather than a place. Kept out of /city and
# flagged for a person to look at, never deleted: deleting someone's visit is not ours to do.
TEST_NAME_WORDS = frozenset(
    {
        "test",
        "testing",
        "asdf",
        "qwerty",
        "foo",
        "bar",
        "baz",
        "demo",
        "example",
        "sample",
        "xxx",
        "delete",
        "ignore",
        "dummy",
        "placeholder",
        "todo",
        "abc",
    }
)


class Finding(Frozen):
    """One feature reported present at one spot, with everything it was counted from."""

    spot_id: str
    # A finding key: one of the four tested features, or a form item such as `barriers`.
    feature: str
    observers: tuple[str, ...]
    visit_ids: tuple[str, ...]
    first_seen: date
    last_seen: date
    # The observers above who held a passing, unexpired score for this feature on the day they
    # last reported it. A form item nobody is tested on has none.
    passed_observers: tuple[str, ...] = ()

    @property
    def n_observers(self) -> int:
        return len(self.observers)

    @property
    def n_passed(self) -> int:
        return len(self.passed_observers)


class Need(Frozen):
    """One measure this creek needs, and the findings that asked for it."""

    sentence_id: str
    text: str
    source: str
    because: tuple[str, ...]
    visit_ids: tuple[str, ...]


class PipeCase(Frozen):
    """A pipe worth testing: reported running in dry weather by two people who both passed."""

    spot_id: str
    spot_name: str
    observers: tuple[str, ...]
    visit_ids: tuple[str, ...]
    dry_days: tuple[int, ...]
    last_seen: date


def _present(value: object) -> bool:
    """Our answers say present or absent; a yes is the same thing from the quick check.

    A list, such as which plants, is never present on its own: the yes to the question before it
    already says so. Checked first, because a list cannot be looked up in a set.
    """
    if isinstance(value, list | dict):
        return False
    return value in {"present", "yes", True}


def findings_from_visits(
    visits: Iterable[VisitRecord], finding_key_for: Mapping[str, str] | None = None
) -> list[Finding]:
    """Every feature reported present at each spot, with its observers and visit ids.

    A person who visits twice counts once: the list is of people, not of visits.

    A stored answer is keyed by the creek check form item, `bank_type`, not by the feature,
    `artificial_bank`. `finding_key_for` maps one to the other and comes from content/form.yaml,
    so the mapping has one home. Without it the answer keys are taken as finding keys, which is
    what the pure tests do.
    """
    lookup = dict(finding_key_for or {})
    seen: dict[tuple[str, str], dict[str, object]] = {}
    for v in visits:
        for answer_key, value in v.answers.items():
            feature = lookup.get(answer_key, answer_key)
            if feature not in FINDING_KEYS or not _present(value):
                continue
            key = (v.spot.spot_id, feature)
            day = v.answered_at.date()
            row = seen.setdefault(
                key,
                {"observers": [], "passed": [], "visits": [], "first": day, "last": day},
            )
            token = v.observer.contributor_token
            observers = row["observers"]
            assert isinstance(observers, list)
            if token not in observers:
                observers.append(token)
            passed = row["passed"]
            assert isinstance(passed, list)
            if token not in passed and _passed_feature(v, feature, day):
                passed.append(token)
            visit_ids = row["visits"]
            assert isinstance(visit_ids, list)
            # Two form items can name one feature (both pipe items are pipe_running), and one
            # visit that answers both is still one visit (review REVIEW_03 R32, REVIEW_02 F82).
            if v.visit_id not in visit_ids:
                visit_ids.append(v.visit_id)
            first, last = row["first"], row["last"]
            assert isinstance(first, date) and isinstance(last, date)
            row["first"] = min(first, day)
            row["last"] = max(last, day)
    out: list[Finding] = []
    for (spot_id, feature), row in sorted(seen.items()):
        out.append(
            Finding(
                spot_id=spot_id,
                feature=feature,
                observers=tuple(row["observers"]),  # type: ignore[arg-type]
                visit_ids=tuple(row["visits"]),  # type: ignore[arg-type]
                first_seen=row["first"],  # type: ignore[arg-type]
                last_seen=row["last"],  # type: ignore[arg-type]
                passed_observers=tuple(row["passed"]),  # type: ignore[arg-type]
            )
        )
    return out


def needs_from_findings(
    findings: Sequence[Finding], sentences: Iterable[Mapping[str, object]]
) -> list[Need]:
    """What this creek needs, in approved words only.

    An unapproved sentence is simply absent. That is the honest failure: a city sees nothing
    rather than a sentence nobody checked against a source.
    """
    approved = {
        str(s["id"]): s
        for s in sentences
        if s.get("approved") is True and s.get("audience") == "city"
    }
    wanted: dict[str, dict[str, list[str]]] = {}
    for f in findings:
        for sentence_id in MEASURE_FOR_FEATURE.get(f.feature, ()):
            if sentence_id not in approved:
                continue
            row = wanted.setdefault(sentence_id, {"because": [], "visits": []})
            if f.feature not in row["because"]:
                row["because"].append(f.feature)
            row["visits"].extend(f.visit_ids)
    out: list[Need] = []
    for sentence_id, row in sorted(wanted.items()):
        s = approved[sentence_id]
        out.append(
            Need(
                sentence_id=sentence_id,
                text=str(s.get("text", "")),
                source=str(s.get("source", "")),
                because=tuple(row["because"]),
                visit_ids=tuple(dict.fromkeys(row["visits"])),
            )
        )
    return out


def _passed_feature(v: VisitRecord, feature: str, today: date) -> bool:
    """A passing, unexpired score for this feature. A form item nobody is tested on never passes."""
    if feature not in FEATURES:
        return False
    score = v.observer.score_for(feature)
    if score is None or score.expired_on(today):
        return False
    return score.correct >= HUMAN_PASS_MIN


def _passed_pipe(v: VisitRecord, today: date) -> bool:
    return _passed_feature(v, "pipe_running", today)


def _dry_pipe_days(v: VisitRecord) -> int | None:
    """The dry day count if this visit confirmed a pipe running after dry weather."""
    for c in v.checks:
        if c.rule_id != DRY_PIPE_RULE or not c.asked or c.answer != "yes":
            continue
        days = c.detail.get("days")
        if isinstance(days, int) and days >= 1:
            return days
    return None


def pipes_worth_testing(visits: Iterable[VisitRecord], today: date) -> list[PipeCase]:
    """A pipe two different people saw running in dry weather, both of whom passed that feature.

    Two people, because one person can be wrong. Both passed, because a person who cannot tell a
    pipe from a shadow should not be able to send a city out with a sample bottle.
    """
    by_spot: dict[str, dict[str, object]] = {}
    for v in visits:
        days = _dry_pipe_days(v)
        if days is None or not _passed_pipe(v, today):
            continue
        row = by_spot.setdefault(
            v.spot.spot_id,
            {
                "name": v.spot.spot_name,
                "observers": [],
                "visits": [],
                "days": [],
                "last": v.answered_at.date(),
            },
        )
        observers = row["observers"]
        assert isinstance(observers, list)
        if v.observer.contributor_token not in observers:
            observers.append(v.observer.contributor_token)
        for key, value in (("visits", v.visit_id), ("days", days)):
            bucket = row[key]
            assert isinstance(bucket, list)
            bucket.append(value)
        last = row["last"]
        assert isinstance(last, date)
        row["last"] = max(last, v.answered_at.date())
    out: list[PipeCase] = []
    for spot_id, row in sorted(by_spot.items()):
        observers = row["observers"]
        assert isinstance(observers, list)
        if len(observers) < PIPE_OBSERVERS_NEEDED:
            continue
        out.append(
            PipeCase(
                spot_id=spot_id,
                spot_name=str(row["name"]),
                observers=tuple(observers),
                visit_ids=tuple(row["visits"]),  # type: ignore[arg-type]
                dry_days=tuple(row["days"]),  # type: ignore[arg-type]
                last_seen=row["last"],  # type: ignore[arg-type]
            )
        )
    return out


def metres_between(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great circle distance in metres. Good to a metre at the scale of one creek."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


class NearbySpot(Frozen):
    spot: Spot
    metres: float = Field(ge=0)


def nearest_spot(
    latitude: float, longitude: float, spots: Iterable[Spot], within: float = SAME_SPOT_METRES
) -> NearbySpot | None:
    """The closest existing spot within `within` metres, so a new pin can offer it first.

    A person dropping a pin near a spot that already exists almost always means the same place.
    Offering the existing one is kinder than asking them to notice, and it keeps the map honest.
    """
    best: NearbySpot | None = None
    for s in spots:
        if s.latitude is None or s.longitude is None:
            continue
        d = metres_between(latitude, longitude, s.latitude, s.longitude)
        if d <= within and (best is None or d < best.metres):
            best = NearbySpot(spot=s, metres=d)
    return best


def looks_like_a_test_name(name: str) -> bool:
    """True when a spot name reads like someone trying the form out.

    Flagged for a person to look at and kept out of /city. Never deleted: a real place called
    Test Creek would be wrong to throw away, and a person can clear the flag.
    """
    cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in name.lower())
    words = cleaned.split()
    if not words:
        return True
    if any(w in TEST_NAME_WORDS for w in words):
        return True
    # A name with no letters at all, like "123" or "...", is not a place name.
    return not any(ch.isalpha() for ch in name)


def downstream_note(
    finding: Finding, feature_name: str, reaches_below: Sequence[str]
) -> dict[str, str]:
    """One plain line for each reach below a finding. Our store knows what flows into what.

    It says who reported and when, and nothing about what the water will do to anybody.
    """
    people = "one person" if finding.n_observers == 1 else f"{finding.n_observers} people"
    when = f"{finding.last_seen:%b %-d}"
    line = f"Upstream of here, {people} reported {feature_name} on {when}."
    return {reach: line for reach in reaches_below}


class DownstreamNote(Frozen):
    """One plain line on one reach below a finding, with the visits it was counted from."""

    reach_slug: str
    reach_name: str
    from_reach_slug: str
    from_reach_name: str
    feature: str
    line: str
    observers: int
    visit_ids: tuple[str, ...]


def notes_below(
    findings: Sequence[Finding],
    reach_of: Mapping[str, Reach | None],
    creek: Creek,
    labels: Mapping[str, str],
) -> list[DownstreamNote]:
    """The downstream note for every reach below every finding on this creek.

    `reach_of` says which reach a spot sits on, or None when the reach is unknown (a coarse pin).
    A finding on an unknown reach gives no note, and a reach with no `flows_into` gives none
    either: the note appears only where the store knows what flows into what (Update 10B).
    `labels` gives the plain words for a finding key, such as "built banks".
    """
    out: list[DownstreamNote] = []
    for f in findings:
        reach = reach_of.get(f.spot_id)
        if reach is None or reach.creek_slug != creek.slug:
            continue
        below = reaches_below(reach, creek)
        if not below:
            continue
        label = labels.get(f.feature, f.feature.replace("_", " "))
        lines = downstream_note(f, label, [r.slug for r in below])
        for r in below:
            out.append(
                DownstreamNote(
                    reach_slug=r.slug,
                    reach_name=r.name,
                    from_reach_slug=reach.slug,
                    from_reach_name=reach.name,
                    feature=f.feature,
                    line=lines[r.slug],
                    observers=f.n_observers,
                    visit_ids=f.visit_ids,
                )
            )
    return out
