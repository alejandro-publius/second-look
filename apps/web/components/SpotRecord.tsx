"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { FhirView } from "./FhirView";
import { FocusHeading } from "./FocusHeading";
import { api, type SpotRecordOut, type VisitOut } from "@/lib/api";
import { featureById } from "@/lib/content";
import { t } from "@/lib/t";

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
  const place = [spot.reach_name, spot.creek_name].filter(Boolean).join(", ");

  return (
    <div className="stack">
      <FocusHeading>{title}</FocusHeading>
      {place ? <p className="muted">{place}</p> : null}
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
                  {t("spot.rating_first")}: {v.first_rating ?? t("spot.none")}. {t("spot.rating_final")}: {v.final_rating ?? t("spot.none")}.
                </p>
              ) : null}
              {answers.length === 0 ? <p className="small muted">{t("spot.no_passed_answers")}</p> : null}
              <div>
                {answers.map((a) => (
                  <div key={a.item_id} className="answer-line">
                    <span>
                      <span className="small muted">{a.text}</span>
                      <br />
                      <strong>{valueText(a)}</strong>
                    </span>
                    <span className="observer">
                      {a.observer_label ?? (a.feature ? t("spot.no_score", { feature: featureById(a.feature)?.name ?? a.feature }) : t("spot.no_feature"))}
                    </span>
                  </div>
                ))}
              </div>
              {v.checks.length > 0 ? (
                <div className="stack">
                  <h3>{t("spot.checks")}</h3>
                  <ul>
                    {v.checks.map((c) => (
                      <li key={c.rule_id} className="small">
                        <strong>{c.rule_id}</strong>: {c.asked ? t("spot.check_asked") : t("spot.check_not_asked")}
                        {c.question_text ? ` ${c.question_text}` : ""}
                        {c.answer ? ` ${t("spot.check_answer", { answer: c.answer })}` : ""}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </li>
          );
        })}
      </ol>

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
