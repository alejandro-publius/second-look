"use client";

import { FocusHeading } from "@/components/FocusHeading";
import { SpotRecord } from "@/components/SpotRecord";
import { useQueryParamOrNull } from "@/components/QueryParam";
import { WalkStoredRecord } from "@/components/WalkRecord";
import { t } from "@/lib/t";

// /spot?id=<spot id>. A query route, not a path route, because Cloudflare Pages serves a static
// export and a spot id is not known at build time. The record is fetched only once the id has been
// read, and a link with no id says so rather than asking for an empty one (REVIEW_03 R43).
export default function SpotPage() {
  const id = useQueryParamOrNull("id");
  if (id === null) {
    return (
      <p role="status" className="muted">
        {t("spot.loading")}
      </p>
    );
  }
  if (id === "") {
    return (
      <div className="stack">
        <FocusHeading>{t("spot.title")}</FocusHeading>
        <p className="notice notice-warn">{t("spot.no_id")}</p>
      </div>
    );
  }
  // A finished video walk's stored demo record (UPDATE_30 section 1 item 3). Its id starts with
  // "walk-", which no creek spot's id can (core/walks.py), and it is read from its own route.
  if (id.startsWith("walk-")) return <WalkStoredRecord recordId={id} />;
  return <SpotRecord spotId={id} />;
}
