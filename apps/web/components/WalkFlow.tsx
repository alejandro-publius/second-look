"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FhirView } from "./FhirView";
import { FocusHeading } from "./FocusHeading";
import { FormQuestion } from "./FormQuestion";
import { Photo } from "./Photo";
import { Progress } from "./Progress";
import { WalkAnswers, walkDay } from "./WalkRecord";
import { api, type AnswerValue } from "@/lib/api";
import { content, featureById, licenseName, licenseUrl, questionCount, type FormItem, type Walk } from "@/lib/content";
import { deleteWalkState, enqueue, flushQueue, getQueued, loadWalkState, onQueueChange, removeQueued, saveWalkState, sendQueued, startQueueWatcher, type WalkState } from "@/lib/offline";
import { t } from "@/lib/t";
import { buildRecord } from "@/lib/walks";

type Stage =
  | { name: "loading" }
  | { name: "watch" }
  | { name: "items"; index: number }
  | { name: "question" }
  | { name: "record"; answeredAt: string };

/** Where the finished walk's record is: being sent, waiting for a network, kept, or refused. */
type Stored =
  | { state: "sending" }
  | { state: "waiting" }
  | { state: "stored"; record_id: string; delete_after: string }
  | { state: "failed"; detail: string };

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
export function checkerLine(walk: Pick<Walk, "question" | "checker_run" | "checker_dropped">): string {
  if (walk.question) return t("walk.checker_asked");
  if (walk.checker_run !== "real") return t("walk.checker_not_real");
  if (walk.checker_dropped === 0) return t("walk.checker_nothing_seen");
  if (walk.checker_dropped === 1) return t("walk.checker_none_one");
  return t("walk.checker_none", { n: walk.checker_dropped });
}

/** The stage a walk this device holds opens on: its record, or the next unanswered question. */
function resumeStage(walk: Walk, saved: WalkState): Stage {
  if (saved.answered_at) return { name: "record", answeredAt: saved.answered_at };
  const items = visibleItems(saved.answers);
  if (saved.next < items.length) return { name: "items", index: Math.max(0, saved.next) };
  return walk.question ? { name: "question" } : { name: "items", index: Math.max(0, items.length - 1) };
}

