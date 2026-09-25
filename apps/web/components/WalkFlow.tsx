"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { AnswerLine } from "./AnswerLine";
import { FhirView } from "./FhirView";
import { FocusHeading } from "./FocusHeading";
import { FormQuestion } from "./FormQuestion";
import { Photo } from "./Photo";
import { Progress } from "./Progress";
import { answerRows } from "@/lib/answers";
import type { AnswerValue } from "@/lib/api";
import { content, featureById, licenseUrl, questionCount, type FormItem, type Walk } from "@/lib/content";
import { t } from "@/lib/t";
import { buildRecord, saveWalkVisit, type WalkAnswers } from "@/lib/walks";

type Stage =
  | { name: "watch" }
  | { name: "items"; index: number }
  | { name: "question" }
  | { name: "record"; answeredAt: string };

function visibleItems(answers: Record<string, AnswerValue>): FormItem[] {
  return content.form.items.filter((item) => !item.depends_on || answers[item.depends_on.item] === item.depends_on.value);
}

function Clip({ walk }: { walk: Walk }) {
  const poster = content.photos[walk.poster_photo_id];
  return (
    <figure className="stack walk-figure">
      <video className="walk-clip" controls muted playsInline preload="metadata" poster={poster?.url} aria-label={t("walk.clip_label", { creek: walk.creek_name })}>
        <source src={`/${walk.clip.file}`} type="video/mp4" />
        <Photo id={walk.poster_photo_id} />
      </video>
      <figcaption className="small">
        {t("walk.credit", { title: walk.title, author: walk.author })}{" "}
        {licenseUrl(walk.license) ? (
          <a href={licenseUrl(walk.license)} rel="license noreferrer">
            {walk.license}
          </a>
        ) : (
          walk.license
        )}
        {". "}
        <a href={walk.source_url} rel="noreferrer nofollow">
          {t("credits.source")}
        </a>
      </figcaption>
    </figure>
  );
}

/**
 * The line under the record about the checker. The count of stopped guesses is shown only when the
 * checker's run on the footage was real: a number from the fake client's run is never shown.
 *
 * With no question and nothing dropped, no model said yes to any feature on the clip's frames in
 * most of its runs (scripts/build_walks.py), so the pass rule stopped nothing and the line must
 * not say it did (CRITIC_03 E04). One stopped guess "was", more "were".
 */
export function checkerLine(walk: Pick<Walk, "question" | "checker_run" | "checker_dropped">): string {
  if (walk.question) return t("walk.checker_asked");
  if (walk.checker_run !== "real") return t("walk.checker_not_real");
  if (walk.checker_dropped === 0) return t("walk.checker_nothing_seen");
  if (walk.checker_dropped === 1) return t("walk.checker_none_one");
  return t("walk.checker_none", { n: walk.checker_dropped });
}

/**
 * A guided creek check made while watching a clip (Update 14 3.7). The checker's flag, if the gate
 * let one through at build time, is asked only after the person has answered. The record is made
 * on this device and never sent.
 */
