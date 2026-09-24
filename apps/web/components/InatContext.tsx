"use client";

import { useEffect, useState } from "react";
import { api, type InatOut, type InatSpecies } from "@/lib/api";
import { t } from "@/lib/t";

// A date-only string such as "2025-12-11" is a calendar day, not an instant: read it in UTC so a
// phone west of Greenwich does not show the day before.
function day(iso: string): string {
  const d = new Date(`${iso}T00:00:00Z`);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString(undefined, { dateStyle: "medium", timeZone: "UTC" });
}

function when(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function sighting(s: InatSpecies): string {
  const date = day(s.last_observed);
  return s.count === 1 ? t("inat.species_one", { name: s.name, date }) : t("inat.species_many", { name: s.name, n: s.count, date });
}

/**
 * One line of context per creek: plants on the region's invasive list that people saw near the
 * creek's spots on iNaturalist, from the copy scripts/cache_inaturalist.py stored with its fetch
 * time. Only the record page and /city show it. It is never in the guided check, never counted,
 * and never decides anything. The API withholds the sightings until the creek's record answers
 * the invasive plant question, and until then this shows nothing at all. If the route fails, it
 * shows nothing too: without the answer it cannot know the line may be shown.
 */
export function InatContext({ creek }: { creek: string }) {
  const [out, setOut] = useState<InatOut | null>(null);

  useEffect(() => {
    let live = true;
    api
      .inaturalist(creek)
      .then((r) => live && setOut(r))
      .catch(() => live && setOut(null));
    return () => {
      live = false;
    };
  }, [creek]);

  if (out === null || !out.shown) return null;
  const terms = (
    <a href={out.terms} rel="noreferrer">
      {t("inat.terms_link")}
    </a>
  );
  const fetched = out.fetched_at ? <> {t("inat.fetched", { when: when(out.fetched_at) })}</> : null;

  return (
    <section className="stack" aria-label={t("inat.region")}>
      {out.species.length === 0 ? (
        <p className="small muted">
          <strong>{t("inat.lead")}</strong> {t("inat.none")}
          {fetched}
        </p>
      ) : (
        <p className="small">
          <strong>{t("inat.lead")}</strong> {t("inat.intro", { metres: out.radius_m ?? "", since: out.since ? day(out.since) : "" })}{" "}
          {out.species.map((s, i) => (
            <span key={s.url}>
              {sighting(s)} (
              <a href={s.url} rel="noreferrer">
                {t("inat.see")}
                <span className="visually-hidden"> {t("inat.see_for", { name: s.name })}</span>
              </a>
              ){i < out.species.length - 1 ? "; " : "."}{" "}
            </span>
          ))}
          {t("inat.licence")} {terms}.{fetched}
        </p>
      )}
    </section>
  );
}