/**
 * A guided creek check made while watching a clip (Update 14 3.7). The checker's flag, if the gate
 * let one through at build time, is asked only after the person has answered.
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
  const [lookedAgain, setLookedAgain] = useState<string | null>(null);
  const [resumed, setResumed] = useState(false);
  const [stored, setStored] = useState<Stored>({ state: "sending" });
  const items = useMemo(() => visibleItems(answers), [answers]);

  // The walk as this device keeps it, and the writes to IndexedDB, one after another in order.
  const kept = useRef<WalkState>({ walk_id: walk.id, answers: {}, next: 0, answered_at: null, queue_id: null, record_id: null, delete_after: null });
  const writes = useRef<Promise<void>>(Promise.resolve());
  // Start again begins a new attempt. A send still going for the old one must not write into the
  // new one, or a reload would open on the walk that was set aside.
  const attempt = useRef(0);
  const keep = useCallback((patch: Partial<WalkState>) => {
    const next = { ...kept.current, ...patch, walk_id: walk.id };
    kept.current = next;
    writes.current = writes.current.then(() => saveWalkState(next));
    return writes.current;
  }, [walk.id]);

  /** Reads the finished walk's queue item and shows what the store did with it. */
  const showQueued = useCallback(async () => {
    const mine = attempt.current;
    const id = kept.current.queue_id;
    if (kept.current.record_id && kept.current.delete_after) {
      setStored({ state: "stored", record_id: kept.current.record_id, delete_after: kept.current.delete_after });
      return;
    }
    if (id === null) return;
    const item = await getQueued(id).catch(() => undefined);
    if (item === undefined || attempt.current !== mine) return;
    if (item.status === "sent" && item.result?.record_id && item.result.delete_after) {
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
    const body = { walk_id: walk.id, answers: w.answers, answered_at: w.answered_at };
    let id: number;
    try {
      id = await enqueue({ kind: "walk", created_at: new Date().toISOString(), walk: body, photos: [] });
    } catch {
      // No IndexedDB here (a private window can refuse it), so no queue: send it once, directly.
      try {
        const r = await api.storeWalk(body);
        if (attempt.current === mine) setStored({ state: "stored", record_id: r.record_id, delete_after: r.delete_after });
      } catch (err) {
        if (attempt.current === mine) setStored({ state: "failed", detail: (err as { detail?: string }).detail ?? t("error.network") });
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
      setAnswers(saved.answers);
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
    if (w.queue_id !== null && !w.record_id) await removeQueued(w.queue_id).catch(() => undefined);
    kept.current = { walk_id: walk.id, answers: {}, next: 0, answered_at: null, queue_id: null, record_id: null, delete_after: null };
    writes.current = writes.current.then(() => deleteWalkState(walk.id));
    await writes.current;
    setAnswers({});
    setLookedAgain(null);
    setResumed(false);
    setStored({ state: "sending" });
    setStage({ name: "watch" });
  }

  // The answers to save come in as an argument: after the last question, `answers` still holds the
  // state from before it, so the saved walk lacked its last answer (CRITIC_10 S01).
  async function finish(final: Record<string, AnswerValue>) {
    const answeredAt = new Date().toISOString();
    setAnswers(final);
    setStage({ name: "record", answeredAt });
    await keep({ answers: final, answered_at: answeredAt, next: visibleItems(final).length });
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
    } else if (walk.question) {
      void keep({ answers: next, next: nextItems.length });
      setStage({ name: "question" });
    } else void finish(next);
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
            {resumed ? (
              <p className="notice notice-ok" role="status" data-testid="walk-resumed">
                {t("walk.resumed")}
              </p>
            ) : null}
            <Progress value={count.n} max={count.total} labelKey="check.progress" />
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
          <button type="button" className="btn btn-block" onClick={() => void finish(answers)}>
            {t("check.finish")}
          </button>
        </>
      );
      break;
    }
    case "record": {
      const { bundle, problems } = buildRecord(walk, answers, stage.answeredAt);
      const recordId = stored.state === "stored" ? stored.record_id : null;
      const city = `/city?walk=${encodeURIComponent(walk.id)}${recordId ? `&record=${encodeURIComponent(recordId)}` : ""}`;
      return (
        <div className="stack">
          <FocusHeading>{t("walk.done_title")}</FocusHeading>
          <p className="notice notice-ok" role="status">
            {t("walk.done_body")}
          </p>
          <p className={problems.length === 0 ? "badge badge-ok" : "badge badge-bad"} data-testid="walk-structure">
            {problems.length === 0 ? t("walk.structure_ok") : t("walk.structure_bad", { n: problems.length })}
          </p>
          <section className="card stack" aria-labelledby="walk-stored-title" data-testid="walk-stored">
            <h2 id="walk-stored-title">{t("walk.stored_heading")}</h2>
            {stored.state === "stored" ? (
              <>
                <p>
                  <Link href={`/spot?id=${encodeURIComponent(stored.record_id)}`} data-testid="walk-record-link">
                    {t("walk.stored_link")}
                  </Link>
                </p>
                <p className="small muted">{t("walk.stored_until", { date: walkDay(stored.delete_after) })}</p>
              </>
            ) : stored.state === "waiting" ? (
              <>
                <p>{t("walk.stored_waiting")}</p>
                <button type="button" className="btn btn-secondary" onClick={() => void flushQueue()}>
                  {t("walk.stored_retry")}
                </button>
              </>
            ) : stored.state === "failed" ? (
              <p className="notice notice-warn">{t("walk.stored_failed", { detail: stored.detail })}</p>
            ) : (
              <p role="status" className="muted">
                {t("walk.stored_sending")}
              </p>
            )}
          </section>
          <WalkAnswers answers={answers} title={t("walk.answers_title")} />
          <p className="small muted">{checkerLine(walk)}</p>
          <FhirView load={() => Promise.resolve(bundle)} curl={recordId ? `curl -s ${api.walkRecordUrl(recordId)}` : null} walk="phone" />
          <p>
            <Link className="btn btn-block" href={city}>
              {t("walk.city_link")}
            </Link>
          </p>
          <button type="button" className="btn btn-secondary btn-block" onClick={() => void startAgain()}>
            {t("walk.start_again")}
          </button>
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
