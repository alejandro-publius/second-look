"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AnswerLine } from "./AnswerLine";
import { ChecksThatRan } from "./ChecksThatRan";
import { FhirView } from "./FhirView";
import { FocusHeading } from "./FocusHeading";
import { answerRows } from "@/lib/answers";
import { ApiError, api, type AnswerValue, type WalkRecordOut } from "@/lib/api";
import { walkById } from "@/lib/content";
import { t } from "@/lib/t";
import { bundleProblems } from "@/lib/walks";

/** A day as a person reads it, in UTC so the server's delete date reads the same everywhere. */
export function walkDay(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("en-US", { dateStyle: "medium", timeZone: "UTC" });
}

/**
 * A walk's answers, listed as /spot lists a stored visit's (CRITIC_04 F01). Where /spot shows the
 * observer's score, a walk has none: the record's observer carries no score, because nobody took
 * the test on this phone for it. A question with no feature is never tested.
 */
export function WalkAnswers({ answers, title }: { answers: Record<string, AnswerValue>; title: string }) {
  // The link sits inside the sentence, where the locale string says {link}.
  const [scoreBefore, scoreAfter] = t("walk.score_note").split("{link}");
  return (
    <section className="stack" aria-labelledby="walk-answers-title">
      <h2 id="walk-answers-title">{title}</h2>
      <div data-testid="walk-answers">
        {answerRows(answers).map((row) => (
          <AnswerLine key={row.item_id} text={row.text} value={row.label} score={row.feature ? t("walk.not_tested") : t("spot.no_feature")} />
        ))}
      </div>
      <p className="small muted" data-testid="walk-score-note">
        {scoreBefore}
        <Link href="/two">{t("walk.score_link")}</Link>
        {scoreAfter}
      </p>
    </section>
  );
}

/**
 * /spot?id=walk-...: a finished walk's record as the store keeps it (UPDATE_30 section 1 item 3),
 * so the link opens on any device, until its delete date. The same answers and the same Bundle
 * the walk page built, read back from GET /api/walk/{record_id}.
 */
export function WalkStoredRecord({ recordId }: { recordId: string }) {
  const [record, setRecord] = useState<WalkRecordOut | null>(null);
  const [problem, setProblem] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    api
      .walkRecord(recordId)
      .then((r) => {
        if (alive) setRecord(r);
      })
      .catch((err: unknown) => {
        if (alive) setProblem(err instanceof ApiError ? (err.detail ?? t("spot.not_found")) : t("error.network"));
      });
    return () => {
      alive = false;
    };
  }, [recordId]);

  if (problem !== null) {
    return (
      <div className="stack">
        <FocusHeading>{t("walk.stored_title")}</FocusHeading>
        <p className="notice notice-warn">{problem}</p>
        <p>
          <Link href="/walk">{t("walk.list_title")}</Link>
        </p>
      </div>
    );
  }
  if (record === null) {
    return (
      <p role="status" className="muted">
        {t("spot.loading")}
      </p>
    );
  }
  const walk = walkById(record.walk_id);
  // The structure check the walk page runs, over the stored Bundle itself.
  const problems = bundleProblems(record.bundle);
  const city = `/city?walk=${encodeURIComponent(record.walk_id)}&record=${encodeURIComponent(record.record_id)}`;
  return (
    <div className="stack">
      <FocusHeading>{t("walk.stored_title")}</FocusHeading>
      <p className="muted">{t("walk.stored_intro", { creek: walk?.creek_name ?? record.walk_id, date: walkDay(record.answered_at) })}</p>
      <p className="notice notice-warn" data-testid="walk-stored-notice">
        {t("walk.stored_notice", { date: walkDay(record.delete_after) })}
      </p>
      <p className={problems.length === 0 ? "badge badge-ok" : "badge badge-bad"} data-testid="walk-structure">
        {problems.length === 0 ? t("walk.structure_ok") : t("walk.structure_bad", { n: problems.length })}
      </p>
      <WalkAnswers answers={record.answers} title={t("walk.stored_answers")} />
      {/* The follow-up checks the store ran and kept with the walk (judge walk W01), as /spot shows
          a creek check's. A record stored before walks asked any has none. */}
      <ChecksThatRan checks={record.checks ?? []} ratings={{ first_rating: record.first_rating ?? null, final_rating: record.final_rating ?? null }} level="h2" />
      <FhirView load={() => Promise.resolve(record.bundle)} curl={`curl -s ${api.walkFhirUrl(record.record_id)}`} walk="stored" />
      <p>
        <Link className="btn btn-block" href={city}>
          {t("walk.city_link")}
        </Link>
      </p>
      {walk ? (
        <p>
          <Link href={`/walk/${encodeURIComponent(walk.id)}`}>{t("walk.do_it")}</Link>
        </p>
      ) : null}
    </div>
  );
}
