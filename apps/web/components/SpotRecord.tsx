"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AnswerLine } from "./AnswerLine";
import { FhirView } from "./FhirView";
import { FocusHeading } from "./FocusHeading";
import { InatContext } from "./InatContext";
import { api, type CheckResultOut, type SpotRecordOut, type VisitOut } from "@/lib/api";
import { featureById } from "@/lib/content";
import { has, t } from "@/lib/t";

function when(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function valueText(v: VisitOut["answers"][number]): string {
  if (v.label) return v.label;
  if (Array.isArray(v.value)) return v.value.join(", ");
  if (typeof v.value === "object" && v.value !== null) return Object.entries(v.value).map(([k, x]) => `${k}: ${String(x)}`).join(", ");
  return String(v.value);
}

/** A check's title from the locale. The rule id is a code name and is never shown. */
function checkTitle(ruleId: string): string {
  const key = `spot.rule_${ruleId}`;
  return has(key) ? t(key) : t("spot.rule_other");
}

/** A stored rating (good, moderate, poor) as the word a person reads. */
function ratingWord(value: string | null): string | null {
  if (!value) return null;
  const key = `spot.rating_word_${value}`;
  return has(key) ? t(key) : value;
}

// The follow-up answers the API accepts, each written as a sentence.
const OUTCOME_KEYS = new Map([
  ["yes", "spot.outcome_yes"],
  ["no", "spot.outcome_no"],
  ["cant_tell", "spot.outcome_cant_tell"],
  ["skipped", "spot.outcome_skipped"],
]);
// The rating check answers. The servers store "change" and always refused "changed", which the
// check page sent until 2026-09-23; "changed" stays here only so an old mock record reads right.
const RATING_ANSWERS = new Set(["keep", "change", "changed"]);

/** What the person did with a check, in words. The rating check reads the visit's two ratings. */
function checkOutcome(c: CheckResultOut, v: VisitOut): string {
  if (!c.asked) return t("spot.check_not_asked");
  const answer = c.answer ?? null;
  if (!answer) return t("spot.outcome_none");
  if (RATING_ANSWERS.has(answer)) {
    const from = ratingWord(v.first_rating);
    const to = ratingWord(v.final_rating);
    if (from && to && v.first_rating !== v.final_rating) return t("spot.outcome_changed", { from, to });
    const kept = to ?? from;
    if (answer === "keep" || (from && to)) return kept ? t("spot.outcome_kept", { rating: kept }) : t("spot.outcome_kept_plain");
    return t("spot.outcome_changed_plain");
  }
  const said = OUTCOME_KEYS.get(answer);
  if (said) return t(said);
  // A photo follow-up stores the upload id, which means nothing to a person.
  if (c.rule_id === "low_score" || c.detail?.kind === "photo") return t("spot.outcome_photo");
  return t("spot.check_answer", { answer });
}

/** The creek's record: a timeline of visits, each answer beside the observer's label, the checks, FHIR, the health card. */
export function SpotRecord({ spotId }: { spotId: string }) {
  const [record, setRecord] = useState<SpotRecordOut | null>(null);
  const [state, setState] = useState<"loading" | "ok" | "missing" | "down">("loading");
  const [onlyPassed, setOnlyPassed] = useState(false);

  useEffect(() => {
    let alive = true;
    api
      .spot(spotId)
      .then((r) => {
        if (!alive) return;
        setRecord(r);
        setState("ok");
      })
      .catch((err: { status?: number }) => {
        if (!alive) return;
        setState(err?.status === 404 ? "missing" : "down");
      });
    return () => {
      alive = false;
    };
  }, [spotId]);

  if (state === "loading") {
    return (
      <p role="status" className="muted">
        {t("spot.loading")}
      </p>
    );
  }
  if (state === "missing" || !record) {
    return (
      <div className="stack">
        <FocusHeading>{t("spot.title")}</FocusHeading>
        <p className="notice notice-warn">{state === "down" ? t("error.network") : t("spot.not_found")}</p>
      </div>
    );
  }

  const { spot, visits, health_card } = record;
  const title = spot.spot_name || spotId;
  const placed = record.place ?? null;
  const notes = record.downstream_notes ?? [];
  // The creek this spot sits on, as /city and the iNaturalist route read it.
  const creekKey = placed?.creek_slug ?? spot.creek_id ?? null;
  // The region pack's readable names when the spot sits on a known creek, else the stored ones.
  const place = placed ? [placed.reach_name, placed.creek_name].filter(Boolean).join(", ") : [spot.reach_name, spot.creek_name].filter(Boolean).join(", ");

  return (
    <div className="stack">
      <FocusHeading>{title}</FocusHeading>
      {place ? (
        <p className="muted">
          {place}
          {placed ? (
            <>
              {". "}
              <Link href={`/city?creek=${encodeURIComponent(placed.creek_slug)}`}>{t("spot.city_link")}</Link>
            </>
          ) : null}
        </p>
      ) : null}
      {notes.length > 0 ? (
        <section className="card stack" aria-labelledby="upstream-title">
          <h2 id="upstream-title">{t("spot.upstream_title")}</h2>
          {notes.map((n) => (
            <p key={`${n.from_reach_slug}:${n.feature}`} className="small">
              {n.line}{" "}
              <a href={n.fhir[0]} rel="noreferrer">
                {t("city.evidence")}
              </a>
            </p>
          ))}
        </section>
      ) : null}
      <div className="btn-row">
        <Link className="btn" href={`/quick?spot=${encodeURIComponent(spot.spot_id ?? spotId)}`}>
          {t("spot.quick_link")}
        </Link>
        <Link className="btn btn-secondary" href="/check">
          {t("spot.full_check_link")}
        </Link>
      </div>
      <label className="check">
        <input type="checkbox" checked={onlyPassed} onChange={(e) => setOnlyPassed(e.target.checked)} />
        <span>{t("spot.only_passed")}</span>
      </label>

      <h2>{t("spot.timeline")}</h2>
      {visits.length === 0 ? <p className="muted">{t("spot.empty")}</p> : null}
      <ol className="timeline">
        {visits.map((v) => {
          const answers = onlyPassed ? v.answers.filter((a) => a.observer_passed === true) : v.answers;
          return (
            <li key={v.visit_id}>
              <h3>{when(v.answered_at)}</h3>
              {v.first_rating || v.final_rating ? (
                <p className="small muted">
                  {t("spot.rating_first")}: {ratingWord(v.first_rating) ?? t("spot.none")}. {t("spot.rating_final")}: {ratingWord(v.final_rating) ?? t("spot.none")}.
                </p>
              ) : null}
              {answers.length === 0 ? <p className="small muted">{t("spot.no_passed_answers")}</p> : null}
              <div>
                {answers.map((a) => (
                  <AnswerLine
                    key={a.item_id}
                    text={a.text}
                    value={valueText(a)}
                    score={a.observer_label ?? (a.feature ? t("spot.no_score", { feature: featureById(a.feature)?.name ?? a.feature }) : t("spot.no_feature"))}
                  />
                ))}
              </div>
              {v.checks.length > 0 ? (
                <div className="stack">
                  <h3>{t("spot.checks")}</h3>
                  <ul className="stack">
                    {v.checks.map((c) => (
                      <li key={c.rule_id} className="small">
                        <strong>{checkTitle(c.rule_id)}</strong>
                        {c.asked && c.question_text ? (
                          <>
                            <br />
                            <span className="muted">{c.question_text}</span>
                          </>
                        ) : null}
                        <br />
                        {checkOutcome(c, v)}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </li>
          );
        })}
      </ol>

      {/* Context from iNaturalist, below the answers, never above them. The API sends the
          sightings only once this creek's record answers the invasive plant question. */}
      {creekKey ? <InatContext creek={creekKey} /> : null}

      <FhirView load={() => api.spotFhir(spotId)} curl={`curl -s ${api.spotFhirUrl(spotId)}`} />

      {health_card ? (
        <section className="card stack" aria-labelledby="health-title">
          <h2 id="health-title">{t("spot.health_title")}</h2>
          <p>
            <strong>{t("spot.health_person")}</strong>: {health_card.person}
          </p>
          <p>
            <strong>{t("spot.health_pet")}</strong>: {health_card.pet}
          </p>
          <p>
            <strong>{t("spot.health_city")}</strong>: {health_card.city}
          </p>
          <p className="small muted">
            {t("spot.health_sources")}: {health_card.sources.join("; ")}
          </p>
        </section>
      ) : null}
      <p className="muted">{t("footer.snapshot")}</p>
    </div>
  );
}
