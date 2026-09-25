"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { FocusHeading } from "./FocusHeading";
import { Row } from "./ui/Row";
import { ApiError, api } from "@/lib/api";
import { content, featureById, walkById, type Walk } from "@/lib/content";
import { has, t } from "@/lib/t";
import { reasonsThenSource } from "@/lib/text";
import { demoCreek, exampleNeeds, finishedWalk, hasMeasure, type WalkVisitSaved } from "@/lib/walks";

/**
 * A finding's name: a short label from the locale when the finding has one (city.finding_<key>),
 * else the feature's name, else the form question. A finding from a question with no feature, such
 * as barriers, would otherwise be titled with the whole question beside "Pipes and drain outlets"
 * (CRITIC_04 F04); the creek check itself still asks the question.
 */
function findingName(key: string): string {
  const short = `city.finding_${key}`;
  if (has(short)) return t(short);
  return featureById(key)?.name ?? content.form.items.find((i) => i.id === key)?.text ?? key;
}

type Demo = ReturnType<typeof demoCreek>;

/**
 * The demo creek on screen: what the walks found and what the creek needs, in approved words.
 * Pure, so scripts/tests/test_web_flows.py can draw it with the rows it hands in.
 */
export function WalkCityView({ walk, demo, back, missing }: { walk: Walk; demo: Demo | null; back: { href: string; label: string } | null; missing?: string | null }) {
  const example = exampleNeeds();
  return (
    <div className="stack">
      <FocusHeading>{t("city.walk_title", { name: walk.creek_name })}</FocusHeading>
      <p className="notice notice-warn">{t("city.walk_notice")}</p>
      {missing ? (
        <p className="notice notice-warn" data-testid="walk-record-missing">
          {missing}
        </p>
      ) : null}
      {demo === null ? null : demo.visits.length === 0 ? (
        <p>{t("city.walk_empty")}</p>
      ) : (
        <>
          <p>{t("city.walk_visits", { n: demo.visits.length })}</p>
          <section className="card stack" aria-label={t("city.walk_findings")}>
            <h2>{t("city.walk_findings")}</h2>
            {demo.findings.length === 0 ? <p className="muted">{t("city.walk_nothing")}</p> : null}
            {/* A plant is listed like any finding, and says plainly that no measure answers it
                (CRITIC_06 H01). */}
            {demo.findings.map((f) => (
              <Row
                key={`${f.spot_id}-${f.feature}`}
                label={findingName(f.feature)}
                value={
                  hasMeasure(f.feature) ? (
                    t("city.walk_seen", { n: f.visit_ids.length })
                  ) : (
                    <>
                      {t("city.walk_seen", { n: f.visit_ids.length })}
                      <br />
                      {t("city.walk_no_measure")}
                    </>
                  )
                }
              />
            ))}
          </section>
          <section className="card stack" aria-label={t("city.walk_needs")}>
            <h2>{t("city.walk_needs")}</h2>
            {/* Findings with no measure (a plant) are not "nothing found" (CRITIC_07 J04). */}
            {demo.needs.length === 0 ? (
              <p className="muted">{t(demo.findings.length === 0 ? "city.walk_nothing" : "city.walk_needs_none")}</p>
            ) : null}
            {demo.needs.map((n) => (
              <Row key={n.sentence_id} label={n.text} value={reasonsThenSource(n.because.map(findingName), n.source)} />
            ))}
          </section>
          {/* The clips show natural creeks, so an honest walk asks nothing of a city. Rather than
              end on nothing, the view shows what one reported built bank would ask for, marked as
              an example, from the same rules and approved sentences as the box above (CRITIC_09 Q01). */}
          {demo.needs.length === 0 ? (
            <section className="card stack" aria-label={t("city.walk_example_title")} data-testid="walk-example">
              <h2>{t("city.walk_example_title")}</h2>
              <p>{t("city.walk_example_intro")}</p>
              {example.map((n) => (
                <Row key={n.sentence_id} label={n.text} value={reasonsThenSource(n.because.map(findingName), n.source)} />
              ))}
            </section>
          ) : null}
        </>
      )}
      {back ? (
        <p>
          <Link href={back.href}>{back.label}</Link>
        </p>
      ) : null}
      <p>
        <Link href="/judges">{t("city.walk_more")}</Link>
      </p>
    </div>
  );
}

/**
 * /city?walk=<id>[&record=<record id>]: the demo creek a video walk feeds. Same two functions the
 * city view runs on stored visits (findings, then what the creek needs in approved words), over
 * the walk this browser finished, kept in IndexedDB so a new tab sees it too, and the stored
 * record the link names, read from GET /api/walk/{record_id}, so the link opens on any device
 * (UPDATE_30 section 1 item 3). It never pools other visitors' walks, and nothing here is counted.
 */
export function WalkCity({ walkId, recordId }: { walkId: string; recordId: string }) {
  const walk = walkById(walkId);
  // Null until IndexedDB and the store have answered, so the page never says to do the walk first
  // to someone whose walk is on its way.
  const [loaded, setLoaded] = useState<{ mine: WalkVisitSaved | null; linked: WalkVisitSaved | null; missing: string | null } | null>(null);
  useEffect(() => {
    let alive = true;
    const linked: Promise<{ visit: WalkVisitSaved | null; missing: string | null }> = recordId
      ? api.walkRecord(recordId).then(
          (r) => ({ visit: r.walk_id === walkId ? { walk_id: r.walk_id, answers: r.answers, answered_at: r.answered_at } : null, missing: null }),
          (err: unknown) => ({ visit: null, missing: err instanceof ApiError ? (err.detail ?? t("spot.not_found")) : t("error.network") }),
        )
      : Promise.resolve({ visit: null, missing: null });
    void Promise.all([finishedWalk(walkId).catch(() => null), linked]).then(([mine, other]) => {
      if (alive) setLoaded({ mine, linked: other.visit, missing: other.missing });
    });
    return () => {
      alive = false;
    };
  }, [walkId, recordId]);
  const demo = useMemo(() => {
    if (!walk || loaded === null) return null;
    return demoCreek(walk, [loaded.mine, loaded.linked].filter((v): v is WalkVisitSaved => v !== null));
  }, [walk, loaded]);
  if (!walk) return <p className="notice notice-warn">{t("city.none")}</p>;
  // Back to the walk page, which opens on the record this browser made (CRITIC_10 S01), or to the
  // stored record the link named.
  const back = loaded?.mine
    ? { href: `/walk/${encodeURIComponent(walk.id)}`, label: t("city.walk_back") }
    : loaded?.linked
      ? { href: `/spot?id=${encodeURIComponent(recordId)}`, label: t("city.walk_back_stored") }
      : null;
  return <WalkCityView walk={walk} demo={demo} back={back} missing={loaded?.missing ?? null} />;
}
