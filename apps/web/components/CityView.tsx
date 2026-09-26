"use client";

import { useEffect, useState } from "react";
import { FocusHeading } from "./FocusHeading";
import { InatContext } from "./InatContext";
import { Icon } from "./ui/Icon";
import { Row } from "./ui/Row";
import { Skeleton } from "./ui/Skeleton";
import { api, ApiError, isNetworkError, type CityOut, type CityPipe, type FhirResource } from "@/lib/api";
import { creeksByRegion } from "@/lib/content";
import { t } from "@/lib/t";
import { reasonsThenSource } from "@/lib/text";

// "1 spot", not "1 spots": the key for one, or the key for any other number with {n} filled in.
function count(n: number, one: string, many: string): string {
  return n === 1 ? t(one) : t(many, { n });
}

function people(n: number): string {
  return count(n, "city.observer_one", "city.observers");
}

/**
 * "Open the records" on screen. A screen reader hears what the link opens as well, so five of
 * these in a links list can be told apart.
 */
function Evidence({ href, name }: { href: string; name: string }) {
  return (
    <a href={href} rel="noreferrer">
      {t("city.evidence")}
      <span className="visually-hidden"> {t("city.evidence_for", { name })}</span>
    </a>
  );
}

/** The laboratory Observations of an example result: the ones that point at a Specimen. */
function panelOf(entries: { resource: FhirResource }[] | undefined): FhirResource[] {
  return (entries ?? []).map((e) => e.resource).filter((r) => r.resourceType === "Observation" && r.specimen !== undefined);
}

function measureOf(r: FhirResource): string {
  return r.code?.coding?.[0]?.display ?? r.code?.text ?? r.id ?? "";
}

function valueOf(r: FhirResource): string {
  if (r.valueQuantity) return `${r.valueQuantity.value ?? ""} ${r.valueQuantity.unit ?? r.valueQuantity.code ?? ""}`.trim();
  const coding = r.valueCodeableConcept?.coding?.[0];
  return coding?.display ?? coding?.code ?? "";
}

/**
 * One pipe worth testing. The referral link is real. The example result is fetched only when
 * asked for, wears the word Example in a badge and in a notice, and is never a number on this page.
 */
