"use client";

import { useEffect, useRef, useState } from "react";
import { Consent } from "./Consent";
import { FocusHeading } from "./FocusHeading";
import { Lesson } from "./Lesson";
import { Part2Offer } from "./Part2Offer";
import { ScoreScreen } from "./ScoreScreen";
import { TestItems } from "./TestItems";
import { Warmup } from "./Warmup";
import { Button } from "./ui/Button";
import { Icon } from "./ui/Icon";
import { Skeleton } from "./ui/Skeleton";
import { api, type FeatureScoreOut, type ResponseRequest, type SessionResponse, type TestAnswer } from "@/lib/api";
import type { AnswerTrail } from "./TestItems";
import { content, FEATURE_IDS, testItemById } from "@/lib/content";
import { buildHash, captureSource, clearOpenSession, clientTokenHash, getOpenSession, setContributorToken, setOpenSession, sourceLabel, takeLandingGuess, uaClass } from "@/lib/session";
import { t } from "@/lib/t";

interface Result {
  scores: FeatureScoreOut[];
  correct_total: number;
}

type Stage =
  | { name: "restoring" }
  | { name: "consent" }
  | { name: "warmup"; hidden: string }
  | { name: "assigning" }
  | { name: "lesson"; session: SessionResponse; after: "test" | "done"; startIndex: number }
  | { name: "test"; session: SessionResponse; startIndex: number }
  | { name: "before_score"; session: SessionResponse }
  | { name: "completing"; session: SessionResponse }
  | { name: "score"; session: SessionResponse; result: Result; token?: string }
  | { name: "done" }
  | { name: "error"; message: string; retry: () => void };

/**
 * The study flow. Consent first, then warm-up, then the server assigns an arm.
 *
 * A reload resumes, it never restarts. The session id lives in this browser and the server holds
 * the arm, the item order and every answer it has, so a refresh at item 7 comes back at item 7
 * with the same order and the same arm, and makes no second session row.
 */
