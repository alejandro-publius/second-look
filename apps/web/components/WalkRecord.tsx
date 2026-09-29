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
import { checkLanguages } from "@/lib/lang";
import { t } from "@/lib/t";
import { bundleProblems } from "@/lib/walks";

/** A day as a person reads it, in UTC so the server's delete date reads the same everywhere. */
export function walkDay(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("en-US", { dateStyle: "medium", timeZone: "UTC" });
}

/**
 * The language a record's questions were shown in, as its QuestionnaireResponse states it
 * (UPDATE_32 section 2). English when the record states none, or one the check does not offer.
 */
export function recordLanguage(bundle: Record<string, unknown>): string {
  const entries: unknown[] = Array.isArray(bundle.entry) ? bundle.entry : [];
  for (const entry of entries) {
    const r = (entry as { resource?: { resourceType?: unknown; language?: unknown } } | null)?.resource;
    if (r?.resourceType === "QuestionnaireResponse") return typeof r.language === "string" && checkLanguages().includes(r.language) ? r.language : "en";
  }
  return "en";
}

/**
 * A walk's answers, listed as /spot lists a stored visit's (CRITIC_04 F01). Where /spot shows the
 * observer's score, a walk has none: the record's observer carries no score, because nobody took
 * the test on this phone for it. A question with no feature is never tested.
 *
 * lang is the language the walk was taken in: each question and answer reads back in it, in the
 * official app's own words, and English that stands in for a translation carries the English tag.
 */
export function WalkAnswers({ answers, title, lang = "en" }: { answers: Record<string, AnswerValue>; title: string; lang?: string }) {
  // The link sits inside the sentence, where the locale string says {link}.
  const [scoreBefore, scoreAfter] = t("walk.score_note").split("{link}");
  return (
    <section className="stack" aria-labelledby="walk-answers-title">
      <h2 id="walk-answers-title">{title}</h2>
      <div data-testid="walk-answers">
        {answerRows(answers, lang).map((row) => (
          <AnswerLine key={row.item_id} text={row.question} value={row.answer} score={row.feature ? t("walk.not_tested") : t("spot.no_feature")} />
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
      <WalkAnswers answers={record.answers} title={t("walk.stored_answers")} lang={recordLanguage(record.bundle)} />
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
