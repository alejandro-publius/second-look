"use client";

import { useEffect, useState } from "react";
import { FocusHeading } from "./FocusHeading";
import { Icon } from "./ui/Icon";
import { Row } from "./ui/Row";
import { Skeleton } from "./ui/Skeleton";
import { api, type CityOut } from "@/lib/api";
import { t } from "@/lib/t";

/**
 * What a city analyst sees. Two lists decided by code, and never a number without the records
 * behind it: every figure here carries a link to the FHIR Bundles it was counted from.
 *
 * An empty "what this creek needs" is said out loud rather than left blank, because no measure
 * and no approved sentence look identical from the outside and mean very different things.
 */
export function CityView({ creekId }: { creekId: string }) {
  const [view, setView] = useState<CityOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!creekId) return;
    let live = true;
    api
      .city(creekId)
      .then((v) => live && setView(v))
      .catch(() => live && setError(t("error.network")));
    return () => {
      live = false;
    };
  }, [creekId]);

  if (!creekId || error) {
    return (
      <div className="notice notice-warn" role="status">
        <Icon name="info" />
        <p>{error ?? t("city.none")}</p>
      </div>
    );
  }
  if (!view) return <Skeleton label={t("city.title")} lines={3} photo={false} />;

  const people = (n: number) => (n === 1 ? t("city.observer_one") : t("city.observers", { n }));
  const evidence = (links: string[]) => (
    <a href={links[0]} rel="noreferrer">
      {t("city.evidence")}
    </a>
  );

  return (
    <div className="stack">
      <FocusHeading>{t("city.title")}</FocusHeading>
      <p>{t("city.intro", { creek: view.creek_name })}</p>
      <p className="small muted tabular">{t("city.visits", { n: view.visits, spots: view.spots })}</p>

      <h2>{t("city.needs_title")}</h2>
      {view.needs.length === 0 ? (
        <div className="notice notice-warn">
          <Icon name="info" />
          <p>{t("city.needs_waiting")}</p>
        </div>
      ) : (
        <div className="card">
          {view.needs.map((n) => (
            <Row
              key={n.sentence_id}
              label={n.text}
              value={`${n.because.join(", ")}. ${n.source}`}
              end={evidence(n.fhir)}
            />
          ))}
        </div>
      )}

      <h2>{t("city.pipes_title")}</h2>
      <p className="small muted">{t("city.pipes_note")}</p>
      {view.pipes_worth_testing.length === 0 ? (
        <p className="muted">{t("city.pipes_none")}</p>
      ) : (
        <div className="card">
          {view.pipes_worth_testing.map((p) => (
            <Row
              key={p.spot_id}
              label={p.spot_name}
              value={`${people(p.observers)}, ${t("city.dry_days", { days: Math.max(...p.dry_days) })}`}
              end={evidence(p.fhir)}
            />
          ))}
        </div>
      )}

      <h2>{t("city.findings_title")}</h2>
      {view.findings.length === 0 ? (
        <p className="muted">{t("city.none")}</p>
      ) : (
        <div className="card">
          {view.findings.map((f) => (
            <Row
              key={`${f.spot_id}:${f.feature}`}
              label={`${f.feature_name}, ${f.spot_name}`}
              value={people(f.observers)}
              end={evidence(f.fhir)}
            />
          ))}
        </div>
      )}

      {view.flagged_spots.length > 0 ? (
        <>
          <h2>{t("city.flagged_title")}</h2>
          <p className="small muted">{t("city.flagged_note")}</p>
          <div className="card">
            {view.flagged_spots.map((s) => (
              <Row key={s.spot_id} label={s.spot_name} value={s.why} />
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}
