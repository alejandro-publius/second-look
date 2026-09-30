"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChecksThatRan } from "./ChecksThatRan";
import { FhirView } from "./FhirView";
import { FocusHeading } from "./FocusHeading";
import { FollowupCard, tapRating, type RatingTap } from "./FollowupCard";
import { FormQuestion } from "./FormQuestion";
import { LanguagePicker } from "./LanguagePicker";
import { Photo } from "./Photo";
import { Progress } from "./Progress";
import { WalkAnswers, walkDay } from "./WalkRecord";
import { api, type AnswerValue } from "@/lib/api";
import {
  content,
  featureById,
  licenseName,
  licenseUrl,
  questionCount,
  type FormItem,
  type Walk,
} from "@/lib/content";
import {
  deleteWalkState,
  enqueue,
  flushQueue,
  getQueued,
  loadWalkState,
  onQueueChange,
  removeQueued,
  saveWalkState,
  sendQueued,
  startQueueWatcher,
  type WalkState,
} from "@/lib/offline";
import { shownOptions, uiText, useCheckLang } from "@/lib/lang";
import { t } from "@/lib/t";
import { buildRecord, settleFollowups, walkQuestions } from "@/lib/walks";

type Stage =
  | { name: "loading" }
  | { name: "watch" }
  | { name: "items"; index: number }
  | { name: "followups" }
  | { name: "question" }
  | { name: "record"; answeredAt: string };

/** A walk on this device before its first answer. */
function freshState(walkId: string): WalkState {
  return {
    walk_id: walkId,
    answers: {},
    next: 0,
    answered_at: null,
    queue_id: null,
    record_id: null,
    delete_after: null,
    followup_answers: {},
    final_rating: null,
  };
}

/** Where the finished walk's record is: being sent, waiting for a network, kept, or refused. */
type Stored =
  | { state: "sending" }
  | { state: "waiting" }
  | { state: "stored"; record_id: string; delete_after: string }
  | { state: "failed"; detail: string };

function visibleItems(answers: Record<string, AnswerValue>): FormItem[] {
  return content.form.items.filter(
    (item) =>
      !item.depends_on ||
      answers[item.depends_on.item] === item.depends_on.value,
  );
}

/**
 * The clip, with its poster until the person presses play. preload="none" asks for no byte of the
 * video before then, so opening a walk costs a slow phone line nothing (judge walk W05). The clip
 * is served in parts by functions/walks/[[path]].js, so the slider can jump to any second.
 */
