"use client";

import { useEffect, useState } from "react";
import { FocusHeading } from "./FocusHeading";
import { RecordCard, observerScore, readableTime, sameReading } from "./RecordCard";
import { api, type TwoOut } from "@/lib/api";
import { t } from "@/lib/t";

/**
 * What the reader should notice, said once under the heading. "Same creek, same answer" is said only
 * when it is true of the two records on screen; the live pair is a lab reading from another place.
 */
function point(data: TwoOut): string | null {
  if (!data.theirs || !observerScore(data.ours) || observerScore(data.theirs)) return null;
  return sameReading(data.theirs, data.ours) ? t("two.point_same") : t("two.point");
}

/** One viewer, two kinds of observer: their lab Observation and our volunteer Observation. */
export function TwoObservers() {
  const [data, setData] = useState<TwoOut | null>(null);
  const [state, setState] = useState<"loading" | "ok" | "down">("loading");

  useEffect(() => {
    api
      .two()
      .then((d) => {
        setData(d);
        setState("ok");
      })
      .catch(() => setState("down"));
  }, []);

  const lead = data ? point(data) : null;

  return (
    <div className="stack">
      <FocusHeading>{t("two.title")}</FocusHeading>
      {lead ? <p>{lead}</p> : null}
      <p>{data?.ours_example ? t("two.intro_example") : t("two.intro")}</p>
      {state === "loading" ? (
        <p role="status" className="muted">
          {t("spot.loading")}
        </p>
      ) : null}
      {state === "down" ? <p className="notice notice-warn">{t("error.network")}</p> : null}
      {data ? (
        <>
          {data.theirs_status === "down" || !data.theirs ? (
            <p className="notice notice-warn" role="status">
              {t("two.down")}
            </p>
          ) : data.theirs_status === "cached" ? (
            <p className="small muted">{t("two.cached", { when: readableTime(data.fetched_at) || data.fetched_at })}</p>
          ) : null}
          {data.theirs ? <RecordCard observation={data.theirs} heading={t("two.theirs")} performer={t("two.performer_theirs")} /> : null}
          {/* With no creek check stored, the API sends the golden visit, which was made by hand,
              and says so: it is labelled here and never passed off as a volunteer's answer. */}
          <RecordCard
            observation={data.ours}
            heading={t("two.ours")}
            performer={t("two.performer_ours")}
            place={data.ours_place}
            note={data.ours_example ? t("two.example") : undefined}
          />
        </>
      ) : null}
    </div>
  );
}
