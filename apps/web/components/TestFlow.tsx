"use client";

import { useEffect, useRef, useState } from "react";
import { Consent } from "./Consent";
import { FocusHeading } from "./FocusHeading";
import { Lesson } from "./Lesson";
import { ScoreScreen } from "./ScoreScreen";
import { TestItems } from "./TestItems";
import { Warmup } from "./Warmup";
import { api, type CompleteResponse, type SessionResponse, type TestAnswer } from "@/lib/api";
import { content, FEATURE_IDS, testItemById } from "@/lib/content";
import { buildHash, captureSource, clientTokenHash, setContributorToken, sourceLabel, uaClass } from "@/lib/session";
import { t } from "@/lib/t";

type Stage =
  | { name: "consent" }
  | { name: "warmup"; hidden: string }
  | { name: "assigning" }
  | { name: "lesson"; session: SessionResponse; after: "test" | "done" }
  | { name: "test"; session: SessionResponse }
  | { name: "before_score"; session: SessionResponse }
  | { name: "completing"; session: SessionResponse }
  | { name: "score"; session: SessionResponse; result: CompleteResponse; token?: string }
  | { name: "done" }
  | { name: "error"; message: string; retry: () => void };

/** The study flow. Consent first, then warm-up, then the server assigns an arm. */
export function TestFlow() {
  const [stage, setStage] = useState<Stage>({ name: "consent" });
  const pending = useRef<Promise<void>[]>([]);
  const failed = useRef(0);
  const [prior, setPrior] = useState<"yes" | "no" | null>(null);
  const [keep, setKeep] = useState(false);

  useEffect(() => {
    captureSource(window.location.search);
  }, []);

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
      if (clean.lesson_first) setStage({ name: "lesson", session: clean, after: "test" });
      else setStage({ name: "test", session: clean });
    } catch {
      setStage({ name: "error", message: t("error.network"), retry: () => void assign(hidden, warmupChoice) });
    }
  }

  function onAnswer(session: SessionResponse) {
    return (itemId: string, answer: TestAnswer, rtMs: number, position: number) => {
      const p = api.sendResponse({ session_id: session.session_id, item_id: itemId, answer, rt_ms: rtMs, position }).catch(() => {
        failed.current += 1;
      });
      pending.current.push(p);
    };
  }

  async function complete(session: SessionResponse) {
    setStage({ name: "completing", session });
    await Promise.allSettled(pending.current);
    try {
      const result = await api.complete({ session_id: session.session_id, prior_experience: prior, keep_score: keep });
      if (result.contributor_token) setContributorToken(result.contributor_token);
      setStage({ name: "score", session, result, token: result.contributor_token });
    } catch {
      setStage({ name: "error", message: t("error.network"), retry: () => void complete(session) });
    }
  }

  switch (stage.name) {
    case "consent":
      return <Consent onStart={(hidden) => setStage({ name: "warmup", hidden })} />;
    case "warmup":
      return <Warmup onChoice={(choice) => void assign(stage.hidden, choice)} />;
    case "assigning":
      return (
        <p role="status" className="muted">
          {t("test.assigning")}
        </p>
      );
    case "lesson":
      return (
        <Lesson
          features={FEATURE_IDS}
          onDone={(seconds) => {
            void api.lessonDone(stage.session.session_id, seconds).catch(() => undefined);
            if (stage.after === "test") setStage({ name: "test", session: stage.session });
            else setStage({ name: "done" });
          }}
        />
      );
    case "test":
      return <TestItems order={stage.session.item_order} onAnswer={onAnswer(stage.session)} onDone={() => setStage({ name: "before_score", session: stage.session })} />;
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
          <button type="submit" className="btn btn-block">
            {t("end.see_score")}
          </button>
        </form>
      );
    case "completing":
      return (
        <p role="status" className="muted">
          {t("end.scoring")}
        </p>
      );
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
                  <button type="button" className="btn" onClick={() => setStage({ name: "lesson", session: stage.session, after: "done" })}>
                    {t("end.lesson_start")}
                  </button>
                  <button type="button" className="btn btn-secondary" onClick={() => setStage({ name: "done" })}>
                    {t("end.lesson_skip")}
                  </button>
                </div>
              </section>
            ) : (
              <div className="btn-row">
                <button type="button" className="btn btn-secondary" onClick={() => setStage({ name: "done" })}>
                  {t("end.finish")}
                </button>
              </div>
            )}
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
          <p className="notice notice-bad" role="alert">
            {stage.message}
          </p>
          <button type="button" className="btn" onClick={stage.retry}>
            {t("error.retry")}
          </button>
        </div>
      );
  }
}