export function WalkFlow({ walk }: { walk: Walk }) {
  const [stage, setStage] = useState<Stage>({ name: "watch" });
  const [answers, setAnswers] = useState<Record<string, AnswerValue>>({});
  const [lookedAgain, setLookedAgain] = useState<string | null>(null);
  const items = useMemo(() => visibleItems(answers), [answers]);

  function finish() {
    const answeredAt = new Date().toISOString();
    saveWalkVisit({ walk_id: walk.id, answers: answers as WalkAnswers, answered_at: answeredAt });
    setStage({ name: "record", answeredAt });
  }

  function answerItem(index: number, value: AnswerValue | undefined) {
    const item = items[index];
    const next = { ...answers };
    if (value === undefined) delete next[item.id];
    else next[item.id] = value;
    setAnswers(next);
    const nextItems = visibleItems(next);
    const pos = nextItems.findIndex((i) => i.id === item.id);
    if (pos + 1 < nextItems.length) setStage({ name: "items", index: pos + 1 });
    else if (walk.question) setStage({ name: "question" });
    else finish();
  }

  // The clip is mounted once, above whatever the stage shows, so it keeps playing while the person
  // answers. Only the record screen, which comes after, leaves it out.
  let body: React.ReactNode = null;
  switch (stage.name) {
    case "watch":
      body = (
        <>
          <p>{t("walk.intro")}</p>
          {/* The clips show natural creeks, so an honest check finds little for a city to do. This
              says how to see a measure before the check starts (CRITIC_09 Q01). */}
          <p data-testid="walk-honest-note">{t("walk.honest_note")}</p>
          {/* The button before the demo notice, so it is on the first screen of every walk on a
              390 by 844 phone (CRITIC_11 V01). */}
          <button type="button" className="btn btn-block" onClick={() => setStage({ name: "items", index: 0 })}>
            {t("walk.start")}
          </button>
          <p className="notice notice-warn">{t("walk.demo_notice")}</p>
        </>
      );
      break;
    case "items": {
      const item = items[stage.index];
      if (item) {
        const count = questionCount(items, stage.index);
        body = (
          <div className="stack" key={item.id}>
            <Progress value={count.n} max={count.total} labelKey="check.progress" />
            <FormQuestion
              item={item}
              value={answers[item.id]}
              onAnswer={(v) => answerItem(stage.index, v)}
              onSkip={() => answerItem(stage.index, undefined)}
              onBack={() => (stage.index === 0 ? setStage({ name: "watch" }) : setStage({ name: "items", index: stage.index - 1 }))}
            />
          </div>
        );
      }
      break;
    }
    case "question": {
      const q = walk.question!;
      body = (
        <>
          <section className="card stack" aria-label={t("label.checker_noticed")}>
            <p>
              <strong>{t("followup.checker_flag", { note: featureById(q.feature)?.plain ?? q.feature })}</strong>
            </p>
            <p className="small muted">
              {t("label.checker_noticed")}: {q.note}
            </p>
            <div className="btn-row">
              <button type="button" className="btn" aria-pressed={lookedAgain === "looked"} onClick={() => setLookedAgain("looked")}>
                {t("check.looked_again")}
              </button>
              <button type="button" className="btn btn-secondary" aria-pressed={lookedAgain === "skipped"} onClick={() => setLookedAgain("skipped")}>
                {t("check.skip")}
              </button>
            </div>
          </section>
          <button type="button" className="btn btn-block" onClick={finish}>
            {t("check.finish")}
          </button>
        </>
      );
      break;
    }
    case "record": {
      const { bundle, problems } = buildRecord(walk, answers as WalkAnswers, stage.answeredAt);
      // The link sits inside the sentence, where the locale string says {link}.
      const [scoreBefore, scoreAfter] = t("walk.score_note").split("{link}");
      return (
        <div className="stack">
          <FocusHeading>{t("walk.done_title")}</FocusHeading>
          <p className="notice notice-ok" role="status">
            {t("walk.done_body")}
          </p>
          <p className={problems.length === 0 ? "badge badge-ok" : "badge badge-bad"} data-testid="walk-structure">
            {problems.length === 0 ? t("walk.structure_ok") : t("walk.structure_bad", { n: problems.length })}
          </p>
          {/* The answers, listed as /spot lists a stored visit's (CRITIC_04 F01). Where /spot shows
              the observer's score, a walk has none: the record's observer carries no score, because
              nobody took the test on this phone for it. A question with no feature is never tested. */}
          <section className="stack" aria-labelledby="walk-answers-title">
            <h2 id="walk-answers-title">{t("walk.answers_title")}</h2>
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
          <p className="small muted">{checkerLine(walk)}</p>
          <FhirView load={() => Promise.resolve(bundle)} curl={null} />
          <p>
            <Link className="btn btn-block" href={`/city?walk=${encodeURIComponent(walk.id)}`}>
              {t("walk.city_link")}
            </Link>
          </p>
          <p>
            <Link href="/walk">{t("walk.more")}</Link>
          </p>
        </div>
      );
    }
  }

  return (
    <div className="stack">
      <FocusHeading>{walk.creek_name}</FocusHeading>
      <Clip walk={walk} />
      {body}
    </div>
  );
}
