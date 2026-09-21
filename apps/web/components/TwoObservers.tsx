"use client";

import { useEffect, useState } from "react";
import { FocusHeading } from "./FocusHeading";
import { RecordCard } from "./RecordCard";
import { api, type TwoOut } from "@/lib/api";
import { t } from "@/lib/t";

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

  return (
    <div className="stack">
      <FocusHeading>{t("two.title")}</FocusHeading>
      <p>{t("two.intro")}</p>
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
            <p className="small muted">{t("two.cached", { when: data.fetched_at })}</p>
          ) : null}
          {data.theirs ? <RecordCard observation={data.theirs} heading={t("two.theirs")} /> : null}
          <RecordCard observation={data.ours} heading={t("two.ours")} />
        </>
      ) : null}
    </div>
  );
}