export function TestFlow() {
  const [stage, setStage] = useState<Stage>({ name: "restoring" });
  const pending = useRef<Promise<void>[]>([]);
  // Every answer this browser confirmed, kept so it can be sent again if one never arrived.
  const sent = useRef<Map<string, ResponseRequest>>(new Map());
  // Ids the server already held when we resumed. We count them but never resend them, because
  // this browser does not know what was answered.
  const resumed = useRef<Set<string>>(new Set());
  const [failed, setFailed] = useState(0);
  const [prior, setPrior] = useState<"yes" | "no" | null>(null);
  const [keep, setKeep] = useState(false);

  useEffect(() => {
    captureSource(window.location.search);
    void restore();
    // Runs once on mount: restore reads storage and asks the server where this sitting was.
  }, []);

  async function restore() {
    const open = getOpenSession();
    if (!open) {
      setStage({ name: "consent" });
      return;
    }
    try {
      const state = await api.resume(open.session_id);
      const known = state.item_order.filter((id) => testItemById(id));
      const session: SessionResponse = {
        session_id: state.session_id,
        arm: state.arm,
        item_order: known,
        lesson_first: state.lesson_first,
      };
      if (state.completed) {
        // The end screen again, from what the server already scored. Nothing new is created and
        // no second contributor token is minted. The id stays in this browser, because one
        // browser is one sitting: a reload must not offer a second run of the test.
        setStage({
          name: "score",
          session,
          result: { scores: state.scores ?? [], correct_total: state.correct_total ?? 0 },
        });
        return;
      }
      for (const id of state.answered) resumed.current.add(id);
      if (state.lesson_first && !state.lesson_done) {
        setStage({ name: "lesson", session, after: "test", startIndex: open.lesson_index ?? 0 });
        return;
      }
      const next = known.findIndex((id) => !state.answered.includes(id));
      if (next === -1) setStage({ name: "before_score", session });
      else setStage({ name: "test", session, startIndex: next });
    } catch {
      // The sitting is gone or the API is down. Start clean rather than strand the person.
      clearOpenSession();
      setStage({ name: "consent" });
    }
  }

  async function assign(hidden: string, warmupChoice: string) {
    setStage({ name: "assigning" });
    try {
      const session = await api.createSession({
        consent_version: content.consent_version,
        content_hash: content.content_hash,
        build_hash: buildHash(),
        source_label: sourceLabel(),
        hidden_field: hidden,
        client_token_hash: await clientTokenHash(),
        ua_class: uaClass(),
        warmup_choice: warmupChoice,
      });
      const known = session.item_order.filter((id) => testItemById(id));
      if (known.length === 0) throw new Error("item order unknown");
      const clean = { ...session, item_order: known };
      setOpenSession({ session_id: clean.session_id, lesson_index: 0 });
      if (clean.lesson_first) setStage({ name: "lesson", session: clean, after: "test", startIndex: 0 });
      else setStage({ name: "test", session: clean, startIndex: 0 });
    } catch {
      setStage({ name: "error", message: t("error.network"), retry: () => void assign(hidden, warmupChoice) });
    }
  }

  function onAnswer(session: SessionResponse) {
    return (itemId: string, answer: TestAnswer, rtMs: number, position: number, trail: AnswerTrail) => {
      const body: ResponseRequest = { session_id: session.session_id, item_id: itemId, answer, rt_ms: rtMs, position, ...trail };
      sent.current.set(itemId, body);
      const p = api
        .sendResponse(body)
        // One retry here, then the gap is closed at complete before the score is shown.
        .catch(() => api.sendResponse(body))
        .catch(() => {
          setFailed((n) => n + 1);
        });
      pending.current.push(p);
    };
  }

  /**
   * The end screen does not appear until the server holds every answer. We send how many this
   * browser took; if the server holds fewer it names the ones it is missing and we send those
   * again from our own copy. Responses are idempotent, so a resend is safe. Only when a resend
   * still fails does the sitting carry an unsent count.
   */
  async function complete(session: SessionResponse) {
    setStage({ name: "completing", session });
    await Promise.allSettled(pending.current);
    try {
      const answered = new Set([...resumed.current, ...sent.current.keys()]).size;
      let result = await api.complete({ session_id: session.session_id, prior_experience: prior, keep_score: keep, answered_count: answered });
      if (result.need_resend && result.need_resend.length > 0) {
        await Promise.allSettled(result.need_resend.map((id) => (sent.current.has(id) ? api.sendResponse(sent.current.get(id)!) : Promise.resolve())));
        result = await api.complete({ session_id: session.session_id, prior_experience: prior, keep_score: keep, answered_count: answered, final: true });
      }
      if (result.contributor_token) setContributorToken(result.contributor_token);
      setStage({
        name: "score",
        session,
        result: { scores: result.scores ?? [], correct_total: result.correct_total ?? 0 },
        token: result.contributor_token,
      });
    } catch {
      setStage({ name: "error", message: t("error.network"), retry: () => void complete(session) });
    }
  }

  switch (stage.name) {
    case "restoring":
      return <Skeleton label={t("test.resuming")} lines={2} photo={false} />;
    case "consent":
      return (
        <Consent
          onStart={(hidden) => {
            const guess = takeLandingGuess();
            if (guess) void assign(hidden, guess);
            else setStage({ name: "warmup", hidden });
          }}
        />
      );
    case "warmup":
      return <Warmup onChoice={(choice) => void assign(stage.hidden, choice)} />;
    case "assigning":
      return <Skeleton label={t("test.assigning")} />;
    case "lesson":
      return (
        <Lesson
          features={FEATURE_IDS}
          startIndex={stage.startIndex}
          onIndex={(i) => {
            if (stage.after === "test") setOpenSession({ session_id: stage.session.session_id, lesson_index: i });
          }}
          onDone={(seconds) => {
            void api.lessonDone(stage.session.session_id, seconds).catch(() => undefined);
            if (stage.after === "test") setStage({ name: "test", session: stage.session, startIndex: 0 });
            else setStage({ name: "done" });
          }}
        />
      );
    case "test":
      return (
        <>
          {failed > 0 ? (
            <div className="notice notice-warn" role="status">
              <Icon name="wifi-slash" />
              <p>{t("test.some_unsent")}</p>
            </div>
          ) : null}
          <TestItems order={stage.session.item_order} startIndex={stage.startIndex} onAnswer={onAnswer(stage.session)} onDone={() => setStage({ name: "before_score", session: stage.session })} />
        </>
      );
    case "before_score":
      return (
        <form
          className="stack"
          onSubmit={(e) => {
            e.preventDefault();
            void complete(stage.session);
          }}
        >
          <FocusHeading>{t("end.before_title")}</FocusHeading>
          <fieldset className="card">
            <legend>{t("end.prior_experience")}</legend>
            <div className="option-list">
              {(["yes", "no"] as const).map((v) => (
                <label key={v} className="option">
                  <input type="radio" name="prior" value={v} checked={prior === v} onChange={() => setPrior(v)} />
                  <span>{t(v === "yes" ? "end.prior_yes" : "end.prior_no")}</span>
                </label>
              ))}
            </div>
            <p className="small muted">{t("end.prior_optional")}</p>
          </fieldset>
          <label className="check">
            <input type="checkbox" name="keep_score" checked={keep} onChange={(e) => setKeep(e.target.checked)} />
            <span>
              {t("end.keep_score")}
              <br />
              <span className="small muted">{t("end.keep_score_note")}</span>
            </span>
          </label>
          <div className="actions">
            <Button type="submit" block>
              {t("end.see_score")}
            </Button>
          </div>
        </form>
      );
    case "completing":
      return <Skeleton label={t("end.scoring")} lines={3} photo={false} />;
    case "score": {
      const untrained = !stage.session.lesson_first;
      return (
        <div className="stack">
          <FocusHeading>{t("end.title")}</FocusHeading>
          <ScoreScreen scores={stage.result.scores} correctTotal={stage.result.correct_total} token={stage.token}>
            {untrained ? (
              <section className="card stack">
                <h2>{t("end.lesson_offer_title")}</h2>
                <p>{t("end.lesson_offer")}</p>
                <div className="btn-row">
                  <Button onClick={() => setStage({ name: "lesson", session: stage.session, after: "done", startIndex: 0 })}>{t("end.lesson_start")}</Button>
                  <Button kind="secondary" onClick={() => setStage({ name: "done" })}>
                    {t("end.lesson_skip")}
                  </Button>
                </div>
              </section>
            ) : (
              <div className="btn-row">
                <Button kind="secondary" onClick={() => setStage({ name: "done" })}>
                  {t("end.finish")}
                </Button>
              </div>
            )}
            {/* The one change to part 1 (UPDATE_31, docs/deviations.md): the offer of part 2. */}
            <Part2Offer sessionId={stage.session.session_id} onDecline={() => setStage({ name: "done" })} />
          </ScoreScreen>
        </div>
      );
    }
    case "done":
      return (
        <div className="stack">
          <FocusHeading>{t("end.done_title")}</FocusHeading>
          <p>{t("end.done")}</p>
          <p>{t("end.last_line")}</p>
        </div>
      );
    case "error":
      return (
        <div className="stack">
          <div className="notice notice-bad" role="alert">
            <Icon name="warning-circle" />
            <p>{stage.message}</p>
          </div>
          <div className="actions">
            <Button block onClick={stage.retry}>
              {t("error.retry")}
            </Button>
          </div>
        </div>
      );
  }
}