function Clip({ walk }: { walk: Walk }) {
  const poster = content.photos[walk.poster_photo_id];
  return (
    <figure className="stack walk-figure">
      <video
        className="walk-clip"
        controls
        muted
        playsInline
        preload="none"
        poster={poster?.url}
        aria-label={t("walk.clip_label", { creek: walk.creek_name })}
      >
        <source src={`/${walk.clip.file}`} type="video/mp4" />
        <Photo id={walk.poster_photo_id} />
      </video>
      <figcaption className="small">
        {t("walk.credit", { title: walk.title, author: walk.author })}{" "}
        {licenseUrl(walk.license) ? (
          <a href={licenseUrl(walk.license)} rel="license noreferrer">
            {licenseName(walk.license)}
          </a>
        ) : (
          licenseName(walk.license)
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
export function checkerLine(
  walk: Pick<Walk, "question" | "checker_run" | "checker_dropped">,
): string {
  if (walk.question) return t("walk.checker_asked");
  if (walk.checker_run !== "real") return t("walk.checker_not_real");
  if (walk.checker_dropped === 0) return t("walk.checker_nothing_seen");
  if (walk.checker_dropped === 1) return t("walk.checker_none_one");
  return t("walk.checker_none", { n: walk.checker_dropped });
}

/** The stage a walk this device holds opens on: its record, or the next unanswered question. */
function resumeStage(walk: Walk, saved: WalkState): Stage {
  if (saved.answered_at)
    return { name: "record", answeredAt: saved.answered_at };
  const items = visibleItems(saved.answers);
  if (saved.next < items.length)
    return { name: "items", index: Math.max(0, saved.next) };
  if (walkQuestions(saved.answers).length > 0) return { name: "followups" };
  return walk.question
    ? { name: "question" }
    : { name: "items", index: Math.max(0, items.length - 1) };
}

/**
 * A guided creek check made while watching a clip (Update 14 3.7). The checker's flag, if the gate
 * let one through at build time, is asked only after the person has answered.
 *
 * After the last question the creek check's own follow-up rules run on the answers (judge walk
 * W01), through the port the store runs, and the questions they pick are shown the way the creek
 * check shows its own: a clip has no weather, so the dry pipe question is never asked, and the
 * rating check is. The answers go to the store with the walk, which runs the rules again and keeps
 * the checks, and the record shows "Checks that ran" as /spot does for a creek check.
 *
 * Every answer is kept in IndexedDB beside the creek check's offline queue, keyed by the walk's
 * id, so the browser's Back, a reload or a closed tab opens the walk on its next unanswered
 * question with the earlier answers in place (UPDATE_30 section 1 item 2). A finished walk goes
 * into the offline queue, which sends it to the store; the store keeps it as a demo record for 30
 * days and the page shows its link, which opens on any device (item 3). It is never counted.
 */
export function WalkFlow({ walk }: { walk: Walk }) {
  const [stage, setStage] = useState<Stage>({ name: "loading" });
  const [answers, setAnswers] = useState<Record<string, AnswerValue>>({});
  const [lang] = useCheckLang();
  // The language a finished walk was taken in, so its record says that one even if the picker
  // changes later (UPDATE_32 section 7, review finding 2). Null while the walk is not finished.
  const [walkLang, setWalkLang] = useState<string | null>(null);
  const [lookedAgain, setLookedAgain] = useState<string | null>(null);
  const [resumed, setResumed] = useState(false);
  const [stored, setStored] = useState<Stored>({ state: "sending" });
  // The follow-ups the rules asked: what was answered, the rating the rating check left, and
  // whether its rating picker is open, as the creek check holds them.
  const [followupAnswers, setFollowupAnswers] = useState<
    Record<string, string>
  >({});
  const [finalRating, setFinalRating] = useState<string | null>(null);
  const [changingRating, setChangingRating] = useState(false);
  // Start again asks first on a finished walk, since it clears the record from this device.
  const [confirmStartAgain, setConfirmStartAgain] = useState(false);
  const keepWalk = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (confirmStartAgain) keepWalk.current?.focus();
  }, [confirmStartAgain]);
  const items = useMemo(() => visibleItems(answers), [answers]);
  const ratingItem = content.form.items.find((i) => i.id === "overall_rating");

  // The walk as this device keeps it, and the writes to IndexedDB, one after another in order.
  const kept = useRef<WalkState>(freshState(walk.id));
  const writes = useRef<Promise<void>>(Promise.resolve());
  // Start again begins a new attempt. A send still going for the old one must not write into the
  // new one, or a reload would open on the walk that was set aside.
  const attempt = useRef(0);
  const keep = useCallback(
    (patch: Partial<WalkState>) => {
      const next = { ...kept.current, ...patch, walk_id: walk.id };
      kept.current = next;
      writes.current = writes.current.then(() => saveWalkState(next));
      return writes.current;
    },
    [walk.id],
  );

  /** Reads the finished walk's queue item and shows what the store did with it. */
  const showQueued = useCallback(async () => {
    const mine = attempt.current;
    const id = kept.current.queue_id;
    if (kept.current.record_id && kept.current.delete_after) {
      setStored({
        state: "stored",
        record_id: kept.current.record_id,
        delete_after: kept.current.delete_after,
      });
      return;
    }
    if (id === null) return;
    const item = await getQueued(id).catch(() => undefined);
    if (item === undefined || attempt.current !== mine) return;
    if (
      item.status === "sent" &&
      item.result?.record_id &&
      item.result.delete_after
    ) {
      const { record_id, delete_after } = item.result;
      setStored({ state: "stored", record_id, delete_after });
      // The record id now lives with the walk, so the queue item has done its work.
      await keep({ record_id, delete_after, queue_id: null });
      await removeQueued(id).catch(() => undefined);
    } else if (item.status === "failed") {
      setStored({ state: "failed", detail: item.error ?? t("error.server") });
    } else if (item.status === "waiting") {
      setStored({ state: "waiting" });
    }
  }, [keep]);

  /** Puts the finished walk in the offline queue and tries to send it at once. */
  const store = useCallback(async () => {
    const mine = attempt.current;
    const w = kept.current;
    if (!w.answered_at) return;
    setStored({ state: "sending" });
    // The follow-up answers go with the walk; the store runs the rules again and keeps the checks.
    const { followup_answers, final_rating } = settleFollowups(
      w.answers,
      w.followup_answers ?? {},
      w.final_rating ?? null,
    );
    const body = {
      walk_id: walk.id,
      answers: w.answers,
      answered_at: w.answered_at,
      followup_answers,
      final_rating,
      // The language the questions were shown in; the record states it (UPDATE_32 section 2).
      language: w.language ?? "en",
    };
    let id: number;
    try {
      id = await enqueue({
        kind: "walk",
        created_at: new Date().toISOString(),
        walk: body,
        photos: [],
      });
    } catch {
      // No IndexedDB here (a private window can refuse it), so no queue: send it once, directly.
      try {
        const r = await api.storeWalk(body);
        if (attempt.current === mine)
          setStored({
            state: "stored",
            record_id: r.record_id,
            delete_after: r.delete_after,
          });
      } catch (err) {
        if (attempt.current === mine)
          setStored({
            state: "failed",
            detail: (err as { detail?: string }).detail ?? t("error.network"),
          });
      }
      return;
    }
    if (attempt.current !== mine) {
      // Set aside while it was being queued: it is never sent.
      await removeQueued(id).catch(() => undefined);
      return;
    }
    await keep({ queue_id: id });
    const item = await getQueued(id);
    if (item) await sendQueued(item);
    await showQueued();
  }, [keep, showQueued, walk.id]);

  // Open where this device left the walk: its record, or the next question with the answers in.
  useEffect(() => {
    let alive = true;
    void loadWalkState(walk.id).then((saved) => {
      if (!alive) return;
      if (saved === null) {
        setStage({ name: "watch" });
        return;
      }
      kept.current = saved;
      setWalkLang(saved.answered_at ? (saved.language ?? "en") : null);
      setAnswers(saved.answers);
      setFollowupAnswers(saved.followup_answers ?? {});
      setFinalRating(saved.final_rating ?? null);
      setStage(resumeStage(walk, saved));
      if (saved.answered_at) {
        if (saved.record_id || saved.queue_id !== null) void showQueued();
        else void store();
      } else setResumed(true);
    });
    return () => {
      alive = false;
    };
    // Once per walk. store and showQueued read the walk through refs.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [walk.id]);

  // A finished walk that waits for the network is sent when it comes back, while this page is
  // open, and the page shows its link as soon as the store has it.
  useEffect(() => startQueueWatcher(), []);
  useEffect(
    () =>
      onQueueChange(() => {
        if (kept.current.answered_at) void showQueued();
      }),
    [showQueued],
  );

  async function startAgain() {
    attempt.current += 1;
    const w = kept.current;
    // A walk not stored yet is taken out of the queue, so what was set aside is never stored.
    if (w.queue_id !== null && !w.record_id)
      await removeQueued(w.queue_id).catch(() => undefined);
    kept.current = freshState(walk.id);
    setWalkLang(null);
    writes.current = writes.current.then(() => deleteWalkState(walk.id));
    await writes.current;
    setAnswers({});
    setFollowupAnswers({});
    setFinalRating(null);
    setChangingRating(false);
    setConfirmStartAgain(false);
    setLookedAgain(null);
    setResumed(false);
    setStored({ state: "sending" });
    setStage({ name: "watch" });
  }

  // The answers to save come in as an argument: after the last question, `answers` still holds the
  // state from before it, so the saved walk lacked its last answer (CRITIC_10 S01).
  async function finish(final: Record<string, AnswerValue>) {
    const answeredAt = new Date().toISOString();
    // Only the answers to questions these answers still ask are kept (lib/walks.ts).
    const settled = settleFollowups(final, followupAnswers, finalRating);
    setAnswers(final);
    setFollowupAnswers(settled.followup_answers);
    setFinalRating(settled.final_rating);
    setWalkLang(lang);
    setStage({ name: "record", answeredAt });
    await keep({
      answers: final,
      answered_at: answeredAt,
      language: lang,
      next: visibleItems(final).length,
      followup_answers: settled.followup_answers,
      final_rating: settled.final_rating,
    });
    await store();
  }

  function answerItem(index: number, value: AnswerValue | undefined) {
    const item = items[index];
    const next = { ...answers };
    if (value === undefined) delete next[item.id];
    else next[item.id] = value;
    setAnswers(next);
    setResumed(false);
    const nextItems = visibleItems(next);
    const pos = nextItems.findIndex((i) => i.id === item.id);
    if (pos + 1 < nextItems.length) {
      void keep({ answers: next, next: pos + 1 });
      setStage({ name: "items", index: pos + 1 });
    } else if (walkQuestions(next).length > 0) {
      void keep({ answers: next, next: nextItems.length });
      setStage({ name: "followups" });
    } else if (walk.question) {
      void keep({ answers: next, next: nextItems.length });
      setStage({ name: "question" });
    } else void finish(next);
  }

  /** After the follow-ups: the checker's question when the walk has one, else the record. */
  function afterFollowups() {
    if (walk.question) setStage({ name: "question" });
    else void finish(answers);
  }

  function answerFollowup(ruleId: string, value: string) {
    const next = { ...followupAnswers, [ruleId]: value };
    setFollowupAnswers(next);
    void keep({ followup_answers: next });
  }

  function onRatingTap(ruleId: string, tap: RatingTap) {
    const firstRating =
      typeof answers.overall_rating === "string"
        ? answers.overall_rating
        : null;
    const next = tapRating(
      { answer: followupAnswers[ruleId], finalRating, changingRating },
      tap,
      firstRating,
    );
    setFinalRating(next.finalRating);
    setChangingRating(next.changingRating);
    const answered =
      next.answer === undefined
        ? followupAnswers
        : { ...followupAnswers, [ruleId]: next.answer };
    setFollowupAnswers(answered);
    void keep({ followup_answers: answered, final_rating: next.finalRating });
  }

  // The clip is mounted once, above whatever the stage shows, so it keeps playing while the person
  // answers. Only the record screen, which comes after, leaves it out.
  let body: React.ReactNode = null;
  switch (stage.name) {
    case "loading":
      body = (
        <p role="status" className="muted">
          {t("walk.loading")}
        </p>
      );
      break;
    case "watch":
      body = (
        <>
          <p className="walk-lead">{t("walk.intro")}</p>
          {/* The clips show natural creeks, so an honest check finds little for a city to do. This
              says how to see a measure before the check starts (CRITIC_09 Q01). */}
          <p className="walk-lead" data-testid="walk-honest-note">
            {t("walk.honest_note")}
          </p>
          {/* The button before the demo notice, so it is on the first screen of every walk on a
              390 by 844 phone (CRITIC_11 V01). */}
          <button
            type="button"
            className="btn btn-block"
            onClick={() => setStage({ name: "items", index: 0 })}
          >
            {t("walk.start")}
          </button>
          <p className="notice notice-warn">{t("walk.demo_notice")}</p>
          {/* The list of languages is under the title, above the clip; its note stays here. */}
          <LanguagePicker part="note" />
        </>
      );
      break;
    case "items": {
      const item = items[stage.index];
      if (item) {
        const count = questionCount(items, stage.index);
        body = (
          <div className="stack" key={item.id}>
            {resumed ? (
              <p
                className="notice notice-ok"
                role="status"
                data-testid="walk-resumed"
              >
                {t("walk.resumed")}
              </p>
            ) : null}
            <Progress
              value={count.n}
              max={count.total}
              labelKey="check.progress"
            />
            <FormQuestion
              item={item}
              value={answers[item.id]}
              onAnswer={(v) => answerItem(stage.index, v)}
              onSkip={() => answerItem(stage.index, undefined)}
              onBack={() => {
                setResumed(false);
                if (stage.index === 0) setStage({ name: "watch" });
                else setStage({ name: "items", index: stage.index - 1 });
              }}
              plantRegion={walk.region ?? null}
              lang={lang}
            />
          </div>
        );
      }
      break;
    }
    case "followups": {
      // Shown as the creek check shows the follow-ups the API picked: the same cards, the same
      // words, the same Finish (CheckFlow.tsx).
      const asked = walkQuestions(answers);
      body = (
        <section
          className="stack"
          aria-labelledby="walk-followups-title"
          data-testid="walk-followups"
        >
          {/* Takes focus when the follow-ups appear, as each question's heading does (WCAG 2.4.3). */}
          <FocusHeading level={2} id="walk-followups-title">
            {t(
              asked.length === 1
                ? "check.followups_title_one"
                : "check.followups_title",
            )}
          </FocusHeading>
          <p className="small muted">{t("check.followups_intro")}</p>
          {asked.map(({ card }) => (
            <FollowupCard
              key={card.rule_id}
              followup={card}
              value={followupAnswers[card.rule_id]}
              onAnswer={(v) => answerFollowup(card.rule_id, v)}
              photos={[]}
              onPhotos={() => undefined}
              changingRating={changingRating}
              ratingOptions={shownOptions(ratingItem, lang)}
              lang={lang}
              finalRating={finalRating}
              onRatingTap={(tap) => onRatingTap(card.rule_id, tap)}
            />
          ))}
          <div className="btn-row">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() =>
                setStage({
                  name: "items",
                  index: Math.max(0, items.length - 1),
                })
              }
              lang={uiText("back", t("check.back"), lang).lang}
            >
              {uiText("back", t("check.back"), lang).text}
            </button>
            <button type="button" className="btn" onClick={afterFollowups}>
              {t("check.finish")}
            </button>
          </div>
        </section>
      );
      break;
    }
    case "question": {
      const q = walk.question!;
      body = (
        <>
          <section
            className="card stack"
            aria-label={t("label.checker_noticed")}
          >
            <p>
              <strong>
                {t("followup.checker_flag", {
                  note: featureById(q.feature)?.plain ?? q.feature,
                })}
              </strong>
            </p>
            <p className="small muted">
              {t("label.checker_noticed")}: {q.note}
            </p>
            <div className="btn-row">
              <button
                type="button"
                className="btn btn-secondary"
                aria-pressed={lookedAgain === "looked"}
                onClick={() => setLookedAgain("looked")}
              >
                {t("check.looked_again")}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                aria-pressed={lookedAgain === "skipped"}
                onClick={() => setLookedAgain("skipped")}
              >
                {t("check.skip")}
              </button>
            </div>
          </section>
          <button
            type="button"
            className="btn btn-block"
            onClick={() => void finish(answers)}
          >
            {t("check.finish")}
          </button>
        </>
      );
      break;
    }
    case "record": {
      // The checks as the store keeps them: the same rules and the same answers (lib/walks.ts).
      const { kept: checked } = settleFollowups(
        answers,
        followupAnswers,
        finalRating,
      );
      // The FHIR record carries the rating the rating check left, as the stored one does.
      const { bundle, problems } = buildRecord(
        walk,
        answers,
        stage.answeredAt,
        checked.final_rating,
        walkLang ?? lang,
      );
      const recordId = stored.state === "stored" ? stored.record_id : null;
      const city = `/city?walk=${encodeURIComponent(walk.id)}${recordId ? `&record=${encodeURIComponent(recordId)}` : ""}`;
      return (
        <div className="stack">
          <FocusHeading>{t("walk.done_title")}</FocusHeading>
          <p className="notice notice-ok" role="status">
            {t("walk.done_body")}
          </p>
          <p
            className={
              problems.length === 0 ? "badge badge-ok" : "badge badge-bad"
            }
            data-testid="walk-structure"
          >
            {problems.length === 0
              ? t("walk.structure_ok")
              : t("walk.structure_bad", { n: problems.length })}
          </p>
          <section
            className="card stack"
            aria-labelledby="walk-stored-title"
            data-testid="walk-stored"
          >
            <h2 id="walk-stored-title">{t("walk.stored_heading")}</h2>
            {stored.state === "stored" ? (
              <>
                <p>
                  <Link
                    href={`/spot?id=${encodeURIComponent(stored.record_id)}`}
                    data-testid="walk-record-link"
                  >
                    {t("walk.stored_link")}
                  </Link>
                </p>
                <p className="small muted">
                  {t("walk.stored_until", {
                    date: walkDay(stored.delete_after),
                  })}
                </p>
              </>
            ) : stored.state === "waiting" ? (
              <>
                <p>{t("walk.stored_waiting")}</p>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => void flushQueue()}
                >
                  {t("walk.stored_retry")}
                </button>
              </>
            ) : stored.state === "failed" ? (
              <p className="notice notice-warn">
                {t("walk.stored_failed", { detail: stored.detail })}
              </p>
            ) : (
              <p role="status" className="muted">
                {t("walk.stored_sending")}
              </p>
            )}
          </section>
          <WalkAnswers
            answers={answers}
            title={t("walk.answers_title")}
            lang={walkLang ?? lang}
          />
          <ChecksThatRan checks={checked.checks} ratings={checked} level="h2" />
          <p className="small muted">{checkerLine(walk)}</p>
          <FhirView
            load={() => Promise.resolve(bundle)}
            curl={recordId ? `curl -s ${api.walkFhirUrl(recordId)}` : null}
            walk="phone"
          />
          <p>
            <Link className="btn btn-block" href={city}>
              {t("walk.city_link")}
            </Link>
          </p>
          {/* Start again clears the walk and its record from this device, and with them the only
              place its link is shown, so it asks first and says what stays (critic round 15 Y02). */}
          {confirmStartAgain ? (
            <section
              className="card stack"
              data-testid="walk-start-again-warn"
              aria-label={t("walk.start_again")}
            >
              <p>
                {t("walk.start_again_warn")}
                {stored.state === "stored"
                  ? ` ${t("walk.start_again_warn_stored", { date: walkDay(stored.delete_after) })}`
                  : ""}
              </p>
              <div className="btn-row">
                <button
                  ref={keepWalk}
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setConfirmStartAgain(false)}
                >
                  {t("walk.start_again_no")}
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={() => void startAgain()}
                >
                  {t("walk.start_again_yes")}
                </button>
              </div>
            </section>
          ) : (
            <button
              type="button"
              className="btn btn-secondary btn-block"
              onClick={() => setConfirmStartAgain(true)}
            >
              {t("walk.start_again")}
            </button>
          )}
          <p>
            <Link href="/walk">{t("walk.more")}</Link>
          </p>
        </div>
      );
    }
  }

  // No clip while the walk is being opened: a finished walk opens on its record, which has none,
  // so a reload no longer paints an empty clip first (critic round 15 O02 item 4).
  return (
    <div className="stack">
      <FocusHeading>{walk.creek_name}</FocusHeading>
      {/* The languages right under the title, so the first screen of a phone shows them before
          the walk starts (audit finding phone-ux-languages-5). Start still fits that screen. */}
      {stage.name === "watch" ? <LanguagePicker part="list" /> : null}
      {stage.name === "loading" ? null : <Clip walk={walk} />}
      {body}
    </div>
  );
}