function PipeRow({ pipe }: { pipe: CityPipe }) {
  const [example, setExample] = useState<FhirResource[] | null>(null);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function toggle() {
    if (open) {
      setOpen(false);
      return;
    }
    setOpen(true);
    if (example === null) {
      try {
        const bundle = await api.fhirAt(pipe.example_result);
        setExample(panelOf(bundle.entry));
      } catch {
        setError(t("error.network"));
      }
    }
  }

  return (
    <div className="stack">
      <Row
        label={pipe.spot_name}
        value={`${people(pipe.observers)}, ${count(Math.max(...pipe.dry_days), "city.dry_day_one", "city.dry_days")}`}
        end={<Evidence href={pipe.fhir[0]} name={pipe.spot_name} />}
      />
      <div className="btn-row">
        <a className="btn btn-secondary" href={pipe.referral} rel="noreferrer">
          {t("city.referral_link")}
        </a>
        <button type="button" className="btn btn-secondary" aria-expanded={open} onClick={() => void toggle()}>
          {open ? t("city.example_hide") : t("city.example_show")}
        </button>
      </div>
      {open ? (
        <section className="stack" aria-label={t("city.example_badge")}>
          <span className="badge badge-warn">{t("city.example_badge")}</span>
          <div className="notice notice-warn">
            <Icon name="info" />
            <p>{t("city.example_note")}</p>
          </div>
          {error ? <p className="notice notice-bad">{error}</p> : null}
          {example === null && !error ? <p className="muted">{t("city.example_loading")}</p> : null}
          {example !== null ? (
            <table className="tabular">
              <thead>
                <tr>
                  <th scope="col">{t("city.example_measure")}</th>
                  <th scope="col">{t("city.example_value")}</th>
                </tr>
              </thead>
              <tbody>
                {example.map((r) => (
                  <tr key={r.id}>
                    <td>{measureOf(r)}</td>
                    <td>{valueOf(r)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
          <a href={pipe.example_result} rel="noreferrer">
            {t("city.example_fhir")}
          </a>
        </section>
      ) : null}
    </div>
  );
}

/**
 * What a city analyst sees. Two lists decided by code, and never a number without the records
 * behind it: every figure here carries a link to the FHIR Bundles it was counted from.
 *
 * An empty "what this creek needs" is said out loud rather than left blank, because no measure
 * and no approved sentence look identical from the outside and mean very different things.
 */
/**
 * Keeps the tab's title while this screen shows. The page's title is fixed when it is built, the
 * same for every query, and the framework writes it back once the page has loaded, so it is set
 * again whenever it changes (critic round 14 P02).
 */
export function useTabTitle(title: string | null) {
  useEffect(() => {
    if (title === null) return;
    const apply = () => {
      if (document.title !== title) document.title = title;
    };
    apply();
    const watch = new MutationObserver(apply);
    watch.observe(document.head, { subtree: true, childList: true, characterData: true });
    return () => watch.disconnect();
  }, [title]);
}

/** Every region pack with its creeks, each a plain link (CRITIC_13 W02). */
function CreekPicker() {
  return (
    <>
      {creeksByRegion().map((r) => (
        <section key={r.region} className="stack">
          <h2>{r.name}</h2>
          {r.creeks.length === 0 ? (
            <p className="muted">{t("city.pick_none")}</p>
          ) : (
            <ul>
              {r.creeks.map((c) => (
                <li key={c.slug}>
                  <a href={`/city?creek=${encodeURIComponent(c.slug)}`}>{c.name}</a>
                </li>
              ))}
            </ul>
          )}
        </section>
      ))}
    </>
  );
}

export function CityView({ creekId }: { creekId: string | null }) {
  const [view, setView] = useState<CityOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  // An unknown creek gets the pick list as its way on (critic round 14 P02).
  const [unknown, setUnknown] = useState(false);

  // A link that names no creek is a pick list, so its tab says so (critic round 14 P02).
  useTabTitle(creekId === "" ? `${t("city.pick_title")}: ${t("app.name")}` : null);

  useEffect(() => {
    if (!creekId) return;
    let live = true;
    api
      .city(creekId)
      .then((v) => live && setView(v))
      .catch((err) => {
        if (!live) return;
        // A 404 says in the API's own words that it has no record of the creek. Nothing was sent,
        // so "Something did not send" would be untrue (CRITIC_09 R05).
        if (err instanceof ApiError && err.status === 404) {
          setError(t("city.no_creek"));
          setUnknown(true);
        } else setError(isNetworkError(err) ? t("error.network") : t("error.server"));
      });
    return () => {
      live = false;
    };
  }, [creekId]);

  // Every state has the page's one level-one heading, the loading and empty ones too (axe
  // page-has-heading-one on /city, docs/internal/reviews/A11Y_00.md).
  // A link that names no creek, such as bare /city, says so and lists every region pack with its
  // creeks, rather than speak of "this creek" without naming one (CRITIC_11 W02).
  // The creek links are plain links, so each one loads its page whole. This page reads its query
  // once, and a client side move to /city with a new query kept the pick list on screen whenever
  // the router had not fetched the creek's page ahead of the tap, as on a slow phone (CRITIC_13 W02).
  if (creekId === "") {
    return (
      <div className="stack">
        <h1>{t("city.pick_title")}</h1>
        <p>{t("city.pick")}</p>
        <CreekPicker />
      </div>
    );
  }
  if (error) {
    return (
      <div className="stack">
        <h1>{t("city.title")}</h1>
        <div className="notice notice-warn" role="status">
          <Icon name="info" />
          <p>{error}</p>
        </div>
        {unknown ? <CreekPicker /> : null}
      </div>
    );
  }
  // Not read from the address yet (null), or waiting for the API.
  if (!view) {
    return (
      <div className="stack">
        <h1>{t("city.title")}</h1>
        <Skeleton label={t("spot.loading")} lines={3} photo={false} />
      </div>
    );
  }

  return (
    <div className="stack">
      <FocusHeading>{t("city.title")}</FocusHeading>
      <p>{t("city.intro", { creek: view.creek_name })}</p>
      <p className="small muted tabular">{t("city.visits", { visits: count(view.visits, "city.n_visit", "city.n_visits"), spots: count(view.spots, "city.n_spot", "city.n_spots") })}</p>

      <h2>{t("city.needs_title")}</h2>
      <p className="small muted">
        {t("city.needs_source")}{" "}
        <a href="https://www.oneaquahealth.eu/app/uploads/2026/05/OneAquaHealth-Policy-Brief.pdf" rel="noreferrer">
          {t("city.needs_source_link")}
        </a>
        .
      </p>
      {/* An empty list blames approval only when no measure is approved yet. With the measures
          approved, it means nothing reported here calls for one (REVIEW_03 R28). */}
      {view.needs.length === 0 && view.measures_waiting_for_approval ? (
        <div className="notice notice-warn">
          <Icon name="info" />
          <p>{t("city.needs_waiting")}</p>
        </div>
      ) : view.needs.length === 0 ? (
        <p className="muted">{t("city.needs_none")}</p>
      ) : (
        <div className="card">
          {view.needs.map((n) => (
            <Row
              key={n.sentence_id}
              label={n.text}
              value={reasonsThenSource(n.because, n.source)}
              end={<Evidence href={n.fhir[0]} name={n.because.join(", ")} />}
            />
          ))}
        </div>
      )}

      <h2>{t("city.pipes_title")}</h2>
      <p className="small muted">{t("city.pipes_note")}</p>
      {view.pipes_worth_testing.length === 0 ? (
        <p className="muted">{t("city.pipes_none")}</p>
      ) : (
        <div className="card stack">
          {view.pipes_worth_testing.map((p) => (
            <PipeRow key={p.spot_id} pipe={p} />
          ))}
        </div>
      )}

      {view.reaches.length > 0 ? (
        <>
          <h2>{t("city.reaches_title")}</h2>
          <p className="small muted">{t("city.reaches_note")}</p>
          <ol className="timeline">
            {view.reaches.map((r) => (
              <li key={r.slug}>
                <h3>{r.name}</h3>
                <p className="small muted tabular">
                  {r.flows_into_name ? t("city.flows_into", { name: r.flows_into_name }) : t("city.flows_end")}. {t("city.reach_counts", { visits: count(r.visits, "city.n_visit", "city.n_visits"), spots: count(r.spots, "city.n_spot", "city.n_spots") })}.
                </p>
                {r.notes.length === 0 ? (
                  <p className="small muted">{t("city.reach_quiet")}</p>
                ) : (
                  <div className="card">
                    {r.notes.map((n) => (
                      <Row
                        key={`${n.from_reach_slug}:${n.feature}`}
                        label={n.line}
                        value={n.from_reach_name}
                        end={<Evidence href={n.fhir[0]} name={`${n.feature_name}, ${n.from_reach_name}`} />}
                      />
                    ))}
                  </div>
                )}
              </li>
            ))}
          </ol>
          {view.unplaced_spots > 0 ? <p className="small muted">{count(view.unplaced_spots, "city.unplaced_one", "city.unplaced")}</p> : null}
        </>
      ) : null}

      <h2>{t("city.findings_title")}</h2>
      {/* A creek with checks and nothing reported says so, and never that nobody checked it; the
          count at the top would say otherwise (CRITIC_06 H01). */}
      {view.findings.length === 0 ? (
        <p className="muted">{t(view.visits === 0 ? "city.none" : "city.findings_none")}</p>
      ) : (
        <div className="card">
          {view.findings.map((f) => (
            <Row
              key={`${f.spot_id}:${f.feature}`}
              label={`${f.feature_name}, ${f.spot_name}`}
              value={people(f.observers)}
              end={<Evidence href={f.fhir[0]} name={`${f.feature_name}, ${f.spot_name}`} />}
            />
          ))}
        </div>
      )}

      {/* Context from iNaturalist, after what people reported and counted in nothing above. */}
      <InatContext creek={view.creek_slug ?? view.creek_id} />

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
