"use client";

import { useMemo, useSyncExternalStore } from "react";
import { FocusHeading } from "./FocusHeading";
import { Row } from "./ui/Row";
import { content, featureById, walkById } from "@/lib/content";
import { has, t } from "@/lib/t";
import { reasonsThenSource } from "@/lib/text";
import { demoCreek, savedWalkVisits } from "@/lib/walks";

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

/**
 * /city?walk=<id>: the demo creek a video walk feeds. Same two functions the city view runs on
 * stored visits (findings, then what the creek needs in approved words), over the walks made on
 * this phone only. Nothing here is stored or counted.
 */
export function WalkCity({ walkId }: { walkId: string }) {
  const walk = walkById(walkId);
  // Session storage exists only in the browser, so the server render sees no visits yet.
  const saved = useSyncExternalStore(
    () => () => undefined,
    () => JSON.stringify(savedWalkVisits()),
    () => "",
  );
  const demo = useMemo(() => (walk && saved ? demoCreek(walk) : null), [walk, saved]);
  if (!walk) return <p className="notice notice-warn">{t("city.none")}</p>;
  return (
    <div className="stack">
      <FocusHeading>{t("city.walk_title", { name: walk.creek_name })}</FocusHeading>
      <p className="notice notice-warn">{t("city.walk_notice")}</p>
      {demo === null ? null : demo.visits.length === 0 ? (
        <p>{t("city.walk_empty")}</p>
      ) : (
        <>
          <p>{t("city.walk_visits", { n: demo.visits.length })}</p>
          <section className="card stack" aria-label={t("city.walk_findings")}>
            <h2>{t("city.walk_findings")}</h2>
            {demo.findings.length === 0 ? <p className="muted">{t("city.walk_nothing")}</p> : null}
            {demo.findings.map((f) => (
              <Row key={`${f.spot_id}-${f.feature}`} label={findingName(f.feature)} value={t("city.walk_seen", { n: f.visit_ids.length })} />
            ))}
          </section>
          <section className="card stack" aria-label={t("city.walk_needs")}>
            <h2>{t("city.walk_needs")}</h2>
            {demo.needs.length === 0 ? <p className="muted">{t("city.walk_nothing")}</p> : null}
            {demo.needs.map((n) => (
              <Row key={n.sentence_id} label={n.text} value={reasonsThenSource(n.because.map(findingName), n.source)} />
            ))}
          </section>
        </>
      )}
    </div>
  );
}
